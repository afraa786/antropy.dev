# Importing this package triggers registration of every engine via
# `@register_scanner`. Each adapter module is imported here so the registry is
# populated as soon as the engines package is imported.
from appsec.scanner.engines import ssl_tls_engine, urlscan_engine  # noqa: F401

from .katana.adapter import adapter as _katana_adapter
from .nuclei.adapter import adapter as _nuclei_adapter

__all__ = ["_katana_adapter", "_nuclei_adapter"]
