---
name: thunderbird-inbox-categorization
description: "Use when sorting a Thunderbird inbox into category folders."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [email, thunderbird, mcp, triage, inbox, folders, categorization]
    related_skills: [thunderbird-mcp, email-inbox-triage]
---

# Thunderbird Inbox Categorization

Sort an account's INBOX into its existing category folders: classify each message, move what
clearly fits, leave the rest in the INBOX, and report the leftovers at the end. Requires the
`thunderbird-mcp` skill's setup (live Thunderbird + MCP bridge). This skill covers the *workflow
and the conventions*; `thunderbird-mcp` covers the tools.

## When to Use

- "Sort / categorize / file my inbox into the category folders."
- "Move each inbox message into the right folder; report anything that doesn't fit."

Not for: one-off single-message filing, or triage that only ranks/drafts replies (use
`email-inbox-triage`).

## Before You Start

1. **Read the taxonomy off the account, don't assume it.** `listAccounts` then `listFolders`.
   The category folders are the account's custom folders, not Trash/Junk/Drafts/Sent/Archive/Outbox.
   Each account has its own taxonomy — never reuse one account's categories for another.
2. **Resolve the catch-all with the user before moving anything.** Most accounts have a generic
   folder (`Other`). It technically "fits" every message, which makes the "no folder fits → leave
   it and report" instruction dead. Ask which the user means:
   - default assumption: **do not use the catch-all** — mail with no *specific* fit stays in the
     INBOX and goes in the report;
   - or use it as a dumping ground (then the report is near-empty).
   One `clarify` call up front; it changes where dozens of messages land.
3. **Confirm identity/scope.** If two accounts both have inboxes, treat them independently and
   report per account.

## Procedure

1. **Fetch the inbox in full.** `searchMessages` with `query: ""`, the INBOX `folderPath`,
   `includeSubfolders: false`, `maxResults: 200`, **`dedupByMessageId: false`** and an `offset`
   so the response carries `totalMatches`. That total is the number every later step must reconcile to.
   Read `id`, `subject`, `author`, `date` per row; only call `getMessage` for rows whose body you
   genuinely need to classify.
2. **Classify all rows first.** Assign each message to one specific folder (or to "leave").
   Decide the whole batch before moving anything.
3. **Bulk-move per destination.** One `updateMessage` call per destination folder, passing
   `messageIds: [...]` + `folderPath` (source INBOX) + `moveTo` (destination). Bulk `messageIds`
   beats looping single `messageId` calls. Never mix tags with `moveTo` on IMAP — separate calls.
4. **Verify by whole-account search, not by folder counts.** See Verification.
5. **Reconcile:** `moved + left == inbox total`, per account. If it doesn't balance, find the gap
   before reporting — do not report a partial subset as done.

## Classification Rules

- Match on **sender + subject**, not on folder-name intuition alone.
- Strong fit → move. Weak/no fit → leave in the INBOX and list it in the report. Don't force a
  message into a folder just to make the inbox empty.
- Transactional/alert mail (order + delivery updates, statements, payment reminders, security
  alerts) files by its **domain** (retail, financial, security), not by its "notification" form.
- A single sender can split across folders by subject (e.g. a bank's payment reminder → finance,
  its marketing blast → promotions). Classify per message.
- Leave genuinely ambiguous personal mail from unknown senders for the user to judge.

## Verification

**Do not trust the success return, and do not trust folder counts.** On IMAP (Yahoo especially):

- `updateMessage` may return `{success:true, updated:N}` while **nothing moves** — some folders
  (observed: a Yahoo "Security and Account" folder) silently reject `moveTo`, likely because they
  are virtual/search folders. A URL-encoded path probe (`%20` for spaces) returns
  `"Folder not found"` for such folders, which is a useful diagnostic.
- `listFolders` counts and `searchMessages` scoped to a specific `folderPath` **lag for many
  seconds** after a move, showing stale or empty results.

So verify each destination by running a **whole-account `searchMessages`** (no `folderPath`, query
on a distinctive sender/subject token from the moved mail) and check the returned `folderPath`.
Reconcile the per-folder moved counts against `totalMatches` from step 1.

## Report (the deliverable)

End with, per account:

- a **destination-folder table** with counts (and total moved);
- a **leftovers section** naming each message left in the INBOX with sender + a one-line reason
  (no fitting category / destination folder rejected the move / ambiguous sender);
- an explicit **reconciliation** line (`moved + left = inbox total`);
- a note on which category folders stayed empty;
- any **judgment calls** the user may want to reverse (e.g. how you treated order/receipt mail).

## Pitfalls

- Assuming a folder name from a previous account — taxonomies are per account; read `listFolders`.
- Using the catch-all without asking, which silently defeats the "report what didn't fit" requirement.
- Declaring done after moves return `success` — always re-read. Silent move failures are real.
- Trusting the destination folder's own count/search for verification instead of a whole-account search.
- Forgetting `dedupByMessageId: false` + `offset`, which hides `totalMatches` and can undercount the inbox.
- Mixing tags and `moveTo` in one IMAP call (tags may be dropped on the moved copy).
