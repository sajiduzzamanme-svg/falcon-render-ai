"""Falcon Render AI — FastAPI application."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import health, renders

app = FastAPI(title="Falcon Render AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(renders.router, prefix="/api/v1", tags=["renders"])


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


# Map FastAPI request-validation failures onto the contract's error codes.
_VALIDATION_CODE_BY_FIELD = {
    "file": "INVALID_UPLOAD",
    "preset": "INVALID_PRESET",
    "style": "INVALID_STYLE",
}


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    code = "INVALID_REQUEST"
    messages: list[str] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = str(loc[-1]) if loc else ""
        mapped = _VALIDATION_CODE_BY_FIELD.get(field)
        if mapped and code == "INVALID_REQUEST":
            code = mapped
        messages.append(
            f"{field}: {err.get('msg', 'invalid')}" if field else str(err.get("msg"))
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(code, "; ".join(messages) or "Invalid request."),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak tracebacks or secrets to the client.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # Render HTTPException (raised by auth dependencies) in the app's
    # {"error": {"code", "message"}} convention instead of {"detail": ...}.
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": detail}
    else:
        body = _error_body("HTTP_ERROR", str(detail) if detail else "Request failed.")
    return JSONResponse(status_code=exc.status_code, content=body)
