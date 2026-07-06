# Scanner Engines

Each subfolder here is a self-contained scanner plugin: one external tool
wrapped in a class implementing `appsec.scanner.interfaces.scanner.Scanner`.

## Rules for adding an engine

1. Create `scanner/engines/<name>/adapter.py` implementing `Scanner`:
   `name`, `category`, `async validate()`, `async health_check()`, `async scan()`.
2. `scan()` must only invoke the underlying CLI/binary/API and parse its
   output into `ScanResult`/`Finding` (see `scanner/interfaces/models.py`).
   No vulnerability detection logic belongs here — that's the tool's job.
3. Decorate the class with `@register_scanner` from
   `scanner/interfaces/registry.py`.
4. Import the adapter module somewhere it gets loaded at startup (e.g. a
   `scanner/engines/__init__.py` import list) so registration runs.
5. Do not import the adapter from `api/`, `application/`, or
   `infrastructure/` — only the orchestrator (via the registry) should ever
   resolve an engine by name.

## Why this structure

The backend (API, Celery task, scan_jobs service) calls
`scanner.orchestrator.run_scan()` and nothing else. It has no import of any
engine module, so engines can be built, replaced, or removed independently
without touching backend code — only the registry needs the new module
imported.
