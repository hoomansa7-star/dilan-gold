# -*- coding: utf-8 -*-
"""
Database configuration for Dilan Gold ERP.
Supports both:
1. Cloud PostgreSQL (Supabase / Render / Neon) when DATABASE_URL is configured.
2. Local SQLite with WAL mode and foreign keys (offline / development fallback).
"""

import os
import shutil
import sqlite3
from datetime import datetime
from typing import Optional, Any

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
BACKUP_DIR = os.path.join(DB_DIR, "backups")
DB_PATH = os.path.join(DB_DIR, "dilan_gold.db")

try:
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
except OSError:
    # Serverless environment (Vercel / Lambda) where root is read-only
    DB_DIR = "/tmp"
    BACKUP_DIR = "/tmp/backups"
    DB_PATH = "/tmp/dilan_gold.db"
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except OSError:
        pass


def get_database_url() -> Optional[str]:
    """Returns normalized DATABASE_URL if set, fixing postgres:// prefix for psycopg2."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    # Fix Heroku/Supabase legacy postgres:// prefix
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def is_postgres() -> bool:
    """Returns True if a valid DATABASE_URL is configured."""
    return get_database_url() is not None


class PostgresCursorWrapper:
    """
    Transparent cursor wrapper for PostgreSQL that provides:
    1. Automatic '?' to '%s' parameter placeholder translation.
    2. Automatic 'RETURNING id' injection on INSERTs to populate cursor.lastrowid.
    3. Mapping of psycopg2.IntegrityError to sqlite3.IntegrityError for unified route handling.
    """
    def __init__(self, raw_cursor):
        self._cursor = raw_cursor
        self.lastrowid = None

    def execute(self, sql: str, params: Any = None):
        # Convert SQLite '?' placeholders to Postgres '%s'
        pg_sql = sql.replace('?', '%s')
        
        stripped = pg_sql.strip()
        is_insert = stripped.upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in stripped.upper()
        
        if is_insert and not has_returning:
            pg_sql = pg_sql.rstrip().rstrip(';') + " RETURNING id;"

        try:
            if params is not None:
                self._cursor.execute(pg_sql, params)
            else:
                self._cursor.execute(pg_sql)

            if is_insert and not has_returning:
                try:
                    res = self._cursor.fetchone()
                    if res is not None:
                        self.lastrowid = res[0]
                except Exception:
                    pass
            return self
        except Exception as e:
            if PSYCOPG2_AVAILABLE and isinstance(e, psycopg2.IntegrityError):
                raise sqlite3.IntegrityError(str(e)) from e
            raise

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size: Optional[int] = None):
        return self._cursor.fetchmany(size)

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PostgresConnectionWrapper:
    """
    Transparent connection wrapper for PostgreSQL matching the sqlite3 Connection API:
    - conn.execute(...)
    - conn.cursor() with DictCursor factory
    - conn.commit(), conn.rollback(), conn.close()
    """
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def execute(self, sql: str, params: Any = None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()


def get_db_connection():
    """
    Returns an active database connection.
    Connects to Supabase/PostgreSQL if DATABASE_URL is defined;
    otherwise falls back to local SQLite with WAL mode.
    """
    db_url = get_database_url()
    if db_url:
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 is required for PostgreSQL connections. Run 'pip install psycopg2-binary'.")
        conn = psycopg2.connect(db_url)
        return PostgresConnectionWrapper(conn)

    # Local SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Initializes tables, indices, and seeds default master data for both SQLite and PostgreSQL."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if is_postgres():
        # PostgreSQL / Supabase DDL
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS craftsmen (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            role TEXT DEFAULT 'سازنده طلا',
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_shifts (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL UNIQUE,
            day_of_week TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            total_loss DOUBLE PRECISION DEFAULT 0.0,
            total_swarf DOUBLE PRECISION DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_batches (
            id SERIAL PRIMARY KEY,
            shift_id INTEGER NOT NULL REFERENCES daily_shifts(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            total_count INTEGER DEFAULT 1,
            total_weight DOUBLE PRECISION NOT NULL,
            carat INTEGER DEFAULT 750,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_tasks (
            id SERIAL PRIMARY KEY,
            shift_id INTEGER NOT NULL REFERENCES daily_shifts(id) ON DELETE CASCADE,
            batch_id INTEGER REFERENCES workshop_batches(id) ON DELETE SET NULL,
            craftsman_id INTEGER NOT NULL REFERENCES craftsmen(id),
            stage TEXT NOT NULL,
            item_name TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            input_weight DOUBLE PRECISION NOT NULL,
            output_weight DOUBLE PRECISION NOT NULL,
            loss_weight DOUBLE PRECISION NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_incidents (
            id SERIAL PRIMARY KEY,
            shift_id INTEGER NOT NULL REFERENCES daily_shifts(id) ON DELETE CASCADE,
            craftsman_id INTEGER REFERENCES craftsmen(id),
            title TEXT NOT NULL,
            weight DOUBLE PRECISION NOT NULL,
            target_bucket TEXT DEFAULT 'سوآله چرم و سوهانکاری',
            weight_after DOUBLE PRECISION,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS melting_records (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            title TEXT NOT NULL,
            raw_weight DOUBLE PRECISION NOT NULL,
            raw_carat INTEGER NOT NULL,
            target_carat INTEGER DEFAULT 750,
            pure_gold_750 DOUBLE PRECISION NOT NULL,
            alloy_bar_needed DOUBLE PRECISION DEFAULT 0.0,
            melted_weight DOUBLE PRECISION,
            loss_weight DOUBLE PRECISION DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS showcase_items (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            gold_weight DOUBLE PRECISION NOT NULL,
            stone_weight DOUBLE PRECISION DEFAULT 0.0,
            carat INTEGER DEFAULT 750,
            wage_amount DOUBLE PRECISION DEFAULT 0.0,
            wage_percent DOUBLE PRECISION DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_invoices (
            id SERIAL PRIMARY KEY,
            invoice_no TEXT UNIQUE NOT NULL,
            customer_name TEXT DEFAULT 'مشتری حضوری',
            customer_phone TEXT,
            date_shamsi TEXT NOT NULL,
            gold_rate_per_gram DOUBLE PRECISION NOT NULL,
            total_gold_weight DOUBLE PRECISION NOT NULL,
            total_wage DOUBLE PRECISION DEFAULT 0.0,
            profit_percent DOUBLE PRECISION DEFAULT 7.0,
            tax_percent DOUBLE PRECISION DEFAULT 0.0,
            discount_amount DOUBLE PRECISION DEFAULT 0.0,
            total_amount DOUBLE PRECISION NOT NULL,
            payment_method TEXT DEFAULT 'کارتخوان',
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_invoice_items (
            id SERIAL PRIMARY KEY,
            invoice_id INTEGER NOT NULL REFERENCES sales_invoices(id) ON DELETE CASCADE,
            showcase_item_id INTEGER REFERENCES showcase_items(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            category TEXT,
            weight DOUBLE PRECISION NOT NULL,
            count INTEGER DEFAULT 1,
            wage_amount DOUBLE PRECISION DEFAULT 0.0,
            total_price DOUBLE PRECISION NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_ins (
            id SERIAL PRIMARY KEY,
            invoice_id INTEGER REFERENCES sales_invoices(id) ON DELETE SET NULL,
            date_shamsi TEXT NOT NULL,
            title TEXT NOT NULL,
            weight DOUBLE PRECISION NOT NULL,
            carat INTEGER DEFAULT 750,
            calculated_750_weight DOUBLE PRECISION NOT NULL,
            unit_price DOUBLE PRECISION NOT NULL,
            total_credit DOUBLE PRECISION NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts_counterparties (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            role TEXT DEFAULT 'بنکدار / تامین‌کننده',
            phone TEXT,
            balance_gold_750 DOUBLE PRECISION DEFAULT 0.0,
            balance_irr DOUBLE PRECISION DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS counterparty_transactions (
            id SERIAL PRIMARY KEY,
            counterparty_id INTEGER NOT NULL REFERENCES accounts_counterparties(id) ON DELETE CASCADE,
            date_shamsi TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            gold_weight_in DOUBLE PRECISION DEFAULT 0.0,
            gold_weight_out DOUBLE PRECISION DEFAULT 0.0,
            carat INTEGER DEFAULT 750,
            irr_amount_in DOUBLE PRECISION DEFAULT 0.0,
            irr_amount_out DOUBLE PRECISION DEFAULT 0.0,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_expenses (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            category TEXT NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            payee TEXT,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cashbox_logs (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            category TEXT,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 15. Craftsmen Settlements / Wage Payroll (تسویه حساب و کارکرد پرسنل)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS craftsmen_settlements (
            id SERIAL PRIMARY KEY,
            craftsman_id INTEGER NOT NULL REFERENCES craftsmen(id) ON DELETE CASCADE,
            date_shamsi TEXT NOT NULL,
            period_title TEXT NOT NULL,
            total_worked_grams DOUBLE PRECISION DEFAULT 0.0,
            wage_rate_irr DOUBLE PRECISION DEFAULT 0.0,
            total_wage_irr DOUBLE PRECISION DEFAULT 0.0,
            paid_amount_irr DOUBLE PRECISION DEFAULT 0.0,
            paid_gold_weight DOUBLE PRECISION DEFAULT 0.0,
            settlement_status TEXT DEFAULT 'تسویه_شده',
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 16. Crucible Records (دفترچه تخصصی بوته‌های ذوب و شیره)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crucible_records (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            crucible_code TEXT NOT NULL,
            operator_name TEXT DEFAULT 'مسئول ذوب',
            raw_gold_weight DOUBLE PRECISION NOT NULL,
            raw_carat INTEGER NOT NULL,
            target_carat INTEGER DEFAULT 750,
            alloy_bar_added DOUBLE PRECISION DEFAULT 0.0,
            melted_bar_weight DOUBLE PRECISION NOT NULL,
            sheereh_weight DOUBLE PRECISION DEFAULT 0.0,
            loss_weight DOUBLE PRECISION NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 17. Solder Recipes (فرمول‌های ساخت انواع لحیم زرگری)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS solder_recipes (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL UNIQUE,
            solder_type TEXT NOT NULL,
            base_gold_weight DOUBLE PRECISION NOT NULL,
            base_carat INTEGER DEFAULT 750,
            cadmium_percent DOUBLE PRECISION NOT NULL,
            cadmium_weight DOUBLE PRECISION NOT NULL,
            silver_weight DOUBLE PRECISION DEFAULT 0.0,
            copper_weight DOUBLE PRECISION DEFAULT 0.0,
            total_solder_weight DOUBLE PRECISION NOT NULL,
            final_carat INTEGER NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 18. Refining Batches (محموله‌های ارسالی به قالکاری و تیزاب‌کاری)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS refining_batches (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            batch_code TEXT NOT NULL UNIQUE,
            refiner_name TEXT NOT NULL,
            material_type TEXT DEFAULT 'سوآله چرم و سوهان',
            sent_weight DOUBLE PRECISION NOT NULL,
            recovered_gold_750 DOUBLE PRECISION DEFAULT 0.0,
            refining_fee_irr DOUBLE PRECISION DEFAULT 0.0,
            status TEXT DEFAULT 'در_حال_تیزاب',
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 19. Assay Records (مدیریت آبشده‌های شرطی، ری‌گیری و تطبیق کسری/مازاد عیار)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assay_records (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            bar_code TEXT NOT NULL,
            lab_name TEXT NOT NULL,
            receipt_no TEXT,
            phone TEXT,
            raw_scale_weight DOUBLE PRECISION NOT NULL,
            provisional_carat INTEGER DEFAULT 750,
            final_carat INTEGER,
            equiv_750_initial DOUBLE PRECISION NOT NULL,
            equiv_750_final DOUBLE PRECISION,
            variance_750 DOUBLE PRECISION DEFAULT 0.0,
            counterparty_id INTEGER REFERENCES accounts_counterparties(id) ON DELETE SET NULL,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 20. Bank & POS Accounts (تفکیک حساب‌های بانکی، دستگاه‌های پوز شاپرک و وام‌ها)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_and_pos_accounts (
            id SERIAL PRIMARY KEY,
            account_title TEXT NOT NULL,
            account_type TEXT NOT NULL,
            bank_name TEXT NOT NULL,
            card_or_sheba TEXT,
            pos_terminal_id TEXT,
            balance_irr DOUBLE PRECISION DEFAULT 0.0,
            diagnosis TEXT DEFAULT 'بدهکار به ما',
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 21. Gold / Cash Conversions (دفتر ثبت رسمی پولی‌کردن و طلایی‌کردن با مظنه روز)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_cash_conversions (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            conversion_type TEXT NOT NULL,
            counterparty_id INTEGER REFERENCES accounts_counterparties(id) ON DELETE SET NULL,
            mazane_rate DOUBLE PRECISION NOT NULL,
            gram_price_750 DOUBLE PRECISION NOT NULL,
            gold_weight_750 DOUBLE PRECISION NOT NULL,
            toman_amount DOUBLE PRECISION NOT NULL,
            voucher_code TEXT,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 22. Checks Portfolio (سبد چک‌های صیادی اشخاص و چک‌های شخصی صادره)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS checks_portfolio (
            id SERIAL PRIMARY KEY,
            check_direction TEXT NOT NULL,
            sayad_id TEXT,
            serial_no TEXT,
            bank_name TEXT NOT NULL,
            branch_name TEXT,
            drawer_name TEXT NOT NULL,
            payee_name TEXT,
            counterparty_id INTEGER REFERENCES accounts_counterparties(id) ON DELETE SET NULL,
            amount_irr DOUBLE PRECISION NOT NULL,
            due_date_shamsi TEXT NOT NULL,
            status TEXT DEFAULT 'نزد_صندوق',
            deposit_bank_id INTEGER,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 23. Scissor Audit Logs (دفتر ثبت قیچی و انتقال فاکتور بین اشخاص)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scissor_audit_logs (
            id SERIAL PRIMARY KEY,
            date_shamsi TEXT NOT NULL,
            source_counterparty_id INTEGER NOT NULL,
            target_counterparty_id INTEGER NOT NULL,
            voucher_type TEXT NOT NULL,
            voucher_id INTEGER NOT NULL,
            gold_weight_750 DOUBLE PRECISION DEFAULT 0.0,
            irr_amount DOUBLE PRECISION DEFAULT 0.0,
            reason TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seeds for PostgreSQL
        default_craftsmen = [
            ("نیما", "استادکار پوست و پرداخت", "09120000001"),
            ("امیر", "استادکار پوست و پرداخت", "09120000002"),
            ("عطا", "استادکار تراش داخل و مونتاژ", "09120000003"),
        ]
        for name, role, phone in default_craftsmen:
            cursor.execute("""
            INSERT INTO craftsmen (name, role, phone)
            VALUES (?, ?, ?)
            ON CONFLICT (name) DO NOTHING;
            """, (name, role, phone))

        default_parties = [
            ("آقای آزادی", "تامین‌کننده شمش و بنکدار طلا", "09121111111", 0.0, 0.0),
            ("ربیعی", "تامین‌کننده اسید و تجهیزات کارگاه", "09122222222", 0.0, 0.0),
        ]
        # Seed Solder Recipes (فرمول‌های پیش‌فرض لحیم زرگری)
        default_solders = [
            ("لحیم سفت (جوش اولیه و قطعات سنگین)", "hard", 10.0, 750, 4.0, 0.40, 0.30, 0.10, 10.80, 740, "مناسب اتصالات اصلی، حلقه و بازوی انگشتر با دمای ذوب بالا"),
            ("لحیم متوسط (کارهای عمومی کارگاه)", "medium", 10.0, 750, 7.0, 0.70, 0.50, 0.20, 11.40, 730, "مناسب جوشکاری النگو، انگشتر و قطعات ریخته‌گری"),
            ("لحیم شل (کارهای ظریف و گل و نگین)", "soft", 10.0, 750, 11.0, 1.10, 0.80, 0.30, 12.20, 715, "دمای ذوب پایین بدون تغییر شکل قطعه و ریزش جوش قبلی"),
        ]
        for title, stype, bgw, bgc, cdp, cdw, agw, cuw, tsw, fgc, notes in default_solders:
            cursor.execute("""
            INSERT INTO solder_recipes (title, solder_type, base_gold_weight, base_carat, cadmium_percent, cadmium_weight, silver_weight, copper_weight, total_solder_weight, final_carat, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (title) DO NOTHING;
            """, (title, stype, bgw, bgc, cdp, cdw, agw, cuw, tsw, fgc, notes))

        # Seed Bank & POS Accounts for PostgreSQL
        default_accounts = [
            ("حساب جاری بانک ملت مغازه", "bank", "ملت", "IR120120000000123456789012", "", 150000000.0, "بدهکار به ما", "حساب اصلی تسویه شاپرک"),
            ("کارتخوان به پرداخت ملت (POS)", "pos", "ملت", "", "POS-984421", 45000000.0, "بدهکار به ما", "حساب پوز مغازه جهت تطابق تراکنش‌های شاپرک فردا"),
            ("وام طرح نگین بانک صادرات", "loan", "صادرات", "", "", 280000000.0, "بستانکار از ما", "اقساط مانده وام خرید تجهیزات"),
        ]
        for atitle, atype, bname, sheba, pos_id, bal, diag, notes in default_accounts:
            cursor.execute("""
            INSERT INTO bank_and_pos_accounts (account_title, account_type, bank_name, card_or_sheba, pos_terminal_id, balance_irr, diagnosis, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO NOTHING;
            """, (atitle, atype, bname, sheba, pos_id, bal, diag, notes))

    else:
        # SQLite DDL
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS craftsmen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            role TEXT DEFAULT 'سازنده طلا',
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL UNIQUE,
            day_of_week TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            total_loss REAL DEFAULT 0.0,
            total_swarf REAL DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            total_count INTEGER DEFAULT 1,
            total_weight REAL NOT NULL,
            carat INTEGER DEFAULT 750,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(shift_id) REFERENCES daily_shifts(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            batch_id INTEGER,
            craftsman_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            item_name TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            input_weight REAL NOT NULL,
            output_weight REAL NOT NULL,
            loss_weight REAL NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(shift_id) REFERENCES daily_shifts(id) ON DELETE CASCADE,
            FOREIGN KEY(craftsman_id) REFERENCES craftsmen(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            craftsman_id INTEGER,
            title TEXT NOT NULL,
            weight REAL NOT NULL,
            target_bucket TEXT DEFAULT 'سوآله چرم و سوهانکاری',
            weight_after REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(shift_id) REFERENCES daily_shifts(id) ON DELETE CASCADE,
            FOREIGN KEY(craftsman_id) REFERENCES craftsmen(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS melting_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            title TEXT NOT NULL,
            raw_weight REAL NOT NULL,
            raw_carat INTEGER NOT NULL,
            target_carat INTEGER DEFAULT 750,
            pure_gold_750 REAL NOT NULL,
            alloy_bar_needed REAL DEFAULT 0.0,
            melted_weight REAL,
            loss_weight REAL DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS showcase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            gold_weight REAL NOT NULL,
            stone_weight REAL DEFAULT 0.0,
            carat INTEGER DEFAULT 750,
            wage_amount REAL DEFAULT 0.0,
            wage_percent REAL DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            customer_name TEXT DEFAULT 'مشتری حضوری',
            customer_phone TEXT,
            date_shamsi TEXT NOT NULL,
            gold_rate_per_gram REAL NOT NULL,
            total_gold_weight REAL NOT NULL,
            total_wage REAL DEFAULT 0.0,
            profit_percent REAL DEFAULT 7.0,
            tax_percent REAL DEFAULT 0.0,
            discount_amount REAL DEFAULT 0.0,
            total_amount REAL NOT NULL,
            payment_method TEXT DEFAULT 'کارتخوان',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            showcase_item_id INTEGER,
            title TEXT NOT NULL,
            category TEXT,
            weight REAL NOT NULL,
            count INTEGER DEFAULT 1,
            wage_amount REAL DEFAULT 0.0,
            total_price REAL NOT NULL,
            FOREIGN KEY(invoice_id) REFERENCES sales_invoices(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            date_shamsi TEXT NOT NULL,
            title TEXT NOT NULL,
            weight REAL NOT NULL,
            carat INTEGER DEFAULT 750,
            calculated_750_weight REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_credit REAL NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invoice_id) REFERENCES sales_invoices(id) ON DELETE SET NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts_counterparties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            role TEXT DEFAULT 'بنکدار / تامین‌کننده',
            phone TEXT,
            balance_gold_750 REAL DEFAULT 0.0,
            balance_irr REAL DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS counterparty_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            counterparty_id INTEGER NOT NULL,
            date_shamsi TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            gold_weight_in REAL DEFAULT 0.0,
            gold_weight_out REAL DEFAULT 0.0,
            carat INTEGER DEFAULT 750,
            irr_amount_in REAL DEFAULT 0.0,
            irr_amount_out REAL DEFAULT 0.0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(counterparty_id) REFERENCES accounts_counterparties(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            payee TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cashbox_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 15. Craftsmen Settlements / Wage Payroll (تسویه حساب و کارکرد پرسنل)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS craftsmen_settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            craftsman_id INTEGER NOT NULL,
            date_shamsi TEXT NOT NULL,
            period_title TEXT NOT NULL,
            total_worked_grams REAL DEFAULT 0.0,
            wage_rate_irr REAL DEFAULT 0.0,
            total_wage_irr REAL DEFAULT 0.0,
            paid_amount_irr REAL DEFAULT 0.0,
            paid_gold_weight REAL DEFAULT 0.0,
            settlement_status TEXT DEFAULT 'تسویه_شده',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(craftsman_id) REFERENCES craftsmen(id) ON DELETE CASCADE
        );
        """)

        # 16. Crucible Records (دفترچه تخصصی بوته‌های ذوب و شیره)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crucible_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            crucible_code TEXT NOT NULL,
            operator_name TEXT DEFAULT 'مسئول ذوب',
            raw_gold_weight REAL NOT NULL,
            raw_carat INTEGER NOT NULL,
            target_carat INTEGER DEFAULT 750,
            alloy_bar_added REAL DEFAULT 0.0,
            melted_bar_weight REAL NOT NULL,
            sheereh_weight REAL DEFAULT 0.0,
            loss_weight REAL NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 17. Solder Recipes (فرمول‌های ساخت انواع لحیم زرگری)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS solder_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            solder_type TEXT NOT NULL,
            base_gold_weight REAL NOT NULL,
            base_carat INTEGER DEFAULT 750,
            cadmium_percent REAL NOT NULL,
            cadmium_weight REAL NOT NULL,
            silver_weight REAL DEFAULT 0.0,
            copper_weight REAL DEFAULT 0.0,
            total_solder_weight REAL NOT NULL,
            final_carat INTEGER NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 18. Refining Batches (محموله‌های ارسالی به قالکاری و تیزاب‌کاری)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS refining_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            batch_code TEXT NOT NULL UNIQUE,
            refiner_name TEXT NOT NULL,
            material_type TEXT DEFAULT 'سوآله چرم و سوهان',
            sent_weight REAL NOT NULL,
            recovered_gold_750 REAL DEFAULT 0.0,
            refining_fee_irr REAL DEFAULT 0.0,
            status TEXT DEFAULT 'در_حال_تیزاب',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 19. Assay Records (مدیریت آبشده‌های شرطی، ری‌گیری و تطبیق کسری/مازاد عیار)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assay_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            bar_code TEXT NOT NULL,
            lab_name TEXT NOT NULL,
            receipt_no TEXT,
            phone TEXT,
            raw_scale_weight REAL NOT NULL,
            provisional_carat INTEGER DEFAULT 750,
            final_carat INTEGER,
            equiv_750_initial REAL NOT NULL,
            equiv_750_final REAL,
            variance_750 REAL DEFAULT 0.0,
            counterparty_id INTEGER,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(counterparty_id) REFERENCES accounts_counterparties(id) ON DELETE SET NULL
        );
        """)

        # 20. Bank & POS Accounts (تفکیک حساب‌های بانکی، دستگاه‌های پوز شاپرک و وام‌ها)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_and_pos_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_title TEXT NOT NULL,
            account_type TEXT NOT NULL,
            bank_name TEXT NOT NULL,
            card_or_sheba TEXT,
            pos_terminal_id TEXT,
            balance_irr REAL DEFAULT 0.0,
            diagnosis TEXT DEFAULT 'بدهکار به ما',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 21. Gold / Cash Conversions (دفتر ثبت رسمی پولی‌کردن و طلایی‌کردن با مظنه روز)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_cash_conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            conversion_type TEXT NOT NULL,
            counterparty_id INTEGER,
            mazane_rate REAL NOT NULL,
            gram_price_750 REAL NOT NULL,
            gold_weight_750 REAL NOT NULL,
            toman_amount REAL NOT NULL,
            voucher_code TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(counterparty_id) REFERENCES accounts_counterparties(id) ON DELETE SET NULL
        );
        """)

        # 22. Checks Portfolio (سبد چک‌های صیادی اشخاص و چک‌های شخصی صادره)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS checks_portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_direction TEXT NOT NULL,
            sayad_id TEXT,
            serial_no TEXT,
            bank_name TEXT NOT NULL,
            branch_name TEXT,
            drawer_name TEXT NOT NULL,
            payee_name TEXT,
            counterparty_id INTEGER,
            amount_irr REAL NOT NULL,
            due_date_shamsi TEXT NOT NULL,
            status TEXT DEFAULT 'نزد_صندوق',
            deposit_bank_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(counterparty_id) REFERENCES accounts_counterparties(id) ON DELETE SET NULL
        );
        """)

        # 23. Scissor Audit Logs (دفتر ثبت قیچی و انتقال فاکتور بین اشخاص)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scissor_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_shamsi TEXT NOT NULL,
            source_counterparty_id INTEGER NOT NULL,
            target_counterparty_id INTEGER NOT NULL,
            voucher_type TEXT NOT NULL,
            voucher_id INTEGER NOT NULL,
            gold_weight_750 REAL DEFAULT 0.0,
            irr_amount REAL DEFAULT 0.0,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seeds for SQLite
        default_craftsmen = [
            ("نیما", "استادکار پوست و پرداخت", "09120000001"),
            ("امیر", "استادکار پوست و پرداخت", "09120000002"),
            ("عطا", "استادکار تراش داخل و مونتاژ", "09120000003"),
        ]
        for name, role, phone in default_craftsmen:
            cursor.execute("""
            INSERT OR IGNORE INTO craftsmen (name, role, phone)
            VALUES (?, ?, ?);
            """, (name, role, phone))

        default_parties = [
            ("آقای آزادی", "تامین‌کننده شمش و بنکدار طلا", "09121111111", 0.0, 0.0),
            ("ربیعی", "تامین‌کننده اسید و تجهیزات کارگاه", "09122222222", 0.0, 0.0),
        ]
        for name, role, phone, b_gold, b_irr in default_parties:
            cursor.execute("""
            INSERT OR IGNORE INTO accounts_counterparties (name, role, phone, balance_gold_750, balance_irr)
            VALUES (?, ?, ?, ?, ?);
            """, (name, role, phone, b_gold, b_irr))

        # Seed Solder Recipes for SQLite
        default_solders = [
            ("لحیم سفت (جوش اولیه و قطعات سنگین)", "hard", 10.0, 750, 4.0, 0.40, 0.30, 0.10, 10.80, 740, "مناسب اتصالات اصلی، حلقه و بازوی انگشتر با دمای ذوب بالا"),
            ("لحیم متوسط (کارهای عمومی کارگاه)", "medium", 10.0, 750, 7.0, 0.70, 0.50, 0.20, 11.40, 730, "مناسب جوشکاری النگو، انگشتر و قطعات ریخته‌گری"),
            ("لحیم شل (کارهای ظریف و گل و نگین)", "soft", 10.0, 750, 11.0, 1.10, 0.80, 0.30, 12.20, 715, "دمای ذوب پایین بدون تغییر شکل قطعه و ریزش جوش قبلی"),
        ]
        for title, stype, bgw, bgc, cdp, cdw, agw, cuw, tsw, fgc, notes in default_solders:
            cursor.execute("""
            INSERT OR IGNORE INTO solder_recipes (title, solder_type, base_gold_weight, base_carat, cadmium_percent, cadmium_weight, silver_weight, copper_weight, total_solder_weight, final_carat, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (title, stype, bgw, bgc, cdp, cdw, agw, cuw, tsw, fgc, notes))

        # Seed Bank & POS Accounts for SQLite
        default_accounts = [
            ("حساب جاری بانک ملت مغازه", "bank", "ملت", "IR120120000000123456789012", "", 150000000.0, "بدهکار به ما", "حساب اصلی تسویه شاپرک"),
            ("کارتخوان به پرداخت ملت (POS)", "pos", "ملت", "", "POS-984421", 45000000.0, "بدهکار به ما", "حساب پوز مغازه جهت تطابق تراکنش‌های شاپرک فردا"),
            ("وام طرح نگین بانک صادرات", "loan", "صادرات", "", "", 280000000.0, "بستانکار از ما", "اقساط مانده وام خرید تجهیزات"),
        ]
        for atitle, atype, bname, sheba, pos_id, bal, diag, notes in default_accounts:
            cursor.execute("""
            INSERT OR IGNORE INTO bank_and_pos_accounts (account_title, account_type, bank_name, card_or_sheba, pos_terminal_id, balance_irr, diagnosis, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (atitle, atype, bname, sheba, pos_id, bal, diag, notes))

    conn.commit()
    conn.close()


def create_backup() -> str:
    """Creates a backup snapshot of the local database or logs status for cloud DB."""
    if is_postgres():
        return "Cloud Database: Automated point-in-time recovery and snapshots are active via Supabase."
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"dilan_gold_backup_{timestamp}.db")
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, backup_file)
    return backup_file
