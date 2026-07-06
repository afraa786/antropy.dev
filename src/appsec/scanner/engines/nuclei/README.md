# Nuclei Engine (placeholder)

**Category**: `vulnerability_scan`

## Responsibility

Wrap the [Nuclei](https://github.com/projectdiscovery/nuclei) CLI. Given a
verified `Target`, run Nuclei against it with the appropriate template set
and return normalized `Finding`s — one per Nuclei match.

## Expected implementation

- `health_check()` — confirm the `nuclei` binary is on PATH and runnable
  (e.g. `nuclei -version`).
- `validate(target)` — confirm `target.hostname` is a shape Nuclei can scan
  (reachable HTTP(S) host); no network calls here, just structural checks.
- `scan(target)` — invoke `nuclei -target <hostname> -jsonl -silent`,
  capture stdout, parse each JSON line (see
  `scanner/normalizer/parser.iter_json_lines`), map Nuclei's
  `info.severity` via `scanner/normalizer/severity.normalize_severity`, and
  build one `Finding` per match with `Evidence` populated from the matched
  request/response snippet Nuclei reports.

## Explicitly out of scope here

No custom vulnerability logic, no writing/maintaining Nuclei templates as
part of this codebase — Nuclei's own template repo is the source of truth
for what counts as a finding.

## Status

Not implemented. This folder currently contains only this README and no
adapter module.
