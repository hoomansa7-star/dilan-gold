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


# =========================================================================
# PHASE 2: BENCH QUICK-TASK, CRAFTSMEN PAYROLL, CRUCIBLE, SOLDER & REFINING
# =========================================================================

class QuickTaskCreate(BaseModel):
    shift_id: Optional[int] = None
    craftsman_id: int
    stage: str
    item_name: str
    count: int = 1
    input_weight: float
    output_weight: float
    send_to_swarf_weight: Optional[float] = 0.0
    notes: Optional[str] = ""


class SettlementCreate(BaseModel):
    craftsman_id: int
    date_shamsi: str
    period_title: str
    total_worked_grams: float = 0.0
    wage_rate_irr: float = 0.0
    total_wage_irr: float = 0.0
    paid_amount_irr: float = 0.0
    paid_gold_weight: float = 0.0
    settlement_status: str = "تسویه_شده"
    notes: Optional[str] = ""


class CrucibleCreate(BaseModel):
    date_shamsi: str
    crucible_code: str
    operator_name: Optional[str] = "مسئول ذوب"
    raw_gold_weight: float
    raw_carat: int = 750
    target_carat: int = 750
    alloy_bar_added: float = 0.0
    melted_bar_weight: float
    sheereh_weight: float = 0.0
    notes: Optional[str] = ""


class SolderCalcRequest(BaseModel):
    base_gold_weight: float
    recipe_type: str = "medium"  # hard, medium, soft, custom
    custom_cadmium_percent: Optional[float] = None
    base_carat: int = 750


class RefiningBatchCreate(BaseModel):
    date_shamsi: str
    batch_code: str
    refiner_name: str
    material_type: str = "سوآله چرم و سوهان"
    sent_weight: float
    notes: Optional[str] = ""


class RefiningBatchComplete(BaseModel):
    recovered_gold_750: float
    refining_fee_irr: float = 0.0
    status: str = "تسویه_شده"
    notes: Optional[str] = ""


@router.post("/quick-task")
def add_quick_task(qt: QuickTaskCreate):
    """Ultra-fast bench endpoint: logs task, calculates loss, and optionally sends item to swarf."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Resolve shift_id
    shift_id = qt.shift_id
    if not shift_id:
        latest = conn.execute("SELECT id FROM daily_shifts ORDER BY id DESC LIMIT 1").fetchone()
        if latest:
            shift_id = latest["id"]
        else:
            today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")
            cursor.execute("INSERT INTO daily_shifts (date_shamsi, day_of_week) VALUES (?, 'امروز')", (today_shamsi,))
            conn.commit()
            shift_id = cursor.lastrowid

    loss = round(qt.output_weight - qt.input_weight, 3)

    cursor.execute("""
        INSERT INTO workshop_tasks (shift_id, craftsman_id, stage, item_name, count, input_weight, output_weight, loss_weight, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (shift_id, qt.craftsman_id, qt.stage, qt.item_name, qt.count, qt.input_weight, qt.output_weight, loss, qt.notes))
    conn.commit()
    task_id = cursor.lastrowid

    incident_id = None
    if qt.send_to_swarf_weight and qt.send_to_swarf_weight > 0:
        cursor.execute("""
            INSERT INTO workshop_incidents (shift_id, craftsman_id, title, weight, target_bucket, weight_after, notes)
            VALUES (?, ?, ?, ?, 'سوآله', ?, ?)
        """, (shift_id, qt.craftsman_id, f"ارسال به سوآله ({qt.item_name})", qt.send_to_swarf_weight, qt.output_weight, qt.notes or "ثبت سریع پای میز کار"))
        conn.commit()
        incident_id = cursor.lastrowid

    # Recalculate shift totals
    tot_loss = conn.execute("SELECT SUM(loss_weight) FROM workshop_tasks WHERE shift_id = ?", (shift_id,)).fetchone()[0] or 0.0
    tot_swarf = conn.execute("SELECT SUM(weight) FROM workshop_incidents WHERE shift_id = ?", (shift_id,)).fetchone()[0] or 0.0
    conn.execute("UPDATE daily_shifts SET total_loss = ?, total_swarf = ? WHERE id = ?", (tot_loss, tot_swarf, shift_id))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "task_id": task_id,
        "incident_id": incident_id,
        "loss_weight": loss,
        "shift_id": shift_id
    }


@router.get("/craftsmen-payroll")
def get_craftsmen_payroll(shift_id: Optional[int] = None):
    """Calculates wage and gram statistics for each craftsman with stage breakdown."""
    conn = get_db_connection()
    craftsmen = conn.execute("SELECT id, name, role, phone FROM craftsmen WHERE is_active = 1 ORDER BY id ASC").fetchall()

    payroll_data = []
    for c in craftsmen:
        cid = c["id"]
        if shift_id:
            tasks = conn.execute("SELECT * FROM workshop_tasks WHERE craftsman_id = ? AND shift_id = ?", (cid, shift_id)).fetchall()
        else:
            tasks = conn.execute("SELECT * FROM workshop_tasks WHERE craftsman_id = ?", (cid,)).fetchall()

        total_input = round(sum(float(t["input_weight"]) for t in tasks), 3)
        total_output = round(sum(float(t["output_weight"]) for t in tasks), 3)
        total_loss = round(sum(float(t["loss_weight"]) for t in tasks), 3)
        task_count = len(tasks)

        # Stage breakdown
        stages = {}
        for t in tasks:
            stg = t["stage"]
            stages[stg] = round(stages.get(stg, 0.0) + float(t["output_weight"]), 3)

        # Total settled from craftsmen_settlements
        settlements = conn.execute("""
            SELECT COALESCE(SUM(paid_amount_irr), 0) as total_irr,
                   COALESCE(SUM(paid_gold_weight), 0) as total_gold
            FROM craftsmen_settlements WHERE craftsman_id = ?
        """, (cid,)).fetchone()

        paid_irr = float(settlements["total_irr"]) if settlements else 0.0
        paid_gold = float(settlements["total_gold"]) if settlements else 0.0

        # Suggested wage standard rate: 45,000 Tomans = 450,000 Rials per gram processed
        wage_rate_irr = 450000.0
        calculated_wage_irr = round(total_output * wage_rate_irr)
        wage_balance_irr = calculated_wage_irr - paid_irr

        payroll_data.append({
            "craftsman_id": cid,
            "name": c["name"],
            "role": c["role"],
            "phone": c["phone"],
            "task_count": task_count,
            "total_input_weight": total_input,
            "total_output_weight": total_output,
            "total_loss_weight": total_loss,
            "stage_breakdown": stages,
            "wage_rate_irr": wage_rate_irr,
            "calculated_wage_irr": calculated_wage_irr,
            "paid_amount_irr": paid_irr,
            "paid_gold_weight": paid_gold,
            "wage_balance_irr": wage_balance_irr
        })

    conn.close()
    return payroll_data


@router.get("/settlements")
def list_settlements():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT s.*, c.name as craftsman_name, c.role as craftsman_role
        FROM craftsmen_settlements s
        JOIN craftsmen c ON s.craftsman_id = c.id
        ORDER BY s.date_shamsi DESC, s.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/settlements")
def add_settlement(s: SettlementCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO craftsmen_settlements (
            craftsman_id, date_shamsi, period_title, total_worked_grams,
            wage_rate_irr, total_wage_irr, paid_amount_irr, paid_gold_weight,
            settlement_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        s.craftsman_id, s.date_shamsi, s.period_title, s.total_worked_grams,
        s.wage_rate_irr, s.total_wage_irr, s.paid_amount_irr, s.paid_gold_weight,
        s.settlement_status, s.notes
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "status": "created"}


@router.get("/crucibles")
def list_crucibles():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM crucible_records ORDER BY date_shamsi DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/crucibles")
def add_crucible(c: CrucibleCreate):
    # Pure net loss = raw_gold_weight + alloy_bar_added - melted_bar_weight - sheereh_weight
    loss = round(c.raw_gold_weight + c.alloy_bar_added - c.melted_bar_weight - c.sheereh_weight, 3)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crucible_records (
            date_shamsi, crucible_code, operator_name, raw_gold_weight,
            raw_carat, target_carat, alloy_bar_added, melted_bar_weight,
            sheereh_weight, loss_weight, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        c.date_shamsi, c.crucible_code, c.operator_name, c.raw_gold_weight,
        c.raw_carat, c.target_carat, c.alloy_bar_added, c.melted_bar_weight,
        c.sheereh_weight, loss, c.notes
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "loss_weight": loss, "status": "created"}


@router.get("/solder-recipes")
def list_solder_recipes():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM solder_recipes ORDER BY final_carat DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/solder-calc")
def calculate_solder(req: SolderCalcRequest):
    """Calculates cadmium and silver additions for standard Iranian gold solder alloys."""
    recipes = {
        "hard": {
            "cadmium_pct": 1.00,
            "silver_pct": 0.35,
            "copper_pct": 0.00,
            "target_carat": 740,
            "title": "لحیم سفت (جوش اولیه و اتصالات سنگین - عیار ۷۴۰)"
        },
        "medium": {
            "cadmium_pct": 2.00,
            "silver_pct": 0.74,
            "copper_pct": 0.00,
            "target_carat": 730,
            "title": "لحیم متوسط (کارهای عمومی و النگو - عیار ۷۳۰)"
        },
        "soft": {
            "cadmium_pct": 3.50,
            "silver_pct": 1.40,
            "copper_pct": 0.00,
            "target_carat": 715,
            "title": "لحیم شل (کارهای ظریف، گل و نگین - عیار ۷۱۵)"
        },
    }

    if req.recipe_type in recipes:
        config = recipes[req.recipe_type]
        cadmium_pct = config["cadmium_pct"]
        silver_pct = config["silver_pct"]
        copper_pct = config["copper_pct"]
        target_carat = config["target_carat"]
        title = config["title"]
    else:
        cadmium_pct = req.custom_cadmium_percent if req.custom_cadmium_percent is not None else 1.5
        silver_pct = round(cadmium_pct * 0.4, 2)
        copper_pct = 0.0
        target_carat = 735
        title = f"لحیم سفارشی با {cadmium_pct}٪ کادمیوم"

    base_w = req.base_gold_weight
    cadmium_w = round(base_w * (cadmium_pct / 100.0), 3)
    silver_w = round(base_w * (silver_pct / 100.0), 3)
    copper_w = round(base_w * (copper_pct / 100.0), 3)
    total_w = round(base_w + cadmium_w + silver_w + copper_w, 3)

    pure_gold = base_w * (req.base_carat / 1000.0)
    calculated_carat = round((pure_gold / total_w) * 1000)

    instructions = [
        "۱. ابتدا طلای پایه ۷۵۰ و نقره را داخل بوته تمیز با مقداری بوراکس (تنه کار) ذوب و کاملاً یکدست کنید.",
        "۲. پس از روان شدن کامل مذاب طلا، مشعل را اندکی عقب ببرید تا جوشش مذاب آرام گیرد (از سوختن و تبخیر کادمیوم جلوگیری شود).",
        "۳. تکه کادمیوم وزن‌شده را درون یک ورق نازک کاغذ سیگار یا فویل نقره پیچیده و سریعاً به قلب مذاب بیافزایید.",
        "۴. بلافاصله با میله گرافیتی یا مفتول کربنی مذاب را به مدت ۳ ثانیه هم‌زده و فوراً درون ریجه بریزید."
    ]

    return {
        "title": title,
        "base_gold_weight": base_w,
        "base_carat": req.base_carat,
        "cadmium_percent": cadmium_pct,
        "cadmium_weight": cadmium_w,
        "silver_weight": silver_w,
        "copper_weight": copper_w,
        "total_solder_weight": total_w,
        "resulting_carat": calculated_carat,
        "instructions": instructions
    }


@router.get("/refining")
def list_refining_batches():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM refining_batches ORDER BY date_shamsi DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/refining")
def add_refining_batch(b: RefiningBatchCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO refining_batches (date_shamsi, batch_code, refiner_name, material_type, sent_weight, status, notes)
        VALUES (?, ?, ?, ?, ?, 'در_حال_تیزاب', ?)
    """, (b.date_shamsi, b.batch_code, b.refiner_name, b.material_type, b.sent_weight, b.notes))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "status": "created"}


@router.put("/refining/{batch_id}/complete")
def complete_refining_batch(batch_id: int, c: RefiningBatchComplete):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE refining_batches
        SET recovered_gold_750 = ?, refining_fee_irr = ?, status = ?, notes = COALESCE(notes, '') || ' | ' || ?
        WHERE id = ?
    """, (c.recovered_gold_750, c.refining_fee_irr, c.status, c.notes or "تسویه قالکاری", batch_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "batch_id": batch_id}

