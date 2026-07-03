# Monthly Active Users

Monthly Active Users (MAU) is calculated as the distinct count of active customer IDs in the analytics month.

## Formula
`COUNT(DISTINCT customer_id) WHERE event_type IN ('session_start', 'purchase', 'support_ticket')`

## Dependencies
- Customer Profile Dataset
- Orders API

## Owner
Growth Analytics Team
