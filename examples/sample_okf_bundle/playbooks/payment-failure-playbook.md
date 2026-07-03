---
id: playbook:payment-failure-playbook
type: playbook
title: Payment Failure Playbook
description: Checkout payment error rate above 3% for 5 consecutive minutes.
tags:
- enterprise-docs
- examples
- markdown
- playbook
- playbooks
resource: playbooks/payment_failure_playbook.md
sources:
- playbooks/payment_failure_playbook.md
relationships: []
timestamp: '2026-07-02T21:01:21.967043+00:00'
---

# Payment Failure Playbook

## Summary
Checkout payment error rate above 3% for 5 consecutive minutes.

## Source References
- `playbooks/payment_failure_playbook.md`

## Tags
`enterprise-docs`, `examples`, `markdown`, `playbook`, `playbooks`

## Relationships
- none

## Knowledge Notes
### Excerpt 1
# Payment Failure Playbook

### Excerpt 2
## Trigger
Checkout payment error rate above 3% for 5 consecutive minutes.

### Excerpt 3
## Triage Steps
1. Check Orders API latency and error budget burn.
2. Validate write latency on Orders Fact Table.
3. Compare failed customer cohort against Customer Profile Dataset enrichment lag.

### Excerpt 4
## Recovery
Rollback gateway adapter and replay failed events.
