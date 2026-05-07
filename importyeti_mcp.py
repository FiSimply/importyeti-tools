#!/usr/bin/env python3
"""
MCP Server for ImportYeti Data API (v1.0 / OAS 3.0).

Provides tools to search and fetch US import shipment data:
  - Bills of lading lookup
  - US company search and profile
  - Overseas supplier search and profile
  - Product-based supplier/buyer discovery
  - PowerQuery advanced search (BOLs, companies, suppliers)
  - Database freshness check

Authentication:
  Set the IMPORTYETI_API_KEY environment variable before running.
  The API key is sent as the IYApiKey request header.

Install:
  pip install "mcp[cli]" httpx pydantic

Run (stdio for Claude Desktop):
  python importyeti_mcp.py

Claude Desktop config (~/.claude/claude_desktop_config.json):
  {
    "mcpServers": {
      "importyeti": {
        "command": "python",
        "args": ["/path/to/importyeti_mcp.py"],
        "env": { "IMPORTYETI_API_KEY": "your_key_here" }
      }
    }
  }
"""

import json
import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Server init
# ---------------------------------------------------------------------------
mcp = FastMCP("importyeti_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
API_BASE_URL = "https://data.importyeti.com"
API_KEY_HEADER = "IYApiKey"


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    key = os.environ.get("IMPORTYETI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "IMPORTYETI_API_KEY environment variable is not set. "
            "Set it before starting the MCP server."
        )
    return key


async def _get(endpoint: str, params: Optional[dict] = None) -> dict:
    """Make an authenticated GET request to the ImportYeti API."""
    api_key = _get_api_key()
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_BASE_URL}{endpoint}",
            headers={API_KEY_HEADER: api_key},
            params=clean_params,
        )
        response.raise_for_status()
        return response.json()


def _fmt_error(e: Exception) -> str:
    """Convert exceptions into actionable error strings."""
    if isinstance(e, RuntimeError):
        return f"Configuration error: {e}"
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 401:
            return "Error 401: Invalid API key. Verify IMPORTYETI_API_KEY."
        if code == 402:
            return "Error 402: Insufficient credits. Purchase more at importyeti.com/credits-checkout."
        if code == 404:
            return "Error 404: Resource not found. Check the identifier or slug."
        if code == 429:
            return "Error 429: Rate limit hit. Wait a moment then retry."
        return f"Error {code}: {e.response.text[:300]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    return f"Error ({type(e).__name__}): {e}"


def _dumps(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class BolGetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    number: str = Field(
        ...,
        description="Bill of lading number (e.g. 'CCLLMILS17011590').",
        min_length=1,
        max_length=100,
    )


class CompanySearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(
        ...,
        description="Company name to search for (e.g. 'Walmart', 'Target').",
        min_length=1,
        max_length=200,
    )


class CompanyGetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    company: str = Field(
        ...,
        description="Company slug or identifier (e.g. 'wal-mart', 'target'). "
                    "Use importyeti_search_companies to find the correct slug.",
        min_length=1,
        max_length=200,
    )


class CompanyBolsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    company: str = Field(
        ...,
        description="Company slug or identifier (e.g. 'wal-mart').",
        min_length=1,
        max_length=200,
    )
    page_size: Optional[int] = Field(
        default=20,
        description="Number of BOLs to return per page.",
        ge=1,
        le=100,
    )
    offset: Optional[int] = Field(
        default=0,
        description="Number of results to skip for pagination.",
        ge=0,
    )


class SupplierSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(
        ...,
        description="Overseas supplier name to search for (e.g. 'Yantian International', 'Samsung').",
        min_length=1,
        max_length=200,
    )


class SupplierGetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    supplier: str = Field(
        ...,
        description="Supplier slug or identifier. Use importyeti_search_suppliers to find it.",
        min_length=1,
        max_length=200,
    )


class SupplierBolsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    supplier: str = Field(
        ...,
        description="Supplier slug or identifier.",
        min_length=1,
        max_length=200,
    )
    page_size: Optional[int] = Field(default=20, ge=1, le=100)
    offset: Optional[int] = Field(default=0, ge=0)


class ProductSuppliersInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    product: str = Field(
        ...,
        description="Product name or keyword to find overseas suppliers for "
                    "(e.g. 'shoes', 'LED modules', 'furniture').",
        min_length=1,
        max_length=200,
    )
    page_size: Optional[int] = Field(default=20, ge=1, le=100)
    offset: Optional[int] = Field(default=0, ge=0)


class ProductCompaniesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    product: str = Field(
        ...,
        description="Product name or keyword to find US importing companies for "
                    "(e.g. 'shoes', 'LED modules', 'furniture').",
        min_length=1,
        max_length=200,
    )
    page_size: Optional[int] = Field(default=20, ge=1, le=100)
    offset: Optional[int] = Field(default=0, ge=0)


class PowerQueryBolsInput(BaseModel):
    """
    Advanced BOL search. All filters are optional and combinable.
    Text fields support boolean operators (AND, OR, NOT) and wildcards (* ?).
    Numeric fields support range syntax: [min TO max], [min TO *], [* TO max].
    Dates use MM/DD/YYYY format.
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    page_size: Optional[int] = Field(
        default=20,
        description="Number of results to return per page (1-100).",
        ge=1,
        le=100,
    )
    offset: Optional[int] = Field(
        default=None,
        description="Zero-based result offset for pagination.",
        ge=0,
    )
    page: Optional[int] = Field(
        default=None,
        description="1-indexed page number. Takes precedence over offset.",
        ge=1,
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Filter BOLs on or after this date. Format: MM/DD/YYYY (e.g. '01/01/2023').",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Filter BOLs on or before this date. Format: MM/DD/YYYY (e.g. '12/31/2024'). Defaults to today.",
    )
    company: Optional[str] = Field(
        default=None,
        description="US company identifier/slug to filter by (e.g. 'ikea-supply').",
    )
    supplier: Optional[str] = Field(
        default=None,
        description="Overseas supplier identifier/slug to filter by (e.g. 'damco-india').",
    )
    product_description: Optional[str] = Field(
        default=None,
        description='Product description filter. Supports boolean operators and wildcards. '
                    'Examples: "LED modules", "cat toys OR dog toys", "shoes AND NOT leather".',
    )
    weight: Optional[str] = Field(
        default=None,
        description='Shipment weight filter. Supports ranges, e.g. "0 TO 15000" or "[500 TO *]".',
    )
    teu: Optional[str] = Field(
        default=None,
        description='TEU (twenty-foot equivalent unit) filter. Supports ranges, e.g. "* TO 2".',
    )
    company_total_shipments: Optional[str] = Field(
        default=None,
        description='Filter by total shipments the US company has made. Supports ranges: "500 TO *".',
    )
    supplier_total_shipments: Optional[str] = Field(
        default=None,
        description='Filter by total shipments the supplier has made. Supports ranges: "[* TO 500]".',
    )
    hs_code: Optional[str] = Field(
        default=None,
        description='HS tariff code filter. Supports wildcards: "7013*" or "7013* AND NOT 701391".',
    )
    entry_port: Optional[str] = Field(
        default=None,
        description='US port of entry. Supports boolean operators: "Houston, Tx" or "Los Angeles OR Long Beach".',
    )
    exit_port: Optional[str] = Field(
        default=None,
        description='Foreign port of origin. Example: "Pusan" or "Shanghai OR Yantian".',
    )
    internal_supplier: Optional[str] = Field(
        default=None,
        description='Filter for internal suppliers. Default: "false".',
    )
    supplier_country: Optional[str] = Field(
        default=None,
        description='Country of origin for supplier. Example: "Republic of Korea" or "China".',
    )
    notify_party: Optional[str] = Field(
        default=None,
        description='Notify party on the shipment. Supports boolean operators.',
    )
    last_visited_foreign_port: Optional[str] = Field(
        default=None,
        description='Last foreign port visited. Example: "Vancouver, BC".',
    )
    vessel_name: Optional[str] = Field(
        default=None,
        description='Name of the vessel. Example: "Seaspan Yangtze".',
    )
    carrier_scac_code: Optional[str] = Field(
        default=None,
        description='Carrier SCAC (Standard Carrier Alpha Code). Example: "MAEU" for Maersk.',
    )


class PowerQueryCompaniesInput(BaseModel):
    """Advanced search for US companies aggregated from BOL data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    page_size: Optional[int] = Field(default=20, ge=1, le=100)
    offset: Optional[int] = Field(default=None, ge=0)
    page: Optional[int] = Field(default=None, ge=1)
    start_date: Optional[str] = Field(
        default=None,
        description="Start date filter: MM/DD/YYYY.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End date filter: MM/DD/YYYY.",
    )
    company: Optional[str] = Field(
        default=None,
        description="Company name or identifier filter.",
    )
    supplier: Optional[str] = Field(
        default=None,
        description="Supplier identifier filter.",
    )
    product_description: Optional[str] = Field(
        default=None,
        description="Product description filter. Supports boolean operators and wildcards.",
    )
    supplier_country: Optional[str] = Field(
        default=None,
        description="Country of origin for supplier.",
    )
    entry_port: Optional[str] = Field(
        default=None,
        description="US port of entry.",
    )


class PowerQuerySuppliersInput(BaseModel):
    """Advanced search for overseas suppliers aggregated from BOL data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    page_size: Optional[int] = Field(default=20, ge=1, le=100)
    offset: Optional[int] = Field(default=None, ge=0)
    page: Optional[int] = Field(default=None, ge=1)
    start_date: Optional[str] = Field(
        default=None,
        description="Start date filter: MM/DD/YYYY.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End date filter: MM/DD/YYYY.",
    )
    company: Optional[str] = Field(
        default=None,
        description="US company identifier filter.",
    )
    supplier: Optional[str] = Field(
        default=None,
        description="Supplier name or identifier filter.",
    )
    product_description: Optional[str] = Field(
        default=None,
        description="Product description filter. Supports boolean operators and wildcards.",
    )
    supplier_country: Optional[str] = Field(
        default=None,
        description="Country of origin for supplier.",
    )
    exit_port: Optional[str] = Field(
        default=None,
        description="Foreign port of origin.",
    )


# ---------------------------------------------------------------------------
# Tools - Bills of Lading
# ---------------------------------------------------------------------------

@mcp.tool(name="importyeti_get_bol")
async def importyeti_get_bol(params: BolGetInput) -> str:
    """
    Retrieve a single US import bill of lading by its BOL number.

    Returns shipment metadata including BOL type, arrival date, entry port
    coordinates, master BOL number, and confidentiality flags.

    Args:
        params (BolGetInput):
            - number (str): BOL number (e.g. 'CCLLMILS17011590').

    Returns:
        str: JSON object with BOL details, or an error string.
    """
    try:
        data = await _get(f"/v1.0/bol/{params.number}")
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


# ---------------------------------------------------------------------------
# Tools - Companies
# ---------------------------------------------------------------------------

@mcp.tool(name="importyeti_search_companies")
async def importyeti_search_companies(params: CompanySearchInput) -> str:
    """
    Search for US importing companies by name.

    Returns a list of matching companies with their slugs/identifiers.
    Use the returned slug with importyeti_get_company or
    importyeti_get_company_bols for deeper lookups.

    Args:
        params (CompanySearchInput):
            - name (str): Company name to search (e.g. 'Walmart', 'Home Depot').

    Returns:
        str: JSON array of company matches, or an error string.
    """
    try:
        data = await _get("/v1.0/company/search", {"name": params.name})
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool(name="importyeti_get_company")
async def importyeti_get_company(params: CompanyGetInput) -> str:
    """
    Get full profile for a US importing company by its slug/identifier.

    Returns company overview including title, aliases, address, contact
    information, and shipment summary statistics.

    Args:
        params (CompanyGetInput):
            - company (str): Company slug (e.g. 'wal-mart', 'home-depot').
              Use importyeti_search_companies to find the correct slug.

    Returns:
        str: JSON object with company profile, or an error string.
    """
    try:
        data = await _get(f"/v1.0/company/{params.company}")
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool(name="importyeti_get_company_bols")
async def importyeti_get_company_bols(params: CompanyBolsInput) -> str:
    """
    Retrieve a paginated list of bills of lading for a specific US company.

    Args:
        params (CompanyBolsInput):
            - company (str): Company slug (e.g. 'wal-mart').
            - page_size (int): Results per page, 1-100 (default: 20).
            - offset (int): Pagination offset (default: 0).

    Returns:
        str: JSON object with BOL list and pagination metadata, or an error string.
    """
    try:
        data = await _get(
            f"/v1.0/company/{params.company}/bols",
            {"page_size": params.page_size, "offset": params.offset},
        )
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


# ---------------------------------------------------------------------------
# Tools - Suppliers
# ---------------------------------------------------------------------------

@mcp.tool(name="importyeti_search_suppliers")
async def importyeti_search_suppliers(params: SupplierSearchInput) -> str:
    """
    Search for overseas suppliers by name.

    Returns a list of matching suppliers with their slugs.

    Args:
        params (SupplierSearchInput):
            - name (str): Supplier name to search (e.g. 'Samsung', 'Yantian International').

    Returns:
        str: JSON array of supplier matches, or an error string.
    """
    try:
        data = await _get("/v1.0/supplier/search", {"name": params.name})
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool(name="importyeti_get_supplier")
async def importyeti_get_supplier(params: SupplierGetInput) -> str:
    """
    Get full profile for an overseas supplier by its slug/identifier.

    Args:
        params (SupplierGetInput):
            - supplier (str): Supplier slug. Use importyeti_search_suppliers to find it.

    Returns:
        str: JSON object with supplier profile, or an error string.
    """
    try:
        data = await _get(f"/v1.0/supplier/{params.supplier}")
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool(name="importyeti_get_supplier_bols")
async def importyeti_get_supplier_bols(params: SupplierBolsInput) -> str:
    """
    Retrieve a paginated list of bills of lading for a specific overseas supplier.

    Args:
        params (SupplierBolsInput):
            - supplier (str): Supplier slug.
            - page_size (int): Results per page, 1-100 (default: 20).
            - offset (int): Pagination offset (default: 0).

    Returns:
        str: JSON object with BOL list and pagination metadata, or an error string.
    """
    try:
        data = await _get(
            f"/v1.0/supplier/{params.supplier}/bols",
            {"page_size": params.page_size, "offset": params.offset},
        )
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


# ---------------------------------------------------------------------------
# Tools - Products
# ---------------------------------------------------------------------------

@mcp.tool(name="importyeti_search_product_suppliers")
async def importyeti_search_product_suppliers(params: ProductSuppliersInput) -> str:
    """
    Find overseas suppliers that ship a given product to the US.

    Args:
        params (ProductSuppliersInput):
            - product (str): Product name or keyword (e.g. 'LED modules', 'shoes').
            - page_size (int): Results per page, 1-100 (default: 20).
            - offset (int): Pagination offset (default: 0).

    Returns:
        str: JSON list of suppliers for this product, or an error string.
    """
    try:
        data = await _get(
            f"/v1.0/product/{params.product}/suppliers",
            {"page_size": params.page_size, "offset": params.offset},
        )
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool(name="importyeti_search_product_companies")
async def importyeti_search_product_companies(params: ProductCompaniesInput) -> str:
    """
    Find US companies that import a given product.

    Args:
        params (ProductCompaniesInput):
            - product (str): Product name or keyword (e.g. 'LED modules', 'shoes').
            - page_size (int): Results per page, 1-100 (default: 20).
            - offset (int): Pagination offset (default: 0).

    Returns:
        str: JSON list of US companies importing this product, or an error string.
    """
    try:
        data = await _get(
            f"/v1.0/product/{params.product}/companies",
            {"page_size": params.page_size, "offset": params.offset},
        )
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


# ---------------------------------------------------------------------------
# Tools - PowerQuery
# ---------------------------------------------------------------------------

@mcp.tool(name="importyeti_powerquery_bols")
async def importyeti_powerquery_bols(params: PowerQueryBolsInput) -> str:
    """
    Advanced search for US import bills of lading with flexible multi-field filtering.

    Supports boolean operators (AND, OR, NOT), wildcards (* ?), exact phrases,
    and range queries on numeric fields.

    Args:
        params (PowerQueryBolsInput): Any combination of:
            - page_size, offset, page: Pagination controls.
            - start_date, end_date: Date range (MM/DD/YYYY).
            - company: US company slug filter.
            - supplier: Overseas supplier slug filter.
            - product_description: Product keyword filter.
            - weight, teu: Shipment size filters.
            - hs_code: HS tariff code.
            - entry_port, exit_port: Port filters.
            - supplier_country: Supplier country of origin.
            - vessel_name, carrier_scac_code: Vessel/carrier filters.

    Returns:
        str: JSON with matching BOLs including requestCost and creditsRemaining,
             or an error string.
    """
    try:
        data = await _get("/v1.0/powerquery/us-import/bols", params.model_dump())
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool(name="importyeti_powerquery_companies")
async def importyeti_powerquery_companies(params: PowerQueryCompaniesInput) -> str:
    """
    Advanced search for US importing companies, aggregated from BOL data.

    Args:
        params (PowerQueryCompaniesInput): Any combination of:
            - page_size, offset, page: Pagination controls.
            - start_date, end_date: Date range (MM/DD/YYYY).
            - company, supplier: Entity filters.
            - product_description: Product keyword filter.
            - supplier_country: Supplier country filter.
            - entry_port: US port of entry filter.

    Returns:
        str: JSON with matching companies and aggregate shipment data,
             or an error string.
    """
    try:
        data = await _get("/v1.0/powerquery/us-import/companies", params.model_dump())
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool(name="importyeti_powerquery_suppliers")
async def importyeti_powerquery_suppliers(params: PowerQuerySuppliersInput) -> str:
    """
    Advanced search for overseas suppliers, aggregated from BOL data.

    Args:
        params (PowerQuerySuppliersInput): Any combination of:
            - page_size, offset, page: Pagination controls.
            - start_date, end_date: Date range (MM/DD/YYYY).
            - company, supplier: Entity filters.
            - product_description: Product keyword filter.
            - supplier_country: Supplier country filter.
            - exit_port: Foreign port of origin filter.

    Returns:
        str: JSON with matching suppliers and aggregate data, or an error string.
    """
    try:
        data = await _get("/v1.0/powerquery/us-import/suppliers", params.model_dump())
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


# ---------------------------------------------------------------------------
# Tools - Database
# ---------------------------------------------------------------------------

@mcp.tool(name="importyeti_database_updated")
async def importyeti_database_updated() -> str:
    """
    Get the date when the ImportYeti database was last updated.

    Returns:
        str: JSON with the last updated date, or an error string.
    """
    try:
        data = await _get("/v1.0/database-updated")
        return _dumps(data)
    except Exception as e:
        return _fmt_error(e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
