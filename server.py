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

# Configuration - stored per-request via auth tool
# In stateless mode, auth must be passed with each request or stored externally
CONFIG = {
    "base_url": None,
    "auth_header": None,
    "authenticated": False
}


# ============================================================================
# Input Models
# ============================================================================

class AuthInput(BaseModel):
    """Input for Oracle Fusion authentication."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    base_url: str = Field(
        ..., 
        description="Oracle Fusion base URL (e.g., 'https://eqjz.ds-fa.oraclepdemos.com')"
    )
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")


class InvoiceLookupInput(BaseModel):
    """Input for invoice queries."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: Optional[str] = Field(default=None, description="Filter by customer account ID")
    invoice_number: Optional[str] = Field(default=None, description="Filter by invoice number")
    status: Optional[str] = Field(default=None, description="Filter by status (e.g., 'Open', 'Closed')")
    limit: int = Field(default=25, description="Max results to return", ge=1, le=500)
    offset: int = Field(default=0, description="Offset for pagination", ge=0)


class ReceiptLookupInput(BaseModel):
    """Input for receipt queries."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: Optional[str] = Field(default=None, description="Filter by customer account ID")
    receipt_number: Optional[str] = Field(default=None, description="Filter by receipt number")
    limit: int = Field(default=25, description="Max results to return", ge=1, le=500)
    offset: int = Field(default=0, description="Offset for pagination", ge=0)


class CustomerActivityInput(BaseModel):
    """Input for customer account activity queries."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: Optional[str] = Field(default=None, description="Filter by customer account ID")
    limit: int = Field(default=25, description="Max results to return", ge=1, le=500)
    offset: int = Field(default=0, description="Offset for pagination", ge=0)


class CustomerSummaryInput(BaseModel):
    """Input for customer AR summary."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: str = Field(..., description="Customer account ID (required)")


class AgingInput(BaseModel):
    """Input for aging summary."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    base_url: str = Field(..., description="Oracle Fusion base URL")
    username: str = Field(..., description="Oracle Fusion username")
    password: str = Field(..., description="Oracle Fusion password")
    customer_account_id: Optional[str] = Field(default=None, description="Filter by customer account ID")
    limit: int = Field(default=25, description="Max results to return", ge=1, le=500)
    offset: int = Field(default=0, description="Offset for pagination", ge=0)


# ============================================================================
# HTTP Client Helpers
# ============================================================================

def _build_auth_header(username: str, password: str) -> str:
    """Build Basic Auth header."""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


async def _make_request(base_url: str, auth_header: str, endpoint: str, params: dict = None) -> dict:
    """Make authenticated request to Oracle Fusion API."""
    url = f"{base_url.rstrip('/')}/fscmRestApi/resources/11.13.18.05/{endpoint}"
    
    async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
        response = await client.get(
            url,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json"
            },
            params=params or {}
        )
        response.raise_for_status()
        return response.json()


def _handle_api_error(e: Exception) -> str:
    """Format API errors consistently."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 401:
            return json.dumps({"error": "Authentication failed. Check username and password."})
        elif status == 403:
            return json.dumps({"error": "Permission denied. Check your Oracle Fusion role permissions."})
        elif status == 404:
            return json.dumps({"error": "Resource not found. Check the endpoint or filter parameters."})
        elif status == 429:
            return json.dumps({"error": "Rate limit exceeded. Wait before retrying."})
        else:
            try:
                detail = e.response.json()
            except:
                detail = e.response.text
            return json.dumps({"error": f"API error {status}", "detail": detail})
    elif isinstance(e, httpx.TimeoutException):
        return json.dumps({"error": "Request timed out. Oracle Fusion may be slow or unreachable."})
    elif isinstance(e, httpx.ConnectError):
        return json.dumps({"error": "Connection failed. Check the base URL and network connectivity."})
    return json.dumps({"error": f"Unexpected error: {type(e).__name__}: {str(e)}"})


# ============================================================================
# Tools
# ============================================================================

@mcp.tool(
    name="oracle_ar_test_connection",
    annotations={
        "title": "Test Oracle Fusion Connection",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def test_connection(params: AuthInput) -> str:
    """Test connection to Oracle Fusion AR APIs.
    
    Validates credentials by making a minimal API request.
    Use this before other operations to verify connectivity.
    """
    auth_header = _build_auth_header(params.username, params.password)
    base_url = params.base_url.rstrip("/")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            test_url = f"{base_url}/fscmRestApi/resources/11.13.18.05/receivablesInvoices?limit=1"
            response = await client.get(
                test_url,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return json.dumps({"error": "Authentication failed. Check username and password."})
        return _handle_api_error(e)
    except Exception as e:
        return _handle_api_error(e)
    
    return json.dumps({
        "status": "connected",
        "base_url": base_url,
        "message": "Successfully connected to Oracle Fusion. Credentials are valid."
    })


@mcp.tool(
    name="oracle_ar_list_invoices",
    annotations={
        "title": "List Receivables Invoices",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def list_invoices(params: InvoiceLookupInput) -> str:
    """List receivables invoices from Oracle Fusion.
    
    Returns invoice details including customer, amounts, due dates, and status.
    Supports filtering by customer account, invoice number, and status.
    """
    auth_header = _build_auth_header(params.username, params.password)
    base_url = params.base_url.rstrip("/")
    
    query_params = {"limit": params.limit, "offset": params.offset}
    
    filters = []
    if params.customer_account_id:
        filters.append(f"CustomerAccountId={params.customer_account_id}")
    if params.invoice_number:
        filters.append(f"TransactionNumber={params.invoice_number}")
    
    if filters:
        query_params["q"] = ";".join(filters)
    
    try:
        data = await _make_request(base_url, auth_header, "receivablesInvoices", query_params)
        
        items = data.get("items", [])
        
        invoices = []
        for inv in items:
            invoices.append({
                "invoice_id": inv.get("CustomerTransactionId"),
                "invoice_number": inv.get("TransactionNumber"),
                "customer_account_id": inv.get("CustomerAccountId"),
                "customer_name": inv.get("BillToCustomerName"),
                "invoice_date": inv.get("TransactionDate"),
                "due_date": inv.get("DueDate"),
                "amount": inv.get("EnteredAmount"),
                "balance_due": inv.get("BalanceDue"),
                "currency": inv.get("EnteredCurrencyCode"),
                "status": inv.get("Status"),
                "business_unit": inv.get("BusinessUnit"),
            })
        
        return json.dumps({
            "invoices": invoices,
            "count": len(invoices),
            "total_amount": sum(i.get("amount") or 0 for i in invoices),
            "total_balance_due": sum(i.get("balance_due") or 0 for i in invoices),
            "has_more": data.get("hasMore", False),
            "offset": params.offset,
            "limit": params.limit
        }, indent=2)
        
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="oracle_ar_list_receipts",
    annotations={
        "title": "List Standard Receipts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def list_receipts(params: ReceiptLookupInput) -> str:
    """List standard receipts (payments) from Oracle Fusion.
    
    Returns receipt details including amounts, dates, and payment methods.
    Supports filtering by customer account and receipt number.
    """
    auth_header = _build_auth_header(params.username, params.password)
    base_url = params.base_url.rstrip("/")
    
    query_params = {"limit": params.limit, "offset": params.offset}
    
    filters = []
    if params.customer_account_id:
        filters.append(f"CustomerAccountId={params.customer_account_id}")
    if params.receipt_number:
        filters.append(f"ReceiptNumber={params.receipt_number}")
    
    if filters:
        query_params["q"] = ";".join(filters)
    
    try:
        data = await _make_request(base_url, auth_header, "standardReceipts", query_params)
        
        items = data.get("items", [])
        
        receipts = []
        for rcpt in items:
            receipts.append({
                "receipt_id": rcpt.get("CashReceiptId"),
                "receipt_number": rcpt.get("ReceiptNumber"),
                "customer_account_id": rcpt.get("CustomerAccountId"),
                "customer_name": rcpt.get("CustomerName"),
                "receipt_date": rcpt.get("ReceiptDate"),
                "amount": rcpt.get("Amount"),
                "currency": rcpt.get("CurrencyCode"),
                "status": rcpt.get("Status"),
                "payment_method": rcpt.get("PaymentMethod"),
                "business_unit": rcpt.get("BusinessUnit"),
            })
        
        return json.dumps({
            "receipts": receipts,
            "count": len(receipts),
            "total_collected": sum(r.get("amount") or 0 for r in receipts),
            "has_more": data.get("hasMore", False),
            "offset": params.offset,
            "limit": params.limit
        }, indent=2)
        
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="oracle_ar_list_customer_activities",
    annotations={
        "title": "List Customer Account Activities",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def list_customer_activities(params: CustomerActivityInput) -> str:
    """List customer account activities from Oracle Fusion.
    
    Shows transaction history and account movements.
    """
    auth_header = _build_auth_header(params.username, params.password)
    base_url = params.base_url.rstrip("/")
    
    query_params = {"limit": params.limit, "offset": params.offset}
    
    if params.customer_account_id:
        query_params["q"] = f"CustomerAccountId={params.customer_account_id}"
    
    try:
        data = await _make_request(base_url, auth_header, "receivablesCustomerAccountActivities", query_params)
        
        items = data.get("items", [])
        
        activities = []
        for act in items:
            activities.append({
                "activity_id": act.get("ActivityId"),
                "customer_account_id": act.get("CustomerAccountId"),
                "customer_name": act.get("CustomerName"),
                "transaction_number": act.get("TransactionNumber"),
                "transaction_type": act.get("TransactionType"),
                "transaction_date": act.get("TransactionDate"),
                "amount": act.get("Amount"),
                "currency": act.get("CurrencyCode"),
                "status": act.get("Status"),
            })
        
        return json.dumps({
            "activities": activities,
            "count": len(activities),
            "has_more": data.get("hasMore", False),
            "offset": params.offset,
            "limit": params.limit
        }, indent=2)
        
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="oracle_ar_get_customer_summary",
    annotations={
        "title": "Get Customer AR Summary",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def get_customer_summary(params: CustomerSummaryInput) -> str:
    """Get a complete AR summary for a specific customer.
    
    Aggregates invoices and receipts to show total invoiced, paid, and outstanding balance.
    """
    auth_header = _build_auth_header(params.username, params.password)
    base_url = params.base_url.rstrip("/")
    customer_id = params.customer_account_id
    
    try:
        inv_data = await _make_request(
            base_url, auth_header,
            "receivablesInvoices", 
            {"q": f"CustomerAccountId={customer_id}", "limit": 500}
        )
        invoices = inv_data.get("items", [])
        
        rcpt_data = await _make_request(
            base_url, auth_header,
            "standardReceipts",
            {"q": f"CustomerAccountId={customer_id}", "limit": 500}
        )
        receipts = rcpt_data.get("items", [])
        
        total_invoiced = sum(inv.get("EnteredAmount") or 0 for inv in invoices)
        total_balance_due = sum(inv.get("BalanceDue") or 0 for inv in invoices)
        total_paid = sum(rcpt.get("Amount") or 0 for rcpt in receipts)
        
        customer_name = None
        if invoices:
            customer_name = invoices[0].get("BillToCustomerName")
        elif receipts:
            customer_name = receipts[0].get("CustomerName")
        
        open_invoices = [i for i in invoices if (i.get("BalanceDue") or 0) > 0]
        
        invoice_summaries = []
        for inv in invoices:
            invoice_summaries.append({
                "invoice_number": inv.get("TransactionNumber"),
                "invoice_date": inv.get("TransactionDate"),
                "due_date": inv.get("DueDate"),
                "amount": inv.get("EnteredAmount"),
                "balance_due": inv.get("BalanceDue"),
                "status": inv.get("Status"),
            })
        
        receipt_summaries = []
        for rcpt in receipts:
            receipt_summaries.append({
                "receipt_number": rcpt.get("ReceiptNumber"),
                "receipt_date": rcpt.get("ReceiptDate"),
                "amount": rcpt.get("Amount"),
                "payment_method": rcpt.get("PaymentMethod"),
            })
        
        return json.dumps({
            "customer": {
                "customer_account_id": customer_id,
                "customer_name": customer_name,
            },
            "summary": {
                "total_invoiced": round(total_invoiced, 2),
                "total_paid": round(total_paid, 2),
                "outstanding_balance": round(total_balance_due, 2),
                "invoice_count": len(invoices),
                "open_invoice_count": len(open_invoices),
                "receipt_count": len(receipts),
            },
            "invoices": invoice_summaries,
            "receipts": receipt_summaries,
        }, indent=2)
        
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="oracle_ar_get_aging_summary",
    annotations={
        "title": "Get AR Aging Summary",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def get_aging_summary(params: AgingInput) -> str:
    """Get an aging summary of open invoices.
    
    Buckets outstanding invoices by age: Current, 1-30 days, 31-60 days, 61-90 days, 90+ days.
    """
    auth_header = _build_auth_header(params.username, params.password)
    base_url = params.base_url.rstrip("/")
    
    query_params = {"limit": params.limit, "offset": params.offset}
    
    filters = []
    if params.customer_account_id:
        filters.append(f"CustomerAccountId={params.customer_account_id}")
    
    if filters:
        query_params["q"] = ";".join(filters)
    
    try:
        data = await _make_request(base_url, auth_header, "receivablesInvoices", query_params)
        invoices = data.get("items", [])
        
        today = date.today()
        aging_buckets = {
            "current": {"count": 0, "amount": 0},
            "1_30_days": {"count": 0, "amount": 0},
            "31_60_days": {"count": 0, "amount": 0},
            "61_90_days": {"count": 0, "amount": 0},
            "over_90_days": {"count": 0, "amount": 0},
        }
        
        aged_invoices = []
        
        for inv in invoices:
            balance = inv.get("BalanceDue") or 0
            if balance <= 0:
                continue
            
            due_date_str = inv.get("DueDate")
            if not due_date_str:
                continue
            
            try:
                due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).date()
            except:
                continue
            
            days_past_due = (today - due_date).days
            
            if days_past_due <= 0:
                bucket = "current"
            elif days_past_due <= 30:
                bucket = "1_30_days"
            elif days_past_due <= 60:
                bucket = "31_60_days"
            elif days_past_due <= 90:
                bucket = "61_90_days"
            else:
                bucket = "over_90_days"
            
            aging_buckets[bucket]["count"] += 1
            aging_buckets[bucket]["amount"] += balance
            
            aged_invoices.append({
                "invoice_number": inv.get("TransactionNumber"),
                "customer_name": inv.get("BillToCustomerName"),
                "due_date": due_date_str,
                "days_past_due": max(0, days_past_due),
                "balance_due": balance,
                "aging_bucket": bucket,
            })
        
        aged_invoices.sort(key=lambda x: x["days_past_due"], reverse=True)
        
        return json.dumps({
            "aging_buckets": {
                k: {"count": v["count"], "amount": round(v["amount"], 2)}
                for k, v in aging_buckets.items()
            },
            "total_outstanding": round(sum(v["amount"] for v in aging_buckets.values()), 2),
            "total_open_invoices": sum(v["count"] for v in aging_buckets.values()),
            "invoices": aged_invoices,
            "has_more": data.get("hasMore", False),
        }, indent=2)
        
    except Exception as e:
        return _handle_api_error(e)


# Health check endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "oracle_ar_mcp"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
