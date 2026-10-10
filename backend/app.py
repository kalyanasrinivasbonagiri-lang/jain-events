from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError

from backend.db import client, create_indexes
from backend.routes.admin import router as admin_router
from backend.routes.events import router as events_router

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    client.admin.command("ping")
    create_indexes()
    yield
    client.close()


app = FastAPI(title="Event Registration Portal", version="1.0.0", lifespan=lifespan)
app.include_router(events_router)
app.include_router(admin_router)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content={"error": message})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid request data", "details": details},
    )


@app.exception_handler(PyMongoError)
async def database_error(_: Request, __: PyMongoError):
    return JSONResponse(
        status_code=503,
        content={"error": "MongoDB is unavailable or could not complete the request"},
    )


@app.get("/api/health")
def health():
    client.admin.command("ping")
    return {"status": "ok", "database": "event_portal"}


@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")


@app.get("/events")
def events_page():
    return FileResponse(FRONTEND / "events.html")


@app.get("/admin-login")
def admin_login_page():
    return FileResponse(FRONTEND / "admin-login.html")


@app.get("/admin")
def admin_shortcut():
    return FileResponse(FRONTEND / "admin-login.html")


@app.get("/admin/dashboard")
def admin_dashboard_page():
    return FileResponse(FRONTEND / "admin.html")


@app.get("/student-register")
def student_register_page():
    return FileResponse(FRONTEND / "student-login.html")


@app.get("/student-login")
def student_login_page():
    return FileResponse(FRONTEND / "student-login.html")


@app.get("/my-registrations")
def my_registrations_page():
    return FileResponse(FRONTEND / "my-registrations.html")


@app.get("/db-view")
def db_view_page():
    return FileResponse(FRONTEND / "db-view.html")
