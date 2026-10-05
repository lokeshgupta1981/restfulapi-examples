from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI()

AVAILABLE_TYPES = ["application/json", "text/csv"]

SALES_REPORT = {
    "month": "2026-09",
    "rows": [
        {"region": "north", "orders": 412, "revenue": "18350.00"},
        {"region": "south", "orders": 287, "revenue": "12990.50"},
    ],
}


def parse_accept(accept_header: str) -> list[tuple[str, float]]:
    """Turn 'text/csv;q=0.5, application/json' into [(media_range, q), ...]."""
    ranges = []
    for part in accept_header.split(","):
        pieces = [piece.strip() for piece in part.split(";")]
        media_range = pieces[0].lower()
        if not media_range:
            continue
        quality = 1.0
        for param in pieces[1:]:
            name, _, value = param.partition("=")
            if name.strip().lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        ranges.append((media_range, quality))
    return ranges


def quality_for(media_type: str, ranges: list[tuple[str, float]]) -> float:
    """Use the most specific matching range: type/subtype, then type/*, then */*."""
    main_type = media_type.split("/")[0]
    for candidate in (media_type, main_type + "/*", "*/*"):
        for media_range, quality in ranges:
            if media_range == candidate:
                return quality
    return 0.0


def choose_media_type(accept_header: str | None) -> str | None:
    if not accept_header:
        return AVAILABLE_TYPES[0]
    ranges = parse_accept(accept_header)
    best_type, best_quality = None, 0.0
    for media_type in AVAILABLE_TYPES:
        quality = quality_for(media_type, ranges)
        if quality > best_quality:
            best_type, best_quality = media_type, quality
    return best_type


def report_as_csv(report: dict) -> str:
    lines = ["region,orders,revenue"]
    for row in report["rows"]:
        lines.append(f'{row["region"]},{row["orders"]},{row["revenue"]}')
    return "\n".join(lines) + "\n"


def not_acceptable_response(month: str, accept_header: str | None) -> JSONResponse:
    problem = {
        "type": "https://example.com/problems/not-acceptable",
        "title": "Not Acceptable",
        "status": 406,
        "detail": f"No available format matches Accept: {accept_header}",
        "available": [
            {"type": "application/json", "href": f"/reports/{month}"},
            {"type": "text/csv", "href": f"/reports/{month}"},
        ],
    }
    return JSONResponse(
        problem,
        status_code=406,
        media_type="application/problem+json",
        headers={"Vary": "Accept"},
    )


@app.get("/reports/{month}")
def sales_report(month: str, request: Request):
    accept_header = request.headers.get("accept")
    media_type = choose_media_type(accept_header)
    vary_header = {"Vary": "Accept"}
    if media_type is None:
        return not_acceptable_response(month, accept_header)

    if media_type == "text/csv":
        return PlainTextResponse(
            report_as_csv(SALES_REPORT), media_type="text/csv", headers=vary_header
        )
    return JSONResponse(SALES_REPORT, headers=vary_header)


@app.get("/plain-reports/{month}")
def plain_sales_report(month: str):
    # A normal FastAPI route: it never looks at Accept.
    return SALES_REPORT
