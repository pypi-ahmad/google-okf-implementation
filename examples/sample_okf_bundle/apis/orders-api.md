---
id: api:orders-api
type: api
title: Orders API
description: '`PATCH /v2/orders/{order_id}` updates order status and fulfillment metadata
  for downstream analytics.'
tags:
- api
- apis
- enterprise-docs
- examples
- markdown
resource: apis/orders_api.md
sources:
- apis/orders_api.md
- apis/orders_api_duplicate.md
relationships:
- type: references
  target_id: metric:monthly-active-users
  target_type: metric
  target_title: Monthly Active Users
  path: metrics/monthly-active-users.md
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
timestamp: '2026-07-02T21:01:09.508841+00:00'
---

# Orders API

## Summary
`PATCH /v2/orders/{order_id}` updates order status and fulfillment metadata for downstream analytics.

## Source References
- `apis/orders_api.md`
- `apis/orders_api_duplicate.md`

## Tags
`api`, `apis`, `enterprise-docs`, `examples`, `markdown`

## Relationships
- [Monthly Active Users](../metrics/monthly-active-users.md) (`metric:monthly-active-users`, type=`metric`)
- [Incident: Payment Outage](../playbooks/incident-payment-outage.md) (`playbook:incident-payment-outage`, type=`playbook`)
- [Payment Failure Playbook](../playbooks/payment-failure-playbook.md) (`playbook:payment-failure-playbook`, type=`playbook`)

## Knowledge Notes
### Excerpt 1
# Orders API

### Excerpt 2
## Endpoint
`PATCH /v2/orders/{order_id}` updates order status and fulfillment metadata for downstream analytics.

### Excerpt 3
## Owner
Order Platform Team

### Excerpt 4
## Dependencies
- Customer Profile Dataset
- Monthly Active Users
- Orders Fact Table

### Excerpt 5
## Endpoint
`PATCH /v2/orders/{order_id}`

### Excerpt 6
## Reliability Notes
The Orders API writes to Orders Fact Table and depends on Customer Profile Dataset for enrichment attributes.

### Excerpt 7
## Governance
Changes require schema review by Data Platform and analytics sign-off because Monthly Active Users dashboards consume this endpoint.
