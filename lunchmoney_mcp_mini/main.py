"""
Lunch Money MCP Server

An MCP server for the Lunch Money API with optimized, minimal responses
to prevent context window bloat.
"""

import calendar
import functools
import os
from typing import Any, Literal

from fastmcp import FastMCP
from requests_openapi import Client, Server


def handle_auth_errors(func):
    """Decorator to handle authentication errors consistently."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "401" in str(e):
                raise ValueError(
                    "Authentication failed. Please check your "
                    "LUNCHMONEY_API_TOKEN environment variable."
                )
            raise

    return wrapper


# Initialize FastMCP server
mcp = FastMCP("Lunch Money")

# Base URL for Lunch Money API v2
API_BASE_URL = "https://api.lunchmoney.dev/v2"

# Cached API client
_client: Client | None = None


def _get_categories() -> dict[int, str]:
    """Fetch all categories and return mapping of id -> name."""
    client = get_api_client()
    response = client.getAllCategories(format="flattened")
    data = response.json()
    return {c["id"]: c["name"] for c in data["categories"]}


def get_api_client() -> Client:
    """Get an authenticated Lunch Money API client (cached)."""
    global _client

    if _client is not None:
        return _client

    token = os.getenv("LUNCHMONEY_API_TOKEN")
    if not token:
        raise ValueError(
            "LUNCHMONEY_API_TOKEN environment variable not set. "
            "Get your API token from https://my.lunchmoney.app/developers"
        )

    # Load the OpenAPI spec
    spec_path = os.path.join(os.path.dirname(__file__), "openapi.yaml")

    _client = Client()
    _client.load_spec_from_file(spec_path)
    _client.set_server(Server(url=API_BASE_URL))
    _client.requestor.headers.update({"Authorization": f"Bearer {token}"})

    return _client


@mcp.tool()
@handle_auth_errors
def get_current_user() -> dict[str, Any]:
    """Get details about the current Lunch Money user.

    Returns user information including:
    - name: User's full name
    - email: User's email address
    - user_id: Unique user identifier
    - account_id: Unique account identifier
    - budget_name: Name of the budget
    - primary_currency: Primary currency code (e.g., 'usd')
    - api_key_label: Label for the API key being used (or null)

    Useful for verifying authentication and understanding the account context.
    """
    client = get_api_client()

    # Call the /me endpoint
    response = client.getMe()
    data = response.json()

    # Return a minimal, focused subset of the data
    return {
        "name": data["name"],
        "email": data["email"],
        "user_id": data["id"],
        "account_id": data["account_id"],
        "budget_name": data["budget_name"],
        "primary_currency": data["primary_currency"],
        "api_key_label": data["api_key_label"],
    }


@mcp.tool()
@handle_auth_errors
def get_transactions(
    start_date: str,
    end_date: str | None = None,
    category_name: str | None = None,
    tag_id: int | None = None,
    status: Literal["reviewed", "unreviewed", "delete_pending"] | None = None,
    is_pending: bool | None = None,
    manual_account_id: int | None = None,
    plaid_account_id: int | None = None,
    recurring_id: int | None = None,
    include_pending: bool | None = None,
    limit: int = 100,
    offset: int | None = None,
    include_aggregates: bool = True,
) -> dict[str, Any]:
    """Get transactions for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format (required)
        end_date: End date in YYYY-MM-DD format (defaults to last day of start_date's month)
        category_name: Filter by category name (e.g., "Groceries", "Dining Out")
        tag_id: Filter by tag ID
        status: Filter by transaction status (reviewed, unreviewed, delete_pending)
        is_pending: Filter by pending status
        manual_account_id: Filter by manual account ID
        plaid_account_id: Filter by plaid account ID
        recurring_id: Filter by recurring item ID
        include_pending: Include pending transactions (ignored if is_pending is set)
        limit: Maximum number of transactions to return (1-2000, default 100)
        offset: Pagination offset
        include_aggregates: If True, calculates totals per category for full date range (respects all filters)

    Returns:
        Structured JSON where transactions include category names instead of IDs,
        has_more pagination flag, and optionally category aggregates
    """
    client = get_api_client()

    category_names = _get_categories()

    category_id = None
    if category_name:
        name_to_id = {name: id for id, name in category_names.items()}
        category_id = name_to_id.get(category_name)
        if category_id is None:
            raise ValueError(f"Category '{category_name}' not found")

    # Calculate default end_date if not provided (last day of start_date's month)
    if end_date is None:
        year, month = map(int, start_date.split("-")[:2])
        _, last_day = calendar.monthrange(year, month)
        end_date = f"{year}-{month:02d}-{last_day}"

    # Build params with only non-None values
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "limit": min(limit, 2000),
    }
    # Add optional filters (skip None values)
    optional_params = {
        "category_id": category_id,
        "tag_id": tag_id,
        "status": status,
        "is_pending": is_pending,
        "manual_account_id": manual_account_id,
        "plaid_account_id": plaid_account_id,
        "recurring_id": recurring_id,
        "include_pending": include_pending or None,
        "offset": offset,
    }
    params.update({k: v for k, v in optional_params.items() if v is not None})

    # Call API
    response = client.getAllTransactions(**params)
    data = response.json()

    result = {
        "transactions": [
            {
                "id": t["id"],
                "date": t["date"],
                "amount": t["amount"],
                "payee": t["payee"],
                "category": (
                    category_names.get(t["category_id"], "Uncategorized")
                    if t["category_id"]
                    else "Uncategorized"
                ),
                "status": t["status"],
                "is_pending": t["is_pending"],
            }
            for t in data["transactions"]
        ],
        "has_more": data["has_more"],
    }

    # Add aggregates if requested
    if include_aggregates:
        # Build params for full range (same filters, no limit/offset)
        agg_params = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": 2000,
        }
        agg_params.update(
            {
                k: v
                for k, v in optional_params.items()
                if k not in ("offset", "limit") and v is not None
            }
        )

        # Fetch all transactions for aggregation
        agg_response = client.getAllTransactions(**agg_params)
        agg_data = agg_response.json()

        # Build category aggregates
        category_totals: dict[int | None, dict] = {}
        total_count = 0
        total_amount = 0.0

        for t in agg_data["transactions"]:
            cat_id = t["category_id"]
            if cat_id not in category_totals:
                category_totals[cat_id] = {"count": 0, "total_amount": 0.0}
            category_totals[cat_id]["count"] += 1
            category_totals[cat_id]["total_amount"] += float(t["amount"])
            total_count += 1
            total_amount += float(t["amount"])

        # Build aggregates array with category names, sorted by total_amount descending
        by_category = []
        for cat_id, stats in category_totals.items():
            cat_name = (
                category_names.get(cat_id, "Uncategorized")
                if cat_id
                else "Uncategorized"
            )
            by_category.append(
                {
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "count": stats["count"],
                    "total_amount": f"{stats['total_amount']:.4f}",
                }
            )

        result["aggregates"] = {
            "by_category": sorted(
                by_category, key=lambda x: float(x["total_amount"]), reverse=True
            ),
            "total_count": total_count,
            "total_amount": f"{total_amount:.4f}",
        }

    return result


@mcp.tool()
@handle_auth_errors
def get_transaction(transaction_id: int) -> dict[str, Any]:
    """Get details about a specific transaction.

    Retrieves the full details of a single transaction by its ID, including:
    - Core data: id, date, amount, currency, payee, original_name
    - Category: category name (and category_id for reference)
    - Accounts: manual_account_id, plaid_account_id, recurring_id
    - Metadata: plaid_metadata, custom_metadata, files (if available)
    - Grouping/splitting: is_split_parent, split_parent_id, is_group_parent, group_parent_id, children
    - Timestamps: created_at, updated_at
    - Status: status, is_pending, source, external_id, tag_ids, notes

    Args:
        transaction_id: ID of the transaction to retrieve

    Returns:
        Full transaction object with all available fields
    """
    client = get_api_client()

    response = client.getTransactionById(id=transaction_id)
    data = response.json()

    category_names = _get_categories()

    if data.get("category_id"):
        data["category"] = category_names.get(data["category_id"], "Uncategorized")
    else:
        data["category"] = "Uncategorized"

    return data


@mcp.tool()
def add_numbers(numbers: list[float]) -> dict[str, Any]:
    """Helper tool for adding numbers together.

    LLMs should use this tool for arithmetic operations to avoid calculation errors.
    This is especially useful for summing expenses, calculating totals, or performing
    any arithmetic where precision matters.

    Args:
        numbers: List of numbers to add together. Can include negative values for subtraction.

    Returns:
        Dictionary with the sum rounded to 2 decimal places to avoid floating-point precision issues.
    """
    total = sum(numbers) if numbers else 0.0
    rounded_total = round(total, 2)

    return {
        "sum": rounded_total,
        "input_count": len(numbers),
    }


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
