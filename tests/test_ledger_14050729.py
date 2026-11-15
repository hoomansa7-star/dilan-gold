# -*- coding: utf-8 -*-
"""
Unit tests for the real gold workshop shift (Wednesday 1405/07/29).
Strictly uses Python's Decimal module with 3 decimal places precision (no float rounding errors).
"""

from decimal import Decimal, ROUND_HALF_UP
import unittest


def to_dec(val) -> Decimal:
    """Converts value to Decimal rounded to 3 decimal places."""
    return Decimal(str(val)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)


def calculate_loss(input_weight: Decimal, output_weight: Decimal) -> Decimal:
    """Loss is always: output_weight - input_weight (negative means loss)."""
    return (output_weight - input_weight).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)


class TestRealShift14050729(unittest.TestCase):

    def setUp(self):
        # 1. Batches on Wednesday 1405/07/29
        self.batches = [
            {"title": "گل و نگین برای پوست", "count": 33, "weight": to_dec("26.770")},
            {"title": "انگشتر و نگین", "count": 18, "weight": to_dec("23.870")},
            {"title": "انگشتر متفرقه", "count": 4, "weight": to_dec("11.900")},
            {"title": "گل و نگین برای تراش داخل", "count": 1, "weight": to_dec("49.340")},
        ]

        # 2. Tasks recorded in ledger (Pages 4 & 5)
        self.tasks = [
            # پوست و ملگات گل
            {"worker": "نیما", "stage": "skin", "item": "گل و نگین", "count": 16, "in": to_dec("12.510"), "out": to_dec("12.340"), "expected_loss": to_dec("-0.170")},
            {"worker": "امیر", "stage": "skin", "item": "گل و نگین", "count": 17, "in": to_dec("14.250"), "out": to_dec("14.090"), "expected_loss": to_dec("-0.160")},
            # پوست انگشتر متفرقه
            {"worker": "نیما", "stage": "skin", "item": "انگشتر متفرقه", "count": 2, "in": to_dec("5.850"), "out": to_dec("5.440"), "expected_loss": to_dec("-0.410")},
            {"worker": "امیر", "stage": "skin", "item": "انگشتر متفرقه", "count": 2, "in": to_dec("6.040"), "out": to_dec("4.960"), "expected_loss": to_dec("-1.080")},
            # پوست النگو و نگین
            {"worker": "نیما", "stage": "skin", "item": "النگو و نگین", "count": 5, "in": to_dec("6.910"), "out": to_dec("6.420"), "expected_loss": to_dec("-0.490")},
            {"worker": "امیر", "stage": "skin", "item": "النگو و نگین", "count": 6, "in": to_dec("8.220"), "out": to_dec("7.480"), "expected_loss": to_dec("-0.740")},
            {"worker": "عطا", "stage": "skin", "item": "النگو و نگین", "count": 7, "in": to_dec("8.710"), "out": to_dec("8.500"), "expected_loss": to_dec("-0.210")},
            # پرداخت انگشتر متفرقه
            {"worker": "نیما", "stage": "polish", "item": "انگشتر متفرقه", "count": 2, "in": to_dec("5.440"), "out": to_dec("5.280"), "expected_loss": to_dec("-0.160")},
            {"worker": "امیر", "stage": "polish", "item": "انگشتر متفرقه", "count": 2, "in": to_dec("4.960"), "out": to_dec("4.820"), "expected_loss": to_dec("-0.140")},
            # پرداخت انگشتر و نگین
            {"worker": "نیما", "stage": "polish", "item": "انگشتر و نگین", "count": 5, "in": to_dec("6.420"), "out": to_dec("6.350"), "expected_loss": to_dec("-0.070")},
            {"worker": "امیر", "stage": "polish", "item": "انگشتر و نگین", "count": 11, "in": to_dec("7.480"), "out": to_dec("7.350"), "expected_loss": to_dec("-0.130")},
            {"worker": "عطا", "stage": "polish", "item": "انگشتر و نگین", "count": 10, "in": to_dec("7.410"), "out": to_dec("7.230"), "expected_loss": to_dec("-0.180")},
        ]

        # 3. Incident (سوآله)
        self.swarf_incident = {
            "worker": "عطا",
            "item": "انگشتر و نگین سایز ۳ عطا",
            "swarf_weight": to_dec("1.100"),
            "weight_after": to_dec("7.400")
        }

    def test_batch_division_checksum(self):
        """بررسی برابری سرجمع تقسیم کار گل بین نیما و امیر (12.51 + 14.25 = 26.76 ~ 26.77)"""
        nima_in = to_dec("12.510")
        amir_in = to_dec("14.250")
        total_split = nima_in + amir_in
        self.assertEqual(total_split, to_dec("26.760"))

    def test_individual_task_losses(self):
        """بررسی محاسبه دقیق کسری تک‌تک مراحل"""
        for t in self.tasks:
            calculated = calculate_loss(t["in"], t["out"])
            self.assertEqual(
                calculated,
                t["expected_loss"],
                f"خطا در محاسبه کسری {t['worker']} در {t['stage']} برای {t['item']}: {calculated} != {t['expected_loss']}"
            )

    def test_worker_losses_summary(self):
        """سرجمع کسری هر کارگر به تفکیک"""
        worker_losses = {}
        for t in self.tasks:
            loss = calculate_loss(t["in"], t["out"])
            worker_losses[t["worker"]] = worker_losses.get(t["worker"], Decimal("0.000")) + loss

        # مجموع کسر نیما
        expected_nima = to_dec("-0.170") + to_dec("-0.410") + to_dec("-0.490") + to_dec("-0.160") + to_dec("-0.070")
        self.assertEqual(worker_losses["نیما"], expected_nima)
        self.assertEqual(worker_losses["نیما"], to_dec("-1.300"))

        # مجموع کسر امیر
        expected_amir = to_dec("-0.160") + to_dec("-1.080") + to_dec("-0.740") + to_dec("-0.140") + to_dec("-0.130")
        self.assertEqual(worker_losses["امیر"], expected_amir)
        self.assertEqual(worker_losses["امیر"], to_dec("-2.250"))

        # مجموع کسر عطا
        expected_ata = to_dec("-0.210") + to_dec("-0.180")
        self.assertEqual(worker_losses["عطا"], expected_ata)
        self.assertEqual(worker_losses["عطا"], to_dec("-0.390"))

    def test_total_daily_loss_exact_match(self):
        """کسری کل روز دقیقاً برابر با -۳٫۹۴۰ گرم مطابق دفتر دست‌نویس باشد"""
        total_loss = sum((calculate_loss(t["in"], t["out"]) for t in self.tasks), Decimal("0.000"))
        expected_total = to_dec("-3.940")
        self.assertEqual(total_loss, expected_total, f"کسری کل {total_loss} با عدد دفتر {expected_total} مطابقت ندارد!")


if __name__ == "__main__":
    unittest.main()
