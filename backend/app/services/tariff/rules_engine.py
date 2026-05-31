"""Rules engine for tariff policy matching."""
import re
from typing import Optional
from app.services.tariff.constants import (
    CN_ZERO_TARIFF_COUNTRIES,
    EU_EPA_COUNTRIES,
)


class TariffRuleResult:
    def __init__(
        self,
        tariff_rate: float,
        origin_qualified: bool,
        rule_name: str,
        message: str,
        savings_vs_mfn: float | None = None,
    ):
        self.tariff_rate = tariff_rate
        self.origin_qualified = origin_qualified
        self.rule_name = rule_name
        self.message = message
        self.savings_vs_mfn = savings_vs_mfn


class TariffRulesEngine:
    """
    Matches HS code + origin + destination against policy rules.
    Returns the applicable tariff rate and qualification status.
    """

    def evaluate(
        self,
        hs_code: str,
        origin_country: str,
        destination: str,
        mfn_rate: float = 0.0,
    ) -> TariffRuleResult:
        """
        Evaluate which tariff rule applies for a given trade flow.
        
        Args:
            hs_code: Normalized HS code (digits only)
            origin_country: ISO 2-letter country code
            destination: CN (China), EU, or AFCFTA
            mfn_rate: MFN tariff rate for comparison (0-1 scale)
        """
        origin = origin_country.upper().strip()

        if destination == "CN":
            return self._evaluate_china(origin, mfn_rate)
        elif destination == "EU":
            return self._evaluate_eu(origin, mfn_rate)
        elif destination == "AFCFTA":
            return self._evaluate_afcfta(origin, mfn_rate)
        else:
            return TariffRuleResult(
                tariff_rate=mfn_rate,
                origin_qualified=False,
                rule_name="MFN税率",
                message=f"未知目的地市场: {destination}",
            )

    def _evaluate_china(self, origin: str, mfn_rate: float) -> TariffRuleResult:
        """Evaluate China zero-tariff policy."""
        if origin in CN_ZERO_TARIFF_COUNTRIES:
            savings = mfn_rate  # proportion of FOB saved
            return TariffRuleResult(
                tariff_rate=0.0,
                origin_qualified=True,
                rule_name="中国对非洲53个建交国零关税政策（2026年5月1日起）",
                message="符合零关税条件",
                savings_vs_mfn=savings,
            )
        return TariffRuleResult(
            tariff_rate=mfn_rate,
            origin_qualified=False,
            rule_name="MFN税率",
            message=f"{origin} 不在中国零关税白名单内（仅建交国适用）",
        )

    def _evaluate_eu(self, origin: str, mfn_rate: float) -> TariffRuleResult:
        """Evaluate EU-EPA policy."""
        if origin in EU_EPA_COUNTRIES:
            return TariffRuleResult(
                tariff_rate=0.0,
                origin_qualified=True,
                rule_name="EU-EPA零关税（增值≥40%估算）",
                message="可能符合EPA零关税条件（需验证增值比例≥40%）",
                savings_vs_mfn=mfn_rate,
            )
        return TariffRuleResult(
            tariff_rate=mfn_rate,
            origin_qualified=False,
            rule_name="MFN税率",
            message=f"{origin} 未与欧盟签署EPA协议",
        )

    def _evaluate_afcfta(self, origin: str, mfn_rate: float) -> TariffRuleResult:
        """Evaluate AfCFTA regional policy."""
        return TariffRuleResult(
            tariff_rate=0.0,
            origin_qualified=True,
            rule_name="AfCFTA区内优惠税率（增值≥40%）",
            message="可能符合AfCFTA优惠条件",
            savings_vs_mfn=mfn_rate,
        )

    def match_hs_pattern(self, hs_code: str, patterns: list[str]) -> bool:
        """Check if HS code matches any of the given patterns."""
        normalized = hs_code.replace(".", "").replace("-", "").replace(" ", "")
        for pattern in patterns:
            pat_normalized = pattern.replace(".", "").replace("*", "")
            if normalized.startswith(pat_normalized):
                return True
            if "*" in pattern:
                regex = pattern.replace(".", r"\.").replace("*", ".*")
                if re.match(f"^{regex}", normalized):
                    return True
        return False


# Singleton instance
rules_engine = TariffRulesEngine()
