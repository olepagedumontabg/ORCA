---
name: Salsify sync runs against the live in-memory app, not on-disk code
description: Why a Salsify sync can complete "successfully" yet not reflect recent code changes
---

When debugging why a Salsify sync did not populate a newly-added field (e.g. `parent_id`)
even though the feed and parser were correct: the sync runs inside the long-running
ASP.NET process serving on port 5000. A sync that completes with `products_updated` = full
count can still skip new logic if the running process predates the rebuild.

**Why:** `dotnet run` keeps serving the previously compiled binary until the workflow is
restarted. Editing/merging source on disk does NOT hot-reload the running sync code. A sync
triggered before a restart executes old logic, so it can mark every row "updated" (a
pre-existing quirk — some field always differs) while never writing the new column.

**How to apply:** After any change to `SalsifyService` (or related sync/parse code),
restart the `Start application` workflow BEFORE re-triggering a sync, then verify the DB.
To re-trigger without Salsify: POST `/api/salsify/webhook?key=$SALSIFY_WEBHOOK_SECRET` with
`{"publication_status":"completed","product_feed_url":"<url>", ...}`. Feed URLs stored in
`sync_status.sync_metadata->>'product_feed_url'` (S3 signed, valid ~7 days) can be reused.
