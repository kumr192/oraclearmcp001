"""
Oracle Fusion AR MCP Server
Streamable HTTP transport for Railway deployment.
"""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import httpx
import json
import base64
import os
from datetime import datetime, date

# Initialize MCP server with stateless HTTP mode for Railway
mcp = FastMCP(
    "oracle_ar_mcp",
    stateless_http=True,
    json_response=True
)


# ============================================================================
# Input Models
# ============================================================================

class AuthInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")


class InvoiceLookupInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: Optional[str] = Field(default=None, description="Filter by customer account ID")
    invoice_number: Optional[str] = Field(default=None, description="Filter by invoice number")
    limit: int = Field(default=25, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ReceiptLookupInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: Optional[str] = Field(default=None, description="Filter by customer account ID")
    receipt_number: Optional[str] = Field(default=None, description="Filter by receipt number")
    limit: int = Field(default=25, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class CustomerSummaryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: str = Field(..., description="Customer account ID")


class AgingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: Optional[str] = Field(default=None)
    limit: int = Field(default=25, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ============================================================================
# Helpers
# ============================================================================

def _build_auth_header(username: str, password: str) -> str:
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


async def _make_request(base_url: str, auth_header: str, endpoint: str, params: dict = None) -> dict:
    url = f"{base_url.rstrip('/')}/fscmRestApi/resources/11.13.18.05/{endpoint}"
    async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
        response = await client.get(url, headers={"Authorization": auth_header, "Content-Type": "application/json"}, params=params or {})
        response.raise_for_status()
        return response.json()


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 401:
            return json.dumps({"error": "Authentication failed"})
        elif status == 403:
            return json.dumps({"error": "Permission denied"})
        elif status == 404:
            return json.dumps({"error": "Resource not found"})
        return json.dumps({"error": f"API error {status}"})
    return json.dumps({"error": str(e)})


# ============================================================================
# Tools
# ============================================================================

@mcp.tool(name="oracle_ar_test_connection")
async def test_connection(params: AuthInput) -> str:
    """Test connection to Oracle Fusion."""
    auth_header = _build_auth_header(params.username, params.password)
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            url = f"{params.base_url.rstrip('/')}/fscmRestApi/resources/11.13.18.05/receivablesInvoices?limit=1"
            response = await client.get(url, headers={"Authorization": auth_header})
            response.raise_for_status()
        return json.dumps({"status": "connected", "message": "Credentials valid"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="oracle_ar_list_invoices")
async def list_invoices(params: InvoiceLookupInput) -> str:
    """List AR invoices from Oracle Fusion."""
    auth_header = _build_auth_header(params.username, params.password)
    query_params = {"limit": params.limit, "offset": params.offset}
    filters = []
    if params.customer_account_id:
        filters.append(f"CustomerAccountId={params.customer_account_id}")
    if params.invoice_number:
        filters.append(f"TransactionNumber={params.invoice_number}")
    if filters:
        query_params["q"] = ";".join(filters)
    try:
        data = await _make_request(params.base_url, auth_header, "receivablesInvoices", query_params)
        invoices = [{"invoice_number": inv.get("TransactionNumber"), "customer_name": inv.get("BillToCustomerName"), "amount": inv.get("EnteredAmount"), "balance_due": inv.get("BalanceDue"), "due_date": inv.get("DueDate"), "status": inv.get("Status")} for inv in data.get("items", [])]
        return json.dumps({"invoices": invoices, "count": len(invoices), "has_more": data.get("hasMore", False)}, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="oracle_ar_list_receipts")
async def list_receipts(params: ReceiptLookupInput) -> str:
    """List payment receipts from Oracle Fusion."""
    auth_header = _build_auth_header(params.username, params.password)
    query_params = {"limit": params.limit, "offset": params.offset}
    filters = []
    if params.customer_account_id:
        filters.append(f"CustomerAccountId={params.customer_account_id}")
    if params.receipt_number:
        filters.append(f"ReceiptNumber={params.receipt_number}")
    if filters:
        query_params["q"] = ";".join(filters)
    try:
        data = await _make_request(params.base_url, auth_header, "standardReceipts", query_params)
        receipts = [{"receipt_number": r.get("ReceiptNumber"), "customer_name": r.get("CustomerName"), "amount": r.get("Amount"), "receipt_date": r.get("ReceiptDate"), "status": r.get("Status")} for r in data.get("items", [])]
        return json.dumps({"receipts": receipts, "count": len(receipts), "has_more": data.get("hasMore", False)}, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="oracle_ar_get_customer_summary")
async def get_customer_summary(params: CustomerSummaryInput) -> str:
    """Get AR summary for a customer."""
    auth_header = _build_auth_header(params.username, params.password)
    try:
        inv_data = await _make_request(params.base_url, auth_header, "receivablesInvoices", {"q": f"CustomerAccountId={params.customer_account_id}", "limit": 500})
        invoices = inv_data.get("items", [])
        total_invoiced = sum(inv.get("EnteredAmount") or 0 for inv in invoices)
        total_balance = sum(inv.get("BalanceDue") or 0 for inv in invoices)
        customer_name = invoices[0].get("BillToCustomerName") if invoices else None
        return json.dumps({"customer_account_id": params.customer_account_id, "customer_name": customer_name, "total_invoiced": round(total_invoiced, 2), "outstanding_balance": round(total_balance, 2), "invoice_count": len(invoices)}, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="oracle_ar_get_aging_summary")
async def get_aging_summary(params: AgingInput) -> str:
    """Get aging summary of open invoices."""
    auth_header = _build_auth_header(params.username, params.password)
    query_params = {"limit": params.limit, "offset": params.offset}
    if params.customer_account_id:
        query_params["q"] = f"CustomerAccountId={params.customer_account_id}"
    try:
        data = await _make_request(params.base_url, auth_header, "receivablesInvoices", query_params)
        today = date.today()
        buckets = {"current": 0, "1_30": 0, "31_60": 0, "61_90": 0, "over_90": 0}
        for inv in data.get("items", []):
            balance = inv.get("BalanceDue") or 0
            if balance <= 0:
                continue
            due_str = inv.get("DueDate")
            if not due_str:
                continue
            try:
                due = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()
                days = (today - due).days
                if days <= 0:
                    buckets["current"] += balance
                elif days <= 30:
                    buckets["1_30"] += balance
                elif days <= 60:
                    buckets["31_60"] += balance
                elif days <= 90:
                    buckets["61_90"] += balance
                else:
                    buckets["over_90"] += balance
            except:
                pass
        return json.dumps({"aging_buckets": {k: round(v, 2) for k, v in buckets.items()}, "total_outstanding": round(sum(buckets.values()), 2)}, indent=2)
    except Exception as e:
        return _handle_error(e)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
