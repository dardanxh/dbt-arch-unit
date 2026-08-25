-- TODO: revisit the amount column once refunds land
select
    order_id,
    customer_id,
    amount
from {{ source('raw', 'orders') }}
