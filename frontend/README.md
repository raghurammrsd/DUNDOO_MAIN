# DUNDOO Frontend & Cloudflare Pages Deployment Guide

This directory contains the decoupled frontend architecture for **DUNDOO (Nearby Shop Discovery & Marketplace)**.

## Directory Structure
- `templates/` — Jinja2/HTML templates for user discovery, shopkeeper dashboard, and authentication.
- `static/` — CSS, JavaScript, icons, manifest files, and local fallback uploads (`uploads/products/`, `uploads/reels/`).
- `public/_redirects` — Proxy configuration for **Cloudflare Pages**.

---

## Deployment Instructions

### 1. Backend Deployment on Render (`backend/`)
1. Connect this repository to your **Render** dashboard.
2. Select **Web Service** and choose the `backend/` directory as the Root Directory.
3. Render will automatically detect `render.yaml` or use:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app --workers 3 --bind 0.0.0.0:$PORT`
4. Set the environment variable `DATABASE_URL` to your Neon Postgres database connection string:
   `postgresql+psycopg://neondb_owner:npg_OQNst5Sm2Vyx@ep-still-thunder-adkxyevh-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
5. Set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` for persistent cloud media storage.

### 2. Frontend Deployment on Cloudflare Pages (`frontend/`)
1. Connect this repository to **Cloudflare Pages**.
2. Set the **Build output directory** to `frontend/public/` (or serve `frontend/static/` with proxying configured in `_redirects`).
3. Update the destination URLs inside `_redirects` (`https://dundoo-backend.onrender.com/...`) to match your actual Render live URL once deployed.
4. Cloudflare Pages will serve static assets from the global edge network while automatically routing dynamic API endpoints (`/api/*`, `/user/*`, `/shop/*`) directly to your Render Python backend!
