# Subfinder Engine (placeholder)

**Category**: `subdomain_enum`

## Responsibility

Wrap the [Subfinder](https://github.com/projectdiscovery/subfinder) tool.
Given a verified apex `Target`, enumerate subdomains and surface each as an
`info`-severity `Finding` — the platform's basis for expanding a single
verified domain into its full attack surface before other engines run.

## Expected implementation

- `health_check()` — confirm the `subfinder` binary is present and runnable.
- `validate(target)` — confirm `target.hostname` is an apex/registrable
  domain (not e.g. an IP) Subfinder can enumerate against.
- `scan(target)` — invoke `subfinder -d <hostname> -json -silent`, parse
  each JSON line, and emit one `Finding` per discovered subdomain with the
  subdomain in `matched_at`.

## Important constraint

Only subdomains of a domain the organization has already verified ownership
of should ever be scanned further — discovered subdomains from this engine
must still pass through the same ownership-verification gate before any
follow-on scan (Nuclei, Katana, etc.) targets them. That gating logic lives
in the application layer (`scan_jobs` service), not here.

## Status

Not implemented. This folder currently contains only this README and no
adapter module.
