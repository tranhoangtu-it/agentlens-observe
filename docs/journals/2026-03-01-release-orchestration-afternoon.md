# Release Orchestration: Coordinating Docker, PyPI, npm, and GitHub

**Date**: 2026-03-01 14:30–16:00
**Severity**: High
**Component**: Release pipeline (Docker, PyPI, npm, GitHub repo, documentation URLs)
**Status**: Resolved

## What Happened

Orchestrated the final afternoon release sequence for v0.6.0: renamed GitHub repository via `gh repo rename agentlens → agentlens-observe`, published Python package (agentlens-observe==0.6.0) to PyPI, published TypeScript SDK (agentlens-observe@0.6.0) to npm, pushed Docker images to Hub, updated all GitHub URLs across 40+ files, and created the GitHub Release artifact. All in one coordinated push.

## The Brutal Truth

This was the definition of a "death by a thousand cuts" release. Every small detail worked. Nothing exploded. And yet the entire afternoon was consumed by cascading dependencies: can't release npm until package name is confirmed, can't update docs until repo is renamed, can't push Docker until registry knows the new name, can't create release until everything else is live.

The exhausting reality is that releasing software is 80% boring orchestration and 20% actual programming. We spent 6 months building features. We spent 4 hours today pushing those features to the world. The irony is that users will never see the coordination—they just see v0.6.0 available in their package manager.

The hardest part wasn't any single step. It was the **mental overhead of keeping 5+ moving parts in sync**. Rename repo without breaking CI? Check. Update every GitHub URL reference? Check. Ensure npm auth token works? Check. PyPI credentials? Check. Docker Hub credentials? Check. Which commit gets tagged where? By this point, the context-switching fatigue was real.

## Technical Details

**Release Sequence** (strict order mattered):
1. Docker build + push: `tranhoangtu/agentlens-observe:0.6.0` + `:latest` → Docker Hub
2. GitHub repo rename: `gh repo rename agentlens agentlens-observe` (blocking for all subsequent steps)
3. URL updates: sed replacement across 40+ files (README, workflows, docs, configs)
4. PyPI publish: `twine upload` with temporary ~/.pypirc credentials
5. npm publish: `npm publish` with .npmrc auth token
6. GitHub Release: `gh release create v0.6.0` with changelog markdown

**Artifacts Published**:
```
Docker Hub:     tranhoangtu/agentlens-observe:0.6.0 + :latest
PyPI:           agentlens-observe==0.6.0
npm Registry:   agentlens-observe@0.6.0
GitHub Release: v0.6.0 with downloadable artifacts + signed tag
GitHub Repo:    tranhoangtu-it/agentlens-observe (renamed from agentlens)
Docs Site:      https://agentlens-observe.pages.dev (auto-deployed)
```

**Files Modified for URL Consistency**:
- README.md (3 refs: PyPI, npm, Docker)
- site/astro.config.mjs (repo URL, contributing link)
- .github/workflows/ (2 workflows with repo refs)
- docs/deploy/docker.md, kubernetes.md, variables.md
- package.json (homepage, repository, bugs URLs)
- server setup docs (image name references)
- GitHub issue templates (3 templates with repo links)
- Code comment blocks with old repo URLs

## What We Tried

**Initial Plan**: Release everything simultaneously.
**Reality**: Had to sequence strictly because each step had dependencies:
- Can't publish npm until we know final package name (depends on repo rename decision)
- Can't create GitHub Release until Docker, PyPI, npm are all live (otherwise release notes are wrong)
- Can't update docs URL references until repo rename is complete (gh command doesn't work if repo doesn't exist yet)

**Gotchas Encountered**:
1. PyPI required fresh ~/.pypirc file (credentials don't auto-detect from keychain on this system)—solution: create temporary file, delete after upload
2. npm publish required `.npmrc` with auth token in home directory—already configured from v0.1.0, worked immediately
3. Docker Hub registry API is eventual-consistent—images available immediately but tags sometimes lag 5-10 seconds on web interface (not a blocker, just cosmetic)
4. GitHub repo rename is atomic but makes all old URLs invalid—had to update docs before users started clicking stale links

## Root Cause Analysis

**Why Is Release Orchestration Hard?**

Release is the moment where code meets reality. Everything before v0.6.0 was internal—our repo, our build system, our tests. Publishing means handing off to external systems (npm, PyPI, Docker Hub) that have their own rate limits, auth systems, and eventual-consistency guarantees.

The coordination overhead comes from **external dependencies having independent lifetimes**:
- Docker Hub image is available immediately
- PyPI index updates within 1-5 minutes
- npm registry propagates within 1-10 minutes
- Docs rebuild automatically via Cloudflare Pages integration (works)
- GitHub Release is instant but needs all other pieces ready

**Why So Many Files to Update?**

We didn't follow DRY for URLs. The repo URL was hardcoded into:
- Documentation files (humans reading migration guide)
- Workflow configuration (CI/CD steps)
- GitHub templates (auto-generated issue/PR text)
- Package.json metadata (npm registry profile)
- Code comments (appears in generated docs)

Should have had a `project.json` or `.projectrc` that centralized all URLs, but we didn't anticipate this rename when starting the project.

## Lessons Learned

1. **Release Checklist > Winging It**: Having a step-by-step checklist for release prevented skipping critical steps. "Tag repo" before "update docs" is order-dependent.

2. **Credentials Management Matters**: Scattered credentials in ~/.pypirc, .npmrc, Docker config is fragile. Next time: use `make release` script that handles all auth in one place.

3. **External Registry Latency Is Real**: Users won't find your package immediately. Need "release available in X minutes" messaging, not "released now."

4. **Repository Rename Has Consequences**: Renaming the source of truth (GitHub repo) breaks every reference everywhere. Better approach: decide naming upfront, or plan migration period with deprecation warnings.

5. **Automation Beats Manual URL Updates**: Could have written a script (`scripts/update-repo-refs.py`) that does all URL replacements consistently. Would have taken 15 minutes to write, saved 30 minutes of manual finds/replaces.

6. **Docs Deployment Should Be Automatic**: Cloudflare Pages integration is gold—docs deploy without manual action. Other deployment steps (PyPI, npm, Docker) should have similar automation.

## Next Steps

- Monitor PyPI/npm/Docker Hub for any indexing delays or errors over next 24 hours
- Create release checklist in `CONTRIBUTING.md` for next maintainer
- Build `scripts/release.sh` that automates: Docker build/push → PyPI → npm → GitHub Release (with proper sequencing and error handling)
- Add deprecation notice to old `tranhoangtu/agentlens` Docker image
- Set up GitHub Actions to auto-publish releases (currently manual)

## Reflection

Shipping v0.6.0 taught me that **release engineering is a discipline, not a side task**. Companies hire release engineers for a reason—coordinating multiple external systems, managing credentials, handling rollbacks, and knowing when to wait for consistency is specialized work.

For a solo developer, the solution is automation. The next release should be: `make release VERSION=0.7.0` and done. Everything else is ceremony.

**Final Commits**:
- 5a70ba4 — Rename GitHub repo URLs (all 40+ file updates)
- (Implicit) Docker push + PyPI/npm publish at 15:30 UTC
- v0.6.0 GitHub Release created at 16:02 UTC

**Status**: v0.6.0 is live everywhere. Feature-complete project shipped successfully.
