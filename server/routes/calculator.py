# -*- coding: utf-8 -*-
"""
Gold melting, multi-ingot conversion to 750, alloy (bar) addition, melting loss,
swarf recovery (تیزاب‌کاری و بازیافت سوآله چرم), and missing gold (کسر غیرمتصل) audit.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from server.database import get_db_connection

router = APIRouter(prefix="/api/calc", tags=["Calculator"])


class IngotItem(BaseModel):
    title: str = "شمش"
    weight: float
    carat: int


class MultiIngotMeltingRequest(BaseModel):
    date_shamsi: str
    title: str
    ingots: List[IngotItem]
    crust_weight: float = 0.0  # ته پوسته
    melted_output_weight: Optional[float] = None
    target_carat: int = 750
    notes: Optional[str] = ""


class SwarfRecoveryRequest(BaseModel):
    date_shamsi: str
    bucket_type: str  # سوآله چرم, سوآله سوهانکاری, ته دیگ تیزاب
    raw_swarf_weight: float
    melted_weight: float
    lab_carat: int  # عیار ری‌گیری
    notes: Optional[str] = ""


class GoldAuditRequest(BaseModel):
    input_gold_750: float
    finished_output_gold: float
    swarf_gold_collected: float
    stage_losses_total: float


@router.post("/multi-melting")
def calculate_multi_melting(req: MultiIngotMeltingRequest):
    """
    قانون ۱ دست‌نوشته همکار:
    ورود ۴ شمش با عیارهای مختلف در یک بوته ریخته‌گری:
    - تبدیل تک‌تک شمش‌ها به عیار ۷۵۰
    - محاسبه سرجمع طلای خالص
    - محاسبه بار مس/نقره مورد نیاز برای رساندن به عیار ۷۵۰
    - محاسبه کسر ذوب با در نظر گرفتن ته پوسته بوته
    """
    total_raw_weight = 0.0
    total_gold_750 = 0.0
    ingots_analysis = []

    for ing in req.ingots:
        equiv_750 = round((ing.weight * ing.carat) / req.target_carat, 3)
        total_raw_weight += ing.weight
        total_gold_750 += equiv_750
        ingots_analysis.append({
            "title": ing.title,
            "weight": ing.weight,
            "carat": ing.carat,
            "equivalent_750": equiv_750
        })

    total_raw_weight = round(total_raw_weight, 3)
    total_gold_750 = round(total_gold_750, 3)

    # Alloy (بار مس و نقره) مورد نیاز
    alloy_bar_needed = 0.0
    pure_bullion_needed = 0.0

    if total_gold_750 > total_raw_weight:
        # عیار بالاتر از ۷۵۰ بوده است -> نیاز به افزودن بار
        alloy_bar_needed = round(total_gold_750 - total_raw_weight, 3)
    elif total_gold_750 < total_raw_weight:
        # عیار پایین‌تر از ۷۵۰ بوده است -> نیاز به طلای ناب ۹۹۵
        pure_bullion_needed = round((total_raw_weight * (req.target_carat - (total_gold_750 * req.target_carat / total_raw_weight))) / (995 - req.target_carat), 3)

    # کسر ذوب (افت ریخته‌گری)
    melting_loss = 0.0
    if req.melted_output_weight is not None:
        total_metal_in = total_raw_weight + alloy_bar_needed
        total_metal_out = req.melted_output_weight + req.crust_weight
        melting_loss = round(total_metal_in - total_metal_out, 3)

    # ثبت در دیتابیس
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO melting_records (date_shamsi, title, raw_weight, raw_carat, target_carat, pure_gold_750, alloy_bar_needed, melted_weight, loss_weight, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.date_shamsi,
        f"{req.title} ({len(req.ingots)} شمش)",
        total_raw_weight,
        int(total_gold_750 * req.target_carat / total_raw_weight) if total_raw_weight > 0 else 750,
        req.target_carat,
        total_gold_750,
        alloy_bar_needed,
        req.melted_output_weight,
        melting_loss,
        f"ته پوسته: {req.crust_weight} گرم | {req.notes or ''}"
    ))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()

    return {
        "record_id": record_id,
        "total_raw_weight": total_raw_weight,
        "total_gold_750": total_gold_750,
        "alloy_bar_needed": alloy_bar_needed,
        "pure_bullion_needed": pure_bullion_needed,
        "crust_weight": req.crust_weight,
        "melted_output_weight": req.melted_output_weight,
        "melting_loss": melting_loss,
        "ingots_breakdown": ingots_analysis
    }


@router.post("/swarf-recovery")
def recover_swarf(req: SwarfRecoveryRequest):
    """
    قانون ۴ و ۹ دست‌نوشته همکار:
    ذوب سوآله‌ها (چرم و سوهانکاری)، ری‌گیری در آزمایشگاه، و بازگشت طلای عیار ۷50 حاصله به موجودی کارگاه
    """
    # طلای خالص عیار ۷۵۰ حاصل از بازیافت
    pure_gold_750 = round((req.melted_weight * req.lab_carat) / 750, 3)
    loss_in_recovery = round(req.raw_swarf_weight - req.melted_weight, 3)

    conn = get_db_connection()
    cursor = conn.cursor()

    # افزایش موجودی ویترین یا طلای آبشده کارگاه
    cursor.execute("""
        INSERT INTO showcase_items (code, title, category, count, gold_weight, carat, notes)
        VALUES (
            (SELECT 'RCV-' || COALESCE(MAX(id)+1, 1) FROM showcase_items),
            ?, 'طلای آبشده / بازیافت', 1, ?, 750, ?
        )
    """, (
        f"شمش بازیافتی از {req.bucket_type}",
        pure_gold_750,
        f"تاریخ: {req.date_shamsi} | وزن سوآله اولیه: {req.raw_swarf_weight} گرم | عیار ری‌گیری: {req.lab_carat} | {req.notes or ''}"
    ))

    # ثبت در رویدادها
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "recovered_gold_750": pure_gold_750,
        "loss_in_recovery": loss_in_recovery,
        "message": f"شمش بازیافتی به وزن {pure_gold_750} گرم (عیار ۷۵۰) با موفقیت به موجودی کارگاه اضافه شد."
    }


@router.post("/audit-missing-gold")
def audit_missing_gold(req: GoldAuditRequest):
    """
    قانون ۹ دست‌نوشته همکار:
    بررسی عدم مفقودی طلا یا کسر غیرمتصل (Unconnected Loss):
    ورودی اولیه - (کارهای ساخته شده + سوآله‌های چرم و تیزاب + کسر مجاز مراحل) = طلای گم‌شده یا نشتی
    """
    accounted_gold = req.finished_output_gold + req.swarf_gold_collected + abs(req.stage_losses_total)
    unconnected_loss = round(req.input_gold_750 - accounted_gold, 3)

    status = "healthy"
    message = "تراز طلای کارگاه کاملاً متصل و دقیق است؛ هیچ طلای گم‌شده‌ای وجود ندارد."

    if unconnected_loss > 0.05:  # تلورانس بیش از ۵ سوت
        status = "warning"
        message = f"هشدار کسر غیرمتصل: مقدار {unconnected_loss} گرم طلا در چرخه کارگاه کسری غیرمتصل (بلاتکلیف یا مفقودی) دارد!"
    elif unconnected_loss < -0.05:
        status = "gain"
        message = f"اضافه وزن غیرمتصل: مقدار {abs(unconnected_loss)} گرم اضافه در چرخه دیده می‌شود (احتمالاً ناشی از مفتول/لحیم مصرفی ثبت نشده)."

    return {
        "input_gold_750": req.input_gold_750,
        "accounted_gold": round(accounted_gold, 3),
        "unconnected_loss": unconnected_loss,
        "status": status,
        "message": message
    }


@router.get("/melting-records")
def list_melting_records():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM melting_records ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
