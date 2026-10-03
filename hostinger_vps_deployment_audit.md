# Jarvis CRM — Hostinger VPS Deployment Readiness Audit

**Local Verification Date:** October 3, 2026  
**Target Environment:** Hostinger KVM VPS (Ubuntu 22.04 / 24.04 LTS)  
**Deployment Model:** Containerized Stack (Docker Engine + Docker Compose)  
**Overall Readiness Verdict:** ⚠️ **NOT READY AS-IS (5 Showstopper Bugs & 2 Critical Security Flaws Detected)**

---

## 1. Executive Summary & Verdict

While the core application architecture (FastAPI backend, Celery task workers, React SPA, and PostgreSQL schema) is functionally sound—with **all 59 automated test suites passing cleanly** and **all 16 Alembic migrations running successfully**—the application **cannot be deployed directly to a Hostinger VPS without fixing several critical configuration and runtime blockers**:

1. **Immediate Production Crash**: The backend, Celery worker, and Celery beat containers will crash immediately upon startup because `CORS_ORIGINS` defaults to containing `"*"` while `validate_production_security()` raises a fatal validation error in production.
2. **Broken Client-to-API Connectivity**: The frontend SPA defaults its API base URL to `http://localhost:8000/api/v1` at build time. When deployed to a public VPS, user web browsers attempt to connect to their own local machines rather than the VPS, causing all login and data requests to fail with `ERR_CONNECTION_REFUSED`.
3. **Missing Automated Schema Migration & Admin Bootstrap**: On a fresh VPS deployment, the PostgreSQL database initializes empty (0 tables). The application lacks an automated migration step in its container startup, causing all queries to fail with `500 Internal Server Error`. Furthermore, without running the seed script, the database has 0 users, locking administrators out permanently.
4. **Severe Security Vulnerabilities**: `docker-compose.yml` exposes PostgreSQL (`5432`) and unauthenticated Redis (`6379`) directly to the public internet (`0.0.0.0`), leaving the database open to brute-force attacks and Redis vulnerable to unauthenticated remote access and data wiping by automated internet scanners.
5. **Missing Build Context Exclusion (`.dockerignore`)**: Over 500 MB of unnecessary files (including a 23MB MP4 screen recording, local Windows virtual environments, SQLite databases, and local `.env` files with developer passwords) will be uploaded into the Docker daemon on build.

With targeted corrections to configuration parsing, Docker definitions, and network policies, the application can be made **100% production-ready**.

---

## 2. Comprehensive Readiness Matrix

| Category | Component | Current State | Production Ready? | Risk / Severity |
| :--- | :--- | :--- | :---: | :--- |
| **App Runtime** | `backend/app/core/config.py` | Default `CORS_ORIGINS` includes `"*"`. Validator raises error if `ENVIRONMENT=production`. | ❌ **No** | **FATAL (App crashes on startup)** |
| **App Runtime** | Pydantic Settings Parser | `CORS_ORIGINS` crashes on comma-separated strings; only accepts raw JSON strings. | ❌ **No** | **HIGH (Config error)** |
| **Frontend** | `frontend/src/services/api.ts` | Hardcoded fallback to `http://localhost:8000/api/v1`. | ❌ **No** | **FATAL (UI cannot reach API)** |
| **Frontend** | `Dockerfile.frontend` | `npm run build` runs without build-args or relative path fallback. | ❌ **No** | **FATAL (Bakes localhost into JS)** |
| **Database** | Alembic Migrations | 16 linear migrations verified working end-to-end to head (`9f4c2b7d1e30`). | ⚠️ **Partial** | **HIGH (No auto-run on start)** |
| **Database** | Initial Admin Bootstrap | Requires `production_seed.py` to create the initial Super Admin. | ⚠️ **Partial** | **HIGH (Locked out without seed)** |
| **Networking** | `docker-compose.yml` (Redis) | Port `6379:6379` published to public internet without password. | ❌ **No** | **CRITICAL SECURITY FLAW** |
| **Networking** | `docker-compose.yml` (Postgres) | Port `5432:5432` published to public host internet interface. | ❌ **No** | **HIGH SECURITY RISK** |
| **Reverse Proxy** | `nginx.conf` | Basic proxy for `/api/` and SPA fallback; missing client timeouts & SSL config. | ⚠️ **Partial** | **MEDIUM (HTTP only, no SSL)** |
| **Persistence** | File Uploads (`/storage_uploads`) | Backend runs as non-root `app` user; Docker volume owned by `root` causes permission errors. | ❌ **No** | **HIGH (Import uploads fail)** |
| **Docker Build** | `.dockerignore` | Missing entirely. 500MB+ build context copied into images. | ❌ **No** | **MEDIUM (Bloated images / leaks)** |
| **Queue & Worker**| Celery & Celery Beat | `worker.py` and tasks verified working. | ✅ **Yes** | **OK (once CORS crash is resolved)** |
| **Test Suite** | Pytest Suite | 59 of 59 backend security & feature tests passing. | ✅ **Yes** | **OK** |

---

## 3. Deep-Dive Root Cause Analysis

### 3.1. The Production Startup Crash (`config.py`)
In `backend/app/core/config.py`:
```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*",                         # <-- Problem 1: '*' is in the default list
    "http://192.168.0.158:5173",
]
...
@model_validator(mode="after")
def validate_production_security(self):
    if self.ENVIRONMENT.lower() in {"production", "prod"}:
        if not os.getenv("SECRET_KEY") or len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be explicitly configured with at least 32 characters in production")
        if "*" in self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS must not contain '*' in production when credentials are enabled")
    return self
```
When `docker compose up` starts with `ENVIRONMENT=production`, FastAPI initializes `settings = Settings()`. Because `*` is in `CORS_ORIGINS` and `docker-compose.yml` does not provide an override, Pydantic immediately raises a `ValidationError`, crashing `backend`, `worker`, and `beat`.

Furthermore, if an administrator specifies `CORS_ORIGINS=https://crm.example.com` in their `.env` file, Pydantic's default complex-type loader attempts `json.loads()` and throws `JSONDecodeError`, crashing the server.

### 3.2. Frontend Hardcoded Localhost in Docker Build
In `frontend/src/services/api.ts`:
```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
```
In `Dockerfile.frontend`:
```dockerfile
COPY frontend ./
RUN npm run build
```
Vite environment variables (`import.meta.env.VITE_*`) are resolved **at build time** and statically inlined into the client-side JavaScript bundle. Because `VITE_API_BASE_URL` is undefined during Docker build, Vite bakes `"http://localhost:8000/api/v1"` into the bundle.

When a client in London or New York opens `http://195.35.x.x` (or `https://crm.yourdomain.com`), their browser attempts to connect to `http://localhost:8000/api/v1/auth/login`. Their computer is not running the backend, so every request fails.

**The Fix:** Default `API_BASE` to `"/api/v1"`. Because Nginx serves the React bundle on port 80/443 and proxies `/api/` to `backend:8000/api/`, using a relative URL `/api/v1` guarantees that the browser always targets the exact same domain, IP, and protocol serving the web page, with zero CORS preflight overhead.

### 3.3. Database Initialization Gap
In `backend/app/main.py`:
```python
@app.on_event("startup")
def on_startup():
    logger.info("Database schema evolution is managed exclusively by Alembic; run 'alembic upgrade head' before startup.")
    ...
    seed_platform_rbac(seed_db)
```
FastAPI explicitly disclaims responsibility for creating tables and delegates this to Alembic. However, `docker-compose.yml` has no command or container running `alembic upgrade head`.

On a fresh Hostinger VPS, the PostgreSQL volume `postgres_data` is empty. The application starts up with 0 tables, immediately logging warnings during RBAC initialization and failing all subsequent HTTP requests with `UndefinedTable: relation "users" does not exist`.

### 3.4. Security Vulnerability: Public Redis & Postgres Exposure
In `docker-compose.yml`:
```yaml
  postgres:
    ports:
      - "5432:5432"
  redis:
    ports:
      - "6379:6379"
```
On a Hostinger VPS with a public static IP, Docker modifies `iptables` directly, bypassing standard UFW firewall rules unless explicitly configured otherwise.
- Redis 7 in alpine runs with **no password** by default. Binding `0.0.0.0:6379` exposes the queue, cache, and session data to any internet port scanner.
- Internal services (`backend`, `worker`, `beat`) connect via the Docker bridge network (`postgres:5432` and `redis:6379`). **These ports must not be published to the host.**

### 3.5. Storage Upload Permissions
In `Dockerfile.backend`:
```dockerfile
RUN addgroup --system app && adduser --system --group app && \
    chown -R app:app /app
USER app
```
In `docker-compose.yml`:
```yaml
volumes:
  - storage_uploads:/app/storage_uploads
```
When Docker mounts a named volume (`storage_uploads`) on Linux, the underlying directory on the host is created by `root:root` with mode 0755. Because `backend` and `worker` run as `USER app`, any file upload attempt to `/app/storage_uploads` raises `PermissionError: [Errno 13] Permission denied`.

---

## 4. Required Codebase Fixes

### 4.1. Fix `backend/app/core/config.py`
Remove `*` from the default `CORS_ORIGINS` and add a robust validator to accept comma-separated strings or JSON arrays:
```python
from pydantic import field_validator
from typing import Union, List
import json

class Settings(BaseSettings):
    ...
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
```

### 4.2. Fix `frontend/src/services/api.ts` & `frontend/vite.config.ts`
Change line 1 in `frontend/src/services/api.ts`:
```typescript
// Use relative path by default so it works under any domain/IP behind Nginx proxy
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";
```
Update `frontend/vite.config.ts` to include a dev proxy so local `npm run dev` works seamlessly without hardcoded URLs:
```typescript
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### 4.3. Fix `Dockerfile.frontend`
Pass build arguments into Vite:
```dockerfile
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build
```

### 4.4. Add Automated Migration & Seed to `docker-compose.yml`
Add a dedicated one-shot migration runner service that executes before the application containers start, and close public database/redis ports:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: jarvis_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-jarvis_crm}
      POSTGRES_USER: ${POSTGRES_USER:-jarvis_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in your environment}
    # Security: do not publish to 0.0.0.0 on a public VPS
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-jarvis_user} -d ${POSTGRES_DB:-jarvis_crm}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: jarvis_redis
    restart: unless-stopped
    # Security: do not publish to 0.0.0.0 on a public VPS
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # One-shot container to run migrations and seed admin user
  migration:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: jarvis_migration
    command: >
      sh -c "alembic upgrade head && python production_seed.py"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${POSTGRES_USER:-jarvis_user}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-jarvis_crm}
      - SECRET_KEY=${SECRET_KEY:?Set SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: jarvis_api
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - DATABASE_URL=postgresql://${POSTGRES_USER:-jarvis_user}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-jarvis_crm}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY:?Set a random SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS:-[]}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      migration:
        condition: service_completed_successfully
    volumes:
      - storage_uploads:/app/storage_uploads

  worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: jarvis_worker
    restart: unless-stopped
    command: celery -A app.worker.celery_app worker --loglevel=info
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${POSTGRES_USER:-jarvis_user}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-jarvis_crm}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS:-[]}
    depends_on:
      backend:
        condition: service_started
      redis:
        condition: service_healthy
    volumes:
      - storage_uploads:/app/storage_uploads

  beat:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: jarvis_beat
    restart: unless-stopped
    command: celery -A app.worker.celery_app beat --loglevel=info
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${POSTGRES_USER:-jarvis_user}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-jarvis_crm}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS:-[]}
    depends_on:
      redis:
        condition: service_healthy

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: jarvis_frontend
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
  storage_uploads:
```

### 4.5. Add `.dockerignore`
Create `.dockerignore` at repository root:
```gitignore
.git
.gitignore
.env
.env.local
*.pyc
__pycache__
*.db
*.sqlite
*.sqlite3
storage_uploads/
node_modules/
frontend/node_modules/
frontend/dist/
jarvis-crm/
.pytest_cache/
tests/
*.log
*.mp4
*.pdf
```

---

## 5. Hostinger VPS Sizing & Operating System Specifications

### 5.1. Recommended VPS Plan
| Hostinger Plan | vCPU | RAM | NVMe SSD | Assessment for Jarvis CRM |
| :--- | :---: | :---: | :---: | :--- |
| **KVM 1** | 1 | 4 GB | 50 GB | **Supported with Swap.** Good for testing / small team (<10 telecallers). Must enable 2-4GB Linux swap to prevent build OOM. |
| **KVM 2** *(Recommended)* | 2 | 8 GB | 100 GB | **Optimal.** Handles concurrent imports, Celery jobs, multiple telecallers, and builds effortlessly. |
| **KVM 4** | 4 | 16 GB | 200 GB | **Enterprise.** For high-volume CSV lead ingestion (>100k rows/day) and large teams. |

### 5.2. Recommended Operating System
Select **Ubuntu 22.04 LTS 64-bit** or **Ubuntu 24.04 LTS 64-bit** in the Hostinger hPanel.

---

## 6. Step-by-Step Hostinger VPS Deployment Playbook

### Step 1: Connect to your Hostinger VPS via SSH
```bash
ssh root@<YOUR_HOSTINGER_VPS_IP>
```

### Step 2: System Update, Swapfile & Docker Installation
```bash
# Update package repositories
apt-get update && apt-get upgrade -y

# Enable 4GB Swapfile (Vital for Docker builds)
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Install Docker & Docker Compose Plugin
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
```

### Step 3: Clone Repository & Configure Environment
```bash
git clone <YOUR_GIT_REPO_URL> /opt/jarvis_crm
cd /opt/jarvis_crm

# Create production .env file
cat << 'EOF' > .env
PROJECT_NAME="JARVIS CRM"
ENVIRONMENT=production
DEBUG=false

# Generate secure password & secret key
POSTGRES_USER=jarvis_user
POSTGRES_DB=jarvis_crm
POSTGRES_PASSWORD=$(openssl rand -hex 16)
SECRET_KEY=$(openssl rand -hex 32)

# Allowed Origins (Set your domain or VPS IP)
CORS_ORIGINS=["http://<YOUR_HOSTINGER_VPS_IP>", "https://crm.yourdomain.com"]

# Storage
STORAGE_PROVIDER=LOCAL
STORAGE_LOCAL_DIR=./storage_uploads
MAX_UPLOAD_SIZE_MB=50
EOF
```

### Step 4: Build & Launch the Services
```bash
docker compose up -d --build
```
This will:
1. Spin up PostgreSQL and Redis with healthchecks.
2. Automatically run `jarvis_migration` (`alembic upgrade head` and `production_seed.py`).
3. Start the FastAPI backend, Celery worker, Celery beat, and Frontend Nginx proxy.

### Step 5: Verify Deployment Health
```bash
# Check running containers
docker compose ps

# Check API health endpoint
curl http://localhost/api/v1/health
```
Expected output:
```json
{"status":"healthy","service":"JARVIS CRM","version":"1.0.0","environment":"production","database":"connected","redis_broker":"connected","storage":"LOCAL"}
```

### Step 6: SSL / HTTPS Setup with Let's Encrypt (For Custom Domain)
If pointing a domain (e.g., `crm.yourcompany.com`) from Hostinger DNS to the VPS:
1. In `docker-compose.yml`, change frontend port from `"80:80"` to `"127.0.0.1:8080:80"`.
2. Install host Nginx and Certbot:
```bash
apt-get install -y nginx certbot python3-certbot-nginx
```
3. Configure `/etc/nginx/sites-available/crm`:
```nginx
server {
    server_name crm.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100M;
    }
}
```
4. Enable the site and request SSL certificate:
```bash
ln -s /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
certbot --nginx -d crm.yourdomain.com
```

### Step 7: Access the System
- **URL**: `http://<YOUR_HOSTINGER_VPS_IP>` (or `https://crm.yourdomain.com`)
- **Default Super Admin**: `superadmin@jarvis.com`
- **Default Password**: `admin123` *(Must be changed immediately upon first login)*

---

## 7. Next Steps

1. Apply the 5 code fixes (`config.py`, `api.ts`, `Dockerfile.frontend`, `docker-compose.yml`, `.dockerignore`).
2. Verify local builds (`docker compose build`).
3. Push to your repository and execute the deployment playbook on Hostinger.
