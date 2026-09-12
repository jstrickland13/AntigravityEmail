# Accountant

Autonomous agent workflows and skills for email triage, bill tracking, and financial reconciliation using Thunderbird MCP.

## Features

- **Thunderbird MCP Bridge Integration**: Connects locally via JSON-RPC / MCP (`TKasperczyk/thunderbird-mcp`) without transmitting credentials.
- **Inbox Categorization (`thunderbird-inbox-categorization`)**:
  - Automatically sorts incoming mail into account-specific category folders.
  - Leaves unclassified/ambiguous mail in INBOX and generates an audit reconciliation report.
- **Bills Extraction to CSV (`thunderbird-bills-to-csv`)**:
  - Direct HTTP/JSON-RPC fetch to disk (`bills_raw.json`) to prevent LLM context blowup.
  - Extracts bills with stated amounts and due dates into `Bills.csv`.
  - Idempotent deduplication against payee, amount, and due date.
  - Automatically trashes processed emails after verification.

## Project Structure

```
Accountant/
├── .agents/
│   ├── plugins/
│   │   └── thunderbird/        # MCP server configuration (command + bridge args)
│   └── skills/
│       ├── thunderbird-mcp/    # General Thunderbird MCP skill & tools reference
│       ├── thunderbird-inbox-categorization/ # Inbox triage workflow
│       └── thunderbird-bills-to-csv/         # Bill extraction pipeline
│           └── scripts/
│               ├── tbclient.py           # Direct JSON-RPC client (bearer token stays on disk)
│               ├── fetch_finance_mail.py # Fetches finance folder mail to disk
│               ├── digest.py             # Generates compact text digests
│               ├── append_bills.py       # Deduplicates and appends to Bills.csv
│               └── trash_processed.py    # Trashes processed mail & verifies
├── AGENTS.md                   # Agent execution instructions and guidelines
├── CLAUDE.md                   # Semantic protocol & token reduction rules
├── README.md                   # Project overview and security guide
└── .gitignore                  # Prevents accidental commit of sensitive artifacts
```

## Security & Privacy Guidelines

- **No Hardcoded Passwords or Credentials**: All authentication is handled dynamically by Thunderbird and the MCP bridge extension.
- **Session Tokens**: Bearer tokens are dynamically written to the local OS temporary directory (`%TEMP%\thunderbird-mcp\connection.json`) by the Thunderbird extension during runtime and are never printed or committed.
- **Email Privacy**: Raw email bodies dumped to `bills_raw.json` or staging files like `bills_new.json` are excluded via `.gitignore` to prevent committing personal email contents or sensitive financial notices.
- **Execution Safety**: High-risk mailbox actions (empty trash/junk, mass delete) enforce verification steps before execution.

