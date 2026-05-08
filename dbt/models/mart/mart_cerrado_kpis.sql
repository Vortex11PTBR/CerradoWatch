{{
    config(
        materialized='table',
        schema='mart'
    )
}}

/*
  mart_cerrado_kpis
  ------------------
  Tabela de uma única linha com os KPIs principais do Cerrado para o dashboard.
  Atualizada a cada execução do pipeline — o Streamlit lê daqui para o header.

  KPIs:
    - Queimadas: total na última semana completa vs semana anterior
    - Desmatamento: total no ano mais recente disponível vs ano anterior
    - Preços: última cotação de soja e milho (GO, referência)
    - Meta: atualização dos dados
*/

with latest_fires as (
    select
        week_start                      as latest_fire_week,
        fire_count                      as latest_week_fires,
        prev_week_fire_count,
        wow_change_pct                  as fires_wow_pct,
        alert_threshold_exceeded        as fire_alert_active,
        total_frp_mw                    as latest_week_total_frp

    from {{ ref('mart_fires_weekly') }}
    order by week_start desc
    limit 1
),

latest_deforestation as (
    select
        year                            as latest_deforestation_year,
        area_km2                        as latest_year_deforestation_km2,
        prev_year_area_km2              as prev_year_deforestation_km2,
        yoy_change_pct                  as deforestation_yoy_pct

    from {{ ref('mart_deforestation_annual') }}
    where state_code = 'BR_CERRADO'
    order by year desc
    limit 1
),

latest_soja as (
    select
        avg_price_per_sack_brl          as soja_price_brl_sc,
        mom_change_pct                  as soja_mom_pct

    from {{ ref('mart_prices_monthly') }}
    where product = 'soja' and state_code = 'GO'
    order by reference_month desc
    limit 1
),

latest_milho as (
    select
        avg_price_per_sack_brl          as milho_price_brl_sc,
        mom_change_pct                  as milho_mom_pct

    from {{ ref('mart_prices_monthly') }}
    where product = 'milho' and state_code = 'GO'
    order by reference_month desc
    limit 1
)

select
    -- Queimadas
    f.latest_fire_week,
    f.latest_week_fires,
    f.prev_week_fire_count,
    f.fires_wow_pct,
    f.fire_alert_active,
    f.latest_week_total_frp,

    -- Desmatamento
    d.latest_deforestation_year,
    d.latest_year_deforestation_km2,
    d.prev_year_deforestation_km2,
    d.deforestation_yoy_pct,

    -- Preços
    s.soja_price_brl_sc,
    s.soja_mom_pct,
    m.milho_price_brl_sc,
    m.milho_mom_pct,

    -- Metadados
    now()::timestamp                    as generated_at

from latest_fires f
cross join latest_deforestation d
left  join latest_soja  s on true
left  join latest_milho m on true
