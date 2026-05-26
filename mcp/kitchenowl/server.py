import sys
import os

# Allow running from repo root: python mcp/kitchenowl/server.py
sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from kitchenowl import KitchenOwlClient, KitchenOwlError

mcp = FastMCP("KitchenOwl")
_client: KitchenOwlClient | None = None


def client() -> KitchenOwlClient:
    global _client
    if _client is None:
        _client = KitchenOwlClient()
    return _client


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KitchenOwlError as e:
        return {"error": str(e)}


# ── Recipes ──────────────────────────────────────────────────────────

@mcp.tool()
def list_recipes(page: int = 0, per_page: int = 20) -> dict | list:
    """List recipes from KitchenOwl (paginated)."""
    return _run(client().list_recipes, page=page, per_page=per_page)


@mcp.tool()
def search_recipes(query: str) -> dict | list:
    """Search recipes by name or ingredient."""
    return _run(client().search_recipes, query)


@mcp.tool()
def get_recipe(recipe_id: int) -> dict:
    """Get full recipe including ingredients and steps."""
    return _run(client().get_recipe, recipe_id)


@mcp.tool()
def get_trashed_recipes() -> dict | list:
    """List recipes in the KitchenOwl trash."""
    return _run(client().get_trashed_recipes)


@mcp.tool()
def restore_recipe(recipe_id: int) -> dict:
    """Restore a recipe from the trash."""
    return _run(client().restore_recipe, recipe_id)


# ── Favorites ────────────────────────────────────────────────────────

@mcp.tool()
def get_favorites() -> dict | list:
    """Get all favorited recipes."""
    return _run(client().get_favorites)


@mcp.tool()
def toggle_favorite(recipe_id: int) -> dict:
    """Add or remove a recipe from favorites."""
    return _run(client().toggle_favorite, recipe_id)


# ── Shopping List ─────────────────────────────────────────────────────

@mcp.tool()
def get_shopping_list() -> dict | list:
    """Get current shopping list with item IDs."""
    return _run(client().get_shopping_list)


@mcp.tool()
def add_to_shopping_list(name: str, amount: str = "") -> dict:
    """Add a single item to the shopping list. amount is optional (e.g. '200 g')."""
    return _run(client().add_to_shopping_list, name, amount or None)


@mcp.tool()
def add_recipe_to_shopping_list(recipe_id: int) -> dict:
    """Add all ingredients of a recipe to the shopping list (with amounts)."""
    return _run(client().add_recipe_to_shopping_list, recipe_id)


@mcp.tool()
def check_off_shopping_item(item_id: int) -> dict:
    """Mark a shopping list item as checked (use item_id from get_shopping_list)."""
    return _run(client().check_off_shopping_item, item_id)


@mcp.tool()
def remove_from_shopping_list(item_id: int) -> dict:
    """Remove an item from the shopping list."""
    return _run(client().remove_from_shopping_list, item_id)


# ── Meal Plan ─────────────────────────────────────────────────────────

@mcp.tool()
def get_meal_plan() -> dict | list:
    """Get current meal plan. Each entry has id, recipe_id, day."""
    return _run(client().get_meal_plan)


@mcp.tool()
def add_to_meal_plan(recipe_id: int, date: str = "") -> dict:
    """Add a recipe to the meal plan. date format: YYYY-MM-DD (default: today)."""
    return _run(client().add_to_meal_plan, recipe_id, date or None)


@mcp.tool()
def remove_from_meal_plan(plan_item_id: int) -> dict:
    """Remove an entry from the meal plan (use id from get_meal_plan)."""
    return _run(client().remove_from_meal_plan, plan_item_id)


if __name__ == "__main__":
    mcp.run()
