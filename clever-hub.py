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
from matplotlib.patches import Patch
# -------------------- NOUVEL IMPORT AJOUTÉ --------------------
import mplsoccer
from mplsoccer import Pitch
import matplotlib.cm as cm
import matplotlib.colors as mcolors
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
    .progress-bar {
        height: 8px;
        background: rgba(255,255,255,0.1);
        border-radius: 4px;
        margin: 8px 0;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
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
# -------------------- MAPPING POSTE → COORDONNÉES TERRAIN (CORRIGÉ) --------------------
# -------------------- MAPPING POSTE → COORDONNÉES TERRAIN (AJUSTÉ POUR LA SURFACE) --------------------
POSTE_COORDONNEES = {
    "Gardien de but": (2, 50),           # Tout en bas, au centre
    "Défenseur axial": (20, 50),         # Dans la défense centrale
    "Défenseur latéral droit": (20, 80), # Sur le côté droit défensif
    "Défenseur latéral gauche": (20, 20),# Sur le côté gauche défensif
    "Milieu relayeur": (50, 50),         # Au centre du terrain
    "Milieu offensif": (70, 50),         # Dans l'entrejeu, proche de l'attaque
    "Milieu droit": (65, 75),            # A droite, dans le milieu offensif
    "Milieu gauche": (65, 25),           # A gauche, dans le milieu offensif
    "Attaquant central": (100, 50),       # DANS la surface de réparation adverse (93 au lieu de 90)
    "Attaquant de côté droit": (88, 70), # A droite, DANS la surface
    "Attaquant de côté gauche": (88, 30),# A gauche, DANS la surface
    # Valeurs par défaut si le poste n'est pas trouvé
    "Défaut": (50, 50),
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
df_tracking = data.get("Tracking", pd.DataFrame())  # <-- NOUVEAU : onglet Tracking

for df in (df_players, df_match, df_well, df_tracking):
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
# AJOUT DE L'ONGLET "👁️ Visualisation" ici
tabs = st.tabs(["🏠 Dashboard", "📊 Performance", "📈 Projections", "🩺 Wellness", "🔍 Analyse", "👁️ Visualisation", "📄 Données"])

# ======================= DASHBOARD =======================
# ... (tout le contenu existant de tabs[0] reste inchangé)
with tabs[0]:
    st.markdown('<div class="hero"><span class="pill">🎯 Dashboard de Performance Joueur</span></div>', unsafe_allow_html=True)
    st.write("")
    if player_id is not None:
        # --- CHARGER LES DONNÉES DU JOUEUR ---
        if not df_players.empty and "PlayerID_norm" in df_players.columns:
            p_row = df_players[df_players["PlayerID_norm"] == player_id]
            if not p_row.empty:
                p = p_row.iloc[0]
                initials = (str(p.get("Prénom","")[:1]) + str(p.get("Nom","")[:1])).upper()
                poste_detail = p.get('Poste Détail', p.get('Poste', 'Défaut'))
                dm = df_match[df_match["PlayerID_norm"] == player_id].copy() if not df_match.empty else pd.DataFrame()
                total_minutes = to_num(dm.get("Minutes Jouées", 0)).sum() if not dm.empty else 0
                total_matches = len(dm) if not dm.empty else 0
                perf_score = calculate_performance_score(dm) if not dm.empty else 0
                perf_badge = get_performance_badge(perf_score)
                kpis_season = calculate_kpis(dm, total_minutes, total_matches, player_id, df_players) if not dm.empty else {}
                # --- SECTION 1 : INFOS JOUEUR (AVANT TOUT) ---
                st.markdown("##### 👤 Informations du Joueur")
                col_avatar, col_info = st.columns([0.8, 3.2], gap="medium")
                with col_avatar:
                    st.markdown(f'<div class="avatar">{initials}</div>', unsafe_allow_html=True)
                with col_info:
                    st.markdown(f"""
                        <div style="font-size: 20px; font-weight: 700; margin-bottom: 4px;">{p.get('Prénom','')} {p.get('Nom','')}</div>
                        <div style="color: var(--muted); font-size: 15px;">{poste_detail} • {p.get('Club','')}</div>
                        <div style="margin-top: 8px;">{perf_badge}</div>
                    """, unsafe_allow_html=True)
                st.write("")
                # --- SECTION 2 : INFOS PHYSIQUES + KPIs ESSENTIELS (6 cartes uniformes) ---
                cols = st.columns(6, gap="small")
                metrics = [
                    (f"{p.get('Taille','')} cm", "Taille", "", "#e2e8f0"),
                    (f"{p.get('Poids','')} kg", "Poids", "", "#e2e8f0"),
                    (p.get('Pied',''), "Pied Fort", "", "#e2e8f0"),
                    (f"{int(total_minutes)}", "Minutes Jouées", "", "#3b82f6"),
                    (f"{total_matches}", "Matchs Joués", "", "#8b5cf6"),
                    (f"{perf_score:.1f}", "Score Global", "", '#10b981' if perf_score >= 70 else '#f59e0b' if perf_score >= 50 else '#ef4444'),
                ]
                for i, (val, label, unit, color) in enumerate(metrics):
                    with cols[i]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <h3>{label}</h3>
                            <div class="value" style="color: {color};">{val}{unit}</div>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        # --- SECTION 3 : TERRAIN CORRIGÉ (attaquants DANS la surface) ---
        st.markdown("##### 📍 Position sur le Terrain")
        # ✅ Coordonnées corrigées pour les attaquants → x = 93 à 100 (dans la surface)
        POSTE_COORDONNEES_CORRIGEES = {
            "Gardien de but": (2, 50),
            "Défenseur axial": (20, 50),
            "Défenseur latéral droit": (20, 80),
            "Défenseur latéral gauche": (20, 20),
            "Milieu relayeur": (50, 50),
            "Milieu offensif": (70, 50),
            "Milieu droit": (65, 75),
            "Milieu gauche": (65, 25),
            "Attaquant central": (95, 50),          # ✅ DANS la surface (x=95)
            "Attaquant de côté droit": (90, 70),    # ✅ DANS la surface
            "Attaquant de côté gauche": (90, 30),   # ✅ DANS la surface
            "Défaut": (50, 50),
        }
        if not df_players.empty and "PlayerID_norm" in df_players.columns:
            p = df_players[df_players["PlayerID_norm"] == player_id]
            if not p.empty:
                p = p.iloc[0]
                poste_detail = p.get('Poste Détail', p.get('Poste', 'Défaut'))
                x_pos, y_pos = POSTE_COORDONNEES_CORRIGEES.get(poste_detail, POSTE_COORDONNEES_CORRIGEES['Défaut'])
                pitch = mplsoccer.Pitch(
                    pitch_type='opta',
                    pitch_color='#0b1220',
                    line_color='#e2e8f0',
                    linewidth=1.5,
                    goal_type='box'
                )
                fig, ax = pitch.draw(figsize=(10, 6))  # Taille équilibrée
                pitch.scatter(
                    x_pos, y_pos,
                    ax=ax,
                    s=600,
                    color='#3b82f6',
                    edgecolors='white',
                    linewidth=2,
                    alpha=0.9,
                    zorder=5
                )
                ax.text(
                    x_pos, y_pos + 4,
                    poste_detail,
                    color='white',
                    fontsize=11,
                    ha='center',
                    va='bottom',
                    weight='bold',
                    zorder=6
                )
                st.pyplot(fig, use_container_width=True)
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        # --- SECTION 4 : KPIs SAISON + RADAR ---
        if not df_match.empty and "PlayerID_norm" in df_match.columns:
            dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
            if not dm.empty:
                total_minutes = to_num(dm.get("Minutes Jouées")).sum()
                total_matches = len(dm)
                kpis_season = calculate_kpis(dm, total_minutes, total_matches, player_id, df_players)
                st.markdown(f"##### ⏱️ Minutes Jouées: {int(total_minutes)} (Moyenne: {int(total_minutes/total_matches) if total_matches > 0 else 0}/match)")
                max_minutes_season = 3420
                progress_pct = min(total_minutes / max_minutes_season * 100, 100) if max_minutes_season > 0 else 0
                progress_color = "#10b981" if progress_pct > 70 else "#3b82f6" if progress_pct > 40 else "#f59e0b"
                st.markdown(
                    f"""
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {progress_pct}%; background-color: {progress_color};"></div>
                    </div>
                    <div style="text-align: right; font-size: 12px; color: var(--muted);">{progress_pct:.1f}% de la saison</div>
                    """,
                    unsafe_allow_html=True
                )
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
        # --- SECTION 5 : SYNTHÈSE MATCH (inchangée) ---
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
                    minutes_color = "#10b981" if total_min_scalar >= 70 else "#f59e0b" if total_min_scalar >= 45 else "#ef4444"
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
                        <div style="font-size: 14px; color: var(--muted);">Minutes Jouées</div>
                        <div class="value" style="color: {minutes_color};">{int(total_min_scalar)}</div>
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
# ... (tabs[1] inchangé)
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
                # Section Minutes Jouées
                st.markdown("#### ⏱️ Statistiques de Temps de Jeu")
                minutes_col1, minutes_col2, minutes_col3 = st.columns(3)
                with minutes_col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Total Minutes</h3>
                        <div class="value" style="color: #3b82f6;">{int(total_minutes)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with minutes_col2:
                    avg_minutes = total_minutes / total_matches if total_matches > 0 else 0
                    color = "#10b981" if avg_minutes >= 70 else "#f59e0b" if avg_minutes >= 45 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Moyenne par Match</h3>
                        <div class="value" style="color: {color};">{int(avg_minutes)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with minutes_col3:
                    max_possible_minutes = total_matches * 90
                    pct_played = (total_minutes / max_possible_minutes * 100) if max_possible_minutes > 0 else 0
                    color = "#10b981" if pct_played >= 80 else "#f59e0b" if pct_played >= 60 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>% du Temps de Jeu</h3>
                        <div class="value" style="color: {color};">{pct_played:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown(f"##### 📈 Progression du Temps de Jeu")
                progress_color = "#10b981" if pct_played > 70 else "#3b82f6" if pct_played > 40 else "#f59e0b"
                st.markdown(
                    f"""
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {pct_played}%; background-color: {progress_color};"></div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if analysis_mode == "📊 Vue saison complète" and len(match_data) > 1:
                    st.markdown("##### 📊 Évolution des Minutes par Match")
                    match_numbers = list(range(1, len(match_data) + 1))
                    minutes_per_match = to_num(match_data.get("Minutes Jouées", 0)).tolist()
                    fig_minutes = go.Figure()
                    fig_minutes.add_trace(go.Scatter(
                        x=match_numbers,
                        y=minutes_per_match,
                        mode='lines+markers',
                        name='Minutes par Match',
                        line=dict(color='#3b82f6', width=3),
                        marker=dict(size=8, color='#3b82f6')
                    ))
                    fig_minutes.add_hline(
                        y=avg_minutes,
                        line_dash="dash",
                        line_color="rgba(16, 185, 129, 0.8)",
                        annotation_text=f"Moyenne: {int(avg_minutes)} min",
                        annotation_position="bottom right"
                    )
                    fig_minutes.update_layout(
                        title="Évolution des Minutes Jouées par Match",
                        xaxis_title="Numéro de Match",
                        yaxis_title="Minutes",
                        paper_bgcolor='rgba(0, 0, 0, 0)',
                        plot_bgcolor='rgba(0, 0, 0, 0)',
                        font=dict(color='#e2e8f0'),
                        yaxis=dict(range=[0, max(90, max(minutes_per_match) if len(minutes_per_match) > 0 else 90)])
                    )
                    st.plotly_chart(fig_minutes, use_container_width=True)
                st.markdown("---")
                st.markdown("#### 🎯 KPIs de Performance - Synthèse Tactique")
                # ========== DISTRIBUTION ==========
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
                # --- Visualisations Distribution ---
                st.markdown("##### 📊 Répartition des Passes par Type (Cumul Saison)")
                if analysis_mode == "📊 Vue saison complète" and len(match_data) > 1:
                    pass_cols = {
                        "Courtes complètes": "Passe courte complète",
                        "Moyennes complètes": "Passe moyenne complète",
                        "Longues complètes": "Passe longue complète"
                    }
                    available_passes = {label: to_num(match_data[col]).sum() for label, col in pass_cols.items() if col in match_data.columns}
                    if available_passes:
                        match_numbers = list(range(1, len(match_data) + 1))
                        fig_passes = go.Figure()
                        for label, col in pass_cols.items():
                            if col in match_data.columns:
                                values = to_num(match_data[col]).cumsum()
                                fig_passes.add_trace(go.Scatter(
                                    x=match_numbers,
                                    y=values,
                                    mode='lines',
                                    name=label,
                                    stackgroup='one',
                                    line=dict(width=0),
                                    fillcolor={'Courtes complètes': '#10b981', 'Moyennes complètes': '#f59e0b', 'Longues complètes': '#ef4444'}.get(label, '#3b82f6')
                                ))
                        fig_passes.update_layout(
                            title="Cumul des Passes Complètes par Type au Fil des Matchs",
                            xaxis_title="Numéro de Match",
                            yaxis_title="Passes complètes (cumulées)",
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e2e8f0'),
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig_passes, use_container_width=True)
                        st.markdown("##### 🥧 Répartition Finale des Passes Complètes")
                        total_passes = sum(available_passes.values())
                        if total_passes > 0:
                            fig_pie = go.Figure(data=[go.Pie(
                                labels=list(available_passes.keys()),
                                values=list(available_passes.values()),
                                marker_colors=['#10b981', '#f59e0b', '#ef4444'],
                                textinfo='percent+label',
                                hole=0.4
                            )])
                            fig_pie.update_layout(title="Répartition des Passes Complètes par Distance", paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
                            st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.info("Données de passes par type non disponibles.")
                    st.markdown("##### 📊 Taux de Réussite par Type de Passe")
                    pct_cols = st.columns(3)
                    with pct_cols[0]:
                        if "Passe tentées" in match_data.columns and "Passe complete" in match_data.columns:
                            total_tent = to_num(match_data["Passe tentées"]).sum()
                            total_comp = to_num(match_data["Passe complete"]).sum()
                            pct_global = (total_comp / total_tent * 100) if total_tent > 0 else 0
                            st.markdown(f"""
                            <div class="metric-card">
                                <h3>Passes Complètes</h3>
                                <div class="value" style="color: #3b82f6;">{pct_global:.1f}%</div>
                            </div>
                            """, unsafe_allow_html=True)
                    with pct_cols[1]:
                        if "Passe courte tentée" in match_data.columns and "Passe courte complète" in match_data.columns:
                            ct = to_num(match_data["Passe courte tentée"]).sum()
                            cc = to_num(match_data["Passe courte complète"]).sum()
                            pct_courte = (cc / ct * 100) if ct > 0 else 0
                            st.markdown(f"""
                            <div class="metric-card">
                                <h3>Courtes</h3>
                                <div class="value" style="color: #10b981;">{pct_courte:.1f}%</div>
                            </div>
                            """, unsafe_allow_html=True)
                    with pct_cols[2]:
                        if "Passe moyenne tentée" in match_data.columns and "Passe moyenne complète" in match_data.columns:
                            mt = to_num(match_data["Passe moyenne tentée"]).sum()
                            mc = to_num(match_data["Passe moyenne complète"]).sum()
                            pct_moy = (mc / mt * 100) if mt > 0 else 0
                            st.markdown(f"""
                            <div class="metric-card">
                                <h3>Moyennes</h3>
                                <div class="value" style="color: #f59e0b;">{pct_moy:.1f}%</div>
                            </div>
                            """, unsafe_allow_html=True)
                    if "Passe longue tentée" in match_data.columns and "Passe longue complète" in match_data.columns:
                        lt = to_num(match_data["Passe longue tentée"]).sum()
                        lc = to_num(match_data["Passe longue complète"]).sum()
                        pct_long = (lc / lt * 100) if lt > 0 else 0
                        st.markdown(f"""
                        <div class="metric-card" style="margin-top: 12px;">
                            <h3>Longues</h3>
                            <div class="value" style="color: #ef4444;">{pct_long:.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Données insuffisantes pour afficher l'évolution (nécessite ≥2 matchs en mode saison).")
                st.markdown("---")
                # ========== POSSESSION ==========
                st.markdown("##### 🎯 Zones de Toucher de Balle & Déplacement")
                if analysis_mode == "📊 Vue saison complète" and len(match_data) > 1:
                    zone_cols = {"Haute": "Ballon touché haute", "Médiane": "Ballon touché médian", "Basse": "Ballon touché basse", "Surface": "Ballon touché surface"}
                    zones = {zone: to_num(match_data[col]).sum() for zone, col in zone_cols.items() if col in match_data.columns}
                    dist_cols = {"Avec ballon": "Distance parcouru avec ballon (m)", "En progression": "Distance parcouru progression(m)"}
                    distances = {label: to_num(match_data[col]).sum() for label, col in dist_cols.items() if col in match_data.columns}
                    if zones or distances:
                        fig_zones = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], specs=[[{"type": "bar"}, {"type": "bar"}]], subplot_titles=("Touches par Zone", "Distances avec Ballon"))
                        if zones:
                            fig_zones.add_trace(go.Bar(y=list(zones.keys()), x=list(zones.values()), orientation='h', marker_color=['#3b82f6', '#10b981', '#f59e0b', '#ef4444'][:len(zones)]), row=1, col=1)
                        if distances:
                            fig_zones.add_trace(go.Bar(x=list(distances.keys()), y=list(distances.values()), marker_color=['#8b5cf6', '#ec4899']), row=1, col=2)
                        fig_zones.update_layout(title="Synthèse Possession : Zones & Déplacement", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'), showlegend=False, height=400)
                        st.plotly_chart(fig_zones, use_container_width=True)
                        if "Recuperation du ballon" in match_data.columns:
                            total_recup = to_num(match_data["Recuperation du ballon"]).sum()
                            st.markdown(f"""
                            <div class="metric-card" style="margin-top: 12px;">
                                <h3>Récupérations Totales</h3>
                                <div class="value" style="color: #8b5cf6;">{int(total_recup)}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("Aucune donnée de possession disponible.")
                else:
                    st.info("Données insuffisantes pour afficher l'évolution (nécessite ≥2 matchs en mode saison).")
                st.markdown("---")
                # ========== OFFENSE ==========
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
                # --- Visualisation Offensive ---
                st.markdown("##### 🎯 Performance Offensive Détaillée")
                if analysis_mode == "📊 Vue saison complète" and len(match_data) > 1:
                    match_numbers = list(range(1, len(match_data) + 1))
                    buts = to_num(match_data.get("Buts", 0))
                    tirs = to_num(match_data.get("Tir", 0))
                    tirs_cadres = to_num(match_data.get("Tir cadre", 0))
                    xg = to_num(match_data.get("xG", 0))
                    buts_cum = buts.cumsum()
                    tirs_cum = tirs.cumsum()
                    tirs_cadres_cum = tirs_cadres.cumsum()
                    xg_cum = xg.cumsum()
                    fig_offense = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_offense.add_trace(go.Scatter(x=match_numbers, y=buts_cum, mode='lines+markers', name='Buts', line=dict(color='#ef4444', width=3)), secondary_y=False)
                    fig_offense.add_trace(go.Scatter(x=match_numbers, y=tirs_cum, mode='lines+markers', name='Tirs', line=dict(color='#f59e0b', width=2)), secondary_y=False)
                    fig_offense.add_trace(go.Scatter(x=match_numbers, y=tirs_cadres_cum, mode='lines+markers', name='Tirs Cadrés', line=dict(color='#10b981', width=2)), secondary_y=False)
                    fig_offense.add_trace(go.Scatter(x=match_numbers, y=xg_cum, mode='lines+markers', name='xG', line=dict(color='#8b5cf6', width=3, dash='dot')), secondary_y=True)
                    fig_offense.update_layout(
                        title="Cumul Offensif : Buts, Tirs, Tirs Cadrés & xG",
                        xaxis_title="Numéro de Match",
                        yaxis_title="Nombre cumulé",
                        yaxis2_title="xG cumulé",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e2e8f0'),
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_offense, use_container_width=True)
                    total_buts = buts.sum()
                    total_xg = xg.sum()
                    ratio_buts_xg = total_buts / total_xg if total_xg > 0 else 0
                    eff_col1, eff_col2, eff_col3, eff_col4 = st.columns(4)
                    with eff_col1:
                        st.markdown(f"""<div class="metric-card"><h3>Total Buts</h3><div class="value" style="color: #ef4444;">{int(total_buts)}</div></div>""", unsafe_allow_html=True)
                    with eff_col2:
                        st.markdown(f"""<div class="metric-card"><h3>Total Tirs</h3><div class="value" style="color: #f59e0b;">{int(tirs.sum())}</div></div>""", unsafe_allow_html=True)
                    with eff_col3:
                        st.markdown(f"""<div class="metric-card"><h3>Tirs Cadrés</h3><div class="value" style="color: #10b981;">{int(tirs_cadres.sum())}</div></div>""", unsafe_allow_html=True)
                    with eff_col4:
                        color = "#10b981" if ratio_buts_xg > 1.1 else "#f59e0b" if ratio_buts_xg >= 0.9 else "#ef4444"
                        st.markdown(f"""<div class="metric-card"><h3>Buts / xG</h3><div class="value" style="color: {color};">{ratio_buts_xg:.2f}</div></div>""", unsafe_allow_html=True)
                elif analysis_mode == "🎯 Match spécifique" and not match_data.empty:
                    buts = to_num(match_data.iloc[0].get("Buts", 0)).iloc[0]
                    tirs = to_num(match_data.iloc[0].get("Tir", 0)).iloc[0]
                    tirs_cadres = to_num(match_data.iloc[0].get("Tir cadre", 0)).iloc[0]
                    xg_val = to_num(match_data.iloc[0].get("xG", 0)).iloc[0]
                    categories = ['Buts', 'Tirs', 'Tirs Cadrés', 'xG']
                    values = [buts, tirs, tirs_cadres, xg_val]
                    max_vals = [5, 10, 8, 2]
                    normalized = [min(v / m * 100, 100) for v, m in zip(values, max_vals)]
                    fig_radar_off = go.Figure()
                    fig_radar_off.add_trace(go.Scatterpolar(r=normalized, theta=categories, fill='toself', line=dict(color='#ef4444'), fillcolor='rgba(239, 68, 68, 0.2)'))
                    fig_radar_off.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="Synthèse Offensive du Match", paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
                    st.plotly_chart(fig_radar_off, use_container_width=True)
                    ratio_match = buts / xg_val if xg_val > 0 else 0
                    st.markdown(f"""
                    <div style="text-align: center; margin-top: 10px; font-size: 16px; color: #e2e8f0;">
                        🎯 <strong>Buts / xG</strong> : <span style="color: {'#10b981' if ratio_match > 1.1 else '#f59e0b' if ratio_match >= 0.9 else '#ef4444'}">{ratio_match:.2f}</span>
                        {" → Finisseur froid !" if ratio_match > 1.1 else " → Conforme à l'attendu" if ratio_match >= 0.9 else " → À améliorer"}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Données offensives non disponibles.")
                st.markdown("---")
                # ========== DÉFENSE ==========
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
                # --- Visualisation Défensive ---
                st.markdown("##### 🛡️ Analyse Détaillée des Duels et Actions Défensives")
                if analysis_mode == "📊 Vue saison complète" and len(match_data) > 1:
                    recup = to_num(match_data.get("Recuperation du ballon", 0)).sum()
                    inter = to_num(match_data.get("Interception", 0)).sum()
                    duels_tent = to_num(match_data.get("Duel tenté", 0)).sum()
                    duels_gagnes = to_num(match_data.get("Duel gagne", 0)).sum()
                    duels_aer_g = to_num(match_data.get("Duel aérien gagné", 0)).sum()
                    duels_aer_p = to_num(match_data.get("Duel aérien perdu", 0)).sum()
                    # Actions défensives
                    fig_def_actions = go.Figure(data=[go.Bar(x=["Récupérations", "Interceptions"], y=[recup, inter], marker_color=['#8b5cf6', '#ec4899'])])
                    fig_def_actions.update_layout(title="Actions Défensives Totales", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'), yaxis_title="Nombre")
                    st.plotly_chart(fig_def_actions, use_container_width=True)
                    # Taux de réussite en duel
                    if duels_tent > 0:
                        duel_win_pct = duels_gagnes / duels_tent * 100
                        duel_aer_total = duels_aer_g + duels_aer_p
                        duel_aer_pct = duels_aer_g / duel_aer_total * 100 if duel_aer_total > 0 else 0
                        fig_duels = go.Figure()
                        fig_duels.add_trace(go.Bar(
                            y=["Duels Globaux", "Duels Aériens"],
                            x=[duel_win_pct, duel_aer_pct],
                            orientation='h',
                            marker_color=[
                                "#10b981" if duel_win_pct > 55 else "#f59e0b" if duel_win_pct > 50 else "#ef4444",
                                "#10b981" if duel_aer_pct > 55 else "#f59e0b" if duel_aer_pct > 50 else "#ef4444"
                            ],
                            text=[f"{duel_win_pct:.1f}%", f"{duel_aer_pct:.1f}%"],
                            textposition='auto'
                        ))
                        fig_duels.update_layout(
                            title="Taux de Réussite en Duel",
                            xaxis_title="Pourcentage de réussite (%)",
                            xaxis=dict(range=[0, 100]),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e2e8f0'),
                            height=250
                        )
                        st.plotly_chart(fig_duels, use_container_width=True)
                elif analysis_mode == "🎯 Match spécifique" and not match_data.empty:
                    recup = to_num(match_data.iloc[0].get("Recuperation du ballon", 0)).iloc[0]
                    inter = to_num(match_data.iloc[0].get("Interception", 0)).iloc[0]
                    duels_tent = to_num(match_data.iloc[0].get("Duel tenté", 0)).iloc[0]
                    duels_gagnes = to_num(match_data.iloc[0].get("Duel gagne", 0)).iloc[0]
                    duels_aer_g = to_num(match_data.iloc[0].get("Duel aérien gagné", 0)).iloc[0]
                    duels_aer_p = to_num(match_data.iloc[0].get("Duel aérien perdu", 0)).iloc[0]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"""<div class="metric-card"><h3>Récupérations</h3><div class="value" style="color: #8b5cf6;">{int(recup)}</div></div>""", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""<div class="metric-card"><h3>Interceptions</h3><div class="value" style="color: #ec4899;">{int(inter)}</div></div>""", unsafe_allow_html=True)
                    with col3:
                        duel_pct = duels_gagnes / duels_tent * 100 if duels_tent > 0 else 0
                        color = "#10b981" if duel_pct > 55 else "#f59e0b" if duel_pct > 50 else "#ef4444"
                        st.markdown(f"""<div class="metric-card"><h3>Duels Gagnés</h3><div class="value" style="color: {color};">{duel_pct:.1f}%</div></div>""", unsafe_allow_html=True)
                    if duels_aer_g + duels_aer_p > 0:
                        aer_pct = duels_aer_g / (duels_aer_g + duels_aer_p) * 100
                        st.markdown(f"""<div class="metric-card" style="margin-top: 12px;"><h3>Duels Aériens</h3><div class="value" style="color: {'#10b981' if aer_pct > 55 else '#f59e0b' if aer_pct > 50 else '#ef4444'};">{aer_pct:.1f}%</div></div>""", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("#### 📊 Synthèse Visuelle des KPIs")
                st.caption("Comparaison par rapport aux benchmarks spécifiques à votre poste")
                kpi_names = ['Précision Passes', 'Passes Progressives', 'Passes Décisives', 'Précision Tirs', 'xG Généré', 'Efficacité Finition', 'Taux Duel Gagné', 'Interceptions', 'Récupérations']
                kpi_values = [kpis['pass_accuracy'], kpis['prog_passes_per_90'], kpis['key_passes_per_match'], kpis['shot_accuracy'], kpis['xg_per_90'], kpis['goals_per_xg'], kpis['duel_win_rate'], kpis['interceptions_per_90'], kpis['recoveries_per_90']]
                benchmarks = list(kpis['benchmarks'].values())
                colors = ['#3b82f6', '#3b82f6', '#3b82f6', '#10b981', '#10b981', '#10b981', '#ef4444', '#ef4444', '#ef4444']
                fig_synthesis = go.Figure()
                fig_synthesis.add_trace(go.Bar(y=kpi_names, x=kpi_values, orientation='h', marker_color=colors, name='Performance', text=[f"{v:.1f}" for v in kpi_values], textposition='auto'))
                for i, benchmark in enumerate(benchmarks):
                    fig_synthesis.add_shape(type="line", line=dict(color="rgba(255,255,255,0.5)", width=2, dash="dot"), y0=i-0.4, y1=i+0.4, x0=benchmark, x1=benchmark)
                fig_synthesis.update_layout(title="Performance par KPI vs Benchmark (Spécifique au Poste)", xaxis_title="Valeur", yaxis_title="KPI", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'), showlegend=False, height=600)
                st.plotly_chart(fig_synthesis, use_container_width=True)

# ======================= PROJECTIONS =======================
# ... (tabs[2] inchangé)
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
            # Ajouter les minutes jouées comme option de prédiction
            kpi_options = {
                'Précision Passes': 'pass_accuracy',
                'xG Généré (/90)': 'xg_per_90',
                'Taux Duel Gagné': 'duel_win_rate',
                'Passes Progressives (/90)': 'prog_passes_per_90',
                'Interceptions (/90)': 'interceptions_per_90',
                'Minutes Jouées': 'minutes_jouees'
            }
            selected_kpi_name = st.selectbox("KPI à prédire", list(kpi_options.keys()), key="ml_kpi_select")
            selected_kpi_key = kpi_options[selected_kpi_name]
            periods_ahead = st.slider("Nombre de matchs à prédire", 1, 10, 5, key="ml_periods")
            historical_kpis = []
            for i in range(len(dm_ml)):
                match_slice = dm_ml.iloc[:i+1]
                total_min = to_num(match_slice.get("Minutes Jouées", 0)).sum()
                total_matches = len(match_slice)
                if selected_kpi_key == 'minutes_jouees':
                    # Pour les minutes jouées, on prend simplement les minutes du match
                    current_match_minutes = to_num(match_slice.iloc[-1].get("Minutes Jouées", 0)).iloc[0]
                    historical_kpis.append(current_match_minutes)
                else:
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
                # Ajuster l'axe y pour les minutes jouées
                if selected_kpi_key == 'minutes_jouees':
                    fig_ml.update_layout(
                        title=f"Prédiction du KPI '{selected_kpi_name}'",
                        xaxis_title="Numéro de Match",
                        yaxis_title=selected_kpi_name,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e2e8f0'),
                        hovermode='x unified',
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                        yaxis=dict(range=[0, 95])  # Limiter à 95 minutes
                    )
                else:
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
# ... (tabs[3] inchangé)
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
                            perf_kpi_options = ['xg_per_90', 'duel_win_rate', 'pass_accuracy', 'minutes_jouees']
                            # Modifier l'affichage pour inclure les minutes jouées
                            def format_perf_kpi(x):
                                if x == 'minutes_jouees':
                                    return 'Minutes Jouées'
                                else:
                                    return x.replace('_', ' ').title()
                            selected_perf_kpi = st.selectbox("KPI de Performance", perf_kpi_options,
                                                           format_func=format_perf_kpi,
                                                           key="wellness_corr_kpi")
                            corr_results = []
                            for w_metric in selected_metrics:
                                if w_metric in corr_df.columns:
                                    if selected_perf_kpi == 'minutes_jouees':
                                        # Calculer la corrélation avec les minutes jouées
                                        minutes_data = to_num(dm_player.loc[dm_player.index.intersection(corr_df.index), "Minutes Jouées"])
                                        clean_data = pd.DataFrame({
                                            'wellness': corr_df[w_metric],
                                            'performance': minutes_data.values[:len(corr_df)]
                                        }).dropna()
                                        if len(clean_data) >= 3:
                                            corr_coef = clean_data['wellness'].corr(clean_data['performance'])
                                            corr_results.append({
                                                'Wellness': w_metric,
                                                'Corrélation': corr_coef
                                            })
                                    else:
                                        if selected_perf_kpi in corr_df.columns:
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
                                                    title=f"Corrélation avec {format_perf_kpi(selected_perf_kpi)}",
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
                                        st.success(f"✅ {row['Wellness']} a un impact POSITIF fort sur {format_perf_kpi(selected_perf_kpi)} (r={row['Corrélation']:.2f})")
                                    elif row['Corrélation'] < -0.5:
                                        st.error(f"⚠️ {row['Wellness']} a un impact NÉGATIF fort sur {format_perf_kpi(selected_perf_kpi)} (r={row['Corrélation']:.2f})")
                                    elif abs(row['Corrélation']) < 0.3:
                                        st.info(f"ℹ️ {row['Wellness']} n'a pas d'impact significatif sur {format_perf_kpi(selected_perf_kpi)} (r={row['Corrélation']:.2f})")

# ======================= ANALYSE COMPARATIVE =======================
# ... (tabs[4] inchangé)
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
                ["Buts", "xG", "Passe complete", "Tir", "Duel gagne", "Minutes Jouées"],
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

# ======================= VISUALISATION TRACKING (NOUVEL ONGLET) =======================
with tabs[5]:  # 👁️ Visualisation
    st.markdown('<div class="hero"><span class="pill">👁️ Visualisation des Événements sur le Terrain</span></div>', unsafe_allow_html=True)
    if df_tracking.empty:
        st.warning("L'onglet 'Tracking' est vide ou manquant dans le fichier Google Sheets.")
    else:
        required_cols = ['PlayerID_norm', 'Event', 'X', 'Y']
        missing = [c for c in required_cols if c not in df_tracking.columns]
        if missing:
            st.error(f"Colonnes manquantes dans 'Tracking' : {missing}")
        else:
            # Conversion numérique
            for col in ['X', 'Y', 'X2', 'Y2']:
                if col in df_tracking.columns:
                    df_tracking[col] = pd.to_numeric(df_tracking[col], errors='coerce')

            # Conversion coordonnées si en 0–100
            max_coord = df_tracking[['X', 'Y']].max().max()
            if pd.notna(max_coord) and max_coord <= 105 and max_coord > 50:
                st.info("Conversion des coordonnées de 0-100 → 0-120/0-80")
                df_tracking['X'] *= 1.2
                df_tracking['Y'] *= 0.8
                if 'X2' in df_tracking.columns:
                    df_tracking['X2'] *= 1.2
                if 'Y2' in df_tracking.columns:
                    df_tracking['Y2'] *= 0.8

            # Nettoyage texte
            df_tracking['Event'] = df_tracking['Event'].fillna('').astype(str).str.strip().str.lower().str.title()

            # Classification des zones (logique inversée)
            def classify_zone(x, y):
                if 102 < x <= 120 and 18 < y < 62:
                    return 'Surface Rép.'
                elif 0 <= x < 36:
                    return 'Haute'
                elif 36 <= x <= 90:
                    return 'Médiane'
                elif 90 < x <= 102:
                    return 'Basse'
                else:
                    return 'Médiane'

            df_tracking['Zone'] = df_tracking.apply(lambda row: classify_zone(row['X'], row['Y']), axis=1)

            # Filtres dans la sidebar
            st.sidebar.header("👁️ Filtres Visualisation")
            if player_id:
                tracking_filtered = df_tracking[df_tracking['PlayerID_norm'] == player_id].copy()
            else:
                tracking_filtered = df_tracking.copy()

            if tracking_filtered.empty:
                st.warning("Aucun événement pour ce joueur.")
            else:
                event_options = sorted(tracking_filtered['Event'].dropna().unique())
                zone_options = sorted(tracking_filtered['Zone'].dropna().unique())

                selected_events_vis = st.sidebar.multiselect("Événements", event_options, default=event_options[:min(3, len(event_options))] if event_options else [])
                selected_zones_vis = st.sidebar.multiselect("Zones", zone_options, default=zone_options)

                # Filtre par journée si colonne existe
                if 'Journée' in tracking_filtered.columns:
                    match_options = sorted(tracking_filtered['Journée'].dropna().unique())
                    selected_match = st.sidebar.selectbox("Journée", ["Toutes"] + list(match_options))
                    if selected_match != "Toutes":
                        tracking_filtered = tracking_filtered[tracking_filtered['Journée'] == selected_match]

                # Appliquer filtres
                tracking_filtered = tracking_filtered[
                    tracking_filtered['Event'].isin(selected_events_vis) &
                    tracking_filtered['Zone'].isin(selected_zones_vis)
                ]

                if tracking_filtered.empty:
                    st.warning("Aucun événement ne correspond aux filtres.")
                else:
                    # Palette de couleurs
                    PALETTE_OPTIONS = {
                        'Par défaut (Couleurs spécifiques + Tab20)': 'Par défaut',
                        'Tab20': 'tab20',
                        'Set1': 'Set1',
                        'Viridis': 'viridis',
                        'Plasma': 'plasma',
                        'Coolwarm': 'coolwarm',
                        'Pastel1': 'Pastel1',
                        'Dark2': 'Dark2'
                    }
                    selected_palette = st.sidebar.selectbox("Palette", list(PALETTE_OPTIONS.keys()), index=0)
                    color_palette_name = PALETTE_OPTIONS[selected_palette]

                    base_colors = {
                        'Shot': '#FF4B4B', 'Pass': '#6C9AC3', 'Dribble': '#FFA500',
                        'Cross': '#92c952', 'Tackle': '#A52A2A', 'Interception': '#FFD700',
                        'Clearance': '#00CED1'
                    }

                    def get_event_colors(event_list, palette_name, base_colors_dict):
                        if palette_name == 'Par défaut':
                            cmap_for_others = cm.get_cmap('tab20', max(1, len(event_list)))
                            generated_colors = {event: mcolors.to_hex(cmap_for_others(i)) for i, event in enumerate([e for e in event_list if e not in base_colors_dict])}
                            return {**base_colors_dict, **generated_colors}
                        else:
                            try:
                                cmap_selected = cm.get_cmap(palette_name, max(1, len(event_list)))
                                return {event: mcolors.to_hex(cmap_selected(i)) for i, event in enumerate(event_list)}
                            except ValueError:
                                cmap_fallback = cm.get_cmap('tab20', max(1, len(event_list)))
                                return {event: mcolors.to_hex(cmap_fallback(i)) for i, event in enumerate(event_list)}

                    event_colors = get_event_colors(event_options, color_palette_name, base_colors)

                    # Tableau récap
                    st.subheader("Répartition des événements")
                    zone_counts = tracking_filtered.groupby(['Event', 'Zone']).size().unstack(fill_value=0)
                    st.dataframe(zone_counts)

                    # Visualisation des événements
                    st.subheader("Carte des événements")
                    pitch = Pitch(pitch_color='#0b1220', line_color='#e2e8f0', linewidth=1)
                    fig, ax = pitch.draw(figsize=(10, 6))
                    legend_elements = []

                    for event_type in selected_events_vis:
                        ev_data = tracking_filtered[tracking_filtered['Event'] == event_type]
                        color = event_colors.get(event_type, '#ffffff')
                        has_xy2 = ev_data[['X2', 'Y2']].notna().all(axis=1)

                        if has_xy2.any():
                            pitch.arrows(
                                ev_data[has_xy2]['X'], ev_data[has_xy2]['Y'],
                                ev_data[has_xy2]['X2'], ev_data[has_xy2]['Y2'],
                                color=color, width=2.0, headwidth=6, headlength=4, alpha=0.8, ax=ax
                            )
                        if (~has_xy2).any():
                            pitch.scatter(
                                ev_data[~has_xy2]['X'], ev_data[~has_xy2]['Y'],
                                ax=ax, fc=color, ec='white', lw=0.5, s=80, alpha=0.8
                            )
                        legend_elements.append(Patch(facecolor=color, label=event_type))

                    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5))
                    st.pyplot(fig, use_container_width=True)

                    # Heatmap
                    st.subheader("Heatmap des événements")
                    pitch_hm = Pitch(pitch_type='statsbomb', pitch_color='#0b1220', line_color='#e2e8f0')
                    fig2, ax2 = pitch_hm.draw(figsize=(10, 6))
                    bin_stat = pitch_hm.bin_statistic(tracking_filtered['X'], tracking_filtered['Y'], statistic='count', bins=(6, 5))
                    pitch_hm.heatmap(bin_stat, ax=ax2, cmap='Reds', edgecolor='white', alpha=0.8)
                    pitch_hm.label_heatmap(bin_stat, ax=ax2, str_format='{:.0f}', fontsize=12, color='white', ha='center', va='center')
                    st.pyplot(fig2, use_container_width=True)

# ======================= DONNÉES =======================
# ... (tabs[6] inchangé, anciennement tabs[5])
with tabs[6]:
    st.markdown("#### 📄 Données Brutes et Export")
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Joueurs", df_players.shape[0])
    col2.metric("⚽ Matchs", df_match.shape[0])
    col3.metric("🩺 Wellness", df_well.shape[0])
    if 'df_tracking' in locals() and not df_tracking.empty:
        col4 = st.columns(4)[-1]
        col4.metric("📍 Tracking", df_tracking.shape[0])
    data_view = st.selectbox(
        "Vue des données",
        ["Joueurs", "Matchs", "Wellness", "Tracking", "Statistiques agrégées"]
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
    elif data_view == "Tracking":
        st.markdown("**📍 Données Tracking**")
        if player_id:
            dt_filtered = df_tracking[df_tracking["PlayerID_norm"] == player_id]
            st.dataframe(dt_filtered, use_container_width=True)
        else:
            st.dataframe(df_tracking.head(50), use_container_width=True)
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
        <p style="font-size: 12px;">Version 2.8 • Visualisation Tracking ajoutée • Zones inversées • Filtres dynamiques</p>
    </div>
    """,
    unsafe_allow_html=True
)
