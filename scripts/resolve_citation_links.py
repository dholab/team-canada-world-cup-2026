#!/usr/bin/env python3
"""Resolve every reference to a link that actually works, and cache the result.

Why this exists: inline citations link to the DOI, which is normally the right
target. But a DOI only guarantees that the *registration* resolves, not that the
publisher's page still exists. Reference 36 (Emerg Infect Dis) is the live
example: its DOI returns HTTP 200 and lands on the publisher's own 404 page, so
a status-code check alone does not catch it.

So this script checks each DOI's landing page for real content and, where the
DOI is dead, falls back to the PubMed record — which is stable, always
resolvable, and gets the reader to the abstract and the publisher's current
link.

The result is written to `_citation_links.json`, which is committed and read by
scripts/fetch_prose.py. The network work happens here, deliberately, so the
manuscript build stays offline-safe and reproducible: CI never depends on
publisher sites being reachable.

    python scripts/resolve_citation_links.py           # refresh the cache
    python scripts/resolve_citation_links.py --check   # report only, no write

Re-run it when references are added or changed in the Doc.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fetch_prose as fp  # noqa: E402  (same directory, stdlib-only)

OUT = HERE.parent / "_citation_links.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; team-canada-manuscript/1.0)"}
# Two bibliography styles have to be understood. The original Doc wrote
# "doi: 10.1136/bjsports-2019-101040"; after the bibliography was reformatted
# for submission, Paperpile writes "Available from: http://dx.doi.org/10.1136/..."
# instead. Match the bare "doi:" form and the dx.doi.org/doi.org URL form, or
# every reference silently loses its DOI and the run aborts with "No link at
# all".
DOI_RE = re.compile(
    r"(?:doi:\s*|https?://(?:dx\.)?doi\.org/)(10\.\d{4,9}/\S+)", re.I)

# Phrases that mean the publisher served an error page under a 200 status.
DEAD_MARKERS = ("page not found", "404 not found", "article not found",
                "the page you requested", "cannot be found")


def doi_of(text: str) -> str | None:
    m = DOI_RE.search(text)
    return m.group(1).rstrip(".,;)]") if m else None


def doi_is_live(doi: str) -> bool:
    """True if the DOI lands on a real article page.

    A 403 counts as live: many publishers block scripted requests outright, and
    that says nothing about whether the article exists. Only an explicit 404, or
    a 200 whose body or final URL is an error page, counts as dead."""
    url = "https://doi.org/" + doi
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            final = resp.geturl().lower()
            if "/404" in final or "error" in final.split("?")[0]:
                return False
            body = resp.read(6000).decode("utf-8", "replace").lower()
            return not any(m in body for m in DEAD_MARKERS)
    except urllib.error.HTTPError as e:
        return e.code != 404          # 403/401/429 -> blocked, not dead
    except Exception:
        return True                   # network hiccup: keep the DOI


def pmid_for(doi: str) -> str | None:
    """Look up a DOI's PubMed ID."""
    q = urllib.parse.quote(f'"{doi}"[AID] OR "{doi}"[DOI]')
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
           f"?db=pubmed&retmode=json&term={q}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=30) as resp:
            ids = json.load(resp)["esearchresult"].get("idlist", [])
            return ids[0] if ids else None
    except Exception:
        return None


def resolve(entry: tuple[int, str]) -> tuple[int, str, str]:
    """Return (number, url, how) for one reference."""
    num, text = entry
    doi = doi_of(text)
    if not doi:
        m = fp.REF_URL.search(text)
        return num, (m.group(1).rstrip(".,;)]") if m else ""), "url"
    if doi_is_live(doi):
        return num, "https://doi.org/" + doi, "doi"
    pmid = pmid_for(doi)
    if pmid:
        return num, f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "pubmed"
    return num, "https://doi.org/" + doi, "doi-dead-no-pmid"


def main() -> None:
    check_only = "--check" in sys.argv
    raw = fp.fetch(None)
    refs = fp.extract_references(raw)

    with ThreadPoolExecutor(8) as pool:
        results = sorted(pool.map(resolve, refs))

    links = {str(n): u for n, u, _ in results if u}
    by_how: dict[str, list[int]] = {}
    for n, _, how in results:
        by_how.setdefault(how, []).append(n)

    for how in sorted(by_how):
        nums = by_how[how]
        print(f"{how:18} {len(nums):3}  {nums if how != 'doi' else ''}")

    missing = [n for n, u, _ in results if not u]

    if check_only:
        if missing:
            print(f"\nNo link at all for references: {missing}")
        print("\n--check: nothing written.")
        return

    # A reference with no resolvable link used to abort the run before the
    # write, which meant one unlinkable entry silently left the whole cache
    # stale — and a stale cache keyed by the OLD numbering mislabels every
    # citation after the point where the bibliography changed. Write what did
    # resolve, and report the rest loudly instead.
    if missing:
        print(f"\nWARNING - no link resolved for references: {missing}")
        print("  Their citations will fall back to the DOI derived at build "
              "time. Check these entries in the Doc.")

    OUT.write_text(json.dumps(links, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT} ({len(links)} links)")


if __name__ == "__main__":
    main()
