import os
import requests
from datetime import date as _date


class KitchenOwlError(Exception):
    pass


class KitchenOwlClient:
    def __init__(self):
        self.base_url = os.environ["KITCHENOWL_URL"].rstrip("/")
        self.token = os.environ["KITCHENOWL_TOKEN"]
        self.household_id = int(os.environ.get("KITCHENOWL_HOUSEHOLD_ID", "1"))
        self.verify_ssl = os.environ.get("KITCHENOWL_VERIFY_SSL", "true").lower() != "false"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })
        self._default_list_id: int | None = None

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, verify=self.verify_ssl, timeout=(5, 30), **kwargs)
        except requests.ConnectionError as e:
            raise KitchenOwlError(f"Connection failed: {e}")
        if resp.status_code == 401:
            raise KitchenOwlError("Token invalid or expired — create a new LLT in KitchenOwl settings.")
        if resp.status_code == 404:
            raise KitchenOwlError(f"Not found: {path}")
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            raise KitchenOwlError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.content else {}

    def _get(self, path, **params):
        return self._request("GET", path, params={k: v for k, v in params.items() if v is not None})

    def _post(self, path, data=None):
        kwargs = {"json": data} if data is not None else {}
        return self._request("POST", path, **kwargs)

    def _delete(self, path):
        return self._request("DELETE", path)

    # ── Recipes ──────────────────────────────────────────────────────
    def list_recipes(self, page: int = 0, per_page: int = 20):
        return self._get(f"/api/household/{self.household_id}/recipe",
                         offset=page * per_page, limit=per_page)

    def search_recipes(self, query: str):
        return self._get(f"/api/household/{self.household_id}/recipe", query=query)

    def get_recipe(self, recipe_id: int):
        return self._get(f"/api/household/{self.household_id}/recipe/{recipe_id}")

    def get_trashed_recipes(self):
        # endpoint needs verification against actual API
        return self._get(f"/api/household/{self.household_id}/recipe", deleted=True)

    def restore_recipe(self, recipe_id: int):
        return self._post(f"/api/household/{self.household_id}/recipe/{recipe_id}/restore")

    # ── Favorites ────────────────────────────────────────────────────
    def get_favorites(self):
        # endpoint needs verification — may be wishlist=True param or separate endpoint
        return self._get(f"/api/household/{self.household_id}/recipe", wishlist=True)

    def toggle_favorite(self, recipe_id: int):
        return self._post(f"/api/household/{self.household_id}/recipe/{recipe_id}/wishlist")

    # ── Shopping List ─────────────────────────────────────────────────
    def _get_default_list_id(self) -> int:
        if self._default_list_id is None:
            lists = self._get(f"/api/household/{self.household_id}/shoppinglist")
            if isinstance(lists, list) and lists:
                self._default_list_id = lists[0].get("id", 1)
            else:
                self._default_list_id = 1
        return self._default_list_id

    def get_shopping_list(self):
        list_id = self._get_default_list_id()
        return self._get(f"/api/household/{self.household_id}/shoppinglist/{list_id}/item")

    def add_to_shopping_list(self, name: str, amount: str | None = None):
        list_id = self._get_default_list_id()
        return self._post(
            f"/api/household/{self.household_id}/shoppinglist/{list_id}/item",
            {"name": name, "description": amount or ""},
        )

    def add_recipe_to_shopping_list(self, recipe_id: int):
        recipe = self.get_recipe(recipe_id)
        items = recipe.get("items", [])
        for item in items:
            name = item.get("name", "")
            parts = [str(item.get("amount", "")), item.get("unit", "")]
            amount = " ".join(p for p in parts if p).strip()
            if name:
                self.add_to_shopping_list(name, amount or None)
        return {"added": len([i for i in items if i.get("name")]), "recipe": recipe.get("name")}

    def check_off_shopping_item(self, item_id: int):
        list_id = self._get_default_list_id()
        return self._post(
            f"/api/household/{self.household_id}/shoppinglist/{list_id}/item/{item_id}",
            {"checked": True},
        )

    def remove_from_shopping_list(self, item_id: int):
        list_id = self._get_default_list_id()
        return self._delete(
            f"/api/household/{self.household_id}/shoppinglist/{list_id}/item/{item_id}"
        )

    # ── Meal Plan ─────────────────────────────────────────────────────
    def get_meal_plan(self):
        return self._get(f"/api/household/{self.household_id}/planner")

    def add_to_meal_plan(self, recipe_id: int, date: str | None = None):
        return self._post(
            f"/api/household/{self.household_id}/planner",
            {"recipe_id": recipe_id, "day": date or _date.today().isoformat()},
        )

    def remove_from_meal_plan(self, plan_item_id: int):
        return self._delete(f"/api/household/{self.household_id}/planner/{plan_item_id}")
