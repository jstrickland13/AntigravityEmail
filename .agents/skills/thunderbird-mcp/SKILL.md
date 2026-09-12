---
name: thunderbird-mcp
description: "Manage Thunderbird mail, contacts, events via MCP bridge."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [email, thunderbird, mcp, imap, calendar, contacts, filters]
    related_skills: [email-inbox-triage, thunderbird-inbox-categorization]
---

# Thunderbird MCP Skill

Drive a local Thunderbird install — read/search mail, compose replies, organize folders, run filters, and manage contacts/calendar — through the `TKasperczyk/thunderbird-mcp` MCP server. Everything runs locally: a Thunderbird extension embeds an HTTP server on localhost, and a Node bridge translates MCP stdio to that HTTP API. Hermes connects to the bridge as a native MCP server, so its ~40 tools appear as `mcp_<server>_<tool>`.

This skill covers setup, the tool surface, and the safety rules. It does not cover IMAP/POP account setup in Thunderbird itself.

## When to Use

- Read, search, triage, or summarize the user's Thunderbird mailbox
- Compose / reply / forward mail, or draft replies for review
- Organize mail: move, tag, flag, create folders, empty Trash/Junk
- Create/run/repair Thunderbird message filters
- Look up contacts or manage calendar events and tasks
- Don't use for: Gmail/Outlook via cloud APIs (use `google-workspace`), or non-Thunderbird mail. Don't use `email-inbox-triage` workflows that assume IMAP credentials — here access is through the local client.

## Prerequisites

1. **Thunderbird running** with the accounts signed in (the bridge only talks to a live Thunderbird).
2. **Node.js** on PATH (`node --version`).
3. **The thunderbird-mcp extension installed** in Thunderbird. One-time bootstrap:
   ```
   terminal(command="git clone https://github.com/TKasperczyk/thunderbird-mcp.git ~/thunderbird-mcp")
   ```
   Then install `~/thunderbird-mcp/dist/thunderbird-mcp.xpi` via Thunderbird → Tools → Add-ons → **Install Add-on From File**, and restart. From v0.7.3+ it auto-updates.

   **Install through the Add-ons Manager UI — do not sideload.** Dropping the XPI into the profile's `extensions/` dir and hand-patching `extensions.json` marks the add-on "active" but never boots its background script: no `console.log`, no listener on 8765-8774, no `connection.json`. The add-on only runs when registered through the Add-ons Manager's own install path. If you must verify headlessly, the tell is `/tmp/thunderbird-mcp/connection.json` plus a listening port — absence of both means the server never started regardless of what `extensions.json` claims.
4. **`mcp` Python package** in the Hermes venv (otherwise MCP discovery is silently disabled): `pip install mcp` or `uv pip install mcp`.
5. **The server registered in Hermes config** (next section).

If the extension is missing or Thunderbird is closed, every tool call fails with *connection refused* — that is not a Hermes bug.

## Setup: register the bridge with Hermes

Do NOT hand-edit `config.yaml` — use `hermes config set`, or ask before editing, so the live gateway isn't corrupted. The bridge is a stdio MCP server; configure it under `mcp_servers` with an absolute path to `mcp-bridge.cjs`:

```yaml
mcp_servers:
  thunderbird:
    command: "node"
    args: ["/home/<user>/thunderbird-mcp/mcp-bridge.cjs"]
    connect_timeout: 30
```

Name the server `thunderbird` (short) so tools resolve as `mcp_thunderbird_searchMessages`, `mcp_thunderbird_sendMail`, etc. Restart Hermes after adding it — MCP servers load at startup, no hot-reload.

### Sandbox / non-standard temp dirs

The bridge auto-discovers `connection.json` (which holds the port + bearer token) in: `$THUNDERBIRD_MCP_CONNECTION_FILE`, then the OS temp dir, then macOS `/var/folders`, Linux Snap `TMPDIR`, and Flatpak `$XDG_RUNTIME_DIR`. If your Thunderbird is Snap/Flatpak/Betterbird and auto-discovery fails, pin it explicitly:

```yaml
    env:
      THUNDERBIRD_MCP_CONNECTION_FILE: "/path/to/connection.json"
```

Never read or print the token in `connection.json` into chat — it is a session credential.

## How to Run

Once registered, call the tools directly. Verify connectivity first:

```
mcp_thunderbird_listAccounts()
```

A list of accounts means the whole chain (Hermes → bridge → extension → Thunderbird) is up. To test the bridge outside Hermes:

```
terminal(command="echo '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}' | node ~/thunderbird-mcp/mcp-bridge.cjs | head -c 2000", timeout=60)
```

## Quick Reference (tool → purpose)

Prefix every name with `mcp_thunderbird_`. Full catalog in `references/tools.md`.

**Mail read** — `listAccounts`, `listFolders` (folder tree + counts), `searchMessages` (see query syntax), `getMessage`, `getMessages` (batch ≤10 default, ≤20 max), `getRecentMessages`, `displayMessage` (open in GUI).
**Mail write** — `updateMessage` (read/flag/tag/move/trash, bulk via `messageIds`), `deleteMessages`, `createFolder`, `renameFolder`, `deleteFolder`, `moveFolder`, `emptyTrash`, `emptyJunk`.
**Compose** — `sendMail`, `replyToMessage`, `forwardMessage` (all open a review window by default).
**Filters** — `listFilters`, `createFilter`, `updateFilter`, `deleteFilter`, `reorderFilters`, `applyFilters`.
**Contacts** — `searchContacts`, `getContact`, `createContact`, `updateContact`, `deleteContact`.
**Calendar** — `listCalendars`, `createEvent`, `listEvents`, `updateEvent`, `deleteEvent`, `createTask`, `listTasks`, `updateTask`.
**Access** — `getAccountAccess` (read-only view of what the server may touch).

### searchMessages query syntax

- Multi-word query = AND of every token. Use `from:`, `subject:`, `to:`, `cc:` prefixes to scope a token to one field.
- `searchBody: true` → full-text via Gloda (needs offline/disk copy synced on IMAP; otherwise headers only).
- `includeSubfolders`, `countOnly`, and offset pagination are supported. Results carry `threadId` and a `preview` snippet.
- `dedupByMessageId` (default true) collapses the same RFC Message-ID found in multiple folders/labels and lists the others in `dupLocations`.

## Procedure

1. **Orient.** Call `listAccounts` then `listFolders` for the target account. Completion: you know the exact `folderPath` strings before searching (guessing paths causes empty results).
2. **Find.** `searchMessages` with scoped tokens; confirm result count and read `threadId` before acting. For full bodies use `getMessage` with `bodyFormat` (`markdown` default / `text` / `html`).
3. **Read before you change.** Any mutating call (move, tag, trash, send) must first resolve the exact `messageId` + `folderPath`. Completion: the ID and folder are confirmed by a prior read, not assumed from search order.
4. **Act.** Apply the change; use `messageIds` for bulk `updateMessage`/`deleteMessages` instead of looping one-by-one.
5. **Verify.** Re-read with `searchMessages`/`listFolders` to confirm the change landed. IMAP folder ops (rename/move/delete) are async — completion criterion is that `listFolders` reflects the new state, not just a success return.

## Safety (do not bypass)

- **Review gates are on by default.** The extension's *Block `skipReview`* setting rejects `skipReview: true` for `sendMail`, `replyToMessage`, `forwardMessage`, `createEvent`, and `createTask`; the compose/review window opens for the user instead. Never disable that setting to send silently, and never tell the user to. The user reviews and sends.
- **Confirm before destructive bulk ops** (`emptyTrash`, `emptyJunk`, `deleteMessages` in bulk, `deleteFolder`). State the count and folder first.
- **`from` identity is validated** — compose tools error if the sender doesn't match a configured identity rather than substituting an account. Pass a real identity; don't retry blindly.
- **Account/tool access control is user-only** (extension settings page). `getAccountAccess` is read-only. Don't try to widen scope; if a tool is missing from `tools/list` it was disabled by the user.
- If `THUNDERBIRD_MCP_CONNECTION_FILE` or the token is ever surfaced, treat it as a secret — never echo it.

## Pitfalls

- **Move reports `success` but nothing moves** → some folders (observed: a Yahoo "Security and Account" folder) silently reject `moveTo`: the call returns `{success:true,updated:N}` yet the messages stay put, and the folder stays empty. Treat every move as unverified until a follow-up read shows the message at the destination; if it didn't take, fall back to leaving the mail in place and reporting it. Encoded paths (`%20`) for such folders return "Folder not found" — a useful probe.
- **Folder counts and folder-scoped `searchMessages` lag badly on IMAP** (Yahoo especially) → `listFolders` counts and searches scoped to a specific `folderPath` can show stale/empty results for many seconds after a move. Verify placement with a whole-account `searchMessages` (no `folderPath`, search by a distinctive sender/subject token) instead of trusting the destination folder's own count or search.
- **"Connection refused"** → Thunderbird isn't running or the extension is disabled. Ensure both, then retry.
- **Bridge can't find `connection.json`** → set `THUNDERBIRD_MCP_CONNECTION_FILE` (Snap/Flatpak/macOS temp dirs).
- Stale IMAP folders → counts/results lag until the folder is clicked in Thunderbird (or Properties → Repair Folder). Not a bridge bug. This also affects post-move verification: prefer a whole-account `searchMessages` over the destination folder's count.
- **`searchBody` returns nothing** → IMAP account has no offline sync, so Gloda only indexed headers.
- **`rawSource` errors** → requires a local/offline message copy; open the message in Thunderbird first to cache it.
- **HTML-only mail loses formatting** → body is converted to plain text.
- **Recurring events** → CRUD applies to the whole series, not single occurrences.
- **Tags + move/trash in one IMAP call** may drop tags on the moved copy — do them in separate calls.
- **Pre-existing filters with cross-account move/copy targets** bypass account access control.
- **Sideloaded extension looks installed but does nothing** → `extensions.json` shows `active: true` yet no `connection.json` and no listening port. The background script isn't running; reinstall via Tools → Add-ons → Install Add-on From File. Editing `extensions.json` or `addonStartup.json.lz4` by hand does not fix it.
- **Tool not found after an upgrade** → reconnect/restart Hermes to re-list tools; MCP tools load at startup.

## Verification

- `mcp_thunderbird_listAccounts` returns the expected accounts.
- The bridge self-test above prints a `tools/list` JSON with the mail/compose/filter/calendar tools.
- Any mutation is re-confirmed by a follow-up read (`searchMessages` / `listFolders`) showing the new state.

## References

- `references/tools.md` — full tool catalog with the key parameters for each.
- Upstream: https://github.com/TKasperczyk/thunderbird-mcp (MIT; bundled `httpd.sys.mjs` is MPL-2.0).
