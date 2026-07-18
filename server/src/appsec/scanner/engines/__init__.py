# Importing this package triggers registration of every engine via
# `@register_scanner`. Each adapter module is imported here so the registry is
# populated as soon as the engines package is imported.
from appsec.scanner.engines import ssl_tls_engine, urlscan_engine  # noqa: F401

__all__ = ["ssl_tls_engine", "urlscan_engine"]
