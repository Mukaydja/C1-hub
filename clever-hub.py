# -*- coding: utf-8 -*-
# Football Hub - Analytics (v3.0)
# Réécriture complète : colonnes canoniques, KPIs enrichis, nouvelles visualisations

import os
from pathlib import Path
import io
import hashlib
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import unicodedata
import requests

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Football Hub - Analytics", page_icon="⚽", layout="wide")

# =============================================================================
# ------------------------------- STYLE GLOBAL --------------------------------
# =============================================================================
st.markdown(
    """
    <style>
    :root { 
        --bg: #0b1220; --card: #121a2b; --muted: #94a3b8; --text: #e2e8f0;
        --radius: 16px; --primary: #3b82f6; --success: #10b981; --warning: #f59e0b; --danger: #ef4444;
    }
    .stApp { background: linear-gradient(180deg, #0b1220 0%, #0c1322 100%); color: var(--text); font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .glass { background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03));
             border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius); padding: 1rem 1.25rem; backdrop-filter: blur(10px); }
    .hero { border-radius: 22px; padding: 20px 24px; border: 1px solid rgba(255,255,255,0.10);
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(16, 185, 129, 0.1)); }
    .pill { display: inline-block; padding: 6px 12px; font-size: 13px; border-radius: 999px;
            background: rgba(94,234,212,0.15); border: 1px solid rgba(94,234,212,0.35); font-weight: 500; }
    .divider { height: 1px; background: rgba(255,255,255,0.08); margin: 12px 0 16px 0; }
    .metric-card { background: var(--card); border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius); padding: 16px; transition: all 0.3s ease; }
    .metric-card:hover { border-color: var(--primary); transform: translateY(-2px); }
    .metric-card h3 { font-size: 13px; color: var(--muted); margin: 0 0 8px 0; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-card .value { font-size: 24px; font-weight: 700; line-height: 1.2; }
    .avatar { width: 54px; height: 54px; border-radius: 12px; background: linear-gradient(135deg, var(--primary), var(--success));
              display: flex; align-items: center; justify-content: center; font-weight: 700; border: 1px solid rgba(255,255,255,0.08); color: white; }
    .performance-badge { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .badge-excellent { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-good { background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-average { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-poor { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .match-synthesis { background: linear-gradient(135deg, rgba(26, 32, 44, 0.8), rgba(16, 185, 129, 0.1)); border: 1px solid rgba(94,234,212,0.3);
                       border-radius: 16px; padding: 20px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# ------------------------------- HELPERS -------------------------------------
# =============================================================================
LOCAL_FALLBACK = "/mnt/data/Football-Hub-all-in-one.xlsx"
GOOGLE_SHEET_ID = st.secrets.get("GOOGLE_SHEET_ID", "1giSdEgXz3VytLq9Acn9rlQGbUhNAo2bI")

def safe_div(a, b, default=0.0):
    try:
        a = float(a); b = float(b)
        return default if (b == 0 or np.isnan(a) or np.isnan(b)) else a / b
    except Exception:
        return default

def to_num(x) -> pd.Series:
    if isinstance(x, pd.Series):
        s = x.astype(str).str.replace(",", ".", regex=False)
        return pd.to_numeric(s, errors="coerce").fillna(0)
    elif isinstance(x, (list, tuple, np.ndarray)):
        s = pd.Series(x).astype(str).str.replace(",", ".", regex=False)
        return pd.to_numeric(s, errors="coerce").fillna(0)
    else:
        s = pd.Series([str(x)]).str.replace(",", ".", regex=False)
        return pd.to_numeric(s, errors="coerce").fillna(0)

def perf_badge(score: float) -> str:
    if score >= 80:
        return '<span class="performance-badge badge-excellent">Excellent</span>'
    elif score >= 65:
        return '<span class="performance-badge badge-good">Bon</span>'
    elif score >= 50:
        return '<span class="performance-badge badge-average">Moyen</span>'
    else:
        return '<span class="performance-badge badge-poor">À améliorer</span>'

# ---- Canonicalisation colonnes
CANON = {
    "minutes jouee":"minutes", "minutes jouees":"minutes", "minutes":"minutes",
    "buts":"goals", "but":"goals",
    "tir":"shots", "tirs":"shots",
    "tir cadre":"shots_on", "tirs cadres":"shots_on",
    "xg":"xg",
    "passe tentees":"passes_att", "passe tentee":"passes_att", "passe tente":"passes_att",
    "passe completes":"passes_cmp", "passe complete":"passes_cmp",
    "passe progressive":"prog_passes",
    "passe decisive":"key_passes",
    "duel tente":"duels_att", "duel tentee":"duels_att", "duel tentés":"duels_att", "duel tenté":"duels_att",
    "duel gagne":"duels_won", "duel gagné":"duels_won",
    "interception":"interceptions",
    "recuperation du ballon":"recoveries",
    "ballon touche":"touches",
    "ballon touche haute":"touches_high", "ballon touche median":"touches_mid", "ballon touche médian":"touches_mid",
    "ballon touche basse":"touches_low", "ballon touche surface":"touches_box",
    "journee":"matchday", "journée":"matchday",
    "adversaire":"opponent",
    "date":"date",
    "playerid_norm":"player_id",
    "prenom":"first_name", "nom":"last_name", "poste detail":"role_detail", "poste détail":"role_detail",
    "club":"club", "taille":"height", "poids":"weight", "pied":"foot",
    "energie generale":"wel_energy", "fraicheur musculaire":"wel_fresh", "humeur":"wel_mood", "sommeil":"wel_sleep", "intensite douleur":"wel_pain",
}

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii")
    s = s.replace("é","e").replace("è","e").replace("ê","e").replace("à","a").replace("ô","o")
    return s.strip().lower().replace("  "," ")

def canonize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    new_cols = []
    for c in df.columns:
        nc = CANON.get(_norm(c), _norm(c))
        new_cols.append(nc)
    out = df.copy()
    out.columns = new_cols
    return out

# ---- Plotly template
def apply_plotly_template(fig: go.Figure, height=None):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'), hovermode='x unified'
    )
    if height: fig.update_layout(height=height)
    return fig

# ---- Radar
def radar_figure(values, categories, title):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself', name='Performance',
        line=dict(width=2), marker=dict(size=7)
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        showlegend=True, title=title
    )
    return apply_plotly_template(fig, height=520)

# ---- Téléchargement
def _download_gsheets_as_xlsx(file_id: str) -> tuple[bytes, str, int]:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    r = requests.get(url, allow_redirects=True, timeout=30)
    if r.status_code != 200 or r.headers.get("Content-Type","").startswith("text/html"):
        raise RuntimeError(f"Export Google Sheets KO (HTTP {r.status_code}) — vérifier le partage public.")
    content = r.content
    return content, hashlib.md5(content).hexdigest(), len(content)

@st.cache_data(show_spinner=False, ttl=600)
def _parse_excel_bytes(xlsx_bytes: bytes, sig: str) -> dict:
    xl = pd.ExcelFile(io.BytesIO(xlsx_bytes), engine="openpyxl")
    return {name: xl.parse(name).copy(deep=True) for name in xl.sheet_names}

def load_data():
    # 1) Essai Google Sheets
    try:
        xlsx_bytes, sig, size = _download_gsheets_as_xlsx(GOOGLE_SHEET_ID)
        data = _parse_excel_bytes(xlsx_bytes, sig)
        source = "Drive"
    except Exception:
        # 2) Fallback local
        if not Path(LOCAL_FALLBACK).exists():
            st.error("❌ Impossible de charger les données (Drive & fichier local absents).")
            st.stop()
        xl = pd.ExcelFile(LOCAL_FALLBACK, engine="openpyxl")
        data = {name: xl.parse(name).copy(deep=True) for name in xl.sheet_names}
        source = "Local"
    return data, source

# =============================================================================
# ----------------------------- KPIs & BENCHMARKS ------------------------------
# =============================================================================
BENCHMARKS_PAR_POSTE = {
    "attaquant central": {
        'pass_accuracy': 75, 'prog_passes_per_90': 3, 'key_passes_per_match': 0.8,
        'shot_accuracy': 35, 'xg_per_90': 0.4, 'goals_per_xg': 0.9,
        'duel_win_rate': 45, 'interceptions_per_90': 0.8, 'recoveries_per_90': 4,
    },
    "milieu relayeur": {
        'pass_accuracy': 88, 'prog_passes_per_90': 6, 'key_passes_per_match': 0.5,
        'shot_accuracy': 20, 'xg_per_90': 0.1, 'goals_per_xg': 1.5,
        'duel_win_rate': 55, 'interceptions_per_90': 2.5, 'recoveries_per_90': 8,
    },
    "milieu offensif": {
        'pass_accuracy': 82, 'prog_passes_per_90': 8, 'key_passes_per_match': 1.5,
        'shot_accuracy': 30, 'xg_per_90': 0.3, 'goals_per_xg': 1.1,
        'duel_win_rate': 50, 'interceptions_per_90': 1.5, 'recoveries_per_90': 6,
    },
    "defenseur axial": {
        'pass_accuracy': 85, 'prog_passes_per_90': 4, 'key_passes_per_match': 0.2,
        'shot_accuracy': 15, 'xg_per_90': 0.05, 'goals_per_xg': 2.0,
        'duel_win_rate': 60, 'interceptions_per_90': 3.0, 'recoveries_per_90': 7,
    },
    "defaut": {
        'pass_accuracy': 80, 'prog_passes_per_90': 5, 'key_passes_per_match': 1.0,
        'shot_accuracy': 30, 'xg_per_90': 0.2, 'goals_per_xg': 1.0,
        'duel_win_rate': 50, 'interceptions_per_90': 2.0, 'recoveries_per_90': 6,
    }
}

KPI_ORDER = [
    'pass_accuracy','prog_passes_per_90','key_passes_per_match',
    'shot_accuracy','xg_per_90','goals_per_xg',
    'duel_win_rate','interceptions_per_90','recoveries_per_90'
]
KPI_NAMES = [
    'Précision Passes','Passes Progressives','Passes Décisives',
    'Précision Tirs','xG/90','Efficacité',
    'Duels Gagnés %','Interceptions/90','Récupérations/90'
]

def infer_benchmarks(role_detail: str):
    role = _norm(role_detail or "").lower()
    return BENCHMARKS_PAR_POSTE.get(role, BENCHMARKS_PAR_POSTE["defaut"])

def calculate_kpis(data: pd.DataFrame, total_min: float, total_matches: int, role_detail: str = None):
    # agrégats
    passes_att = to_num(data.get("passes_att", 0)).sum()
    passes_cmp = to_num(data.get("passes_cmp", 0)).sum()
    prog_passes = to_num(data.get("prog_passes", 0)).sum()
    key_passes = to_num(data.get("key_passes", 0)).sum()
    shots = to_num(data.get("shots", 0)).sum()
    shots_on = to_num(data.get("shots_on", 0)).sum()
    xg = to_num(data.get("xg", 0)).sum()
    goals = to_num(data.get("goals", 0)).sum()
    duels_att = to_num(data.get("duels_att", 0)).sum()
    duels_won = to_num(data.get("duels_won", 0)).sum()
    interceptions = to_num(data.get("interceptions", 0)).sum()
    recoveries = to_num(data.get("recoveries", 0)).sum()

    # principaux
    pass_accuracy = safe_div(passes_cmp*100, passes_att)
    prog_passes_per_90 = safe_div(prog_passes*90, total_min)
    key_passes_per_match = safe_div(key_passes, total_matches)
    shot_accuracy = safe_div(shots_on*100, shots)
    xg_per_90 = safe_div(xg*90, total_min)
    goals_per_xg = safe_div(goals, xg)
    duel_win_rate = safe_div(duels_won*100, duels_att)
    interceptions_per_90 = safe_div(interceptions*90, total_min)
    recoveries_per_90 = safe_div(recoveries*90, total_min)

    # enrichis
    xg_per_shot = safe_div(xg, shots)
    finishing_delta = goals - xg
    shot_involvement_per_90 = safe_div((shots + key_passes)*90, total_min)

    # spatial
    touches_high = to_num(data.get("touches_high", 0)).sum()
    touches_mid  = to_num(data.get("touches_mid", 0)).sum()
    touches_low  = to_num(data.get("touches_low", 0)).sum()
    touches_box  = to_num(data.get("touches_box", 0)).sum()
    tot_touches = max(touches_high + touches_mid + touches_low, 1)
    touches_high_pct = touches_high / tot_touches * 100
    touches_mid_pct  = touches_mid  / tot_touches * 100
    touches_low_pct  = touches_low  / tot_touches * 100
    box_touch_rate   = touches_box / tot_touches * 100

    # PAdj très simple : rapporté à l'exposition (duels subis = duels_att)
    exposure = max(duels_att, 1)
    interceptions_padj = interceptions / exposure * 10
    recoveries_padj    = recoveries / exposure * 10

    kpis = {
        'pass_accuracy': pass_accuracy,
        'prog_passes_per_90': prog_passes_per_90,
        'key_passes_per_match': key_passes_per_match,
        'shot_accuracy': shot_accuracy,
        'xg_per_90': xg_per_90,
        'goals_per_xg': goals_per_xg,
        'duel_win_rate': duel_win_rate,
        'interceptions_per_90': interceptions_per_90,
        'recoveries_per_90': recoveries_per_90,

        # enrichis
        'xg_per_shot': xg_per_shot,
        'finishing_delta': finishing_delta,
        'shot_involvement_per_90': shot_involvement_per_90,

        # spatial
        'touches_high_pct': touches_high_pct,
        'touches_mid_pct' : touches_mid_pct,
        'touches_low_pct' : touches_low_pct,
        'box_touch_rate'  : box_touch_rate,

        # padj
        'interceptions_padj': interceptions_padj,
        'recoveries_padj': recoveries_padj,
    }
    kpis['benchmarks'] = infer_benchmarks(role_detail)
    return kpis

def performance_score(df: pd.DataFrame) -> float:
    if df is None or df.empty: return 0.0
    passes_att = to_num(df.get("passes_att", 0)).sum()
    passes_cmp = to_num(df.get("passes_cmp", 0)).sum()
    pass_eff = safe_div(passes_cmp*100, passes_att)

    duels_att = to_num(df.get("duels_att", 0)).sum()
    duels_won = to_num(df.get("duels_won", 0)).sum()
    duel_eff = safe_div(duels_won*100, duels_att)

    goals = to_num(df.get("goals", 0)).sum()
    shots = to_num(df.get("shots", 0)).sum()
    xg = to_num(df.get("xg", 0)).sum()
    att_score = (goals * 10) + (shots * 2) + (xg * 5)

    interceptions = to_num(df.get("interceptions", 0)).sum()
    recoveries = to_num(df.get("recoveries", 0)).sum()
    def_score = (interceptions * 3) + (recoveries * 2)

    touches = to_num(df.get("touches", 0)).sum()
    ball_retention = safe_div(touches, len(df)) if len(df) else 0

    weights = {'passing':0.25,'duel':0.20,'attack':0.25,'defense':0.20,'retention':0.10}
    final_score = (pass_eff*weights['passing'] +
                   duel_eff*weights['duel'] +
                   min(att_score,100)*weights['attack'] +
                   min(def_score,100)*weights['defense'] +
                   min(ball_retention,100)*weights['retention'])
    return float(min(final_score, 100))

# =============================================================================
# ------------------------------ CHARGEMENT DATA -------------------------------
# =============================================================================
with st.sidebar:
    if st.button("🔄 Recharger les données", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

data, data_source = load_data()
df_players = canonize_df(data.get("Joueur") or data.get("joueur") or pd.DataFrame())
df_match   = canonize_df(data.get("Match")  or data.get("match")  or pd.DataFrame())
df_well    = canonize_df(data.get("Wellness") or data.get("wellness") or pd.DataFrame())

# PlayerID normalisé
for df in (df_players, df_match, df_well):
    if not df.empty:
        if "playerid" in df.columns and "player_id" not in df.columns:
            df["player_id"] = df["playerid"].astype(str).str.strip()
        elif "player_id" in df.columns:
            df["player_id"] = df["player_id"].astype(str).str.strip()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

# =============================================================================
# ----------------------------- SIDEBAR & CONTROLS -----------------------------
# =============================================================================
st.sidebar.markdown("### 🎯 Paramètres d’analyse")
player_map = {}
if not df_players.empty and {"player_id","first_name","last_name"}.issubset(df_players.columns):
    for _, r in df_players.iterrows():
        display = f"{r.get('first_name','')} {r.get('last_name','')} (#{str(r.get('player_id'))})"
        player_map[display] = str(r.get("player_id"))
elif not df_match.empty and "player_id" in df_match.columns:
    for pid in sorted(df_match["player_id"].dropna().astype(str).unique()):
        player_map[pid] = pid

sel_display = st.sidebar.selectbox("🏃 Sélection joueur", list(player_map.keys()) if player_map else [])
player_id = player_map.get(sel_display) if player_map else None

show_predictions = st.sidebar.checkbox("📈 Afficher les prédictions", value=True)
compare_mode = st.sidebar.checkbox("🔄 Mode comparaison", value=False)
advanced_metrics = st.sidebar.checkbox("📊 Métriques avancées", value=True)

compare_player_id = None
if compare_mode and len(player_map) > 1:
    available = [k for k in player_map.keys() if k != sel_display]
    compare_player = st.sidebar.selectbox("👥 Comparer avec", available)
    compare_player_id = player_map.get(compare_player)

st.sidebar.info(f"Source données : **{data_source}**")

# =============================================================================
# ---------------------------------- TABS -------------------------------------
# =============================================================================
tabs = st.tabs(["🏠 Dashboard", "📊 Performance", "📈 Projections", "🩺 Wellness", "🔍 Analyse", "📄 Données"])

# =============================================================================
# ------------------------------- DASHBOARD -----------------------------------
# =============================================================================
with tabs[0]:
    st.markdown('<div class="hero"><span class="pill">🎯 Dashboard de Performance Joueur</span></div>', unsafe_allow_html=True)
    st.write("")

    if player_id and not df_match.empty:
        dm = df_match[df_match["player_id"] == player_id].copy()
        if "date" in dm.columns and dm["date"].notna().any():
            dm = dm.sort_values("date")
        elif "matchday" in dm.columns:
            dm = dm.sort_values("matchday", kind="mergesort")

        col1, col2 = st.columns([1,2], gap="large")
        with col1:
            st.markdown("##### 👤 Profil Joueur")
            role_detail = None
            initials = "?"
            if not df_players.empty:
                p = df_players[df_players["player_id"] == player_id]
                if not p.empty:
                    p = p.iloc[0]
                    initials = (str(p.get("first_name","")[:1]) + str(p.get("last_name","")[:1])).upper()
                    role_detail = p.get("role_detail", p.get("poste", ""))
                    perf_score = performance_score(dm)
                    badge = perf_badge(perf_score)
                    st.markdown(
                        f"""
                        <div class="glass">
                          <div style="display:flex; gap:12px; align-items:center; margin-bottom:16px;">
                            <div class="avatar">{initials}</div>
                            <div>
                              <div style="font-size:18px; font-weight:600; margin-bottom:4px;">{p.get('first_name','')} {p.get('last_name','')}</div>
                              <div style="color: var(--muted); font-size:14px;">{role_detail} • {p.get('club','')}</div>
                            </div>
                          </div>
                          <div style="margin-bottom:12px;">{badge}</div>
                          <div class="divider"></div>
                          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                            <div class="metric-card"><h3>Score Global</h3><div class="value" style="color:{'#10b981' if perf_score>=70 else '#f59e0b' if perf_score>=50 else '#ef4444'};">{perf_score:.1f}</div></div>
                            <div class="metric-card"><h3>Taille</h3><div class="value">{p.get('height','')} cm</div></div>
                            <div class="metric-card"><h3>Poids</h3><div class="value">{p.get('weight','')} kg</div></div>
                            <div class="metric-card"><h3>Pied Fort</h3><div class="value">{p.get('foot','')}</div></div>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                role_detail = ""
                perf_score = performance_score(dm)
                st.caption("Profil joueur indisponible — affichage minimal.")

        with col2:
            st.markdown("##### 📊 KPIs Saison")
            total_minutes = float(to_num(dm.get("minutes", 0)).sum())
            total_matches = int(len(dm))
            k = calculate_kpis(dm, total_minutes, total_matches, role_detail)

            cols = st.columns(4)
            cols[0].markdown(f"""<div class="metric-card"><h3>xG/90</h3><div class="value" style="color:{'#10b981' if k['xg_per_90']>0.5 else '#f59e0b' if k['xg_per_90']>0.3 else '#ef4444'};">{k['xg_per_90']:.2f}</div></div>""", unsafe_allow_html=True)
            cols[1].markdown(f"""<div class="metric-card"><h3>Précision</h3><div class="value" style="color:{'#10b981' if k['pass_accuracy']>80 else '#f59e0b' if k['pass_accuracy']>70 else '#ef4444'};">{k['pass_accuracy']:.1f}%</div></div>""", unsafe_allow_html=True)
            cols[2].markdown(f"""<div class="metric-card"><h3>Duels</h3><div class="value" style="color:{'#10b981' if k['duel_win_rate']>55 else '#f59e0b' if k['duel_win_rate']>50 else '#ef4444'};">{k['duel_win_rate']:.1f}%</div></div>""", unsafe_allow_html=True)
            cols[3].markdown(f"""<div class="metric-card"><h3>Δ Finition</h3><div class="value" style="color:{'#10b981' if k['finishing_delta']>=0 else '#ef4444'};">{k['finishing_delta']:.2f}</div></div>""", unsafe_allow_html=True)

            # Radar Tactique
            st.markdown("##### 🕸️ Radar de Performance Tactique")
            radar_categories = [
                'Précision Passes','Passes Prog./90','Passes Décisives',
                'Précision Tirs','xG/90','Efficacité',
                'Duels Gagnés','Interceptions/90','Récupérations/90'
            ]
            radar_values = [
                min(k['pass_accuracy'], 100),
                min(k['prog_passes_per_90']*10, 100),
                min(k['key_passes_per_match']*50, 100),
                min(k['shot_accuracy'], 100),
                min(k['xg_per_90']*150, 100),
                min(k['goals_per_xg']*70, 100),
                min(k['duel_win_rate'], 100),
                min(k['interceptions_per_90']*30, 100),
                min(k['recoveries_per_90']*10, 100)
            ]
            st.plotly_chart(radar_figure(radar_values, radar_categories, "Performance Tactique"), use_container_width=True)

        # Synthèse dernier match
        st.markdown("##### 🎯 Synthèse Dernier Match")
        if not dm.empty:
            last = dm.iloc[-1]
            j_day = last.get("matchday", "N/A")
            opponent = last.get("opponent", "N/A")
            st.markdown(f"""<div class="match-synthesis"><h3 style="margin:0 0 10px 0; color:#5eead4;">Match J{j_day} • {opponent}</h3></div>""", unsafe_allow_html=True)

            match_df = pd.DataFrame([last])
            minutes_last = float(to_num(last.get("minutes", 0)).sum())
            k_last = calculate_kpis(match_df, minutes_last, 1, role_detail)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Précision Passes", f"{k_last['pass_accuracy']:.1f}%")
            c2.metric("xG/90", f"{k_last['xg_per_90']:.2f}")
            c3.metric("Duels Gagnés", f"{k_last['duel_win_rate']:.1f}%")
            c4.metric("Tirs cadrés", f"{int(to_num(match_df.get('shots_on',0)).sum())}")

# =============================================================================
# ------------------------------ PERFORMANCE ----------------------------------
# =============================================================================
with tabs[1]:
    st.markdown('<div class="hero"><span class="pill">📊 Performance — Distribution / Offense / Défense</span></div>', unsafe_allow_html=True)
    st.write("")

    if player_id and not df_match.empty:
        dm = df_match[df_match["player_id"] == player_id].copy()
        if "date" in dm.columns and dm["date"].notna().any():
            dm = dm.sort_values("date")
        else:
            dm = dm.sort_values("matchday", kind="mergesort")

        analysis_mode = st.radio("Mode d'analyse", ["📊 Vue saison complète", "🎯 Match spécifique"], horizontal=True, key="perf_mode")
        if analysis_mode == "🎯 Match spécifique" and {"matchday","opponent"}.issubset(dm.columns):
            pairs = dm[["matchday","opponent"]].dropna().drop_duplicates().sort_values(["matchday","opponent"])
            j_sel = st.selectbox("Journée", pairs["matchday"].unique().tolist(), key="j_sel_perf")
            adv_sel = st.selectbox("Adversaire", pairs.loc[pairs["matchday"]==j_sel,"opponent"].unique().tolist(), key="adv_sel_perf")
            df_scope = dm[(dm["matchday"]==j_sel) & (dm["opponent"]==adv_sel)].copy()
            total_matches = 1
        else:
            df_scope = dm.copy()
            total_matches = len(df_scope)

        role_detail = ""
        if not df_players.empty:
            r = df_players[df_players["player_id"] == player_id]
            if not r.empty:
                role_detail = r.iloc[0].get("role_detail","")

        total_minutes = float(to_num(df_scope.get("minutes", 0)).sum())
        k = calculate_kpis(df_scope, total_minutes, total_matches, role_detail)

        # --- Cartes KPI vs Benchmarks
        st.markdown("#### 🎯 KPIs vs Benchmarks")
        grid = st.columns(3)
        cards = [
            ("Précision Passes", k['pass_accuracy'], k['benchmarks']['pass_accuracy'], "%"),
            ("Passes Prog./90", k['prog_passes_per_90'], k['benchmarks']['prog_passes_per_90'], ""),
            ("Passes Décisives/Match", k['key_passes_per_match'], k['benchmarks']['key_passes_per_match'], ""),
            ("Précision Tirs", k['shot_accuracy'], k['benchmarks']['shot_accuracy'], "%"),
            ("xG/90", k['xg_per_90'], k['benchmarks']['xg_per_90'], ""),
            ("Finition (Buts/xG)", k['goals_per_xg'], k['benchmarks']['goals_per_xg'], ""),
            ("Duels Gagnés %", k['duel_win_rate'], k['benchmarks']['duel_win_rate'], "%"),
            ("Interceptions/90", k['interceptions_per_90'], k['benchmarks']['interceptions_per_90'], ""),
            ("Récupérations/90", k['recoveries_per_90'], k['benchmarks']['recoveries_per_90'], ""),
        ]
        for i, (name, val, bmk, suf) in enumerate(cards):
            with grid[i%3]:
                color = "#10b981" if val>=bmk else "#f59e0b" if val>=0.8*bmk else "#ef4444"
                st.markdown(f"""<div class="metric-card"><h3>{name}</h3><div class="value" style="color:{color};">{val:.2f}{suf}</div><div style="font-size:12px;color:var(--muted);">Benchmark: {bmk}{suf}</div></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📊 Synthèse visuelle des KPIs")
        kpi_values = [k[x] for x in KPI_ORDER]
        bmk_values = [k['benchmarks'][x] for x in KPI_ORDER]
        fig_syn = go.Figure()
        fig_syn.add_trace(go.Bar(y=KPI_NAMES, x=kpi_values, orientation='h', name='Performance',
                                 text=[f"{v:.2f}" for v in kpi_values], textposition='auto'))
        for i, b in enumerate(bmk_values):
            fig_syn.add_shape(type="line", line=dict(width=2, dash="dot"),
                              y0=i-0.4, y1=i+0.4, x0=b, x1=b)
        fig_syn.update_layout(title="KPIs vs Benchmarks (poste)", xaxis_title="Valeur", yaxis_title="")
        st.plotly_chart(apply_plotly_template(fig_syn, 600), use_container_width=True)

        # ------ Nouvelles visualisations
        st.markdown("---")
        st.markdown("### 🔥 Nouvelles visualisations")

        # A) Funnel de création (Prog → KeyPass → Shots) par 90
        prog90 = k['prog_passes_per_90']
        kp90 = safe_div(to_num(df_scope.get("key_passes",0)).sum()*90, total_minutes)
        shots90 = safe_div(to_num(df_scope.get("shots",0)).sum()*90, total_minutes)
        funnel_df = pd.DataFrame({
            "Étape": ["Passes Progressives", "Passes Décisives", "Tirs"],
            "/90": [prog90, kp90, shots90]
        })
        fig_funnel = px.funnel(funnel_df, x="/90", y="Étape", title="Funnel de Création /90 (Prog → KP → Shots)")
        st.plotly_chart(apply_plotly_template(fig_funnel), use_container_width=True)

        # B) Quadrants Volume vs Qualité (shots/90 vs xG/shot)
        per_match_minutes = to_num(df_scope.get("minutes",0)).replace(0, np.nan).fillna(90)
        shots_per_match = to_num(df_scope.get("shots",0))
        xg_per_match = to_num(df_scope.get("xg",0))
        shots_per_90_series = shots_per_match*90/per_match_minutes
        xg_per_shot_series = xg_per_match / shots_per_match.replace(0,np.nan)
        qdf = pd.DataFrame({
            "match_idx": range(1, len(df_scope)+1),
            "shots_per_90": shots_per_90_series.fillna(0),
            "xg_per_shot": xg_per_shot_series.fillna(0)
        })
        fig_quad = px.scatter(qdf, x="shots_per_90", y="xg_per_shot", title="Quadrants : Volume vs Qualité (par match)", trendline="ols")
        fig_quad.add_vline(x=qdf["shots_per_90"].median(), line_dash="dot")
        fig_quad.add_hline(y=qdf["xg_per_shot"].median(), line_dash="dot")
        st.plotly_chart(apply_plotly_template(fig_quad, 520), use_container_width=True)

        # C) Waterfall Finishing Luck (Buts - xG) par match
        goals_series = to_num(df_scope.get("goals",0))
        delta = goals_series - xg_per_match
        wf_df = pd.DataFrame({"Match": list(range(1,len(delta)+1)), "Δ Buts-xG": delta})
        fig_wf = go.Figure(go.Waterfall(x=wf_df["Match"], measure=["relative"]*len(wf_df),
                                        y=wf_df["Δ Buts-xG"], text=[f"{v:.2f}" for v in wf_df["Δ Buts-xG"]],
                                        connector={"line":{"width":1}}))
        fig_wf.update_layout(title="Waterfall — Sur/Sous-performance (Buts - xG)")
        st.plotly_chart(apply_plotly_template(fig_wf, 520), use_container_width=True)

        # D) Match Flow (xG cumulé & Buts cumulés)
        xg_cum = xg_per_match.cumsum()
        goals_cum = goals_series.cumsum()
        fig_flow = go.Figure()
        fig_flow.add_trace(go.Scatter(x=list(range(1,len(df_scope)+1)), y=xg_cum, mode="lines+markers", name="xG cumulé"))
        fig_flow.add_trace(go.Scatter(x=list(range(1,len(df_scope)+1)), y=goals_cum, mode="lines+markers", name="Buts cumulés"))
        fig_flow.update_layout(title="Match Flow — xG vs Buts (cumulés)", xaxis_title="Match #")
        st.plotly_chart(apply_plotly_template(fig_flow, 520), use_container_width=True)

        # E) Ternary des touches (profil de zones)
        if {"touches_high","touches_mid","touches_low"}.issubset(df_scope.columns) and df_scope.shape[0] >= 3:
            td = pd.DataFrame({
                "A (Haut)": to_num(df_scope["touches_high"]),
                "B (Médian)": to_num(df_scope["touches_mid"]),
                "C (Bas)": to_num(df_scope["touches_low"]),
                "Match": list(range(1,len(df_scope)+1))
            })
            s = td[["A (Haut)","B (Médian)","C (Bas)"]].sum(axis=1).replace(0,np.nan)
            td["a"] = td["A (Haut)"]/s*100; td["b"] = td["B (Médian)"]/s*100; td["c"] = td["C (Bas)"]/s*100
            fig_tern = px.scatter_ternary(td, a="a", b="b", c="c", hover_name="Match",
                                          title="Répartition des touches (Haut / Médian / Bas) — par match")
            st.plotly_chart(apply_plotly_template(fig_tern, 520), use_container_width=True)

# =============================================================================
# ------------------------------- PROJECTIONS ---------------------------------
# =============================================================================
with tabs[2]:
    st.markdown('<div class="hero"><span class="pill">📈 Projections — régression lissée</span></div>', unsafe_allow_html=True)
    st.write("")

    if show_predictions and player_id and not df_match.empty:
        dm = df_match[df_match["player_id"] == player_id].copy()
        if "date" in dm.columns and dm["date"].notna().any():
            dm = dm.sort_values("date")
        else:
            dm = dm.sort_values("matchday", kind="mergesort")
        if len(dm) >= 5:
            dm_ml = dm.reset_index(drop=True)
            dm_ml['match_number'] = np.arange(1, len(dm_ml)+1)

            # KPI au choix
            kpi_options = {
                'Précision Passes (%)': ('pass_accuracy', "%"),
                'xG/90': ('xg_per_90', ""),
                'Duels Gagnés (%)': ('duel_win_rate', "%"),
                'Passes Progressives /90': ('prog_passes_per_90', ""),
                'Interceptions /90': ('interceptions_per_90', "")
            }
            chosen = st.selectbox("KPI à prédire", list(kpi_options.keys()))
            chosen_key, suf = kpi_options[chosen]

            # Historique per-match : recalcul par fenêtre glissante 1 match
            hist_vals = []
            for i in range(len(dm_ml)):
                sl = dm_ml.iloc[:i+1]
                total_min = float(to_num(sl.get("minutes",0)).sum())
                total_matches = len(sl)
                role_detail = ""
                if not df_players.empty:
                    rp = df_players[df_players["player_id"] == player_id]
                    if not rp.empty: role_detail = rp.iloc[0].get("role_detail","")
                k = calculate_kpis(sl, total_min, total_matches, role_detail)
                hist_vals.append(k[chosen_key])

            y = pd.Series(hist_vals, dtype=float)
            x = dm_ml['match_number'].values

            # Lissage EWMA
            y_smooth = y.ewm(alpha=0.3, adjust=False).mean()

            # Rupture simple : si variation EWMA > 2*std residu, on recalcule slope sur 40% récents
            resid = y - y_smooth
            thr = 2*resid.std(ddof=0)
            last_jump = np.where(resid.abs().values > thr)[0]
            start_idx = int(0.6*len(x)) if len(last_jump)==0 else max(last_jump[-1], int(0.6*len(x)))

            X_fit = x[start_idx:]
            Y_fit = y_smooth.iloc[start_idx:].values
            if len(X_fit) < 2:
                X_fit, Y_fit = x, y_smooth.values

            # Régression manuelle
            n = len(X_fit)
            sx, sy = X_fit.sum(), Y_fit.sum()
            sxy = (X_fit*Y_fit).sum()
            sx2 = (X_fit**2).sum()
            slope = (n*sxy - sx*sy) / (n*sx2 - sx**2) if (n*sx2 - sx**2) != 0 else 0
            intercept = (sy - slope*sx) / n if n else 0

            periods_ahead = st.slider("Nombre de matchs à prédire", 1, 10, 5)
            all_x = np.arange(1, len(x)+periods_ahead+1)
            y_pred = slope*all_x + intercept

            mae = np.mean(np.abs(Y_fit - (slope*X_fit + intercept)))
            ci = 1.96 * mae

            fig_ml = go.Figure()
            fig_ml.add_trace(go.Scatter(x=x, y=y, mode="markers+lines", name="Valeurs (brut)"))
            fig_ml.add_trace(go.Scatter(x=x, y=y_smooth, mode="lines", name="EWMA (α=0.3)", line=dict(dash="solid")))
            fig_ml.add_trace(go.Scatter(x=all_x, y=y_pred, mode="lines", name="Régression lissée", line=dict(dash="dash")))
            fig_ml.add_trace(go.Scatter(x=all_x, y=y_pred+ci, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig_ml.add_trace(go.Scatter(x=all_x, y=y_pred-ci, mode="lines", fill='tonexty', fillcolor='rgba(16,185,129,0.2)', line=dict(width=0), name='IC 95%', hoverinfo="skip"))
            fig_ml.update_layout(title=f"Prédiction — {chosen}", xaxis_title="Match #", yaxis_title=chosen)
            st.plotly_chart(apply_plotly_template(fig_ml, 560), use_container_width=True)

            r2 = 0.0
            y_fit_hat = slope*X_fit + intercept
            sst = ((Y_fit - Y_fit.mean())**2).sum()
            ssr = ((Y_fit - y_fit_hat)**2).sum()
            if sst > 0: r2 = 1 - ssr/sst

            c1, c2, c3 = st.columns(3)
            c1.metric("📈 Pente", f"{slope:.3f}", "par match")
            c2.metric("🎯 R² (segment)", f"{r2:.2f}")
            c3.metric("📏 MAE", f"{mae:.2f}{suf}")

# =============================================================================
# -------------------------------- WELLNESS -----------------------------------
# =============================================================================
with tabs[3]:
    st.markdown('<div class="hero"><span class="pill">🩺 Wellness & Corrélation Performance</span></div>', unsafe_allow_html=True)
    st.write("")
    if player_id and not df_well.empty and "player_id" in df_well.columns:
        dw = df_well[df_well["player_id"] == player_id].copy()
        if not dw.empty and "date" in dw.columns:
            dw = dw.sort_values("date").tail(60)
            metrics = [c for c in ["wel_energy","wel_fresh","wel_mood","wel_sleep","wel_pain"] if c in dw.columns]
            labels = {"wel_energy":"Énergie","wel_fresh":"Fraîcheur","wel_mood":"Humeur","wel_sleep":"Sommeil","wel_pain":"Douleur"}

            if metrics:
                sel = st.multiselect("Indicateurs à afficher", options=metrics, default=metrics, format_func=lambda x: labels.get(x,x))
                for m in sel:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=dw["date"], y=dw[m], mode="lines+markers", name=f"{labels.get(m,m)}"))
                    ma7 = dw[m].rolling(7, min_periods=1).mean()
                    fig_m.add_trace(go.Scatter(x=dw["date"], y=ma7, mode="lines", name=f"{labels.get(m,m)} (MA7)", line=dict(dash="solid")))
                    fig_m.update_layout(title=f"Tendance {labels.get(m,m)} — 60 jours", xaxis_title="Date", yaxis_title="Score (0-10)", yaxis=dict(range=[0,10]))
                    st.plotly_chart(apply_plotly_template(fig_m, 420), use_container_width=True)

                # Heatmap corr Wellness ↔ KPIs (sur derniers matchs avec fenêtre ±3j)
                st.markdown("---")
                st.markdown("#### 🔗 Heatmap Corrélation Wellness ↔ KPIs")
                if not df_match.empty and "date" in df_match.columns:
                    dm_p = df_match[df_match["player_id"] == player_id].copy()
                    dm_p["date"] = pd.to_datetime(dm_p["date"], errors="coerce")
                    rows = []
                    for _, mr in dm_p.iterrows():
                        md = mr["date"]
                        if pd.isna(md): continue
                        wwin = dw[(dw["date"] >= md - timedelta(days=3)) & (dw["date"] <= md)]
                        if wwin.empty: continue
                        avg_well = {m: wwin[m].mean() for m in sel if m in wwin}
                        # per-match KPIs
                        mdf = pd.DataFrame([mr])
                        mins = float(to_num(mdf.get("minutes",0)).sum())
                        k_match = calculate_kpis(mdf, mins, 1, "")
                        rows.append({**avg_well, **{kk:k_match[kk] for kk in ["xg_per_90","duel_win_rate","pass_accuracy","shot_accuracy"]}})
                    if len(rows) >= 3:
                        corr_df = pd.DataFrame(rows)
                        wel_cols = [c for c in sel if c in corr_df.columns]
                        kpi_cols = ["xg_per_90","duel_win_rate","pass_accuracy","shot_accuracy"]
                        # matrice corr
                        M = corr_df[wel_cols + kpi_cols].corr().loc[wel_cols, kpi_cols]
                        fig_heat = px.imshow(M, text_auto=".2f", aspect="auto", title="Corrélation (r)")
                        st.plotly_chart(apply_plotly_template(fig_heat, 520), use_container_width=True)

# =============================================================================
# ------------------------------ ANALYSE COMPAREE ------------------------------
# =============================================================================
with tabs[4]:
    st.markdown('<div class="hero"><span class="pill">🔍 Analyse Comparative Avancée</span></div>', unsafe_allow_html=True)
    st.write("")
    if compare_mode and player_id and compare_player_id:
        dm1 = df_match[df_match["player_id"] == player_id].copy()
        dm2 = df_match[df_match["player_id"] == compare_player_id].copy()
        if "date" in dm1.columns: dm1 = dm1.sort_values("date")
        if "date" in dm2.columns: dm2 = dm2.sort_values("date")

        def player_name(pid):
            if not df_players.empty:
                r = df_players[df_players["player_id"] == pid]
                if not r.empty: return f"{r.iloc[0].get('first_name','')} {r.iloc[0].get('last_name','')}"
            return str(pid)

        p1_name = player_name(player_id)
        p2_name = player_name(compare_player_id)

        if not dm1.empty and not dm2.empty:
            st.markdown(f"#### ⚖️ {p1_name} vs {p2_name}")

            def quick_stats(dm):
                return dict(
                    matches=len(dm),
                    minutes=int(to_num(dm.get("minutes",0)).sum()),
                    goals=int(to_num(dm.get("goals",0)).sum()),
                    xg=float(to_num(dm.get("xg",0)).sum()),
                    passes=int(to_num(dm.get("passes_cmp",0)).sum()),
                )
            s1, s2 = quick_stats(dm1), quick_stats(dm2)
            kpi_cols = st.columns(5)
            kpi_cols[0].metric("Matchs Joués", f"{s1['matches']}", f"{s1['matches']-s2['matches']:+d} vs {p2_name}")
            kpi_cols[1].metric("Minutes", f"{s1['minutes']}", f"{s1['minutes']-s2['minutes']:+d}")
            kpi_cols[2].metric("Buts", f"{s1['goals']}", f"{s1['goals']-s2['goals']:+d}")
            kpi_cols[3].metric("xG", f"{s1['xg']:.1f}", f"{s1['xg']-s2['xg']:+.1f}")
            kpi_cols[4].metric("Passes", f"{s1['passes']}", f"{s1['passes']-s2['passes']:+d}")

            # Radar overlay (même figure)
            def radar_metrics(dm):
                m = len(dm) if len(dm)>0 else 1
                pa = safe_div(to_num(dm.get("passes_cmp",0)).sum()*100, to_num(dm.get("passes_att",0)).sum())
                duel = safe_div(to_num(dm.get("duels_won",0)).sum()*100, to_num(dm.get("duels_att",0)).sum())
                sh_acc = safe_div(to_num(dm.get("shots_on",0)).sum()*100, to_num(dm.get("shots",0)).sum())
                xg_match = safe_div(to_num(dm.get("xg",0)).sum(), m)
                goals_match = safe_div(to_num(dm.get("goals",0)).sum(), m)
                minutes_match = safe_div(to_num(dm.get("minutes",0)).sum(), m)
                playtime_pct = min(minutes_match/90*100, 100)
                return [
                    min(pa,100), min(duel,100), min(sh_acc,100),
                    min(xg_match*20, 100), min(goals_match*50, 100), playtime_pct
                ]
            radar_categories = ['Passes','Duels','Tirs','xG/Match','Buts/Match','Temps de Jeu']
            p1_r = radar_metrics(dm1); p2_r = radar_metrics(dm2)
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=p1_r, theta=radar_categories, fill='toself', name=p1_name))
            fig_r.add_trace(go.Scatterpolar(r=p2_r, theta=radar_categories, fill='toself', name=p2_name, opacity=0.6))
            fig_r.update_layout(title="Radar comparatif")
            st.plotly_chart(apply_plotly_template(fig_r, 520), use_container_width=True)

            # Évolution comparée cumulée
            metric = st.selectbox("Métrique à comparer", ["goals","xg","passes_cmp","shots","duels_won"], index=0,
                                  format_func=lambda x: {"goals":"Buts","xg":"xG","passes_cmp":"Passes compl.","shots":"Tirs","duels_won":"Duels gagnés"}[x])
            fig_ev = go.Figure()
            fig_ev.add_trace(go.Scatter(x=list(range(1,len(dm1)+1)), y=to_num(dm1.get(metric,0)).cumsum(), mode="lines+markers", name=p1_name))
            fig_ev.add_trace(go.Scatter(x=list(range(1,len(dm2)+1)), y=to_num(dm2.get(metric,0)).cumsum(), mode="lines+markers", name=p2_name))
            fig_ev.update_layout(title=f"Évolution Cumulative — {metric}", xaxis_title="Match #")
            st.plotly_chart(apply_plotly_template(fig_ev, 520), use_container_width=True)

# =============================================================================
# ---------------------------------- DONNEES ----------------------------------
# =============================================================================
with tabs[5]:
    st.markdown("#### 📄 Données Brutes & Exports")
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Joueurs", df_players.shape[0])
    col2.metric("⚽ Matchs", df_match.shape[0])
    col3.metric("🩺 Wellness", df_well.shape[0])

    data_view = st.selectbox("Vue des données", ["Joueurs","Matchs","Wellness","Statistiques agrégées"], index=0)

    if data_view == "Joueurs":
        st.dataframe(df_players, use_container_width=True)
    elif data_view == "Matchs":
        if player_id: st.dataframe(df_match[df_match["player_id"]==player_id], use_container_width=True)
        else: st.dataframe(df_match.head(100), use_container_width=True)
    elif data_view == "Wellness":
        if player_id: st.dataframe(df_well[df_well["player_id"]==player_id], use_container_width=True)
        else: st.dataframe(df_well.head(100), use_container_width=True)
    else:
        # Agrégation par joueur + percentiles intra-effectif (ex. sur xG/90)
        agg = []
        if not df_match.empty and "player_id" in df_match.columns:
            for pid, g in df_match.groupby("player_id"):
                minutes = float(to_num(g.get("minutes",0)).sum())
                matches = int(len(g))
                xg = float(to_num(g.get("xg",0)).sum())
                goals = int(to_num(g.get("goals",0)).sum())
                shots = int(to_num(g.get("shots",0)).sum())
                passes = int(to_num(g.get("passes_cmp",0)).sum())
                score = performance_score(g)
                d = dict(player_id=pid, Matchs=matches, Minutes=minutes, Buts=goals, xG=xg, Tirs=shots, Passes=passes, Score=score)
                d["xG/90"] = safe_div(xg*90, minutes)
                d["Buts/Match"] = safe_div(goals, matches)
                agg.append(d)
            stats_df = pd.DataFrame(agg)
            if not stats_df.empty:
                # percentiles sur xG/90
                xg90 = stats_df["xG/90"]
                stats_df["xG/90 pct"] = xg90.rank(pct=True)*100
            st.dataframe(stats_df, use_container_width=True)
            csv = stats_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Télécharger (CSV)", data=csv, file_name=f"football_stats_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

# =============================================================================
# --------------------------------- FOOTER ------------------------------------
# =============================================================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; padding: 20px; color: var(--muted);">
      <p>⚽ <strong>Football Hub Analytics</strong> — Analytics enrichies & visualisations avancées</p>
      <p>Source: Google Drive (fallback local) • Cache TTL 10 min</p>
      <p style="font-size:12px;">Version 3.0 • Canonical Columns • KPIs+ • Radar Overlay • Funnels • EWMA Regression</p>
    </div>
    """,
    unsafe_allow_html=True
)
