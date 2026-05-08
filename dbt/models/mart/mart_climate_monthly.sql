{{
    config(
        materialized='table',
        schema='mart'
    )
}}

/*
  mart_climate_monthly
  ---------------------
  Médias mensais de variáveis climáticas por estado no Cerrado.
  Granularidade: 1 linha por (year_month, state_code).
  Usado pelo dashboard para: correlação temperatura × queimadas, análise de seca.
*/

with daily as (
    select
        date_trunc('month', measure_date)::date     as year_month,
        state_code,
        measure_date,
        temp_max_c,
        temp_min_c,
        temp_avg_c,
        precipitation_mm,
        humidity_pct,
        wind_speed_ms

    from {{ ref('stg_inmet__observations') }}
    where state_code is not null and state_code != ''
),

monthly as (
    select
        year_month,
        state_code,

        -- Quantas estações contribuíram
        count(distinct station_code)                         as station_count,
        count(*)                                             as observation_count,

        -- Temperatura
        round(avg(temp_max_c)::numeric, 1)                  as avg_temp_max_c,
        round(avg(temp_min_c)::numeric, 1)                  as avg_temp_min_c,
        round(avg(temp_avg_c)::numeric, 1)                  as avg_temp_c,
        round(max(temp_max_c)::numeric, 1)                  as peak_temp_max_c,

        -- Precipitação
        round(sum(precipitation_mm)::numeric, 1)            as total_precipitation_mm,
        count(*) filter (where coalesce(precipitation_mm, 0) = 0) as dry_days_count,

        -- Umidade e vento
        round(avg(humidity_pct)::numeric, 1)                as avg_humidity_pct,
        round(avg(wind_speed_ms)::numeric, 1)               as avg_wind_speed_ms,

        -- Indicador de seca: temperatura alta + sem chuva + umidade baixa
        (
            coalesce(avg(temp_max_c), 0) > 35
            and coalesce(sum(precipitation_mm), 0) < 30
            and coalesce(avg(humidity_pct), 100) < 40
        )::int                                               as drought_risk_flag

    from daily
    group by 1, 2
)

select
    *,
    extract(year  from year_month)::int as year,
    extract(month from year_month)::int as month

from monthly
order by year_month, state_code
