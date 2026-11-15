# -*- coding: utf-8 -*-
"""
Showcase inventory management (موجودی ویترین مغازه).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from server.database import get_db_connection

router = APIRouter(prefix="/api/showcase", tags=["Showcase"])


class ShowcaseItemCreate(BaseModel):
    code: Optional[str] = None
    title: str
    category: str
    count: int = 1
    gold_weight: float
    stone_weight: float = 0.0
    carat: int = 750
    wage_amount: float = 0.0
    wage_percent: float = 0.0
    notes: Optional[str] = ""


@router.get("/items")
def list_items(category: Optional[str] = None, search: Optional[str] = None):
    conn = get_db_connection()
    query = "SELECT * FROM showcase_items WHERE 1=1"
    params = []
    if category and category != "همه":
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (title LIKE ? OR code LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/items")
def add_or_update_item(item: ShowcaseItemCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Generate code if empty
    code = item.code
    if not code:
        last = conn.execute("SELECT MAX(id) FROM showcase_items").fetchone()[0] or 0
        code = f"DLN-{last + 1:04d}"

    cursor.execute("""
        INSERT INTO showcase_items (code, title, category, count, gold_weight, stone_weight, carat, wage_amount, wage_percent, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (code, item.title, item.category, item.count, item.gold_weight, item.stone_weight, item.carat, item.wage_amount, item.wage_percent, item.notes))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "code": code, "status": "created"}


@router.delete("/items/{item_id}")
def delete_item(item_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM showcase_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


@router.get("/summary")
def get_showcase_summary():
    conn = get_db_connection()
    row = conn.execute("""
        SELECT 
            COUNT(*) as item_types_count,
            COALESCE(SUM(count), 0) as total_pieces,
            COALESCE(SUM(gold_weight), 0.0) as total_gold_weight,
            COALESCE(SUM(stone_weight), 0.0) as total_stone_weight
        FROM showcase_items
    """).fetchone()

    # Category breakdown
    cat_rows = conn.execute("""
        SELECT category, SUM(count) as pieces, SUM(gold_weight) as weight
        FROM showcase_items
        GROUP BY category
    """).fetchall()

    conn.close()
    return {
        "item_types_count": row["item_types_count"],
        "total_pieces": row["total_pieces"],
        "total_gold_weight": round(row["total_gold_weight"], 3),
        "total_stone_weight": round(row["total_stone_weight"], 3),
        "categories": [dict(c) for c in cat_rows]
    }
