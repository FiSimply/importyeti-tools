# ImportYeti Tools for Claude

Two tools for querying the [ImportYeti](https://www.importyeti.com) US import data API — a FastMCP server and a lightweight CLI query helper.

## Background

This started as an attempt to build a custom MCP server for use inside Claude's Cowork mode. The MCP server works correctly when run standalone, but Cowork mode uses its own isolated connector system and doesn't load custom MCPs from `claude_desktop_config.json` or `~/.claude/settings.json`.

The solution: a simple Python script (`iy_query.py`) that hits the ImportYeti API directly, writes results to a JSON file, and lets Claude read it. Less elegant, completely reliable.

---

## Files

| File | Purpose |
|------|---------|
| `importyeti_mcp.py` | FastMCP server — 13 tools covering companies, suppliers, BOLs, and PowerQuery. Works in standard Claude Desktop chat if custom MCPs are supported in your setup. |
| `iy_query.py` | CLI query helper. Runs a query and saves results to `iy_result.json` for Claude to read. The reliable path for Cowork mode. |
| `run_setup.ps1` | PowerShell script that patches `claude_desktop_config.json` to register the MCP server. Windows only. |

---

## Setup

### 1. Get an API key
Sign up at [importyeti.com/yeti-api](https://www.importyeti.com/yeti-api) to get your API key.

### 2. Set your environment variable

**Windows (CMD):**
```cmd
set IMPORTYETI_API_KEY=your_key_here
```

**Windows (PowerShell):**
```powershell
$env:IMPORTYETI_API_KEY = "your_key_here"
```

**Mac/Linux:**
```bash
export IMPORTYETI_API_KEY=your_key_here
```

Or copy `.env.example` to `.env` and fill it in. Then load it before running scripts.

### 3. Install dependencies
```bash
pip install mcp[cli] httpx pydantic
```

---

## iy_query.py — CLI Query Helper

Run a query and save results to `iy_result.json`. In Cowork sessions, paste the CMD command into your terminal, then tell Claude to read `iy_result.json`.

```bash
# Search for a US company
python iy_query.py search-company "Acme Signs"

# Get full company profile (use slug from search results)
python iy_query.py get-company "acme-signs"

# Get recent shipments for a company
python iy_query.py get-company-bols "acme-signs" --page-size 50

# Search overseas suppliers
python iy_query.py search-supplier "Shenzhen LED"

# Get full supplier profile
python iy_query.py get-supplier "shenzhen-led-co"

# Find overseas suppliers by product
python iy_query.py search-product-suppliers "LED modules"

# Find US companies importing a product
python iy_query.py search-product-companies "LED modules"

# Advanced BOL search with filters
python iy_query.py powerquery-bols --product "LED modules" --country "China" --start 01/01/2024

# Advanced company search
python iy_query.py powerquery-companies --product "LED modules" --entry-port "Los Angeles"

# Advanced supplier search
python iy_query.py powerquery-suppliers --product "LED modules" --country "China"

# Check database freshness
python iy_query.py db-updated
```

### PowerQuery filters
`--product`, `--company`, `--supplier`, `--country`, `--entry-port`, `--exit-port`, `--start` (MM/DD/YYYY), `--end` (MM/DD/YYYY), `--hs-code`, `--weight`, `--vessel`, `--carrier`, `--page-size`, `--page`

---

## importyeti_mcp.py — MCP Server

For use in standard Claude Desktop chat or any MCP-compatible client.

**Register with Claude Desktop** — run `run_setup.ps1` (Windows) or manually add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "importyeti": {
      "command": "python",
      "args": ["/absolute/path/to/importyeti_mcp.py"],
      "env": {
        "IMPORTYETI_API_KEY": "your_key_here"
      }
    }
  }
}
```

Then fully restart Claude Desktop.

### Known issues
- **mcp 1.27.0 on Windows**: JSONRPCMessage blank-line parsing error breaks the stdio handshake. Downgrade to `mcp[cli]==1.6.0`.
- **Cowork mode**: Does not load custom MCPs from config files. Use `iy_query.py` instead.
- The `annotations=` parameter in `@mcp.tool()` is not supported in mcp 1.6.0 — already removed from this version of the server.

---

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `importyeti_get_bol` | Get a bill of lading by number |
| `importyeti_search_companies` | Search US companies by name |
| `importyeti_get_company` | Get full company profile by slug |
| `importyeti_get_company_bols` | List BOLs for a US company |
| `importyeti_search_suppliers` | Search overseas suppliers by name |
| `importyeti_get_supplier` | Get full supplier profile by slug |
| `importyeti_get_supplier_bols` | List BOLs for a supplier |
| `importyeti_search_product_suppliers` | Find overseas suppliers by product keyword |
| `importyeti_search_product_companies` | Find US buyers by product keyword |
| `importyeti_powerquery_bols` | Advanced BOL search (15+ filters) |
| `importyeti_powerquery_companies` | Advanced US company search |
| `importyeti_powerquery_suppliers` | Advanced overseas supplier search |
| `importyeti_database_updated` | Get database last updated date |

---

## Notes
- `get-company` returns large JSON responses (40k+ tokens for active importers). Read the first portion for key fields.
- `get-company-bols` returns BOL numbers only, not full shipment detail. Use `powerquery-bols` with a company filter for detailed shipment data.
- API credits are consumed by PowerQuery and `get-company-bols` calls. Simple searches are free.
