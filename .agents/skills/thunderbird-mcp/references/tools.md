# Thunderbird MCP — Full Tool Catalog

All tools are exposed to Hermes as `mcp_thunderbird_<toolName>` (server named `thunderbird`).
Parameters below are the notable ones, not exhaustive — the schema is authoritative at call time.

## Mail — read

| Tool | Key purpose / params |
| --- | --- |
| `listAccounts` | All accounts + identities. First call to verify connectivity. |
| `listFolders` | Folder tree with counts; filter by account or subtree. Returns the `folderPath` strings used everywhere else. |
| `searchMessages` | subject/sender/recipient/preview/date/tag search. `from:` `subject:` `to:` `cc:` prefixes; `searchBody`, `includeSubfolders`, `countOnly`, offset pagination, `dedupByMessageId`. Returns `threadId` + `preview`. |
| `getMessage` | Full content. `bodyFormat`: `markdown`\|`text`\|`html`. `rawSource: true` for RFC 2822. Optional attachment saving. `includeInlineImages` → PNG/JPEG/GIF/WebP, ≤1 MiB each, ≤4 MiB total. |
| `getMessages` | Batch read (default 10, max 20). Each item = `messageId` + `folderPath`. |
| `getRecentMessages` | Recent with date/unread/tag filters + pagination. |
| `displayMessage` | Open in GUI: `3pane` (default) \| `tab` \| `window`. |

## Mail — write / organize

| Tool | Key purpose / params |
| --- | --- |
| `updateMessage` | Mark read/unread, flag, add/remove tags, move, trash. Bulk via `messageIds`. |
| `deleteMessages` | Delete; drafts move safely to Trash. |
| `createFolder` / `renameFolder` / `moveFolder` | Folder management (move within same account). |
| `deleteFolder` | To Trash, or permanent if already in Trash. |
| `emptyTrash` / `emptyJunk` | Permanently delete Trash / Junk incl. subfolders. Confirm first. |

## Compose

| Tool | Notes |
| --- | --- |
| `sendMail` | Opens a review window by default. `skipReview: true` rejected unless the user disabled the *Block skipReview* setting. |
| `replyToMessage` | Quotes original, threads properly. Same review rule. |
| `forwardMessage` | Preserves original attachments. Same review rule. |

Attachments: file paths or inline base64 objects. `from` must match a configured identity or the tool errors.

## Filters

| Tool | Notes |
| --- | --- |
| `listFilters` | All rules, human-readable conditions + actions. |
| `createFilter` | Structured conditions (from, subject, date…) + actions (move, tag, flag…). |
| `updateFilter` | Change name, enabled state, conditions, actions. |
| `deleteFilter` | Remove by index. |
| `reorderFilters` | Priority order. |
| `applyFilters` | Run on a folder on demand. |

Changes persist immediately.

## Contacts

`searchContacts` (email/name, `maxResults`), `getContact` (by UID), `createContact`
(email/name, phones, addresses, org, title, note, birthday; phone-only ok),
`updateContact` (omitted fields unchanged; empty arrays clear collections), `deleteContact` (UID).

## Calendar & tasks

| Tool | Notes |
| --- | --- |
| `listCalendars` | Read-only / event / task capability flags. |
| `createEvent` | Review dialog by default; `skipReview` gated. `status`: tentative\|confirmed\|cancelled (RFC 5545). |
| `listEvents` | Date range, recurring events expanded; includes `status`. |
| `updateEvent` / `deleteEvent` | By ID. |
| `createTask` | Pre-filled dialog for review; `skipReview` gated. |
| `listTasks` | Filter by completion, due date, calendar. |
| `updateTask` | Title, due, description, priority, completion, percent-complete. |

## Access control

`getAccountAccess` — read-only view of accessible accounts. Account and tool access are
changed only by the user via the extension settings page (Tools → Add-ons → Thunderbird MCP → Options),
which also holds the *Send Safety / Block skipReview* toggle. Disabled tools are hidden from
`tools/list` and blocked at dispatch.
