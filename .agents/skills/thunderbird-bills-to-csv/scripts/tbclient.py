#!/usr/bin/env python3
"""Direct JSON-RPC client for the Thunderbird MCP extension.

Bypasses mcp-bridge.cjs (a stdio shim) and POSTs straight to the extension's
HTTP endpoint, so message bodies can be processed in code and never enter an
LLM context. The bearer token is read from connection.json and never printed.
"""
import json, urllib.request, os

CONN = os.environ.get(
    "THUNDERBIRD_MCP_CONNECTION_FILE",
    os.path.join(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")), "thunderbird-mcp", "connection.json")
    if os.name == "nt" else "/tmp/thunderbird-mcp/connection.json"
)


def _conn():
    with open(CONN) as f:
        d = json.load(f)
    return d["port"], d.get("token")


def call(tool, args=None, _id=1):
    port, token = _conn()
    payload = {"jsonrpc": "2.0", "id": _id, "method": "tools/call",
               "params": {"name": tool, "arguments": args or {}}}
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read().decode("utf-8", "replace"))
    if "error" in out:
        raise RuntimeError(out["error"])
    res = out.get("result", {})
    content = res.get("content") or []
    if isinstance(content, list) and content:
        return content[0].get("text", "")
    return json.dumps(res)


def call_json(tool, args=None, _id=1):
    return json.loads(call(tool, args, _id))
