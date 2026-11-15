# -*- coding: utf-8 -*-
"""
Main FastAPI application entrypoint for Dilan Gold ERP.
Serves both backend REST APIs and the rich client Single Page Application.
"""

import sys
import os

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from server.database import init_db, get_db_connection
from server.routes.workshop import router as workshop_router, seed_sample_shift
from server.routes.calculator import router as calc_router
from server.routes.showcase import router as showcase_router
from server.routes.sales import router as sales_router
from server.routes.accounts import router as accounts_router
from server.routes.system import router as system_router

app = FastAPI(
    title="Dilan Gold ERP",
    description="سیستم یکپارچه حسابداری طلا، مدیریت خط تولید کارگاه و ویترین گالری دیلان",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(workshop_router)
app.include_router(calc_router)
app.include_router(showcase_router)
app.include_router(sales_router)
app.include_router(accounts_router)
app.include_router(system_router)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(BASE_DIR, "client")

# Mount static files
app.mount("/static", StaticFiles(directory=CLIENT_DIR), name="static")


@app.on_event("startup")
def on_startup():
    init_db()
    # Check if sample shift exists, if not seed it
    conn = get_db_connection()
    shift_count = conn.execute("SELECT COUNT(*) FROM daily_shifts").fetchone()[0]
    conn.close()
    if shift_count == 0:
        seed_sample_shift()


@app.get("/")
def serve_index():
    index_file = os.path.join(CLIENT_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "Dilan Gold ERP API is running. Client index.html is being prepared."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=True)
