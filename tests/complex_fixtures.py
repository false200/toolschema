"""Complex real-world-style tools for end-to-end testing."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from toolschema import Field, tool


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@tool
def search_products(
    query: Annotated[str, Field(description="Search query", min_length=1)],
    category: Annotated[str, "Product category slug"],
    tags: list[str] | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    sort: SortOrder = SortOrder.ASC,
    limit: Annotated[int, Field(description="Max results", ge=1, le=100)] = 20,
    include_metadata: bool = False,
    filters: dict[str, str] | None = None,
    mode: Literal["fuzzy", "exact"] = "fuzzy",
) -> list[dict]:
    """Search the product catalog with filters and sorting."""
    sort_value = sort.value if isinstance(sort, SortOrder) else sort
    return [
        {
            "id": "prod-1",
            "name": f"{query} in {category}",
            "sort": sort_value,
            "mode": mode,
            "limit": limit,
            "include_metadata": include_metadata,
            "tags": tags or [],
            "filters": filters or {},
            "price_min": price_min,
            "price_max": price_max,
        }
    ]


def book_flight(
    origin: Annotated[str, Field(description="IATA airport code", pattern=r"^[A-Z]{3}$")],
    destination: Annotated[str, Field(description="IATA airport code", pattern=r"^[A-Z]{3}$")],
    passengers: Annotated[int, Field(ge=1, le=9)] = 1,
    cabin: Literal["economy", "business", "first"] = "economy",
    flexible_dates: bool = False,
) -> dict:
    """Book a one-way flight between two airports."""
    return {
        "origin": origin,
        "destination": destination,
        "passengers": passengers,
        "cabin": cabin,
        "flexible_dates": flexible_dates,
        "confirmation": "TS-12345",
    }
