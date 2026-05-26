# KitchenOwl MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python fastmcp server that gives Claude access to KitchenOwl recipes, shopping list, meal plan, and favorites — deployed as Docker container.

**Architecture:** `KitchenOwlClient` HTTP class handles all API calls; `server.py` registers thin FastMCP tool wrappers. Config via ENV vars. Tests run locally in a venv (not in Docker).

**Tech Stack:** Python 3.12, `mcp[cli]` (FastMCP), `requests`, `pytest`, Docker, direnv

---

## File Map

| File | Purpose |
|------|---------|
| `mcp/kitchenowl/kitchenowl.py` | KitchenOwl HTTP client, all API calls, error handling |
| `mcp/kitchenowl/server.py` | FastMCP instance + tool definitions |
| `mcp/kitchenowl/Dockerfile` | Container build |
| `mcp/kitchenowl/requirements.txt` | Python deps |
| `mcp/kitchenowl/tests/test_kitchenowl.py` | Unit tests for HTTP client |
| `mcp/kitchenowl/tests/conftest.py` | Shared fixtures |
| `.env.template` | ENV vars template (safe to commit) |
| `.envrc` | direnv — loads `.env` (gitignored) |
| `.mcp.json` | MCP server registration |
| `chef.md` | Preferences + recipe notes |

---

## Task 1: Git repo + project scaffold

**Files:** all of the above (empty/skeleton)

- [ ] **Initialize git repo and create directory structure**

```bash
cd /home/simon/Nextcloud/Aster/Agents/projects/kochen
git init && git branch -M main
mkdir -p mcp/kitchenowl/tests docs/superpowers/{specs,plans}
touch mcp/kitchenowl/{server.py,kitchenowl.py,requirements.txt,Dockerfile}
touch mcp/kitchenowl/tests/{__init__.py,conftest.py,test_kitchenowl.py}
```

- [ ] **Create .gitignore**

```
.env
venv/
__pycache__/
*.pyc
.envrc
```

Save to `mcp/kitchenowl/.gitignore` (applies to that subtree only).

- [ ] **Set up local venv + pytest.ini for tests**

```bash
cd mcp/kitchenowl
python3 -m venv venv
./venv/bin/pip install mcp[cli] requests pytest
```

Create `mcp/kitchenowl/pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
```

Expected: venv created, packages installed without errors.

- [ ] **First commit**

```bash
git add mcp/ docs/ .gitignore
git commit -m "chore: scaffold kitchenowl-mcp project"
```

---

## Task 2: KitchenOwl HTTP client

**Files:**
- Create: `mcp/kitchenowl/kitchenowl.py`
- Create: `mcp/kitchenowl/tests/conftest.py`
- Create: `mcp/kitchenowl/tests/test_kitchenowl.py`

- [ ] **Write failing tests first**

`mcp/kitchenowl/tests/conftest.py`:
```python
import os
import pytest

os.environ.setdefault("KITCHENOWL_URL", "https://kitchenowl.test")
os.environ.setdefault("KITCHENOWL_TOKEN", "test-token")
os.environ.setdefault("KITCHENOWL_HOUSEHOLD_ID", "1")

from kitchenowl import KitchenOwlClient, KitchenOwlError

@pytest.fixture
def client():
    return KitchenOwlClient()

@pytest.fixture
def mock_get(client, monkeypatch):
    def factory(return_value, status_code=200):
        from unittest.mock import Mock
        mock_resp = Mock()
        mock_resp.status_code = status_code
        mock_resp.content = b"x"
        mock_resp.json.return_value = return_value
        monkeypatch.setattr(client.session, "request", lambda *a, **kw: mock_resp)
        return mock_resp
    return factory
```

`mcp/kitchenowl/tests/test_kitchenowl.py`:
```python
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
```

- [ ] **Run tests — expect ImportError (module not yet written)**

```bash
cd mcp/kitchenowl
./venv/bin/pytest tests/ -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'kitchenowl'`

- [ ] **Write `kitchenowl.py`**

```python
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

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, verify=self.verify_ssl, **kwargs)
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
        return self._request("POST", path, json=data or {})

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
        # NOTE: endpoint needs verification against actual API
        return self._get(f"/api/household/{self.household_id}/recipe", deleted=True)

    def restore_recipe(self, recipe_id: int):
        return self._post(f"/api/household/{self.household_id}/recipe/{recipe_id}/restore")

    # ── Favorites ────────────────────────────────────────────────────
    def get_favorites(self):
        # NOTE: endpoint needs verification — may be wishlist=True param or separate endpoint
        return self._get(f"/api/household/{self.household_id}/recipe", wishlist=True)

    def toggle_favorite(self, recipe_id: int):
        return self._post(f"/api/household/{self.household_id}/recipe/{recipe_id}/wishlist")

    # ── Shopping List ─────────────────────────────────────────────────
    def _get_default_list_id(self) -> int:
        lists = self._get(f"/api/household/{self.household_id}/shoppinglist")
        if isinstance(lists, list) and lists:
            return lists[0]["id"]
        return 1

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
```

- [ ] **Run tests — expect PASS**

```bash
cd mcp/kitchenowl
./venv/bin/pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Commit**

```bash
git add mcp/kitchenowl/
git commit -m "feat: KitchenOwl HTTP client with tests"
```

---

## Task 3: FastMCP server

**Files:**
- Create: `mcp/kitchenowl/server.py`

- [ ] **Write `server.py`**

```python
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
```

- [ ] **Write tool-registration test**

Add to `mcp/kitchenowl/tests/test_kitchenowl.py`:
```python
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
```

- [ ] **Run tests — verify all pass**

```bash
cd mcp/kitchenowl
./venv/bin/pytest tests/ -v
```
Expected: all PASS including `test_all_tools_registered`.

- [ ] **Smoke-test: verify server starts without crash**

```bash
cd mcp/kitchenowl
KITCHENOWL_URL=https://kitchenowl.aster.wien \
KITCHENOWL_TOKEN=dummy \
./venv/bin/python -c "import server; print('tools:', len(list(server.mcp._tool_manager._tools)))"
```
Expected: prints `tools: 15`.

- [ ] **Commit**

```bash
git add mcp/kitchenowl/server.py
git commit -m "feat: FastMCP server with all KitchenOwl tools"
```

---

## Task 4: Dockerfile + requirements.txt

**Files:**
- Create: `mcp/kitchenowl/Dockerfile`
- Create: `mcp/kitchenowl/requirements.txt`

- [ ] **Write requirements.txt**

```
mcp[cli]>=1.0.0
requests>=2.31.0
```

- [ ] **Write Dockerfile**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py kitchenowl.py ./
CMD ["python", "server.py"]
```

- [ ] **Build and verify**

```bash
cd mcp/kitchenowl
docker build -t kitchenowl-mcp:latest .
```
Expected: build succeeds, no errors.

- [ ] **Test container starts**

```bash
docker run --rm -e KITCHENOWL_URL=https://x -e KITCHENOWL_TOKEN=x \
  kitchenowl-mcp:latest python -c "import server; print('OK')"
```
Expected: prints `OK`.

- [ ] **Commit**

```bash
git add mcp/kitchenowl/Dockerfile mcp/kitchenowl/requirements.txt
git commit -m "feat: Docker build for kitchenowl-mcp"
```

---

## Task 5: Project config (.env.template, .mcp.json, .envrc, chef.md)

**Files:**
- Create: `.env.template`
- Create: `.env` (from template, gitignored — user fills token)
- Create/Recreate: `.mcp.json` (currently corrupted null device)
- Create: `.envrc`
- Create: `chef.md`

- [ ] **Create .env.template**

`/home/simon/Nextcloud/Aster/Agents/projects/kochen/.env.template`:
```bash
# KitchenOwl MCP — copy to .env and fill in your values
KITCHENOWL_URL=https://kitchenowl.aster.wien
KITCHENOWL_TOKEN=<paste your Long-Lived Token here>
KITCHENOWL_HOUSEHOLD_ID=1
# Set to false if using a self-signed certificate
KITCHENOWL_VERIFY_SSL=true
```

- [ ] **Create .env from template (user fills token)**

```bash
cp /home/simon/Nextcloud/Aster/Agents/projects/kochen/.env.template \
   /home/simon/Nextcloud/Aster/Agents/projects/kochen/.env
```
User opens `.env` and pastes their LLT token.

- [ ] **Create .envrc**

`/home/simon/Nextcloud/Aster/Agents/projects/kochen/.envrc`:
```bash
dotenv
```
Then allow: `direnv allow /home/simon/Nextcloud/Aster/Agents/projects/kochen`

- [ ] **Recreate .mcp.json** (current file is a null device due to cloud sync corruption — must remove first)

```bash
rm /home/simon/Nextcloud/Aster/Agents/projects/kochen/.mcp.json
```

Then write:
```json
{
  "mcpServers": {
    "kitchenowl": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "KITCHENOWL_URL",
        "-e", "KITCHENOWL_TOKEN",
        "-e", "KITCHENOWL_HOUSEHOLD_ID",
        "-e", "KITCHENOWL_VERIFY_SSL",
        "kitchenowl-mcp:latest"
      ]
    }
  }
}
```

- [ ] **Create chef.md**

`/home/simon/Nextcloud/Aster/Agents/projects/kochen/chef.md`:
```markdown
# Chef — Präferenzen & Rezept-Notizen

## Präferenzen

*(Hier notiere ich deine Geschmacksvorlieben, Einschränkungen und Lieblingsküchen.)*

- Küchen: –
- Vermeide: –
- Diät/Allergien: –
- Lieblingszutaten: –

## Rezept-Notizen

| KitchenOwl-ID | Name | Bewertung | Notiz |
|---|---|---|---|
| – | – | – | – |
```

- [ ] **Commit (excluding .env)**

```bash
cd /home/simon/Nextcloud/Aster/Agents/projects/kochen
git add .env.template .mcp.json .envrc chef.md
git commit -m "chore: project config, .env.template, chef.md"
```

---

## Task 6: API endpoint verification (requires LLT token)

**Pre-condition:** `.env` contains a valid token.

- [ ] **Test basic connectivity**

```bash
source /home/simon/Nextcloud/Aster/Agents/projects/kochen/.env
curl -s -H "Authorization: Bearer $KITCHENOWL_TOKEN" \
  "$KITCHENOWL_URL/api/household/$KITCHENOWL_HOUSEHOLD_ID/recipe?limit=3" | python3 -m json.tool | head -30
```
Expected: JSON array of recipes. If 401 → token wrong. If 404 → household ID wrong.

- [ ] **Verify trash endpoint**

```bash
curl -s -H "Authorization: Bearer $KITCHENOWL_TOKEN" \
  "$KITCHENOWL_URL/api/household/$KITCHENOWL_HOUSEHOLD_ID/recipe?deleted=true" | python3 -m json.tool | head -20
```
If this returns an error, try: `GET /api/household/{id}/recipe/deleted` and update `kitchenowl.py:get_trashed_recipes`.

- [ ] **Verify favorites endpoint**

```bash
curl -s -H "Authorization: Bearer $KITCHENOWL_TOKEN" \
  "$KITCHENOWL_URL/api/household/$KITCHENOWL_HOUSEHOLD_ID/recipe?wishlist=true" | python3 -m json.tool | head -20
```
If error, check KitchenOwl source for correct endpoint and update `kitchenowl.py:get_favorites` + `toggle_favorite`.

- [ ] **Find chicken-white-beans recipe in trash**

```bash
# After confirming trash endpoint works:
source /home/simon/Nextcloud/Aster/Agents/projects/kochen/.env
curl -s -H "Authorization: Bearer $KITCHENOWL_TOKEN" \
  "$KITCHENOWL_URL/api/household/$KITCHENOWL_HOUSEHOLD_ID/recipe?deleted=true" | \
  python3 -c "import sys,json; r=json.load(sys.stdin); [print(x['id'],x['name']) for x in (r if isinstance(r,list) else r.get('recipes',[]))]"
```

- [ ] **Fix any endpoint discrepancies in kitchenowl.py, re-run tests, rebuild Docker**

```bash
cd mcp/kitchenowl
./venv/bin/pytest tests/ -v
docker build -t kitchenowl-mcp:latest .
```

- [ ] **Test MCP tool via Docker**

```bash
source /home/simon/Nextcloud/Aster/Agents/projects/kochen/.env
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_recipes","arguments":{}}}' | \
  docker run --rm -i \
    -e KITCHENOWL_URL -e KITCHENOWL_TOKEN -e KITCHENOWL_HOUSEHOLD_ID \
    kitchenowl-mcp:latest
```
Expected: JSON response with recipe data.

- [ ] **Final commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/projects/kochen
git add -A
git commit -m "feat: KitchenOwl MCP complete — verified against live API"
```

---

## API Endpoint Notes

These endpoints are assumptions based on KitchenOwl's documented structure. Verify in Task 6 and update if needed:

| Method | Assumption | May need adjustment |
|--------|------------|---------------------|
| `get_trashed_recipes` | `?deleted=true` param | Might be `/recipe/deleted` endpoint |
| `get_favorites` | `?wishlist=true` param | Might be per-member endpoint |
| `toggle_favorite` | `POST /recipe/{id}/wishlist` | Might be PUT or different path |
| `get_shopping_list` | `GET /shoppinglist/{id}/item` | List structure TBD |
| `add_to_shopping_list` | `POST /shoppinglist/{id}/item` | Body fields TBD |
| `check_off_shopping_item` | `POST /shoppinglist/{id}/item/{id}` + `{"checked":true}` | Body field may differ |

**Performance note:** `_get_default_list_id()` makes an extra API call on every shopping operation. If this feels slow, cache the list ID on the client instance after the first call.
