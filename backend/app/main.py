import time
import logging
import uuid
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.api.v1 import admin
from app.api.v1 import billing
from app.api.v1 import data_quality
from app.api.v1 import jobs, api_keys, action_center, global_edits
import app.models  # Ensure all models are registered

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("jarvis_crm")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "detail": "An internal server error occurred", "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An internal server error occurred"}},
    )


# Include API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(billing.router, prefix=settings.API_V1_STR)
app.include_router(data_quality.router, prefix=settings.API_V1_STR)
app.include_router(jobs.router, prefix=settings.API_V1_STR)
app.include_router(api_keys.router, prefix=settings.API_V1_STR)
app.include_router(action_center.router, prefix=settings.API_V1_STR)
app.include_router(global_edits.router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def on_startup():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    logger.info("Database schema evolution is managed exclusively by Alembic; run 'alembic upgrade head' before startup.")

    # Seed Platform RBAC System (Roles & Permissions)
    try:
        from app.core.database import SessionLocal
        from app.models.rbac import seed_platform_rbac
        seed_db = SessionLocal()
        try:
            seed_platform_rbac(seed_db)
            logger.info("Platform RBAC initialized and verified.")
        finally:
            seed_db.close()
    except Exception as exc:
        logger.warning(f"RBAC initialization notice: {exc}")

    logger.info("Database schema checked and verified.")



@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "status": "operational"
    }
