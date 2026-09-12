#!/usr/bin/env python3
"""Dump every message in the finance folders (bodies included) to bills_raw.json.

Edit FOLDERS to match the account, or pass folder URIs as argv.
"""
import json, sys
import tbclient

FOLDERS = [
    "imap://purplepirate2004%40yahoo.com@imap.mail.yahoo.com/Finance and Bills",
    "imap://jstrickland13%40gmail.com@imap.gmail.com/Cat/Financial",
]
OUT = "bills_raw.json"


def list_messages(folder):
    r = tbclient.call_json("searchMessages", {
        "query": "", "folderPath": folder, "maxResults": 200, "sortOrder": "asc"})
    return r if isinstance(r, list) else r.get("messages", [])


def main():
    folders = sys.argv[1:] or FOLDERS
    listing = []
    for folder in folders:
        for m in list_messages(folder):
            listing.append({"id": m["id"], "folderPath": folder,
                            "subject": m.get("subject", ""),
                            "author": m.get("author", ""), "date": m.get("date", "")})
    print(f"listed {len(listing)} messages", file=sys.stderr)
    all_msgs = []
    for i in range(0, len(listing), 10):
        chunk = listing[i:i + 10]
        r = tbclient.call_json("getMessages", {
            "messages": [{"messageId": c["id"], "folderPath": c["folderPath"]}
                         for c in chunk],
            "bodyFormat": "text"}, _id=i + 1)
        all_msgs.extend(r.get("messages", []))
        print(f"  fetched {len(all_msgs)}/{len(listing)}", file=sys.stderr)
    json.dump(all_msgs, open(OUT, "w"))
    print(f"wrote {OUT} ({len(all_msgs)} messages)")


if __name__ == "__main__":
    main()
