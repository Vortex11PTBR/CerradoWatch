{{
    config(
        materialized='table',
        schema='mart'
    )
}}

/*
  mart_deforestation_annual
  --------------------------
  Desmatamento anual por estado no Cerrado, com variação YoY e ranking.
  Granularidade: 1 linha por (year, state).
  Usado pelo dashboard para: mapa choropleth, gráfico de barras por estado, ranking.
*/

with base as (
    select
        deforestation_year                          as year,
        state_code,
        round(sum(area_km2)::numeric, 2)            as area_km2

    from {{ ref('stg_prodes__deforestation') }}
    where class_name = 'd'          -- apenas desmatamento, não regeneração
    group by 1, 2
),

with_lag as (
    select
        *,
        lag(area_km2) over (
            partition by state_code order by year
        )                                           as prev_year_area_km2,

        sum(area_km2) over (
            partition by state_code order by year rows unbounded preceding
        )                                           as cumulative_area_km2

    from base
),

with_yoy as (
    select
        *,
        case
            when prev_year_area_km2 > 0
            then round(
                (100.0 * (area_km2 - prev_year_area_km2) / prev_year_area_km2)::numeric, 1
            )
        end                                         as yoy_change_pct,

        rank() over (partition by year order by area_km2 desc) as rank_within_year

    from with_lag
),

-- Agrega também totais nacionais (bioma todo) por ano
national as (
    select
        year,
        'BR_CERRADO'                                as state_code,
        round(sum(area_km2)::numeric, 2)            as area_km2,
        lag(round(sum(area_km2)::numeric, 2)) over (
            order by year
        )                                           as prev_year_area_km2,
        null::numeric                               as cumulative_area_km2,
        null::numeric                               as yoy_change_pct,
        0                                           as rank_within_year

    from base
    group by 1
)

select * from with_yoy
union all
select * from national
order by year, rank_within_year
