# Documentation Audit Summary

This audit summarizes the state of TimeTracker documentation as of the audit date. Use it to find accurate sources, fix outdated content, and fill gaps.

---

## Accurate (keep; minimal edits only)

| Doc | Notes |
|-----|--------|
| **README.md** | Tech stack, quick start (Docker HTTPS/HTTP/SQLite), features, doc links correct. Version: states "defined in setup.py"; avoid hardcoding version examples in What's New. |
| **INSTALLATION.md** | Matches actual flow; points to GETTING_STARTED and DOCKER_COMPOSE_SETUP. |
| **DEVELOPMENT.md** | Venv + `flask run`, `docker-compose.local-test.yml`, folder structure, test commands align with repo. |
| **ARCHITECTURE.md** | Module table, data flow, API structure match app/ (blueprint_registry, routes, services, repositories, models). |
| **API.md** (root), **docs/api/REST_API.md** | Accurate overview and auth; REST_API is full reference. |
| **docs/development/SERVICE_LAYER_AND_BASE_CRUD.md** | Accurately describes service/repository pattern and BaseCRUDService. |
| **docs/development/LOCAL_TESTING_WITH_SQLITE.md** | Correct for docker-compose.local-test.yml and scripts. |
| **docs/TESTING_QUICK_REFERENCE.md**, **docs/TESTING_COVERAGE_GUIDE.md** | Align with Makefile targets and pytest markers. |
| **docs/UI_GUIDELINES.md**, **docs/FRONTEND.md** | Match templates (base.html, components/ui.html) and Tailwind. |
| **docs/GETTING_STARTED.md** | Correct: default compose → https://localhost; documents example compose for http://localhost:8080. |
| **requirements-test.txt** | Exists; referenced by Makefile and CI. |

---

## Outdated

| Item | Location | Fix |
|------|----------|-----|
| Version numbers | README "What's New" / "Current version" | Point to setup.py + CHANGELOG only; remove or generalize hardcoded v4.14.0, v4.6.0. |
| Hardcoded version | docs/development/PROJECT_STRUCTURE.md | Replace "version='4.20.9'" with "version in setup.py (single source of truth)". |
| Hardcoded version | docs/FEATURES_COMPLETE.md | Remove "Version: 4.20.6" or replace with "See setup.py". |
| Docker access URL | docs/development/CONTRIBUTING.md | Default `docker-compose up --build` → https://localhost. For http://localhost:8080 use docker-compose.example.yml or docker-compose.local-test.yml. |
| Compose role | docs/development/PROJECT_STRUCTURE.md | Describe docker-compose.yml as "Default stack (HTTPS via nginx)"; add docker-compose.example.yml (HTTP 8080) and docker-compose.local-test.yml (SQLite). |
| Refactored modules | docs/ARCHITECTURE_AUDIT.md | Note that timer_refactored/projects_refactored/invoices_refactored are historical (merged or removed). |
| Deployment guide label | docs/guides/DEPLOYMENT_GUIDE.md | Content is feature checklist, not "how to deploy". Add note at top pointing to DOCKER_COMPOSE_SETUP and DOCKER_PUBLIC_SETUP. |

---

## Missing

| Gap | Resolution |
|-----|------------|
| Single contributor onboarding doc | **CONTRIBUTOR_GUIDE.md** — Architecture, local dev, testing, how to add route/service/repository/template, versioning. |
| Versioning for contributors | Short "For contributors" note: app version in setup.py only; desktop/mobile have own config; link BUILD.md and VERSION_MANAGEMENT. |
| Step-by-step "add route/service/repository/template" | Include in CONTRIBUTOR_GUIDE with concrete steps (files, blueprint_registry, tests). |

---

## Duplicated or Overlapping

| Area | Notes |
|------|--------|
| **Installation** | README Quick Start, INSTALLATION.md, GETTING_STARTED.md, DOCKER_COMPOSE_SETUP all cover install. Keep overlap; add one-line pointers (e.g. "For step-by-step see INSTALLATION.md", "For all env vars see DOCKER_COMPOSE_SETUP"). |
| **Contributing** | Root CONTRIBUTING.md points to docs/development/CONTRIBUTING.md; fix Docker URL in full CONTRIBUTING. |
| **Deployment** | README, INSTALLATION, DOCKER_COMPOSE_SETUP, DOCKER_PUBLIC_SETUP, guides/DEPLOYMENT_GUIDE. Clarify DEPLOYMENT_GUIDE as feature checklist; "how to deploy" = DOCKER_COMPOSE_SETUP / DOCKER_PUBLIC_SETUP. |

---

## Contradictions

| Issue | Resolution |
|-------|------------|
| **Docker URL** | CONTRIBUTING (full) said http://localhost:8080 after default `docker-compose up --build`. Default compose serves **HTTPS** (https://localhost). Fix: document default = https://localhost; for 8080 use docker-compose.example.yml or docker-compose.local-test.yml. |
| **Compose purpose** | PROJECT_STRUCTURE said "Local development compose" for docker-compose.yml; README uses it for quick start and production. Unify: default = full stack HTTPS; development options = example (HTTP) or local-test (SQLite). |

---

## File reference

- **Audit doc**: this file — `docs/DOCS_AUDIT.md`
- **Updates**: README.md, docs/development/CONTRIBUTING.md, docs/development/PROJECT_STRUCTURE.md, docs/FEATURES_COMPLETE.md, docs/ARCHITECTURE_AUDIT.md, docs/README.md, docs/guides/DEPLOYMENT_GUIDE.md
- **New**: docs/development/CONTRIBUTOR_GUIDE.md
- **Cross-links**: CONTRIBUTING.md (root), docs/README.md, DEVELOPMENT.md
