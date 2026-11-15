# -*- coding: utf-8 -*-
"""
Counterparties (طرف‌حساب‌ها مانند آقای آزادی)، مخارج کارگاه (اسید، رزین، حقوق)، و سود و زیان.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from server.database import get_db_connection

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


class CounterpartyCreate(BaseModel):
    name: str
    role: str = "بنکدار / تامین‌کننده"
    phone: Optional[str] = ""
    balance_gold_750: float = 0.0
    balance_irr: float = 0.0
    notes: Optional[str] = ""


class CounterpartyTransactionCreate(BaseModel):
    counterparty_id: int
    date_shamsi: str
    tx_type: str  # ورود شمش، خروج کار ساخته، پرداخت ریالی، دریافت ریالی
    gold_weight_in: float = 0.0
    gold_weight_out: float = 0.0
    carat: int = 750
    irr_amount_in: float = 0.0
    irr_amount_out: float = 0.0
    description: Optional[str] = ""


class WorkshopExpenseCreate(BaseModel):
    date_shamsi: str
    category: str  # حقوق، اسید، رزین، اجرت تراش، اجرت زنجیر، مته و ابزار، متفرقه
    amount: float
    payee: Optional[str] = ""
    description: Optional[str] = ""


@router.get("/counterparties")
def list_counterparties():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM accounts_counterparties ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/counterparties")
def create_counterparty(cp: CounterpartyCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts_counterparties (name, role, phone, balance_gold_750, balance_irr, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (cp.name, cp.role, cp.phone, cp.balance_gold_750, cp.balance_irr, cp.notes))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "status": "created"}


@router.get("/transactions/{counterparty_id}")
def get_party_transactions(counterparty_id: int):
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM counterparty_transactions 
        WHERE counterparty_id = ? 
        ORDER BY id DESC
    """, (counterparty_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/transactions")
def add_party_transaction(tx: CounterpartyTransactionCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Convert gold weight to 750
    gold_750_in = round((tx.gold_weight_in * tx.carat) / 750, 3)
    gold_750_out = round((tx.gold_weight_out * tx.carat) / 750, 3)

    cursor.execute("""
        INSERT INTO counterparty_transactions (
            counterparty_id, date_shamsi, tx_type, gold_weight_in, gold_weight_out,
            carat, irr_amount_in, irr_amount_out, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tx.counterparty_id, tx.date_shamsi, tx.tx_type, tx.gold_weight_in, tx.gold_weight_out,
        tx.carat, tx.irr_amount_in, tx.irr_amount_out, tx.description
    ))

    # Update party balance
    net_gold = gold_750_in - gold_750_out
    net_irr = tx.irr_amount_in - tx.irr_amount_out

    cursor.execute("""
        UPDATE accounts_counterparties
        SET balance_gold_750 = balance_gold_750 + ?,
            balance_irr = balance_irr + ?
        WHERE id = ?
    """, (net_gold, net_irr, tx.counterparty_id))

    conn.commit()
    conn.close()
    return {"status": "success", "net_gold_750": net_gold, "net_irr": net_irr}


@router.get("/expenses")
def list_expenses():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM workshop_expenses ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/expenses")
def add_expense(exp: WorkshopExpenseCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workshop_expenses (date_shamsi, category, amount, payee, description)
        VALUES (?, ?, ?, ?, ?)
    """, (exp.date_shamsi, exp.category, exp.amount, exp.payee, exp.description))

    # Record in cashbox log as outgoing cash
    cursor.execute("""
        INSERT INTO cashbox_logs (date_shamsi, tx_type, amount, category, description)
        VALUES (?, 'خروج', ?, ?, ?)
    """, (exp.date_shamsi, exp.amount, f"هزینه {exp.category}", f"{exp.payee or ''} - {exp.description or ''}"))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "status": "created"}


@router.get("/pnl")
def get_pnl_summary():
    """محاسبه سود و زیان با در نظر گرفتن درآمد فروش و کسر هزینه‌های کارگاه (حقوق، اسید، تراش، زنجیر و...)"""
    conn = get_db_connection()

    # Total Sales Revenue
    sales_row = conn.execute("""
        SELECT COALESCE(SUM(total_amount), 0) as total_sales,
               COALESCE(SUM(total_wage), 0) as total_wages_earned,
               COALESCE(SUM(total_gold_weight), 0.0) as total_gold_sold
        FROM sales_invoices
    """).fetchone()

    # Total Expenses
    exp_rows = conn.execute("""
        SELECT category, SUM(amount) as cat_total
        FROM workshop_expenses
        GROUP BY category
    """).fetchall()

    total_expenses = sum(r["cat_total"] for r in exp_rows)

    # Cashbox balance
    cash_in = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM cashbox_logs WHERE tx_type = 'ورود'").fetchone()[0]
    cash_out = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM cashbox_logs WHERE tx_type = 'خروج'").fetchone()[0]

    # Total Workshop Gold Loss (کسری کل کارگاه)
    total_workshop_loss = conn.execute("SELECT COALESCE(SUM(loss_weight), 0.0) FROM workshop_tasks").fetchone()[0]

    conn.close()

    net_profit = sales_row["total_wages_earned"] - total_expenses

    return {
        "total_sales_revenue": sales_row["total_sales"],
        "total_wages_earned": sales_row["total_wages_earned"],
        "total_gold_sold_weight": round(sales_row["total_gold_sold"], 3),
        "total_expenses": total_expenses,
        "expenses_by_category": [dict(r) for r in exp_rows],
        "net_profit_estimate": net_profit,
        "cashbox_balance": cash_in - cash_out,
        "total_workshop_loss_grams": round(total_workshop_loss, 3)
    }
