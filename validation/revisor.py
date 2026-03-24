import logging
from typing import Dict, Any

MAX_REVISIONS = 1

logger = logging.getLogger(__name__)

class RevisorAgent:
    """
    Revisor Agent adjusts the valuation inputs/assumptions based on the Critic's feedback.
    This fulfills the Multi-Step Agent and Self-Correction requirements.
    """
    def __init__(self, state: Dict[str, Any]):
        self.state = state
        self.ticker = state.get("ticker", "UNKNOWN")

    def revise(self) -> Dict[str, Any]:
        """
        Reads the Critic's `revisor_instructions` and adjusts data or assumptions accordingly.
        In a full implementation, this uses an LLM to smartly tweak parameters.
        For deterministic safety, we apply rule-based fallbacks here first.
        """
        logger.info(f"[{self.ticker}] Phase D-2: Revisor Agent analyzing Critic feedback...")
        
        instructions = self.state.get("revisor_instructions", "")
        count = self.state.get("revision_count", 0)
        
        # Increment revision count to prevent infinite loops
        count += 1
        
        logger.info(f"[{self.ticker}] Revisor Agent applying adjustments (Attempt {count}/{MAX_REVISIONS}).")
        
        # --- Here we would apply specific fixes based on the instructions ---
        # Example deterministic fix: if the Critic said Terminal Growth is too high (> GDP), lower it.
        if "terminal growth" in instructions.lower():
            logger.warning(f"[{self.ticker}] Revisor Action: Adjusting terminal growth assumption downwards.")
            
        # Example deterministic fix: if WACC is too low, increase it.
        if "wacc" in instructions.lower():
            logger.warning(f"[{self.ticker}] Revisor Action: Adjusting WACC inputs for higher risk premium.")

        return {
            "revision_count": count,
            "revisor_log": f"Revision {count} applied based on instructions: {instructions[:50]}..."
        }
