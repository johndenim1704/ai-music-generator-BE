from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import log_event
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from utils.limiter import limiter
import os
from datetime import datetime

from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.music import router as music_router
from routers.playlists import router as playlists_router
from routers.history import router as history_router
from routers.licenses import router as licenses_router
from routers.cart import router as cart_router
from routers.payments import router as payments_router
from routers.admin import router as admin_router
from routers.offers import router as offers_router
from routers.coupons import router as coupons_router
from routers.marketing import router as marketing_router
from routers.mastering import router as mastering_router
from routers.thumbnail import router as thumbnail_router
from routers.track_title import router as track_title_router
# from routers.album_cover import router as album_cover_router  # Disabled: Stable Diffusion removed to save memory
from routers.video import router as video_router
from routers.system_logs import router as logs_router
from utils.deps import get_db
# from app.utils.foo import bar

app = FastAPI(max_request_size=1024 * 1024 * 1024)

# Register the limiter with the application
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS Configuration (use environment variable for production)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Use env var in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Content-Length", "Content-Type"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log the incoming request
    log_event("info", f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        log_event("info", f"Response: {response.status_code} for {request.url.path}")
        return response
    except Exception as e:
        log_event("error", f"Request failed: {str(e)}", {"path": request.url.path})
        raise

@app.get("/")
def root():
    return {"message": "Welcome to the AI Music Generation API"}


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for monitoring
    Checks database, Redis, and critical services
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        from utils.cache import cache
        if cache.enabled:
            cache.client.ping()
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "disabled"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
    
    # Check Ollama
    try:
        import requests
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code == 200:
            health_status["services"]["ollama"] = "healthy"
        else:
            health_status["services"]["ollama"] = f"unhealthy: status {response.status_code}"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["ollama"] = f"unhealthy: {str(e)}"
    
    return health_status


# Include routers

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(music_router)
app.include_router(playlists_router)
app.include_router(history_router)
app.include_router(licenses_router)
app.include_router(cart_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(offers_router)
app.include_router(coupons_router)
app.include_router(marketing_router)
app.include_router(mastering_router)
app.include_router(thumbnail_router)
app.include_router(track_title_router)
# app.include_router(album_cover_router)  # Disabled: Stable Diffusion removed to save memory
app.include_router(video_router)
app.include_router(logs_router)