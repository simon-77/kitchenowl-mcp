# kitchenowl-mcp

MCP server for [KitchenOwl](https://kitchenowl.org) — gives AI assistants (Claude, etc.) access to your self-hosted KitchenOwl recipes, shopping list, and meal plan via 15 tools.

Built with [FastMCP](https://github.com/jlowin/fastmcp) (Python), runs as a Docker container over stdio.

## Tools

| Category | Tool | Description |
|----------|------|-------------|
| **Recipes** | `list_recipes` | List all recipes (paginated) |
| | `search_recipes` | Search recipes by name (client-side filter) |
| | `get_recipe` | Full recipe with ingredients and steps |
| | `get_trashed_recipes` | *(see Known Limitations)* |
| | `restore_recipe` | *(see Known Limitations)* |
| **Favorites** | `get_favorites` | *(see Known Limitations)* |
| | `toggle_favorite` | *(see Known Limitations)* |
| **Shopping List** | `get_shopping_list` | Current list with item IDs |
| | `add_to_shopping_list` | Add item by name (optional: amount/description) |
| | `add_recipe_to_shopping_list` | Add all ingredients of a recipe |
| | `check_off_shopping_item` | Remove item (KitchenOwl has no check-off state) |
| | `remove_from_shopping_list` | Remove item by ID |
| **Meal Plan** | `get_meal_plan` | Current meal plan |
| | `add_to_meal_plan` | Add recipe; optional date `YYYY-MM-DD` |
| | `remove_from_meal_plan` | Remove recipe from plan |

## Known Limitations

- **No server-side trash**: KitchenOwl permanently deletes recipes. `get_trashed_recipes` and `restore_recipe` return an informative error.
- **No server-side favorites**: Favorites are stored client-side in the KitchenOwl app only. `get_favorites` and `toggle_favorite` return an informative error.
- **`search_recipes`**: KitchenOwl's API ignores server-side search params; this tool fetches all recipes and filters by name client-side.
- **`check_off_shopping_item`**: KitchenOwl has no check-off state — the item is removed from the list.

## Setup

### Prerequisites

- Docker
- A running KitchenOwl instance (self-hosted)
- An MCP-compatible AI client (e.g. [Claude Code](https://claude.ai/code) or Claude Desktop)

### 1. Build the Docker image

```bash
git clone https://github.com/simon-77/kitchenowl-mcp.git
cd kitchenowl-mcp
docker build -t kitchenowl-mcp:latest mcp/kitchenowl/
```

### 2. Create a Long-Lived Token

In KitchenOwl: **Settings → Account → API Tokens → Create Long-Lived Token**

### 3. Create an env file

```bash
# Recommended: store outside the project directory
cat > ~/.config/kitchenowl/kitchenowl.env <<'EOF'
KITCHENOWL_URL=https://your-kitchenowl.example.com
KITCHENOWL_TOKEN=your-long-lived-token-here
KITCHENOWL_HOUSEHOLD_ID=1
KITCHENOWL_VERIFY_SSL=true
EOF
chmod 600 ~/.config/kitchenowl/kitchenowl.env
```

> Set `KITCHENOWL_VERIFY_SSL=false` if your instance uses a self-signed certificate.

### 4. Add to your MCP client config

**Claude Code** — add to `.mcp.json` in your project (or `~/.claude.json` for global access):

```json
{
  "mcpServers": {
    "kitchenowl": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "/absolute/path/to/kitchenowl.env",
        "kitchenowl-mcp:latest"
      ]
    }
  }
}
```

> **Note:** `--env-file` requires an **absolute path** — Docker does not expand `~` or `$HOME`.

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kitchenowl": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "/absolute/path/to/kitchenowl.env",
        "kitchenowl-mcp:latest"
      ]
    }
  }
}
```

## Running Without Docker

```bash
cd mcp/kitchenowl
pip install -r requirements.txt

export KITCHENOWL_URL=https://your-kitchenowl.example.com
export KITCHENOWL_TOKEN=your-long-lived-token-here
python server.py
```

Or wire up the Python script directly in `.mcp.json`:

```json
{
  "mcpServers": {
    "kitchenowl": {
      "command": "python",
      "args": ["/absolute/path/to/mcp/kitchenowl/server.py"],
      "env": {
        "KITCHENOWL_URL": "https://your-kitchenowl.example.com",
        "KITCHENOWL_TOKEN": "your-long-lived-token-here",
        "KITCHENOWL_HOUSEHOLD_ID": "1"
      }
    }
  }
}
```

> **Warning:** Avoid inlining the token in `.mcp.json` if the file is tracked in git or shared.

## Development

```bash
cd mcp/kitchenowl
pip install -r requirements.txt
pytest
```

Tests use `unittest.mock` — no live KitchenOwl instance required.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KITCHENOWL_URL` | yes | — | Base URL of your KitchenOwl instance |
| `KITCHENOWL_TOKEN` | yes | — | Long-Lived Token from KitchenOwl settings |
| `KITCHENOWL_HOUSEHOLD_ID` | no | `1` | Household ID (most single-user installs: `1`) |
| `KITCHENOWL_VERIFY_SSL` | no | `true` | Set `false` for self-signed certificates |
