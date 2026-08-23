with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        customer_id,
        first_name,
        last_name
    from source
)

select customer_id, first_name, last_name from renamed
