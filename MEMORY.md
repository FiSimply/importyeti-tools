# ImportYeti MCP — Project Memory

## Files
- `importyeti_mcp.py` — FastMCP server, 13 tools, stdio transport (mcp 1.6.0 compatible — no annotations)
- `setup_importyeti_mcp.py` — Original one-click config patcher (for claude_desktop_config.json)
- `run_setup.ps1` — PowerShell setup script (preferred over setup_importyeti_mcp.py). Patches config, installs packages, validates JSON, uses Python 3.14 explicitly.
- `iy_query.py` — **PRIMARY WORKFLOW TOOL** for Cowork mode. Queries ImportYeti API and writes results to iy_result.json. Claude reads that file. See usage below.
- `iy_result.json` — Output file written by iy_query.py. Read by Claude after each query.

## API
- Base URL: `https://data.importyeti.com`
- Auth header: `IYApiKey`
- API key: `4ab472540d69750c2089569fd24fc1b2f6193f523e48de9c14f96ccf636fde82`
- Account: deacon@fisimply.com
- Credits: 92 remaining as of May 6 2026

## iy_query.py — Usage (Primary Workflow)

Run in CMD. Results saved to iy_result.json. Tell Claude to read it.

```
set PY="C:\Users\pdwar\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set IY="C:\Users\pdwar\OneDrive\Desktop\HS Items\AI Projects\IMPORTYETI\iy_query.py"

%PY% %IY% search-company "Company Name"
%PY% %IY% get-company "company-slug"
%PY% %IY% get-company-bols "company-slug" --page-size 50
%PY% %IY% search-supplier "Supplier Name"
%PY% %IY% get-supplier "supplier-slug"
%PY% %IY% get-supplier-bols "supplier-slug"
%PY% %IY% search-product-suppliers "LED modules"
%PY% %IY% search-product-companies "LED modules"
%PY% %IY% powerquery-bols --product "LED modules" --country "China" --start 01/01/2024
%PY% %IY% powerquery-companies --product "LED modules"
%PY% %IY% powerquery-suppliers --product "LED modules"
%PY% %IY% db-updated
```

Note: get-company returns a large file (40k+ tokens). Claude reads the first 400 lines to get key data.

## Tools (13)
| Tool | Description |
|------|-------------|
| importyeti_get_bol | Get a bill of lading by number |
| importyeti_search_companies | Search US companies by name |
| importyeti_get_company | Get full company profile by slug |
| importyeti_get_company_bols | List BOLs for a US company |
| importyeti_search_suppliers | Search overseas suppliers by name |
| importyeti_get_supplier | Get full supplier profile by slug |
| importyeti_get_supplier_bols | List BOLs for a supplier |
| importyeti_search_product_suppliers | Find overseas suppliers by product |
| importyeti_search_product_companies | Find US buyers by product |
| importyeti_powerquery_bols | Advanced BOL search (15+ filters) |
| importyeti_powerquery_companies | Advanced company search |
| importyeti_powerquery_suppliers | Advanced supplier search |
| importyeti_database_updated | Get DB last updated date |

## PowerQuery Key Filters
product_description, supplier_country, entry_port, exit_port,
start_date/end_date (MM/DD/YYYY), company, supplier,
hs_code, weight, teu, vessel_name, carrier_scac_code

## MCP Server Status (as of May 6 2026)

### What was tried
- claude_desktop_config.json — configured correctly but importyeti tools do NOT load in standard Claude Desktop chat or Cowork mode
- ~/.claude/settings.json — mcpServers entry added but importyeti tools still do NOT load in Cowork
- Cowork connector registry — no ImportYeti connector exists

### Root cause (observed)
- mcp 1.27.0: JSONRPCMessage validation error on blank line input (`'\n'`) — handshake fails
- mcp 1.6.0: Does not support `annotations` keyword in @mcp.tool() — server crashes
- After fix (removed annotations + mcp 1.6.0 + transport="stdio"): server runs clean in CMD but Claude Desktop/Cowork still does not load the tools
- Cowork mode appears to use its own isolated connector system separate from both claude_desktop_config.json and ~/.claude/settings.json

### Current workaround
Use iy_query.py (see above). This is the reliable path for Cowork sessions.

## Python
- Version: 3.14
- Path: C:\Users\pdwar\AppData\Local\Python\pythoncore-3.14-64\python.exe
- mcp version installed: 1.6.0
- Other packages: httpx, pydantic

## Site Notes
- importyeti.com/yeti-api and data.importyeti.com are client-rendered (Next.js)
- Raw web_fetch returns blank HTML — must use Chrome browser extension to read these pages
- API only accepts auth via IYApiKey header (not query param) — web_fetch cannot call it directly
- get-company response is large (40k+ tokens for major companies). Read in 200-line chunks.

## Lessons
- Any script that reads a JSON config must wrap json.load() in try/except JSONDecodeError and degrade gracefully (start fresh) rather than crashing
- mcp 1.27.0 has a stdio blank-line parsing bug on Windows — downgrade to 1.6.0
- mcp 1.6.0 does not support annotations= in @mcp.tool() — remove all annotations blocks
- Always specify transport="stdio" explicitly in mcp.run() regardless of version
- Cowork mode does not load custom MCPs from claude_desktop_config.json or ~/.claude/settings.json
- get-company-bols returns only BOL numbers (not full shipment detail) — use powerquery-bols for detailed filtering
