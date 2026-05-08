{{
    config(
        materialized='incremental',
        unique_key='deforestation_id',
        schema='staging'
    )
}}

with source as (
    select * from {{ source('raw', 'prodes_deforestation') }}

    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
),

renamed as (
    select
        {{ dbt_utils.generate_surrogate_key(['year', 'state', 'municipality']) }}
            as deforestation_id,
        year::int                       as deforestation_year,
        upper(state)                    as state_code,
        coalesce(nullif(trim(municipality), ''), 'ESTADO') as municipality_name,
        area_km2::numeric(12, 4)        as area_km2,
        biome,
        class_name,
        case class_name
            when 'd' then 'Desmatamento'
            when 'r' then 'Regeneração'
            else 'Outros'
        end                             as class_label,
        ingested_at

    from source
)

select * from renamed
