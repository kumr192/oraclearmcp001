# Oracle Fusion AR MCP Server

MCP server for Oracle Fusion Accounts Receivable APIs. Deployed via Streamable HTTP transport on Railway.

## Tools Available

| Tool | Description |
|------|-------------|
| `oracle_ar_test_connection` | Test Oracle Fusion credentials |
| `oracle_ar_list_invoices` | List AR invoices with filters |
| `oracle_ar_list_receipts` | List payment receipts |
| `oracle_ar_list_customer_activities` | Get customer transaction history |
| `oracle_ar_get_customer_summary` | Full AR summary for a customer |
| `oracle_ar_get_aging_summary` | Invoice aging buckets |

## Deploy to Railway

### Option 1: One-Click Deploy

1. Push this repo to GitHub
2. Go to [Railway](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Railway auto-detects the Dockerfile
5. Wait for build to complete
6. Get your URL: `https://your-app.railway.app`

### Option 2: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

## Connect to Claude

### Claude.ai (Web)

Add as MCP connector with URL:
```
https://your-app.railway.app/mcp
```

### Claude Desktop (via mcp-remote)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "oracle-ar": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://your-app.railway.app/mcp",
        "--header",
        "Accept: application/json, text/event-stream"
      ]
    }
  }
}
```

## Usage

Every tool requires Oracle Fusion credentials:

```
base_url: "https://your-instance.oraclepdemos.com"
username: "your_username"
password: "your_password"
```

**Note**: This is a stateless server. Credentials are not stored between requests.

### Example: Test Connection

```json
{
  "base_url": "https://eqjz.ds-fa.oraclepdemos.com",
  "username": "user@example.com",
  "password": "secret"
}
```

### Example: Get Aging Report

```json
{
  "base_url": "https://eqjz.ds-fa.oraclepdemos.com",
  "username": "user@example.com",
  "password": "secret",
  "limit": 100
}
```

## Local Development

```bash
# With uv
uv sync
uv run python server.py

# Server runs at http://localhost:8000/mcp
```

## Test the Endpoint

```bash
curl -X POST https://your-app.railway.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {"tools": {}},
      "clientInfo": {"name": "test", "version": "1.0.0"}
    }
  }'
```

## Architecture

- **Transport**: Streamable HTTP (stateless mode)
- **Framework**: FastMCP
- **Auth**: Per-request Basic Auth to Oracle Fusion
- **Deployment**: Docker on Railway

## Security Notes

- Credentials are passed per-request, not stored
- SSL verification disabled for Oracle demo instances (enable for prod)
- Railway provides HTTPS automatically
