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
  target_id: glossary:mau
  target_type: glossary
  target_title: Mau
  path: glossary/mau.md
- type: references
  target_id: glossary:rpo
  target_type: glossary
  target_title: Rpo
  path: glossary/rpo.md
- type: references
  target_id: glossary:sla
  target_type: glossary
  target_title: Sla
  path: glossary/sla.md
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
- [Mau](../glossary/mau.md) (`glossary:mau`, type=`glossary`)
- [Rpo](../glossary/rpo.md) (`glossary:rpo`, type=`glossary`)
- [Sla](../glossary/sla.md) (`glossary:sla`, type=`glossary`)

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
