import os
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import unicodedata
from datetime import datetime, timedelta
import warnings
import io
import hashlib
import requests
warnings.filterwarnings('ignore')
st.set_page_config(page_title="Football Hub - Analytics", page_icon="⚽", layout="wide")

# --- CANONICALISATION DES COLONNES ---
CANON = {
    "minutes jouees": "minutes", "buts": "goals", "tir": "shots", "tir cadre": "shots_on",
    "xg": "xg", "passe tentees": "passes_att", "passe tentee": "passes_att",
    "passe completes": "passes_cmp", "passe complete": "passes_cmp",
    "passe progressive": "prog_passes", "passe decisive": "key_passes",
    "duel tente": "duels_att", "duel tenté": "duels_att",
    "duel gagne": "duels_won", "duel gagné": "duels_won",
    "interception": "interceptions",
    "recuperation du ballon": "recoveries",
    "ballon touche": "touches", "ballon touche haute": "touches_high",
    "ballon touche median": "touches_mid", "ballon touche basse": "touches_low",
    "ballon touche surface": "touches_box",
    "journee": "matchday", "adversaire": "opponent", "date": "date", "playerid_norm": "player_id",
    "prénom": "prenom", "nom": "nom", "poste détail": "poste_detail", "date de naissance": "date_naissance",
    "taille": "taille", "poids": "poids", "pied": "pied", "club": "club"
}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    s = s.replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("ç", "c")
    return s.strip().lower().replace("  ", " ")

def canonize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cols = [CANON.get(norm(c), norm(c)) for c in df.columns]
    out = df.copy()
    out.columns = cols
    return out

def safe_div(a, b, default=0.0):
    try:
        if pd.isna(a) or pd.isna(b) or b == 0:
            return default
        return float(a) / float(b)
    except:
        return default

# -------------------- STYLE AVANCÉ --------------------
st.markdown(
    """
    <style>
    :root { 
        --bg: #0b1220; 
        --card: #121a2b; 
        --muted: #94a3b8; 
        --text: #e2e8f0; 
        --radius: 16px;
        --primary: #3b82f6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
    }
    .stApp { 
        background: linear-gradient(180deg, #0b1220 0%, #0c1322 100%); 
        color: var(--text); 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .glass { 
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03));
        border: 1px solid rgba(255,255,255,0.08); 
        border-radius: var(--radius); 
        padding: 1rem 1.25rem;
        backdrop-filter: blur(10px);
    }
    .hero { 
        border-radius: 22px; 
        padding: 20px 24px; 
        border: 1px solid rgba(255,255,255,0.10);
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(16, 185, 129, 0.1));
    }
    .pill { 
        display: inline-block; 
        padding: 6px 12px; 
        font-size: 13px; 
        border-radius: 999px;
        background: rgba(94,234,212,0.15); 
        border: 1px solid rgba(94,234,212,0.35);
        font-weight: 500;
    }
    .divider { 
        height: 1px; 
        background: rgba(255,255,255,0.08); 
        margin: 12px 0 16px 0; 
    }
    .metric-card { 
        background: var(--card); 
        border: 1px solid rgba(255,255,255,0.08); 
        border-radius: var(--radius); 
        padding: 16px;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: var(--primary);
        transform: translateY(-2px);
    }
    .metric-card h3 { 
        font-size: 13px; 
        color: var(--muted); 
        margin: 0 0 8px 0; 
        font-weight: 500; 
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card .value { 
        font-size: 24px; 
        font-weight: 700; 
        line-height: 1.2;
    }
    .avatar { 
        width: 54px; 
        height: 54px; 
        border-radius: 12px; 
        background: linear-gradient(135deg, var(--primary), var(--success)); 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        font-weight: 700; 
        border: 1px solid rgba(255,255,255,0.08);
        color: white;
    }
    .performance-badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-excellent { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-good { background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-average { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-poor { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .match-synthesis {
        background: linear-gradient(135deg, rgba(26, 32, 44, 0.8), rgba(16, 185, 129, 0.1));
        border: 1px solid rgba(94,234,212,0.3);
        border-radius: 16px;
        padding: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- HELPERS AVANCÉS --------------------
def get_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0

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

def df_has_cols(df: pd.DataFrame, cols: list) -> bool:
    return all(c in df.columns for c in cols)

def calculate_performance_score(player_data, player_poste="Défaut"):
    if player_data.empty:
        return 0
    
    weights_by_poste = {
        "Attaquant central": {'passing_efficiency': 0.15,'duel_success': 0.15,'attacking_contribution': 0.40,'defensive_contribution': 0.10,'ball_retention': 0.20},
        "Milieu relayeur": {'passing_efficiency': 0.35,'duel_success': 0.25,'attacking_contribution': 0.15,'defensive_contribution': 0.15,'ball_retention': 0.10},
        "Milieu offensif": {'passing_efficiency': 0.25,'duel_success': 0.15,'attacking_contribution': 0.35,'defensive_contribution': 0.10,'ball_retention': 0.15},
        "Défenseur axial": {'passing_efficiency': 0.25,'duel_success': 0.35,'attacking_contribution': 0.05,'defensive_contribution': 0.25,'ball_retention': 0.10},
        "Défaut": {'passing_efficiency': 0.25,'duel_success': 0.20,'attacking_contribution': 0.25,'defensive_contribution': 0.20,'ball_retention': 0.10}
    }
    
    weights = weights_by_poste.get(player_poste, weights_by_poste['Défaut'])
    
    passes_tent = to_num(player_data.get("passes_att", pd.Series([0]))).sum()
    passes_comp = to_num(player_data.get("passes_cmp", pd.Series([0]))).sum()
    passing_eff = safe_div(passes_comp, passes_tent, 0) * 100
    
    duels_tent = to_num(player_data.get("duels_att", pd.Series([0]))).sum()
    duels_gagnes = to_num(player_data.get("duels_won", pd.Series([0]))).sum()
    duel_eff = safe_div(duels_gagnes, duels_tent, 0) * 100
    
    buts = to_num(player_data.get("goals", pd.Series([0]))).sum()
    tirs = to_num(player_data.get("shots", pd.Series([0]))).sum()
    xg = to_num(player_data.get("xg", pd.Series([0]))).sum()
    attacking_score = (buts * 10) + (tirs * 2) + (xg * 5)
    
    interceptions = to_num(player_data.get("interceptions", pd.Series([0]))).sum()
    recoveries = to_num(player_data.get("recoveries", pd.Series([0]))).sum()
    defensive_score = (interceptions * 3) + (recoveries * 2)
    
    touches = to_num(player_data.get("touches", pd.Series([0]))).sum()
    ball_retention_score = safe_div(touches, len(player_data), 0)
    
    final_score = (
        (passing_eff * weights['passing_efficiency']) +
        (duel_eff * weights['duel_success']) +
        (min(attacking_score, 100) * weights['attacking_contribution']) +
        (min(defensive_score, 100) * weights['defensive_contribution']) +
        (min(ball_retention_score, 100) * weights['ball_retention'])
    )
    
    return min(final_score, 100)

def get_performance_badge(score):
    if score >= 80:
        return '<span class="performance-badge badge-excellent">Excellent</span>'
    elif score >= 65:
        return '<span class="performance-badge badge-good">Bon</span>'
    elif score >= 50:
        return '<span class="performance-badge badge-average">Moyen</span>'
    else:
        return '<span class="performance-badge badge-poor">À améliorer</span>'

def create_radar_chart(data, categories, title="Performance Radar"):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=data,
        theta=categories,
        fill='toself',
        name='Performance',
        line=dict(color='#3b82f6', width=2),
        fillcolor='rgba(59, 130, 246, 0.2)',
        marker=dict(size=8, color='#3b82f6')
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor='rgba(255, 255, 255, 0.2)',
                linecolor='rgba(255, 255, 255, 0.3)'
            ),
            angularaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.2)',
                linecolor='rgba(255, 255, 255, 0.3)'
            ),
            bgcolor='rgba(0, 0, 0, 0)'
        ),
        showlegend=False,
        title=dict(text=title, x=0.5, font=dict(color='#e2e8f0')),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        font=dict(color='#e2e8f0')
    )
    return fig

def predict_performance_trend_manual(x, y, periods_ahead=5):
    if len(x) < 2:
        return None
    n = len(x)
    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.sum(x * y)
    sum_x2 = np.sum(x ** 2)
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
    intercept = (sum_y - slope * sum_x) / n
    future_x = np.arange(len(x) + 1, len(x) + periods_ahead + 1)
    predictions = slope * future_x + intercept
    y_mean = np.mean(y)
    ss_tot = np.sum((y - y_mean) ** 2)
    ss_res = np.sum((y - (slope * x + intercept)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    return {
        'slope': slope,
        'intercept': intercept,
        'predictions': predictions,
        'future_matches': future_x,
        'r_squared': r_squared
    }

# -------------------- BENCHMARKS PAR POSTE DÉTAIL --------------------
BENCHMARKS_PAR_POSTE = {
    "Attaquant central": {
        'pass_accuracy': 75,
        'prog_passes_per_90': 3,
        'key_passes_per_match': 0.8,
        'shot_accuracy': 35,
        'xg_per_90': 0.4,
        'goals_per_xg': 0.9,
        'duel_win_rate': 45,
        'interceptions_per_90': 0.8,
        'recoveries_per_90': 4,
        'xg_per_shot': 0.12,
        'finishing_delta_per_90': 0.0,
        'shot_involvement_per_90': 3.5,
        'interceptions_padj': 1.5,
        'recoveries_padj': 8.0,
        'touches_high_pct': 20,
        'touches_mid_pct': 30,
        'touches_low_pct': 50,
        'box_touch_rate': 15
    },
    "Milieu relayeur": {
        'pass_accuracy': 88,
        'prog_passes_per_90': 6,
        'key_passes_per_match': 0.5,
        'shot_accuracy': 20,
        'xg_per_90': 0.1,
        'goals_per_xg': 1.5,
        'duel_win_rate': 55,
        'interceptions_per_90': 2.5,
        'recoveries_per_90': 8,
        'xg_per_shot': 0.08,
        'finishing_delta_per_90': 0.0,
        'shot_involvement_per_90': 2.0,
        'interceptions_padj': 3.0,
        'recoveries_padj': 12.0,
        'touches_high_pct': 15,
        'touches_mid_pct': 40,
        'touches_low_pct': 45,
        'box_touch_rate': 5
    },
    "Milieu offensif": {
        'pass_accuracy': 82,
        'prog_passes_per_90': 8,
        'key_passes_per_match': 1.5,
        'shot_accuracy': 30,
        'xg_per_90': 0.3,
        'goals_per_xg': 1.1,
        'duel_win_rate': 50,
        'interceptions_per_90': 1.5,
        'recoveries_per_90': 6,
        'xg_per_shot': 0.10,
        'finishing_delta_per_90': 0.0,
        'shot_involvement_per_90': 4.5,
        'interceptions_padj': 2.0,
        'recoveries_padj': 10.0,
        'touches_high_pct': 25,
        'touches_mid_pct': 35,
        'touches_low_pct': 40,
        'box_touch_rate': 10
    },
    "Défenseur axial": {
        'pass_accuracy': 85,
        'prog_passes_per_90': 4,
        'key_passes_per_match': 0.2,
        'shot_accuracy': 15,
        'xg_per_90': 0.05,
        'goals_per_xg': 2.0,
        'duel_win_rate': 60,
        'interceptions_per_90': 3.0,
        'recoveries_per_90': 7,
        'xg_per_shot': 0.05,
        'finishing_delta_per_90': 0.0,
        'shot_involvement_per_90': 1.0,
        'interceptions_padj': 4.0,
        'recoveries_padj': 15.0,
        'touches_high_pct': 10,
        'touches_mid_pct': 30,
        'touches_low_pct': 60,
        'box_touch_rate': 5
    },
    "Défaut": {
        'pass_accuracy': 80,
        'prog_passes_per_90': 5,
        'key_passes_per_match': 1.0,
        'shot_accuracy': 30,
        'xg_per_90': 0.2,
        'goals_per_xg': 1.0,
        'duel_win_rate': 50,
        'interceptions_per_90': 2.0,
        'recoveries_per_90': 6,
        'xg_per_shot': 0.10,
        'finishing_delta_per_90': 0.0,
        'shot_involvement_per_90': 3.0,
        'interceptions_padj': 2.5,
        'recoveries_padj': 10.0,
        'touches_high_pct': 20,
        'touches_mid_pct': 35,
        'touches_low_pct': 45,
        'box_touch_rate': 10
    }
}

def calculate_kpis(data, total_min, total_matches, player_id=None, df_players=None):
    kpis = {}
    
    passes_tent = to_num(data.get("passes_att", pd.Series([0]))).sum()
    passes_comp = to_num(data.get("passes_cmp", pd.Series([0]))).sum()
    kpis['pass_accuracy'] = safe_div(passes_comp, passes_tent, 0) * 100
    
    prog_passes = to_num(data.get("prog_passes", pd.Series([0]))).sum()
    kpis['prog_passes_per_90'] = safe_div(prog_passes, total_min, 0) * 90
    
    key_passes = to_num(data.get("key_passes", pd.Series([0]))).sum()
    kpis['key_passes_per_match'] = safe_div(key_passes, total_matches, 0)
    
    tirs = to_num(data.get("shots", pd.Series([0]))).sum()
    tirs_cadres = to_num(data.get("shots_on", pd.Series([0]))).sum()
    kpis['shot_accuracy'] = safe_div(tirs_cadres, tirs, 0) * 100
    
    xg = to_num(data.get("xg", pd.Series([0]))).sum()
    kpis['xg_per_90'] = safe_div(xg, total_min, 0) * 90
    
    buts = to_num(data.get("goals", pd.Series([0]))).sum()
    kpis['goals_per_xg'] = safe_div(buts, xg, 0)
    
    duels_tent = to_num(data.get("duels_att", pd.Series([0]))).sum()
    duels_gagnes = to_num(data.get("duels_won", pd.Series([0]))).sum()
    kpis['duel_win_rate'] = safe_div(duels_gagnes, duels_tent, 0) * 100
    
    interceptions = to_num(data.get("interceptions", pd.Series([0]))).sum()
    kpis['interceptions_per_90'] = safe_div(interceptions, total_min, 0) * 90
    
    recoveries = to_num(data.get("recoveries", pd.Series([0]))).sum()
    kpis['recoveries_per_90'] = safe_div(recoveries, total_min, 0) * 90
    
    # NOUVEAUX KPIs
    kpis['xg_per_shot'] = safe_div(xg, tirs, 0)
    kpis['finishing_delta'] = buts - xg
    kpis['finishing_delta_per_90'] = safe_div(kpis['finishing_delta'], total_min, 0) * 90
    kpis['shot_involvement_per_90'] = safe_div((tirs + key_passes), total_min, 0) * 90
    
    exposure = max(duels_tent, 1)
    kpis['interceptions_padj'] = safe_div(interceptions, exposure, 0) * 10
    kpis['recoveries_padj'] = safe_div(recoveries, exposure, 0) * 10
    
    touches_high = to_num(data.get("touches_high", pd.Series([0]))).sum()
    touches_mid = to_num(data.get("touches_mid", pd.Series([0]))).sum()
    touches_low = to_num(data.get("touches_low", pd.Series([0]))).sum()
    touches_box = to_num(data.get("touches_box", pd.Series([0]))).sum()
    tot_touches = max(touches_high + touches_mid + touches_low, 1)
    
    kpis['touches_high_pct'] = safe_div(touches_high, tot_touches, 0) * 100
    kpis['touches_mid_pct'] = safe_div(touches_mid, tot_touches, 0) * 100
    kpis['touches_low_pct'] = safe_div(touches_low, tot_touches, 0) * 100
    kpis['box_touch_rate'] = safe_div(touches_box, tot_touches, 0) * 100
    
    kpis['kp_per_prog'] = safe_div(key_passes, prog_passes, 0)
    kpis['shots_per_kp'] = safe_div(tirs, key_passes, 0)
    
    if player_id is not None and df_players is not None and not df_players.empty:
        player_row = df_players[df_players["player_id"] == str(player_id)]
        if not player_row.empty:
            poste_detail = player_row.iloc[0].get('poste_detail', 'Défaut')
            benchmarks = BENCHMARKS_PAR_POSTE.get(poste_detail, BENCHMARKS_PAR_POSTE['Défaut'])
        else:
            benchmarks = BENCHMARKS_PAR_POSTE['Défaut']
    else:
        benchmarks = BENCHMARKS_PAR_POSTE['Défaut']
    
    kpis['benchmarks'] = benchmarks
    kpis['poste_detail'] = poste_detail if 'poste_detail' in locals() else 'Défaut'
    
    return kpis

def calculate_percentile_rank(series, value):
    s = pd.to_numeric(series, errors='coerce').dropna()
    if len(s) == 0:
        return 0
    return (s < value).mean() * 100

# ==================== GOOGLE SHEETS → XLSX (public) ====================
def get_file_id():
    try:
        return st.secrets["GOOGLE_SHEET_ID"]
    except:
        return "1giSdEgXz3VytLq9Acn9rlQGbUhNAo2bI"

def _download_gsheets_as_xlsx(file_id: str) -> tuple[bytes, str, int]:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    try:
        r = requests.get(url, allow_redirects=True, timeout=30)
        if r.status_code != 200 or r.headers.get("Content-Type","").startswith("text/html"):
            raise RuntimeError(
                f"Échec export Google Sheets (HTTP {r.status_code}). "
                "Vérifie que le fichier est public en lecture."
            )
        content = r.content
        sig = hashlib.md5(content).hexdigest()
        size = len(content)
        return content, sig, size
    except Exception as e:
        local_path = "/mnt/data/Football-Hub-all-in-one.xlsx"
        if os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                content = f.read()
                sig = hashlib.md5(content).hexdigest()
                size = len(content)
                return content, sig, size
        raise e

@st.cache_data(show_spinner=False, ttl=600)
def _parse_excel_bytes(xlsx_bytes: bytes, sig: str) -> dict:
    xl = pd.ExcelFile(io.BytesIO(xlsx_bytes), engine="openpyxl")
    return {name: xl.parse(name).copy(deep=True) for name in xl.sheet_names}

with st.sidebar:
    if st.button("🔄 Recharger depuis Drive", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    FILE_ID = get_file_id()
    xlsx_bytes, FILE_SIG, FILE_SIZE = _download_gsheets_as_xlsx(FILE_ID)
    data = _parse_excel_bytes(xlsx_bytes, FILE_SIG)
except Exception as e:
    st.error(f"❌ Impossible de charger depuis Drive : {e}")
    st.stop()

# === Déballage des feuilles ===
df_players = data.get("Joueur", pd.DataFrame())
df_match   = data.get("Match", pd.DataFrame())
df_well    = data.get("Wellness", pd.DataFrame())

# CANONICALISATION DES DATAFRAMES (CORRECTION CRITIQUE)
df_players = canonize_df(df_players)
df_match = canonize_df(df_match)
df_well = canonize_df(df_well)

# Tri des données match par date
if not df_match.empty and 'date' in df_match.columns:
    df_match = df_match.sort_values('date', kind='mergesort')

if not df_well.empty and "date" in df_well.columns:
    df_well["date"] = pd.to_datetime(df_well["date"], errors="coerce")

# -------------------- SIDEBAR --------------------
st.sidebar.markdown("### 🎯 Paramètres d'analyse")
player_map = {}
if not df_players.empty and {"player_id", "prenom", "nom"}.issubset(df_players.columns):
    for _, r in df_players.iterrows():
        display = f"{r.get('prenom','')} {r.get('nom','')} (#{str(r.get('player_id'))})"
        player_map[display] = str(r.get("player_id"))
elif not df_match.empty and "player_id" in df_match.columns:
    for pid in sorted(df_match["player_id"].dropna().unique()):
        player_map[str(pid)] = str(pid)

sel_display = st.sidebar.selectbox("🏃 Sélection joueur", list(player_map.keys()) if player_map else [])
player_id = player_map.get(sel_display) if player_map else None

st.sidebar.markdown("### ⚙️ Options d'analyse")
show_predictions = st.sidebar.checkbox("📈 Afficher les prédictions", value=True)
compare_mode = st.sidebar.checkbox("🔄 Mode comparaison", value=False)
advanced_metrics = st.sidebar.checkbox("📊 Métriques avancées", value=True)

if compare_mode and len(player_map) > 1:
    available_players = [k for k in player_map.keys() if k != sel_display]
    compare_player = st.sidebar.selectbox("👥 Comparer avec", available_players)
    compare_player_id = player_map.get(compare_player)
else:
    compare_player_id = None

# -------------------- PAGES --------------------
tabs = st.tabs(["🏠 Dashboard", "📊 Performance", "📈 Projections", "🩺 Wellness", "🔍 Analyse", "📄 Données"])

# ======================= DASHBOARD =======================
with tabs[0]:
    st.markdown('<div class="hero"><span class="pill">🎯 Dashboard de Performance Joueur</span></div>', unsafe_allow_html=True)
    st.write("")
    if player_id is not None:
        col1, col2 = st.columns([1, 2], gap="large")
        with col1:
            st.markdown("##### 👤 Profil Joueur")
            if not df_players.empty and "player_id" in df_players.columns:
                p = df_players[df_players["player_id"] == player_id]
                if not p.empty:
                    p = p.iloc[0]
                    initials = (str(p.get("prenom","")[:1]) + str(p.get("nom","")[:1])).upper()
                    if not df_match.empty:
                        dm = df_match[df_match["player_id"] == player_id]
                        poste_detail = p.get('poste_detail', 'Défaut')
                        perf_score = calculate_performance_score(dm, poste_detail)
                        perf_badge = get_performance_badge(perf_score)
                    else:
                        perf_score = 0
                        perf_badge = get_performance_badge(0)
                    try:
                        naissance = str(pd.to_datetime(p.get("date_naissance")).date())
                    except Exception:
                        naissance = str(p.get("date_naissance")) if pd.notna(p.get("date_naissance")) else ""
                    st.markdown(
                        f"""
                        <div class="glass">
                            <div style="display:flex; gap:12px; align-items:center; margin-bottom: 16px;">
                                <div class="avatar">{initials}</div>
                                <div>
                                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 4px;">{p.get('prenom','')} {p.get('nom','')}</div>
                                    <div style="color: var(--muted); font-size: 14px;">{p.get('poste_detail', p.get('poste',''))} • {p.get('club','')}</div>
                                </div>
                            </div>
                            <div style="margin-bottom: 12px;">{perf_badge}</div>
                            <div class="divider"></div>
                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                                <div class="metric-card">
                                    <h3>Score Global</h3>
                                    <div class="value" style="color: {'#10b981' if perf_score >= 70 else '#f59e0b' if perf_score >= 50 else '#ef4444'};">{perf_score:.1f}</div>
                                </div>
                                <div class="metric-card">
                                    <h3>Taille</h3>
                                    <div class="value">{p.get('taille','')} cm</div>
                                </div>
                                <div class="metric-card">
                                    <h3>Poids</h3>
                                    <div class="value">{p.get('poids','')} kg</div>
                                </div>
                                <div class="metric-card">
                                    <h3>Pied Fort</h3>
                                    <div class="value">{p.get('pied','')}</div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        with col2:
            st.markdown("##### 📊 KPIs Saison")
            if not df_match.empty and "player_id" in df_match.columns:
                dm = df_match[df_match["player_id"] == player_id].copy()
                if not dm.empty:
                    total_minutes = to_num(dm.get("minutes")).sum()
                    total_matches = len(dm)
                    kpis_season = calculate_kpis(dm, total_minutes, total_matches, player_id, df_players)
                    
                    cols = st.columns(3)
                    with cols[0]:
                        color = "#10b981" if kpis_season['xg_per_90'] > 0.5 else "#f59e0b" if kpis_season['xg_per_90'] > 0.3 else "#ef4444"
                        st.markdown(f"""
                        <div class="metric-card">
                            <h3>⚽ xG/90</h3>
                            <div class="value" style="color: {color};">{kpis_season['xg_per_90']:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with cols[1]:
                        color = "#10b981" if kpis_season['pass_accuracy'] > 80 else "#f59e0b" if kpis_season['pass_accuracy'] > 70 else "#ef4444"
                        st.markdown(f"""
                        <div class="metric-card">
                            <h3>✅ Précision</h3>
                            <div class="value" style="color: {color};">{kpis_season['pass_accuracy']:.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with cols[2]:
                        color = "#10b981" if kpis_season['duel_win_rate'] > 55 else "#f59e0b" if kpis_season['duel_win_rate'] > 50 else "#ef4444"
                        st.markdown(f"""
                        <div class="metric-card">
                            <h3>🏆 Duels</h3>
                            <div class="value" style="color: {color};">{kpis_season['duel_win_rate']:.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("##### 🕸️ Radar de Performance Tactique")
                    radar_categories = [
                        'Précision Passes', 'Passes Prog./90', 'Passes Décisives',
                        'Précision Tirs', 'xG/90', 'Efficacité',
                        'Duels Gagnés', 'Interceptions/90', 'Récupérations/90'
                    ]
                    radar_values = [
                        min(kpis_season['pass_accuracy'], 100),
                        min(kpis_season['prog_passes_per_90'] * 10, 100),
                        min(kpis_season['key_passes_per_match'] * 50, 100),
                        min(kpis_season['shot_accuracy'], 100),
                        min(kpis_season['xg_per_90'] * 150, 100),
                        min(kpis_season['goals_per_xg'] * 70, 100),
                        min(kpis_season['duel_win_rate'], 100),
                        min(kpis_season['interceptions_per_90'] * 30, 100),
                        min(kpis_season['recoveries_per_90'] * 10, 100)
                    ]
                    radar_fig = create_radar_chart(radar_values, radar_categories, "Performance Tactique Complète")
                    st.plotly_chart(radar_fig, use_container_width=True)
        
        st.markdown("##### 🎯 Synthèse Match Spécifique — Améliorée")
        if not df_match.empty:
            dm = df_match[df_match["player_id"] == player_id].copy()
            if not dm.empty:
                if 'date' in dm.columns:
                    dm = dm.sort_values('date')
                elif 'matchday' in dm.columns:
                    dm = dm.sort_values('matchday', kind='mergesort')
                
                last_match = dm.iloc[-1]
                j_day = last_match.get("matchday", "N/A")
                opponent = last_match.get("opponent", "N/A")
                match_df = pd.DataFrame([last_match])
                total_min_scalar = to_num(last_match.get("minutes", 0)).iloc[0]
                kpis_match = calculate_kpis(match_df, total_min_scalar, 1, player_id, df_players)
                
                wellness_summary = {}
                if not df_well.empty:
                    match_date = pd.to_datetime(last_match.get("date"), errors='coerce')
                    if pd.notna(match_date):
                        dw_match = df_well[
                            (df_well["player_id"] == player_id) &
                            (df_well["date"] >= match_date - timedelta(days=1)) &
                            (df_well["date"] <= match_date)
                        ]
                        if not dw_match.empty:
                            for metric in ["Energie générale", "Fraicheur musculaire", "Humeur", "Sommeil", "Intensité douleur"]:
                                if metric in dw_match.columns:
                                    avg_val = dw_match[metric].mean()
                                    wellness_summary[metric] = avg_val
                
                st.markdown(f"""
                <div class="match-synthesis">
                    <h3 style="margin:0 0 16px 0; color: #5eead4;">Match J{j_day} • {opponent}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                synth_col1, synth_col2, synth_col3 = st.columns(3)
                with synth_col1:
                    st.markdown("##### 📤 Distribution")
                    pass_color = "#10b981" if kpis_match['pass_accuracy'] > 80 else "#f59e0b" if kpis_match['pass_accuracy'] > 70 else "#ef4444"
                    prog_color = "#10b981" if kpis_match['prog_passes_per_90'] > 8 else "#f59e0b" if kpis_match['prog_passes_per_90'] > 5 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Précision Passes</div>
                        <div class="value" style="color: {pass_color};">{kpis_match['pass_accuracy']:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Passes Prog./90</div>
                        <div class="value" style="color: {prog_color};">{kpis_match['prog_passes_per_90']:.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with synth_col2:
                    st.markdown("##### ⚽ Offense")
                    shot_color = "#10b981" if kpis_match['shot_accuracy'] > 40 else "#f59e0b" if kpis_match['shot_accuracy'] > 30 else "#ef4444"
                    xg_color = "#10b981" if kpis_match['xg_per_90'] > 0.5 else "#f59e0b" if kpis_match['xg_per_90'] > 0.3 else "#ef4444"
                    finishing_color = "#10b981" if kpis_match['finishing_delta'] > 0 else "#f59e0b" if kpis_match['finishing_delta'] > -0.5 else "#ef4444"
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Précision Tirs</div>
                        <div class="value" style="color: {shot_color};">{kpis_match['shot_accuracy']:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">xG/90</div>
                        <div class="value" style="color: {xg_color};">{kpis_match['xg_per_90']:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Finishing Δ</div>
                        <div class="value" style="color: {finishing_color};">{kpis_match['finishing_delta']:.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with synth_col3:
                    st.markdown("##### 🛡️ Défense & Wellness")
                    duel_color = "#10b981" if kpis_match['duel_win_rate'] > 55 else "#f59e0b" if kpis_match['duel_win_rate'] > 50 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Duels Gagnés</div>
                        <div class="value" style="color: {duel_color};">{kpis_match['duel_win_rate']:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Interceptions PAdj</div>
                        <div class="value" style="color: #3b82f6;">{kpis_match['interceptions_padj']:.1f}</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Récupérations PAdj</div>
                        <div class="value" style="color: #3b82f6;">{kpis_match['recoveries_padj']:.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if wellness_summary:
                        energy = wellness_summary.get("Energie générale", 0)
                        freshness = wellness_summary.get("Fraicheur musculaire", 0)
                        energy_color = "#10b981" if energy > 7 else "#f59e0b" if energy > 5 else "#ef4444"
                        fresh_color = "#10b981" if freshness > 7 else "#f59e0b" if freshness > 5 else "#ef4444"
                        st.markdown(f"""
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">Énergie</div>
                            <div class="value" style="color: {energy_color};">{energy:.1f}/10</div>
                        </div>
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">Fraîcheur</div>
                            <div class="value" style="color: {fresh_color};">{freshness:.1f}/10</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("Wellness non disponible")

# ======================= PERFORMANCE =======================
with tabs[1]:
    st.markdown('<div class="hero"><span class="pill">📊 Performance Tactique - Distribution, Offense, Défense</span></div>', unsafe_allow_html=True)
    st.write("")
    if player_id is not None and not df_match.empty:
        dm = df_match[df_match["player_id"] == player_id].copy()
        if not dm.empty:
            analysis_mode = st.radio("Mode d'analyse", ["📊 Vue saison complète", "🎯 Match spécifique"], horizontal=True, key="perf_mode")
            if analysis_mode == "🎯 Match spécifique":
                if "matchday" in dm.columns and "opponent" in dm.columns:
                    pairs = dm[["matchday","opponent"]].dropna().drop_duplicates().sort_values(["matchday","opponent"])
                    journees = pairs["matchday"].unique().tolist()
                    j_sel = st.selectbox("Journée", journees, index=0 if journees else None, key="j_sel_perf")
                    adv_for_j = pairs.loc[pairs["matchday"] == j_sel, "opponent"].unique().tolist()
                    adv_sel = st.selectbox("Adversaire", adv_for_j, index=0 if adv_for_j else None, key="adv_sel_perf")
                    match_data = dm[(dm["matchday"] == j_sel) & (dm["opponent"] == adv_sel)]
                else:
                    match_data = dm.iloc[:1]
            else:
                match_data = dm
            
            if not match_data.empty:
                total_minutes = to_num(match_data.get("minutes", 0)).sum()
                total_matches = len(match_data) if analysis_mode == "📊 Vue saison complète" else 1
                kpis = calculate_kpis(match_data, total_minutes, total_matches, player_id, df_players)
                
                st.markdown("#### 🎯 KPIs de Performance - Synthèse Tactique")
                
                st.markdown("##### 📤 Distribution (Contrôle et Création)")
                dist_cols = st.columns(3)
                with dist_cols[0]:
                    color = "#10b981" if kpis['pass_accuracy'] > kpis['benchmarks']['pass_accuracy'] else "#f59e0b" if kpis['pass_accuracy'] > kpis['benchmarks']['pass_accuracy'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Précision Passes</h3>
                        <div class="value" style="color: {color};">{kpis['pass_accuracy']:.1f}%</div>
                        <div style="font-size: 12px; color: var(--muted);">Benchmark: {kpis['benchmarks']['pass_accuracy']}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with dist_cols[1]:
                    color = "#10b981" if kpis['prog_passes_per_90'] > kpis['benchmarks']['prog_passes_per_90'] else "#f59e0b" if kpis['prog_passes_per_90'] > kpis['benchmarks']['prog_passes_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Passes Progressives</h3>
                        <div class="value" style="color: {color};">{kpis['prog_passes_per_90']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/90 min</div>
                    </div>
                    """, unsafe_allow_html=True)
                with dist_cols[2]:
                    color = "#10b981" if kpis['key_passes_per_match'] > kpis['benchmarks']['key_passes_per_match'] else "#f59e0b" if kpis['key_passes_per_match'] > kpis['benchmarks']['key_passes_per_match'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Passes Décisives</h3>
                        <div class="value" style="color: {color};">{kpis['key_passes_per_match']:.2f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/match</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("##### ⚽ Offense (Création et Finition)")
                off_cols = st.columns(3)
                with off_cols[0]:
                    color = "#10b981" if kpis['shot_accuracy'] > kpis['benchmarks']['shot_accuracy'] else "#f59e0b" if kpis['shot_accuracy'] > kpis['benchmarks']['shot_accuracy'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Précision Tirs</h3>
                        <div class="value" style="color: {color};">{kpis['shot_accuracy']:.1f}%</div>
                        <div style="font-size: 12px; color: var(--muted);">Benchmark: {kpis['benchmarks']['shot_accuracy']}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with off_cols[1]:
                    color = "#10b981" if kpis['xg_per_90'] > kpis['benchmarks']['xg_per_90'] else "#f59e0b" if kpis['xg_per_90'] > kpis['benchmarks']['xg_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>xG Généré</h3>
                        <div class="value" style="color: {color};">{kpis['xg_per_90']:.2f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/90 min</div>
                    </div>
                    """, unsafe_allow_html=True)
                with off_cols[2]:
                    color = "#10b981" if kpis['goals_per_xg'] > kpis['benchmarks']['goals_per_xg'] else "#f59e0b" if kpis['goals_per_xg'] > kpis['benchmarks']['goals_per_xg'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Efficacité Finition</h3>
                        <div class="value" style="color: {color};">{kpis['goals_per_xg']:.2f}</div>
                        <div style="font-size: 12px; color: var(--muted);">Buts/xG</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("##### 🛡️ Défense (Récupération et Duel)")
                def_cols = st.columns(3)
                with def_cols[0]:
                    color = "#10b981" if kpis['duel_win_rate'] > kpis['benchmarks']['duel_win_rate'] else "#f59e0b" if kpis['duel_win_rate'] > kpis['benchmarks']['duel_win_rate'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Taux Duel Gagné</h3>
                        <div class="value" style="color: {color};">{kpis['duel_win_rate']:.1f}%</div>
                        <div style="font-size: 12px; color: var(--muted);">Benchmark: {kpis['benchmarks']['duel_win_rate']}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with def_cols[1]:
                    color = "#10b981" if kpis['interceptions_padj'] > kpis['benchmarks'].get('interceptions_padj', 2.5) else "#f59e0b" if kpis['interceptions_padj'] > kpis['benchmarks'].get('interceptions_padj', 2.5) * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Interceptions PAdj</h3>
                        <div class="value" style="color: {color};">{kpis['interceptions_padj']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/10 duels subis</div>
                    </div>
                    """, unsafe_allow_html=True)
                with def_cols[2]:
                    color = "#10b981" if kpis['recoveries_padj'] > kpis['benchmarks'].get('recoveries_padj', 10.0) else "#f59e0b" if kpis['recoveries_padj'] > kpis['benchmarks'].get('recoveries_padj', 10.0) * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Récupérations PAdj</h3>
                        <div class="value" style="color: {color};">{kpis['recoveries_padj']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/10 duels subis</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("#### 📊 Synthèse Visuelle des KPIs")
                st.caption("Comparaison par rapport aux benchmarks spécifiques à votre poste")
                
                kpi_names = [
                    'Précision Passes', 'Passes Progressives', 'Passes Décisives',
                    'Précision Tirs', 'xG Généré', 'Efficacité Finition',
                    'Taux Duel Gagné', 'Interceptions', 'Récupérations'
                ]
                kpi_keys = [
                    'pass_accuracy','prog_passes_per_90','key_passes_per_match',
                    'shot_accuracy','xg_per_90','goals_per_xg',
                    'duel_win_rate','interceptions_per_90','recoveries_per_90'
                ]
                kpi_values = [kpis[k] for k in kpi_keys]
                benchmarks_in_order = [kpis['benchmarks'][k] for k in kpi_keys]
                colors = ['#3b82f6', '#3b82f6', '#3b82f6', '#10b981', '#10b981', '#10b981', '#ef4444', '#ef4444', '#ef4444']
                
                fig_synthesis = go.Figure()
                fig_synthesis.add_trace(go.Bar(
                    y=kpi_names,
                    x=kpi_values,
                    orientation='h',
                    marker_color=colors,
                    name='Performance',
                    text=[f"{v:.1f}" for v in kpi_values],
                    textposition='auto',
                ))
                
                for i, benchmark in enumerate(benchmarks_in_order):
                    fig_synthesis.add_shape(
                        type="line", line=dict(color="rgba(255,255,255,0.5)", width=2, dash="dot"),
                        y0=i-0.4, y1=i+0.4, x0=benchmark, x1=benchmark
                    )
                
                fig_synthesis.update_layout(
                    title="Performance par KPI vs Benchmark (Spécifique au Poste)",
                    xaxis_title="Valeur",
                    yaxis_title="KPI",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    showlegend=False,
                    height=600
                )
                st.plotly_chart(fig_synthesis, use_container_width=True)

# ======================= PROJECTIONS =======================
with tabs[2]:
    st.markdown('<div class="hero"><span class="pill">📈 Projections par Régression Linéaire</span></div>', unsafe_allow_html=True)
    st.write("")
    if player_id is not None and not df_match.empty and show_predictions:
        dm = df_match[df_match["player_id"] == player_id].copy()
        if not dm.empty and len(dm) >= 5:
            if 'date' in dm.columns:
                dm = dm.sort_values('date')
            elif 'matchday' in dm.columns:
                dm = dm.sort_values('matchday', kind='mergesort')
            
            dm_ml = dm.reset_index(drop=True)
            dm_ml['match_number'] = range(1, len(dm_ml) + 1)
            
            kpi_options = {
                'Précision Passes': 'pass_accuracy',
                'xG Généré (/90)': 'xg_per_90',
                'Taux Duel Gagné': 'duel_win_rate',
                'Passes Progressives (/90)': 'prog_passes_per_90',
                'Interceptions (/90)': 'interceptions_per_90',
                'xG par Tir': 'xg_per_shot',
                'Finishing Delta': 'finishing_delta_per_90'
            }
            selected_kpi_name = st.selectbox("KPI à prédire", list(kpi_options.keys()), key="ml_kpi_select")
            selected_kpi_key = kpi_options[selected_kpi_name]
            periods_ahead = st.slider("Nombre de matchs à prédire", 1, 10, 5, key="ml_periods")
            
            per_match_kpis = []
            for i in range(len(dm_ml)):
                match_row = dm_ml.iloc[i:i+1]
                match_minutes = to_num(match_row.get("minutes", 0)).iloc[0]
                kpi_dict = calculate_kpis(match_row, match_minutes, 1, player_id, df_players)
                per_match_kpis.append(kpi_dict[selected_kpi_key])
            
            dm_ml['target_kpi'] = per_match_kpis
            
            if len(per_match_kpis) >= 3:
                y_smooth = pd.Series(per_match_kpis).ewm(alpha=0.3, adjust=False).mean().values
                dm_ml['target_kpi_smooth'] = y_smooth
                y_values = y_smooth
            else:
                y_values = per_match_kpis
            
            X = dm_ml['match_number'].values
            y = y_values
            
            n = len(X)
            split_idx = int(0.8 * n)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            model = predict_performance_trend_manual(X_train, y_train, periods_ahead)
            
            if model:
                all_match_numbers = np.arange(1, len(dm_ml) + periods_ahead + 1)
                y_pred_full = model['slope'] * all_match_numbers + model['intercept']
                y_pred_train = model['slope'] * X_train + model['intercept']
                mae = np.mean(np.abs(y_train - y_pred_train))
                confidence_interval = 1.96 * mae
                
                fig_ml = go.Figure()
                fig_ml.add_trace(go.Scatter(
                    x=dm_ml['match_number'],
                    y=y_values,
                    mode='markers+lines',
                    name='Valeurs Réelles (lissées)',
                    marker=dict(size=8, color='#3b82f6'),
                    line=dict(color='#3b82f6', width=2)
                ))
                fig_ml.add_trace(go.Scatter(
                    x=all_match_numbers,
                    y=y_pred_full,
                    mode='lines',
                    name='Prédictions ML',
                    line=dict(color='#10b981', width=3, dash='dash')
                ))
                fig_ml.add_trace(go.Scatter(
                    x=all_match_numbers,
                    y=y_pred_full + confidence_interval,
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo='skip'
                ))
                fig_ml.add_trace(go.Scatter(
                    x=all_match_numbers,
                    y=y_pred_full - confidence_interval,
                    mode='lines',
                    fill='tonexty',
                    fillcolor='rgba(16, 185, 129, 0.2)',
                    line=dict(width=0),
                    name='Intervalle 95%',
                    hoverinfo='skip'
                ))
                
                fig_ml.update_layout(
                    title=f"Prédiction du KPI '{selected_kpi_name}'",
                    xaxis_title="Numéro de Match",
                    yaxis_title=selected_kpi_name,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    hovermode='x unified',
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                )
                st.plotly_chart(fig_ml, use_container_width=True)
                
                if len(X_test) > 0:
                    y_pred_test = model['slope'] * X_test + model['intercept']
                    ss_res = np.sum((y_test - y_pred_test) ** 2)
                    ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                else:
                    r2 = model['r_squared']
                
                col1, col2, col3 = st.columns(3)
                col1.metric("📈 Pente", f"{model['slope']:.3f}", "par match")
                col2.metric("🎯 R² Score", f"{r2:.2f}", "Qualité du modèle")
                col3.metric("📏 MAE", f"{mae:.2f}", "Erreur moyenne")
                
                if model['slope'] > 0.1:
                    trend_text = "📈 Tendance fortement positive - Continuez comme ça !"
                elif model['slope'] > 0:
                    trend_text = "↗️ Tendance positive - Bonne progression."
                elif model['slope'] > -0.1:
                    trend_text = "➡️ Tendance stable - Cherchez à vous améliorer."
                else:
                    trend_text = "📉 Tendance négative - Travaillez sur ce point."
                st.success(f"**Interprétation :** {trend_text}")

# ======================= WELLNESS =======================
with tabs[3]:
    st.markdown('<div class="hero"><span class="pill">🩺 Analyse Wellness & Corrélation Performance</span></div>', unsafe_allow_html=True)
    st.write("")
    if player_id is not None and not df_well.empty:
        dw = df_well[df_well["player_id"] == player_id].copy()
        if not dw.empty and "date" in dw.columns:
            dw = dw.sort_values("date").tail(60)
            wellness_metrics = [c for c in ["Energie générale", "Fraicheur musculaire", "Humeur", "Sommeil", "Intensité douleur"] if c in dw.columns]
            if wellness_metrics:
                st.markdown("#### 📈 Courbes de Tendance par Indicateur")
                selected_metrics = st.multiselect(
                    "Sélectionner les indicateurs à afficher",
                    options=wellness_metrics,
                    default=wellness_metrics
                )
                if selected_metrics:
                    for metric in selected_metrics:
                        fig_metric = go.Figure()
                        fig_metric.add_trace(go.Scatter(
                            x=dw["date"],
                            y=dw[metric],
                            mode='lines+markers',
                            name=f'{metric} (brut)',
                            line=dict(width=3, color='#3b82f6'),
                            marker=dict(size=6)
                        ))
                        ma7 = dw[metric].rolling(window=7, min_periods=1).mean()
                        fig_metric.add_trace(go.Scatter(
                            x=dw["date"],
                            y=ma7,
                            mode='lines',
                            name=f'{metric} (MA7)',
                            line=dict(width=4, color='#10b981', dash='solid')
                        ))
                        fig_metric.update_layout(
                            title=f"Tendance de '{metric}' sur 60 jours",
                            xaxis_title="Date",
                            yaxis_title="Score (0-10)",
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e2e8f0'),
                            yaxis=dict(range=[0, 10]),
                            hovermode='x unified',
                            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                        )
                        st.plotly_chart(fig_metric, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 🔄 Vue d'Ensemble — Tous les Indicateurs")
                if selected_metrics:
                    fig_combined = go.Figure()
                    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
                    for i, metric in enumerate(selected_metrics):
                        fig_combined.add_trace(go.Scatter(
                            x=dw["date"],
                            y=dw[metric],
                            mode='lines',
                            name=metric,
                            line=dict(width=3, color=colors[i % len(colors)])
                        ))
                    fig_combined.update_layout(
                        title="Vue d'Ensemble du Bien-être — Tous les Indicateurs",
                        xaxis_title="Date",
                        yaxis_title="Score (0-10)",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e2e8f0'),
                        yaxis=dict(range=[0, 10]),
                        hovermode='x unified',
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                    )
                    st.plotly_chart(fig_combined, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📊 Statistiques des 7 Derniers Jours")
                recent_data = dw.tail(7)
                cols = st.columns(len(selected_metrics)) if selected_metrics else []
                for i, metric in enumerate(selected_metrics):
                    with cols[i] if cols else st.container():
                        values = pd.to_numeric(recent_data[metric], errors='coerce').dropna()
                        if not values.empty:
                            avg_val = values.mean()
                            trend = "📈" if len(values) > 1 and values.iloc[-1] > values.iloc[0] else "📉" if len(values) > 1 and values.iloc[-1] < values.iloc[0] else "➡️"
                            if avg_val >= 8:
                                color = "#10b981"
                                status = "Optimal"
                            elif avg_val >= 6:
                                color = "#3b82f6"
                                status = "Bon"
                            elif avg_val >= 4:
                                color = "#f59e0b"
                                status = "Moyen"
                            else:
                                color = "#ef4444"
                                status = "À surveiller"
                            st.markdown(f"""
                            <div class="metric-card">
                                <h3>{metric}</h3>
                                <div class="value" style="color: {color};">{avg_val:.1f}/10</div>
                                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                                    {status} {trend}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

# ======================= ANALYSE COMPARATIVE =======================
with tabs[4]:
    st.markdown('<div class="hero"><span class="pill">🔍 Analyse Comparative Avancée</span></div>', unsafe_allow_html=True)
    st.write("")
    if compare_mode and player_id is not None and compare_player_id is not None:
        dm1 = df_match[df_match["player_id"] == player_id].copy()
        dm2 = df_match[df_match["player_id"] == compare_player_id].copy()
        if not dm1.empty and not dm2.empty:
            player1_name = sel_display.split(" (#")[0]
            player2_name = compare_player.split(" (#")[0]
            st.markdown(f"#### ⚖️ Comparaison: **{player1_name}** vs **{player2_name}**")
            
            p1_matches = len(dm1)
            p1_minutes = int(to_num(dm1.get("minutes", 0)).sum())
            p1_buts = int(to_num(dm1.get("goals", 0)).sum())
            p1_xg = float(to_num(dm1.get("xg", 0)).sum())
            p1_passes = int(to_num(dm1.get("passes_cmp", 0)).sum())
            
            p2_matches = len(dm2)
            p2_minutes = int(to_num(dm2.get("minutes", 0)).sum())
            p2_buts = int(to_num(dm2.get("goals", 0)).sum())
            p2_xg = float(to_num(dm2.get("xg", 0)).sum())
            p2_passes = int(to_num(dm2.get("passes_cmp", 0)).sum())
            
            kpi_cols = st.columns(5)
            kpi_cols[0].metric("Matchs Joués", f"{p1_matches}", f"{p1_matches - p2_matches:+d} vs {player2_name[:10]}")
            kpi_cols[1].metric("Minutes", f"{p1_minutes}", f"{p1_minutes - p2_minutes:+d}")
            kpi_cols[2].metric("Buts", f"{p1_buts}", f"{p1_buts - p2_buts:+d}")
            kpi_cols[3].metric("xG", f"{p1_xg:.1f}", f"{p1_xg - p2_xg:+.1f}")
            kpi_cols[4].metric("Passes", f"{p1_passes}", f"{p1_passes - p2_passes:+d}")
            
            st.markdown("##### 🕸️ Comparaison Radar (Overlay)")
            def calc_radar_metrics(dm):
                matches = len(dm) if len(dm) > 0 else 1
                passes_tent = to_num(dm.get("passes_att", 0)).sum()
                passes_comp = to_num(dm.get("passes_cmp", 0)).sum()
                pass_eff = safe_div(passes_comp, passes_tent, 0) * 100
                
                duels_tent = to_num(dm.get("duels_att", 0)).sum()
                duels_gagnes = to_num(dm.get("duels_won", 0)).sum()
                duel_eff = safe_div(duels_gagnes, duels_tent, 0) * 100
                
                tirs = to_num(dm.get("shots", 0)).sum()
                tirs_cadres = to_num(dm.get("shots_on", 0)).sum()
                tir_eff = safe_div(tirs_cadres, tirs, 0) * 100
                
                xg_per_match = to_num(dm.get("xg", 0)).sum() / matches
                buts_per_match = to_num(dm.get("goals", 0)).sum() / matches
                minutes_per_match = to_num(dm.get("minutes", 0)).sum() / matches
                playtime_pct = min(minutes_per_match / 90 * 100, 100)
                
                xg_per_shot = safe_div(to_num(dm.get("xg", 0)).sum(), to_num(dm.get("shots", 0)).sum(), 0)
                finishing_delta = to_num(dm.get("goals", 0)).sum() - to_num(dm.get("xg", 0)).sum()
                
                return [
                    min(pass_eff, 100),
                    min(duel_eff, 100),
                    min(tir_eff, 100),
                    min(xg_per_match * 20, 100),
                    min(buts_per_match * 50, 100),
                    playtime_pct,
                    min(xg_per_shot * 1000, 100),
                    min(finishing_delta * 20 + 50, 100)
                ]
            
            radar_categories = ['Passes', 'Duels', 'Tirs', 'xG/Match', 'Buts/Match', 'Temps de Jeu', 'xG/Tir', 'Finishing']
            
            p1_radar = calc_radar_metrics(dm1)
            p2_radar = calc_radar_metrics(dm2)
            
            fig_overlay = go.Figure()
            fig_overlay.add_trace(go.Scatterpolar(
                r=p1_radar,
                theta=radar_categories,
                fill='toself',
                name=player1_name,
                line=dict(color='#3b82f6', width=2),
                fillcolor='rgba(59, 130, 246, 0.2)',
                marker=dict(size=8, color='#3b82f6')
            ))
            fig_overlay.add_trace(go.Scatterpolar(
                r=p2_radar,
                theta=radar_categories,
                fill='toself',
                name=player2_name,
                line=dict(color='#10b981', width=2),
                fillcolor='rgba(16, 185, 129, 0.2)',
                marker=dict(size=8, color='#10b981'),
                opacity=0.7
            ))
            
            fig_overlay.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        gridcolor='rgba(255, 255, 255, 0.2)',
                        linecolor='rgba(255, 255, 255, 0.3)'
                    ),
                    angularaxis=dict(
                        gridcolor='rgba(255, 255, 255, 0.2)',
                        linecolor='rgba(255, 255, 255, 0.3)'
                    ),
                    bgcolor='rgba(0, 0, 0, 0)'
                ),
                showlegend=True,
                title=dict(text=f"Comparaison Radar - {player1_name} vs {player2_name}", x=0.5, font=dict(color='#e2e8f0')),
                paper_bgcolor='rgba(0, 0, 0, 0)',
                plot_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig_overlay, use_container_width=True)

# ======================= DONNÉES =======================
with tabs[5]:
    st.markdown("#### 📄 Données Brutes et Export")
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Joueurs", df_players.shape[0])
    col2.metric("⚽ Matchs", df_match.shape[0])
    col3.metric("🩺 Wellness", df_well.shape[0])
    
    data_view = st.selectbox(
        "Vue des données",
        ["Joueurs", "Matchs", "Wellness", "Statistiques agrégées", "Export PDF"]
    )
    
    if data_view == "Joueurs":
        st.markdown("**👥 Données Joueurs**")
        st.dataframe(df_players, use_container_width=True)
    elif data_view == "Matchs":
        st.markdown("**⚽ Données Matchs**")
        if player_id:
            dm_filtered = df_match[df_match["player_id"] == player_id]
            st.dataframe(dm_filtered, use_container_width=True)
        else:
            st.dataframe(df_match.head(50), use_container_width=True)
    elif data_view == "Wellness":
        st.markdown("**🩺 Données Wellness**")
        if player_id:
            dw_filtered = df_well[df_well["player_id"] == player_id]
            st.dataframe(dw_filtered, use_container_width=True)
        else:
            st.dataframe(df_well.head(50), use_container_width=True)
    elif data_view == "Statistiques agrégées":
        st.markdown("**📈 Statistiques Agrégées par Joueur**")
        if not df_match.empty and "player_id" in df_match.columns:
            agg_stats = []
            for pid in df_match["player_id"].unique():
                dm_player = df_match[df_match["player_id"] == pid]
                if not dm_player.empty:
                    stats = {
                        'PlayerID': pid,
                        'Matchs': len(dm_player),
                        'Minutes_Total': int(to_num(dm_player.get("minutes", 0)).sum()),
                        'Buts': int(to_num(dm_player.get("goals", 0)).sum()),
                        'xG': float(to_num(dm_player.get("xg", 0)).sum()),
                        'Tirs': int(to_num(dm_player.get("shots", 0)).sum()),
                        'Passes_Completes': int(to_num(dm_player.get("passes_cmp", 0)).sum()),
                        'Duels_Gagnes': int(to_num(dm_player.get("duels_won", 0)).sum()),
                        'Score_Performance': calculate_performance_score(dm_player)
                    }
                    matches = stats['Matchs'] if stats['Matchs'] > 0 else 1
                    stats['Buts_par_Match'] = stats['Buts'] / matches
                    stats['xG_par_Match'] = stats['xG'] / matches
                    stats['Minutes_par_Match'] = stats['Minutes_Total'] / matches
                    agg_stats.append(stats)
            if agg_stats:
                stats_df = pd.DataFrame(agg_stats)
                st.dataframe(stats_df, use_container_width=True)
                csv = stats_df.to_csv(index=False)
                st.download_button(
                    label="📥 Télécharger les statistiques (CSV)",
                    data=csv,
                    file_name=f"football_stats_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )

# -------------------- FOOTER --------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; padding: 20px; color: var(--muted);">
        <p>⚽ <strong>Football Hub Analytics</strong> - Analyse de Performance Avancée</p>
        <p>Construit avec ❤️ par votre équipe Data • Les données se synchronisent automatiquement</p>
        <p style="font-size: 12px;">Version 3.0 • Benchmarks Dynamiques • Poste Détail • Visualisations Avancées</p>
    </div>
    """,
    unsafe_allow_html=True
)
