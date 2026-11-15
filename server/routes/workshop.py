# -*- coding: utf-8 -*-
"""
Workshop line, daily shifts, craftsmen, tasks, incidents, and loss management.
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import jdatetime
from server.database import get_db_connection
from server.excel_exporter import export_shift_to_excel

router = APIRouter(prefix="/api/workshop", tags=["Workshop"])


class ShiftCreate(BaseModel):
    date_shamsi: str
    day_of_week: str
    notes: Optional[str] = ""


class BatchCreate(BaseModel):
    shift_id: int
    title: str
    total_count: int = 1
    total_weight: float
    carat: int = 750
    notes: Optional[str] = ""


class TaskCreate(BaseModel):
    shift_id: int
    batch_id: Optional[int] = None
    craftsman_id: int
    stage: str
    item_name: str
    count: int = 1
    input_weight: float
    output_weight: float
    notes: Optional[str] = ""


class IncidentCreate(BaseModel):
    shift_id: int
    craftsman_id: Optional[int] = None
    title: str
    weight: float
    target_bucket: str = "سوآله چرم و سوهانکاری"
    weight_after: Optional[float] = None
    notes: Optional[str] = ""


class CraftsmanCreate(BaseModel):
    name: str
    role: str = "سازنده طلا"
    phone: Optional[str] = ""


@router.get("/craftsmen")
def list_craftsmen():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM craftsmen WHERE is_active = 1 ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/craftsmen")
def add_craftsman(c: CraftsmanCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO craftsmen (name, role, phone) VALUES (?, ?, ?)", (c.name, c.role, c.phone))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"id": new_id, "name": c.name, "status": "created"}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="استادکار با این نام از قبل وجود دارد")


@router.get("/shifts")
def list_shifts():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT s.*, 
               (SELECT COUNT(*) FROM workshop_tasks WHERE shift_id = s.id) as task_count,
               (SELECT COALESCE(SUM(loss_weight), 0) FROM workshop_tasks WHERE shift_id = s.id) as calculated_loss
        FROM daily_shifts s
        ORDER BY s.date_shamsi DESC, s.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/shifts")
def create_shift(s: ShiftCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_shifts (date_shamsi, day_of_week, notes)
            VALUES (?, ?, ?)
        """, (s.date_shamsi, s.day_of_week, s.notes))
        conn.commit()
        shift_id = cursor.lastrowid
        conn.close()
        return {"id": shift_id, "date_shamsi": s.date_shamsi, "status": "created"}
    except sqlite3.IntegrityError:
        # If exists, return existing
        existing = conn.execute("SELECT * FROM daily_shifts WHERE date_shamsi = ?", (s.date_shamsi,)).fetchone()
        conn.close()
        return dict(existing)


@router.get("/shifts/{shift_id}")
def get_shift_detail(shift_id: int):
    conn = get_db_connection()
    shift = conn.execute("SELECT * FROM daily_shifts WHERE id = ?", (shift_id,)).fetchone()
    if not shift:
        conn.close()
        raise HTTPException(status_code=404, detail="شیفت مورد نظر یافت نشد")

    batches = conn.execute("SELECT * FROM workshop_batches WHERE shift_id = ? ORDER BY id ASC", (shift_id,)).fetchall()
    
    tasks = conn.execute("""
        SELECT t.*, c.name as craftsman_name 
        FROM workshop_tasks t
        JOIN craftsmen c ON t.craftsman_id = c.id
        WHERE t.shift_id = ?
        ORDER BY t.id ASC
    """, (shift_id,)).fetchall()

    incidents = conn.execute("""
        SELECT i.*, c.name as craftsman_name 
        FROM workshop_incidents i
        LEFT JOIN craftsmen c ON i.craftsman_id = c.id
        WHERE i.shift_id = ?
        ORDER BY i.id ASC
    """, (shift_id,)).fetchall()

    conn.close()

    total_loss = sum(float(t["loss_weight"]) for t in tasks)
    total_input = sum(float(t["input_weight"]) for t in tasks)
    total_output = sum(float(t["output_weight"]) for t in tasks)

    return {
        "shift": dict(shift),
        "batches": [dict(b) for b in batches],
        "tasks": [dict(t) for t in tasks],
        "incidents": [dict(i) for i in incidents],
        "summary": {
            "total_input_weight": round(total_input, 3),
            "total_output_weight": round(total_output, 3),
            "total_loss_weight": round(total_loss, 3),
            "batch_count": len(batches),
            "task_count": len(tasks),
            "incident_count": len(incidents),
        }
    }


@router.post("/batches")
def add_batch(b: BatchCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workshop_batches (shift_id, title, total_count, total_weight, carat, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (b.shift_id, b.title, b.total_count, b.total_weight, b.carat, b.notes))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "status": "created"}


@router.delete("/batches/{batch_id}")
def delete_batch(batch_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM workshop_batches WHERE id = ?", (batch_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


@router.post("/tasks")
def add_task(t: TaskCreate):
    # loss = output - input (negative if loss, positive if gain)
    loss = round(t.output_weight - t.input_weight, 3)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workshop_tasks (shift_id, batch_id, craftsman_id, stage, item_name, count, input_weight, output_weight, loss_weight, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (t.shift_id, t.batch_id, t.craftsman_id, t.stage, t.item_name, t.count, t.input_weight, t.output_weight, loss, t.notes))
    conn.commit()
    new_id = cursor.lastrowid
    
    # Recalculate shift total loss
    tot = conn.execute("SELECT SUM(loss_weight) FROM workshop_tasks WHERE shift_id = ?", (t.shift_id,)).fetchone()[0] or 0.0
    conn.execute("UPDATE daily_shifts SET total_loss = ? WHERE id = ?", (tot, t.shift_id))
    conn.commit()
    conn.close()
    return {"id": new_id, "loss_weight": loss, "status": "created"}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_db_connection()
    task = conn.execute("SELECT shift_id FROM workshop_tasks WHERE id = ?", (task_id,)).fetchone()
    if task:
        shift_id = task["shift_id"]
        conn.execute("DELETE FROM workshop_tasks WHERE id = ?", (task_id,))
        tot = conn.execute("SELECT SUM(loss_weight) FROM workshop_tasks WHERE shift_id = ?", (shift_id,)).fetchone()[0] or 0.0
        conn.execute("UPDATE daily_shifts SET total_loss = ? WHERE id = ?", (tot, shift_id))
        conn.commit()
    conn.close()
    return {"status": "deleted"}


@router.post("/incidents")
def add_incident(i: IncidentCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workshop_incidents (shift_id, craftsman_id, title, weight, target_bucket, weight_after, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (i.shift_id, i.craftsman_id, i.title, i.weight, i.target_bucket, i.weight_after, i.notes))
    conn.commit()
    new_id = cursor.lastrowid

    # Update swarf total
    tot_swarf = conn.execute("SELECT SUM(weight) FROM workshop_incidents WHERE shift_id = ?", (i.shift_id,)).fetchone()[0] or 0.0
    conn.execute("UPDATE daily_shifts SET total_swarf = ? WHERE id = ?", (tot_swarf, i.shift_id))
    conn.commit()
    conn.close()
    return {"id": new_id, "status": "created"}


@router.delete("/incidents/{incident_id}")
def delete_incident(incident_id: int):
    conn = get_db_connection()
    inc = conn.execute("SELECT shift_id FROM workshop_incidents WHERE id = ?", (incident_id,)).fetchone()
    if inc:
        shift_id = inc["shift_id"]
        conn.execute("DELETE FROM workshop_incidents WHERE id = ?", (incident_id,))
        tot_swarf = conn.execute("SELECT SUM(weight) FROM workshop_incidents WHERE shift_id = ?", (shift_id,)).fetchone()[0] or 0.0
        conn.execute("UPDATE daily_shifts SET total_swarf = ? WHERE id = ?", (tot_swarf, shift_id))
        conn.commit()
    conn.close()
    return {"status": "deleted"}


@router.get("/shifts/{shift_id}/export-excel")
def export_shift_excel(shift_id: int):
    shift_details = get_shift_detail(shift_id)
    excel_stream = export_shift_to_excel(
        shift_data=shift_details["shift"],
        tasks=shift_details["tasks"],
        batches=shift_details["batches"],
        incidents=shift_details["incidents"]
    )
    filename = f"dilan_shift_{shift_details['shift']['date_shamsi'].replace('/', '_')}.xlsx"
    return Response(
        content=excel_stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/seed-sample-shift")
def seed_sample_shift():
    """Seeds the exact 1405/07/29 Wednesday notebook records from user uploaded images."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get craftsman IDs
    craftsmen_map = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM craftsmen").fetchall()}
    nima_id = craftsmen_map.get("نیما", 1)
    amir_id = craftsmen_map.get("امیر", 2)
    ata_id = craftsmen_map.get("عطا", 3)

    # 1. Create or update shift
    existing = conn.execute("SELECT id FROM daily_shifts WHERE date_shamsi = '1405/07/29'").fetchone()
    if existing:
        shift_id = existing["id"]
        cursor.execute("""
            UPDATE daily_shifts 
            SET day_of_week = 'چهارشنبه', total_loss = -3.94, total_swarf = 1.10, notes = 'نمونه ثبت‌شده بر اساس دفاتر دست‌نویس کارگاه'
            WHERE id = ?
        """, (shift_id,))
    else:
        cursor.execute("""
            INSERT INTO daily_shifts (date_shamsi, day_of_week, total_loss, total_swarf, notes)
            VALUES ('1405/07/29', 'چهارشنبه', -3.94, 1.10, 'نمونه ثبت‌شده بر اساس دفاتر دست‌نویس کارگاه')
        """)
        shift_id = cursor.lastrowid

    # Clear previous details for this shift if re-seeding
    cursor.execute("DELETE FROM workshop_batches WHERE shift_id = ?", (shift_id,))
    cursor.execute("DELETE FROM workshop_tasks WHERE shift_id = ?", (shift_id,))
    cursor.execute("DELETE FROM workshop_incidents WHERE shift_id = ?", (shift_id,))

    # 2. Batches
    batches = [
        ("گل و نگین برای پوست", 23, 26.77, "تفکیک سایزهای ۱ تا ۶"),
        ("انگشتر و نگین", 18, 23.87, "ملگات شده ۱۱ عدد، پوست خورده ۷ عدد"),
        ("انگشتر متفرقه", 4, 11.90, "عطا: ۴ عدد، ۸٫۷۲ گرم"),
        ("گل و نگین برای تراش داخل", 1, 49.34, "وزن با یک مفتول - تحویل عطا شد"),
    ]
    for title, count, weight, notes in batches:
        cursor.execute("""
            INSERT INTO workshop_batches (shift_id, title, total_count, total_weight, carat, notes)
            VALUES (?, ?, ?, ?, 750, ?)
        """, (shift_id, title, count, weight, notes))

    # 3. Tasks from page 4 and 5
    tasks = [
        # مرحله ۱: تقسیم گل و پوست و ملگات گل
        (nima_id, "skin", "پوست و ملگات گل", 16, 12.51, 12.34, -0.170, "سایز ۱ تا ۶"),
        (amir_id, "skin", "پوست و ملگات گل", 17, 14.25, 14.09, -0.160, "سایز ۱ تا ۶"),
        # پوست انگشتر متفرقه
        (nima_id, "skin", "پوست انگشتر متفرقه", 2, 5.85, 5.44, -0.410, ""),
        (amir_id, "skin", "پوست انگشتر متفرقه", 2, 6.04, 4.96, -1.080, ""),
        # پوست النگو و نگین
        (nima_id, "skin", "پوست النگو و نگین", 5, 6.91, 6.42, -0.490, ""),
        (amir_id, "skin", "پوست النگو و نگین", 6, 8.22, 7.48, -0.740, ""),
        (ata_id, "skin", "پوست النگو و نگین", 7, 8.71, 8.50, -0.210, ""),
        # پرداخت انگشتر متفرقه
        (nima_id, "polish", "پرداخت انگشتر متفرقه", 2, 5.44, 5.28, -0.160, ""),
        (amir_id, "polish", "پرداخت انگشتر متفرقه", 2, 4.96, 4.82, -0.140, ""),
        # پرداخت انگشتر و نگین
        (nima_id, "polish", "پرداخت انگشتر و نگین", 5, 6.42, 6.35, -0.070, ""),
        (amir_id, "polish", "پرداخت انگشتر و نگین", 11, 7.48, 7.35, -0.130, ""),
        (ata_id, "polish", "پرداخت انگشتر و نگین", 10, 7.41, 7.23, -0.180, ""),
    ]

    for cid, stage, iname, cnt, in_w, out_w, loss, nts in tasks:
        cursor.execute("""
            INSERT INTO workshop_tasks (shift_id, craftsman_id, stage, item_name, count, input_weight, output_weight, loss_weight, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (shift_id, cid, stage, iname, cnt, in_w, out_w, loss, nts))

    # 4. Incident
    cursor.execute("""
        INSERT INTO workshop_incidents (shift_id, craftsman_id, title, weight, target_bucket, weight_after, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (shift_id, ata_id, "انگشتر و نگین سایز ۳ عطا", 1.10, "سوآله", 7.40, "یک عدد انگشتر سایز ۳ عطا به وزن ۱٫۱۰ به سوآله رفت. وزن بعد سوآله: ۷٫۴۰ گرم"))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "داده‌های واقعی ۲۹ مهر ۱۴۰۵ با موفقیت در سیستم بارگذاری شدند."}
