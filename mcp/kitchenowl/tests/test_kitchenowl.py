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

def test_add_recipe_to_shopping_builds_payload(client, mock_get):
    """add_recipe_to_shopping_list calls recipeitems endpoint with correct payload."""
    recipe = {
        "id": 5,
        "name": "Pasta",
        "items": [
            {"id": 1, "name": "Nudeln", "description": "200 g", "optional": False},
            {"id": 2, "name": "Salz", "description": "", "optional": False},
            {"name": "No ID item"},  # should be skipped (no id)
        ],
    }
    calls = []
    from unittest.mock import Mock

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        resp = Mock()
        resp.status_code = 200
        resp.content = b"x"
        # First call: get_recipe; subsequent: shoppinglist list; then recipeitems
        if method == "GET" and "/recipe/5" in url:
            resp.json.return_value = recipe
        elif method == "GET" and "/shoppinglist" in url:
            resp.json.return_value = [{"id": 1, "name": "Default", "items": []}]
        else:
            resp.json.return_value = {}
        return resp

    client.session.request = fake_request

    result = client.add_recipe_to_shopping_list(5)
    assert result["added"] == 2  # "No ID item" skipped
    assert result["recipe"] == "Pasta"
    # Verify the recipeitems call was made with correct payload
    recipe_items_call = [c for c in calls if "recipeitems" in c[1]]
    assert len(recipe_items_call) == 1
    payload = recipe_items_call[0][2]["json"]["items"]
    assert len(payload) == 2
    assert payload[0]["name"] == "Nudeln"


def test_search_recipes_filters_by_name(client, mock_get):
    mock_get([{"id": 1, "name": "Pasta Bolognese"}, {"id": 2, "name": "Hühnchen"}])
    result = client.search_recipes("pasta")
    assert len(result) == 1
    assert result[0]["name"] == "Pasta Bolognese"


def test_add_to_meal_plan_date_as_unix_ms(client):
    """ISO date '2026-01-15' must be sent as Unix ms timestamp."""
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs)
        resp = Mock()
        resp.status_code = 200
        resp.content = b"x"
        resp.json.return_value = {}
        return resp

    client.session.request = fake_request
    client.add_to_meal_plan(42, "2026-01-15")
    assert calls, "no request made"
    payload = calls[0]["json"]
    assert payload["recipe_id"] == 42
    # 2026-01-15 UTC midnight = 1768435200000 ms
    assert payload["cooking_date"] == 1768435200000


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
