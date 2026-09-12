---
name: thunderbird-bills-to-csv
description: "Extract bills from Thunderbird finance folders into a CSV."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [email, thunderbird, bills, csv, finance, automation]
    related_skills: [thunderbird-mcp, thunderbird-inbox-categorization]
---

# Thunderbird Bills to CSV

Extract bill records from the user's Thunderbird *finance* folders and append them to a bills tracker CSV (`~/Documents/Bills.csv`) without creating duplicates, then move each email that produced a row to Trash.

## When to Use

- "Extract bills from my finance folders", "add my new bills to Bills.csv", "log these bills".
- Any recurring pass over a finance/billing mail folder that ends in a CSV row plus mail cleanup.
- Not for: triaging an inbox, or composing replies (use `thunderbird-mcp` / `email-inbox-triage`).

## Token-Efficiency Rule (the core trick)

**Never read message bodies through the MCP tools** — every body lands in context and 50+ emails will blow the budget. The `mcp-bridge.cjs` is only a stdio→HTTP shim: the extension's real API is JSON-RPC over `POST http://127.0.0.1:<port>/` with `Authorization: Bearer <token>`, both read from `/tmp/thunderbird-mcp/connection.json`.

Call that endpoint directly from a script (`scripts/tbclient.py`) so bodies stay on disk. Then surface only a **compact digest** (sender, subject, `$` amounts, dates, one or two key lines) into context, and let code do all fetching, parsing, writing and verification. Never print the token.

## Procedure

1. **Locate folders.** `listFolders` (`format: 'table'`). Finance folders are named things like `Finance and Bills` / `Category/Financial` — confirm the exact `folderPath` URIs; do not guess.
2. **Fetch to disk.** `scripts/fetch_finance_mail.py` writes every message (body included) to `bills_raw.json`. Completion: message count equals the folders' counts.
3. **Digest.** `scripts/digest.py` prints one compact block per message (sender, subject, `$` amounts, dates, key lines). **Read the schema and existing rows first** (`read_file` on the CSV) so new rows match the file's conventions.
4. **Classify in your head, not in the file.** For each message decide: *bill* (a demand/reminder to pay) vs *notice / receipt / marketing / balance summary*. Rules that held up:
   - Include only rows with a **stated amount**. Past-due notices that never state a number are real bills but logging them as `0` fabricates data — report them to the user instead.
   - Exclude: statement-generated notices, "payment status changed", balance summaries, receipts for already-paid purchases, transaction/spend alerts, credit-limit alerts, promotional offers, newsletters.
   - Same vendor + different amount/date = **separate rows**, not a duplicate (the tracker already lists Capital One at $67 twice).
5. **Append with dedup.** `scripts/append_bills.py <bills.json>` — dedup key is `(normalised payee, amount, normalised due date)`. Idempotent: re-running adds nothing. Backs up to `Bills.csv.bak` first.
6. **Trash the processed mail.** `scripts/trash_processed.py bills_raw.json <indexes...>` sends every message that produced a row to Trash, grouped by `folderPath`.
7. **Verify both.** Re-read the CSV (row count, field count per row, header unchanged, CRLF preserved) and re-search the mail **whole-account** to confirm the messages now live in Trash.

## CSV Conventions (match the existing file)

Header: `Id,Payee,Amount,DueDate,Frequency,Category,IsAutoPay,IsActive,AccountId,CreatedAt`

- **CRLF line endings**, trailing newline. Write with `csv.writer(f, lineterminator='\r\n')` and open with `newline=''`.
- **Id** = `max(existing ids) + 1`; ids are sparse, never re-sequence them.
- **Amount** = minimal decimals (`237`, `214.5`, `435.9`), no currency symbol.
- **DueDate** = `M/D/YYYY` with no leading zeros (`9/22/2026`); leave blank when the mail states none.
- **Category** = reuse the existing vocabulary (`Credit Card`, `Loan`, `Utilities`, `Medical`, `Misc`, `Subscriptions`, `Collections`, `Uncategorized`); only invent one when nothing fits.
- **IsAutoPay** = `1` when the mail says the money will be withdrawn/charged automatically.
- **AccountId** usually blank. **CreatedAt** = the run's local time, `M/D/YYYY H:MM`.
- Payees containing commas (`Velocity Investments, LLC`) are quoted by the csv module — never hand-join with commas.

## Trashing Processed Mail

- Move per `folderPath` with `updateMessage({messageIds, folderPath, trash: true})` — one call per folder, not per message.
- Trash URIs are account-specific: Yahoo `.../Trash`, Gmail `.../[Gmail]/Trash`.
- **Trash only mail that produced a row.** Marketing/notice mail is left alone unless the user says otherwise.

## Pitfalls

- **`updateMessage` returns `success: true` and the message has not moved yet.** IMAP indexes lag; a whole-account `searchMessages` immediately after the move still shows the old folder. Wait ~15–30s and re-check before believing the move failed or repeating it. The real signal is the destination Trash folder count rising (Yahoo Trash +4, Gmail Trash +4 in the reference run).
- **Folder-scoped searches and `listFolders` counts lag worst.** Verify with a whole-account `searchMessages` scoped by a `subject:` token, not by `folderPath`.
- **Do not trust a `success` return as verification** for any move — confirm the message's `folderPath` changed.
- **Gmail messages appear in both a category folder and `[Gmail]/All Mail`** (`dupLocations`) — that is normal, not a failed move.
- **Bodies carry signatures, legal boilerplate and `$600`-style figures** (e.g. an IRS debt-forgiveness threshold) that regex will happily mistake for a bill amount. Always confirm the amount line reads like `Amount due`, `minimum amount of`, `Total Due`, or `past due balance of`.
- **Yahoo folder counts read stale/zero** until the folder is opened in Thunderbird; do not treat a 0 count as proof of an empty folder.

## Verification Checklist

- CSV: header unchanged, `len(row) == 10` for every row, CRLF preserved, `.bak` written.
- Idempotency: a second `append_bills.py` run reports 0 added.
- Mail: each processed message's whole-account search now resolves to a `Trash` folder.

## Files

- `scripts/tbclient.py` — direct JSON-RPC/HTTP client for the Thunderbird extension (token stays on disk).
- `scripts/fetch_finance_mail.py` — dump finance-folder messages to `bills_raw.json`.
- `scripts/digest.py` — compact per-message digest (sender, subject, amounts, dates, key lines).
- `scripts/append_bills.py` — dedup append of a bills JSON list into the CSV.
- `scripts/trash_processed.py` — move processed messages to Trash and verify.
