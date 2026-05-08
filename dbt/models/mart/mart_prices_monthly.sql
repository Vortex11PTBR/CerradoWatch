{{
    config(
        materialized='table',
        schema='mart'
    )
}}

/*
  mart_prices_monthly
  --------------------
  Preços mensais de commodities agrícolas (soja, milho, algodão) por estado.
  Granularidade: 1 linha por (month, product, state).
  Usado pelo dashboard para: correlação preço × desmatamento (hipótese: avanço
  do agro sobre o Cerrado é guiado pelo preço das commodities).
*/

with base as (
    select
        date_trunc('month', reference_date)::date   as reference_month,
        product,
        state_code,
        round(avg(price_per_sack_brl)::numeric, 2)  as avg_price_per_sack_brl,
        round(avg(price_per_ton_brl)::numeric, 2)   as avg_price_per_ton_brl,
        count(*)                                    as record_count

    from {{ ref('stg_conab__prices') }}
    group by 1, 2, 3
),

with_mom as (
    select
        *,
        lag(avg_price_per_sack_brl) over (
            partition by product, state_code order by reference_month
        )                                           as prev_month_price,

        case
            when lag(avg_price_per_sack_brl) over (
                partition by product, state_code order by reference_month
            ) > 0
            then round(
                (100.0 * (avg_price_per_sack_brl - lag(avg_price_per_sack_brl) over (
                    partition by product, state_code order by reference_month
                )) / lag(avg_price_per_sack_brl) over (
                    partition by product, state_code order by reference_month
                ))::numeric, 1
            )
        end                                         as mom_change_pct

    from base
)

select
    *,
    extract(year  from reference_month)::int as year,
    extract(month from reference_month)::int as month

from with_mom
order by reference_month, product, state_code
