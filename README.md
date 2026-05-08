# SyncGuard v2.0

SyncGuard detects implicit invariant drift in codebases shared by multiple agents, humans, services, APIs, databases, and environments. It extracts undocumented rules from source code, checks diffs against those rules, estimates impact, tracks accumulated debt, generates fixes for common drift, and reports ownership impact.

## Quick start

```bash
pip install -e .
syncguard init
syncguard extract
syncguard check
syncguard demo
```

## What it detects

- Data shape conventions such as API responses returning `data`, `meta`, and `links`.
- Type contracts such as `user_id` being consistently represented as `str`.
- Behavioral contracts such as migration files defining both `up()` and `down()`.
- Cross-module assumptions, including consumers expecting a field type provided by producers.
- Naming, file, import, and call conventions.
- Schema evolution that removes fields, changes field types, or adds required fields.
- REST/gRPC API contract drift in response shapes, error formats, and auth requirements.
- Cross-service producer/consumer mismatches.
- Database schema drift against application column assumptions.
- Configuration drift across production, staging, and development.
- Semantic versioning violations for breaking and additive contract changes.
- Breaking changes before merge for known downstream consumers.
- Invariants inferred from tests.
- Dollar-denominated drift debt and team-level drift reports.
- Invariant graph visualization as Graphviz DOT.

## CLI

```bash
syncguard init
syncguard extract --path .
syncguard check --staged
syncguard check --diff changes.diff
syncguard debt
syncguard patterns --type data_shape
syncguard fix --id <drift_id>
syncguard ledger
syncguard predict
syncguard team-report
syncguard graph
syncguard serve --port 8000
syncguard demo
```

## API

- `POST /extract`
- `GET /invariants`
- `POST /check`
- `GET /drifts`
- `GET /debt`
- `GET /predict`
- `GET /health`

SyncGuard is deterministic and does not require ML. Every invariant includes concrete evidence and every drift incident includes a diff excerpt and suggested fix.

## v2 Modules

The v2 production-grade analyzers live under `syncguard.v2` and can be used directly:

- `SchemaEvolutionTracker`
- `APIContractMonitor`
- `CrossServiceInvariantDetector`
- `DatabaseSchemaDriftMonitor`
- `ConfigurationDriftTracker`
- `SemVerEnforcer`
- `BreakingChangeDetector`
- `TestInvariantMiner`
- `DebtQuantifier`
- `AutoFixGenerator`
- `TeamDriftReporter`
- `InvariantGraphVisualizer`
