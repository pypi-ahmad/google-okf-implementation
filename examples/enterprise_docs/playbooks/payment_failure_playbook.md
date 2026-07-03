# Payment Failure Playbook

## Trigger
Checkout payment error rate above 3% for 5 consecutive minutes.

## Triage Steps
1. Check Orders API latency and error budget burn.
2. Validate write latency on Orders Fact Table.
3. Compare failed customer cohort against Customer Profile Dataset enrichment lag.

## Recovery
Rollback gateway adapter and replay failed events.

## Owner
Payments SRE
