import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUESTS = Counter("pantry_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("pantry_http_request_duration_seconds", "Request latency in seconds", ["method", "route"],
                    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5))
IN_FLIGHT = Gauge("pantry_http_in_flight_requests", "Requests currently being handled")
ITEMS_ADDED = Counter("pantry_items_added_total", "Items added to the pantry")
CONSUMED = Counter("pantry_consumed_total", "Quantity consumed, by unit", ["unit"])


def _route(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "__unmatched__")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def record(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        IN_FLIGHT.inc()
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = _route(request)
            LATENCY.labels(request.method, route).observe(time.perf_counter() - start)
            REQUESTS.labels(request.method, route, str(status)).inc()
            IN_FLIGHT.dec()

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
