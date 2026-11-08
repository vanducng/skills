-- nightly export
SELECT o.*, c.* FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.created_at > now() - interval '1 day';
