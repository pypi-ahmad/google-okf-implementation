---
type: Metric
title: Weekly Active Users
description: Count of distinct sessions with at least one pageview in a trailing 7-day window.
tags: [growth, kpi]
timestamp: 2026-06-15T09:00:00Z
---

Weekly Active Users (WAU) counts distinct sessions from
[Website Traffic](/datasets/web_traffic.md) with at least one pageview in
the trailing 7 days. It is recomputed daily.

# Examples

```sql
SELECT COUNT(DISTINCT session_id) AS wau
FROM web_traffic
WHERE occurred_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
```

# Citations

[1] [Active Users definition conventions](https://en.wikipedia.org/wiki/Active_users)
