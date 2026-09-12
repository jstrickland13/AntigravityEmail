#!/usr/bin/env python3
"""Compact per-message digest of bills_raw.json: sender, subject, $ and dates.

Prints one short block per message so an agent can classify without loading
full bodies into context. Usage: digest.py [index ...]
"""
import json, re, sys

RAW = "bills_raw.json"
MONTHS = ("january|february|march|april|may|june|july|august|september|"
          "october|november|december")
AMT = re.compile(r"\$\s?([0-9][0-9,]*(?:\.\d{2})?)")
NUMDATE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")
NAMEDATE = re.compile(rf"\b((?:{MONTHS})\.?\s+\d{{1,2}},?\s+\d{{4}})\b", re.I)
KEY = re.compile(r"\$|\bdue\b|past due|amount|balance|minimum|total|invoice|statement|payment of", re.I)


def sender(author):
    m = re.match(r'\s*"?([^"<]+?)"?\s*<', author or "")
    return (m.group(1) if m else (author or "")).strip()[:40]


def uniq(seq, cap=5):
    out = []
    for s in seq:
        if s not in out:
            out.append(s)
    return out[:cap]


def main():
    msgs = json.load(open(RAW))
    wanted = [int(x) for x in sys.argv[1:]] or range(1, len(msgs) + 1)
    for i in wanted:
        m = msgs[i - 1]
        body = m.get("body", "") or ""
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        hits = [l for l in lines if KEY.search(l)]
        amts = uniq([f"${a}" for a in AMT.findall(body)])
        dates = uniq(NUMDATE.findall(body) + NAMEDATE.findall(body), 4)
        print(f"[{i}] {sender(m.get('author',''))} | {m.get('subject','')[:70]}")
        print(f"    $: {', '.join(amts) or '-'} | dates: {', '.join(dates) or '-'}")
        for l in uniq([h for h in hits if AMT.search(h)], 3):
            print(f"    > {l[:150]}")


if __name__ == "__main__":
    main()
