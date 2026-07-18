import dns.resolver


def resolve_txt_records(hostname: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(hostname, "TXT")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return []
    records: list[str] = []
    for rdata in answers:
        for txt_string in rdata.strings:  # type: ignore[attr-defined]
            records.append(txt_string.decode() if isinstance(txt_string, bytes) else txt_string)
    return records
