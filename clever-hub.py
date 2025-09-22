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
    """Série numérique robuste — retourne TOUJOURS une pd.Series"""
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

def norm_col(c: str) -> str:
    c = unicodedata.normalize("NFKD", str(c)).encode("ascii", "ignore").decode("ascii")
    return c.strip().lower().replace("  ", " ")

def rename_like(df: pd.DataFrame, mapping: dict):
    if df.empty: return df
    norm_map = {col: norm_col(col) for col in df.columns}
    inv = {norm_col(k): v for k, v in mapping.items()}
    new_names = {}
    for col, ncol in norm_map.items():
        if ncol in inv:
            new_names[col] = inv[ncol]
    return df.rename(columns=new_names)

def calculate_performance_score(player_data):
    """Calcule un score de performance global basé sur plusieurs métriques"""
    if player_data.empty:
        return 0
    weights = {
        'passing_efficiency': 0.25,
        'duel_success': 0.20,
        'attacking_contribution': 0.25,
        'defensive_contribution': 0.20,
        'ball_retention': 0.10
    }
    passes_tent_col = player_data.get("Passe tentées", pd.Series([0]))
    passes_comp_col = player_data.get("Passe complete", pd.Series([0]))
    passes_tent = to_num(passes_tent_col).sum()
    passes_comp = to_num(passes_comp_col).sum()
    passing_eff = (passes_comp / passes_tent * 100) if passes_tent > 0 else 0

    duel_tot_col_name = "Duel tenté" if "Duel tenté" in player_data.columns else "Duel tente"
    duels_tent_col = player_data.get(duel_tot_col_name, pd.Series([0]))
    duels_gagnes_col = player_data.get("Duel gagne", pd.Series([0]))
    duels_tent = to_num(duels_tent_col).sum()
    duels_gagnes = to_num(duels_gagnes_col).sum()
    duel_eff = (duels_gagnes / duels_tent * 100) if duels_tent > 0 else 0

    buts_col = player_data.get("Buts", pd.Series([0]))
    tirs_col = player_data.get("Tir", pd.Series([0]))
    xg_col = player_data.get("xG", pd.Series([0]))
    buts = to_num(buts_col).sum()
    tirs = to_num(tirs_col).sum()
    xg = to_num(xg_col).sum()
    attacking_score = (buts * 10) + (tirs * 2) + (xg * 5)

    interceptions_col = player_data.get("Interception", pd.Series([0]))
    recoveries_col = player_data.get("Recuperation du ballon", pd.Series([0]))
    interceptions = to_num(interceptions_col).sum()
    recoveries = to_num(recoveries_col).sum()
    defensive_score = (interceptions * 3) + (recoveries * 2)

    touches_col = player_data.get("Ballon touché", pd.Series([0]))
    touches = to_num(touches_col).sum()
    ball_retention_score = touches / len(player_data) if len(player_data) > 0 else 0

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
    },
    # Ajoutez d'autres postes selon vos besoins
    "Défaut": {  # Pour les postes non définis
        'pass_accuracy': 80,
        'prog_passes_per_90': 5,
        'key_passes_per_match': 1.0,
        'shot_accuracy': 30,
        'xg_per_90': 0.2,
        'goals_per_xg': 1.0,
        'duel_win_rate': 50,
        'interceptions_per_90': 2.0,
        'recoveries_per_90': 6,
    }
}

def calculate_kpis(data, total_min, total_matches, player_id=None, df_players=None):
    kpis = {}
    passes_tent_col = data.get("Passe tentées", pd.Series([0]))
    passes_comp_col = data.get("Passe complete", pd.Series([0]))
    passes_tent = to_num(passes_tent_col).sum()
    passes_comp = to_num(passes_comp_col).sum()
    kpis['pass_accuracy'] = (passes_comp / passes_tent * 100) if passes_tent > 0 else 0

    prog_passes_col = data.get("Passe progressive", pd.Series([0])) if "Passe progressive" in data.columns else pd.Series([0])
    prog_passes = to_num(prog_passes_col).sum()
    kpis['prog_passes_per_90'] = (prog_passes / total_min * 90) if total_min > 0 else 0

    key_passes_col = data.get("Passe decisive", pd.Series([0])) if "Passe decisive" in data.columns else pd.Series([0])
    key_passes = to_num(key_passes_col).sum()
    kpis['key_passes_per_match'] = key_passes / total_matches if total_matches > 0 else 0

    tirs_col = data.get("Tir", pd.Series([0]))
    tirs_cadres_col = data.get("Tir cadre", pd.Series([0]))
    tirs = to_num(tirs_col).sum()
    tirs_cadres = to_num(tirs_cadres_col).sum()
    kpis['shot_accuracy'] = (tirs_cadres / tirs * 100) if tirs > 0 else 0

    xg_col = data.get("xG", pd.Series([0]))
    xg = to_num(xg_col).sum()
    kpis['xg_per_90'] = (xg / total_min * 90) if total_min > 0 else 0

    buts_col = data.get("Buts", pd.Series([0]))
    buts = to_num(buts_col).sum()
    kpis['goals_per_xg'] = buts / xg if xg > 0 else 0

    duel_tot_col_name = "Duel tenté" if "Duel tenté" in data.columns else "Duel tente"
    duels_tent_col = data.get(duel_tot_col_name, pd.Series([0]))
    duels_gagnes_col = data.get("Duel gagne", pd.Series([0]))
    duels_tent = to_num(duels_tent_col).sum()
    duels_gagnes = to_num(duels_gagnes_col).sum()
    kpis['duel_win_rate'] = (duels_gagnes / duels_tent * 100) if duels_tent > 0 else 0

    interceptions_col = data.get("Interception", pd.Series([0]))
    interceptions = to_num(interceptions_col).sum()
    kpis['interceptions_per_90'] = (interceptions / total_min * 90) if total_min > 0 else 0

    recoveries_col = data.get("Recuperation du ballon", pd.Series([0]))
    recoveries = to_num(recoveries_col).sum()
    kpis['recoveries_per_90'] = (recoveries / total_min * 90) if total_min > 0 else 0

    # Récupérer le poste détaillé du joueur pour appliquer les bons benchmarks
    if player_id is not None and df_players is not None and not df_players.empty:
        player_row = df_players[df_players["PlayerID_norm"] == str(player_id)]
        if not player_row.empty:
            poste_detail = player_row.iloc[0].get('Poste Détail', 'Défaut')
            benchmarks = BENCHMARKS_PAR_POSTE.get(poste_detail, BENCHMARKS_PAR_POSTE['Défaut'])
        else:
            benchmarks = BENCHMARKS_PAR_POSTE['Défaut']
    else:
        benchmarks = BENCHMARKS_PAR_POSTE['Défaut']

    # Ajouter les benchmarks au dictionnaire retourné
    kpis['benchmarks'] = benchmarks

    return kpis

# ==================== GOOGLE SHEETS → XLSX (public) ====================
FILE_ID = "1giSdEgXz3VytLq9Acn9rlQGbUhNAo2bI"

def _download_gsheets_as_xlsx(file_id: str) -> tuple[bytes, str, int]:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
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

@st.cache_data(show_spinner=False)
def _parse_excel_bytes(xlsx_bytes: bytes, sig: str) -> dict:
    xl = pd.ExcelFile(io.BytesIO(xlsx_bytes), engine="openpyxl")
    return {name: xl.parse(name).copy(deep=True) for name in xl.sheet_names}

# --- UI: reload
with st.sidebar:
    if st.button("🔄 Recharger depuis Drive", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Téléchargement + parsing
try:
    xlsx_bytes, FILE_SIG, FILE_SIZE = _download_gsheets_as_xlsx(FILE_ID)
    data = _parse_excel_bytes(xlsx_bytes, FILE_SIG)
except Exception as e:
    st.error(f"❌ Impossible de charger depuis Drive : {e}")
    st.stop()

# === Déballage des feuilles ===
df_players = data.get("Joueur", pd.DataFrame())
df_match   = data.get("Match", pd.DataFrame())
df_well    = data.get("Wellness", pd.DataFrame())

for df in (df_players, df_match, df_well):
    if not df.empty and "PlayerID" in df.columns:
        df["PlayerID_norm"] = df["PlayerID"].astype(str).str.strip()

mapping = {
    "minute jouee": "Minutes Jouées",
    "tir cadre": "Tir cadre",
    "passe courte tentee": "Passe courte tentée",
    "passe courte complete": "Passe courte complète",
    "passe moyenne tentee": "Passe moyenne tentée",
    "passe moyenne complete": "Passe moyenne complète",
    "passe longue tentee": "Passe longue tentée",
    "passe longue complete": "Passe longue complète",
    "duel tente": "Duel tenté",
    "duel gagne": "Duel gagné",
    "duel aérien gagné": "Duel aérien gagné",
    "duel aérien perdu": "Duel aérien perdu",
    "distance parcourue avec ballon": "Distance parcouru avec ballon (m)",
    "distance parcourue progression": "Distance parcouru progression(m)",
    "ballon touche haute": "Ballon touché haute",
    "ballon touche médian": "Ballon touché médian",
    "ballon touche basse": "Ballon touché basse",
    "ballon touche surface": "Ballon touché surface",
    "recuperation du ballon": "Recuperation du ballon",
}

df_match = rename_like(df_match, mapping)

if not df_well.empty and "DATE" in df_well.columns:
    df_well["DATE"] = pd.to_datetime(df_well["DATE"], errors="coerce")

# -------------------- SIDEBAR --------------------
st.sidebar.markdown("### 🎯 Paramètres d'analyse")
player_map = {}
if not df_players.empty and {"PlayerID_norm", "Prénom", "Nom"}.issubset(df_players.columns):
    for _, r in df_players.iterrows():
        display = f"{r.get('Prénom','')} {r.get('Nom','')} (#{str(r.get('PlayerID'))})"
        player_map[display] = str(r.get("PlayerID"))
elif not df_match.empty and "PlayerID_norm" in df_match.columns:
    for pid in sorted(df_match["PlayerID_norm"].dropna().unique()):
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
            if not df_players.empty and "PlayerID_norm" in df_players.columns:
                p = df_players[df_players["PlayerID_norm"] == player_id]
                if not p.empty:
                    p = p.iloc[0]
                    initials = (str(p.get("Prénom","")[:1]) + str(p.get("Nom","")[:1])).upper()

                    if not df_match.empty:
                        dm = df_match[df_match["PlayerID_norm"] == player_id]
                        perf_score = calculate_performance_score(dm)
                        perf_badge = get_performance_badge(perf_score)
                    else:
                        perf_score = 0
                        perf_badge = get_performance_badge(0)

                    try:
                        naissance = str(pd.to_datetime(p.get("date de naissance")).date())
                    except Exception:
                        naissance = str(p.get("date de naissance")) if pd.notna(p.get("date de naissance")) else ""

                    st.markdown(
                        f"""
                        <div class="glass">
                            <div style="display:flex; gap:12px; align-items:center; margin-bottom: 16px;">
                                <div class="avatar">{initials}</div>
                                <div>
                                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 4px;">{p.get('Prénom','')} {p.get('Nom','')}</div>
                                    <div style="color: var(--muted); font-size: 14px;">{p.get('Poste Détail', p.get('Poste',''))} • {p.get('Club','')}</div>
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
                                    <div class="value">{p.get('Taille','')} cm</div>
                                </div>
                                <div class="metric-card">
                                    <h3>Poids</h3>
                                    <div class="value">{p.get('Poids','')} kg</div>
                                </div>
                                <div class="metric-card">
                                    <h3>Pied Fort</h3>
                                    <div class="value">{p.get('Pied','')}</div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with col2:
            st.markdown("##### 📊 KPIs Saison")
            if not df_match.empty and "PlayerID_norm" in df_match.columns:
                dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
                if not dm.empty:
                    total_minutes = to_num(dm.get("Minutes Jouées")).sum()
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
            dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
            if not dm.empty and "Journée" in dm.columns:
                last_match = dm.iloc[-1]
                j_day = last_match.get("Journée", "N/A")
                opponent = last_match.get("Adversaire", "N/A")
                match_df = pd.DataFrame([last_match])
                total_min_scalar = to_num(last_match.get("Minutes Jouées", 0)).iloc[0]
                kpis_match = calculate_kpis(match_df, total_min_scalar, 1, player_id, df_players)

                wellness_summary = {}
                if not df_well.empty:
                    match_date = pd.to_datetime(last_match.get("DATE"), errors='coerce')
                    if pd.notna(match_date):
                        dw_match = df_well[
                            (df_well["PlayerID_norm"] == player_id) &
                            (df_well["DATE"] >= match_date - timedelta(days=1)) &
                            (df_well["DATE"] <= match_date)
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
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">Précision Tirs</div>
                        <div class="value" style="color: {shot_color};">{kpis_match['shot_accuracy']:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: var(--muted);">xG/90</div>
                        <div class="value" style="color: {xg_color};">{kpis_match['xg_per_90']:.2f}</div>
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
        dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
        if not dm.empty:
            analysis_mode = st.radio("Mode d'analyse", ["📊 Vue saison complète", "🎯 Match spécifique"], horizontal=True, key="perf_mode")
            if analysis_mode == "🎯 Match spécifique":
                if "Journée" in dm.columns and "Adversaire" in dm.columns:
                    pairs = dm[["Journée","Adversaire"]].dropna().drop_duplicates().sort_values(["Journée","Adversaire"])
                    journees = pairs["Journée"].unique().tolist()
                    j_sel = st.selectbox("Journée", journees, index=0 if journees else None, key="j_sel_perf")
                    adv_for_j = pairs.loc[pairs["Journée"] == j_sel, "Adversaire"].unique().tolist()
                    adv_sel = st.selectbox("Adversaire", adv_for_j, index=0 if adv_for_j else None, key="adv_sel_perf")
                    match_data = dm[(dm["Journée"] == j_sel) & (dm["Adversaire"] == adv_sel)]
                else:
                    match_data = dm.iloc[:1]
            else:
                match_data = dm

            if not match_data.empty:
                total_minutes = to_num(match_data.get("Minutes Jouées", 0)).sum()
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
                    color = "#10b981" if kpis['interceptions_per_90'] > kpis['benchmarks']['interceptions_per_90'] else "#f59e0b" if kpis['interceptions_per_90'] > kpis['benchmarks']['interceptions_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Interceptions</h3>
                        <div class="value" style="color: {color};">{kpis['interceptions_per_90']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/90 min</div>
                    </div>
                    """, unsafe_allow_html=True)
                with def_cols[2]:
                    color = "#10b981" if kpis['recoveries_per_90'] > kpis['benchmarks']['recoveries_per_90'] else "#f59e0b" if kpis['recoveries_per_90'] > kpis['benchmarks']['recoveries_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Récupérations</h3>
                        <div class="value" style="color: {color};">{kpis['recoveries_per_90']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/90 min</div>
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
                kpi_values = [
                    kpis['pass_accuracy'],
                    kpis['prog_passes_per_90'],
                    kpis['key_passes_per_match'],
                    kpis['shot_accuracy'],
                    kpis['xg_per_90'],
                    kpis['goals_per_xg'],
                    kpis['duel_win_rate'],
                    kpis['interceptions_per_90'],
                    kpis['recoveries_per_90']
                ]
                # Utiliser les benchmarks dynamiques
                benchmarks = list(kpis['benchmarks'].values())

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

                for i, benchmark in enumerate(benchmarks):
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
        dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
        if not dm.empty and len(dm) >= 5:
            st.markdown("#### 🔮 Prédictions de KPIs par Régression Linéaire")
            st.info("💡 Les prédictions sont basées sur un modèle de régression linéaire manuelle (sans sklearn).")

            dm_ml = dm.reset_index(drop=True)
            dm_ml['match_number'] = range(1, len(dm_ml) + 1)

            kpi_options = {
                'Précision Passes': 'pass_accuracy',
                'xG Généré (/90)': 'xg_per_90',
                'Taux Duel Gagné': 'duel_win_rate',
                'Passes Progressives (/90)': 'prog_passes_per_90',
                'Interceptions (/90)': 'interceptions_per_90'
            }
            selected_kpi_name = st.selectbox("KPI à prédire", list(kpi_options.keys()), key="ml_kpi_select")
            selected_kpi_key = kpi_options[selected_kpi_name]

            periods_ahead = st.slider("Nombre de matchs à prédire", 1, 10, 5, key="ml_periods")

            historical_kpis = []
            for i in range(len(dm_ml)):
                match_slice = dm_ml.iloc[:i+1]
                total_min = to_num(match_slice.get("Minutes Jouées", 0)).sum()
                total_matches = len(match_slice)
                kpi_dict = calculate_kpis(match_slice, total_min, total_matches, player_id, df_players)
                historical_kpis.append(kpi_dict[selected_kpi_key])

            dm_ml['target_kpi'] = historical_kpis

            X = dm_ml['match_number'].values
            y = dm_ml['target_kpi'].values

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
                    y=dm_ml['target_kpi'],
                    mode='markers+lines',
                    name='Valeurs Réelles',
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
        dw = df_well[df_well["PlayerID_norm"] == player_id].copy()
        if not dw.empty and "DATE" in dw.columns:
            dw = dw.sort_values("DATE").tail(60)

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
                            x=dw["DATE"],
                            y=dw[metric],
                            mode='lines+markers',
                            name=f'{metric} (brut)',
                            line=dict(width=3, color='#3b82f6'),
                            marker=dict(size=6)
                        ))
                        ma7 = dw[metric].rolling(window=7, min_periods=1).mean()
                        fig_metric.add_trace(go.Scatter(
                            x=dw["DATE"],
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
                            x=dw["DATE"],
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

                st.markdown("#### 🔗 Corrélation Wellness ↔ Performance (Derniers 15 jours)")
                if not df_match.empty:
                    dm_player = df_match[df_match["PlayerID_norm"] == player_id].copy()
                    if "DATE" in dm_player.columns:
                        dm_player["DATE"] = pd.to_datetime(dm_player["DATE"], errors='coerce')
                        correlation_data = []
                        for _, match_row in dm_player.iterrows():
                            match_date = match_row["DATE"]
                            if pd.notna(match_date):
                                wellness_window = dw[
                                    (dw["DATE"] >= match_date - timedelta(days=3)) &
                                    (dw["DATE"] <= match_date)
                                ]
                                if not wellness_window.empty:
                                    avg_wellness = {metric: wellness_window[metric].mean() for metric in selected_metrics}
                                    match_df = pd.DataFrame([match_row])
                                    total_min_scalar = to_num(match_row.get("Minutes Jouées", 0)).iloc[0]
                                    perf_kpis = calculate_kpis(match_df, total_min_scalar, 1, player_id, df_players)
                                    correlation_data.append({**avg_wellness, **perf_kpis})

                        if len(correlation_data) >= 3:
                            corr_df = pd.DataFrame(correlation_data)
                            perf_kpi_options = ['xg_per_90', 'duel_win_rate', 'pass_accuracy']
                            selected_perf_kpi = st.selectbox("KPI de Performance", perf_kpi_options,
                                                           format_func=lambda x: x.replace('_', ' ').title(),
                                                           key="wellness_corr_kpi")

                            corr_results = []
                            for w_metric in selected_metrics:
                                if w_metric in corr_df.columns and selected_perf_kpi in corr_df.columns:
                                    clean_data = corr_df[[w_metric, selected_perf_kpi]].dropna()
                                    if len(clean_data) >= 3:
                                        corr_coef = clean_data[w_metric].corr(clean_data[selected_perf_kpi])
                                        corr_results.append({
                                            'Wellness': w_metric,
                                            'Corrélation': corr_coef
                                        })

                            if corr_results:
                                corr_results_df = pd.DataFrame(corr_results)
                                fig_corr_bar = px.bar(corr_results_df, x='Wellness', y='Corrélation',
                                                    title=f"Corrélation avec {selected_perf_kpi.replace('_', ' ').title()}",
                                                    color='Corrélation',
                                                    color_continuous_scale='RdBu',
                                                    range_color=[-1, 1])
                                fig_corr_bar.update_layout(
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='#e2e8f0')
                                )
                                st.plotly_chart(fig_corr_bar, use_container_width=True)

                                st.markdown("##### 💡 Insights Actionnables")
                                for _, row in corr_results_df.iterrows():
                                    if row['Corrélation'] > 0.5:
                                        st.success(f"✅ {row['Wellness']} a un impact POSITIF fort sur {selected_perf_kpi} (r={row['Corrélation']:.2f})")
                                    elif row['Corrélation'] < -0.5:
                                        st.error(f"⚠️ {row['Wellness']} a un impact NÉGATIF fort sur {selected_perf_kpi} (r={row['Corrélation']:.2f})")
                                    elif abs(row['Corrélation']) < 0.3:
                                        st.info(f"ℹ️ {row['Wellness']} n'a pas d'impact significatif sur {selected_perf_kpi} (r={row['Corrélation']:.2f})")

# ======================= ANALYSE COMPARATIVE =======================
with tabs[4]:
    st.markdown('<div class="hero"><span class="pill">🔍 Analyse Comparative Avancée</span></div>', unsafe_allow_html=True)
    st.write("")

    if compare_mode and player_id is not None and compare_player_id is not None:
        dm1 = df_match[df_match["PlayerID_norm"] == player_id].copy()
        dm2 = df_match[df_match["PlayerID_norm"] == compare_player_id].copy()

        if not dm1.empty and not dm2.empty:
            player1_name = sel_display.split(" (#")[0]
            player2_name = compare_player.split(" (#")[0]

            st.markdown(f"#### ⚖️ Comparaison: **{player1_name}** vs **{player2_name}**")

            p1_matches = len(dm1)
            p1_minutes = int(to_num(dm1.get("Minutes Jouées", 0)).sum())
            p1_buts = int(to_num(dm1.get("Buts", 0)).sum())
            p1_xg = float(to_num(dm1.get("xG", 0)).sum())
            p1_passes = int(to_num(dm1.get("Passe complete", 0)).sum())

            p2_matches = len(dm2)
            p2_minutes = int(to_num(dm2.get("Minutes Jouées", 0)).sum())
            p2_buts = int(to_num(dm2.get("Buts", 0)).sum())
            p2_xg = float(to_num(dm2.get("xG", 0)).sum())
            p2_passes = int(to_num(dm2.get("Passe complete", 0)).sum())

            kpi_cols = st.columns(5)
            kpi_cols[0].metric("Matchs Joués", f"{p1_matches}", f"{p1_matches - p2_matches:+d} vs {player2_name[:10]}")
            kpi_cols[1].metric("Minutes", f"{p1_minutes}", f"{p1_minutes - p2_minutes:+d}")
            kpi_cols[2].metric("Buts", f"{p1_buts}", f"{p1_buts - p2_buts:+d}")
            kpi_cols[3].metric("xG", f"{p1_xg:.1f}", f"{p1_xg - p2_xg:+.1f}")
            kpi_cols[4].metric("Passes", f"{p1_passes}", f"{p1_passes - p2_passes:+d}")

            st.markdown("##### 🕸️ Comparaison Radar")
            col1, col2 = st.columns(2)

            def calc_radar_metrics(dm):
                matches = len(dm) if len(dm) > 0 else 1
                passes_tent = to_num(dm.get("Passe tentées", 0)).sum()
                passes_comp = to_num(dm.get("Passe complete", 0)).sum()
                pass_eff = (passes_comp / passes_tent * 100) if passes_tent > 0 else 0

                duel_tot_col = "Duel tenté" if "Duel tenté" in dm.columns else "Duel tente"
                duels_tent = to_num(dm.get(duel_tot_col, 0)).sum()
                duels_gagnes = to_num(dm.get("Duel gagne", 0)).sum()
                duel_eff = (duels_gagnes / duels_tent * 100) if duels_tent > 0 else 0

                tirs = to_num(dm.get("Tir", 0)).sum()
                tirs_cadres = to_num(dm.get("Tir cadre", 0)).sum()
                tir_eff = (tirs_cadres / tirs * 100) if tirs > 0 else 0

                xg_per_match = to_num(dm.get("xG", 0)).sum() / matches
                buts_per_match = to_num(dm.get("Buts", 0)).sum() / matches
                minutes_per_match = to_num(dm.get("Minutes Jouées", 0)).sum() / matches
                playtime_pct = min(minutes_per_match / 90 * 100, 100)

                return [
                    min(pass_eff, 100),
                    min(duel_eff, 100),
                    min(tir_eff, 100),
                    min(xg_per_match * 20, 100),
                    min(buts_per_match * 50, 100),
                    playtime_pct
                ]

            radar_categories = ['Passes', 'Duels', 'Tirs', 'xG/Match', 'Buts/Match', 'Temps de Jeu']

            with col1:
                p1_radar = calc_radar_metrics(dm1)
                fig1 = create_radar_chart(p1_radar, radar_categories, f"Performance - {player1_name}")
                st.plotly_chart(fig1, use_container_width=True)

            with col2:
                p2_radar = calc_radar_metrics(dm2)
                fig2 = create_radar_chart(p2_radar, radar_categories, f"Performance - {player2_name}")
                st.plotly_chart(fig2, use_container_width=True)

            st.markdown("##### ⚡ Comparaison Directe")
            comparison_data = []
            for i, category in enumerate(radar_categories):
                comparison_data.append({
                    'Catégorie': category,
                    player1_name: p1_radar[i],
                    player2_name: p2_radar[i]
                })

            comp_df = pd.DataFrame(comparison_data)
            fig_comp = px.bar(comp_df, x='Catégorie', y=[player1_name, player2_name],
                             title="Comparaison des Performances", barmode='group')
            fig_comp.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            st.markdown("##### 📈 Évolution Comparée")
            metric_to_compare = st.selectbox(
                "Métrique à comparer dans le temps",
                ["Buts", "xG", "Passe complete", "Tir", "Duel gagne"],
                key="compare_metric"
            )

            if metric_to_compare in dm1.columns and metric_to_compare in dm2.columns:
                fig_evolution = go.Figure()
                p1_values = to_num(dm1[metric_to_compare]).cumsum()
                fig_evolution.add_trace(go.Scatter(
                    x=list(range(1, len(p1_values) + 1)),
                    y=p1_values,
                    mode='lines+markers',
                    name=player1_name,
                    line=dict(width=3)
                ))
                p2_values = to_num(dm2[metric_to_compare]).cumsum()
                fig_evolution.add_trace(go.Scatter(
                    x=list(range(1, len(p2_values) + 1)),
                    y=p2_values,
                    mode='lines+markers',
                    name=player2_name,
                    line=dict(width=3)
                ))

                fig_evolution.update_layout(
                    title=f"Évolution Cumulative - {metric_to_compare}",
                    xaxis_title="Numéro de Match",
                    yaxis_title=f"{metric_to_compare} (Cumulé)",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0')
                )
                st.plotly_chart(fig_evolution, use_container_width=True)

# ======================= DONNÉES =======================
with tabs[5]:
    st.markdown("#### 📄 Données Brutes et Export")
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Joueurs", df_players.shape[0])
    col2.metric("⚽ Matchs", df_match.shape[0])
    col3.metric("🩺 Wellness", df_well.shape[0])

    data_view = st.selectbox(
        "Vue des données",
        ["Joueurs", "Matchs", "Wellness", "Statistiques agrégées"]
    )

    if data_view == "Joueurs":
        st.markdown("**👥 Données Joueurs**")
        st.dataframe(df_players, use_container_width=True)

    elif data_view == "Matchs":
        st.markdown("**⚽ Données Matchs**")
        if player_id:
            dm_filtered = df_match[df_match["PlayerID_norm"] == player_id]
            st.dataframe(dm_filtered, use_container_width=True)
        else:
            st.dataframe(df_match.head(50), use_container_width=True)

    elif data_view == "Wellness":
        st.markdown("**🩺 Données Wellness**")
        if player_id:
            dw_filtered = df_well[df_well["PlayerID_norm"] == player_id]
            st.dataframe(dw_filtered, use_container_width=True)
        else:
            st.dataframe(df_well.head(50), use_container_width=True)

    elif data_view == "Statistiques agrégées":
        st.markdown("**📈 Statistiques Agrégées par Joueur**")
        if not df_match.empty and "PlayerID_norm" in df_match.columns:
            agg_stats = []
            for pid in df_match["PlayerID_norm"].unique():
                dm_player = df_match[df_match["PlayerID_norm"] == pid]
                if not dm_player.empty:
                    stats = {
                        'PlayerID': pid,
                        'Matchs': len(dm_player),
                        'Minutes_Total': int(to_num(dm_player.get("Minutes Jouées", 0)).sum()),
                        'Buts': int(to_num(dm_player.get("Buts", 0)).sum()),
                        'xG': float(to_num(dm_player.get("xG", 0)).sum()),
                        'Tirs': int(to_num(dm_player.get("Tir", 0)).sum()),
                        'Passes_Completes': int(to_num(dm_player.get("Passe complete", 0)).sum()),
                        'Duels_Gagnes': int(to_num(dm_player.get("Duel gagne", 0)).sum()),
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
        <p style="font-size: 12px;">Version 2.6 • Benchmarks Dynamiques • Poste Détail • Cloud Ready</p>
    </div>
    """,
    unsafe_allow_html=True
)
