# Naabu Engine (placeholder)

**Category**: `port_scan`

## Responsibility

Wrap the [Naabu](https://github.com/projectdiscovery/naabu) port scanner.
Given a verified `Target`, identify open TCP/UDP ports and surface each as
an `info`-severity `Finding`, typically feeding into `httpx`/`nuclei` for
further probing of discovered services.

## Expected implementation

- `health_check()` — confirm the `naabu` binary is present, runnable, and
  that any required raw-socket privileges are available in the execution
  environment.
- `validate(target)` — confirm `target.hostname` resolves to a scannable
  host; respect any configured port-range limits in `target.options`.
- `scan(target)` — invoke `naabu -host <hostname> -json -silent`, parse the
  JSON output, and emit one `Finding` per open port with the port number in
  `matched_at` and service/protocol info in `Finding.metadata`.

## Explicitly out of scope here

No aggressive/stealth scan-mode policy decisions beyond Naabu's own CLI
flags — this is CLI-invocation-and-parse only, same as every other adapter.

## Status

Not implemented. This folder currently contains only this README and no
adapter module.
