from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from core.middleware import RequestContextMiddleware
from exceptions.common import BadRequestError
from exceptions.handlers import (
    http_exception_handler,
    mileday_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from exceptions.base import MileDayBaseException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class Payload(BaseModel):
    count: int


def build_error_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(MileDayBaseException, mileday_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/domain")
    def domain_error() -> None:
        raise BadRequestError(
            message="Invalid payload.",
            detail={"password": "secret", "email": "tester@example.com"},
        )

    @app.post("/validation")
    def validation_error(payload: Payload) -> dict[str, int]:
        return {"count": payload.count}

    @app.get("/http")
    def http_error() -> None:
        raise HTTPException(status_code=404, detail="Missing")

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("database password leaked")

    return app


def test_domain_error_response_masks_detail() -> None:
    client = TestClient(build_error_app(), raise_server_exceptions=False)
    response = client.get("/domain", headers={"X-Request-ID": "req-domain"})

    assert response.status_code == 400
    body = response.json()
    assert body["request_id"] == "req-domain"
    assert body["error"]["code"] == "BAD_REQUEST"
    assert body["error"]["detail"]["password"] == "[MASKED]"
    assert body["error"]["detail"]["email"] == "te***@example.com"


def test_validation_error_response_uses_400() -> None:
    client = TestClient(build_error_app(), raise_server_exceptions=False)
    response = client.post("/validation", json={"count": "not-int"})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "BAD_REQUEST"
    assert body["error"]["message"] == "Invalid request."


def test_http_exception_response_maps_error_code() -> None:
    client = TestClient(build_error_app(), raise_server_exceptions=False)
    response = client.get("/http")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_unhandled_error_response_hides_internal_message() -> None:
    client = TestClient(build_error_app(), raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "Internal server error."
    assert "database password leaked" not in str(body)
