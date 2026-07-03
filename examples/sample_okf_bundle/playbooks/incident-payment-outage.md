---
id: playbook:incident-payment-outage
type: playbook
title: 'Incident: Payment Outage'
description: Checkout failures reached 12% for 28 minutes due to gateway retry storm.
tags:
- enterprise-docs
- examples
- html
- incidents
- playbook
resource: incidents/payment_outage.html
sources:
- incidents/payment_outage.html
relationships:
- type: references
  target_id: playbook:payment-failure-playbook
  target_type: playbook
  target_title: Payment Failure Playbook
  path: playbooks/payment-failure-playbook.md
timestamp: '2026-06-17T00:00:00+00:00'
---

# Incident: Payment Outage

## Summary
Checkout failures reached 12% for 28 minutes due to gateway retry storm.

## Source References
- `incidents/payment_outage.html`

## Tags
`enterprise-docs`, `examples`, `html`, `incidents`, `playbook`

## Relationships
- [Payment Failure Playbook](payment-failure-playbook.md) (`playbook:payment-failure-playbook`, type=`playbook`)

## Knowledge Notes
### Excerpt 1
# Incident: Payment Outage

Checkout failures reached 12% for 28 minutes due to gateway retry storm.

### Excerpt 2
## Systems Involved

Orders API

Orders Fact Table

Payment Failure Playbook
