# KitchenOwl MCP — Design Spec

**Date:** 2026-05-26  
**Status:** Draft

## Overview

MCP-Server für KitchenOwl (self-hosted unter `kitchenowl.aster.wien`), der Claude direkten Zugriff auf Rezepte, Shopping-Liste und Meal Plan gibt. Präferenzen werden lokal in `chef.md` gepflegt; KitchenOwl-Favorites für schnelles In-App-Markieren.

## Architektur

```
kochen/
├── mcp/kitchenowl/
│   ├── server.py          # fastmcp server (Einstiegspunkt)
│   ├── kitchenowl.py      # HTTP-Client (alle API-Calls)
│   ├── Dockerfile
│   └── requirements.txt
├── chef.md                # Präferenzen + Rezept-Notizen (von Claude gepflegt)
└── .claude/CLAUDE.md      # Projekt-Instruktionen
```

**Laufzeit:** Docker-Container, via stdio in `.mcp.json` eingebunden.

**Konfiguration (ENV):**
- `KITCHENOWL_URL` — z.B. `https://kitchenowl.aster.wien`
- `KITCHENOWL_TOKEN` — Long-Lived Token (LLT)
- `KITCHENOWL_HOUSEHOLD_ID` — Default `1` (die meisten Self-Hosted-Instanzen haben nur eine)

## MCP Tools

### Rezepte
| Tool | Parameter | Beschreibung |
|------|-----------|--------------|
| `list_recipes` | `page`, `per_page` | Alle Rezepte (Household aus ENV) |
| `search_recipes` | `query` | Volltextsuche |
| `get_recipe` | `recipe_id` | Vollständiges Rezept inkl. Zutaten + Schritte |
| `get_trashed_recipes` | — | Rezepte im Papierkorb |
| `restore_recipe` | `recipe_id` | Rezept aus Papierkorb wiederherstellen |

Kein `create`/`update`/`delete` — dafür die KitchenOwl-App nutzen.

### Favorites
| Tool | Parameter | Beschreibung |
|------|-----------|--------------|
| `get_favorites` | — | Alle als Favorit markierten Rezepte |
| `toggle_favorite` | `recipe_id` | Favorit setzen/entfernen |

### Shopping-Liste
| Tool | Parameter | Beschreibung |
|------|-----------|--------------|
| `get_shopping_list` | — | Aktuelle Einkaufsliste (inkl. Item-IDs) |
| `add_to_shopping_list` | `name`, `amount?` | Artikel per Freitext hinzufügen |
| `add_recipe_to_shopping_list` | `recipe_id` | Alle Zutaten eines Rezepts hinzufügen |
| `check_off_shopping_item` | `item_id` | Artikel abhaken (nicht löschen) |
| `remove_from_shopping_list` | `item_id` | Artikel entfernen |

`add_recipe_to_shopping_list` fügt **alle** Zutaten hinzu (einfacher; User entfernt was vorhanden ist).

### Meal Plan
| Tool | Parameter | Beschreibung |
|------|-----------|--------------|
| `get_meal_plan` | — | Aktueller Plan (gibt `id`, `recipe_id`, `date` zurück) |
| `add_to_meal_plan` | `recipe_id`, `date?` | Rezept hinzufügen; default: heute |
| `remove_from_meal_plan` | `plan_item_id` | Eintrag entfernen (ID aus `get_meal_plan`) |

## Präferenz-System

**`chef.md`** — zwei Abschnitte, von Claude gepflegt:

```markdown
## Präferenzen
- Küchen: mediterran, asiatisch
- Vermeide: sehr scharf, Koriander
- ...

## Rezept-Notizen
| KitchenOwl-ID | Name | Bewertung | Notiz |
|---|---|---|---|
| 42 | Hühnchen weiße Bohnen | ★★★★ | nächstes Mal mehr Knoblauch |
```

**KitchenOwl-Favorites** — für schnelles Markieren direkt in der App oder per `toggle_favorite`.

Bei Rezeptempfehlungen liest Claude zuerst `chef.md`, berücksichtigt Favorites und schlägt passende Rezepte vor.

## Authentifizierung

Long-Lived Token (LLT) — erstellt in KitchenOwl unter *Settings → Account → API-Tokens*. Als ENV-Variable übergeben, nie in Dateien gespeichert.

## Fehlerbehandlung

`kitchenowl.py` fängt alle HTTP-Fehler (4xx/5xx) und gibt strukturierte Fehlermeldungen an fastmcp zurück. Token-Fehler (401) werden explizit als "Token ungültig oder abgelaufen" gemeldet. SSL-Verifikation aktiv (self-signed cert → `KITCHENOWL_VERIFY_SSL=false` als Opt-out).

## Docker-Setup

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py kitchenowl.py ./
CMD ["python", "server.py"]
```

Einbindung in `.mcp.json`:
```json
{
  "mcpServers": {
    "kitchenowl": {
      "command": "docker",
      "args": ["run", "--rm", "-i",
               "-e", "KITCHENOWL_URL",
               "-e", "KITCHENOWL_TOKEN",
               "-e", "KITCHENOWL_HOUSEHOLD_ID",
               "kitchenowl-mcp:latest"]
    }
  }
}
```

ENV-Variablen via `direnv` / `.envrc` im Projektordner gesetzt.
