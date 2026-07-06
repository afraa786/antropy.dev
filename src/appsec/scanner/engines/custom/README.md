# Custom Engines

Home for in-house or third-party scanner adapters that don't fit one of the
named ProjectDiscovery/TruffleHog folders above — e.g. a proprietary check,
a wrapped internal tool, or a scanner added later without renaming this
directory.

## Responsibility

Same contract as every other engine: implement
`appsec.scanner.interfaces.scanner.Scanner`, register via
`@register_scanner`, and do only CLI/API invocation + output normalization
— no bespoke vulnerability logic beyond what the wrapped tool itself
determines, unless the "tool" being wrapped is itself the custom detection
logic being intentionally built here (in which case that logic lives inside
the adapter's `scan()`, still returning the common `ScanResult`/`Finding`
shape).

## Structure convention

Each custom engine should get its own subfolder here, e.g.
`scanner/engines/custom/<engine_name>/adapter.py`, mirroring the top-level
engine folders.

## Status

Not implemented. This folder currently contains only this README and no
adapter modules.
