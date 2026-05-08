{{
    config(
        materialized='table',
        schema='mart'
    )
}}

/*
  mart_fires_weekly
  -----------------
  Série temporal semanal de focos de queimada no Cerrado.
  Granularidade: 1 linha por semana.
  Usado pelo dashboard para: gráfico de linha histórico, KPI semanal, alertas.
*/

with weekly as (
    select
        date_trunc('week', acquired_date)::date       as week_start,
        (date_trunc('week', acquired_date) + interval '6 days')::date as week_end,
        extract(year  from acquired_date)::int         as year,
        extract(week  from acquired_date)::int         as week_number,

        count(*)                                       as fire_count,
        count(*) filter (where detection_confidence = 'high')  as high_confidence_count,
        count(*) filter (where detection_confidence = 'nominal') as nominal_confidence_count,
        count(*) filter (where day_or_night = 'day')   as day_fires,
        count(*) filter (where day_or_night = 'night') as night_fires,

        round(avg(fire_radiative_power_mw)::numeric, 2)  as avg_frp_mw,
        round(max(fire_radiative_power_mw)::numeric, 2)  as max_frp_mw,
        round(sum(fire_radiative_power_mw)::numeric, 2)  as total_frp_mw

    from {{ ref('stg_firms__fires') }}
    group by 1, 2, 3, 4
),

with_alert as (
    select
        *,
        -- Threshold: 1 000 focos/semana → alerta
        fire_count >= 1000 as alert_threshold_exceeded,

        -- Variação semana a semana
        lag(fire_count) over (order by week_start) as prev_week_fire_count,
        case
            when lag(fire_count) over (order by week_start) > 0
            then round(
                (100.0 * (fire_count - lag(fire_count) over (order by week_start)))
                / lag(fire_count) over (order by week_start), 1
            )
        end as wow_change_pct

    from weekly
)

select * from with_alert
order by week_start
