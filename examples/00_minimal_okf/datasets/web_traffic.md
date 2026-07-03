---
type: Dataset
title: Website Traffic
description: Raw pageview and session events collected from the marketing site.
resource: https://example.com/warehouse/web_traffic
tags: [web, analytics, raw]
timestamp: 2026-06-15T09:00:00Z
---

Raw event stream capturing every pageview and session on the marketing
site. Each row is one event; sessions are derived downstream, not stored
here directly.

# Schema

| Column        | Type      | Description                          |
|---------------|-----------|---------------------------------------|
| `event_id`    | STRING    | Unique event identifier.               |
| `session_id`  | STRING    | Session the event belongs to.          |
| `page_path`   | STRING    | URL path that was viewed.              |
| `occurred_at` | TIMESTAMP | When the event was recorded.           |

Used to compute [Weekly Active Users](/metrics/weekly_active_users.md).
