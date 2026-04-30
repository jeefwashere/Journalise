# Minute Vision Summary Design

Date: 2026-04-29
Topic: Minute-level screenshot summary with local Ollama vision model
Status: Approved in chat, pending user review of written spec

## Goal

Add a minimal minute-level visual summary feature on top of the background screenshot system.

While recording is running:

- screenshots are captured every 5 seconds
- every 60 seconds, the backend collects the most recent 12 screenshots
- those 12 screenshots are sent to the local Ollama vision model
- the model returns a short JSON summary of what the screenshots show
- the result is saved locally

This should stay MVP-simple:

- local Ollama only
- local file storage only
- no database
- no frontend
- no final journal-summary integration yet

## Model Choice

Use the local Ollama model:

- `qwen2.5vl:7b`

This model is already available on the user's machine and supports image input.

## Scope

In scope:

- minute-level grouping of screenshots
- sending the most recent 12 screenshots to local Ollama
- requiring a fixed JSON response shape
- saving the minute summary locally
- minimal failure handling
- focused tests for screenshot-window selection, Ollama request flow, and JSON persistence

Out of scope:

- label extraction
- OCR-specific features
- summary-service integration
- activity/session correlation
- cloud model providers
- retry queues
- image deduplication

## Summary Window

The summary worker runs every 60 seconds.

Each run should use:

- the most recent 12 screenshots

This assumes screenshots are being captured every 5 seconds.

If fewer than 12 screenshots are available, skip the summary run.

This keeps the behavior simple and avoids partial windows for the MVP.

## Output Shape

Each minute summary should use this JSON shape:

```json
{
  "window_start": "2026-04-29T14:00:00Z",
  "window_end": "2026-04-29T14:01:00Z",
  "summary": "The user was mainly coding in VS Code and briefly viewing a browser page."
}
```

Field meanings:

- `window_start`: timestamp of the earliest screenshot in the analyzed batch
- `window_end`: timestamp of the latest screenshot in the analyzed batch
- `summary`: short natural-language description of what the screenshots show

No `labels` field is included.

## Storage Layout

Minute summaries should be stored under the collector base directory:

- `base_dir/minute_summaries/YYYY-MM-DD.json`

Each file contains a JSON array of summary objects for that day.

## Recommended Approach

Use a separate background worker for visual summaries.

This worker should:

1. wake up every 60 seconds
2. load the most recent 12 screenshot file paths
3. send them to Ollama
4. validate the JSON response
5. append the result to the day's minute-summary JSON file

This is preferred over analyzing every screenshot individually because it matches the user's minute-level requirement directly and keeps request volume low.

## Ollama Request Design

### Endpoint

Use the local Ollama HTTP API at the default base URL unless overridden:

- `http://localhost:11434/api/generate`

### Model

Use:

- `qwen2.5vl:7b`

### Prompt Contract

The prompt should instruct the model to:

- look across all provided screenshots
- summarize what the screen activity appears to be during the minute
- return valid JSON only
- use exactly these keys:
  - `window_start`
  - `window_end`
  - `summary`

The backend should supply the actual `window_start` and `window_end` values from the screenshot batch, and the model output should be validated before persistence.

## Screenshot Selection

Screenshots are already stored on disk by timestamp.

The summary worker should:

- read the screenshot directory for the current day
- sort screenshots by timestamp
- take the most recent 12 files

This is enough for the MVP.

No cross-day stitching is required in this task.

## Worker Lifecycle

The minute-summary worker should run only while recording is active.

Flow:

1. `collect_activity` starts
2. if screenshots and vision summaries are enabled, start the minute-summary worker
3. while recording runs, the worker summarizes every 60 seconds
4. when recording stops, stop the worker cleanly

The summary worker depends on screenshots being enabled.

## Error Handling

If there are fewer than 12 screenshots:

- skip the run
- do not write partial output

If the Ollama request fails:

- print or log an error
- do not crash recording
- skip that minute's summary

If the model returns invalid JSON:

- print or log an error
- skip persistence

If the day summary file is malformed:

- recover safely by treating it as an empty list

## Module Changes

### `journal/management/commands/collect_activity.py`

Add:

- screenshot-file discovery helper
- minute-summary file path helper
- Ollama vision request helper
- JSON normalization helper
- minute-summary append/load helper
- background worker for minute summaries
- command options for enabling minute summaries
- worker startup and shutdown tied to `collect_activity`

### `journal/tests.py`

Add focused tests for:

- selecting the latest 12 screenshots
- skipping summary when fewer than 12 screenshots exist
- persisting valid minute summary JSON
- skipping malformed Ollama responses
- starting and stopping the minute-summary worker when enabled

The tests should cover normal path, failure path, and storage path without becoming overly granular.

## Command Interface

Extend `collect_activity` with a minimal option:

- `--vision-summary`
  Enables minute-level screenshot analysis through Ollama.

This option should require screenshots to be enabled in practice, even if the command does not hard-fail immediately.

## Acceptance Criteria

This task is done when:

- `collect_activity` can optionally produce minute-level screenshot summaries
- each summary analyzes the most recent 12 screenshots
- the local model used is `qwen2.5vl:7b`
- output JSON contains only `window_start`, `window_end`, and `summary`
- summaries are saved under `base_dir/minute_summaries/YYYY-MM-DD.json`
- Ollama or JSON failures do not crash recording
- relevant `journal` tests pass

## Risks And Tradeoffs

### Heavy local inference

Sending 12 screenshots every minute may be somewhat heavy for local inference.

This is acceptable for the MVP because the cadence is low and the user explicitly wants minute-level summaries.

### Current-day only windowing

The MVP only analyzes screenshots from the current day directory. A minute window that crosses midnight is ignored as a special case for now.

### Model output variability

Vision models may occasionally produce malformed JSON even when asked not to.

That is acceptable as long as invalid output is rejected safely and recording continues.

## Next Implementation Task

Implement optional minute-level screenshot summarization with local Ollama, then add focused tests for screenshot selection, Ollama response handling, and clean worker lifecycle management.
