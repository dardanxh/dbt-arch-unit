select order_id, count(*) as n from {{ ref('fct_orders') }} group by 1
