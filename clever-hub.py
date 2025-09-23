# -*- coding: utf-8 -*-
"""
Clever Hub - Plateforme d'analyse de performance footballistique
Version: 2.1
Auteur: C1 - Data Intelligence Team
"""

# ======================= IMPORTS =======================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import unicodedata
import matplotlib.pyplot as plt
# Import modifié - version simplifiée
from mplsoccer import Pitch
import io
from PIL import Image

# ======================= CONFIG =======================
st.set_page_config(
    page_title="Clever Hub - Analyse Footballistique",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================= CONSTANTES =======================
DATA_DIR = Path("data")
CACHE_TTL = 300
POSTE_COORDINATES = {
    'Gardien': (5, 40),
    'Défenseur latéral': (20, 15),
    'Arrière central': (20, 40),
    'Milieu défensif': (40, 40),
    'Milieu box': (45, 25),
    'Milieu relais': (55, 40),
    'Milieu offensif': (65, 40),
    'Ailier gauche': (60, 15),
    'Ailier droit': (60, 65),
    'Attaquant': (80, 40),
    'Attaquant relais': (70, 40),
    'Défaut': (50, 40)
}

BENCHMARKS = {
    "Gardien": {
        'pass_accuracy': 75,
        'prog_passes_per_90': 8,
        'key_passes_per_match': 0.5,
        'shot_accuracy': 25,
        'xg_per_90': 0.05,
        'goals_per_xg': 0.8,
        'duel_win_rate': 40,
        'interceptions_per_90': 1.0,
        'recoveries_per_90': 2,
    },
    "Défenseur latéral": {
        'pass_accuracy': 80,
        'prog_passes_per_90': 6,
        'key_passes_per_match': 0.8,
        'shot_accuracy': 20,
        'xg_per_90': 0.1,
        'goals_per_xg': 1.2,
        'duel_win_rate': 55,
        'interceptions_per_90': 2.0,
        'recoveries_per_90': 6,
    },
    "Arrière central": {
        'pass_accuracy': 85,
        'prog_passes_per_90': 5,
        'key_passes_per_match': 0.3,
        'shot_accuracy': 20,
        'xg_per_90': 0.1,
        'goals_per_xg': 1.5,
        'duel_win_rate': 60,
        'interceptions_per_90': 2.5,
        'recoveries_per_90': 7,
    },
    "Milieu défensif": {
        'pass_accuracy': 88,
        'prog_passes_per_90': 7,
        'key_passes_per_match': 1.0,
        'shot_accuracy': 25,
        'xg_per_90': 0.15,
        'goals_per_xg': 1.2,
        'duel_win_rate': 55,
        'interceptions_per_90': 2.0,
        'recoveries_per_90': 8,
    },
    "Milieu box": {
        'pass_accuracy': 82,
        'prog_passes_per_90': 4,
        'key_passes_per_match': 1.2,
        'shot_accuracy': 35,
        'xg_per_90': 0.25,
        'goals_per_xg': 1.0,
        'duel_win_rate': 50,
        'interceptions_per_90': 2.0,
        'recoveries_per_90': 6,
    },
    "Milieu relais": {
        'pass_accuracy': 85,
        'prog_passes_per_90': 6,
        'key_passes_per_match': 1.8,
        'shot_accuracy': 30,
        'xg_per_90': 0.2,
        'goals_per_xg': 1.1,
        'duel_win_rate': 50,
        'interceptions_per_90': 1.8,
        'recoveries_per_90': 7,
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
    "Défaut": { # Pour les postes non définis
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

# ======================= STYLES =======================
st.markdown("""
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
""", unsafe_allow_html=True)

# ======================= HELPERS =======================
def get_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0

def to_num(x) -> pd.Series:
    """Série numérique robuste — retourne TOUJOURS une pd.Series"""
    if isinstance(x, pd.Series):
        s = x.astype(str).str.replace(",", ".", regex=False)
    else:
        s = pd.Series([str(x)]).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors='coerce').fillna(0)

def norm_col(c):
    """Normalise le nom d'une colonne"""
    c = unicodedata.normalize("NFKD", str(c)).encode("ascii", "ignore").decode("ascii")
    return c.strip().lower().replace(" ", " ")

def rename_like(df: pd.DataFrame, mapping: dict):
    if df.empty:
        return df
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
    
    # Passing Efficiency
    passes_tent_col = player_data.get("Passe tentées", pd.Series([0]))
    passes_comp_col = player_data.get("Passe complete", pd.Series([0]))
    passes_tent = to_num(passes_tent_col).sum()
    passes_comp = to_num(passes_comp_col).sum()
    passing_eff = (passes_comp / passes_tent * 100) if passes_tent > 0 else 0
    
    # Duel Success
    duel_tot_col_name = "Duel tenté" if "Duel tenté" in player_data.columns else "Duel tente"
    duels_tent_col = player_data.get(duel_tot_col_name, pd.Series([0]))
    duels_gagnes_col = player_data.get("Duel gagne", pd.Series([0]))
    duels_tent = to_num(duels_tent_col).sum()
    duels_gagnes = to_num(duels_gagnes_col).sum()
    duel_success = (duels_gagnes / duels_tent * 100) if duels_tent > 0 else 0
    
    # Attacking Contribution (xG + Goals)
    goals = to_num(player_data.get("Buts", pd.Series([0]))).sum()
    xg = to_num(player_data.get("xG", pd.Series([0]))).sum()
    attacking_score = (goals + xg) * 10  # Normalisation arbitraire
    
    # Defensive Contribution (Interceptions + Recoveries)
    interceptions = to_num(player_data.get("Interception", pd.Series([0]))).sum()
    recoveries = to_num(player_data.get("Recuperation du ballon", pd.Series([0]))).sum()
    defensive_score = (interceptions + recoveries) * 5  # Normalisation arbitraire
    
    # Ball Retention (Progressive Passes)
    prog_passes = to_num(player_data.get("Passe progressive", pd.Series([0]))).sum()
    ball_retention_score = prog_passes * 2  # Normalisation arbitraire
    
    # Score final pondéré (0-100)
    score = (
        weights['passing_efficiency'] * min(passing_eff, 100) +
        weights['duel_success'] * min(duel_success, 100) +
        weights['attacking_contribution'] * min(attacking_score, 100) +
        weights['defensive_contribution'] * min(defensive_score, 100) +
        weights['ball_retention'] * min(ball_retention_score, 100)
    )
    
    return round(score, 1)

def calculate_kpis(data, total_min, total_matches, player_id, df_players):
    """Calcule les KPIs pour un joueur"""
    kpis = {}
    
    # Récupérer le poste du joueur
    poste = "Défaut"
    if not df_players.empty:
        player_info = df_players[df_players["PlayerID_norm"] == player_id]
        if not player_info.empty:
            poste = player_info.iloc[0].get('Poste Détail', player_info.iloc[0].get('Poste', 'Défaut'))
    
    # Benchmarks par poste
    kpis['benchmarks'] = BENCHMARKS.get(poste, BENCHMARKS['Défaut'])
    
    # Précision des passes
    passes_tent_col = data.get("Passe tentées", pd.Series([0]))
    passes_comp_col = data.get("Passe complete", pd.Series([0]))
    passes_tent = to_num(passes_tent_col).sum()
    passes_comp = to_num(passes_comp_col).sum()
    kpis['pass_accuracy'] = (passes_comp / passes_tent * 100) if passes_tent > 0 else 0
    
    # Passes progressives
    prog_passes_col = data.get("Passe progressive", pd.Series([0]))
    prog_passes = to_num(prog_passes_col).sum()
    kpis['prog_passes_per_90'] = (prog_passes / total_min * 90) if total_min > 0 else 0
    
    # Passes décisives
    key_passes_col = data.get("Passe decisive", pd.Series([0])) if "Passe decisive" in data.columns else pd.Series([0])
    key_passes = to_num(key_passes_col).sum()
    kpis['key_passes_per_match'] = key_passes / total_matches if total_matches > 0 else 0
    
    # Précision des tirs
    tirs_col = data.get("Tir", pd.Series([0]))
    tirs_cadres_col = data.get("Tir cadre", pd.Series([0]))
    tirs = to_num(tirs_col).sum()
    tirs_cadres = to_num(tirs_cadres_col).sum()
    kpis['shot_accuracy'] = (tirs_cadres / tirs * 100) if tirs > 0 else 0
    
    # xG/90
    xg_col = data.get("xG", pd.Series([0]))
    xg = to_num(xg_col).sum()
    kpis['xg_per_90'] = (xg / total_min * 90) if total_min > 0 else 0
    
    # Efficacité buts/xG
    goals_col = data.get("Buts", pd.Series([0]))
    goals = to_num(goals_col).sum()
    kpis['goals_per_xg'] = (goals / xg) if xg > 0 else 0
    
    # Taux de duels gagnés
    duel_tot_col_name = "Duel tenté" if "Duel tenté" in data.columns else "Duel tente"
    duels_tent_col = data.get(duel_tot_col_name, pd.Series([0]))
    duels_gagnes_col = data.get("Duel gagne", pd.Series([0]))
    duels_tent = to_num(duels_tent_col).sum()
    duels_gagnes = to_num(duels_gagnes_col).sum()
    kpis['duel_win_rate'] = (duels_gagnes / duels_tent * 100) if duels_tent > 0 else 0
    
    # Interceptions/90
    interceptions_col = data.get("Interception", pd.Series([0]))
    interceptions = to_num(interceptions_col).sum()
    kpis['interceptions_per_90'] = (interceptions / total_min * 90) if total_min > 0 else 0
    
    # Récupérations/90
    recoveries_col = data.get("Recuperation du ballon", pd.Series([0]))
    recoveries = to_num(recoveries_col).sum()
    kpis['recoveries_per_90'] = (recoveries / total_min * 90) if total_min > 0 else 0
    
    return kpis

def create_radar_chart(values, categories, title):
    """Crée un graphique radar avec Plotly"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=title,
        line_color='#3b82f6',
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title=title,
        font=dict(color="white"),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def calc_radar_metrics(dm):
    """Calcule les métriques pour le radar chart"""
    if dm.empty:
        return [0]*6
    
    matches = len(dm)
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
        min(xg_per_match * 20, 100),  # Normalisation arbitraire
        min(buts_per_match * 50, 100),  # Normalisation arbitraire
        playtime_pct
    ]

# ======================= CHARGEMENT DES DONNÉES =======================
@st.cache_data(ttl=CACHE_TTL)
def load_data():
    """Charge toutes les données depuis les fichiers JSON"""
    data = {}
    for file in DATA_DIR.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data[file.stem] = pd.json_normalize(json.load(f))
        except Exception as e:
            st.error(f"Erreur lors du chargement de {file.name}: {e}")
            data[file.stem] = pd.DataFrame()
    return data

# ======================= INTERFACE =======================
st.markdown('<div class="hero"><h1>⚽ Clever Hub</h1><p>Plateforme d\'analyse de performance footballistique</p></div>', unsafe_allow_html=True)
st.write("")

# Charger les données
try:
    data = load_data()
except Exception as e:
    st.error(f"Erreur critique lors du chargement des données: {e}")
    st.stop()

# Vérifier que les données sont présentes
if not data:
    st.warning("⚠️ Aucune donnée trouvée dans le dossier 'data'. Veuillez vérifier les fichiers.")
    st.stop()

# Extraire les DataFrames
df_players = data.get("Joueur", pd.DataFrame())
df_match = data.get("Match", pd.DataFrame())
df_well = data.get("Wellness", pd.DataFrame())

# Normaliser les IDs
for df in (df_players, df_match, df_well):
    if not df.empty and "PlayerID" in df.columns:
        df["PlayerID_norm"] = df["PlayerID"].astype(str).str.strip()

# Mapping des colonnes
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
    "duel gagne": "Duel gagne",
    "ballon recupere": "Ballon récupéré",
    "passe decisive": "Passe decisive",
    "passe progressive": "Passe progressive",
    "interception": "Interception",
    "recuperation du ballon": "Recuperation du ballon",
    "ballon perdu": "Ballon perdu",
    "faute commise": "Faute commise",
    "faute subie": "Faute subie",
    "but": "Buts",
    "tir": "Tir",
    "tackle": "Tackle",
    "duel aerien gagne": "Duel aérien gagné",
    "duel aerien perdu": "Duel aérien perdu",
    "duel au sol gagne": "Duel au sol gagné",
    "duel au sol perdu": "Duel au sol perdu"
}

# Renommer les colonnes
df_players = rename_like(df_players, mapping)
df_match = rename_like(df_match, mapping)

# Convertir les dates
if not df_well.empty and "DATE" in df_well.columns:
    df_well["DATE"] = pd.to_datetime(df_well["DATE"], errors="coerce")

# ======================= SIDEBAR =======================
st.sidebar.markdown("### 🎯 Paramètres d'analyse")

# Créer la map joueur
player_map = {}
if not df_players.empty and {"PlayerID_norm", "Prénom", "Nom"}.issubset(df_players.columns):
    for _, r in df_players.iterrows():
        display = f"{r.get('Prénom','')} {r.get('Nom','')} (#{str(r.get('PlayerID'))})"
        player_map[display] = str(r.get("PlayerID"))
elif not df_match.empty and "PlayerID_norm" in df_match.columns:
    for pid in df_match["PlayerID_norm"].unique():
        player_map[f"Joueur #{pid}"] = pid

# Sélection du joueur
sel_display = st.sidebar.selectbox("👤 Sélectionner un joueur", list(player_map.keys()), index=0 if player_map else 0)
player_id = player_map.get(sel_display)

# Mode comparaison
compare_mode = st.sidebar.checkbox("🔄 Mode Comparaison")
compare_player_id = None
compare_player = None

if compare_mode and player_id:
    other_players = {k: v for k, v in player_map.items() if v != player_id}
    if other_players:
        compare_player = st.sidebar.selectbox("👥 Joueur à comparer", list(other_players.keys()))
        compare_player_id = other_players.get(compare_player)

# ======================= ONGLETS =======================
tabs = st.tabs(["📊 Dashboard", "📋 Données Brutes", "📈 Performance Saison", "🎯 Analyse Match", "🔍 Analyse Comparative"])

# ======================= DASHBOARD =======================
with tabs[0]:
    st.markdown('<div class="hero"><span class="pill">📊 Vue d\'ensemble du joueur</span></div>', unsafe_allow_html=True)
    st.write("")
    
    if player_id:
        # LIGNE 1: Profil Joueur + Terrain Vertical
        st.markdown("##### 👤 Profil Joueur & Position")
        col_profile, col_terrain = st.columns([1, 1], gap="large")
        
        with col_profile:
            if not df_players.empty and "PlayerID_norm" in df_players.columns:
                p = df_players[df_players["PlayerID_norm"] == player_id]
                if not p.empty:
                    p = p.iloc[0]
                    
                    # Calculer les minutes totales pour ce joueur
                    total_minutes = 0
                    if not df_match.empty:
                        dm = df_match[df_match["PlayerID_norm"] == player_id]
                        if not dm.empty:
                            total_minutes = to_num(dm.get("Minutes Jouées", 0)).sum()
                    
                    perf_score = calculate_performance_score(dm if 'dm' in locals() and not dm.empty else pd.DataFrame())
                    
                    # Afficher les infos du joueur
                    st.markdown(f"""
                    <div class="glass">
                        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px;">
                            <div class="avatar">{p.get('Prénom', '')[0] if p.get('Prénom') else '?'}</div>
                            <div>
                                <h3 style="margin: 0; font-size: 22px;">{p.get('Prénom', '')} {p.get('Nom', '')}</h3>
                                <div style="color: var(--muted); font-size: 14px;">#{p.get('PlayerID')}</div>
                            </div>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <div style="font-size: 13px; color: var(--muted);">Poste</div>
                                <div style="font-weight: 600;">{p.get('Poste', 'Non défini')}</div>
                            </div>
                            <div>
                                <div style="font-size: 13px; color: var(--muted);">Âge</div>
                                <div style="font-weight: 600;">{p.get('Age', 'N/A')} ans</div>
                            </div>
                            <div>
                                <div style="font-size: 13px; color: var(--muted);">Taille</div>
                                <div style="font-weight: 600;">{p.get('Taille', 'N/A')} cm</div>
                            </div>
                            <div>
                                <div style="font-size: 13px; color: var(--muted);">Pied</div>
                                <div style="font-weight: 600;">{p.get('Pied', 'N/A')}</div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 16px;">
                            <div style="font-size: 13px; color: var(--muted); margin-bottom: 4px;">Score Performance Global</div>
                            <div style="font-size: 28px; font-weight: 800; color: {'#10b981' if perf_score > 70 else '#f59e0b' if perf_score > 50 else '#ef4444'};">
                                {perf_score}/100
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col_terrain:
            if not df_players.empty and "PlayerID_norm" in df_players.columns:
                p = df_players[df_players["PlayerID_norm"] == player_id]
                if not p.empty:
                    p = p.iloc[0]
                    poste_detail = p.get('Poste Détail', p.get('Poste', 'Défaut'))
                    x_pos, y_pos = POSTE_COORDINATES.get(poste_detail, POSTE_COORDINATES['Défaut'])
                    
                    # ==================== MODIFICATION ICI ====================
                    # Créer un pitch (terrain) avec mplsoccer (version simplifiée)
                    pitch = Pitch(half=False) # Utilise les paramètres par défaut de mplsoccer
                    fig, ax = pitch.draw()
                    # ==========================================================

                    # Ajouter le joueur sur le terrain
                    ax.scatter(x_pos, y_pos, s=200, color='red', edgecolors='black', linewidth=1, zorder=5)
                    ax.text(x_pos, y_pos + 2, poste_detail, ha='center', va='bottom', fontsize=9, color='white', weight='bold')

                    # Sauvegarder l'image du pitch dans un buffer
                    buf = io.BytesIO()
                    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
                    buf.seek(0)
                    plt.close(fig) # Fermer la figure pour libérer la mémoire

                    # Afficher l'image dans Streamlit
                    st.image(buf, caption="", use_column_width=True)

        # LIGNE 2: KPIs de la Saison
        st.markdown("##### 📊 KPIs Saison")
        if not df_match.empty and "PlayerID_norm" in df_match.columns:
            dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
            if not dm.empty:
                total_minutes = to_num(dm.get("Minutes Jouées")).sum()
                total_matches = len(dm)
                kpis_season = calculate_kpis(dm, total_minutes, total_matches, player_id, df_players)
                
                # Barre de progression minutes
                st.markdown(f"##### ⏱️ Minutes Jouées: {int(total_minutes)} (Moyenne: {int(total_minutes/total_matches) if total_matches > 0 else 0}/match)")
                max_minutes_season = 3420
                progress_pct = min(total_minutes / max_minutes_season * 100, 100) if max_minutes_season > 0 else 0
                progress_color = "#10b981" if progress_pct > 70 else "#3b82f6" if progress_pct > 40 else "#f59e0b"
                st.markdown(f"""
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress_pct}%; background-color: {progress_color};"></div>
                </div>
                <div style="text-align: right; font-size: 12px; color: var(--muted);">{progress_pct:.1f}% de la saison</div>
                """, unsafe_allow_html=True)
                
                # Cartes KPIs
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
                        <h3>🔁 Précision Passes</h3>
                        <div class="value" style="color: {color};">{kpis_season['pass_accuracy']:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with cols[2]:
                    color = "#10b981" if kpis_season['duel_win_rate'] > 60 else "#f59e0b" if kpis_season['duel_win_rate'] > 50 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>🤼 Taux Duels Gagnés</h3>
                        <div class="value" style="color: {color};">{kpis_season['duel_win_rate']:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Radar Chart
                st.markdown("##### 📈 Profil de Performance")
                radar_categories = ['Passes', 'Duels', 'Tirs', 'xG/Match', 'Buts/Match', 'Temps de Jeu']
                radar_values = calc_radar_metrics(dm)
                fig_radar = create_radar_chart(radar_values, radar_categories, f"Performance - {p.get('Prénom', '')} {p.get('Nom', '')}")
                st.plotly_chart(fig_radar, use_container_width=True)
                
                # KPIs Dashboard détaillés
                st.markdown("#### 📊 Synthèse Visuelle des KPIs")
                st.caption("Comparaison par rapport aux benchmarks spécifiques à votre poste")
                
                kpi_names = [
                    'Précision Passes', 'Passes Progressives', 'Passes Décisives',
                    'Précision Tirs', 'xG Généré', 'Efficacité Finition',
                    'Taux Duel Gagné', 'Interceptions', 'Récupérations'
                ]
                kpi_values = [
                    kpis_season['pass_accuracy'],
                    kpis_season['prog_passes_per_90'],
                    kpis_season['key_passes_per_match'],
                    kpis_season['shot_accuracy'],
                    kpis_season['xg_per_90'],
                    kpis_season['goals_per_xg'],
                    kpis_season['duel_win_rate'],
                    kpis_season['interceptions_per_90'],
                    kpis_season['recoveries_per_90']
                ]
                benchmarks = list(kpis_season['benchmarks'].values())
                
                # Créer le DataFrame pour le bar chart
                kpi_df = pd.DataFrame({
                    'Métrique': kpi_names,
                    'Valeur': kpi_values,
                    'Benchmark': benchmarks
                })
                
                # Normaliser certaines valeurs pour la visualisation
                kpi_df['Valeur_Vis'] = kpi_df['Valeur']
                kpi_df['Benchmark_Vis'] = kpi_df['Benchmark']
                
                # Ajustements pour visualisation
                kpi_df.loc[kpi_df['Métrique'] == 'Passes Progressives', ['Valeur_Vis', 'Benchmark_Vis']] *= 10
                kpi_df.loc[kpi_df['Métrique'] == 'Passes Décisives', ['Valeur_Vis', 'Benchmark_Vis']] *= 50
                kpi_df.loc[kpi_df['Métrique'] == 'xG Généré', ['Valeur_Vis', 'Benchmark_Vis']] *= 150
                kpi_df.loc[kpi_df['Métrique'] == 'Efficacité Finition', ['Valeur_Vis', 'Benchmark_Vis']] *= 70
                kpi_df.loc[kpi_df['Métrique'] == 'Interceptions', ['Valeur_Vis', 'Benchmark_Vis']] *= 30
                kpi_df.loc[kpi_df['Métrique'] == 'Récupérations', ['Valeur_Vis', 'Benchmark_Vis']] *= 10
                
                # Limiter à 100 pour le graphique
                kpi_df['Valeur_Vis'] = kpi_df['Valeur_Vis'].clip(upper=100)
                kpi_df['Benchmark_Vis'] = kpi_df['Benchmark_Vis'].clip(upper=100)
                
                # Créer le bar chart avec Plotly
                fig_kpi = go.Figure()
                fig_kpi.add_trace(go.Bar(
                    x=kpi_df['Métrique'],
                    y=kpi_df['Valeur_Vis'],
                    name='Joueur',
                    marker_color='#3b82f6'
                ))
                fig_kpi.add_trace(go.Bar(
                    x=kpi_df['Métrique'],
                    y=kpi_df['Benchmark_Vis'],
                    name='Benchmark',
                    marker_color='#94a3b8'
                ))
                fig_kpi.update_layout(
                    barmode='group',
                    title="Comparaison KPIs vs Benchmark",
                    xaxis_title="Métriques",
                    yaxis_title="Valeur (normalisée 0-100)",
                    font=dict(color="white"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_kpi, use_container_width=True)

# ======================= DONNÉES BRUTES =======================
with tabs[1]:
    st.markdown('<div class="hero"><span class="pill">📋 Données Brutes</span></div>', unsafe_allow_html=True)
    st.write("")
    
    data_view = st.radio("Type de données", ["Joueurs", "Matchs", "Wellness", "Statistiques agrégées"], horizontal=True)
    
    if data_view == "Joueurs":
        st.markdown("**👥 Données Joueurs**")
        if player_id:
            dp_filtered = df_players[df_players["PlayerID_norm"] == player_id]
            st.dataframe(dp_filtered, use_container_width=True)
        else:
            st.dataframe(df_players.head(50), use_container_width=True)
            
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
                    agg_stats.append(stats)
            
            df_agg = pd.DataFrame(agg_stats)
            st.dataframe(df_agg, use_container_width=True)

# ======================= PERFORMANCE SAISON =======================
with tabs[2]:
    st.markdown('<div class="hero"><span class="pill">📈 Performance Saison</span></div>', unsafe_allow_html=True)
    st.write("")
    
    if player_id and not df_match.empty:
        dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
        if not dm.empty:
            # Vue par match
            st.markdown("##### 📊 Performance par Match")
            match_metrics = []
            for _, match in dm.iterrows():
                match_data = pd.DataFrame([match])
                minutes = to_num(match.get("Minutes Jouées", 0)).iloc[0]
                match_kpis = calculate_kpis(match_data, minutes, 1, player_id, df_players)
                match_metrics.append({
                    'Journée': match.get('Journée', 'N/A'),
                    'Adversaire': match.get('Adversaire', 'N/A'),
                    'Minutes': int(minutes),
                    'xG': match_kpis['xg_per_90'],
                    'Passes_%': match_kpis['pass_accuracy'],
                    'Duels_%': match_kpis['duel_win_rate'],
                    'Score': calculate_performance_score(match_data)
                })
            
            df_match_metrics = pd.DataFrame(match_metrics)
            st.dataframe(df_match_metrics, use_container_width=True)
            
            # Graphiques
            if len(df_match_metrics) > 1:
                st.markdown("##### 📈 Évolution dans la Saison")
                
                # xG par match
                fig_xg = px.line(df_match_metrics, x='Journée', y='xG', title='Évolution xG/90 par Match')
                fig_xg.update_layout(
                    font=dict(color="white"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_xg, use_container_width=True)
                
                # Score performance
                fig_score = px.line(df_match_metrics, x='Journée', y='Score', title='Évolution Score Performance par Match')
                fig_score.update_layout(
                    font=dict(color="white"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_score, use_container_width=True)

# ======================= ANALYSE MATCH =======================
with tabs[3]:
    st.markdown('<div class="hero"><span class="pill">🎯 Analyse Match</span></div>', unsafe_allow_html=True)
    st.write("")
    
    if player_id and not df_match.empty:
        dm = df_match[df_match["PlayerID_norm"] == player_id].copy()
        if not dm.empty:
            analysis_mode = st.radio("Mode d'analyse", ["📊 Vue saison complète", "🎯 Match spécifique"], horizontal=True, key="match_mode")
            
            if analysis_mode == "🎯 Match spécifique":
                if "Journée" in dm.columns and "Adversaire" in dm.columns:
                    match_options = []
                    for _, row in dm.iterrows():
                        journee = row.get('Journée', 'N/A')
                        adversaire = row.get('Adversaire', 'N/A')
                        match_options.append(f"Journée {journee} - vs {adversaire}")
                    
                    selected_match_display = st.selectbox("Sélectionner un match", match_options)
                    if selected_match_display:
                        selected_index = match_options.index(selected_match_display)
                        selected_match = dm.iloc[selected_index:selected_index+1]
                    else:
                        selected_match = dm.head(1)
                else:
                    selected_match = dm.head(1)
                    st.info("Informations de match incomplètes, affichage du premier match disponible")
            else:
                selected_match = dm
            
            if not selected_match.empty:
                match_row = selected_match.iloc[0]
                total_min_scalar = to_num(match_row.get("Minutes Jouées", 0)).iloc[0]
                
                st.markdown(f"##### 📋 Match: Journée {match_row.get('Journée', 'N/A')} - vs {match_row.get('Adversaire', 'N/A')}")
                
                # KPIs du match
                kpis_match = calculate_kpis(selected_match, total_min_scalar, 1, player_id, df_players)
                
                synth_col1, synth_col2, synth_col3 = st.columns(3)
                
                with synth_col1:
                    pass_color = "#10b981" if kpis_match['pass_accuracy'] > kpis_match['benchmarks']['pass_accuracy'] else "#f59e0b" if kpis_match['pass_accuracy'] > kpis_match['benchmarks']['pass_accuracy'] * 0.9 else "#ef4444"
                    shot_color = "#10b981" if kpis_match['shot_accuracy'] > kpis_match['benchmarks']['shot_accuracy'] else "#f59e0b" if kpis_match['shot_accuracy'] > kpis_match['benchmarks']['shot_accuracy'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">Précision Passes</div>
                            <div class="value" style="color: {pass_color};">{kpis_match['pass_accuracy']:.1f}%</div>
                        </div>
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">Précision Tirs</div>
                            <div class="value" style="color: {shot_color};">{kpis_match['shot_accuracy']:.1f}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with synth_col2:
                    xg_color = "#10b981" if kpis_match['xg_per_90'] > kpis_match['benchmarks']['xg_per_90'] else "#f59e0b" if kpis_match['xg_per_90'] > kpis_match['benchmarks']['xg_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">xG</div>
                            <div class="value" style="color: {xg_color};">{match_row.get('xG', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">xG/90</div>
                            <div class="value" style="color: {xg_color};">{kpis_match['xg_per_90']:.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with synth_col3:
                    minutes_color = "#10b981" if total_min_scalar > 60 else "#f59e0b" if total_min_scalar > 30 else "#ef4444"
                    st.markdown(f"""
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">Buts</div>
                            <div class="value" style="color: #3b82f6;">{int(to_num(match_row.get('Buts', 0)).iloc[0])}</div>
                        </div>
                        <div class="metric-card">
                            <div style="font-size: 14px; color: var(--muted);">Minutes Jouées</div>
                            <div class="value" style="color: {minutes_color};">{int(total_min_scalar)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Détail Distribution
                st.markdown("##### 🔁 Distribution")
                passes_tot = to_num(match_row.get("Passe tentées", 0)).iloc[0]
                passes_comp = to_num(match_row.get("Passe complete", 0)).iloc[0]
                prog_passes = to_num(match_row.get("Passe progressive", 0)).iloc[0]
                key_passes = to_num(match_row.get("Passe decisive", 0)).iloc[0] if "Passe decisive" in match_row else 0
                
                dist_cols = st.columns(3)
                with dist_cols[0]:
                    color = "#10b981" if kpis_match['pass_accuracy'] > kpis_match['benchmarks']['pass_accuracy'] else "#f59e0b" if kpis_match['pass_accuracy'] > kpis_match['benchmarks']['pass_accuracy'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Passes</h3>
                        <div class="value" style="color: {color};">{int(passes_comp)}/{int(passes_tot)}</div>
                        <div style="font-size: 12px; color: var(--muted);">{kpis_match['pass_accuracy']:.1f}% réussies</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with dist_cols[1]:
                    color = "#10b981" if kpis_match['prog_passes_per_90'] > kpis_match['benchmarks']['prog_passes_per_90'] else "#f59e0b" if kpis_match['prog_passes_per_90'] > kpis_match['benchmarks']['prog_passes_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Passes Progressives</h3>
                        <div class="value" style="color: {color};">{kpis_match['prog_passes_per_90']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/90 min</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with dist_cols[2]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Passes Décisives</h3>
                        <div class="value" style="color: #3b82f6;">{int(key_passes)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Détail Offense
                st.markdown("##### ⚽ Offense")
                tirs = to_num(match_row.get("Tir", 0)).iloc[0]
                tirs_cadres = to_num(match_row.get("Tir cadre", 0)).iloc[0]
                xg = to_num(match_row.get("xG", 0)).iloc[0]
                buts = to_num(match_row.get("Buts", 0)).iloc[0]
                
                off_cols = st.columns(3)
                with off_cols[0]:
                    color = "#10b981" if kpis_match['shot_accuracy'] > kpis_match['benchmarks']['shot_accuracy'] else "#f59e0b" if kpis_match['shot_accuracy'] > kpis_match['benchmarks']['shot_accuracy'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Tirs</h3>
                        <div class="value" style="color: {color};">{int(tirs_cadres)}/{int(tirs)}</div>
                        <div style="font-size: 12px; color: var(--muted);">{kpis_match['shot_accuracy']:.1f}% cadrés</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with off_cols[1]:
                    color = "#10b981" if xg > kpis_match['benchmarks']['xg_per_90'] else "#f59e0b" if xg > kpis_match['benchmarks']['xg_per_90'] * 0.5 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>xG</h3>
                        <div class="value" style="color: {color};">{xg:.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with off_cols[2]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Buts</h3>
                        <div class="value" style="color: #3b82f6;">{int(buts)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Détail Défense
                st.markdown("##### 🛡️ Défense")
                duel_tot_col_name = "Duel tenté" if "Duel tenté" in dm.columns else "Duel tente"
                duels_tent = to_num(match_row.get(duel_tot_col_name, 0)).iloc[0]
                duels_gagnes = to_num(match_row.get("Duel gagne", 0)).iloc[0]
                interceptions = to_num(match_row.get("Interception", 0)).iloc[0]
                recoveries = to_num(match_row.get("Recuperation du ballon", 0)).iloc[0]
                
                def_cols = st.columns(3)
                with def_cols[0]:
                    color = "#10b981" if kpis_match['duel_win_rate'] > kpis_match['benchmarks']['duel_win_rate'] else "#f59e0b" if kpis_match['duel_win_rate'] > kpis_match['benchmarks']['duel_win_rate'] * 0.9 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Duels</h3>
                        <div class="value" style="color: {color};">{int(duels_gagnes)}/{int(duels_tent)}</div>
                        <div style="font-size: 12px; color: var(--muted);">{kpis_match['duel_win_rate']:.1f}% gagnés</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with def_cols[1]:
                    color = "#10b981" if kpis_match['interceptions_per_90'] > kpis_match['benchmarks']['interceptions_per_90'] else "#f59e0b" if kpis_match['interceptions_per_90'] > kpis_match['benchmarks']['interceptions_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Interceptions</h3>
                        <div class="value" style="color: {color};">{kpis_match['interceptions_per_90']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/90 min</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with def_cols[2]:
                    color = "#10b981" if kpis_match['recoveries_per_90'] > kpis_match['benchmarks']['recoveries_per_90'] else "#f59e0b" if kpis_match['recoveries_per_90'] > kpis_match['benchmarks']['recoveries_per_90'] * 0.8 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Récupérations</h3>
                        <div class="value" style="color: {color};">{kpis_match['recoveries_per_90']:.1f}</div>
                        <div style="font-size: 12px; color: var(--muted);">/90 min</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")

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
            
            # Statistiques de base
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
            with kpi_cols[0]:
                p1_val, p2_val = p1_matches, p2_matches
                winner = player1_name if p1_val > p2_val else player2_name if p2_val > p1_val else "Égalité"
                st.metric("Matchs", f"{p1_val} vs {p2_val}", f"🏆 {winner}" if winner != "Égalité" else "Égalité")
            
            with kpi_cols[1]:
                p1_val, p2_val = p1_minutes, p2_minutes
                winner = player1_name if p1_val > p2_val else player2_name if p2_val > p1_val else "Égalité"
                st.metric("Minutes", f"{p1_val} vs {p2_val}", f"🏆 {winner}" if winner != "Égalité" else "Égalité")
            
            with kpi_cols[2]:
                p1_val, p2_val = p1_buts, p2_buts
                winner = player1_name if p1_val > p2_val else player2_name if p2_val > p1_val else "Égalité"
                st.metric("Buts", f"{p1_val} vs {p2_val}", f"🏆 {winner}" if winner != "Égalité" else "Égalité")
            
            with kpi_cols[3]:
                p1_val, p2_val = round(p1_xg, 2), round(p2_xg, 2)
                winner = player1_name if p1_val > p2_val else player2_name if p2_val > p1_val else "Égalité"
                st.metric("xG Total", f"{p1_val} vs {p2_val}", f"🏆 {winner}" if winner != "Égalité" else "Égalité")
            
            with kpi_cols[4]:
                p1_val, p2_val = p1_passes, p2_passes
                winner = player1_name if p1_val > p2_val else player2_name if p2_val > p1_val else "Égalité"
                st.metric("Passes Complétées", f"{p1_val} vs {p2_val}", f"🏆 {winner}" if winner != "Égalité" else "Égalité")
            
            # Radar Charts Comparatifs
            st.markdown("##### 📊 Profils de Performance Comparés")
            col1, col2 = st.columns(2)
            
            radar_categories = ['Passes', 'Duels', 'Tirs', 'xG/Match', 'Buts/Match', 'Temps de Jeu']
            
            with col1:
                p1_radar = calc_radar_metrics(dm1)
                fig1 = create_radar_chart(p1_radar, radar_categories, f"Performance - {player1_name}")
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                p2_radar = calc_radar_metrics(dm2)
                fig2 = create_radar_chart(p2_radar, radar_categories, f"Performance - {player2_name}")
                st.plotly_chart(fig2, use_container_width=True)
            
            # Tableau comparatif détaillé
            st.markdown("##### 📈 Comparaison Détaillée des KPIs")
            
            # Calculer les KPIs pour les deux joueurs
            kpis1 = calculate_kpis(dm1, p1_minutes, p1_matches, player_id, df_players)
            kpis2 = calculate_kpis(dm2, p2_minutes, p2_matches, compare_player_id, df_players)
            
            # Créer le tableau comparatif
            comp_data = []
            metrics = [
                ('Précision Passes', kpis1['pass_accuracy'], kpis2['pass_accuracy']),
                ('Passes Progressives/90', kpis1['prog_passes_per_90'], kpis2['prog_passes_per_90']),
                ('Passes Décisives/Match', kpis1['key_passes_per_match'], kpis2['key_passes_per_match']),
                ('Précision Tirs', kpis1['shot_accuracy'], kpis2['shot_accuracy']),
                ('xG/90', kpis1['xg_per_90'], kpis2['xg_per_90']),
                ('Efficacité Finition (Buts/xG)', kpis1['goals_per_xg'], kpis2['goals_per_xg']),
                ('Taux Duels Gagnés', kpis1['duel_win_rate'], kpis2['duel_win_rate']),
                ('Interceptions/90', kpis1['interceptions_per_90'], kpis2['interceptions_per_90']),
                ('Récupérations/90', kpis1['recoveries_per_90'], kpis2['recoveries_per_90'])
            ]
            
            for metric, val1, val2 in metrics:
                winner = player1_name if val1 > val2 else player2_name if val2 > val1 else "Égalité"
                comp_data.append({
                    'Métrique': metric,
                    f'{player1_name}': round(val1, 2),
                    f'{player2_name}': round(val2, 2),
                    'Avantage': winner
                })
            
            df_comp = pd.DataFrame(comp_data)
            st.dataframe(df_comp, use_container_width=True)

# ======================= FOOTER =======================
st.markdown("---")
st.caption("⚽ Clever Hub - Plateforme d'analyse footballistique - Données mises à jour en temps réel")
