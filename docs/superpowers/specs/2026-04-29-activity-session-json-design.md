# Activity Session JSON Design

Date: 2026-04-29
Topic: Session-based macOS activity logging to JSON
Status: Approved in chat, pending user review of written spec

## Goal

Change the activity collector so it records one JSON entry per continuous foreground-app session instead of writing a new entry every polling interval.

This is a local MVP hackathon flow. It should stay simple:

- JSON is the only storage target
- no database writes
- no user model
- no summary changes in this task

## Current Problem

The collector polls the foreground macOS app every 2 seconds and currently finalizes a session on every poll. That produces many tiny entries for the same app even when the user stays in the same app continuously.

Example of bad current behavior:

- `Code` from `14:12:19` to `14:12:21`
- `Code` from `14:12:21` to `14:12:23`
- `Code` from `14:12:23` to `14:12:25`

Desired behavior:

- one `Code` session from `14:12:19` until the app actually changes or the collector stops

## Scope

In scope:

- change collector behavior from interval snapshots to session-based logging
- change JSON entry shape
- keep daily JSON files
- keep polling-based app detection
- add or update tests for the new behavior

Out of scope:

- summary service changes
- database models or migrations
- category analysis or app classification logic beyond a fixed default
- bundle ID enrichment
- frontend or API work

## Target JSON Shape

Each finalized session is stored as one object in the day file.

```json
{
  "title": "Code",
  "category": "work",
  "description": "",
  "started_at": "2026-04-29T14:12:19Z",
  "ended_at": "2026-04-29T14:30:45Z",
  "created_at": "2026-04-29T14:30:45Z"
}
```

Field meanings:

- `title`: foreground app name
- `category`: fixed string `"work"` for now
- `description`: empty string for now
- `started_at`: session start timestamp
- `ended_at`: session end timestamp
- `created_at`: write time for the finalized JSON entry

Not included:

- `user`
- `duration_seconds`
- `bundle_id`

## Storage Layout

Daily logs stay in:

- `activity_data/activity_logs/YYYY-MM-DD.json`

Each file contains a JSON array of finalized session objects for that date.

## Behavioral Design

### Polling

The collector continues polling every 2 seconds. Polling remains the detection mechanism only.

Polling no longer implies writing.

### Active Session Lifecycle

The collector keeps one in-memory active session.

1. On startup, read the current foreground app.
2. If an app name is returned successfully, start an in-memory session for that app.
3. On each later poll:
   - if the app name matches the active session title, do nothing
   - if the app name differs, finalize the active session and append it to JSON, then start a new active session
4. On shutdown, finalize the last active session and append it to JSON if one exists

### Same-App Rule

Continuity is determined by `app_name` only.

If the foreground app remains `"Code"` across multiple polls, that entire span becomes one session. No JSON is written during the unchanged span.

### Finalization Rule

A session is finalized only when:

- the foreground app changes
- the collector is interrupted and exits cleanly

## Error Handling

If foreground-app detection fails on a poll:

- record the error
- skip that poll
- do not write an `Unknown` entry
- do not finalize the active session because of that failure alone

This keeps the log cleaner for the MVP and avoids false splits caused by transient read failures.

## Module Changes

### `journal/activity_types.py`

Replace the current session dataclass shape with the JSON entry shape used by the collector:

- `title`
- `category`
- `description`
- `started_at`
- `ended_at`
- `created_at`

### `journal/activity_tracker.py`

Update the tracker so it represents an active session keyed by app title and only returns a completed session when the foreground app actually changes or the collector shuts down.

The tracker should not emit a completed session if the newly read app name is unchanged.

### `journal/activity_store.py`

Update validation and append logic to use the new JSON keys.

The store should keep the same malformed-file recovery behavior:

- malformed JSON becomes an empty list
- non-list JSON becomes an empty list
- invalid items cause safe fallback to an empty list

### `journal/management/commands/collect_activity.py`

Update collection flow so:

- foreground app changes trigger finalization and append
- unchanged app polls do not append
- shutdown finalizes the last session
- app detection failures are logged and skipped

The command remains local, polling-based, and JSON-backed.

## Testing Plan

Update and extend tests in `journal/tests.py`.

Required coverage:

- session objects serialize to the new JSON shape
- store appends and loads the new shape correctly
- unchanged app polls do not finalize a session
- changed app polls finalize the previous session and start the next one
- shutdown finalizes the last session
- app detection failure skips the poll without writing `Unknown`
- collect command still delegates correctly with explicit default arguments

The tests should verify behavior, not implementation detail.

## Acceptance Criteria

This task is done when:

- continuous use of one app produces one JSON entry, not repeated 2-second fragments
- switching apps writes exactly one completed session for the previous app
- stopping the collector writes the final active session if one exists
- JSON entries match the target shape
- no `duration_seconds` field is written
- no `Unknown` entries are written for transient read failures
- relevant `journal` tests pass

## Risks And Tradeoffs

### Partial loss on abrupt termination

Because the active session lives in memory until finalization, a hard crash may lose the in-progress session.

This is acceptable for the current MVP because it keeps the JSON structure simple and avoids writing noisy snapshots.

### Fixed category

Using `"work"` for every record is intentionally simplistic. This preserves forward progress now and leaves categorization for a later task.

## Next Implementation Task

Implement session-based JSON logging in the collector and supporting `journal` modules, then update the `journal` tests to match the new behavior.
