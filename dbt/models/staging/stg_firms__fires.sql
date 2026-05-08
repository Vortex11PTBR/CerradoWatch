-- staging/stg_firms__fires.sql
-- Limpa e tipifica os dados brutos de queimadas do FIRMS/VIIRS
-- Fonte: raw.firms_fire_events (carregada pelo conector Python)

with source as (
    select * from {{ source('raw', 'firms_fire_events') }}
),

renamed as (
    select
        id                                          as fire_id,
        latitude::numeric(9, 6)                     as latitude,
        longitude::numeric(9, 6)                    as longitude,
        acq_date                                    as acquired_date,
        lpad(acq_time::text, 4, '0')                as acquired_time_utc,
        -- Converte HHMM em timestamp completo
        acq_date + (lpad(acq_time::text, 4, '0') || ' minutes')::interval as acquired_at_utc,
        bright_ti4                                  as brightness_ti4_kelvin,
        bright_ti5                                  as brightness_ti5_kelvin,
        frp                                         as fire_radiative_power_mw,
        scan,
        track,
        satellite,
        instrument,
        -- Expande abreviação de confiança para legibilidade
        case confidence
            when 'l' then 'low'
            when 'n' then 'nominal'
            when 'h' then 'high'
        end                                         as detection_confidence,
        case daynight
            when 'D' then 'day'
            when 'N' then 'night'
        end                                         as day_or_night,
        version                                     as firms_version,
        ingested_at
    from source
)

select * from renamed
