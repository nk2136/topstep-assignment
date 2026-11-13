"""Leakage and engine tests: changing future prices must never change past positions."""
import numpy as np, lab, tonight

def test_no_lookahead():
    _, _, rth, m, ms = tonight.build()
    cut = len(m.c) // 2
    rng = np.random.default_rng(0)
    m2 = lab.permute_bars(m, cut, rng)          # future after `cut` scrambled
    for i, (_, tgt, g, _) in enumerate(lab.FAMILIES):
        for th in g:
            p1, _ = m.run(i, th, tgt); p2, _ = m2.run(i, th, tgt)
            assert np.array_equal(p1[:cut + 1], p2[:cut + 1]), (i, th)

def test_regime_uses_prior_close_only():
    d = lab.load_daily(); reg = lab.daily_regime(d)
    reg2 = lab.daily_regime(d.iloc[:-50])
    assert np.array_equal(reg.regime.values[:-50], reg2.regime.values)

def test_flat_at_session_end_and_costs():
    _, _, _, m, _ = tonight.build()
    pos, r = m.run(0, 0.0, lab.BULL)
    assert np.all(pos[m.last_bar] == 0)
    pos0 = np.zeros(len(m.c)); assert np.all(lab.bar_returns(pos0, m.c, m.last_bar, 0.35) == 0)

def test_permutation_preserves_endpoints():
    _, _, _, m, _ = tonight.build()
    p = lab.permute_bars(m, 0, np.random.default_rng(1))
    assert abs(np.log(p.c[-1]) - np.log(m.c[-1])) < 1e-9 and abs(p.c[0] - m.c[0]) < 1e-6
    assert np.all(p.h >= np.maximum(p.o, p.c) - 1e-6) and np.all(p.l <= np.minimum(p.o, p.c) + 1e-6)

if __name__ == "__main__":
    for f in [test_no_lookahead, test_regime_uses_prior_close_only, test_flat_at_session_end_and_costs, test_permutation_preserves_endpoints]:
        f(); print("PASS", f.__name__)
