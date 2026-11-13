"""Tonight's run: regime read, then Judge's 4 gates over every strategy family.

Usage: python3 tonight.py [--is-perms 1000] [--wf-perms 200] [--seed 7]
Writes reports/run_<UTC>.json and reports/latest.md.
"""
from __future__ import annotations

import argparse, datetime, json, os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import lab

TRAIN_MONTHS = 12
MIN_TRADES = 20


def build():
    d = lab.load_daily()
    reg = lab.daily_regime(d)
    rth = lab.load_rth()
    m = lab.Market(rth, lab.attach_regime(rth, reg))
    months = pd.PeriodIndex(m.idx.tz_localize(None), freq="M")
    ms = [0] + [i for i in range(1, len(months)) if months[i] != months[i - 1]] + [len(m.c)]
    return d, reg, rth, m, ms


def is_market(rth, m, ms):
    end = ms[TRAIN_MONTHS]
    return lab.Market(rth.iloc[:end], m.regime[:end]), end


def best_all(m, lo, hi):
    return [lab.optimise(m, i, g, tgt, lo, hi)[1] for i, (_, tgt, g, _) in enumerate(lab.FAMILIES)]


def wf_all(m, ms):
    out = []
    for i, (_, tgt, g, _) in enumerate(lab.FAMILIES):
        r, _ = lab.walk_forward(m, i, g, tgt, ms, TRAIN_MONTHS)
        out.append(lab.profit_factor(r[ms[TRAIN_MONTHS]:]))
    return out


def _is_worker(args):
    seed, n = args
    _, _, rth, m, ms = build()
    mi, end = is_market(rth, m, ms)
    rng = np.random.default_rng(seed)
    return [best_all(lab.permute_bars(mi, 0, rng), 0, end) for _ in range(n)]


def _wf_worker(args):
    seed, n = args
    _, _, _, m, ms = build()
    rng = np.random.default_rng(seed)
    start = ms[TRAIN_MONTHS] - 1   # first training window kept intact
    return [wf_all(lab.permute_bars(m, start, rng), ms) for _ in range(n)]


def parallel(fn, total, seed, workers=4):
    chunks = [(seed * 1000 + k, total // workers + (1 if k < total % workers else 0)) for k in range(workers)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(fn, chunks))
    return np.array([row for part in res for row in part])


def trade_stats(m, pos, lo, hi):
    """Dollar stats per 1 NQ contract over bars [lo, hi), costs included."""
    pnl = np.zeros(len(m.c)); prev = 0.0
    for t in range(len(m.c) - 1):
        p = 0.0 if m.last_bar[t] else pos[t]
        pnl[t] = p * (m.c[t + 1] - m.c[t]) * lab.POINT_VALUE_NQ - abs(p - prev) * lab.COST_PTS_PER_SIDE * lab.POINT_VALUE_NQ
        prev = p
    trades, cur, cur_pnl = [], 0.0, 0.0
    for t in range(lo, hi):
        p = 0.0 if m.last_bar[t] else pos[t]
        if p != cur and cur != 0.0:
            trades.append(cur_pnl); cur_pnl = 0.0
        cur = p
        cur_pnl += pnl[t]
    if cur != 0.0:
        trades.append(cur_pnl)
    seg = pnl[lo:hi]
    eq = np.cumsum(seg)
    dd = float((np.maximum.accumulate(np.concatenate([[0], eq])) - np.concatenate([[0], eq])).max())
    month = pd.Series(seg, index=m.idx[lo:hi].tz_localize(None).to_period("M")).groupby(level=0).sum()
    streak = best = 0
    for x in trades:
        streak = streak + 1 if x < 0 else 0
        best = max(best, streak)
    tr = np.array(trades) if trades else np.zeros(0)
    return {"net_usd_1NQ": round(float(seg.sum()), 0), "trades": int(len(tr)),
            "win_rate": round(float((tr > 0).mean()), 3) if len(tr) else None,
            "max_dd_usd_1NQ": round(dd, 0), "worst_month": [str(month.idxmin()), round(float(month.min()), 0)] if len(month) else None,
            "longest_losing_streak": int(best)}


def benchmark(m, target, lo, hi):
    """Intraday buy-and-hold on the same regime days: long from 10:00 ET close to 16:00 ET, costs included."""
    pos = np.where((m.regime == target) & ~m.last_bar, 1.0, 0.0)
    r = lab.bar_returns(pos, m.c, m.last_bar, lab.COST_PTS_PER_SIDE)
    return pos, float(r[lo:hi].sum())


def holm(pvals):
    order = np.argsort(pvals); n = len(pvals); adj = np.empty(n); run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (n - rank) * pvals[i])); adj[i] = run
    return adj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-perms", type=int, default=1000)
    ap.add_argument("--wf-perms", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%MZ")

    d, reg, rth, m, ms = build()
    mi, is_end = is_market(rth, m, ms)
    wf_lo, wf_hi = ms[TRAIN_MONTHS], len(m.c)
    names = {1: "BULLISH", 0: "FLAT", -1: "BEARISH"}
    last = reg.iloc[-1]
    regime_today = {"as_of_daily_close": str(reg.index[-1].date()), "close": round(float(last.close), 2),
                    "ema200": round(float(last.ema200), 2), "ema200_slope20": round(float(last.ema_slope20), 2),
                    "adx14": round(float(last.adx14), 1), "raw_label": names[int(last.raw)],
                    "confirmed_regime": names[int(last.regime)]}
    days = pd.Series(m.regime[m.bar_in_day == 0]).map(names)
    regime_mix = {"in_sample": days[: (m.bar_in_day[:is_end] == 0).sum()].value_counts().to_dict(),
                  "walk_forward": days[(m.bar_in_day[:is_end] == 0).sum():].value_counts().to_dict()}

    real_is = best_all(mi, 0, is_end)
    real_wf = wf_all(m, ms)
    print("IS perms...", flush=True)
    null_is = parallel(_is_worker, a.is_perms, a.seed)
    print("WF perms...", flush=True)
    null_wf = parallel(_wf_worker, a.wf_perms, a.seed + 1)

    p_is = [(1 + (null_is[:, i] >= real_is[i]).sum()) / (len(null_is) + 1) for i in range(len(lab.FAMILIES))]
    p_wf = [(1 + (null_wf[:, i] >= real_wf[i]).sum()) / (len(null_wf) + 1) for i in range(len(lab.FAMILIES))]
    p_wf_holm = holm(np.array(p_wf))

    cards = []
    for i, (name, tgt, grid, why) in enumerate(lab.FAMILIES):
        hat, pf_is, pfs, rho = lab.optimise(mi, i, grid, tgt, 0, is_end)
        pos_is, _ = mi.run(i, grid[hat], tgt)
        is_stats = trade_stats(mi, pos_is, 0, is_end)
        r_wf, chosen = lab.walk_forward(m, i, grid, tgt, ms, TRAIN_MONTHS)
        # rebuild WF positions for dollar stats
        pos_wf = np.zeros(len(m.c))
        for k in range(TRAIN_MONTHS, len(ms) - 1):
            pk, _ = m.run(i, chosen[k - TRAIN_MONTHS], tgt)
            pos_wf[ms[k]:ms[k + 1]] = pk[ms[k]:ms[k + 1]]
        wf_stats = trade_stats(m, pos_wf, wf_lo, wf_hi)
        bpos, bench_log = benchmark(m, tgt, wf_lo, wf_hi)
        bench_stats = trade_stats(m, bpos, wf_lo, wf_hi)
        strat_log = float(r_wf[wf_lo:wf_hi].sum())
        gates = {
            "G1_in_sample": bool(pf_is > 1.0 and is_stats["trades"] >= MIN_TRADES and rho >= 0.5),
            "G2_is_permutation_p<0.01": bool(p_is[i] < 0.01),
            "G3_walk_forward_PF>1": bool(real_wf[i] > 1.0),
            "G4_wf_permutation_p<0.05": bool(p_wf[i] < 0.05),
        }
        extra = {"holm_adjusted_p_wf<0.05": bool(p_wf_holm[i] < 0.05),
                 "beats_intraday_buy_hold_after_costs": bool(strat_log > bench_log and strat_log > 0),
                 "wf_trades>=20": bool(wf_stats["trades"] >= MIN_TRADES)}
        cards.append({"name": name, "regime": names[tgt], "why": why,
                      "grid": [float(x) for x in grid], "plateau_theta_IS": float(grid[hat]), "rho_plateau": round(float(rho), 2),
                      "pf_is_plateau": round(float(pf_is), 3), "pf_is_by_theta": [round(float(x), 3) for x in pfs],
                      "p_is": round(float(p_is[i]), 4), "pf_wf": round(float(real_wf[i]), 3),
                      "p_wf": round(float(p_wf[i]), 4), "p_wf_holm": round(float(p_wf_holm[i]), 4),
                      "wf_thetas_chosen": chosen, "is_stats": is_stats, "wf_stats": wf_stats,
                      "wf_log_return": round(strat_log, 4), "benchmark_wf_log_return": round(bench_log, 4),
                      "benchmark_wf_stats": bench_stats, "gates": gates, "extra_checks": extra,
                      "passes_all": bool(all(gates.values()) and all(extra.values()))})

    out = {"run_utc": stamp, "data": json.load(open("data/SOURCE.json")),
           "settings": {"is_perms": len(null_is), "wf_perms": len(null_wf), "seed": a.seed,
                        "cost_pts_per_side": lab.COST_PTS_PER_SIDE, "train_months": TRAIN_MONTHS,
                        "in_sample": [str(m.idx[0]), str(m.idx[is_end - 1])],
                        "walk_forward_oos": [str(m.idx[wf_lo]), str(m.idx[wf_hi - 1])],
                        "configs_tested_N": int(sum(len(f[2]) for f in lab.FAMILIES))},
           "regime_today": regime_today, "regime_day_counts": regime_mix, "cards": cards}
    os.makedirs("reports", exist_ok=True)
    json.dump(out, open(f"reports/run_{stamp}.json", "w"), indent=1, default=str)
    json.dump(out, open("reports/latest.json", "w"), indent=1, default=str)
    print(json.dumps({"regime_today": regime_today, "regime_day_counts": regime_mix}, indent=1, default=str))
    for c in cards:
        print(f"{c['name']:18s} PF_IS={c['pf_is_plateau']:.3f} rho={c['rho_plateau']:.2f} p_IS={c['p_is']:.4f} "
              f"PF_WF={c['pf_wf']:.3f} p_WF={c['p_wf']:.4f} holm={c['p_wf_holm']:.3f} "
              f"WF$={c['wf_stats']['net_usd_1NQ']:.0f} tr={c['wf_stats']['trades']} bench$={c['benchmark_wf_stats']['net_usd_1NQ']:.0f} "
              f"gates={''.join('1' if v else '0' for v in c['gates'].values())} PASS={c['passes_all']}")


if __name__ == "__main__":
    main()
