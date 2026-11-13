"""NQ intraday regime lab: regime labelling, strategy families, and the 4 validation gates.

Method follows the user-supplied field report: per-bar log returns (pos decided at close t,
earns bar t+1), profit factor objective, bar permutation in log space (intrabar triplets and
gaps shuffled independently), walk-forward re-optimisation, walk-forward permutation test,
and plateau (neighbourhood) parameter selection. All numbers come from this code and the
saved data files; nothing is estimated by hand.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

POINT_VALUE_NQ = 20.0          # $ per NQ point (MNQ = $2)
TICK = 0.25
COMMISSION_PTS = 0.10          # ~$2 per side per NQ, in points (estimate, labelled)
COST_PTS_PER_SIDE = TICK + COMMISSION_PTS   # 1 tick slippage + commission, each side
RTH_HOURS = list(range(9, 16))  # 1h bars starting 09:00..15:00 ET; flat at 16:00 ET close
STOP_ATR = 1.5                 # close-based stop, fixed (not optimised, keeps N small)
ADX_FLAT = 20.0
EMA_LEN = 200
SLOPE_LOOKBACK = 20
REGIME_HOLD = 3
BULL, FLAT, BEAR = 1, 0, -1


# ----------------------------------------------------------------------------- data
def load_daily(path="data/NQ_1d.csv") -> pd.DataFrame:
    d = pd.read_csv(path, index_col=0, parse_dates=True)
    return d[["Open", "High", "Low", "Close"]].dropna()


def load_rth(path="data/NQ_1h.csv") -> pd.DataFrame:
    h = pd.read_csv(path, index_col=0)
    h.index = pd.to_datetime(h.index, utc=True).tz_convert("America/New_York")
    h = h[["Open", "High", "Low", "Close"]].dropna()
    h = h[h.index.dayofweek < 5]
    h = h[h.index.hour.isin(RTH_HOURS)]
    h["date"] = h.index.date
    counts = h.groupby("date").size()
    full = counts[counts == len(RTH_HOURS)].index      # drop half days / holidays
    return h[h["date"].isin(full)].copy()


# ----------------------------------------------------------------------------- regime
def ema(x: np.ndarray, n: int) -> np.ndarray:
    a = 2.0 / (n + 1)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def wilder(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)):
        out[i] = out[i - 1] + (x[i] - out[i - 1]) / n
    return out


def adx(h, l, c, n=14) -> np.ndarray:
    up = np.diff(h, prepend=h[0])
    dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    atr = wilder(tr, n)
    pdi = 100 * wilder(pdm, n) / atr
    ndi = 100 * wilder(ndm, n) / atr
    dx = 100 * np.abs(pdi - ndi) / np.where(pdi + ndi == 0, np.nan, pdi + ndi)
    dx = np.nan_to_num(dx)
    out = np.full_like(c, np.nan)
    start = 2 * n - 1
    out[start] = dx[n:start + 1].mean()
    for i in range(start + 1, len(c)):
        out[i] = out[i - 1] + (dx[i] - out[i - 1]) / n
    return out


def daily_regime(d: pd.DataFrame) -> pd.DataFrame:
    c, h, l = d.Close.values, d.High.values, d.Low.values
    e = ema(c, EMA_LEN)
    slope = e - np.roll(e, SLOPE_LOOKBACK)
    a = adx(h, l, c)
    raw = np.full(len(c), FLAT)
    raw[(c > e) & (slope > 0)] = BULL
    raw[(c < e) & (slope < 0)] = BEAR
    raw[a < ADX_FLAT] = FLAT
    raw[: EMA_LEN + SLOPE_LOOKBACK] = FLAT
    conf = np.empty_like(raw)
    conf[0] = raw[0]
    for i in range(1, len(raw)):
        if raw[i] != conf[i - 1] and i >= REGIME_HOLD - 1 and np.all(raw[i - REGIME_HOLD + 1:i + 1] == raw[i]):
            conf[i] = raw[i]
        else:
            conf[i] = conf[i - 1]
    return pd.DataFrame({"close": c, "ema200": e, "ema_slope20": slope, "adx14": a,
                         "raw": raw, "regime": conf}, index=d.index)


def attach_regime(rth: pd.DataFrame, reg: pd.DataFrame) -> np.ndarray:
    """Regime for session D = confirmed regime at the last daily close strictly before D."""
    ddates = np.array([x.date() for x in reg.index])
    out = np.empty(len(rth), dtype=np.int64)
    for i, day in enumerate(rth["date"].values):
        j = np.searchsorted(ddates, day, side="left") - 1
        out[i] = reg["regime"].values[j] if j >= 0 else FLAT
    return out


# ----------------------------------------------------------------------------- features
@njit(cache=True)
def _features(o, h, l, c, bar_in_day, rsi_n, atr_n, sma_n):
    n = len(c)
    rsi = np.full(n, 50.0); atr = np.full(n, np.nan); z = np.zeros(n)
    pdh = np.full(n, np.nan); pdl = np.full(n, np.nan); pdc = np.full(n, np.nan)
    ag = 0.0; al = 0.0; tr_s = 0.0
    cur_h = -1e18; cur_l = 1e18; prev_h = np.nan; prev_l = np.nan; prev_c = np.nan
    for i in range(n):
        if bar_in_day[i] == 0 and i > 0:
            prev_h = cur_h; prev_l = cur_l; prev_c = c[i - 1]
            cur_h = -1e18; cur_l = 1e18
        cur_h = max(cur_h, h[i]); cur_l = min(cur_l, l[i])
        pdh[i] = prev_h; pdl[i] = prev_l; pdc[i] = prev_c
        if i > 0:
            ch = c[i] - c[i - 1]
            g = ch if ch > 0 else 0.0
            lo = -ch if ch < 0 else 0.0
            ag = ag + (g - ag) / rsi_n; al = al + (lo - al) / rsi_n
            rsi[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
            tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        else:
            tr = h[i] - l[i]
        tr_s = tr if i == 0 else tr_s + (tr - tr_s) / atr_n
        if i >= atr_n:
            atr[i] = tr_s
        if i >= sma_n:
            w = c[i - sma_n + 1:i + 1]
            m = w.mean(); s = w.std()
            z[i] = (c[i] - m) / s if s > 0 else 0.0
    return rsi, atr, z, pdh, pdl, pdc


def features(o, h, l, c, bar_in_day):
    return _features(o, h, l, c, bar_in_day, 3, 14, 20)


# ----------------------------------------------------------------------------- strategies
# Each family: (name, regime, grid, one-sentence reason / who pays)
FAMILIES = [
    ("BULL_OPEN_DRIVE", BULL, np.round(np.arange(0.0, 0.81, 0.1), 2),
     "Strong first hour in an uptrend continues into the close (intraday momentum); late, under-positioned buyers pay."),
    ("BULL_PULLBACK_RSI", BULL, np.arange(15.0, 56.0, 5.0),
     "Short-term dips inside an uptrend get bought back; impatient sellers demanding liquidity pay."),
    ("BULL_PDH_BREAK", BULL, np.round(np.arange(0.0, 0.81, 0.1), 2),
     "Clearing yesterday's high in an uptrend triggers stops and breakout buying; trapped shorts pay."),
    ("FLAT_Z_FADE", FLAT, np.round(np.arange(1.0, 2.61, 0.2), 2),
     "In a range, stretched moves away from the 20-bar mean revert; liquidity takers overshooting pay."),
    ("FLAT_RSI_FADE", FLAT, np.arange(5.0, 46.0, 5.0),
     "In a range, short-term RSI extremes revert both ways; momentum chasers at the edge pay."),
    ("FLAT_PDR_FADE", FLAT, np.round(np.arange(0.0, 0.81, 0.1), 2),
     "In a range, pokes beyond yesterday's high/low fail; breakout traders pay."),
    ("BEAR_OPEN_DRIVE", BEAR, np.round(np.arange(0.0, 0.81, 0.1), 2),
     "Weak first hour in a downtrend continues into the close; late longs liquidating pay."),
    ("BEAR_PDL_BREAK", BEAR, np.round(np.arange(0.0, 0.81, 0.1), 2),
     "Losing yesterday's low in a downtrend triggers long stops; trapped longs pay."),
    ("BEAR_RALLY_FADE", BEAR, np.arange(45.0, 86.0, 5.0),
     "Short-term rallies inside a downtrend get sold; short-covering buyers pay."),
]
FAM_ID = {f[0]: i for i, f in enumerate(FAMILIES)}


@njit(cache=True)
def positions(fid, theta, regime_target, o, h, l, c, bar_in_day, last_bar, regime,
              rsi, atr, z, pdh, pdl, pdc):
    """Position held over bar t+1, decided with information up to the close of bar t."""
    n = len(c)
    pos = np.zeros(n)
    p = 0.0; entry = 0.0; stop_d = 0.0
    for t in range(n):
        if last_bar[t] or regime[t] != regime_target or np.isnan(atr[t]) or np.isnan(pdh[t]):
            p = 0.0; pos[t] = 0.0
            continue
        a = atr[t]
        # exits
        if p != 0.0:
            if p * (c[t] - entry) <= -stop_d:
                p = 0.0
            elif fid == 1 and rsi[t] > 60.0:
                p = 0.0
            elif fid == 3 and abs(z[t]) < 0.25:
                p = 0.0
            elif fid == 4 and ((p > 0 and rsi[t] > 50.0) or (p < 0 and rsi[t] < 50.0)):
                p = 0.0
            elif fid == 5 and ((p > 0 and c[t] >= (pdh[t] + pdl[t]) / 2) or (p < 0 and c[t] <= (pdh[t] + pdl[t]) / 2)):
                p = 0.0
            elif fid == 8 and rsi[t] < 40.0:
                p = 0.0
        # entries (one trade per signal, only when flat)
        if p == 0.0:
            new = 0.0
            if fid == 0 and bar_in_day[t] == 0 and c[t] - o[t] > theta * a:
                new = 1.0
            elif fid == 1 and rsi[t] < theta:
                new = 1.0
            elif fid == 2 and c[t] > pdh[t] + theta * a and c[t - 1] <= pdh[t] + theta * a:
                new = 1.0
            elif fid == 3:
                if z[t] > theta: new = -1.0
                elif z[t] < -theta: new = 1.0
            elif fid == 4:
                if rsi[t] > 100.0 - theta: new = -1.0
                elif rsi[t] < theta: new = 1.0
            elif fid == 5:
                if c[t] > pdh[t] + theta * a: new = -1.0
                elif c[t] < pdl[t] - theta * a: new = 1.0
            elif fid == 6 and bar_in_day[t] == 0 and o[t] - c[t] > theta * a:
                new = -1.0
            elif fid == 7 and c[t] < pdl[t] - theta * a and c[t - 1] >= pdl[t] - theta * a:
                new = -1.0
            elif fid == 8 and rsi[t] > theta:
                new = -1.0
            if new != 0.0:
                p = new; entry = c[t]; stop_d = 1.5 * a
        pos[t] = p
    return pos


@njit(cache=True)
def bar_returns(pos, c, last_bar, cost_pts):
    """r_t = pos_t * ln(C_{t+1}/C_t) minus cost on every position change; flat across sessions."""
    n = len(c)
    r = np.zeros(n)
    prev = 0.0
    for t in range(n - 1):
        p = pos[t]
        if last_bar[t]:
            p = 0.0
        rr = p * np.log(c[t + 1] / c[t]) if not last_bar[t] else 0.0
        rr -= abs(p - prev) * cost_pts / c[t]
        r[t] = rr
        prev = p
    if prev != 0.0:
        r[n - 1] -= abs(prev) * cost_pts / c[n - 1]
    return r


@njit(cache=True)
def profit_factor(r):
    g = 0.0; lo = 0.0
    for x in r:
        if x > 0: g += x
        elif x < 0: lo -= x
    if lo == 0.0:
        return 0.0 if g == 0.0 else 99.0
    return g / lo


# ----------------------------------------------------------------------------- engine
class Market:
    def __init__(self, rth: pd.DataFrame, regime: np.ndarray):
        self.idx = rth.index
        self.o = rth.Open.values.astype(np.float64)
        self.h = rth.High.values.astype(np.float64)
        self.l = rth.Low.values.astype(np.float64)
        self.c = rth.Close.values.astype(np.float64)
        self.date = rth["date"].values
        hours = rth.index.hour.values
        self.bar_in_day = (hours - RTH_HOURS[0]).astype(np.int64)
        self.last_bar = hours == RTH_HOURS[-1]
        self.regime = regime.astype(np.int64)
        self.feat = features(self.o, self.h, self.l, self.c, self.bar_in_day)

    def with_prices(self, o, h, l, c):
        m = object.__new__(Market)
        m.__dict__.update(self.__dict__)
        m.o, m.h, m.l, m.c = o, h, l, c
        m.feat = features(o, h, l, c, self.bar_in_day)
        return m

    def run(self, fid, theta, target):
        pos = positions(fid, theta, target, self.o, self.h, self.l, self.c, self.bar_in_day,
                        self.last_bar, self.regime, *self.feat)
        return pos, bar_returns(pos, self.c, self.last_bar, COST_PTS_PER_SIDE)


def plateau(pf: np.ndarray):
    n = len(pf)
    nbr = np.array([pf[max(i - 1, 0):min(i + 1, n - 1) + 1].mean() for i in range(n)])
    hat = int(np.argmax(nbr)); star = int(np.argmax(pf))
    rho = (nbr[hat] - 1.0) / (pf[star] - 1.0) if pf[star] > 1.0 else 0.0
    return hat, rho, nbr


def optimise(m: Market, fid, grid, target, lo, hi):
    """Best plateau-centre PF over grid on bars [lo, hi)."""
    pfs = np.empty(len(grid))
    for k, th in enumerate(grid):
        _, r = m.run(fid, th, target)
        pfs[k] = profit_factor(r[lo:hi])
    hat, rho, nbr = plateau(pfs)
    return hat, nbr[hat], pfs, rho


def permute_bars(m: Market, start: int, rng) -> Market:
    """Masters-style bar permutation in log space; bars before `start` kept intact."""
    lo_, lh, ll, lc = np.log(m.o), np.log(m.h), np.log(m.l), np.log(m.c)
    idx = np.arange(start + 1, len(lc))
    gap = lo_[idx] - lc[idx - 1]
    hlc = np.stack([lh[idx] - lo_[idx], ll[idx] - lo_[idx], lc[idx] - lo_[idx]], axis=1)
    rng.shuffle(gap)
    hlc = hlc[rng.permutation(len(hlc))]
    no, nh, nl, nc = lo_.copy(), lh.copy(), ll.copy(), lc.copy()
    prev = lc[start]
    for k, i in enumerate(idx):
        oo = prev + gap[k]
        no[i] = oo; nh[i] = oo + hlc[k, 0]; nl[i] = oo + hlc[k, 1]; nc[i] = oo + hlc[k, 2]
        prev = nc[i]
    return m.with_prices(np.exp(no), np.exp(nh), np.exp(nl), np.exp(nc))


def walk_forward(m: Market, fid, grid, target, month_starts, train_months):
    """Re-optimise on trailing `train_months`, trade next month; returns OOS bar returns and chosen thetas."""
    r_oos = np.zeros(len(m.c)); chosen = []
    for k in range(train_months, len(month_starts) - 1):
        tr_lo, tr_hi = month_starts[k - train_months], month_starts[k]
        hat, _, _, _ = optimise(m, fid, grid, target, tr_lo, tr_hi)
        _, r = m.run(fid, grid[hat], target)
        r_oos[month_starts[k]:month_starts[k + 1]] = r[month_starts[k]:month_starts[k + 1]]
        chosen.append(float(grid[hat]))
    return r_oos, chosen
