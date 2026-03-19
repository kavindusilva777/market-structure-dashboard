"""
Multi-Instrument Market Structure Dashboard
NQ Futures  |  XAU/USD (Gold)
Strict close-to-close candle logic — wicks excluded

Live price sources:
  NQ  → Yahoo Finance NQ=F  (~15 min delay, free)
  XAU → gold-api.com        (real-time, free, no key)
Candle data: Yahoo Finance (both instruments)
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime
import time

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Structure Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap');

  /* ── CSS Variables — both themes ── */
  :root {
    --bull-green:  #4ade80;
    --bear-red:    #f87171;
    --obsidian:    #09080a;
    --obs2:        #0f0d10;
    --obs3:        #161318;
    --obs4:        #1e1a22;
  }

  /* ── XAU theme (gold) ── */
  .theme-xau {
    --accent:        #f5c842;
    --accent-mid:    #d4a017;
    --accent-deep:   #a67c00;
    --accent-muted:  #7a5c1e;
    --accent-dim:    #3d2e0a;
    --text-primary:  #fdf6e3;
    --text-sec:      #d4a844;
    --text-muted:    #9a7c3a;
    --border:        #2a2118;
    --border-acc:    #3d2e0a;
    --orb-color:     rgba(213,160,23,0.05);
  }

  /* ── NQ theme (blue-steel) ── */
  .theme-nq {
    --accent:        #60a5fa;
    --accent-mid:    #3b82f6;
    --accent-deep:   #1d4ed8;
    --accent-muted:  #1e3a5f;
    --accent-dim:    #0f2040;
    --text-primary:  #e8f4ff;
    --text-sec:      #90c0f0;
    --text-muted:    #5a82a8;
    --border:        #141e2e;
    --border-acc:    #0f2040;
    --orb-color:     rgba(59,130,246,0.04);
  }

  /* ── Base styles ── */
  html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
    background-color: var(--obsidian);
    color: var(--text-primary, #e0e8f0);
  }
  .stApp { background-color: var(--obsidian); }
  .block-container { padding: 0 2.2rem 2rem 2.2rem; max-width: 1480px; }
  #MainMenu, footer, header { visibility: hidden; }
  .stDeployButton { display: none; }

  @keyframes livePulse {
    0%,100% { opacity:1; box-shadow: 0 0 6px var(--bull-green); }
    50%      { opacity:0.4; box-shadow: 0 0 2px var(--bull-green); }
  }
  @keyframes fadeUp {
    from { opacity:0; transform:translateY(6px); }
    to   { opacity:1; transform:translateY(0); }
  }

  /* ── Switcher bar ── */
  .switcher-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 0 0.85rem 0;
    margin-bottom: 0;
    border-bottom: 1px solid var(--border, #1a2535);
    position: relative;
  }
  .switcher-bar::after {
    content: '';
    position: absolute; bottom: -1px; left: 0;
    width: 160px; height: 1px;
    background: linear-gradient(90deg, var(--accent-mid, #3b82f6), transparent);
  }
  .switcher-left {
    display: flex; flex-direction: column; gap: 0.1rem;
  }
  .switcher-eyebrow {
    font-size: 0.56rem; letter-spacing: 0.26em; text-transform: uppercase;
    color: var(--accent-deep, #1d4ed8);
  }
  .switcher-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.55rem; font-weight: 600; line-height: 1;
    color: var(--accent, #60a5fa);
    letter-spacing: 0.03em;
  }
  .switcher-sub {
    font-size: 0.58rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--text-muted, #4a5568); margin-top: 0.1rem;
  }

  /* ── Instrument pill buttons ── */
  .inst-pills {
    display: flex; gap: 0.5rem; align-items: center;
  }
  .inst-pill {
    padding: 0.35rem 1.1rem; border-radius: 4px; cursor: pointer;
    font-size: 0.7rem; font-weight: 500; letter-spacing: 0.12em;
    text-transform: uppercase; font-family: 'DM Mono', monospace;
    border: 1px solid; transition: all 0.15s; user-select: none;
  }
  .pill-active-xau {
    background: rgba(245,200,66,0.12); color: #f5c842;
    border-color: rgba(245,200,66,0.4);
  }
  .pill-inactive-xau {
    background: transparent; color: #5a4a2a;
    border-color: #3d2e0a;
  }
  .pill-active-nq {
    background: rgba(96,165,250,0.12); color: #60a5fa;
    border-color: rgba(96,165,250,0.4);
  }
  .pill-inactive-nq {
    background: transparent; color: #2a3f5a;
    border-color: #0f2040;
  }

  /* ── Price block ── */
  .price-block { text-align: right; }
  .price-eyebrow {
    font-size: 0.56rem; color: var(--text-muted); letter-spacing: 0.2em;
    text-transform: uppercase; margin-bottom: 0.1rem;
    display: flex; align-items: center; gap: 0.5rem; justify-content: flex-end;
  }
  .live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--bull-green); display: inline-block;
    animation: livePulse 1.8s ease infinite;
  }
  .price-main {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.5rem; font-weight: 700; line-height: 1;
    color: var(--accent); text-shadow: 0 0 40px var(--orb-color);
  }
  .price-chg-pos { font-size: 0.78rem; color: var(--bull-green); margin-top: 0.08rem; }
  .price-chg-neg { font-size: 0.78rem; color: var(--bear-red);   margin-top: 0.08rem; }

  /* ── Metric cards ── */
  .cards-row { display: flex; gap: 0.8rem; margin: 1.2rem 0 0.4rem; }
  .metric-card {
    flex: 1; background: var(--obs3); border: 1px solid var(--border-acc);
    border-radius: 6px; padding: 0.9rem 1rem; position: relative; overflow: hidden;
  }
  .metric-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  }
  .metric-card.bull::before { background: linear-gradient(90deg, var(--bull-green), transparent); }
  .metric-card.bear::before { background: linear-gradient(90deg, var(--bear-red),  transparent); }
  .metric-card.neu::before  { background: linear-gradient(90deg, var(--accent-mid),transparent); }
  .mc-label {
    font-size: 0.58rem; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--accent-mid); margin-bottom: 0.3rem; font-weight: 500;
  }
  .mc-value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.45rem; font-weight: 700; line-height: 1.1;
  }
  .mc-sub { font-size: 0.64rem; color: var(--text-sec); margin-top: 0.2rem; font-weight: 500; }
  .bull-text { color: var(--bull-green); }
  .bear-text { color: var(--bear-red); }
  .acc-text  { color: var(--accent); }

  /* ── Divider ── */
  .acc-divider {
    height: 1px; margin: 0.8rem 0 1rem;
    background: linear-gradient(90deg, transparent, var(--accent-dim), transparent);
  }

  /* ── Main table ── */
  .tf-table {
    background: var(--obs2); border: 1px solid var(--border-acc);
    border-radius: 8px; overflow: hidden; margin-bottom: 1.2rem;
    animation: fadeUp 0.3s ease both;
  }
  .tf-head {
    display: grid; grid-template-columns: 88px 130px 155px 130px 130px 1fr;
    padding: 0.6rem 1.25rem; background: var(--obs3);
    border-bottom: 1px solid var(--border-acc);
    font-size: 0.56rem; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--accent-mid); font-weight: 600;
  }
  .tf-row {
    display: grid; grid-template-columns: 88px 130px 155px 130px 130px 1fr;
    padding: 0.9rem 1.25rem; border-bottom: 1px solid var(--border);
    align-items: center; position: relative; transition: background 0.1s;
  }
  .tf-row:last-child { border-bottom: none; }
  .tf-row:hover { background: var(--obs3); }
  .tf-row::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px; opacity: 0;
  }
  .tf-row.rbull::before { background: var(--bull-green); opacity: 0.55; }
  .tf-row.rbear::before { background: var(--bear-red);   opacity: 0.55; }
  .tf-name {
    font-family: 'DM Mono', monospace; font-size: 0.82rem; font-weight: 700;
    color: var(--text-primary); letter-spacing: 0.04em;
  }
  .bias-badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    padding: 0.2rem 0.65rem; border-radius: 3px;
    font-size: 0.66rem; font-weight: 500; letter-spacing: 0.1em;
    text-transform: uppercase; font-family: 'DM Mono', monospace;
  }
  .bbull { background:rgba(74,222,128,0.08); color:var(--bull-green); border:1px solid rgba(74,222,128,0.22); }
  .bbear { background:rgba(248,113,113,0.08); color:var(--bear-red);  border:1px solid rgba(248,113,113,0.22); }
  .str-wrap { display:flex; align-items:center; gap:0.5rem; }
  .str-bg { width:60px; height:3px; background:var(--obs4); border-radius:2px; }
  .str-fill { height:100%; border-radius:2px; }
  .str-lbl { font-size:0.65rem; color:var(--text-primary); font-weight:600; }
  .dist-val { font-family:'DM Mono',monospace; font-size:0.76rem; font-weight:500; }
  .brk-lvl  { font-family:'DM Mono',monospace; font-size:0.7rem; color:var(--text-sec); font-weight:500; }
  .stinfo   { font-family:'DM Mono',monospace; font-size:0.64rem; color:var(--text-sec); line-height:1.7; font-weight:500; }

  /* ── Right panel ── */
  .rpanel {
    background: var(--obs2); border: 1px solid var(--border);
    border-radius: 8px; padding: 1.15rem 1.2rem; margin-bottom: 1.1rem;
    position: relative; overflow: hidden;
  }
  .rpanel::before {
    content:''; position:absolute; top:0; left:0; right:0; height:1px;
    background: linear-gradient(90deg, var(--accent-dim), transparent);
  }
  .rp-eyebrow {
    font-size:0.56rem; letter-spacing:0.22em; text-transform:uppercase;
    color:var(--accent-mid); margin-bottom:0.65rem; font-weight:600;
  }
  .align-score {
    font-family:'Cormorant Garamond',serif;
    font-size:2.1rem; font-weight:700; line-height:1;
  }
  .align-lbl { font-size:0.72rem; color:var(--text-sec); margin-top:0.1rem; font-weight:500; }
  .dots-row { display:flex; gap:0.38rem; margin-top:0.75rem; flex-wrap:wrap; }
  .adot {
    width:25px; height:25px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:0.52rem; font-weight:500; font-family:'DM Mono',monospace;
  }
  .adot-bull { background:rgba(74,222,128,0.1); border:1px solid rgba(74,222,128,0.4); color:var(--bull-green); }
  .adot-bear { background:rgba(248,113,113,0.1); border:1px solid rgba(248,113,113,0.4); color:var(--bear-red); }
  .adot-emp  { background:transparent; border:1px solid var(--border); color:var(--text-muted); }

  /* ── Signal card ── */
  .sig-card {
    border-radius:8px; padding:1.15rem 1.2rem; border:1px solid;
    margin-bottom:1.1rem;
  }
  .sc-bull  { background:rgba(74,222,128,0.04);  border-color:rgba(74,222,128,0.2); }
  .sc-bear  { background:rgba(248,113,113,0.04); border-color:rgba(248,113,113,0.2); }
  .sc-mixed { background:rgba(var(--accent-dim),0.04); border-color:rgba(213,160,23,0.2); }
  .sig-eye  { font-size:0.56rem; letter-spacing:0.2em; text-transform:uppercase; color:var(--accent-mid); margin-bottom:0.35rem; font-weight:600; }
  .sig-title {
    font-family:'Cormorant Garamond',serif;
    font-size:1.2rem; font-weight:600; line-height:1.25;
  }
  .sig-desc { font-size:0.7rem; color:var(--text-primary); margin-top:0.35rem; line-height:1.65; font-weight:400; }
  .sig-tags { display:flex; gap:0.38rem; margin-top:0.7rem; flex-wrap:wrap; }
  .sig-tag {
    padding:0.16rem 0.52rem; border-radius:2px;
    font-size:0.57rem; font-family:'DM Mono',monospace;
    background:rgba(255,255,255,0.07); color:var(--text-sec);
    border:1px solid var(--accent-dim);
  }

  /* ── Footer ── */
  .dash-footer {
    display:flex; justify-content:space-between; align-items:center;
    border-top:1px solid var(--border); padding-top:0.75rem; margin-top:0.4rem;
  }
  .foot-l { font-size:0.57rem; color:var(--text-muted); letter-spacing:0.08em; }
  .foot-r { font-size:0.57rem; color:var(--text-muted); }

  /* ── Streamlit radio override (instrument switcher) ── */
  div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
  .stRadio > div { flex-direction: row !important; gap: 0.5rem; }
  .stRadio label {
    padding: 0.35rem 1.1rem !important; border-radius: 4px !important;
    font-size: 0.7rem !important; font-weight: 500 !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
    font-family: 'DM Mono', monospace !important;
    border: 1px solid !important; cursor: pointer !important;
    transition: all 0.15s !important;
  }

  /* ── Orb background glow ── */
  .bg-orb {
    position:fixed; top:-150px; right:-150px;
    width:500px; height:500px; border-radius:50%;
    background: radial-gradient(circle, var(--orb-color) 0%, transparent 70%);
    pointer-events:none; z-index:0;
  }

  ::-webkit-scrollbar { width:4px; height:4px; }
  ::-webkit-scrollbar-track { background:var(--obsidian); }
  ::-webkit-scrollbar-thumb { background:var(--accent-dim); border-radius:2px; }
</style>
""", unsafe_allow_html=True)


# ─── Instrument Config ────────────────────────────────────────────────────────
INSTRUMENTS = {
    "XAU/USD": {
        "ticker":      "GC=F",
        "label":       "XAU / USD",
        "eyebrow":     "Precious Metals · CFD Analysis",
        "sub":         "Multi-Timeframe Structure · Close-to-Close · Wicks Excluded",
        "price_label": "Gold Spot  ·  gold-api.com",
        "theme":       "theme-xau",
        "decimals":    2,
        "dist_suffix": "",
        "timeframes":  ["1D","4H","1H","30M","15M"],
        "tf_labels":   ["Daily","4 Hour","1 Hour","30 Min","15 Min"],
        "tf_dots":     ["D","4H","1H","30","15"],
        "live_api":    True,
    },
    "NQ Futures": {
        "ticker":      "NQ=F",
        "label":       "NQ Futures",
        "eyebrow":     "Nasdaq-100 · Futures Analysis",
        "sub":         "Multi-Timeframe Structure · Close-to-Close · Wicks Excluded",
        "price_label": "NQ=F  ·  Yahoo Finance",
        "theme":       "theme-nq",
        "decimals":    2,
        "dist_suffix": " pts",
        "timeframes":  ["1D","4H","1H","30M"],
        "tf_labels":   ["Daily","4 Hour","1 Hour","30 Min"],
        "tf_dots":     ["D","4H","1H","30"],
        "live_api":    False,
    },
}


# ─── Data Fetching ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=5)
def fetch_xau_live_price():
    """Real-time XAU spot from gold-api.com — free, no key, no rate limits."""
    try:
        resp = requests.get(
            "https://api.gold-api.com/price/XAU",
            timeout=5,
            headers={"User-Agent": "MarketStructureDash/1.0"}
        )
        if resp.status_code == 200:
            j = resp.json()
            current = float(j.get("price", 0))
            prev    = float(j.get("prev_close_price", current))
            if current > 0:
                change = current - prev
                pct    = (change / prev * 100) if prev else 0
                return current, change, pct, True   # True = live
    except Exception:
        pass
    return None, None, None, False


@st.cache_data(ttl=15)
def fetch_yf_price(ticker: str):
    """Yahoo Finance delayed price — fallback for NQ and XAU backup."""
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="5m")
        if hist.empty:
            return None, None, None
        current = float(hist["Close"].iloc[-1])
        df_d = yf.download(ticker, period="5d", interval="1d",
                           progress=False, auto_adjust=True)
        if isinstance(df_d.columns, pd.MultiIndex):
            df_d.columns = df_d.columns.get_level_values(0)
        prev   = float(df_d["Close"].iloc[-2]) if len(df_d) >= 2 else current
        change = current - prev
        pct    = (change / prev * 100) if prev else 0
        return current, change, pct
    except Exception:
        return None, None, None


@st.cache_data(ttl=30)
def fetch_candles(ticker: str):
    """Fetch OHLCV candles for all timeframes."""
    data = {}
    try:
        periods = {
            "15m": ("5d",  "15m"),
            "30m": ("10d", "30m"),
            "1h":  ("30d", "1h"),
            "1h_long": ("60d", "1h"),   # for 4H resample
            "1d":  ("1y",  "1d"),
        }
        dfs = {}
        for key, (period, interval) in periods.items():
            df = yf.download(ticker, period=period, interval=interval,
                             progress=False, auto_adjust=True)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df2 = df[["Open","High","Low","Close","Volume"]].copy()
                # Squeeze any residual MultiIndex columns to 1D
                if isinstance(df2.columns, pd.MultiIndex):
                    df2.columns = df2.columns.get_level_values(0)
                dfs[key] = df2.dropna()

        if "15m"     in dfs: data["15M"] = dfs["15m"]
        if "30m"     in dfs: data["30M"] = dfs["30m"]
        if "1h"      in dfs: data["1H"]  = dfs["1h"]
        if "1h_long" in dfs:
            df4 = dfs["1h_long"].resample("4h").agg({
                "Open":  lambda x: x.iloc[0]  if len(x) > 0 else float("nan"),
                "High":  "max",
                "Low":   "min",
                "Close": lambda x: x.iloc[-1] if len(x) > 0 else float("nan"),
                "Volume":"sum"
            }).dropna()
            data["4H"] = df4
        if "1d" in dfs: data["1D"] = dfs["1d"]

    except Exception as e:
        st.warning(f"Candle data issue ({ticker}): {e}")
    return data


# ─── Market Structure Engine ──────────────────────────────────────────────────


def analyze_structure(df):
    if df is None or len(df) < 10:
        return None
    # Force clean 1D float array — yfinance can return 2D arrays with MultiIndex
    raw = df["Close"].values
    closes = np.array(raw, dtype=float).flatten()
    closes = closes[~np.isnan(closes)]
    n = len(closes)
    if n < 10:
        return None

    # Swing points — closes ONLY, no wicks
    sh, sl = [], []
    for i in range(1, n - 1):
        if closes[i] > closes[i-1] and closes[i] > closes[i+1]: sh.append((i, closes[i]))
        if closes[i] < closes[i-1] and closes[i] < closes[i+1]: sl.append((i, closes[i]))

    if len(sh) < 2 or len(sl) < 2:
        return _simple(closes)

    cur    = closes[-1]
    swings = sorted([(i,v,"H") for i,v in sh] + [(i,v,"L") for i,v in sl])

    bias = "Bullish"
    last_hh = last_hl = last_lh = last_ll = None
    break_idx = 0
    prev_h = prev_l = None

    for idx, val, kind in swings:
        if kind == "H":
            if prev_h is not None:
                if val > prev_h:
                    last_hh = val
                else:
                    last_lh = val
                    if bias == "Bullish" and last_hl and cur < last_hl:
                        bias = "Bearish"; last_hh = prev_h; break_idx = idx
            prev_h = val
        else:
            if prev_l is not None:
                if val > prev_l:
                    last_hl = val
                    if bias == "Bearish" and last_lh and cur > last_lh:
                        bias = "Bullish"; last_ll = prev_l; break_idx = idx
                else:
                    last_ll = val
            prev_l = val

    csb = max(0, n - 1 - break_idx)
    bl  = (last_hl if bias=="Bullish" else last_lh) or \
          (sl[-1][1] if bias=="Bullish" and sl else None) or \
          (sh[-1][1] if bias=="Bearish" and sh else None)
    dist = round(cur - bl, 2) if bl else None

    rh = [v for _,v,t in swings[-10:] if t=="H"]
    rl = [v for _,v,t in swings[-10:] if t=="L"]

    return {
        "bias": bias,
        "strength": _strength(closes, sh, sl, csb, bias),
        "break_level": bl, "distance": dist, "csb": csb,
        "current": cur,
        "last_hh": last_hh, "last_hl": last_hl,
        "last_lh": last_lh, "last_ll": last_ll,
        "hh": sum(1 for i in range(1,len(rh)) if rh[i]>rh[i-1]),
        "hl": sum(1 for i in range(1,len(rl)) if rl[i]>rl[i-1]),
        "lh": sum(1 for i in range(1,len(rh)) if rh[i]<rh[i-1]),
        "ll": sum(1 for i in range(1,len(rl)) if rl[i]<rl[i-1]),
    }


def _simple(closes):
    closes = np.array(closes, dtype=float).flatten()
    closes = closes[~np.isnan(closes)]
    n, cur = len(closes), closes[-1]
    mid = closes[n//2]
    bias = "Bullish" if cur > mid else "Bearish"
    bl = min(closes[n//2:]) if bias=="Bullish" else max(closes[n//2:])
    return {"bias":bias,"strength":"Weak","break_level":bl,
            "distance":round(cur-bl,2),"csb":n//4,"current":cur,
            "last_hh":None,"last_hl":None,"last_lh":None,"last_ll":None,
            "hh":0,"hl":0,"lh":0,"ll":0}


def _strength(closes, sh, sl, csb, bias):
    s = 0
    if csb >= 20: s += 2
    elif csb >= 8: s += 1
    if len(closes) >= 20:
        rng = max(closes[-20:]) - min(closes[-20:])
        if rng > 0:
            move = abs(closes[-1] - closes[max(0, len(closes)-csb-1)])
            ratio = move / rng
            if ratio > 0.6: s += 2
            elif ratio > 0.3: s += 1
    rh = [v for _,v in sh[-6:]]
    rl = [v for _,v in sl[-6:]]
    if bias == "Bullish":
        hhl = sum(1 for i in range(1,len(rh)) if rh[i]>rh[i-1])
        hll = sum(1 for i in range(1,len(rl)) if rl[i]>rl[i-1])
        if hhl+hll >= 4: s += 2
        elif hhl+hll >= 2: s += 1
    else:
        lll = sum(1 for i in range(1,len(rl)) if rl[i]<rl[i-1])
        lhl = sum(1 for i in range(1,len(rh)) if rh[i]<rh[i-1])
        if lll+lhl >= 4: s += 2
        elif lll+lhl >= 2: s += 1
    if s >= 5: return "Strong"
    if s >= 3: return "Medium"
    return "Weak"


def s_pct(s):   return {"Weak":28,"Medium":58,"Strong":93}.get(s,28)
def s_color(s, bias):
    if bias == "Bullish":
        return {"Weak":"#166534","Medium":"#4ade80","Strong":"#86efac"}.get(s,"#4ade80")
    return {"Weak":"#991b1b","Medium":"#f87171","Strong":"#fca5a5"}.get(s,"#f87171")


# ─── Signal Interpreter ───────────────────────────────────────────────────────

def interpret(results, bull, total, inst_name):
    bear = total - bull
    tfs  = list(results.keys())
    htf  = tfs[:2] if len(tfs) >= 2 else tfs
    ltf  = tfs[2:] if len(tfs) >= 3 else []
    htf_bull = all(results.get(t) and results[t]["bias"]=="Bullish" for t in htf)
    ltf_bull = all(results.get(t) and results[t]["bias"]=="Bullish" for t in ltf) if ltf else False
    htf_bear = all(results.get(t) and results[t]["bias"]=="Bearish" for t in htf)
    nm = inst_name

    if bull == total:
        return {"title":f"Strong Bullish Environment","style":"sc-bull","color":"#4ade80",
                "desc":f"All {total} timeframes aligned bullish on {nm}. High-probability long setups. Buy pullbacks to HL.",
                "tags":["Long Bias","Buy Dips","Trend Following",f"{total}/{total} Align"]}
    elif bull == 0:
        return {"title":f"Strong Bearish Environment","style":"sc-bear","color":"#f87171",
                "desc":f"All {total} timeframes aligned bearish on {nm}. Sell rallies into LH on lower timeframes.",
                "tags":["Short Bias","Sell Rallies","Trend Following",f"0/{total} Align"]}
    elif htf_bull and not ltf_bull:
        return {"title":"Pullback Long Environment","style":"sc-bull","color":"#4ade80",
                "desc":f"HTF bullish on {nm} but LTF retracing. Wait for LTF flip bullish for high R:R entry.",
                "tags":["Pullback Buy","Wait LTF Flip","HTF Bullish","High R:R"]}
    elif htf_bear and not all(results.get(t) and results[t]["bias"]=="Bearish" for t in ltf):
        return {"title":"Pullback Short Environment","style":"sc-bear","color":"#f87171",
                "desc":f"HTF bearish but LTF bouncing on {nm}. Wait for LTF to confirm bearish before shorting.",
                "tags":["Counter-Rally Short","HTF Pressure","Wait LTF","Caution"]}
    elif bull >= total - 1:
        return {"title":"Bullish Momentum Environment","style":"sc-bull","color":"#4ade80",
                "desc":f"{bull} of {total} timeframes bullish. Long bias dominant. Minor LTF bearish signals are noise.",
                "tags":["Long Bias","Momentum",f"{bull}/{total} Align"]}
    elif bear >= total - 1:
        return {"title":"Bearish Momentum Environment","style":"sc-bear","color":"#f87171",
                "desc":f"{bear} of {total} timeframes bearish. Short bias dominant. Bounces likely counter-trend.",
                "tags":["Short Bias","Momentum",f"{bull}/{total} Align"]}
    else:
        return {"title":"Choppy / Mixed Market","style":"sc-mixed","color":"#d4a017",
                "desc":f"Timeframes conflicting on {nm}. No clean edge. Reduce size or stand aside.",
                "tags":["No Clear Bias","Reduce Size","Stand Aside","Mixed"]}


# ─── HTML Builders ─────────────────────────────────────────────────────────────

def build_table(results, cfg):
    tf_order = list(zip(cfg["timeframes"], cfg["tf_labels"]))
    dec = cfg["decimals"]
    suf = cfg["dist_suffix"]
    rows = ""
    for key, label in tf_order:
        r = results.get(key)
        if not r:
            rows += f"""<div class="tf-row">
              <div class="tf-name">{label}</div>
              <div style="color:var(--text-sec);font-size:0.7rem;font-weight:500">No data</div>
              <div></div><div></div><div></div><div></div></div>"""
            continue
        bias = r["bias"]
        bc   = "bbull" if bias=="Bullish" else "bbear"
        rc   = "rbull" if bias=="Bullish" else "rbear"
        icon = "▲" if bias=="Bullish" else "▼"
        sp   = s_pct(r["strength"])
        sc   = s_color(r["strength"], bias)
        dist = r["distance"]
        bl   = r["break_level"]
        dc   = "bull-text" if (dist or 0) >= 0 else "bear-text"
        dsg  = "+" if (dist or 0) >= 0 else ""
        ds   = f"{dsg}{dist:,.{dec}f}{suf}" if dist is not None else "—"
        bls  = f"{bl:,.{dec}f}" if bl else "—"
        if bias=="Bullish":
            s1 = f"HH {r['last_hh']:,.{dec}f}" if r["last_hh"] else "HH —"
            s2 = f"HL {r['last_hl']:,.{dec}f}" if r["last_hl"] else "HL —"
        else:
            s1 = f"LH {r['last_lh']:,.{dec}f}" if r["last_lh"] else "LH —"
            s2 = f"LL {r['last_ll']:,.{dec}f}" if r["last_ll"] else "LL —"
        rows += f"""<div class="tf-row {rc}">
          <div class="tf-name">{label}</div>
          <div><span class="bias-badge {bc}">{icon} {bias}</span></div>
          <div class="str-wrap">
            <div class="str-bg"><div class="str-fill" style="width:{sp}%;background:{sc}"></div></div>
            <span class="str-lbl">{r['strength']}</span>
          </div>
          <div class="{dc} dist-val">{ds}</div>
          <div class="brk-lvl">{bls}</div>
          <div class="stinfo">{s1}<br>{s2}</div>
        </div>"""
    return f"""<div class="tf-table">
      <div class="tf-head">
        <div>Timeframe</div><div>Bias</div><div>Strength</div>
        <div>Distance</div><div>Break Level</div><div>Structure</div>
      </div>{rows}</div>"""


def build_alignment(results, cfg):
    tfs  = cfg["timeframes"]
    dots_lbl = cfg["tf_dots"]
    bull = 0
    dots = ""
    for tf, lbl in zip(tfs, dots_lbl):
        r = results.get(tf)
        if r and r["bias"]=="Bullish":
            bull += 1; dots += f'<div class="adot adot-bull">{lbl}</div>'
        elif r:
            dots += f'<div class="adot adot-bear">{lbl}</div>'
        else:
            dots += f'<div class="adot adot-emp">{lbl}</div>'
    total = len(tfs)
    sc = "bull-text" if bull >= total*0.7 else ("bear-text" if bull <= total*0.3 else "acc-text")
    lb = "Bullish" if bull >= total*0.7 else ("Bearish" if bull <= total*0.3 else "Mixed")
    return bull, total, f"""<div class="rpanel">
      <div class="rp-eyebrow">HTF Alignment Score</div>
      <div class="align-score {sc}">{bull}<span style="font-size:1rem;color:var(--text-muted)"> / {total}</span></div>
      <div class="align-lbl">{lb} Alignment</div>
      <div class="dots-row">{dots}</div>
    </div>"""


def build_signal(sig):
    tags = "".join(f'<span class="sig-tag">{t}</span>' for t in sig["tags"])
    return f"""<div class="sig-card {sig['style']}">
      <div class="sig-eye">Trading Environment</div>
      <div class="sig-title" style="color:{sig['color']}">{sig['title']}</div>
      <div class="sig-desc">{sig['desc']}</div>
      <div class="sig-tags">{tags}</div>
    </div>"""


# ─── Main App ──────────────────────────────────────────────────────────────────

def main():
    # ── Session state ──
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
        st.session_state.refresh_count = 0
    if "instrument" not in st.session_state:
        st.session_state.instrument = "XAU/USD"
    if "all_candles" not in st.session_state:
        st.session_state.all_candles = {}
    if "all_prices" not in st.session_state:
        st.session_state.all_prices = {}

    # ── Load ALL instruments into session_state on first run ──
    # session_state persists across reruns so switching is always instant.
    # Data is stored directly — no cache dependency, no threading.
    if not st.session_state.all_candles:
        for inst_key, inst_cfg in INSTRUMENTS.items():
            st.session_state.all_candles[inst_key] = fetch_candles(inst_cfg["ticker"])
        # Prices
        xp, xc, xpct, xl = fetch_xau_live_price()
        st.session_state.all_prices["XAU/USD"] = (xp, xc, xpct, xl)
        np_, nc, npct = fetch_yf_price("NQ=F")
        st.session_state.all_prices["NQ Futures"] = (np_, nc, npct, False)

    # ── Auto-refresh every 10s — refetch in background, update session_state ──
    if time.time() - st.session_state.last_refresh > 10:
        st.session_state.last_refresh = time.time()
        st.session_state.refresh_count += 1
        # Clear cache then refetch all instruments fresh
        st.cache_data.clear()
        for inst_key, inst_cfg in INSTRUMENTS.items():
            st.session_state.all_candles[inst_key] = fetch_candles(inst_cfg["ticker"])
        xp, xc, xpct, xl = fetch_xau_live_price()
        st.session_state.all_prices["XAU/USD"] = (xp, xc, xpct, xl)
        np_, nc, npct = fetch_yf_price("NQ=F")
        st.session_state.all_prices["NQ Futures"] = (np_, nc, npct, False)
        st.rerun()

    cfg   = INSTRUMENTS[st.session_state.instrument]
    theme = cfg["theme"]

    # ── Inject theme class onto root ──
    st.markdown(f"""
    <script>
      document.querySelector('.stApp').className =
        document.querySelector('.stApp').className + ' {theme}';
      document.documentElement.className = '{theme}';
    </script>
    <style>
      .stApp, :root {{ {_theme_vars(theme)} }}
    </style>
    <div class="bg-orb"></div>
    """, unsafe_allow_html=True)

    # ── Pull from session_state — always instant, no network call on switch ──
    candles  = st.session_state.all_candles.get(st.session_state.instrument, {})
    price_data = st.session_state.all_prices.get(st.session_state.instrument, (None, None, None, False))
    price, change, pct, is_live = price_data

    # ── Analyze structure ──
    results = {tf: analyze_structure(candles.get(tf)) for tf in cfg["timeframes"]}

    # ── TOP BAR: instrument name + switcher + price ──
    col_left, col_right = st.columns([2, 1])
    with col_left:
        cc  = "price-chg-pos" if (change or 0) >= 0 else "price-chg-neg"
        sg  = "+" if (change or 0) >= 0 else ""
        ps  = f"{price:,.{cfg['decimals']}f}" if price else "—"
        cs  = f"{sg}{change:,.{cfg['decimals']}f}  ({sg}{pct:.2f}%)" if change is not None else "—"
        live_html = '<span class="live-dot"></span>' if is_live else ""
        src_label = cfg["price_label"]

        st.markdown(f"""
        <div class="switcher-bar">
          <div class="switcher-left">
            <div class="switcher-eyebrow">{cfg['eyebrow']}</div>
            <div class="switcher-title">{cfg['label']}</div>
            <div class="switcher-sub">{cfg['sub']}</div>
          </div>
          <div class="price-block">
            <div class="price-eyebrow">{live_html} {src_label}</div>
            <div class="price-main">{ps}</div>
            <div class="{cc}">{cs}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("<div style='height:0.85rem'></div>", unsafe_allow_html=True)
        st.markdown("**Switch Instrument**")
        choice = st.radio(
            label="instrument",
            options=list(INSTRUMENTS.keys()),
            index=list(INSTRUMENTS.keys()).index(st.session_state.instrument),
            horizontal=True,
            label_visibility="collapsed",
        )
        if choice != st.session_state.instrument:
            st.session_state.instrument = choice
            st.cache_data.clear()
            st.rerun()

    # ── Metric cards ──
    tfs    = cfg["timeframes"]
    labels = cfg["tf_labels"]
    cols   = st.columns(len(tfs))
    for col, tf, lbl in zip(cols, tfs, labels):
        with col:
            r    = results.get(tf)
            bias = r["bias"] if r else "—"
            cls  = "bull" if bias=="Bullish" else ("bear" if bias=="Bearish" else "neu")
            tc   = "bull-text" if bias=="Bullish" else ("bear-text" if bias=="Bearish" else "acc-text")
            st.markdown(f"""<div class="metric-card {cls}">
              <div class="mc-label">{lbl}</div>
              <div class="mc-value {tc}">{bias}</div>
              <div class="mc-sub">{r['strength'] if r else '—'} structure</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div class='acc-divider'></div>", unsafe_allow_html=True)

    # ── Main table + right panel ──
    left, right = st.columns([3, 1.1])
    with left:
        st.markdown(build_table(results, cfg), unsafe_allow_html=True)
    with right:
        bull, total, align_html = build_alignment(results, cfg)
        st.markdown(align_html, unsafe_allow_html=True)
        sig = interpret(results, bull, total, st.session_state.instrument)
        st.markdown(build_signal(sig), unsafe_allow_html=True)

    # ── Footer ──
    now_str = datetime.now().strftime("%H:%M:%S")
    price_src = "gold-api.com (live)" if (cfg["live_api"] and is_live) else "Yahoo Finance (~15min delay)"
    st.markdown(f"""<div class="dash-footer">
      <div class="foot-l">
        {st.session_state.instrument} · CLOSE-TO-CLOSE · WICKS EXCLUDED ·
        Price: {price_src} · Candles: Yahoo Finance
      </div>
      <div class="foot-r">Updated {now_str} · Cycle #{st.session_state.refresh_count}</div>
    </div>""", unsafe_allow_html=True)

    time.sleep(1)
    st.rerun()


def _theme_vars(theme):
    """Return inline CSS variable overrides for the selected theme."""
    if theme == "theme-xau":
        return """
          --accent:#f5c842; --accent-mid:#d4a017; --accent-deep:#a67c00;
          --accent-muted:#7a5c1e; --accent-dim:#3d2e0a;
          --text-primary:#fdf6e3; --text-sec:#d4a844; --text-muted:#9a7c3a;
          --border:#2a2118; --border-acc:#3d2e0a; --orb-color:rgba(213,160,23,0.05);
        """
    else:
        return """
          --accent:#60a5fa; --accent-mid:#3b82f6; --accent-deep:#1d4ed8;
          --accent-muted:#1e3a5f; --accent-dim:#0f2040;
          --text-primary:#e8f4ff; --text-sec:#90c0f0; --text-muted:#5a82a8;
          --border:#141e2e; --border-acc:#0f2040; --orb-color:rgba(59,130,246,0.04);
        """


if __name__ == "__main__":
    main()
