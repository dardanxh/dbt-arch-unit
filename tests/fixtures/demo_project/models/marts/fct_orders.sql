select *
from {{ ref('stg_orders') }} o
left join {{ ref('dim_customers') }} c on o.customer_id = c.customer_id
left join public.legacy_orders l on l.order_id = o.order_id
inner join {{ ref('dim_customers') }} a on a.customer_id = o.customer_id
inner join {{ ref('dim_customers') }} b on b.customer_id = o.customer_id
inner join {{ ref('dim_customers') }} d on d.customer_id = o.customer_id
inner join {{ ref('dim_customers') }} e on e.customer_id = o.customer_id
inner join {{ ref('dim_customers') }} f on f.customer_id = o.customer_id
inner join {{ ref('dim_customers') }} g on g.customer_id = o.customer_id
