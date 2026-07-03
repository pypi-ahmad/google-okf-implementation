---
type: Playbook
---

# Traffic Drop — First Response

This file has exactly one frontmatter field: `type`. That is the entire
OKF v0.1 requirement — everything else (`title`, `description`, `tags`,
`timestamp`, ...) is optional. A consumer without a `title` field falls
back to deriving one from the filename or the first heading in the body.

# Trigger

[Weekly Active Users](/metrics/weekly_active_users.md) drops more than
20% week-over-week.

# Steps

1. Check whether the drop correlates with a [Website Traffic](/datasets/web_traffic.md)
   ingestion gap (missing events look identical to a real drop).
2. Check recent deploys to the marketing site.
3. If no technical cause is found, escalate to the growth team.
