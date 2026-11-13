# NQ intraday regime lab

Paper research only. Nothing here places orders.

- `lab.py`: regime labelling (daily 200 EMA + slope, ADX14 < 20 = flat, 3-day hold), 9 strategy families, per-bar log-return backtest with costs (1 tick + commission per side), bar permutation, walk-forward, plateau selection.
- `tonight.py`: runs all 4 gates (IS PF > 1 with plateau ρ ≥ 0.5, IS permutation p < 0.01 over 1,000 paths, walk-forward PF > 1, walk-forward permutation p < 0.05 over 200 paths) plus Holm correction and an intraday buy-and-hold benchmark. Writes `reports/latest.json`.
- `test_lab.py`: lookahead and engine tests (`python3 test_lab.py`).
- `data/`: Yahoo Finance `NQ=F` daily and 1-hour bars; source and download time in `data/SOURCE.json`.

Run: `pip install yfinance pandas numpy numba && python3 test_lab.py && python3 tonight.py`
