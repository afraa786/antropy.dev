# Importing this package triggers registration of every engine via
# `@register_scanner`. Each adapter module is imported here so the registry is
# populated as soon as the engines package is imported.
from appsec.scanner.engines import ssl_tls_engine, urlscan_engine  # noqa: F401
from appsec.scanner.engines.katana import adapter as katana_adapter  # noqa: F401
from appsec.scanner.engines.nuclei import adapter as nuclei_adapter  # noqa: F401


__all__ = [
    "katana_adapter",
    "nuclei_adapter",
    "ssl_tls_engine",
    "urlscan_engine",
]
