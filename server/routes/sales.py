# -*- coding: utf-8 -*-
"""
Sales invoices, trade-ins (تعویض طلا), and scrap/melted gold purchases.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from server.database import get_db_connection

router = APIRouter(prefix="/api/sales", tags=["Sales"])


class InvoiceItemPayload(BaseModel):
    showcase_item_id: Optional[int] = None
    title: str
    weight: float
    count: int = 1
    wage_amount: float = 0.0
    total_price: float


class TradeInPayload(BaseModel):
    title: str
    weight: float
    carat: int = 750
    unit_price: float
    total_credit: float
    notes: Optional[str] = ""


class InvoiceCreate(BaseModel):
    customer_name: str = "مشتری محترم"
    customer_phone: Optional[str] = ""
    date_shamsi: str
    gold_rate_per_gram: float
    total_gold_weight: float
    total_wage: float = 0.0
    profit_percent: float = 7.0
    tax_percent: float = 0.0
    discount_amount: float = 0.0
    total_amount: float
    payment_method: str = "کارتخوان"
    notes: Optional[str] = ""
    items: List[InvoiceItemPayload]
    trade_ins: Optional[List[TradeInPayload]] = []


class DirectPurchaseCreate(BaseModel):
    date_shamsi: str
    title: str  # مثلا خرید طلای آبشده یا خرید طلای دست دوم
    weight: float
    carat: int = 750
    rate_per_gram: float
    total_amount: float
    seller_name: Optional[str] = "مشتری / همکار"
    notes: Optional[str] = ""


@router.get("/invoices")
def list_invoices():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM sales_invoices ORDER BY id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/invoices/{invoice_id}")
def get_invoice_detail(invoice_id: int):
    conn = get_db_connection()
    inv = conn.execute("SELECT * FROM sales_invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not inv:
        conn.close()
        raise HTTPException(status_code=404, detail="فاکتور یافت نشد")

    items = conn.execute("SELECT * FROM sales_invoice_items WHERE invoice_id = ?", (invoice_id,)).fetchall()
    trade_ins = conn.execute("SELECT * FROM trade_ins WHERE invoice_id = ?", (invoice_id,)).fetchall()
    conn.close()

    return {
        "invoice": dict(inv),
        "items": [dict(it) for it in items],
        "trade_ins": [dict(tr) for tr in trade_ins]
    }


@router.post("/invoices")
def create_invoice(payload: InvoiceCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate invoice number
    count_today = conn.execute("SELECT COUNT(*) FROM sales_invoices WHERE date_shamsi = ?", (payload.date_shamsi,)).fetchone()[0]
    date_clean = payload.date_shamsi.replace('/', '')
    inv_no = f"INV-{date_clean}-{count_today + 1:03d}"

    cursor.execute("""
        INSERT INTO sales_invoices (
            invoice_no, customer_name, customer_phone, date_shamsi, gold_rate_per_gram,
            total_gold_weight, total_wage, profit_percent, tax_percent, discount_amount,
            total_amount, payment_method, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        inv_no, payload.customer_name, payload.customer_phone, payload.date_shamsi, payload.gold_rate_per_gram,
        payload.total_gold_weight, payload.total_wage, payload.profit_percent, payload.tax_percent, payload.discount_amount,
        payload.total_amount, payload.payment_method, payload.notes
    ))
    invoice_id = cursor.lastrowid

    # Insert items & deduct from showcase
    for item in payload.items:
        cursor.execute("""
            INSERT INTO sales_invoice_items (invoice_id, showcase_item_id, title, weight, count, wage_amount, total_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (invoice_id, item.showcase_item_id, item.title, item.weight, item.count, item.wage_amount, item.total_price))

        if item.showcase_item_id:
            # Deduct piece count and weight from showcase
            showcase_row = conn.execute("SELECT count, gold_weight FROM showcase_items WHERE id = ?", (item.showcase_item_id,)).fetchone()
            if showcase_row:
                new_count = max(0, showcase_row["count"] - item.count)
                new_weight = max(0.0, round(showcase_row["gold_weight"] - item.weight, 3))
                if new_count == 0:
                    cursor.execute("DELETE FROM showcase_items WHERE id = ?", (item.showcase_item_id,))
                else:
                    cursor.execute("UPDATE showcase_items SET count = ?, gold_weight = ? WHERE id = ?", (new_count, new_weight, item.showcase_item_id))

    # Insert trade-ins (تعویض طلا)
    total_trade_in_credit = 0.0
    for tr in (payload.trade_ins or []):
        calc_750 = round((tr.weight * tr.carat) / 750, 3)
        cursor.execute("""
            INSERT INTO trade_ins (invoice_id, date_shamsi, title, weight, carat, calculated_750_weight, unit_price, total_credit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (invoice_id, payload.date_shamsi, tr.title, tr.weight, tr.carat, calc_750, tr.unit_price, tr.total_credit, tr.notes))
        total_trade_in_credit += tr.total_credit

    # Add net cash to cashbox log
    net_cash_received = payload.total_amount
    cursor.execute("""
        INSERT INTO cashbox_logs (date_shamsi, tx_type, amount, category, description)
        VALUES (?, 'ورود', ?, 'فروش طلا', ?)
    """, (payload.date_shamsi, net_cash_received, f"فاکتور فروش {inv_no} - {payload.customer_name}"))

    conn.commit()
    conn.close()

    return {
        "invoice_id": invoice_id,
        "invoice_no": inv_no,
        "net_amount": payload.total_amount,
        "status": "created"
    }


@router.post("/direct-purchase")
def direct_purchase(p: DirectPurchaseCreate):
    """خرید طلای آبشده یا طلای دست‌دوم مستقیماً از محل صندوق"""
    calc_750 = round((p.weight * p.carat) / 750, 3)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trade_ins (invoice_id, date_shamsi, title, weight, carat, calculated_750_weight, unit_price, total_credit, notes)
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (p.date_shamsi, p.title, p.weight, p.carat, calc_750, p.rate_per_gram, p.total_amount, f"فروشنده: {p.seller_name} - {p.notes}"))

    # Log cash out
    cursor.execute("""
        INSERT INTO cashbox_logs (date_shamsi, tx_type, amount, category, description)
        VALUES (?, 'خروج', ?, 'خرید طلا', ?)
    """, (p.date_shamsi, p.total_amount, f"{p.title} به وزن {p.weight} گرم از {p.seller_name}"))

    conn.commit()
    conn.close()
    return {"status": "success", "calculated_750": calc_750, "total_paid": p.total_amount}
