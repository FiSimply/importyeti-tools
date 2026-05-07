#!/usr/bin/env python3
"""
ImportYeti Query Helper
-----------------------
Queries the ImportYeti API and saves results to a JSON file
that Claude (Cowork mode) can read directly.

Usage:
  python iy_query.py search-company "Company Q"
  python iy_query.py get-company "company-q"
  python iy_query.py get-company-bols "company-q"
  python iy_query.py search-supplier "Shenzhen"
  python iy_query.py get-supplier "shenzhen-company-q"
  python iy_query.py search-product-suppliers "SMD cobrahead"
  python iy_query.py search-product-companies "SMD cobrahead"
  python iy_query.py powerquery-bols --product "SMD cobrahead" --country "China" --start 01/01/2024
  python iy_query.py db-updated

Results are saved to: iy_result.json (same folder as this script)
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

API_BASE    = "https://data.importyeti.com"
API_KEY     = os.environ.get("IMPORTYETI_API_KEY", "")  # Set via environment variable or .env file
RESULT_FILE = Path(__file__).parent / "iy_result.json"

if not API_KEY:
    print("ERROR: IMPORTYETI_API_KEY environment variable is not set.")
    print("Set it in your shell or create a .env file with IMPORTYETI_API_KEY=your_key_here")
    sys.exit(1)


def api_get(endpoint, params=None):
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    qs    = ("?" + urllib.parse.urlencode(clean)) if clean else ""
    url   = f"{API_BASE}{endpoint}{qs}"
    req   = urllib.request.Request(url, headers={"IYApiKey": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body[:300]}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}")
        sys.exit(1)


def save(data, command, args_dict):
    out = {
        "query_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "command":    command,
        "args":       args_dict,
        "result":     data,
    }
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Saved to: {RESULT_FILE}")
    # Print a compact preview
    if isinstance(data, dict):
        keys = list(data.keys())[:6]
        print(f"Top-level keys: {keys}")
    elif isinstance(data, list):
        print(f"Results: {len(data)} items")
    print("Done. Claude can now read iy_result.json.")


def main():
    parser = argparse.ArgumentParser(description="ImportYeti query helper for Cowork")
    sub    = parser.add_subparsers(dest="cmd", required=True)

    # search-company
    p = sub.add_parser("search-company", help="Search US companies by name")
    p.add_argument("name")

    # get-company
    p = sub.add_parser("get-company", help="Get full company profile by slug")
    p.add_argument("slug")

    # get-company-bols
    p = sub.add_parser("get-company-bols", help="List BOLs for a US company")
    p.add_argument("slug")
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--offset",    type=int, default=0)

    # search-supplier
    p = sub.add_parser("search-supplier", help="Search overseas suppliers by name")
    p.add_argument("name")

    # get-supplier
    p = sub.add_parser("get-supplier", help="Get full supplier profile by slug")
    p.add_argument("slug")

    # get-supplier-bols
    p = sub.add_parser("get-supplier-bols", help="List BOLs for a supplier")
    p.add_argument("slug")
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--offset",    type=int, default=0)

    # search-product-suppliers
    p = sub.add_parser("search-product-suppliers", help="Find overseas suppliers by product")
    p.add_argument("product")
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--offset",    type=int, default=0)

    # search-product-companies
    p = sub.add_parser("search-product-companies", help="Find US buyers by product")
    p.add_argument("product")
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--offset",    type=int, default=0)

    # powerquery-bols
    p = sub.add_parser("powerquery-bols", help="Advanced BOL search (15+ filters)")
    p.add_argument("--product",   dest="product_description")
    p.add_argument("--company",   dest="company")
    p.add_argument("--supplier",  dest="supplier")
    p.add_argument("--country",   dest="supplier_country")
    p.add_argument("--entry-port",dest="entry_port")
    p.add_argument("--exit-port", dest="exit_port")
    p.add_argument("--start",     dest="start_date", help="MM/DD/YYYY")
    p.add_argument("--end",       dest="end_date",   help="MM/DD/YYYY")
    p.add_argument("--hs-code",   dest="hs_code")
    p.add_argument("--weight",    dest="weight")
    p.add_argument("--vessel",    dest="vessel_name")
    p.add_argument("--carrier",   dest="carrier_scac_code")
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--page",      type=int, default=None)

    # powerquery-companies
    p = sub.add_parser("powerquery-companies", help="Advanced US company search")
    p.add_argument("--product",   dest="product_description")
    p.add_argument("--company",   dest="company")
    p.add_argument("--supplier",  dest="supplier")
    p.add_argument("--country",   dest="supplier_country")
    p.add_argument("--entry-port",dest="entry_port")
    p.add_argument("--start",     dest="start_date", help="MM/DD/YYYY")
    p.add_argument("--end",       dest="end_date",   help="MM/DD/YYYY")
    p.add_argument("--page-size", type=int, default=20)

    # powerquery-suppliers
    p = sub.add_parser("powerquery-suppliers", help="Advanced overseas supplier search")
    p.add_argument("--product",   dest="product_description")
    p.add_argument("--company",   dest="company")
    p.add_argument("--supplier",  dest="supplier")
    p.add_argument("--country",   dest="supplier_country")
    p.add_argument("--exit-port", dest="exit_port")
    p.add_argument("--start",     dest="start_date", help="MM/DD/YYYY")
    p.add_argument("--end",       dest="end_date",   help="MM/DD/YYYY")
    p.add_argument("--page-size", type=int, default=20)

    # db-updated
    sub.add_parser("db-updated", help="Get database last updated date")

    args = parser.parse_args()

    if args.cmd == "search-company":
        data = api_get("/v1.0/company/search", {"name": args.name})
        save(data, args.cmd, {"name": args.name})

    elif args.cmd == "get-company":
        data = api_get(f"/v1.0/company/{args.slug}")
        save(data, args.cmd, {"slug": args.slug})

    elif args.cmd == "get-company-bols":
        data = api_get(f"/v1.0/company/{args.slug}/bols",
                       {"page_size": args.page_size, "offset": args.offset})
        save(data, args.cmd, {"slug": args.slug})

    elif args.cmd == "search-supplier":
        data = api_get("/v1.0/supplier/search", {"name": args.name})
        save(data, args.cmd, {"name": args.name})

    elif args.cmd == "get-supplier":
        data = api_get(f"/v1.0/supplier/{args.slug}")
        save(data, args.cmd, {"slug": args.slug})

    elif args.cmd == "get-supplier-bols":
        data = api_get(f"/v1.0/supplier/{args.slug}/bols",
                       {"page_size": args.page_size, "offset": args.offset})
        save(data, args.cmd, {"slug": args.slug})

    elif args.cmd == "search-product-suppliers":
        data = api_get(f"/v1.0/product/{urllib.parse.quote(args.product)}/suppliers",
                       {"page_size": args.page_size, "offset": args.offset})
        save(data, args.cmd, {"product": args.product})

    elif args.cmd == "search-product-companies":
        data = api_get(f"/v1.0/product/{urllib.parse.quote(args.product)}/companies",
                       {"page_size": args.page_size, "offset": args.offset})
        save(data, args.cmd, {"product": args.product})

    elif args.cmd == "powerquery-bols":
        params = {k: v for k, v in vars(args).items()
                  if k not in ("cmd",) and v is not None}
        data = api_get("/v1.0/powerquery/us-import/bols", params)
        save(data, args.cmd, params)

    elif args.cmd == "powerquery-companies":
        params = {k: v for k, v in vars(args).items()
                  if k not in ("cmd",) and v is not None}
        data = api_get("/v1.0/powerquery/us-import/companies", params)
        save(data, args.cmd, params)

    elif args.cmd == "powerquery-suppliers":
        params = {k: v for k, v in vars(args).items()
                  if k not in ("cmd",) and v is not None}
        data = api_get("/v1.0/powerquery/us-import/suppliers", params)
        save(data, args.cmd, params)

    elif args.cmd == "db-updated":
        data = api_get("/v1.0/database-updated")
        save(data, args.cmd, {})


if __name__ == "__main__":
    main()
