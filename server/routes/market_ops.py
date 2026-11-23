# -*- coding: utf-8 -*-
"""
Market operations, clearing, assay labs, conditional gold, ras-giri,
bank/POS accounts, checks portfolio, and scissor transfers.
Based on the best practices of Kimia Develop and Tahesab.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from server.database import get_db_connection

router = APIRouter(prefix="/api/market", tags=["Market Operations"])

# Mazane constant for 750 gold gram calculation
# Formula: 1 Gram 750 = Mazane / 4.331802
MAZANE_DIVISOR = 4.331802


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------

class AssayCreate(BaseModel):
    date_shamsi: str
    bar_code: str
    lab_name: str
    receipt_no: Optional[str] = ""
    phone: Optional[str] = ""
    raw_scale_weight: float
    provisional_carat: int = 750
    counterparty_id: Optional[int] = None
    notes: Optional[str] = ""


class AssayReconcile(BaseModel):
    final_carat: int
    notes: Optional[str] = ""


class CashifyRequest(BaseModel):
    date_shamsi: str
    counterparty_id: Optional[int] = None
    gold_weight_750: float
    mazane_rate: float
    notes: Optional[str] = ""


class GoldifyRequest(BaseModel):
    date_shamsi: str
    counterparty_id: Optional[int] = None
    toman_amount: float
    mazane_rate: float
    notes: Optional[str] = ""


class RasGiriItem(BaseModel):
    title: str
    amount: float  # weight in grams or amount in Tomans
    days_or_date: int  # days from base date or relative maturity


class RasGiriRequest(BaseModel):
    base_date_shamsi: str
    items: List[RasGiriItem]


class BankPosAccountCreate(BaseModel):
    account_title: str
    account_type: str  # 'bank', 'pos', 'loan'
    bank_name: str
    card_or_sheba: Optional[str] = ""
    pos_terminal_id: Optional[str] = ""
    balance_irr: float = 0.0
    diagnosis: str = "بدهکار به ما"
    notes: Optional[str] = ""


class CheckCreate(BaseModel):
    check_direction: str  # 'received', 'issued'
    sayad_id: Optional[str] = ""
    serial_no: Optional[str] = ""
    bank_name: str
    branch_name: Optional[str] = ""
    drawer_name: str
    payee_name: Optional[str] = ""
    counterparty_id: Optional[int] = None
    amount_irr: float
    due_date_shamsi: str
    status: str = "نزد_صندوق"
    deposit_bank_id: Optional[int] = None
    notes: Optional[str] = ""


class ScissorTransferRequest(BaseModel):
    date_shamsi: str
    transaction_id: int
    source_counterparty_id: int
    target_counterparty_id: int
    reason: Optional[str] = ""


# ---------------------------------------------------------
# 1. Assay & Conditional Melted Gold (آبشده شرطی و ری‌گیری)
# ---------------------------------------------------------

@router.get("/assays")
def list_assays():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT a.*, cp.name as counterparty_name
        FROM assay_records a
        LEFT JOIN accounts_counterparties cp ON a.counterparty_id = cp.id
        ORDER BY a.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/assays")
def create_assay_record(req: AssayCreate):
    equiv_initial = round((req.raw_scale_weight * req.provisional_carat) / 750, 3)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO assay_records (
            date_shamsi, bar_code, lab_name, receipt_no, phone,
            raw_scale_weight, provisional_carat, equiv_750_initial,
            counterparty_id, status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        req.date_shamsi, req.bar_code, req.lab_name, req.receipt_no, req.phone,
        req.raw_scale_weight, req.provisional_carat, equiv_initial,
        req.counterparty_id, req.notes
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "status": "pending", "equiv_750_initial": equiv_initial}


@router.put("/assays/{assay_id}/reconcile")
def reconcile_assay(assay_id: int, req: AssayReconcile):
    """
    تطبیق عیار آزمایشگاه ری‌گیری:
    محاسبه وزن معادل قطعی ۷۵۰ و ثبت اختلاف (کسری یا مازاد) در حساب طرف‌حساب
    """
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM assay_records WHERE id = ?", (assay_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="رکورد ری‌گیری یافت نشد")

    assay = dict(row)
    raw_weight = assay["raw_scale_weight"]
    equiv_initial = assay["equiv_750_initial"]
    equiv_final = round((raw_weight * req.final_carat) / 750, 3)
    variance_750 = round(equiv_final - equiv_initial, 3)

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE assay_records
        SET final_carat = ?,
            equiv_750_final = ?,
            variance_750 = ?,
            status = 'confirmed',
            notes = COALESCE(notes, '') || ' | ' || ?
        WHERE id = ?
    """, (req.final_carat, equiv_final, variance_750, req.notes or f"عیار قطعی {req.final_carat}", assay_id))

    # اگر طرف‌حساب متصل است، اختلاف وزنی را در مانده طلایی او اعمال کن
    if assay["counterparty_id"] and variance_750 != 0.0:
        cursor.execute("""
            UPDATE accounts_counterparties
            SET balance_gold_750 = balance_gold_750 + ?
            WHERE id = ?
        """, (variance_750, assay["counterparty_id"]))

        # ثبت سند اصلاحی در تراکنش‌ها
        cursor.execute("""
            INSERT INTO counterparty_transactions (
                counterparty_id, date_shamsi, tx_type, gold_weight_in, gold_weight_out,
                carat, irr_amount_in, irr_amount_out, description
            ) VALUES (?, ?, 'تعدیل ری‌گیری', ?, 0.0, 750, 0.0, 0.0, ?)
        """, (
            assay["counterparty_id"], assay["date_shamsi"],
            variance_750 if variance_750 > 0 else 0.0,
            f"تعدیل عیار ری‌گیری انگ {assay['bar_code']} (عیار {req.final_carat} نسبت به {assay['provisional_carat']})"
        ))

    conn.commit()
    conn.close()
    return {
        "status": "confirmed",
        "equiv_750_final": equiv_final,
        "variance_750": variance_750
    }


# ---------------------------------------------------------
# 2. Cashify & Goldify (پولی‌کردن و طلایی‌کردن)
# ---------------------------------------------------------

@router.post("/cashify")
def execute_cashify(req: CashifyRequest):
    """
    پولی کردن طلا (Cashify):
    تبدیل گرم طلا به تومان بر مبنای مظنه لحظه‌ای بازار تهران
    فرمول: قیمت هر گرم = مظنه / ۴.۳۳۱۸۰۲
    """
    if req.mazane_rate <= 0:
        raise HTTPException(status_code=400, detail="مظنه طلا باید بزرگتر از صفر باشد")

    gram_price = round(req.mazane_rate / MAZANE_DIVISOR, 0)
    total_toman = round(req.gold_weight_750 * gram_price, 0)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO gold_cash_conversions (
            date_shamsi, conversion_type, counterparty_id, mazane_rate,
            gram_price_750, gold_weight_750, toman_amount, notes
        ) VALUES (?, 'cashify', ?, ?, ?, ?, ?, ?)
    """, (
        req.date_shamsi, req.counterparty_id, req.mazane_rate,
        gram_price, req.gold_weight_750, total_toman, req.notes
    ))
    new_id = cursor.lastrowid

    # در صورت وجود طرف‌حساب، حساب طلایی بستانکار و حساب ریالی بدهکار می‌شود (یا برعکس طبق عرف)
    if req.counterparty_id:
        cursor.execute("""
            UPDATE accounts_counterparties
            SET balance_gold_750 = balance_gold_750 - ?,
                balance_irr = balance_irr + ?
            WHERE id = ?
        """, (req.gold_weight_750, total_toman, req.counterparty_id))

        cursor.execute("""
            INSERT INTO counterparty_transactions (
                counterparty_id, date_shamsi, tx_type, gold_weight_in, gold_weight_out,
                carat, irr_amount_in, irr_amount_out, description
            ) VALUES (?, ?, 'پولی کردن طلا', 0.0, ?, 750, ?, 0.0, ?)
        """, (
            req.counterparty_id, req.date_shamsi, req.gold_weight_750, total_toman,
            f"پولی کردن {req.gold_weight_750} گرم طلا با مظنه {req.mazane_rate:,.0f}"
        ))

    conn.commit()
    conn.close()
    return {
        "id": new_id,
        "conversion_type": "cashify",
        "gram_price_750": gram_price,
        "toman_amount": total_toman
    }


@router.post("/goldify")
def execute_goldify(req: GoldifyRequest):
    """
    طلایی کردن پول/اجرت (Goldify):
    تبدیل مبلغ تومانی به معادل گرم طلا ۷۵۰ بر مبنای مظنه لحظه‌ای
    """
    if req.mazane_rate <= 0:
        raise HTTPException(status_code=400, detail="مظنه طلا باید بزرگتر از صفر باشد")

    gram_price = req.mazane_rate / MAZANE_DIVISOR
    gold_weight = round(req.toman_amount / gram_price, 3)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO gold_cash_conversions (
            date_shamsi, conversion_type, counterparty_id, mazane_rate,
            gram_price_750, gold_weight_750, toman_amount, notes
        ) VALUES (?, 'goldify', ?, ?, ?, ?, ?, ?)
    """, (
        req.date_shamsi, req.counterparty_id, req.mazane_rate,
        round(gram_price, 0), gold_weight, req.toman_amount, req.notes
    ))
    new_id = cursor.lastrowid

    if req.counterparty_id:
        cursor.execute("""
            UPDATE accounts_counterparties
            SET balance_irr = balance_irr - ?,
                balance_gold_750 = balance_gold_750 + ?
            WHERE id = ?
        """, (req.toman_amount, gold_weight, req.counterparty_id))

        cursor.execute("""
            INSERT INTO counterparty_transactions (
                counterparty_id, date_shamsi, tx_type, gold_weight_in, gold_weight_out,
                carat, irr_amount_in, irr_amount_out, description
            ) VALUES (?, ?, 'طلایی کردن اجرت/وجه', ?, 0.0, 750, 0.0, ?, ?)
        """, (
            req.counterparty_id, req.date_shamsi, gold_weight, req.toman_amount,
            f"طلایی کردن {req.toman_amount:,.0f} تومان با مظنه {req.mazane_rate:,.0f}"
        ))

    conn.commit()
    conn.close()
    return {
        "id": new_id,
        "conversion_type": "goldify",
        "gram_price_750": round(gram_price, 0),
        "gold_weight_750": gold_weight
    }


@router.get("/conversions")
def list_conversions():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT c.*, cp.name as counterparty_name
        FROM gold_cash_conversions c
        LEFT JOIN accounts_counterparties cp ON c.counterparty_id = cp.id
        ORDER BY c.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------
# 3. Ras-giri (رأس‌گیری طلا و چک)
# ---------------------------------------------------------

@router.post("/rasgiri")
def calculate_rasgiri(req: RasGiriRequest):
    """
    محاسبه رأس‌گیری وزنی و تاریخی:
    فرمول: مجموع (مقدار * روز) تقسیم بر مجموع مقادیر
    """
    total_amount = sum(it.amount for it in req.items)
    if total_amount <= 0:
        raise HTTPException(status_code=400, detail="مجموع مقادیر باید بزرگتر از صفر باشد")

    weighted_days_sum = sum(it.amount * it.days_or_date for it in req.items)
    average_days = round(weighted_days_sum / total_amount, 1)

    return {
        "base_date_shamsi": req.base_date_shamsi,
        "total_amount": round(total_amount, 3),
        "weighted_average_days": average_days,
        "formula_description": f"رأس سررسید میانگین: {average_days} روز پس از تاریخ پایه {req.base_date_shamsi}"
    }


# ---------------------------------------------------------
# 4. Bank & POS Accounts (تفکیک بانک، پوز شاپرک و وام)
# ---------------------------------------------------------

@router.get("/accounts")
def list_bank_pos_accounts():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM bank_and_pos_accounts ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/accounts")
def create_bank_pos_account(acc: BankPosAccountCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bank_and_pos_accounts (
            account_title, account_type, bank_name, card_or_sheba,
            pos_terminal_id, balance_irr, diagnosis, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        acc.account_title, acc.account_type, acc.bank_name, acc.card_or_sheba,
        acc.pos_terminal_id, acc.balance_irr, acc.diagnosis, acc.notes
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "status": "created"}


# ---------------------------------------------------------
# 5. Checks Portfolio (سبد چک‌های صیادی و شخصی)
# ---------------------------------------------------------

@router.get("/checks")
def list_checks():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT c.*, cp.name as counterparty_name
        FROM checks_portfolio c
        LEFT JOIN accounts_counterparties cp ON c.counterparty_id = cp.id
        ORDER BY c.due_date_shamsi ASC, c.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/checks")
def create_check(chk: CheckCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO checks_portfolio (
            check_direction, sayad_id, serial_no, bank_name, branch_name,
            drawer_name, payee_name, counterparty_id, amount_irr,
            due_date_shamsi, status, deposit_bank_id, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chk.check_direction, chk.sayad_id, chk.serial_no, chk.bank_name, chk.branch_name,
        chk.drawer_name, chk.payee_name, chk.counterparty_id, chk.amount_irr,
        chk.due_date_shamsi, chk.status, chk.deposit_bank_id, chk.notes
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "status": "created"}


@router.put("/checks/{check_id}/status")
def update_check_status(check_id: int, new_status: str, deposit_bank_id: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE checks_portfolio
        SET status = ?,
            deposit_bank_id = COALESCE(?, deposit_bank_id)
        WHERE id = ?
    """, (new_status, deposit_bank_id, check_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "new_status": new_status}


# ---------------------------------------------------------
# 6. Scissor Tool (قیچی و انتقال اسناد)
# ---------------------------------------------------------

@router.post("/scissor")
def execute_scissor_transfer(req: ScissorTransferRequest):
    """
    قیچی سند:
    انتقال کامل یک سند یا تراکنش از حساب شخص منبع به حساب شخص مقصد
    بدون ایجاد عدم تعادل در گردش حساب و با ثبت ردپا در لاگ امنیتی
    """
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM counterparty_transactions WHERE id = ?", (req.transaction_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="تراکنش مورد نظر جهت قیچی یافت نشد")

    tx = dict(row)
    gold_750 = round(((tx["gold_weight_in"] - tx["gold_weight_out"]) * tx["carat"]) / 750, 3)
    irr_net = tx["irr_amount_in"] - tx["irr_amount_out"]

    cursor = conn.cursor()

    # 1. کسر اثر از شخص مبدا
    cursor.execute("""
        UPDATE accounts_counterparties
        SET balance_gold_750 = balance_gold_750 - ?,
            balance_irr = balance_irr - ?
        WHERE id = ?
    """, (gold_750, irr_net, req.source_counterparty_id))

    # 2. افزودن اثر به شخص مقصد
    cursor.execute("""
        UPDATE accounts_counterparties
        SET balance_gold_750 = balance_gold_750 + ?,
            balance_irr = balance_irr + ?
        WHERE id = ?
    """, (gold_750, irr_net, req.target_counterparty_id))

    # 3. تغییر مالکیت تراکنش
    cursor.execute("""
        UPDATE counterparty_transactions
        SET counterparty_id = ?,
            description = COALESCE(description, '') || ' [قیچی‌شده از شخص کد ' || ? || ']'
        WHERE id = ?
    """, (req.target_counterparty_id, req.source_counterparty_id, req.transaction_id))

    # 4. ثبت در دفترچه لاگ قیچی
    cursor.execute("""
        INSERT INTO scissor_audit_logs (
            date_shamsi, source_counterparty_id, target_counterparty_id,
            voucher_type, voucher_id, gold_weight_750, irr_amount, reason
        ) VALUES (?, ?, ?, 'counterparty_transaction', ?, ?, ?, ?)
    """, (
        req.date_shamsi, req.source_counterparty_id, req.target_counterparty_id,
        req.transaction_id, gold_750, irr_net, req.reason or "انتقال سند با ابزار قیچی"
    ))

    conn.commit()
    conn.close()
    return {
        "status": "transferred",
        "gold_weight_750": gold_750,
        "irr_amount": irr_net
    }
