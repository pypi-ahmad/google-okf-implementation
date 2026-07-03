---
id: metric:monthly-active-users
type: metric
title: Monthly Active Users
description: Monthly Active Users (MAU) is calculated as the distinct count of active
  customer IDs in the analytics month.
tags:
- enterprise-docs
- examples
- markdown
- metric
- metrics
resource: metrics/monthly_active_users.md
sources:
- metrics/monthly_active_users.md
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
- type: references
  target_id: glossary:mau
  target_type: glossary
  target_title: Mau
  path: glossary/mau.md
timestamp: '2026-07-02T21:01:18.813992+00:00'
---

# Monthly Active Users

## Summary
Monthly Active Users (MAU) is calculated as the distinct count of active customer IDs in the analytics month.

## Source References
- `metrics/monthly_active_users.md`

## Tags
`enterprise-docs`, `examples`, `markdown`, `metric`, `metrics`

## Relationships
- [Orders API](../apis/orders-api.md) (`api:orders-api`, type=`api`)
- [Customer Profile Dataset](../datasets/customer-profile-dataset.md) (`dataset:customer-profile-dataset`, type=`dataset`)
- [Mau](../glossary/mau.md) (`glossary:mau`, type=`glossary`)

## Knowledge Notes
### Excerpt 1
# Monthly Active Users

Monthly Active Users (MAU) is calculated as the distinct count of active customer IDs in the analytics month.

### Excerpt 2
## Formula
`COUNT(DISTINCT customer_id) WHERE event_type IN ('session_start', 'purchase', 'support_ticket')`

### Excerpt 3
## Dependencies
- Customer Profile Dataset
- Orders API

### Excerpt 4
## Owner
Growth Analytics Team
