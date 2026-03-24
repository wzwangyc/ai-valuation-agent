"""
Sensitivity Analysis — Bonus requirement.
Generates WACC vs Terminal Growth Rate matrix showing fair-price sensitivity.
Demonstrates how valuation changes when key assumptions shift by ±1%.
"""
import pandas as pd
from typing import Dict


class SensitivityAnalysis:
    """WACC × Terminal-Growth sensitivity matrix — investment-bank format."""

    def __init__(self, dcf_result: Dict):
        self.result = dcf_result
        self.base_wacc = dcf_result["wacc_details"]["wacc"]
        self.base_tg = dcf_result["terminal_value_details"]["terminal_growth"]

    def generate_matrix(self, step_bp: int = 100) -> Dict:
        """
        Build sensitivity table: fair price at various (WACC, g) combinations.
        step_bp: step size in basis points (100bp = 1%).
        """
        step = step_bp / 10000
        wacc_range = [self.base_wacc + i * step for i in range(-2, 3)]
        tg_range = [self.base_tg + i * step for i in range(-2, 3)]
        # Clamp to reasonable bounds
        wacc_range = [max(w, 0.03) for w in wacc_range]
        tg_range = [max(t, 0.005) for t in tg_range]

        forecast = self.result["forecast_table"]
        ufcf_values = list(forecast["UFCF"].values())
        last_ufcf = ufcf_values[-1]
        n = self.result["key_assumptions"]["forecast_years"]
        net_debt = self.result["net_debt"]
        shares = self.result["shares_outstanding"]

        matrix = {}
        for wacc in wacc_range:
            row_label = f"{wacc * 100:.1f}%"
            row = {}
            disc = [1 / (1 + wacc) ** (i + 0.5) for i in range(n)]
            pv_ufcf = sum(u * d for u, d in zip(ufcf_values, disc))
            for tg in tg_range:
                col_label = f"{tg * 100:.1f}%"
                if tg >= wacc:
                    row[col_label] = "N/A"
                    continue
                tv = last_ufcf * (1 + tg) / (wacc - tg)
                pv_tv = tv / (1 + wacc) ** n
                ev = pv_ufcf + pv_tv
                fair = (ev - net_debt) / shares if shares > 0 else 0
                row[col_label] = round(fair, 2)
            matrix[row_label] = row

        df = pd.DataFrame(matrix).T
        df.index.name = "WACC \\ Terminal Growth"
        return {
            "sensitivity_matrix": df.to_dict(),
            "base_wacc": f"{self.base_wacc * 100:.2f}%",
            "base_terminal_growth": f"{self.base_tg * 100:.2f}%",
            "base_fair_price": self.result["fair_price_per_share"],
            "step_basis_points": step_bp,
            "note": (
                "Matrix shows fair price per share at different WACC and "
                "terminal growth rate combinations. "
                "Base case is highlighted by the center cell."
            ),
        }
