# Lunch Money MCP Server

A Model Context Protocol (MCP) server for the [Lunch Money](https://lunchmoney.app) API v2, designed with minimal response sizes to prevent context window bloat.



## Features

- **Optimized responses**: Concise, formatted output to minimize token usage
- **Simple authentication**: Uses environment variable for API token
- **Type-safe**: Built with modern Python type hints
- **Easy to extend**: Add more endpoints one at a time

## Currently Supported Endpoints

- `add_numbers` - Helper tool for arithmetic operations
- `get_current_user` - Get information about the authenticated user (`GET /me`)
- `get_transaction` - Get details about a specific transaction by ID (`GET /transactions/{id}`)
- `get_transactions` - List transactions for a date range (`GET /transactions`)

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd lunchmoney-mcp-mini
```

2. Install dependencies using [uv](https://github.com/astral-sh/uv):
```bash
uv sync
```

## Configuration

### Get Your API Token

1. Log in to [Lunch Money](https://my.lunchmoney.app)
2. Go to the [Developers page](https://my.lunchmoney.app/developers)
3. Create a new API token or use an existing one

### Set Environment Variable

```bash
export LUNCHMONEY_API_TOKEN="your-api-token-here"
```

Or create a `.env` file (not committed to git):
```
LUNCHMONEY_API_TOKEN=your-api-token-here
```

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "lunchmoney-mini": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/lunchmoney-mcp-mini",
        "run",
        "lunchmoney_mcp_mini/main.py"
      ],
      "env": {
        "LUNCHMONEY_API_TOKEN": "your-api-token-here"
      }
    }
  }
}
```

### Standalone Testing

```bash
# Make sure LUNCHMONEY_API_TOKEN is set
uv run lunchmoney_mcp_mini/main.py
```

## Available Tools

### `add_numbers`

Helper tool for performing arithmetic operations with precise decimal handling to avoid floating-point precision issues.

**Parameters:**
- `numbers` (required): List of numbers to add together. Can include negative values for subtraction.

**Returns:**
- `sum`: Sum rounded to 2 decimal places
- `input_count`: Number of values provided

**Example output:**
```json
{
  "sum": 123.45,
  "input_count": 3
}
```

### `get_current_user`

Get details about the authenticated Lunch Money user.

**Returns:**
- `name`: User's full name
- `email`: User's email address
- `user_id`: Unique user identifier
- `account_id`: Unique account identifier
- `budget_name`: Name of the budget
- `primary_currency`: Primary currency code (e.g., 'usd')
- `api_key_label`: Label for the API key being used

**Example output:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "user_id": 12345,
  "account_id": 67890,
  "budget_name": "Family budget",
  "primary_currency": "usd",
  "api_key_label": "Development key"
}
```

### `get_transaction`

Get full details about a specific transaction by its ID.

**Parameters:**
- `transaction_id` (required): ID of the transaction to retrieve

**Returns:**
Complete transaction object with all available fields including:
- Core data: id, date, amount, currency, payee, original_name
- Category/accounts: category_id, manual_account_id, plaid_account_id, recurring_id
- Metadata: plaid_metadata, custom_metadata, files (if any)
- Grouping/splitting: is_split_parent, split_parent_id, is_group_parent, group_parent_id, children
- Timestamps: created_at, updated_at
- Status: status, is_pending, source, external_id, tag_ids, notes

**Example output:**
```json
{
  "id": 2112150655,
  "date": "2024-07-28",
  "amount": -45.50,
  "currency": "USD",
  "payee": "Whole Foods",
  "original_name": "WHOLE FOODS #1234",
  "category_id": 82,
  "status": "reviewed",
  "is_pending": false,
  "created_at": "2024-07-28T12:34:56.789Z",
  "updated_at": "2024-07-28T12:34:56.789Z"
}
```

### `get_transactions`

List transactions within a specified date range.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format. Defaults to last day of start_date's month
- `category_id` (optional): Filter by category ID
- `tag_id` (optional): Filter by tag ID
- `status` (optional): Filter by status ("reviewed", "unreviewed", "delete_pending")
- `is_pending` (optional): Filter by pending status
- `manual_account_id` (optional): Filter by manual account ID
- `plaid_account_id` (optional): Filter by plaid account ID
- `recurring_id` (optional): Filter by recurring item ID
- `include_pending` (optional): Include pending transactions
- `limit` (optional): Maximum number of transactions (1-2000, default 100)
- `offset` (optional): Pagination offset
- `include_aggregates` (optional): If True, calculates totals per category for full date range (respects all filters)

**Returns:**
- `transactions`: Array of transaction objects
- `has_more`: Boolean indicating if more transactions are available
- `aggregates` (optional): Category totals and counts when `include_aggregates=True`

**Transaction fields:**
- `id`: Transaction ID
- `date`: Transaction date (YYYY-MM-DD)
- `amount`: Transaction amount (numeric string)
- `payee`: Payee name
- `category_id`: Category ID
- `status`: Transaction status
- `is_pending`: Pending status

**Aggregates fields (when `include_aggregates=True`):**
- `by_category`: Array sorted by `total_amount` descending, each with:
  - `category_id`: Category ID (or null for uncategorized)
  - `category_name`: Category name
  - `count`: Number of transactions in this category
  - `total_amount`: Sum of transaction amounts (numeric string)
- `total_count`: Total number of transactions
- `total_amount`: Sum of all transaction amounts (numeric string)

**Example output (without aggregates):**
```json
{
  "transactions": [
    {
      "id": 2112150655,
      "date": "2024-07-28",
      "amount": "1250.8400",
      "payee": "Paycheck",
      "category_id": 88,
      "status": "reviewed",
      "is_pending": false
    }
  ],
  "has_more": false
}
```

**Example output (with aggregates):**
```json
{
  "transactions": [...],
  "has_more": false,
  "aggregates": {
    "by_category": [
      {"category_id": 88, "category_name": "Rent", "count": 2, "total_amount": "2500.00"},
      {"category_id": 82, "category_name": "Groceries", "count": 5, "total_amount": "245.50"},
      {"category_id": null, "category_name": "Uncategorized", "count": 3, "total_amount": "45.00"}
    ],
    "total_count": 10,
    "total_amount": "2790.50"
  }
}
```

## Design Philosophy

This MCP server is intentionally designed to return **minimal, focused responses** to avoid filling up the context window. Each tool:

- Returns only essential information
- Uses concise formatting
- Avoids verbose JSON dumps
- Provides human-readable output

## Technical Details

This server uses:
- **FastMCP**: A high-level Python framework for building MCP servers
- **requests-openapi**: Automatically generates API client from OpenAPI spec
- **OpenAPI 3.0 spec**: Ensures type safety and accurate API calls

The combination of FastMCP and requests-openapi means:
- Less boilerplate code
- Automatic request/response validation
- Easy to add new endpoints from the spec
- Type-safe API calls

## Resources

- [Lunch Money API Documentation](https://alpha.lunchmoney.dev/v2)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [requests-openapi](https://pypi.org/project/requests-openapi/)

## License

MIT
