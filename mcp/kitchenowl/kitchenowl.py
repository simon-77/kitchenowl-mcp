import datetime as _dt
import os
import requests


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

    def _patch(self, path, data=None):
        kwargs = {"json": data} if data is not None else {}
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path, data=None):
        kwargs = {"json": data} if data is not None else {}
        return self._request("DELETE", path, **kwargs)

    # ── Recipes ──────────────────────────────────────────────────────
    def list_recipes(self, page: int = 0, per_page: int = 20):
        # endpoint verified
        return self._get(f"/api/household/{self.household_id}/recipe",
                         offset=page * per_page, limit=per_page)

    def search_recipes(self, query: str):
        # server-side query param is ignored — filter client-side by name
        results = self._get(f"/api/household/{self.household_id}/recipe")
        if isinstance(results, list):
            q = query.lower()
            return [r for r in results if q in r.get("name", "").lower()]
        return results

    def get_recipe(self, recipe_id: int):
        # endpoint verified
        return self._get(f"/api/household/{self.household_id}/recipe/{recipe_id}")

    @staticmethod
    def _build_items(items: list) -> list:
        result = []
        for i in items:
            if not i.get("name"):
                raise KitchenOwlError(f"Each item must have a 'name' key, got: {i}")
            result.append({"name": i["name"], "description": i.get("description", ""), "optional": i.get("optional", False)})
        return result

    def create_recipe(self, name: str, description: str = "", items: list | None = None,
                      steps: list | None = None, tags: list | None = None,
                      time: int = 0, yields: str = "", source: str = "") -> dict:
        payload = {
            "name": name,
            "description": description,
            "time": time,
            "yields": yields,
            "source": source,
            "items": self._build_items(items or []),
            "steps": [{"text": s} for s in (steps or [])],
            "tags": [{"name": t} for t in (tags or [])],
        }
        return self._post(f"/api/household/{self.household_id}/recipe", payload)

    def update_recipe(self, recipe_id: int, name: str | None = None, description: str | None = None,
                      items: list | None = None, steps: list | None = None, tags: list | None = None,
                      time: int | None = None, yields: str | None = None, source: str | None = None) -> dict:
        payload: dict = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if time is not None:
            payload["time"] = time
        if yields is not None:
            payload["yields"] = yields
        if source is not None:
            payload["source"] = source
        if items is not None:
            payload["items"] = self._build_items(items)
        if steps is not None:
            payload["steps"] = [{"text": s} for s in steps]
        if tags is not None:
            payload["tags"] = [{"name": t} for t in tags]
        if not payload:
            raise KitchenOwlError("No fields provided to update.")
        # endpoint not yet verified against live server — PATCH may need to be PUT
        return self._patch(f"/api/household/{self.household_id}/recipe/{recipe_id}", payload)

    def get_trashed_recipes(self):
        # KitchenOwl has no server-side trash — recipes are hard-deleted.
        # This feature does not exist in the API.
        raise KitchenOwlError("KitchenOwl does not support a recipe trash/recycle bin — recipes are permanently deleted.")

    def restore_recipe(self, recipe_id: int):
        # KitchenOwl has no server-side trash — nothing to restore.
        raise KitchenOwlError("KitchenOwl does not support recipe restore — recipes are permanently deleted.")

    # ── Favorites ────────────────────────────────────────────────────
    def get_favorites(self):
        # KitchenOwl has no server-side wishlist/favorites — it is stored client-side only.
        raise KitchenOwlError("KitchenOwl does not support a server-side favorites/wishlist — this feature is client-side only.")

    def toggle_favorite(self, recipe_id: int):
        # KitchenOwl has no server-side wishlist/favorites — it is stored client-side only.
        raise KitchenOwlError("KitchenOwl does not support a server-side favorites/wishlist — this feature is client-side only.")

    # ── Shopping List ─────────────────────────────────────────────────
    def _get_default_list_id(self) -> int:
        if self._default_list_id is None:
            # endpoint verified: GET /api/household/{hh}/shoppinglist returns list of lists with embedded items
            lists = self._get(f"/api/household/{self.household_id}/shoppinglist")
            if isinstance(lists, list) and lists:
                self._default_list_id = lists[0].get("id", 1)
            else:
                self._default_list_id = 1
        return self._default_list_id

    def get_shopping_list(self):
        # endpoint verified: items are embedded in the shoppinglist response
        lists = self._get(f"/api/household/{self.household_id}/shoppinglist")
        if isinstance(lists, list) and lists:
            return lists[0].get("items", [])
        return []

    def add_to_shopping_list(self, name: str, description: str | None = None):
        # endpoint verified: POST /api/shoppinglist/{id}/add-item-by-name
        list_id = self._get_default_list_id()
        return self._post(
            f"/api/shoppinglist/{list_id}/add-item-by-name",
            {"name": name, "description": description or ""},
        )

    def add_recipe_to_shopping_list(self, recipe_id: int):
        # endpoint verified: POST /api/shoppinglist/{id}/recipeitems
        # requires {"items": [{"id": N, "name": "...", "description": "...", "optional": bool}]}
        recipe = self.get_recipe(recipe_id)
        items = recipe.get("items", [])
        payload_items = [
            {
                "id": item["id"],
                "name": item["name"],
                "description": item.get("description", ""),
                "optional": item.get("optional", False),
            }
            for item in items
            if item.get("name") and item.get("id")
        ]
        list_id = self._get_default_list_id()
        self._post(
            f"/api/shoppinglist/{list_id}/recipeitems",
            {"items": payload_items},
        )
        return {"added": len(payload_items), "recipe": recipe.get("name")}

    def remove_from_shopping_list(self, item_id: int):
        # endpoint verified: DELETE /api/shoppinglist/{id}/item with body {"item_id": N}
        list_id = self._get_default_list_id()
        return self._delete(
            f"/api/shoppinglist/{list_id}/item",
            {"item_id": item_id},
        )

    def check_off_shopping_item(self, item_id: int):
        # KitchenOwl has no check-off state — this removes the item from the list
        return self.remove_from_shopping_list(item_id)

    # ── Meal Plan ─────────────────────────────────────────────────────
    def get_meal_plan(self):
        # endpoint verified: GET /api/household/{hh}/planner
        return self._get(f"/api/household/{self.household_id}/planner")

    def add_to_meal_plan(self, recipe_id: int, date: str | None = None):
        # endpoint verified: POST /api/household/{hh}/planner/recipe
        # API requires cooking_date as Unix ms; omit for unscheduled
        payload: dict = {"recipe_id": recipe_id}
        if date:
            d = _dt.date.fromisoformat(date)
            epoch = _dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc)
            payload["cooking_date"] = int(epoch.timestamp() * 1000)
        return self._post(
            f"/api/household/{self.household_id}/planner/recipe",
            payload,
        )

    def remove_from_meal_plan(self, recipe_id: int):
        # endpoint verified: DELETE /api/household/{hh}/planner/recipe/{recipe_id}
        # KitchenOwl API identifies planner entries by recipe_id, not a separate plan-item id
        return self._delete(f"/api/household/{self.household_id}/planner/recipe/{recipe_id}")
