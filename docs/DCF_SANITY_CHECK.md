# DCF Sanity Check

This note records a lightweight post-fix validation pass for the deterministic DCF engine.

## Scope

- Date: 2026-03-24
- Goal: confirm that the DCF pipeline runs after the working-capital/UFCF cleanup and that
  the resulting output remains directionally plausible for large-cap reference names.
- Reference names: `AAPL`, `MSFT`

## Validation Method

1. Run Phase A data collection.
2. Run deterministic Phase B valuation without relying on LLM arithmetic.
3. Inspect:
   - WACC
   - terminal growth rate
   - Year 1 UFCF
   - fair value per share
   - current market price
   - analyst target mean price from market data

The analyst target mean is not treated as ground truth. It is used only as an external market-consensus anchor to check that the model is not producing obviously broken output after the UFCF fix.

## Results

| Ticker | Fair Value / Share | Current Price | Analyst Target Mean | WACC | Terminal Growth | Year 1 UFCF | TV % of EV | Peer Count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | 190.67 | 251.49 | 295.44 | 10.4396% | 3.50% | 95.48B | 82.7% | 0 |
| MSFT | 271.03 | 383.00 | 594.62 | 10.4242% | 3.50% | 53.62B | 84.5% | 5 |

## Interpretation

- The DCF engine runs end-to-end after the operating working-capital cleanup.
- UFCF is computed using the standard formula:
  `UFCF = EBIT * (1 - tax rate) + D&A - CapEx - Delta NWC`
- Delta NWC is treated as a cash outflow when operating working capital increases.
- The outputs are internally coherent, but still conservative versus current market price and analyst target means for both names.
- Terminal value concentration remains high. That is already flagged by validation and should remain a tracked model risk.
- Comparable-company coverage is still not stable enough to be treated as a strong cross-check for every ticker. `MSFT` produced five peers in this run; `AAPL` produced none in this run.

## Current Limitations

- This note is a sanity check, not a claim of institutional benchmark parity.
- Peer collection remains rate-limit sensitive and can weaken the comparable-multiples cross-check.
- The DCF model remains sensitive to terminal-value assumptions, as shown by the high TV share of EV.

## Next Actions

- Continue reducing peer-data fragility so DCF and comps can be compared more consistently.
- Strengthen WACC documentation and parameter provenance further.
- Expand automated tests around valuation outputs and validation rules.
