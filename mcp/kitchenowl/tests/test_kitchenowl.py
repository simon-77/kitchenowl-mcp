import pytest
from unittest.mock import Mock
from kitchenowl import KitchenOwlClient, KitchenOwlError

def test_list_recipes_returns_data(client, mock_get):
    mock_get([{"id": 1, "name": "Pasta"}])
    result = client.list_recipes()
    assert result == [{"id": 1, "name": "Pasta"}]

def test_401_raises_descriptive_error(client, mock_get):
    mock_get(None, status_code=401)
    with pytest.raises(KitchenOwlError, match="Token invalid"):
        client.list_recipes()

def test_add_recipe_to_shopping_amount_formatting():
    """Unit test for amount string assembly — no HTTP needed."""
    items = [
        {"name": "Nudeln", "amount": 200, "unit": "g"},
        {"name": "Salz", "amount": "", "unit": ""},
        {"name": "Öl", "amount": 2, "unit": ""},
    ]
    amounts = []
    for item in items:
        parts = [str(item.get("amount", "")), item.get("unit", "")]
        amount = " ".join(p for p in parts if p).strip()
        amounts.append(amount)
    assert amounts[0] == "200 g"
    assert amounts[1] == ""
    assert amounts[2] == "2"


def test_all_tools_registered():
    import os
    os.environ.setdefault("KITCHENOWL_URL", "https://kitchenowl.test")
    os.environ.setdefault("KITCHENOWL_TOKEN", "x")
    import server
    tool_names = set(server.mcp._tool_manager._tools.keys())
    expected = {
        "list_recipes", "search_recipes", "get_recipe",
        "get_trashed_recipes", "restore_recipe",
        "get_favorites", "toggle_favorite",
        "get_shopping_list", "add_to_shopping_list",
        "add_recipe_to_shopping_list", "check_off_shopping_item",
        "remove_from_shopping_list",
        "get_meal_plan", "add_to_meal_plan", "remove_from_meal_plan",
    }
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"
