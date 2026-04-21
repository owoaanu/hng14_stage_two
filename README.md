# Insighta Labs: Queryable Intelligence Engine (Django)

Demographic profile API with advanced filtering, sorting, pagination, and a rule-based natural language search layer.

## Tech

- Python + Django 6 + Django REST Framework
- PostgreSQL connection in settings.py
- UUID v7 primary keys
- CORS enabled via `django-cors-headers` 

## Quick Start

1. Install deps:

```bash
python -m pip install -r requirements.txt
```

2. Run migrations:

```bash
python manage.py migrate
```

3. Seed the database (idempotent):

```bash
python manage.py seed_profiles
```

4. Run the server:

```bash
python manage.py runserver
```

## Data Seeding

Seed data lives in `seed_profiles.json` and contains 2026 profiles under the `profiles` key.

- Command: `python manage.py seed_profiles`
- Idempotency: re-running does not create duplicates (uses `name` as the unique key and performs `update_or_create`).

Optional: seed from a different file path:

```bash
python manage.py seed_profiles /path/to/seed_profiles.json
```

## API

Base endpoints:

- `GET /api/profiles`
- `GET /api/profiles/search`

All timestamps are UTC ISO 8601. All error responses share the same shape:

```json
{ "status": "error", "message": "<error message>" }
```

### 1. List Profiles

`GET /api/profiles`

Supports advanced filtering, sorting, and pagination.

#### Filters (combinable; AND semantics)

- `gender` (`male` | `female`)
- `age_group` (`child` | `teenager` | `adult` | `senior`)
- `country_id` (2-letter ISO code, e.g. `NG`)
- `min_age` (int)
- `max_age` (int)
- `min_gender_probability` (float)
- `min_country_probability` (float)

Example:

```http
GET /api/profiles?gender=male&country_id=NG&min_age=25
```

#### Sorting

- `sort_by` (`age` | `created_at` | `gender_probability`) default: `created_at`
- `order` (`asc` | `desc`) default: `desc`

Example:

```http
GET /api/profiles?sort_by=age&order=desc
```

#### Pagination

- `page` (default: `1`)
- `limit` (default: `10`, max: `50`)

Success response envelope:

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "data": []
}
```

### 2. Natural Language Search (Rule-Based)

`GET /api/profiles/search?q=<plain english>`

Pagination (`page`, `limit`) applies here too. Parsing is deterministic and rule-based (no AI/LLMs).

Examples:

- `young males` -> `gender=male` + `min_age=16` + `max_age=24`
- `females above 30` -> `gender=female` + `min_age=30`
- `people from angola` -> `country_id=AO`
- `adult males from kenya` -> `gender=male` + `age_group=adult` + `country_id=KE`
- `male and female teenagers above 17` -> `age_group=teenager` + `min_age=17` (gender is omitted when both are present)

Example request:

```http
GET /api/profiles/search?q=young%20males%20from%20nigeria&page=1&limit=10
```

If the query cannot be interpreted:

```json
{ "status": "error", "message": "Unable to interpret query" }
```

### Validation and Errors

Invalid parameters return:

```json
{ "status": "error", "message": "Invalid query parameters" }
```

Status codes used:

- `400 Bad Request`: missing/empty required parameter (e.g. `q=`)
- `422 Unprocessable Entity`: invalid parameter type/value (e.g. `limit=51`, unknown query param)

Note: unknown query parameters are rejected (not ignored).

## Development

Key files:

- `profile_intelligence/models.py` (Profile schema, UUID v7 PK)
- `profile_intelligence/views.py` (filter/sort/pagination + NL parsing)
- `profile_intelligence/management/commands/seed_profiles.py` (idempotent seeding)
- `hng14_stage_two/settings.py` (DRF + CORS settings)
- `hng14_stage_two/profile+intelligence/urls.py` (API routes)

