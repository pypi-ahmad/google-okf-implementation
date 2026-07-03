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
  target_id: dataset:customer-profile-dataset
  target_type: dataset
  target_title: Customer Profile Dataset
  path: datasets/customer-profile-dataset.md
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
- [Customer Profile Dataset](../datasets/customer-profile-dataset.md) (`dataset:customer-profile-dataset`, type=`dataset`)

## Knowledge Notes
### Excerpt 1
column,type,description,owner
order_id,STRING,Unique order identifier,Data Platform
customer_id,STRING,Customer key joined to Customer Profile Dataset,Data Platform
order_status,STRING,Normalized fulfillment status consumed by Orders API,Order Platform
updated_at,TIMESTAMP,Last status update timestamp,Data Platform
