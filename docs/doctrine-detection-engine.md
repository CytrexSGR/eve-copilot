# Doctrine Detection Engine - Documentation

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Data Sources](#data-sources)
- [Database Schema](#database-schema)
- [Core Components](#core-components)
- [API Reference](#api-reference)
- [Background Jobs](#background-jobs)
- [Frontend Integration](#frontend-integration)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Doctrine Detection Engine identifies fleet doctrines from EVE Online combat data using two approaches:

1. **Battle-based Extraction** (Primary): Analyzes completed battles from killmail data
2. **Live Snapshot Clustering** (Secondary): DBSCAN clustering of real-time zkillboard data

### Key Features

- **Battle Analysis**: Extracts doctrines from completed battles with accurate compositions
- **Real Item Data**: Derives consumed items directly from killmail destruction data
- **Production Chains**: Links items to manufacturing materials from EVE SDE
- **Regional Intelligence**: Tracks doctrine activity by region with full SDE region names
- **Confidence Scoring**: Statistical confidence based on observation frequency

### Use Cases

1. **Market Traders**: Identify ammunition/fuel demand from active doctrines
2. **Manufacturers**: See production materials needed for doctrine consumables
3. **Alliance Intelligence**: Track enemy fleet compositions and doctrine changes
4. **Supply Chain**: Pre-position war materials based on actual consumption data

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Sources                                 │
├─────────────────────────────┬───────────────────────────────────┤
│  zkillboard Live Stream     │  battles table (completed)        │
│  (Real-time kills)          │  (Historical battle data)         │
└──────────────┬──────────────┴──────────────┬────────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐   ┌──────────────────────────────────┐
│  FleetSnapshotCollector  │   │  doctrine_from_battles.py        │
│  (5-min windows)         │   │  (Daily extraction job)          │
└───────────┬──────────────┘   └──────────────┬───────────────────┘
            │                                  │
            ▼                                  │
┌──────────────────────────┐                   │
│  DBSCAN Clustering       │                   │
│  (Pattern detection)     │                   │
└───────────┬──────────────┘                   │
            │                                  │
            └──────────────┬───────────────────┘
                           ▼
             ┌──────────────────────────────────┐
             │  doctrine_templates              │
             │  (Detected doctrines)            │
             └──────────────┬───────────────────┘
                            │
                            ▼
             ┌──────────────────────────────────┐
             │  ItemsDeriver                    │
             │  - Extracts from killmail_items  │
             │  - Groups by category            │
             └──────────────┬───────────────────┘
                            │
                            ▼
             ┌──────────────────────────────────┐
             │  doctrine_items_of_interest      │
             │  (Real consumption data)         │
             └──────────────┬───────────────────┘
                            │
                            ▼
             ┌──────────────────────────────────┐
             │  Production Materials API        │
             │  (industryActivityMaterials)     │
             └──────────────────────────────────┘
```

### Data Flow

1. **Battle Extraction** (Daily): battles → doctrine_from_battles.py → doctrine_templates
2. **Items Derivation**: doctrine_templates → ItemsDeriver → doctrine_items_of_interest
3. **Materials Query**: doctrine_items → industryActivityProducts → industryActivityMaterials

---

## Data Sources

### Primary: Battle-based Extraction

Doctrines are primarily extracted from completed battles, providing accurate fleet compositions:

- **Source Table**: `battles` (from zkillboard live service)
- **Minimum Size**: 30+ kills per battle
- **Naming**: `"{Top Ship} Fleet (Battle {id})"`
- **Composition**: Ship types with ratio based on attacker count

**Advantages:**
- Complete fleet visibility (sees all attackers across killmails)
- Accurate composition ratios
- Real consumption data from destroyed items

### Secondary: Live Snapshot Clustering

DBSCAN clustering of real-time zkillboard data:

- **Source**: zkillboard RedisQ live stream
- **Aggregation**: 5-minute time windows
- **Algorithm**: DBSCAN with cosine similarity
- **Minimum Samples**: 5 observations

**Use Case:** Detecting emerging doctrines before major battles complete.

---

## Database Schema

### doctrine_templates

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `doctrine_name` | VARCHAR(100) | Name (e.g., "Raven Fleet (Battle 3034)") |
| `alliance_id` | INTEGER | Alliance ID (if detected) |
| `region_id` | INTEGER | Primary region |
| `composition` | JSONB | Ship distribution `{"type_id": ratio}` |
| `confidence_score` | FLOAT | Statistical confidence (0.0-1.0) |
| `observation_count` | INTEGER | Number of kills/observations |
| `first_seen` | TIMESTAMP | First observation |
| `last_seen` | TIMESTAMP | Most recent observation |
| `total_pilots_avg` | INTEGER | Average fleet size estimate |
| `primary_doctrine_type` | VARCHAR(50) | 'subcap', 'capital', 'supercap' |

### doctrine_items_of_interest

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `doctrine_id` | INTEGER | FK to doctrine_templates |
| `type_id` | INTEGER | EVE item type ID |
| `item_name` | VARCHAR(200) | Item name from SDE |
| `item_category` | VARCHAR(50) | 'ammunition', 'fuel', 'module', 'drone' |
| `consumption_rate` | FLOAT | Actual quantity destroyed in battle |
| `priority` | INTEGER | 1=critical, 2=high, 3=medium |

**Item Categories:**
- `ammunition`: Missiles, charges, crystals, bombs
- `fuel`: Isotopes, Strontium Clathrates
- `module`: Nanite Repair Paste, Cap Boosters, Probes
- `drone`: Combat drones, fighters

---

## Core Components

### ItemsDeriver (v2 - Killmail-based)

**Location:** `services/war_economy/doctrine/items_deriver.py`

**Purpose:** Extracts consumed items from actual killmail data.

**How it works:**
1. Parses battle ID from doctrine name: `"Raven Fleet (Battle 3034)"` → `3034`
2. Queries `killmail_items` table for destroyed items in that battle
3. Groups items by category (ammunition, fuel, module, drone)
4. Adds critical fallback items (Nanite, Strontium) if not present

**SQL Query:**
```sql
SELECT item_type_id, type_name, group_name, SUM(quantity)
FROM killmail_items i
JOIN killmails k ON i.killmail_id = k.killmail_id
JOIN invTypes t ON i.item_type_id = t.typeID
JOIN invGroups g ON t.groupID = g.groupID
WHERE k.battle_id = ? AND i.was_destroyed = true
GROUP BY item_type_id, type_name, group_name
```

**Category Mapping:**
```python
ITEM_CATEGORIES = {
    "Hybrid Charge": "ammunition",
    "Cruise Missile": "ammunition",
    "Heavy Missile": "ammunition",
    "Ice Product": "fuel",
    "Fuel Block": "fuel",
    "Nanite Repair Paste": "module",
    "Cap Booster Charge": "module",
    "Combat Drone": "drone",
    "Fighter": "drone",
}
```

### doctrine_from_battles.py

**Location:** `jobs/doctrine_from_battles.py`

**Purpose:** Daily job to extract doctrines from completed battles.

**Process:**
1. Query battles with 30+ kills from last 48 hours
2. For each battle, get attacker ship composition
3. Create doctrine template with normalized ratios
4. Skip if doctrine with same name already exists

**Execution:**
```bash
python3 jobs/doctrine_from_battles.py
```

**Cron Setup:**
```bash
0 7 * * * cd /home/cytrex/eve_copilot && python3 jobs/doctrine_from_battles.py >> logs/doctrine_battles.log 2>&1
```

---

## API Reference

Base URL: `/api/war/economy/doctrines`

### GET /economy/doctrines

List all detected doctrines with pagination and filtering.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max results (1-500) |
| `offset` | int | 0 | Skip N results |
| `region_id` | int | - | Filter by region |
| `alliance_id` | int | - | Filter by alliance |
| `doctrine_type` | str | - | 'subcap', 'capital', 'supercap' |
| `since` | ISO date | - | Filter by last_seen |

**Response:**
```json
{
  "doctrines": [
    {
      "id": 3,
      "doctrine_name": "Raven Fleet (Battle 3034)",
      "alliance_id": null,
      "alliance_name": null,
      "region_id": 10000002,
      "region_name": "The Forge",
      "composition": {"638": 0.60, "11190": 0.25},
      "composition_with_names": [
        {"type_id": 638, "type_name": "Raven", "ratio": 0.60},
        {"type_id": 11190, "type_name": "Machariel", "ratio": 0.25}
      ],
      "confidence_score": 0.95,
      "observation_count": 150,
      "total_pilots_avg": 45,
      "primary_doctrine_type": "subcap"
    }
  ],
  "total": 66
}
```

### GET /economy/doctrines/{id}/items

Get items consumed by a doctrine.

**Response:**
```json
{
  "items": [
    {
      "id": 1477,
      "doctrine_id": 3,
      "type_id": 27377,
      "item_name": "Caldari Navy Mjolnir Cruise Missile",
      "item_category": "ammunition",
      "consumption_rate": 497991.0,
      "priority": 1
    }
  ]
}
```

### GET /economy/doctrines/{id}/items/materials *(NEW)*

Get items with their production materials for manufacturing.

**Response:**
```json
{
  "items": [
    {
      "id": 1478,
      "doctrine_id": 3,
      "type_id": 12612,
      "item_name": "Void S",
      "item_category": "ammunition",
      "consumption_rate": 494830.0,
      "priority": 1,
      "blueprint_id": 12613,
      "blueprint_name": "Void S Blueprint",
      "produced_quantity": 5000,
      "materials": [
        {"type_id": 16670, "type_name": "Crystalline Carbonide", "quantity": 60},
        {"type_id": 16679, "type_name": "Fullerides", "quantity": 60},
        {"type_id": 11399, "type_name": "Morphite", "quantity": 1}
      ]
    }
  ],
  "total_materials": {
    "16670": {"type_id": 16670, "type_name": "Crystalline Carbonide", "quantity": 120},
    "16679": {"type_id": 16679, "type_name": "Fullerides", "quantity": 3060}
  }
}
```

**Notes:**
- Items without blueprints (faction drops) have `materials: []`
- `total_materials` aggregates all materials across manufacturable items
- `produced_quantity` shows units per blueprint run

### POST /economy/doctrines/{id}/rename

Manually rename a doctrine.

**Request:**
```json
{"doctrine_name": "Goonswarm Shield Ravens"}
```

### POST /economy/doctrines/recluster

Trigger DBSCAN clustering job manually.

**Request:**
```json
{"hours_back": 168}
```

---

## Frontend Integration

### Doctrines Page

**Location:** `public-frontend/src/pages/Doctrines.tsx`

**Features:**
- List all doctrines with filtering by region and confidence
- Expandable cards showing:
  - Ship composition with names
  - Items grouped by category (ammunition, fuel, module, drone)
  - Production materials for manufacturable items
  - Total materials summary

**API Calls:**
- `doctrineApi.getDoctrineTemplates()` - List doctrines
- `doctrineApi.getDoctrineItemsWithMaterials()` - Items + materials

**Item Display:**
- Shows consumption rate formatted (k, M suffixes)
- Items without rates show "Essential" in purple
- Materials shown inline with blueprint info

### Types

**Location:** `public-frontend/src/types/reports.ts`

```typescript
interface DoctrineTemplate {
  id: number;
  doctrine_name: string;
  region_id: number;
  region_name: string | null;  // From SDE
  composition_with_names: ShipComposition[] | null;
  confidence_score: number;
  // ...
}

interface ItemWithMaterials {
  type_id: number;
  item_name: string;
  item_category: 'ammunition' | 'fuel' | 'module' | 'drone';
  consumption_rate: number | null;
  materials: ProductionMaterial[];
  blueprint_id: number | null;
  blueprint_name: string | null;
  produced_quantity: number;
}

interface ProductionMaterial {
  type_id: number;
  type_name: string;
  quantity: number;
}
```

---

## Background Jobs

### doctrine_from_battles.py

**Schedule:** Daily at 07:00 UTC

**Purpose:** Extract doctrines from completed battles.

**Configuration:**
```python
MIN_BATTLE_KILLS = 30    # Minimum kills for a battle
TOP_SHIPS = 15           # Top N ships in composition
```

**Cron:**
```bash
0 7 * * * cd /home/cytrex/eve_copilot && python3 jobs/doctrine_from_battles.py >> logs/doctrine_battles.log 2>&1
```

### doctrine_clustering.py

**Schedule:** Daily at 06:00 UTC

**Purpose:** DBSCAN clustering of live snapshots.

**Cron:**
```bash
0 6 * * * cd /home/cytrex/eve_copilot && python3 jobs/doctrine_clustering.py >> logs/doctrine_clustering.log 2>&1
```

---

## Configuration

### ItemsDeriver Categories

Edit `ITEM_CATEGORIES` in `services/war_economy/doctrine/items_deriver.py`:

```python
ITEM_CATEGORIES = {
    # Ammunition
    "Hybrid Charge": "ammunition",
    "Cruise Missile": "ammunition",
    # Fuel
    "Ice Product": "fuel",
    "Fuel Block": "fuel",
    # Modules
    "Nanite Repair Paste": "module",
    # Drones
    "Combat Drone": "drone",
}
```

### Clustering Parameters

Edit `services/war_economy/doctrine/clustering_service.py`:

```python
epsilon = 0.3        # 30% dissimilarity threshold
min_samples = 5      # Minimum observations per cluster
```

---

## Troubleshooting

### No doctrines detected

**Check battles table:**
```bash
psql -U eve -d eve_sde -c "SELECT COUNT(*) FROM battles WHERE total_kills >= 30"
```

**Run extraction manually:**
```bash
python3 jobs/doctrine_from_battles.py
```

### Items have no consumption_rate

This is expected for:
- **Unnamed Doctrines**: From live snapshots without battle data
- **Fallback items**: Nanite, Strontium added as essential without quantities

These show "Essential" in the UI.

### Materials not showing

Check if item has a blueprint:
```sql
SELECT * FROM "industryActivityProducts"
WHERE "productTypeID" = {type_id} AND "activityID" = 1
```

Faction items (Caldari Navy, Republic Fleet, etc.) don't have blueprints.

### Region names missing

Region names are loaded from `mapRegions` SDE table:
```sql
SELECT "regionID", "regionName" FROM "mapRegions" WHERE "regionID" = 10000002
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-15 | Battle-based extraction, killmail items, production materials |
| 1.0.0 | 2026-01-14 | Initial: DBSCAN clustering, manual item mappings |

---

**Last Updated:** 2026-01-15
