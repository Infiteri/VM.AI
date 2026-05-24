# VM.AI — Image-to-Prompt Data Collection

Downloads and prepares training images for the image-to-prompt classifier (14 activity categories, ~1000 images each).

## Pipeline Overview

```
collect_data.py   →   raw/<category>/<source>/...
                         ↓  (copy)
prepare_data.py   →   selected/<category>/<source>/...
      Phase 0     →     creates selected/, copies raw/ → selected/
      Phase 1     →     flattens: selected/<cat>/<source>/... → selected/<cat>/<prefix>_<name>.jpg
      Phase 2     →     validates: remove corrupted → convert to JPG → filter <180px → deduplicate across categories
```

## Source Types

### OpenImages V7 (`fiftyone`)
Downloads images from Google's OpenImages V7 using category-specific object labels (e.g. `"Gas stove"`, `"Computer monitor"`, `"Dog"`). Labels are passed to `fiftyone.zoo.load_zoo_dataset("open-images-v7", label_types="detections", classes=[...])`. Target per category: 100–700 images depending on label count.

### Kaggle (`kagglehub`)
Four sub-handlers:
- **`kaggle`** — downloads a dataset and samples up to N images per subfolder (e.g. gym exercises, 32 per folder).
- **`kaggle_csv`** — downloads a dataset, reads a CSV, filters to rows matching a label (e.g. `"running"`), copies matching image files.
- **`kaggle_subfolder`** — downloads a dataset and uses a specific subfolder path (e.g. `HAR/train/running`).
- **`kaggle_csv_multi`** (via `kaggle_csv` with `filter_values`) — same as CSV but matches multiple labels at once.

### Pixabay API (`requests`)
Searches Pixabay (CC0 license, ML-safe) with category-specific keywords. `per_page=200`, paginated up to 500 images per keyword. Always downloads `largeImageURL` (1280px) with fallback to 960px. Rate-limit handled via `X-RateLimit-Remaining` header (pauses 60s if < 5 remaining).

## The 14 Categories

| # | Category | OpenImages | Kaggle | Pixabay Keywords | Pixabay Target |
|:--|:---------|:-----------|:------|:-----------------|:---------------|
| 1 | running | — | meetnagadia/har (800) + lumierebatalong/har (840) | person running | 400 |
| 2 | cycling | — | meetnagadia/har (800) + lumierebatalong/har (840) | cycling bicycle | 400 |
| 3 | cooking | Gas stove, Frying pan, Cutting board, Wok, Cooking spray, Kitchen utensil, Kitchenware, Slow cooker, Pressure cooker, Mixing bowl | dataclusterlabs/kitchen (400) | kitchen, cooking, cookware, kitchenware, chef stove | 500 |
| 4 | restaurant | Fast food, Kitchen & dining room table, Tableware, Coffee, Wine | kmader/food41 (900) | restaurant, cafe, restaurant inside | 300 |
| 5 | shopping | Convenience store, Cart, Plastic bag, Handbag | humansintheloop/supermarket (45) | grocery store, mall, clothes store | 1100 |
| 6 | office | Office building, Office supplies, Computer monitor, Whiteboard, Filing cabinet, Printer | sordi-ai/office (500) | office, office room, office desk | 500 |
| 7 | football | Football | ligtfeather/football-vs-rugby (900) | football | 300 |
| 8 | cleaning | Washing machine, Sink, Soap dispenser | — | cleaning, person cleaning house, mopping floor, washing dishes | 1000 |
| 9 | driving | Car, Seat belt, Land vehicle, Taxi | rightway11/state-farm-distracted (600) | person driving car, car | 200 |
| 10 | reading | Book, Bookcase | — | person reading book, reading, reading on the sofa, reading library, book, library | 2000 |
| 11 | computer work | Computer monitor, Computer keyboard, Laptop, Computer mouse | — | person and laptop, developer coding, work in laptop | 1200 |
| 12 | basketball | — | rishikeshkonapure/sports (486) + gpiosenka/sports (169) + ponrajsubramaniian/sport (495) + mmoreaux/caltech256 (90) + sheikhzaib/sports (486) | basketball, basketball field, basketball player | 1000 |
| 13 | pet care | Dog, Cat, Dog bed, Cat furniture | tongpython/cat-and-dog (700) | pet, person walking dog | 200 |
| 14 | gym | Dumbbell, Treadmill, Indoor rower, Stationary bicycle, Training bench, Punching bag, Horizontal bar | hasyimabdillah/workoutexercises (700) | gym workout | 200 |

## Usage

### 1. Setup

Ensure the Pixabay API key is set:

```
PIXABAY_API_KEY="your_key_here"
PIXABAY_BASE_URL="https://pixabay.com/api/"
```

Copy this to `src/image_to_promp/.env` or set the environment variable directly. The script loads `.env` automatically via `dotenv`.

### 2. Collect Raw Data

```bash
uv run python src/image_to_promp/collect_data.py
```

Runs all 15 categories. To run specific categories only:

```bash
uv run python src/image_to_promp/collect_data.py basketball computer_work
```

Each category downloads into `data/image_to_prompt/raw/<category>/<source>/` and writes a `metadata.json`.

### 3. Prepare & Validate

```bash
uv run python src/image_to_promp/prepare_data.py
```

Three phases:
- **Phase 0** — Deletes `selected/` if exists, recreates it, copies `raw/<category>/...` → `selected/<category>/...`
- **Phase 1** — Flattens `selected/<category>/<source>/filename.ext` → `selected/<category>/<source>_filename.ext`, removes source subdirs
- **Phase 2** — Per-image validation: opens & verifies, converts non-JPG to JPG, removes images < 180×180, deduplicates across all categories (keeps first occurrence)

## Folder Structure

After collection:

```
data/image_to_prompt/
  raw/
    running/
      openimages/   (if applicable)
      kaggle/       (if applicable)
      pixabay/      (if applicable)
      metadata.json
    ...
  selected/         (created by prepare_data.py)
    running/
      openimages_0000.jpg
      kaggle_0000.jpg
      pixabay_0000.jpg
    ...
```

## Source Files

| File | Purpose |
|------|---------|
| `src/image_to_promp/collect_data.py` | Download from all sources (5 handler types) |
| `src/image_to_promp/prepare_data.py` | Copy, flatten, validate, deduplicate |
| `src/image_to_promp/.env` | Pixabay API credentials (gitignored) |
| `src/image_to_promp/.env.example` | Template for `.env` |
| `src/backend/logs/notes.log` | Source-of-truth for per-category config (15 entries) |
