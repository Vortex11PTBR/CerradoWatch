{{
    config(
        materialized='incremental',
        unique_key='observation_id',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'inmet_daily_observations') }}

    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
),

renamed as (
    select
        {{ dbt_utils.generate_surrogate_key(['station_code', 'measure_date']) }}
            as observation_id,
        station_code,
        measure_date,
        upper(state) as state_code,

        -- Temperaturas: valores fora do intervalo plausível → NULL
        case when temp_max_c between -20 and 55 then temp_max_c end as temp_max_c,
        case when temp_min_c between -20 and 55 then temp_min_c end as temp_min_c,
        case when temp_avg_c between -20 and 55 then temp_avg_c end as temp_avg_c,

        -- Precipitação: sempre >= 0
        case when precipitation_mm >= 0 then precipitation_mm end as precipitation_mm,

        -- Umidade: 0–100
        case when humidity_pct between 0 and 100 then humidity_pct end as humidity_pct,

        -- Vento: >= 0
        case when wind_speed_ms >= 0 then wind_speed_ms end as wind_speed_ms,

        ingested_at

    from source
)

select * from renamed
