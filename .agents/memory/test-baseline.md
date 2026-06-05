---
name: ORCA test baseline
description: Known pre-existing test failures and how to verify a change didn't cause regressions
---

# Pre-existing failing tests

`dotnet test ORCA.Tests` has a baseline of failing tests that are NOT caused by recent
work — they fail identically on a clean HEAD checkout. As of mid-2026 this was ~10
failures concentrated in `CompatibilityEngineTests` (reverse lookups, door-width
boundaries, sort order, performance) and one in `SalsifyServiceTests`
(`RunSync_Should_Delete_Missing_Product`).

**How to apply:** When tests fail after a change, do NOT assume your change caused them.
Verify against baseline before spending time debugging. The main agent is blocked from
`git stash`/`worktree`/`checkout`/`restore`, so reproduce the baseline by copying the repo
to `/tmp` and overwriting only your changed files with their HEAD versions via
`git show HEAD:<file> > /tmp/copy/<file>`, then `dotnet test` there. Compare failure sets.

**Why:** Saves re-investigating flaky/legacy failures on every change and avoids chasing
phantom regressions.
