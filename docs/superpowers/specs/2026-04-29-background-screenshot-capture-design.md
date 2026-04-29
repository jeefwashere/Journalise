# Background Screenshot Capture Design

Date: 2026-04-29
Topic: Background screenshot capture during activity recording
Status: Approved in chat, pending user review of written spec

## Goal

Add a minimal background screenshot capability to the existing activity recording flow.

When `collect_activity` is running, the backend should silently capture screenshots of the main screen at a fixed interval and save them to a local folder.

This is an MVP-only feature. It should stay simple:

- local file storage only
- no frontend
- no database
- no image analysis
- no summary integration

## User Intent

The user wants screenshots only while recording is active.

The user does not want a visible screenshot UI or user-facing flow. The capture should happen quietly in the backend.

Image quality does not need to be especially high. The simplest stable solution is preferred.

## Scope

In scope:

- background screenshot capture while `collect_activity` is running
- fixed interval capture
- local screenshot storage
- minimal error handling that does not crash the recorder
- tests for the screenshot loop and integration points

Out of scope:

- OCR
- AI image understanding
- screenshot deduplication
- compression tuning
- multi-monitor customization
- screenshot review UI
- summary pipeline changes

## Recommended Approach

Use a dedicated background screenshot loop that starts when `collect_activity` starts and stops when recording stops.

This loop should be independent from app switching. The activity collector continues to poll app changes, while the screenshot worker captures images on its own fixed interval.

This is preferred over tying screenshots directly to the activity polling loop because it keeps responsibilities clearer and avoids mixing unrelated timing logic.

## Capture Behavior

### When screenshots run

Screenshots run only while `collect_activity` is actively running.

If recording stops:

- the screenshot worker stops
- no more screenshots are taken

### Interval

Default screenshot interval: `5` seconds.

This should be configurable through the command layer so it can be changed later without editing code.

### Capture target

Capture the full main screen using the simplest macOS-native mechanism available.

No cropping, window targeting, or quality tuning is required for this task.

## Storage Layout

Screenshots should be stored under the collector base directory:

- `base_dir/screenshots/YYYY-MM-DD/`

Example:

- `activity_data/screenshots/2026-04-29/14-30-05.png`

Each file name should be timestamp-based and deterministic enough to avoid collisions during normal usage.

Recommended format:

- `HH-MM-SS.png`

If sub-second uniqueness is needed during implementation, append milliseconds.

## Technical Design

### Capture command

Use the macOS built-in `screencapture` command in silent mode.

Expected form:

```bash
screencapture -x /path/to/file.png
```

Reasoning:

- built into macOS
- no new dependency
- silent mode avoids UI noise
- sufficient for MVP

### Worker model

Create a small background worker using the Python standard library.

Recommended shape:

- one loop running in a daemon thread
- one stop signal using `threading.Event`
- loop structure:
  - compute destination path
  - call screenshot command
  - sleep for the configured interval unless stop is requested

### Integration point

The screenshot worker should be managed by `collect_activity`.

Flow:

1. `collect_activity` starts
2. if screenshot capture is enabled, create and start the worker
3. activity recording loop runs as usual
4. on normal exit or `KeyboardInterrupt`, signal screenshot worker to stop
5. wait briefly for clean shutdown

## Error Handling

Screenshot failures should not crash activity recording.

If a single capture fails:

- print or log an error
- skip that image
- continue the loop

If the screenshot directory does not exist:

- create it automatically

If recording exits:

- stop the screenshot worker cleanly

## Command Interface

Extend `collect_activity` with minimal screenshot options.

Recommended arguments:

- `--screenshots`
  Enables screenshot capture.
- `--screenshot-interval`
  Defaults to `5.0`.

This keeps the feature optional and avoids surprising screenshot capture unless explicitly requested.

## Module Changes

### `journal/management/commands/collect_activity.py`

Add:

- screenshot directory path helper
- screenshot capture helper
- background screenshot loop
- thread/event lifecycle handling inside `run_collector`
- command arguments for enabling screenshots and setting interval

### `journal/tests.py`

Add focused tests for:

- screenshot path generation
- loop invoking screenshot capture at the requested interval
- screenshot failures not crashing recording
- `run_collector` starting and stopping screenshot capture when enabled

The tests should stay lightweight and focus on behavior rather than thread internals.

## Acceptance Criteria

This task is done when:

- `collect_activity --screenshots` captures images while recording runs
- screenshots are saved under `base_dir/screenshots/YYYY-MM-DD/`
- default interval is 5 seconds
- screenshot capture does not depend on app switching
- screenshot failures do not crash the activity recorder
- screenshot capture stops when recording stops
- relevant `journal` tests pass

## Risks And Tradeoffs

### macOS permissions

Screenshot capture may require screen recording permission for the terminal or host process.

This is acceptable for the MVP. If permission is missing, the feature should fail visibly in logs but should not bring down the activity recorder.

### Silent but not invisible to the OS

The implementation will avoid app-level UI, but macOS may still enforce system privacy permissions. That is outside the scope of this task.

### Storage growth

Capturing every 5 seconds will create many files over time. This is acceptable for the MVP because retention and pruning are not part of this feature.

## Next Implementation Task

Implement optional background screenshot capture in `collect_activity`, then add focused tests for screenshot pathing, loop behavior, and clean shutdown.
