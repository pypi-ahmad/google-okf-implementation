---
id: dataset:customer-profile-dataset
type: dataset
title: Customer Profile Dataset
description: Primary customer dimension used across retention reporting, segmentation
  models, and order risk policies.
tags:
- dataset
- datasets
- enterprise-docs
- examples
- markdown
resource: datasets/customer_profile.md
sources:
- datasets/customer_profile.md
relationships:
- type: references
  target_id: api:orders-api
  target_type: api
  target_title: Orders API
  path: apis/orders-api.md
- type: references
  target_id: metric:monthly-active-users
  target_type: metric
  target_title: Monthly Active Users
  path: metrics/monthly-active-users.md
timestamp: '2026-07-02T21:01:16.067947+00:00'
---

# Customer Profile Dataset

## Summary
Primary customer dimension used across retention reporting, segmentation models, and order risk policies.

## Source References
- `datasets/customer_profile.md`

## Tags
`dataset`, `datasets`, `enterprise-docs`, `examples`, `markdown`

## Relationships
- [Orders API](../apis/orders-api.md) (`api:orders-api`, type=`api`)
- [Monthly Active Users](../metrics/monthly-active-users.md) (`metric:monthly-active-users`, type=`metric`)

## Knowledge Notes
### Excerpt 1
# Customer Profile Dataset

Primary customer dimension used across retention reporting, segmentation models, and order risk policies.

### Excerpt 2
## Owner
Data Platform Engineering

### Excerpt 3
## Source Systems
- CRM
- Identity Service

### Excerpt 4
## Downstream Consumers
- Orders API
- Monthly Active Users
