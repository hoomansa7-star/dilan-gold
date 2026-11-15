-- ====================================================================
-- Dilan Gold ERP - Supabase PostgreSQL Database Schema
-- سامانه مدیریت کارگاه و گالری طلای دیلان - اسکریپت ساخت دیتابیس سوپابیس
-- ====================================================================

-- 1. جدول استادکاران و پرسنل کارگاه (نیما، امیر، عطا و...)
CREATE TABLE IF NOT EXISTS craftsmen (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    role TEXT DEFAULT 'سازنده طلا',
    phone TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. جدول شیفت‌های روزانه کارگاه
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

-- 3. جدول پارت‌ها و اقلام تحویلی به کارگاه (بچ‌های تولید)
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

-- 4. جدول مراحل کاری، ثبت وزن ورود/خروج و محاسبه کسری کارگاه
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

-- 5. جدول رویدادها و افت به سوآله کارگاه
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

-- 6. جدول رکوردهای ذوب و تبدیل شمش و کسر بار
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

-- 7. جدول موجودی ویترین مغازه
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

-- 8. جدول فاکتورهای فروش
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

-- 9. جدول اقلام فاکتور فروش
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

-- 10. جدول تعویض طلا / طلای کهنه در فاکتور
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

-- 11. جدول طرف‌حساب‌ها (بنکداران، تامین‌کنندگان، آقای آزادی و...)
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

-- 12. جدول گردش معاملات طرف‌حساب‌ها
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

-- 13. جدول مخارج کارگاه
CREATE TABLE IF NOT EXISTS workshop_expenses (
    id SERIAL PRIMARY KEY,
    date_shamsi TEXT NOT NULL,
    category TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    payee TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 14. جدول صندوق ریالی
CREATE TABLE IF NOT EXISTS cashbox_logs (
    id SERIAL PRIMARY KEY,
    date_shamsi TEXT NOT NULL,
    tx_type TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    category TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ایندکس‌ها برای بهینه‌سازی سرعت کوئری‌ها
CREATE INDEX IF NOT EXISTS idx_shifts_date ON daily_shifts(date_shamsi);
CREATE INDEX IF NOT EXISTS idx_tasks_shift ON workshop_tasks(shift_id);
CREATE INDEX IF NOT EXISTS idx_batches_shift ON workshop_batches(shift_id);
CREATE INDEX IF NOT EXISTS idx_showcase_code ON showcase_items(code);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON sales_invoices(date_shamsi);

-- ثبت استادکاران اولیه کارگاه
INSERT INTO craftsmen (name, role, phone)
VALUES 
    ('نیما', 'استادکار پوست و پرداخت', '09120000001'),
    ('امیر', 'استادکار پوست و پرداخت', '09120000002'),
    ('عطا', 'استادکار تراش داخل و مونتاژ', '09120000003')
ON CONFLICT (name) DO NOTHING;

-- ثبت طرف‌حساب‌های اولیه کارگاه
INSERT INTO accounts_counterparties (name, role, phone, balance_gold_750, balance_irr)
VALUES 
    ('آقای آزادی', 'تامین‌کننده شمش و بنکدار طلا', '09121111111', 0.0, 0.0),
    ('ربیعی', 'تامین‌کننده اسید و تجهیزات کارگاه', '09122222222', 0.0, 0.0)
ON CONFLICT (name) DO NOTHING;
