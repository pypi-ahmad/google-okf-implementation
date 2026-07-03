# Orders API

## Endpoint
`PATCH /v2/orders/{order_id}`

## Reliability Notes
The Orders API writes to Orders Fact Table and depends on Customer Profile Dataset for enrichment attributes.

## Governance
Changes require schema review by Data Platform and analytics sign-off because Monthly Active Users dashboards consume this endpoint.
