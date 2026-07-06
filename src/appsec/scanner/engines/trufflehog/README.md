# TruffleHog Engine (placeholder)

**Category**: `secret_scan`

## Responsibility

Wrap [TruffleHog](https://github.com/trufflesecurity/trufflehog). Given a
verified `Target` (a web endpoint, and/or a repository reference passed via
`target.options`), scan for exposed secrets/credentials and surface each as
a `Finding` — severity driven by TruffleHog's own verification status
(verified secrets should map to `high`/`critical`, unverified to `medium`).

## Expected implementation

- `health_check()` — confirm the `trufflehog` binary is present and
  runnable.
- `validate(target)` — confirm the target type (git repo URL, filesystem
  path, or web endpoint) matches a TruffleHog scan mode this adapter
  supports.
- `scan(target)` — invoke the appropriate `trufflehog <mode> ... --json`
  command, parse each JSON line, and emit one `Finding` per detected
  secret. Redact the actual secret value in `Evidence.raw_data` — store only
  what's needed to locate and remediate it (file/URL, line, detector name),
  never the live credential itself.

## Explicitly out of scope here

No secret-detection rules of our own — entirely delegated to TruffleHog's
built-in detectors.

## Status

Not implemented. This folder currently contains only this README and no
adapter module.
