#!/usr/bin/env python3
"""Append bills from a JSON list into the Bills.csv tracker, skipping duplicates.

Usage: append_bills.py bills_new.json [csv_path]

bills_new.json is a list of objects:
  {"payee": str, "amount": str|number, "duedate": "M/D/YYYY"|"",
   "frequency": "Monthly|Weekly|Annually|OneTime|...", "category": str,
   "autopay": 0|1, "accountid": ""}

Dedup key = (normalised payee, amount, normalised due date): the tracker
itself lists the same payee at the same amount under two dates, so the date is
part of a bill's identity. The run is idempotent.
"""
import csv, datetime, json, os, re, shutil, sys

CSV_PATH = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/Documents/Bills.csv")
HEADER = ["Id", "Payee", "Amount", "DueDate", "Frequency", "Category",
          "IsAutoPay", "IsActive", "AccountId", "CreatedAt"]


def norm_payee(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def norm_amount(s):
    s = str(s or "").strip()
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return s


def norm_date(s):
    s = (s or "").strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if not m:
        return s.lower()
    mo, d, y = m.groups()
    return f"{int(mo)}/{int(d)}/{('20' + y) if len(y) == 2 else y}"


def key(payee, amount, duedate):
    return (norm_payee(payee), norm_amount(amount), norm_date(duedate))


def main():
    new = json.load(open(sys.argv[1]))
    rows = list(csv.reader(open(CSV_PATH, newline="")))
    if not rows or rows[0][:len(HEADER)] != HEADER:
        raise SystemExit(f"unexpected header: {rows[0] if rows else None}")

    seen = {key(r[1], r[2], r[3]) for r in rows[1:] if len(r) > 3}
    ids = [int(r[0]) for r in rows[1:] if r and r[0].strip().isdigit()]
    next_id = (max(ids) + 1) if ids else 1
    _n = datetime.datetime.now()
    now = f"{_n.month}/{_n.day}/{_n.year} {_n.hour}:{_n.minute:02d}"

    added, skipped = [], []
    for b in new:
        k = key(b["payee"], b.get("amount", ""), b.get("duedate", ""))
        if k in seen:
            skipped.append(b)
            continue
        seen.add(k)
        rows.append([str(next_id), b["payee"], str(b.get("amount", "")),
                     b.get("duedate", ""), b.get("frequency", ""),
                     b.get("category", ""), str(b.get("autopay", 0)), "1",
                     b.get("accountid", ""), now])
        added.append(rows[-1])
        next_id += 1

    if added:
        shutil.copy2(CSV_PATH, CSV_PATH + ".bak")
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f, lineterminator="\r\n").writerows(rows)

    print(f"added {len(added)}, skipped {len(skipped)} duplicates, "
          f"{len(rows) - 1} rows total")
    for r in added:
        print("  + " + ",".join(r[:4]))


if __name__ == "__main__":
    main()
