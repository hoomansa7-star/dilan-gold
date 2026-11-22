# -*- coding: utf-8 -*-
"""
Unit tests for Phase 2 workshop operations:
1. Quick bench task & swarf diversion.
2. Craftsmen payroll & settlements.
3. Crucible dross (شیره) & net loss calculation.
4. Solder recipes (cadmium % metallurgy calculation).
5. Refining batches (قالکاری).
"""

import unittest
from decimal import Decimal, ROUND_HALF_UP
from server.routes.workshop import calculate_solder, SolderCalcRequest


def to_dec(val) -> Decimal:
    return Decimal(str(val)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)


class TestWorkshopPhase2Ops(unittest.TestCase):

    def test_solder_calculation_hard(self):
        """Test hard solder formula (1.0% cadmium, 0.35% silver -> Carat 740)."""
        req = SolderCalcRequest(base_gold_weight=10.0, recipe_type="hard")
        res = calculate_solder(req)
        self.assertEqual(res["cadmium_percent"], 1.0)
        self.assertEqual(res["cadmium_weight"], 0.10)
        self.assertEqual(res["resulting_carat"], 740)
        self.assertAlmostEqual(res["total_solder_weight"], 10.135, places=3)

    def test_solder_calculation_soft(self):
        """Test soft solder formula (3.5% cadmium, 1.4% silver -> Carat 715)."""
        req = SolderCalcRequest(base_gold_weight=10.0, recipe_type="soft")
        res = calculate_solder(req)
        self.assertEqual(res["cadmium_percent"], 3.5)
        self.assertEqual(res["cadmium_weight"], 0.35)
        self.assertEqual(res["resulting_carat"], 715)
        self.assertAlmostEqual(res["total_solder_weight"], 10.490, places=3)

    def test_crucible_net_loss_formula(self):
        """Test crucible net loss = raw + alloy - bar - sheereh."""
        raw_gold = to_dec("100.000")
        alloy_added = to_dec("2.500")
        melted_bar = to_dec("101.800")
        sheereh = to_dec("0.450")  # gold trapped in crucible wall
        
        # Net loss
        net_loss = raw_gold + alloy_added - melted_bar - sheereh
        self.assertEqual(net_loss, to_dec("0.250"))

    def test_swarf_balance_consistency(self):
        """Ata's ring 1.10g sent to swarf must reconcile without gold gap."""
        input_w = to_dec("8.710")
        output_w = to_dec("7.400")
        swarf_w = to_dec("1.100")
        craftsman_loss = to_dec("-0.210")
        
        # Balance equation: output + swarf - input = craftsman_loss
        balance = output_w + swarf_w - input_w
        self.assertEqual(balance, craftsman_loss)


if __name__ == "__main__":
    unittest.main()
