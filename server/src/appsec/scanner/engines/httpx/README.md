# httpx (ProjectDiscovery) Engine (placeholder)

**Category**: `http_probe`

Note: this refers to the ProjectDiscovery `httpx` CLI probe tool, unrelated
to the Python `httpx` HTTP client library already used elsewhere in this
codebase (e.g. `infrastructure/tasks/domain_verification.py`).

## Responsibility

Wrap the [httpx](https://github.com/projectdiscovery/httpx) probing tool.
Given a verified `Target`, determine live HTTP(S) endpoints, status codes,
titles, tech stack fingerprints, and TLS details, surfaced as `info`-severity
`Finding`s that describe the target's HTTP surface.

## Expected implementation

- `health_check()` — confirm the `httpx` binary is present and runnable
  (careful: must resolve to the Go binary, not the Python package, in PATH).
- `validate(target)` — confirm `target.hostname` is a probeable host.
- `scan(target)` — invoke `httpx -u <hostname> -json -silent`, parse the
  JSON output, and emit `Finding`s carrying status code, title, and
  detected technologies in `Finding.metadata`.

## Explicitly out of scope here

No fingerprint database logic — rely entirely on httpx's own
`-tech-detect` output.

## Status

Not implemented. This folder currently contains only this README and no
adapter module.
