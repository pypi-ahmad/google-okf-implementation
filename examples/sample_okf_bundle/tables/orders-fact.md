---
id: table:orders-fact
type: table
title: Orders Fact
description: column,type,description,owner
tags:
- csv
- enterprise-docs
- examples
- table
- tables
resource: tables/orders_fact.csv
sources:
- tables/orders_fact.csv
relationships:
- type: references
  target_id: api:orders-api
  target_type: api
  target_title: Orders API
  path: apis/orders-api.md
- type: references
  target_id: playbook:incident-payment-outage
  target_type: playbook
  target_title: 'Incident: Payment Outage'
  path: playbooks/incident-payment-outage.md
- type: references
  target_id: playbook:payment-failure-playbook
  target_type: playbook
  target_title: Payment Failure Playbook
  path: playbooks/payment-failure-playbook.md
timestamp: '2026-07-02T21:06:30.868038+00:00'
---

# Orders Fact

## Summary
column,type,description,owner

## Source References
- `tables/orders_fact.csv`

## Tags
`csv`, `enterprise-docs`, `examples`, `table`, `tables`

## Relationships
- [Orders API](../apis/orders-api.md) (`api:orders-api`, type=`api`)
- [Incident: Payment Outage](../playbooks/incident-payment-outage.md) (`playbook:incident-payment-outage`, type=`playbook`)
- [Payment Failure Playbook](../playbooks/payment-failure-playbook.md) (`playbook:payment-failure-playbook`, type=`playbook`)

## Knowledge Notes
### Excerpt 1
column,type,description,owner
order_id,STRING,Unique order identifier,Data Platform
customer_id,STRING,Customer key joined to Customer Profile Dataset,Data Platform
order_status,STRING,Normalized fulfillment status consumed by Orders API,Order Platform
updated_at,TIMESTAMP,Last status update timestamp,Data Platform
