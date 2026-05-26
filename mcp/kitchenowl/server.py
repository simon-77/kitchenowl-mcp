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
    """Search recipes by name (client-side filter — returns recipes whose name contains query)."""
    return _run(client().search_recipes, query)


@mcp.tool()
def get_recipe(recipe_id: int) -> dict:
    """Get full recipe including ingredients and steps."""
    return _run(client().get_recipe, recipe_id)


@mcp.tool()
def get_trashed_recipes() -> dict | list:
    """List recipes in the KitchenOwl trash. NOTE: KitchenOwl does not support a trash bin — recipes are permanently deleted."""
    return _run(client().get_trashed_recipes)


@mcp.tool()
def restore_recipe(recipe_id: int) -> dict:
    """Restore a recipe from the trash. NOTE: KitchenOwl does not support recipe restore."""
    return _run(client().restore_recipe, recipe_id)


# ── Favorites ────────────────────────────────────────────────────────

@mcp.tool()
def get_favorites() -> dict | list:
    """Get all favorited recipes. NOTE: KitchenOwl favorites are client-side only — no server API exists."""
    return _run(client().get_favorites)


@mcp.tool()
def toggle_favorite(recipe_id: int) -> dict:
    """Add or remove a recipe from favorites. NOTE: KitchenOwl favorites are client-side only — no server API exists."""
    return _run(client().toggle_favorite, recipe_id)


# ── Shopping List ─────────────────────────────────────────────────────

@mcp.tool()
def get_shopping_list() -> dict | list:
    """Get current shopping list with item IDs."""
    return _run(client().get_shopping_list)


@mcp.tool()
def add_to_shopping_list(name: str, description: str = "") -> dict:
    """Add a single item to the shopping list. description is optional (e.g. '200 g')."""
    return _run(client().add_to_shopping_list, name, description or None)


@mcp.tool()
def add_recipe_to_shopping_list(recipe_id: int) -> dict:
    """Add all ingredients of a recipe to the shopping list (with amounts)."""
    return _run(client().add_recipe_to_shopping_list, recipe_id)


@mcp.tool()
def check_off_shopping_item(item_id: int) -> dict:
    """Remove a shopping list item by marking it done (KitchenOwl has no check-off state — this removes the item)."""
    return _run(client().check_off_shopping_item, item_id)


@mcp.tool()
def remove_from_shopping_list(item_id: int) -> dict:
    """Remove an item from the shopping list."""
    return _run(client().remove_from_shopping_list, item_id)


# ── Meal Plan ─────────────────────────────────────────────────────────

@mcp.tool()
def get_meal_plan() -> dict | list:
    """Get current meal plan. Each entry has recipe_id, day, cooking_date."""
    return _run(client().get_meal_plan)


@mcp.tool()
def add_to_meal_plan(recipe_id: int, date: str = "") -> dict:
    """Add a recipe to the meal plan. date: YYYY-MM-DD (optional — omit to add as unscheduled)."""
    return _run(client().add_to_meal_plan, recipe_id, date or None)


@mcp.tool()
def remove_from_meal_plan(recipe_id: int) -> dict:
    """Remove a recipe from the meal plan (use recipe_id from get_meal_plan)."""
    return _run(client().remove_from_meal_plan, recipe_id)


if __name__ == "__main__":
    mcp.run()
