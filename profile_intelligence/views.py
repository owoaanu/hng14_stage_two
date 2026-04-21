import re

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Profile
from .serializers import ProfileSerializer


REAL_FILTER_PARAMS = {
    "gender",
    "age_group",
    "country_id",
    "min_age",
    "max_age",
    "min_gender_probability",
    "min_country_probability",
}
DATA_CONTROL_PARAMS = {"page", "limit", "sort_by", "order"}
PROFILE_PARAMS = REAL_FILTER_PARAMS | DATA_CONTROL_PARAMS
SEARCH_PARAMS = {"q", "page", "limit", "sort_by", "order"}

GENDERS = {"male", "female"}
AGE_GROUPS = {"child", "teenager", "adult", "senior"}
DATA_SORT_FIELDS = {"age", "created_at", "gender_probability"}
ORDERS = {"asc", "desc"}


COUNTRY_ALIASES = {
    "nigeria": "NG",
}


class QueryParameterError(ValueError):
    def __init__(self, http_status=422):
        self.http_status = http_status


def error_response(message, http_status):
    return Response(
        {"status": "error", "message": message},
        status=http_status,
    )


def invalid_query(http_status=422):
    return error_response("Invalid query parameters", http_status)


def parse_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise QueryParameterError

    if parsed < 1:
        raise QueryParameterError
    return parsed


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise QueryParameterError


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise QueryParameterError


def reject_empty_values(params):
    for value in params.values():
        if value == "":
            raise QueryParameterError(400)


def validate_allowed_param_names(params, allowed_params):
    if set(params.keys()) - allowed_params:
        raise QueryParameterError


def validate_allowed_params(params, allowed_params):
    validate_allowed_param_names(params, allowed_params)
    reject_empty_values(params)


def normalize_gender(value):
    normalized_gender = value.lower()
    if normalized_gender not in GENDERS:
        raise QueryParameterError
    return normalized_gender


def normalize_age_group(value):
    normalized = value.lower()
    if normalized not in AGE_GROUPS:
        raise QueryParameterError
    return normalized


def normalize_country_id(value):
    normalized = value.upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise QueryParameterError
    return normalized


def parse_pagination(params):
    page = parse_positive_int(params.get("page", "1"))
    limit = parse_positive_int(params.get("limit", "10"))
    if limit > 50:
        raise QueryParameterError
    return page, limit


def parse_sorting(params):
    sort_by = params.get("sort_by", "created_at")
    order = params.get("order", "desc")

    if sort_by not in DATA_SORT_FIELDS or order not in ORDERS:
        raise QueryParameterError

    prefix = "" if order == "asc" else "-"
    return f"{prefix}{sort_by}"


def apply_filters(queryset, filters):
    if "gender" in filters:
        queryset = queryset.filter(gender=normalize_gender(filters["gender"]))
    if "age_group" in filters:
        queryset = queryset.filter(age_group=normalize_age_group(filters["age_group"]))
    if "country_id" in filters:
        queryset = queryset.filter(country_id=normalize_country_id(filters["country_id"]))
    if "min_age" in filters:
        queryset = queryset.filter(age__gte=parse_int(filters["min_age"]))
    if "max_age" in filters:
        queryset = queryset.filter(age__lte=parse_int(filters["max_age"]))
    if "min_gender_probability" in filters:
        queryset = queryset.filter(
            gender_probability__gte=parse_float(filters["min_gender_probability"])
        )
    if "min_country_probability" in filters:
        queryset = queryset.filter(
            country_probability__gte=parse_float(filters["min_country_probability"])
        )

    if "min_age" in filters and "max_age" in filters:
        if parse_int(filters["min_age"]) > parse_int(filters["max_age"]):
            raise QueryParameterError

    return queryset


def paginated_response(queryset, params):
    page, limit = parse_pagination(params)
    ordering = parse_sorting(params)
    queryset = queryset.order_by(ordering, "id")
    total = queryset.count()
    offset = (page - 1) * limit
    serializer = ProfileSerializer(queryset[offset : offset + limit], many=True)

    return Response(
        {
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "data": serializer.data,
        }
    )


def normalize_search_query(query):
    query = query.lower().strip()
    query = re.sub(r"\b(females|women|woman)\b", "female", query)
    query = re.sub(r"\b(males|men|man)\b", "male", query)
    query = re.sub(r"\bteenagers\b", "teenager", query)
    query = re.sub(r"\badults\b", "adult", query)
    query = re.sub(r"\bchildren\b", "child", query)
    query = re.sub(r"\bseniors\b", "senior", query)
    return re.sub(r"\s+", " ", query)


def country_map():
    countries = dict(COUNTRY_ALIASES)
    for country_name, country_id in (
        Profile.objects.exclude(country_name="")
        .values_list("country_name", "country_id")
        .distinct()
    ):
        countries[country_name.lower()] = country_id.upper()
    return countries


def detect_country(query):
    match = re.search(r"\bfrom\s+([a-z ]+?)(?:\s+(?:above|over|under|below)\b|$)", query)
    if not match:
        return None

    candidate = match.group(1).strip()
    countries = country_map()
    if candidate in countries:
        return countries[candidate]

    words = candidate.split()
    for end in range(len(words), 0, -1):
        name = " ".join(words[:end])
        if name in countries:
            return countries[name]

    return None


def parse_natural_language_query(raw_query):
    query = normalize_search_query(raw_query)
    filters = {}

    has_male = bool(re.search(r"\bmale\b", query))
    has_female = bool(re.search(r"\bfemale\b", query))
    if has_male ^ has_female:
        filters["gender"] = "male" if has_male else "female"

    for age_group in AGE_GROUPS:
        if re.search(rf"\b{age_group}\b", query):
            filters["age_group"] = age_group
            break

    if re.search(r"\byoung\b", query):
        filters["min_age"] = "16"
        filters["max_age"] = "24"

    above_match = re.search(r"\b(?:above|over|older than)\s+(\d+)\b", query)
    if above_match:
        filters["min_age"] = above_match.group(1)

    below_match = re.search(r"\b(?:below|under|younger than)\s+(\d+)\b", query)
    if below_match:
        filters["max_age"] = below_match.group(1)

    country_id = detect_country(query)
    if country_id:
        filters["country_id"] = country_id
    elif re.search(r"\bfrom\b", query):
        return None

    return filters or None


@api_view(["GET"])
def profile_list(request):
    try:
        params = request.query_params.dict()
        validate_allowed_params(params, PROFILE_PARAMS)
        queryset = apply_filters(Profile.objects.all(), params)
        return paginated_response(queryset, params)
    except QueryParameterError as exc:
        return invalid_query(exc.http_status)


@api_view(["GET"])
def profile_search(request):
    try:
        params = request.query_params.dict()
        validate_allowed_param_names(params, SEARCH_PARAMS)
        query = params.get("q")
        if query is None or not query.strip():
            return invalid_query(400)
        reject_empty_values(params)

        parsed_filters = parse_natural_language_query(query)
        if not parsed_filters:
            return error_response(
                "Unable to interpret query",
                400,
            )

        query_params = {**params, **parsed_filters}
        query_params.pop("q", None)
        queryset = apply_filters(Profile.objects.all(), parsed_filters)
        return paginated_response(queryset, query_params)
    except QueryParameterError as exc:
        return invalid_query(exc.http_status)
