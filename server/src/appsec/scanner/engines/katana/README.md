# Katana Engine (placeholder)

**Category**: `web_crawl`

## Responsibility

Wrap the [Katana](https://github.com/projectdiscovery/katana) crawler.
Given a verified `Target`, crawl the site and surface discovered
endpoints/URLs as `Finding`s (severity `info`) that other engines (e.g.
Nuclei) or the platform can later act on.

## Expected implementation

- `health_check()` — confirm the `katana` binary is present and runnable.
- `validate(target)` — confirm `target.hostname` looks like a crawlable
  HTTP(S) host.
- `scan(target)` — invoke `katana -u <hostname> -jsonl`, parse each JSON
  line via `scanner/normalizer/parser.iter_json_lines`, and emit one
  `info`-severity `Finding` per discovered endpoint, with the URL in
  `matched_at` and crawl metadata (status code, content-type, etc.) in
  `Finding.metadata`.

## Explicitly out of scope here

No link-following policy decisions or scope logic beyond what Katana itself
supports via its own CLI flags — this adapter only shells out and parses.

## Status

Not implemented. This folder currently contains only this README and no
adapter module.
