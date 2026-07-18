"""Generic helpers for engine adapters parsing CLI output. Contains no
tool-specific parsing logic — each adapter is responsible for turning its own
tool's output (JSON lines, JSON array, etc.) into `Finding` objects; this
module only offers shared plumbing so adapters don't duplicate it.
"""

import json
from collections.abc import Iterator
from typing import Any


def iter_json_lines(raw_output: str) -> Iterator[dict[str, Any]]:
    """Yields one dict per non-empty line of JSONL output, skipping lines
    that fail to parse (many CLI tools emit stray log lines interleaved with
    JSON results on stdout).
    """
    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def parse_json_array(raw_output: str) -> list[dict[str, Any]]:
    """Parses a single JSON array document. Returns an empty list if the
    output is empty or malformed rather than raising — a malformed scan
    output should surface as zero findings, not a pipeline crash.
    """
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []
