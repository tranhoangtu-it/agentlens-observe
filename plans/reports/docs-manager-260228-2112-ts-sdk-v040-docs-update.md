# Docs Update Report — TypeScript SDK & v0.4.0

**Date:** 2026-02-28 | **Scope:** v0.4.0 release docs sync

## Changes Made

### `docs/project-overview-pdr.md`
- Version header: 0.2.0 → 0.4.0, date updated
- Distribution: added npm entry (`agentlens-observe@0.1.0`)
- F6 SDK: added TypeScript SDK v0.1.0 bullet points (Node 18+, zero prod deps, ESM+CJS)
- F7 Testing: updated to 46 server tests + 30 TS vitest tests
- Tech Stack table: split SDK row into Python SDK / TypeScript SDK rows; added npm to Deployment
- Key Features: bumped to v0.4.0, added TS SDK + OTel ingestion + replay items
- Roadmap: checked off replay, OTel ingestion, TypeScript SDK
- Constraints: added TS SDK constraint line

### `docs/system-architecture.md`
- Version header: 0.2.0 → 0.4.0
- Architecture diagram: added TypeScript Agent box and OTel-instrumented system box alongside Python Agent
- Backend API table: added `POST /api/otel/v1/traces` row
- Added full TypeScript SDK section after Python SDK section (public API table, module descriptions, testing)
- Testing section: updated to 46 server tests, split Python/TS SDK test sections
- Future Scaling: added TypeScript SDK framework integrations item

### `docs/development-roadmap.md`
- Version header: 0.2.0 → 0.4.0
- OTel Span Ingestion: marked complete, added actual implementation details
- TypeScript SDK: marked complete, added shipped work items + npm publish note; kept future framework integrations as pending
- Success Criteria: checked off OTel + TS SDK items
- Deprecation schedule: updated from v0.2.0/v0.3.0 to v0.4.0/v0.5.0

### `docs/project-changelog.md`
- Added `[0.4.0] — 2026-02-28` section with TypeScript SDK details + Docker bump + upgrade instructions
- Added `[0.3.0] — 2026-02-28` section with Replay and OTel ingestion details
- Supported Versions table: added 0.4.0 (Current), 0.3.0 (Maintained), updated 0.2.0 to EOL
- Next Planned Release: updated to v0.5.0

## File Sizes (LOC)
| File | LOC |
|------|-----|
| project-changelog.md | 377 |
| system-architecture.md | 326 |
| development-roadmap.md | 286 |
| project-overview-pdr.md | 169 |

All under 800 LOC limit.

## Unresolved Questions
- None.
