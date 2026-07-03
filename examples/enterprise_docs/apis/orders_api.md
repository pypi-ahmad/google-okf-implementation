# Orders API

## Endpoint
`PATCH /v2/orders/{order_id}` updates order status and fulfillment metadata for downstream analytics.

## Owner
Order Platform Team

## Dependencies
- Customer Profile Dataset
- Monthly Active Users
- Orders Fact Table

## Operational Notes
This API emits `order.updated` events and triggers reconciliation steps in Payment Failure Playbook when settlement status is delayed.
