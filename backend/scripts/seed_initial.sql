-- Seed inicial por tenant (substituir TENANT_ID antes de executar)

INSERT INTO metric_snapshots (
  id,
  tenant_id,
  metric_date,
  granularity,
  channel,
  leads_count,
  responses_count,
  conversions_count,
  closed_sales_count,
  revenue_total
)
VALUES
  (UUID(), 'TENANT_ID', CURDATE(), 'day', 'whatsapp', 0, 0, 0, 0, 0),
  (UUID(), 'TENANT_ID', CURDATE(), 'day', 'email', 0, 0, 0, 0, 0);
