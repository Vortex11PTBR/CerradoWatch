{{
    config(
        materialized='incremental',
        unique_key='price_id',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'conab_agricultural_prices') }}

    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
),

renamed as (
    select
        {{ dbt_utils.generate_surrogate_key(['product', 'reference_date', 'state']) }}
            as price_id,
        product,
        reference_date,
        upper(state) as state_code,

        -- Normaliza preços: saca 60kg → tonelada e vice-versa
        price_per_sack::numeric(10, 2) as price_per_sack_brl,
        case
            when price_per_ton is not null
                then price_per_ton::numeric(10, 2)
            when price_per_sack is not null
                then round((price_per_sack * 1000 / 60)::numeric, 2)
        end as price_per_ton_brl,

        unit,
        source_url,
        ingested_at

    from source
    where price_per_sack is not null or price_per_ton is not null
)

select * from renamed
