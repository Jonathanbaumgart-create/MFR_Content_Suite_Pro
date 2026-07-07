# AGENTS.md

Engineering instructions for future Codex sessions working on MFR Content Suite Pro.

## Project Vision

MFR Content Suite Pro is a commercial AI-powered Digital Asset Management and communications platform for fire departments and emergency services.

The application is intended to manage very large photo and video libraries, analyze media with interchangeable AI providers, convert analysis into structured fire-service intelligence, and later support communications workflows such as archives, campaigns, calendars, recommendations, and generated content.

## Core Architecture

Current system flow:

```text
Scanner -> SQLite -> Gallery -> Viewer -> AI Brain -> Media Intelligence -> Future Content Generator
```

Preserve this architecture unless the user explicitly requests an architectural redesign.

## Current Major Systems

- Scanner and scan reporting
- SQLite persistence
- Gallery and async thumbnail loading
- Photo Viewer
- AI Brain
- Job Manager
- Provider abstraction
- Mock provider
- Ollama provider
- Media Intelligence Engine
- AI Dashboard
- Structured logging
- Smoke tests

## Mandatory Development Rules

- Never redesign the app unless explicitly asked.
- Always evolve the existing codebase.
- GUI must remain thin.
- No AI logic in GUI.
- No AI logic in database layer.
- All long-running work must run in background jobs.
- UI must never freeze.
- Design for 100,000+ media files.
- Preserve existing module names unless instructed.
- One responsibility per class where practical.
- Keep providers interchangeable.
- Never let mock provider overwrite real provider analysis.
- Never save failed provider output as successful analysis.
- Do not remove scanner reporting or deduplication.

## Threading Rules

- Tkinter updates must happen on the main thread.
- Background workers may not directly update widgets.
- Long-running scanner, thumbnail, AI, and rebuild work must be backgrounded.
- Queue work must be bounded for large libraries.
- Use `after(...)` or an equivalent main-thread handoff for GUI updates.
- Avoid creating one future or thread per media item for large operations.

## Database Rules

- SQLite is the persistence layer.
- Use JSON serialization for structured list fields.
- Use indexes for large-library queries.
- Preserve migration safety.
- Do not put business logic or AI interpretation in `DatabaseManager`.
- Avoid unbounded `OFFSET` patterns where practical.
- Keep database methods focused on persistence, retrieval, and schema compatibility.
- Do not hide skipped, failed, duplicate, or unsupported media cases.

## AI Rules

- `BrainService` is the AI orchestration layer.
- `VisionService` owns provider selection and provider abstraction.
- `AIService` handles parsing/normalization only.
- `MediaIntelligenceService` converts saved analysis into structured intelligence.
- Mock provider is test data only.
- Ollama provider is for real local analysis.
- Provider failures must be logged and visible.
- Existing good analysis must not be overwritten by failed analysis.
- Existing real provider analysis must not be overwritten by mock analysis.
- Do not rerun the vision model to build Media Intelligence from already saved analysis.

## Performance Rules

- Gallery must use paging.
- Thumbnails must load asynchronously.
- Bulk AI analysis must be bounded/batched.
- Scanner must reconcile discovered, supported, duplicate, skipped, failed, and inserted files.
- Large libraries must remain responsive.
- Avoid full-library in-memory lists when a paged or streamed approach is practical.
- Avoid synchronous image decoding in GUI construction paths.

## Testing Expectations

Before reporting completion, run the relevant verification for the work performed.

Default completion checks:

- Full compile check.
- `git diff --check`.
- Scanner smoke test.
- Media intelligence smoke test.
- Gallery responsiveness smoke test when gallery code changes.
- App launch smoke test.

If a check cannot be run, clearly state why and what residual risk remains.

## Git Workflow

- Use clear commits per sprint or bug fix.
- Do not mix unrelated feature work.
- Summarize modified files after each task.
- Keep main stable.
- Do not revert user changes unless explicitly instructed.
- Do not include generated logs, thumbnails, databases, or local artifacts in commits unless explicitly requested.

## Roadmap Context

Upcoming modules:

- Intelligence Explorer
- Semantic Search
- Recommendation Engine
- Facebook Archive
- Instagram Archive
- Campaign Builder
- Content Calendar
- Learning Engine

Treat these as roadmap context only. Do not build them while working on regressions or hardening unless the user explicitly asks.

## Things Not To Do

- Do not add AI calls directly in GUI.
- Do not block UI while loading images.
- Do not enqueue 100,000 futures at once.
- Do not rely on mock output as real analysis.
- Do not silently skip media files.
- Do not open reports externally if it steals focus.
- Do not start new features while fixing regressions.
- Do not remove pagination from the Gallery.
- Do not remove scanner deduplication or skip reporting.
- Do not weaken provider failure handling to make tests pass.

## Current Engineering Posture

The application is being evolved sprint by sprint toward commercial release. Favor small, safe, well-verified changes over broad rewrites. When a module needs cleanup, preserve its public behavior first, add tests or smoke checks where practical, and only then simplify internals.
