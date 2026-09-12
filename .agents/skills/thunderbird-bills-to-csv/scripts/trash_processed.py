#!/usr/bin/env python3
"""Move processed messages to Trash (grouped by folder) and verify.

Usage: trash_processed.py bills_raw.json 2 3 10 15 ...

The indexes refer to positions in bills_raw.json (1-based). Verification uses
a whole-account search because folder-scoped searches and folder counts lag
badly on IMAP; the move itself can also take ~15-30s to become visible.
"""
import json, sys, time
import tbclient

raw = sys.argv[1] if len(sys.argv) > 1 else "bills_raw.json"
idxs = [int(x) for x in sys.argv[2:]]
msgs = json.load(open(raw))

if not idxs:
    raise SystemExit("no message indexes supplied")

groups = {}
for i in idxs:
    m = msgs[i - 1]
    groups.setdefault(m["folderPath"], []).append(m["id"])

for folder, ids in groups.items():
    print(folder.split("/")[-1], tbclient.call_json(
        "updateMessage", {"messageIds": ids, "folderPath": folder, "trash": True},
        _id=len(ids)))

print("waiting 20s for IMAP indexes to settle...")
time.sleep(20)
print("--- verify ---")
for i in idxs:
    m = msgs[i - 1]
    r = tbclient.call_json("searchMessages", {
        "query": f"subject:{m['subject'][:25]}", "maxResults": 5,
        "dedupByMessageId": False}, _id=i)
    rows = r if isinstance(r, list) else r.get("messages", [])
    locs = [x.get("folderPath", "") for x in rows if x.get("id") == m["id"]]
    ok = bool(locs) and all("Trash" in l for l in locs)
    print(f"  [{i}] {'TRASH' if ok else 'STILL IN PLACE':15s} {m['subject'][:40]:40s} {locs}")
