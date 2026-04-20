# Queryable Intelligence Engine Implementation Plan

## Goal

Upgrade the current profile API into a queryable demographic intelligence engine that supports:

- Advanced filtering
- Combined filters
- Sorting
- Pagination
- Rule-based natural language search
- Strict response and error formats for automated grading

This plan is for implementation guidance only. Code should be written and validated incrementally.

## Current Project Baseline

The project is a Django app with:

- `Profile` model in `profile_intelligence/models.py`
- `ProfileSerializer` in `profile_intelligence/serializers.py`
- Empty API views in `profile_intelligence/views.py`
- Only admin routes currently wired in `hng14_stage_two/urls.py`
- `profile_intelligence` not yet registered in `INSTALLED_APPS`
- `country_name` missing from the `Profile` model

## Required Endpoints

### List Profiles

```http
GET /api/profiles
```

Supports filtering, sorting, and pagination.

### Natural Language Search

```http
GET /api/profiles/search?q=young males from nigeria
```

Interprets plain English queries using rule-based parsing only.

## Required Database Schema

The `profiles` table must contain exactly these core fields:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID v7 | Primary key |
| `name` | VARCHAR + UNIQUE | Person's full name |
| `gender` | VARCHAR | `male` or `female` |
| `gender_probability` | FLOAT | Confidence score |
| `age` | INT | Exact age |
| `age_group` | VARCHAR | `child`, `teenager`, `adult`, `senior` |
| `country_id` | VARCHAR(2) | ISO code, such as `NG`, `BJ`, `AO` |
| `country_name` | VARCHAR | Full country name |
| `country_probability` | FLOAT | Confidence score |
| `created_at` | TIMESTAMP | Auto-generated |

## Implementation Steps

## 1. Project Wiring

Register the app and API framework.

Checklist:

- Add `profile_intelligence` to `INSTALLED_APPS`.
- Add `rest_framework` to `INSTALLED_APPS` if using Django REST Framework.
- Wire these routes:
  - `/api/profiles`
  - `/api/profiles/search`
- Keep route paths exact because grading may be automated.

Recommended approach:

- Use DRF function-based views with `@api_view(["GET"])`, or DRF `APIView`.
- Keep response construction explicit so the output shape matches the task.

## 2. Model Schema Update

Update `Profile` so it fully matches the required schema.

Checklist:

- Add `country_name`.
- Keep `id` as UUID v7.
- Keep `name` unique.
- Consider making required fields non-null if the seed data always provides them.
- Add indexes for frequently queried fields.

Recommended indexed fields:

- `gender`
- `age_group`
- `country_id`
- `age`
- `gender_probability`
- `country_probability`
- `created_at`

Why:

- The dataset has only 2026 records, but indexes show correct query design and help avoid unnecessary full-table scans.

## 3. Serializer Update

Update the profile serializer.

Checklist:

- Include `country_name` in serialized output.
- Ensure `id` and `created_at` remain read-only.
- Confirm `created_at` serializes as UTC ISO 8601.

The serializer should only serialize profile records. The views should wrap results in the required response envelope.

## 4. Data Seeding

Create an idempotent database seed process.

Recommended approach:

- Add a Django management command, for example:

```text
profile_intelligence/management/commands/seed_profiles.py
```

Checklist:

- Load the provided 2026-profile data file.
- Insert records into the database.
- Re-running the seed must not create duplicates.
- Use `name` as the natural dedupe key because it is unique.
- Use `update_or_create()` or `get_or_create()`.
- Confirm exactly 2026 records exist after repeated runs.

Seed validation:

- First run creates 2026 profiles.
- Second run keeps total at 2026.
- Every record has a UUID v7 id.
- `country_id` is a two-letter ISO code.
- `country_name` is populated.
- `created_at` is generated automatically.

## 5. Shared Query Logic

Build reusable logic for:

- Query parameter validation
- Filtering
- Sorting
- Pagination
- Response formatting

This avoids duplicating behavior between:

- `/api/profiles`
- `/api/profiles/search`

Possible locations:

- Keep helpers inside `views.py` for a small submission.
- Or move them into `query_utils.py` for cleaner organization.

## 6. Advanced Filtering

Supported filters:

| Query Parameter | Behavior |
| --- | --- |
| `gender` | exact match |
| `age_group` | exact match |
| `country_id` | exact match |
| `min_age` | `age >= value` |
| `max_age` | `age <= value` |
| `min_gender_probability` | `gender_probability >= value` |
| `min_country_probability` | `country_probability >= value` |

Example:

```http
GET /api/profiles?gender=male&country_id=NG&min_age=25
```

Expected behavior:

- All filters are combinable.
- Combined filters use AND semantics.
- Results must strictly match all supplied conditions.

Validation checklist:

- Reject unknown query parameters.
- Reject empty query parameter values.
- Reject invalid numeric values.
- Reject invalid enum values.
- Reject `min_age > max_age`.

Allowed enum values:

| Field | Allowed Values |
| --- | --- |
| `gender` | `male`, `female` |
| `age_group` | `child`, `teenager`, `adult`, `senior` |

## 7. Sorting

Supported sorting parameters:

| Query Parameter | Allowed Values |
| --- | --- |
| `sort_by` | `age`, `created_at`, `gender_probability` |
| `order` | `asc`, `desc` |

Example:

```http
GET /api/profiles?sort_by=age&order=desc
```

Recommended default:

```text
sort_by=created_at
order=desc
```

Validation checklist:

- Reject unsupported `sort_by` values.
- Reject unsupported `order` values.
- If `order` is supplied without `sort_by`, apply it to the default sort field.

## 8. Pagination

Supported pagination parameters:

| Query Parameter | Default | Rule |
| --- | --- | --- |
| `page` | `1` | Must be positive integer |
| `limit` | `10` | Must be positive integer, maximum `50` |

Response format:

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "data": []
}
```

Important:

- `total` should be the number of records after filters are applied.
- Pagination should happen at the queryset/database level.
- Do not fetch all records and slice in Python.

Offset calculation:

```text
offset = (page - 1) * limit
```

Validation checklist:

- Reject `page < 1`.
- Reject `limit < 1`.
- Reject `limit > 50`.
- Reject non-integer page or limit values.

## 9. Natural Language Search

Endpoint:

```http
GET /api/profiles/search?q=young males from nigeria
```

Rules:

- Rule-based parsing only.
- No AI or LLM calls.
- Pagination applies here too.
- Parsed filters should reuse the same query logic as `/api/profiles`.

Required examples:

| Query | Parsed Filters |
| --- | --- |
| `young males` | `gender=male`, `min_age=16`, `max_age=24` |
| `females above 30` | `gender=female`, `min_age=30` |
| `people from angola` | `country_id=AO` |
| `adult males from kenya` | `gender=male`, `age_group=adult`, `country_id=KE` |
| `male and female teenagers above 17` | `age_group=teenager`, `min_age=17` |

Important parsing notes:

- `young` maps to ages `16-24` only for parsing.
- `young` is not a stored `age_group`.
- If both male and female appear in a query, treat that as no gender filter.
- Normalize plural words:
  - `males` -> `male`
  - `females` -> `female`
  - `teenagers` -> `teenager`
- Match country names case-insensitively.

Recommended parser flow:

1. Read `q`.
2. Reject missing or empty `q`.
3. Lowercase and normalize text.
4. Detect gender.
5. Detect age group.
6. Detect `young`.
7. Detect age phrases such as `above 30`.
8. Detect country from `from <country>`.
9. If no filters were found, return unable-to-interpret error.
10. Apply filters, sorting if supported, and pagination.

Possible country mapping strategies:

- Hardcode the countries needed by the seed data.
- Build a map from distinct `country_name` and `country_id` values in the database.
- Use a small explicit mapping for required examples and supplement from the database.

## 10. Error Responses

All errors must follow this structure:

```json
{
  "status": "error",
  "message": "<error message>"
}
```

Required messages:

Invalid query parameters:

```json
{
  "status": "error",
  "message": "Invalid query parameters"
}
```

Unable to interpret natural language query:

```json
{
  "status": "error",
  "message": "Unable to interpret query"
}
```

HTTP status guidance:

| Status | Use Case |
| --- | --- |
| `400 Bad Request` | Missing or empty required parameter |
| `422 Unprocessable Entity` | Invalid parameter type or invalid value |
| `404 Not Found` | Profile not found, if detail endpoints exist |
| `500/502` | Server failure |

For list endpoints, no matching profiles should return success with empty data:

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 0,
  "data": []
}
```

## 11. CORS

Requirement:

```http
Access-Control-Allow-Origin: *
```

Implementation options:

- Use `django-cors-headers` and set `CORS_ALLOW_ALL_ORIGINS = True`.
- Or add the header manually to every API response.

Recommended:

- Use `django-cors-headers` if dependency management is allowed.
- Otherwise, centralize response creation so the header is consistently attached.

## 12. Timestamp and ID Requirements

Checklist:

- `created_at` must be UTC.
- Timestamp output must be ISO 8601.
- `id` must be UUID v7.

Current settings already help:

```python
TIME_ZONE = "UTC"
USE_TZ = True
```

Expected timestamp style:

```json
"created_at": "2026-04-20T12:34:56Z"
```

or:

```json
"created_at": "2026-04-20T12:34:56.123456Z"
```

## 13. Testing Plan

Add tests around grading-critical behavior.

Minimum tests:

- `/api/profiles` returns the required success envelope.
- Default pagination returns `page=1` and `limit=10`.
- `limit=50` works.
- `limit=51` fails.
- Filtering by `gender` works.
- Filtering by `country_id` works.
- Combined filters use AND semantics.
- `min_age` and `max_age` work.
- Sorting by age ascending works.
- Sorting by age descending works.
- Unknown query parameter fails.
- Invalid integer parameter fails.
- Missing `q` on `/api/profiles/search` fails.
- Empty `q` on `/api/profiles/search` fails.
- `young males` parses correctly.
- `females above 30` parses correctly.
- `people from angola` parses correctly.
- `adult males from kenya` parses correctly.
- `male and female teenagers above 17` parses correctly.
- Uninterpretable query returns the exact error message.

## Suggested Build Order

1. Register app and DRF in settings.
2. Add URL routes.
3. Update the model schema with `country_name`.
4. Create and run migrations.
5. Update serializer fields.
6. Build the seed command.
7. Seed and verify exactly 2026 profiles.
8. Implement shared query validation and pagination helpers.
9. Implement `/api/profiles`.
10. Implement the rule-based natural language parser.
11. Implement `/api/profiles/search`.
12. Add CORS.
13. Add tests.
14. Run migrations, seed command, and test suite.
15. Verify sample requests manually.

## Manual Verification Requests

Use these sample requests after implementation:

```http
GET /api/profiles
GET /api/profiles?page=1&limit=10
GET /api/profiles?gender=male
GET /api/profiles?gender=male&country_id=NG&min_age=25
GET /api/profiles?sort_by=age&order=desc
GET /api/profiles?limit=51
GET /api/profiles?unknown=value
GET /api/profiles/search?q=young males
GET /api/profiles/search?q=females above 30
GET /api/profiles/search?q=people from angola
GET /api/profiles/search?q=adult males from kenya
GET /api/profiles/search?q=male and female teenagers above 17
GET /api/profiles/search?q=
GET /api/profiles/search?q=random words that mean nothing
```

## Review Checklist

Use this checklist when validating changes:

- Database schema includes every required field.
- `country_name` is present in model and serializer.
- UUIDs are UUID v7.
- Seeding is idempotent.
- Seeded database contains 2026 profiles.
- `/api/profiles` exists.
- `/api/profiles/search` exists.
- Success response shape matches exactly.
- Error response shape matches exactly.
- Filters combine correctly.
- Unknown query parameters are rejected.
- Invalid query values are rejected.
- Sorting only allows required fields.
- Pagination defaults are correct.
- Pagination max limit is enforced.
- Natural language parser is rule-based.
- Required natural language examples work.
- CORS header is present.
- Timestamps are UTC ISO 8601.
- Tests cover the grading-critical behavior.
