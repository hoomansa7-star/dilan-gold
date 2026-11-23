# -*- coding: utf-8 -*-
"""
Unit tests for Phase 3: Market Operations, Assay Management, Cashify/Goldify,
Ras-giri, Bank/POS accounts, and Scissor transfer tools.
Direct route function invocation (zero-dependency, robust testing).
"""

import unittest
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Force local SQLite for lightning-fast, zero-network unit tests
os.environ["DATABASE_URL"] = ""

from server.database import init_db
from server.routes.market_ops import (
    create_assay_record, reconcile_assay, AssayCreate, AssayReconcile,
    execute_cashify, CashifyRequest,
    execute_goldify, GoldifyRequest,
    calculate_rasgiri, RasGiriRequest, RasGiriItem,
    create_bank_pos_account, BankPosAccountCreate, list_bank_pos_accounts,
    create_check, CheckCreate, update_check_status,
    execute_scissor_transfer, ScissorTransferRequest
)
from server.routes.accounts import add_party_transaction, CounterpartyTransactionCreate


class TestPhase3MarketOps(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_assay_workflow(self):
        """تست چرخه کامل آبشده شرطی: ثبت اولیه و تطبیق نتیجه آزمایشگاه ری‌گیری"""
        req1 = AssayCreate(
            date_shamsi="1403/08/23",
            bar_code="ش-9912",
            lab_name="ری‌گیری کاسپین",
            receipt_no="11045",
            phone="02155601122",
            raw_scale_weight=80.0,
            provisional_carat=750,
            counterparty_id=1,
            notes="آبشده ارسالی به آزمایشگاه کاسپین"
        )
        res1 = create_assay_record(req1)
        assay_id = res1["id"]
        self.assertEqual(res1["equiv_750_initial"], 80.0)

        # ۲. ورود جواب آزمایشگاه ری‌گیری: عیار قطعی ۷۴۰ (کسری عیار ۱۰ خطی)
        req2 = AssayReconcile(
            final_carat=740,
            notes="جواب رسمی ری‌گیری: عیار ۷۴۰"
        )
        res2 = reconcile_assay(assay_id, req2)
        self.assertEqual(res2["status"], "confirmed")
        # 80 * 740 / 750 = 78.933 -> variance = 78.933 - 80.0 = -1.067
        self.assertEqual(res2["equiv_750_final"], 78.933)
        self.assertEqual(res2["variance_750"], -1.067)

    def test_02_cashify_formula(self):
        """تست پولی کردن طلا با فرمول مظنه بازار تهران (مظنه ÷ ۴.۳۳۱۸۰۲)"""
        mazane = 18_500_000.0
        weight = 10.0

        req = CashifyRequest(
            date_shamsi="1403/08/23",
            counterparty_id=1,
            gold_weight_750=weight,
            mazane_rate=mazane,
            notes="تسویه ریالی ۱۰ گرم طلای بدهی"
        )
        res = execute_cashify(req)
        expected_gram = round(mazane / 4.331802, 0)
        expected_toman = round(weight * expected_gram, 0)
        self.assertEqual(res["gram_price_750"], expected_gram)
        self.assertEqual(res["toman_amount"], expected_toman)

    def test_03_goldify_formula(self):
        """تست طلایی کردن اجرت یا بدهی تومانی بر مبنای مظنه روز"""
        mazane = 18_500_000.0
        toman = 42_707_400.0

        req = GoldifyRequest(
            date_shamsi="1403/08/23",
            counterparty_id=1,
            toman_amount=toman,
            mazane_rate=mazane,
            notes="طلایی کردن اجرت ساخت فاکتور"
        )
        res = execute_goldify(req)
        gram_price = mazane / 4.331802
        expected_gold = round(toman / gram_price, 3)
        self.assertEqual(res["gold_weight_750"], expected_gold)

    def test_04_rasgiri_weighted_average(self):
        """تست رأس‌گیری وزنی طلا و مبالغ فاکتورها"""
        req = RasGiriRequest(
            base_date_shamsi="1403/08/01",
            items=[
                RasGiriItem(title="فاکتور ۱", amount=100.0, days_or_date=10),
                RasGiriItem(title="فاکتور ۲", amount=200.0, days_or_date=25),
                RasGiriItem(title="فاکتور ۳", amount=100.0, days_or_date=40)
            ]
        )
        res = calculate_rasgiri(req)
        # Sum amount = 400
        # Weighted = (100*10) + (200*25) + (100*40) = 1000 + 5000 + 4000 = 10000
        # Average = 10000 / 400 = 25.0
        self.assertEqual(res["weighted_average_days"], 25.0)

    def test_05_bank_and_pos_accounts(self):
        """تست تفکیک حساب پوز شاپرک از حساب بانکی و وام"""
        req = BankPosAccountCreate(
            account_title="کارتخوان پاسارگاد",
            account_type="pos",
            bank_name="پاسارگاد",
            pos_terminal_id="POS-554411",
            balance_irr=25000000.0,
            diagnosis="بدهکار به ما",
            notes="پوز پیشخوان طلافروشی"
        )
        res = create_bank_pos_account(req)
        self.assertEqual(res["status"], "created")

        accounts = list_bank_pos_accounts()
        self.assertTrue(any(a["account_title"] == "کارتخوان پاسارگاد" for a in accounts))

    def test_06_checks_portfolio(self):
        """تست سبد چک‌های صیادی و تغییر وضعیت به خوابانده به حساب"""
        req = CheckCreate(
            check_direction="received",
            sayad_id="1234567890123456",
            serial_no="A-89912",
            bank_name="ملت",
            drawer_name="حسین رضایی",
            payee_name="گالری طلا دیلان",
            amount_irr=65000000.0,
            due_date_shamsi="1403/09/15",
            status="نزد_صندوق",
            notes="بابت خرید النگو"
        )
        res1 = create_check(req)
        chk_id = res1["id"]

        # تغییر وضعیت به خوابانده به حساب
        res2 = update_check_status(chk_id, "خوابانده_به_حساب", deposit_bank_id=1)
        self.assertEqual(res2["status"], "updated")
        self.assertEqual(res2["new_status"], "خوابانده_به_حساب")

    def test_07_scissor_transfer(self):
        """تست ابزار قیچی سند و انتقال تراکنش بین دو طرف‌حساب"""
        tx = add_party_transaction(CounterpartyTransactionCreate(
            counterparty_id=1,
            date_shamsi="1403/08/23",
            tx_type="ورود شمش",
            gold_weight_in=15.0,
            gold_weight_out=0.0,
            carat=750,
            irr_amount_in=0.0,
            irr_amount_out=0.0,
            description="سند اشتباهی جهت انتقال با قیچی"
        ))
        tx_id = tx["id"]

        sc_req = ScissorTransferRequest(
            date_shamsi="1403/08/23",
            transaction_id=tx_id,
            source_counterparty_id=1,
            target_counterparty_id=2,
            reason="ثبت اشتباهی در حساب آقای آزادی به جای ربیعی"
        )
        res = execute_scissor_transfer(sc_req)
        self.assertEqual(res["status"], "transferred")
        self.assertEqual(res["gold_weight_750"], 15.0)


if __name__ == "__main__":
    unittest.main()
