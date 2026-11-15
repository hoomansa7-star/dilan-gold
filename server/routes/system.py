# -*- coding: utf-8 -*-
"""
System info, Jalali date resolution, and automated backups.
"""

from fastapi import APIRouter
import jdatetime
import os
from datetime import datetime
from server.database import get_db_connection, create_backup, BACKUP_DIR

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/status")
def get_system_status():
    now_j = jdatetime.datetime.now()
    days_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    day_name = days_fa[now_j.weekday()]

    conn = get_db_connection()
    craftsmen_cnt = conn.execute("SELECT COUNT(*) FROM craftsmen WHERE is_active = 1").fetchone()[0]
    shifts_cnt = conn.execute("SELECT COUNT(*) FROM daily_shifts").fetchone()[0]
    items_cnt = conn.execute("SELECT COUNT(*) FROM showcase_items").fetchone()[0]
    total_gold_weight = conn.execute("SELECT COALESCE(SUM(gold_weight), 0.0) FROM showcase_items").fetchone()[0]
    invoices_cnt = conn.execute("SELECT COUNT(*) FROM sales_invoices").fetchone()[0]
    conn.close()

    return {
        "status": "online",
        "app_name": "Dilan Gold ERP (نرم‌افزار حسابداری طلا و کارگاه دیلان)",
        "today_shamsi": now_j.strftime("%Y/%m/%d"),
        "today_day_of_week": day_name,
        "current_time": now_j.strftime("%H:%M"),
        "metrics": {
            "craftsmen_count": craftsmen_cnt,
            "shifts_count": shifts_cnt,
            "showcase_items_count": items_cnt,
            "total_showcase_gold_weight": round(total_gold_weight, 3),
            "invoices_count": invoices_cnt,
        }
    }


@router.post("/backup")
def trigger_backup():
    file_path = create_backup()
    filename = os.path.basename(file_path)
    return {"status": "success", "filename": filename, "path": file_path}


@router.get("/backups")
def list_backups():
    backups = []
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.endswith(".db"):
                f_path = os.path.join(BACKUP_DIR, f)
                stat = os.stat(f_path)
                backups.append({
                    "filename": f,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups
