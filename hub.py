# -*- coding: utf-8 -*-
# Football Pro Performance Hub — version chemin fixe (local), sans sidebar

import os
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------------------
# 0) Config de page
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Football Pro Performance Hub", layout="wide", page_icon="⚽")

# ------------------------------------------------------------------------------
# 1) Chargement des données — chemin FIXE + cache invalidé sur modification
# ------------------------------------------------------------------------------
EXCEL_PATH = Path("/Users/abbesaine/Desktop/Hub/Football-Hub-all-in-one.xlsx").expanduser()

if not EXCEL_PATH.exists():
    st.error(
        f"📂 Fichier introuvable : {EXCEL_PATH}\n\n"
        "Vérifie que le chemin est exact sur CETTE machine.\n"
        "Astuce macOS : Finder → clic droit en maintenant ⌥ Option → « Copier le nom du chemin »."
    )
    st.stop()

file_mtime = EXCEL_PATH.stat().st_mtime  # dernière modification (secondes)

@st.cache_data(show_spinner=False)
def load_data_cached(path_str: str, mtime: float):
    """
    Lis l'Excel au chemin donné.
    Le cache est invalidé automatiquement quand 'mtime' change.
    """
    xfile = pd.ExcelFile(path_str)

    def pick_sheet(candidates):
        names = {s.lower().strip(): s for s in xfile.sheet_names}
        for c in candidates:
            if c in xfile.sheet_names:
                return c
            k = c.lower().strip()
            if k in names:
                return names[k]
        raise ValueError(f"Feuille introuvable. Présentes: {xfile.sheet_names} — Recherché: {candidates}")

    joueur_sheet = pick_sheet(["Joueur", "Joueurs", "Players"])
    match_sheet  = pick_sheet(["Match", "Matches"])
    well_sheet   = pick_sheet(["Wellness", "Bien-être", "Wellbeing"])

    df_players  = pd.read_excel(xfile, sheet_name=joueur_sheet)
    df_matches  = pd.read_excel(xfile, sheet_name=match_sheet)
    df_wellness = pd.read_excel(xfile, sheet_name=well_sheet)

    # Nettoyage colonnes (trim + espaces multiples)
    for df in (df_players, df_matches, df_wellness):
        df.columns = (df.columns.astype(str)
                      .str.strip()
                      .str.replace(r"\s+", " ", regex=True))

    # --- Players ---
    if 'PlayerID' in df_players.columns:
        df_players = df_players.dropna(subset=['PlayerID']).reset_index(drop=True)
        df_players['PlayerID'] = df_players['PlayerID'].astype(int)
    if 'date de naissance' in df_players.columns:
        df_players['date de naissance'] = pd.to_datetime(df_players['date de naissance'], errors='coerce')

    # --- Matches ---
    if 'PlayerID' in df_matches.columns:
        df_matches = df_matches.dropna(subset=['PlayerID']).reset_index(drop=True)
        df_matches['PlayerID'] = df_matches['PlayerID'].astype(int)

    numeric_cols_matches = [
        'Journée', 'Minute jouee', 'Buts', 'Tir', 'Tir cadre', 'xG',
        'Passe complete', 'Passe tentées', 'Tacles gagne', 'Ballon touche',
        'Passe décisive', 'Minute/titularisation',
        'Passe courte complete', 'Passe moyenne complete', 'Passe  long complete',
        'Duel 1v1 gagne', 'Duel 1v1 total', 'Duel aérien gagne', 'Duel aérien perdu',
        'Ballon touch dans surface', 'Ballon touche dans son camp',
        'Ballon touche milieu', 'Ballon touche dernier tiers 1/3',
        'Interception', 'Recuperation', 'Passe clé', 'Passe progressive',
        'Tacles total',
        'Progressive passe distance (m)', 'Distance parcouru avec ballon (m)',
        'Erreur technique', 'Perte du ballon par un adversaire',
        'Distance passe (m)', 'Tacle camp', 'Tacle camp adverse',
        'Match joue', 'Titulaire', 'Match complet', 'Remplaçant', 'Remplaçant non rentré', 'Sortie en cours de match',
        'Passe dans surface', 'Passe dernier tiers 1/3',
        'Reception du ballon', 'Ballon sur passe progressive'
    ]
    for col in numeric_cols_matches:
        if col in df_matches.columns:
            df_matches[col] = pd.to_numeric(df_matches[col], errors='coerce')

    # --- Wellness ---
    if 'PlayerID' in df_wellness.columns:
        df_wellness = df_wellness.dropna(subset=['PlayerID']).reset_index(drop=True)
        df_wellness['PlayerID'] = df_wellness['PlayerID'].astype(int)
    if 'DATE' in df_wellness.columns:
        df_wellness['DATE'] = pd.to_datetime(df_wellness['DATE'], errors='coerce')
        df_wellness = df_wellness.dropna(subset=['DATE']).reset_index(drop=True)

    return df_players, df_matches, df_wellness

# 👉 Charge les DataFrames depuis TON chemin fixe
df_players, df_matches, df_wellness = load_data_cached(str(EXCEL_PATH), file_mtime)

# Toast discret si le fichier a changé entre deux runs
_prev_mtime = st.session_state.get("_last_mtime")
if _prev_mtime is not None and _prev_mtime != file_mtime:
    st.toast("🔄 Données rechargées (modification du fichier détectée).", icon="✅")
st.session_state["_last_mtime"] = file_mtime

# ------------------------------------------------------------------------------
# 2) KPIs agrégés
# ------------------------------------------------------------------------------
def calculate_kpis(df_matches: pd.DataFrame):
    total_players = df_matches['PlayerID'].nunique() if 'PlayerID' in df_matches.columns else 0
    total_goals = int(df_matches['Buts'].sum()) if 'Buts' in df_matches.columns else 0
    total_assists = int(df_matches['Passe décisive'].sum()) if 'Passe décisive' in df_matches.columns else 0
    avg_rating = float(df_matches['Minute/titularisation'].mean()) if 'Minute/titularisation' in df_matches.columns else 0.0
    return [
        {"title": "Total Joueurs", "value": f"{total_players}", "trend": "positive", "subtitle": "+12% vs last season"},
        {"title": "Buts Marqués", "value": f"{total_goals}", "trend": "positive" if total_goals > 0 else "negative", "subtitle": "+18% vs last season"},
        {"title": "Passes Décisives", "value": f"{total_assists}", "trend": "positive" if total_assists > 0 else "negative", "subtitle": "-5% vs last season"},
        {"title": "Note Moyenne", "value": f"{avg_rating:.1f}", "trend": "positive" if avg_rating > 0.5 else "negative", "subtitle": "+0.3 vs last season"},
    ]

kpis = calculate_kpis(df_matches)

# ------------------------------------------------------------------------------
# 3) CSS (thème & composants)
# ------------------------------------------------------------------------------
st.markdown("""
<style>
:root {
  --bg-primary:#0f172a; --bg-secondary:#1e293b; --bg-tertiary:#334155;
  --text-primary:#f8fafc; --text-secondary:#cbd5e1; --text-muted:#94a3b8;
  --accent-primary:#3b82f6; --accent-secondary:#60a5fa;
  --success:#10b981; --warning:#f59e0b; --danger:#ef4444;
  --border:rgba(51,65,85,.4); --shadow:0 8px 32px rgba(0,0,0,.15);
  --transition:all .3s cubic-bezier(.4,0,.2,1);
  --gradient-primary:linear-gradient(135deg,#1e293b,#0f172a);
  --gradient-accent:linear-gradient(135deg,#3b82f6,#1e40af);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg-primary);color:var(--text-primary);line-height:1.6;background-image:radial-gradient(circle at 25% 25%,rgba(59,130,246,.1) 0%,transparent 50%),radial-gradient(circle at 75% 75%,rgba(16,185,129,.1) 0%,transparent 50%);background-attachment:fixed}
.main-content{padding-top:80px}

/* Navbar */
.navbar{position:fixed;top:0;left:0;right:0;z-index:1000;background:rgba(30,41,59,.8);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);height:80px}
.navbar-container{max-width:1200px;margin:0 auto;padding:0 2rem;height:100%;display:flex;align-items:center;justify-content:space-between}
.navbar-brand{display:flex;align-items:center;gap:.75rem;cursor:pointer;transition:var(--transition)}
.navbar-logo{color:var(--accent-primary);font-size:1.5rem}
.navbar-title{font-size:1.25rem;font-weight:700;background:var(--gradient-accent);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.navbar-desktop{display:flex;gap:1rem}
.navbar-link{display:flex;align-items:center;gap:.5rem;padding:.75rem 1rem;border-radius:.75rem;background:transparent;border:none;color:var(--text-secondary);cursor:pointer;transition:var(--transition);font-size:.95rem;font-weight:500}
.navbar-link:hover{background:rgba(59,130,246,.1);color:var(--text-primary)}
.navbar-link.active{background:var(--accent-primary);color:white}

/* Sections */
.hero-section{position:relative;padding:6rem 2rem;text-align:center;overflow:hidden;background:var(--gradient-primary);border-radius:0 0 3rem 3rem;margin:0 -2rem 3rem}
.hero-title{font-size:4rem;font-weight:900;margin-bottom:1rem;background:linear-gradient(135deg,var(--danger),var(--accent-primary),var(--success));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-subtitle{font-size:1.25rem;color:var(--text-secondary);max-width:600px;margin:0 auto;font-weight:300;letter-spacing:.5px}

.kpis-section{padding:0 2rem 3rem}
.kpis-container{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:2rem;max-width:1200px;margin:0 auto}
.kpi-card{background:rgba(30,41,59,.6);backdrop-filter:blur(16px);border:1px solid var(--border);border-radius:1.5rem;padding:2rem;transition:var(--transition);position:relative;overflow:hidden}
.kpi-card:hover{transform:translateY(-8px);border-color:var(--accent-secondary);box-shadow:0 20px 40px rgba(59,130,246,.2)}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:var(--gradient-accent);opacity:0;transition:var(--transition)}
.kpi-card:hover::before{opacity:1}
.kpi-card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem}
.kpi-card-icon{padding:.75rem;border-radius:1rem;background:rgba(59,130,246,.1);color:var(--accent-primary)}
.kpi-trend{font-size:.85rem;font-weight:600;padding:.25rem .5rem;border-radius:.5rem}
.kpi-trend.positive{color:var(--success);background:rgba(16,185,129,.1)}
.kpi-trend.negative{color:var(--danger);background:rgba(239,68,68,.1)}
.kpi-value{font-size:2.5rem;font-weight:800;margin-bottom:.5rem;line-height:1;background:var(--gradient-accent);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.kpi-title{font-size:.95rem;color:var(--text-secondary);font-weight:500;margin-bottom:.25rem}
.kpi-subtitle{font-size:.8rem;color:var(--text-muted)}

.filters-section{padding:0 2rem 2rem}
.filters-container{max-width:1200px;margin:0 auto;background:rgba(30,41,59,.6);backdrop-filter:blur(16px);border:1px solid var(--border);border-radius:1.5rem;padding:2rem;display:flex;gap:2rem;align-items:center;flex-wrap:wrap}
.search-input{width:100%;padding:.875rem 1rem;background:rgba(15,23,42,.6);border:1px solid var(--border);border-radius:1rem;color:var(--text-primary);font-size:.95rem;transition:var(--transition);outline:none}
.search-input:focus{border-color:var(--accent-primary);box-shadow:0 0 0 3px rgba(59,130,246,.1)}
.filter-select{padding:.875rem 1rem;background:rgba(15,23,42,.6);border:1px solid var(--border);border-radius:1rem;color:var(--text-primary);font-size:.95rem;cursor:pointer;transition:var(--transition);min-width:150px}
.filter-select:focus{outline:none;border-color:var(--accent-primary)}

.players-section{padding:2rem}
.players-header{max-width:1200px;margin:0 auto 2rem;text-align:center}
.section-title{font-size:2.5rem;font-weight:800;margin-bottom:1rem;background:var(--gradient-accent);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.section-subtitle{font-size:1.1rem;color:var(--text-secondary)}
.players-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:2rem;max-width:1200px;margin:0 auto}

/* Cards joueur */
.player-card{background:var(--bg-secondary);border-radius:1.5rem;overflow:hidden;transition:var(--transition);box-shadow:var(--shadow);cursor:pointer;border:1px solid var(--border);height:420px;display:flex;flex-direction:column}
.player-card:hover{transform:translateY(-10px);box-shadow:0 25px 50px rgba(0,0,0,.3);border-color:var(--accent-secondary)}
.player-card-header{height:200px;background:var(--gradient-primary);position:relative;display:flex;align-items:center;justify-content:center}
.player-avatar{width:100px;height:100px;border-radius:50%;overflow:hidden;border:4px solid rgba(255,255,255,.2);position:relative;z-index:2}
.player-avatar-placeholder{width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:rgba(59,130,246,.2);font-size:2rem;font-weight:700;color:var(--accent-primary)}
.player-card-overlay{position:absolute;bottom:0;left:0;right:0;padding:1.5rem;background:linear-gradient(transparent,rgba(0,0,0,.8));text-align:center;z-index:1}
.player-name{font-size:1.5rem;font-weight:700;margin-bottom:.5rem;color:white}
.player-meta{font-size:.95rem;color:rgba(255,255,255,.9)}
.player-number{position:absolute;top:1rem;right:1rem;background:rgba(59,130,246,.9);color:white;padding:.5rem 1rem;border-radius:.5rem;font-weight:700;font-size:.9rem}
.player-card-content{padding:1.5rem;flex:1;display:flex;flex-direction:column}
.player-badges{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}
.badge{padding:.25rem .75rem;border-radius:50px;font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.badge-position{background:rgba(59,130,246,.15);color:var(--accent-primary);border:1px solid rgba(59,130,246,.3)}
.badge-info{background:rgba(59,130,246,.15);color:var(--accent-primary);border:1px solid rgba(59,130,246,.3)}
.player-stats-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem;margin-bottom:1.5rem}
.stat-item{display:flex;align-items:center;gap:.75rem;color:var(--text-muted)}
.stat-value{font-size:1.1rem;font-weight:700;color:var(--text-primary)}
.stat-label{font-size:.85rem;color:var(--text-muted)}
.player-card-cta{display:flex;align-items:center;justify-content:center;gap:.5rem;padding:.875rem 1rem;background:var(--gradient-accent);border-radius:1rem;color:white;font-weight:600;transition:var(--transition);margin-top:auto}
.player-card:hover .player-card-cta{transform:translateY(-2px);box-shadow:0 8px 20px rgba(59,130,246,.4)}

/* Header détail joueur */
.player-detail-header{background:var(--bg-secondary);border:1px solid var(--border);border-radius:1.5rem;padding:2rem;margin-bottom:2rem;display:flex;align-items:center;gap:2rem}
.player-avatar-large{width:120px;height:120px;border-radius:50%;overflow:hidden;border:4px solid var(--border);display:flex;align-items:center;justify-content:center;background:rgba(59,130,246,.2);font-size:3rem;font-weight:700;color:var(--accent-primary)}
.player-info{flex:1}
.player-name-large{font-size:2.5rem;font-weight:800;margin-bottom:.5rem;background:var(--gradient-accent);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.player-meta-large{display:flex;align-items:center;gap:1rem;margin-bottom:1rem;flex-wrap:wrap}
.player-meta-item{font-size:1.1rem;color:var(--text-secondary)}
.player-meta-label{font-weight:600;color:var(--accent-primary)}

/* Stats & graphs */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1.5rem;margin-bottom:2rem}
.stat-box{background:rgba(15,23,42,.6);border:1px solid var(--border);border-radius:1rem;padding:1.5rem;text-align:center}
.stat-box .stat-value{font-size:2rem;font-weight:800;color:var(--accent-primary);margin-bottom:.5rem}
.stat-box .stat-label{font-size:.9rem;color:var(--text-muted)}
.graph-container{background:rgba(15,23,42,.6);border:1px solid var(--border);border-radius:1rem;padding:1.5rem;margin:1rem 0}
.graph-title{font-size:1.2rem;font-weight:700;margin-bottom:1rem;color:var(--text-primary)}

/* Responsive */
@media (max-width:768px){
  .hero-title{font-size:2.5rem}
  .players-grid{grid-template-columns:1fr}
  .player-detail-header{flex-direction:column;text-align:center}
  .player-meta-large{justify-content:center}
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 4) État de session
# ------------------------------------------------------------------------------
if 'selected_player_id' not in st.session_state:
    st.session_state.selected_player_id = None

def select_player(player_id: int):
    st.session_state.selected_player_id = player_id
    st.rerun()

# ------------------------------------------------------------------------------
# 5) Navbar
# ------------------------------------------------------------------------------
st.markdown("""
<div class="navbar">
  <div class="navbar-container">
    <div class="navbar-brand">
      <div class="navbar-logo">⚽</div>
      <div class="navbar-title">Football Pro Performance Hub</div>
    </div>
    <div class="navbar-desktop">
      <button class="navbar-link active">Dashboard</button>
      <button class="navbar-link">Players</button>
      <button class="navbar-link">Matches</button>
      <button class="navbar-link">Wellness</button>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 6) Page d'accueil : Hero + KPIs + Filtres
# ------------------------------------------------------------------------------
if st.session_state.selected_player_id is None:
    # Hero
    st.markdown("""
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">Football Pro Performance Hub</h1>
        <p class="hero-subtitle">Analyse de performance tactique, physique et technique en temps réel pour le staff professionnel.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    st.markdown('<div class="kpis-section"><div class="kpis-container">', unsafe_allow_html=True)
    cols = st.columns(len(kpis) if kpis else 1)
    for i, kpi in enumerate(kpis):
        trend_class = "positive" if kpi["trend"] == "positive" else "negative"
        with cols[i]:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="kpi-card-header">
                <div class="kpi-card-icon">📊</div>
                <span class="kpi-trend {trend_class}">{kpi['trend'].upper()}</span>
              </div>
              <div class="kpi-value">{kpi['value']}</div>
              <div class="kpi-title">{kpi['title']}</div>
              <div class="kpi-subtitle">{kpi['subtitle']}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

    # Filtres (inline — pas de sidebar)
    st.markdown('<div class="filters-section"><div class="filters-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search_query = st.text_input("", placeholder="Rechercher un joueur...", label_visibility="collapsed")
    with col2:
        unique_positions = ["Tous"] + (df_players['Poste'].dropna().astype(str).unique().tolist() if 'Poste' in df_players.columns else [])
        selected_position = st.selectbox("Position", unique_positions, label_visibility="collapsed")
    with col3:
        unique_clubs = ["Tous"] + (df_players['Club'].dropna().astype(str).unique().tolist() if 'Club' in df_players.columns else [])
        selected_club = st.selectbox("Club", unique_clubs, label_visibility="collapsed")
    st.markdown('</div></div>', unsafe_allow_html=True)

    # Application des filtres
    filtered_players = df_players.copy()
    if {'Nom','Prénom'}.issubset(filtered_players.columns):
        if search_query:
            mask = (
                filtered_players['Nom'].astype(str).str.contains(search_query, case=False, na=False) |
                filtered_players['Prénom'].astype(str).str.contains(search_query, case=False, na=False)
            )
            filtered_players = filtered_players[mask]
    if selected_position != "Tous" and 'Poste' in filtered_players.columns:
        filtered_players = filtered_players[filtered_players['Poste'] == selected_position]
    if selected_club != "Tous" and 'Club' in filtered_players.columns:
        filtered_players = filtered_players[filtered_players['Club'] == selected_club]

# ------------------------------------------------------------------------------
# 7) Page DÉTAIL joueur
# ------------------------------------------------------------------------------
else:
    player_id = st.session_state.selected_player_id
    player_row = df_players[df_players['PlayerID'] == player_id].iloc[0]

    if st.button("⬅️ Retour à la liste des joueurs"):
        st.session_state.selected_player_id = None
        st.rerun()

    player_matches = df_matches[df_matches['PlayerID'] == player_id].copy()
    player_wellness = df_wellness[df_wellness['PlayerID'] == player_id].copy()

    # Indicateurs wellness
    if not player_wellness.empty:
        wellness_cols = ['Energie générale', 'Fraicheur musculaire', 'Humeur', 'Sommeil']
        for col in wellness_cols:
            if col in player_wellness.columns:
                player_wellness[col] = player_wellness[col].fillna(player_wellness[col].mean())
        if all(c in player_wellness.columns for c in wellness_cols):
            player_wellness['Form Score'] = player_wellness[wellness_cols].mean(axis=1).round(1)
        else:
            player_wellness['Form Score'] = np.nan
        current_form_score = player_wellness['Form Score'].dropna().iloc[-1] if not player_wellness['Form Score'].dropna().empty else 0
        avg_form_score = float(player_wellness['Form Score'].mean()) if not player_wellness['Form Score'].dropna().empty else 0
        form_trend = "good" if avg_form_score and current_form_score >= avg_form_score else "warning"
    else:
        current_form_score, avg_form_score, form_trend = 0, 0, "bad"

    # En-tête joueur
    st.markdown(f"""
    <div class="player-detail-header">
      <div class="player-avatar-large">⚽</div>
      <div class="player-info">
        <h1 class="player-name-large">{player_row.get('Prénom', '')} {player_row.get('Nom', '')}</h1>
        <div class="player-meta-large">
          <div class="player-meta-item"><span class="player-meta-label">Club:</span> {player_row.get('Club', '—')}</div>
          <div class="player-meta-item"><span class="player-meta-label">Poste:</span> {player_row.get('Poste', '—')}</div>
          <div class="player-meta-item"><span class="player-meta-label">Âge:</span> {player_row.get('Age', '—')}</div>
          <div class="player-meta-item"><span class="player-meta-label">Taille:</span> {player_row.get('Taille', '—')} cm</div>
          <div class="player-meta-item"><span class="player-meta-label">Poids:</span> {player_row.get('Poids', '—')} kg</div>
          <div class="player-meta-item"><span class="player-meta-label">Pied:</span> {player_row.get('Pied', '—')}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Indicateurs de forme rapides
    col_form1, col_form2, col_form3 = st.columns(3)
    with col_form1:
        st.markdown(f"""
        <div class="stat-box">
          <div class="stat-value">{current_form_score}/10</div>
          <div class="stat-label">Forme Actuelle</div>
        </div>""", unsafe_allow_html=True)
    with col_form2:
        st.markdown(f"""
        <div class="stat-box">
          <div class="stat-value">{avg_form_score:.1f}/10</div>
          <div class="stat-label">Forme Moyenne</div>
        </div>""", unsafe_allow_html=True)
    with col_form3:
        pain_col = 'Intensité douleur'
        if not player_wellness.empty and pain_col in player_wellness.columns:
            recent_pain = player_wellness[pain_col].dropna().iloc[-1] if not player_wellness[pain_col].dropna().empty else 0
            st.markdown(f"""
            <div class="stat-box">
              <div class="stat-value">{int(recent_pain)}/10</div>
              <div class="stat-label">Douleur Actuelle</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="stat-box">
              <div class="stat-value">N/A</div>
              <div class="stat-label">Douleur Actuelle</div>
            </div>""", unsafe_allow_html=True)

    # Onglets
    tab1, tab2, tab3 = st.tabs(["📊 Statistiques", "⚽ Matchs", "🧘 Wellness"])

    # --- Tab 1: Statistiques synthétiques + tableau simple ---
    with tab1:
        total_goals = int(player_matches['Buts'].sum()) if 'Buts' in player_matches.columns else 0
        total_assists = int(player_matches['Passe décisive'].sum()) if 'Passe décisive' in player_matches.columns else 0
        total_matches = len(player_matches[player_matches['Match joue'] == 1]) if 'Match joue' in player_matches.columns else len(player_matches)
        avg_minutes = float(player_matches['Minute jouee'].mean()) if 'Minute jouee' in player_matches.columns and not player_matches.empty else 0

        st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f"""<div class="stat-box"><div class="stat-value">{total_matches}</div><div class="stat-label">Matchs joués</div></div>""", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"""<div class="stat-box"><div class="stat-value">{total_goals}</div><div class="stat-label">Buts</div></div>""", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"""<div class="stat-box"><div class="stat-value">{total_assists}</div><div class="stat-label">Passes décisives</div></div>""", unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"""<div class="stat-box"><div class="stat-value">{avg_minutes:.0f}'</div><div class="stat-label">Moy. minutes/match</div></div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if not player_matches.empty:
            st.subheader("Détail des matchs")
            display_cols = ['Journée', 'Adversaire', 'Minute jouee', 'Buts', 'Passe décisive', 'xG']
            display_cols = [c for c in display_cols if c in player_matches.columns]
            st.dataframe(player_matches[display_cols], use_container_width=True)
        else:
            st.info("Aucun match trouvé pour ce joueur.")

    # --- Tab 2: Matchs (analyses + nouveaux graphiques) ---
    with tab2:
        st.subheader("⚽ Analyse Tactique & Performance en Match")

        if not player_matches.empty and 'Journée' in player_matches.columns:
            player_matches = player_matches.sort_values('Journée').reset_index(drop=True)

            # Calculs indicateurs
            player_matches['Efficacité Offensive'] = player_matches.apply(
                lambda r: r['Buts'] / r['xG'] if r.get('xG', 0) and r['xG'] > 0 else 0, axis=1
            ).round(2)
            player_matches['% Tirs Cadrés'] = player_matches.apply(
                lambda r: (r['Tir cadre'] / r['Tir'] * 100) if r.get('Tir', 0) else 0, axis=1
            ).round(1)
            player_matches['Buts par Tir'] = player_matches.apply(
                lambda r: (r['Buts'] / r['Tir']) if r.get('Tir', 0) else 0, axis=1
            ).round(2)
            player_matches['Taux Passes'] = player_matches.apply(
                lambda r: (r['Passe complete'] / r['Passe tentées'] * 100) if r.get('Passe tentées', 0) else 0, axis=1
            ).round(1)
            player_matches['Impact Défensif'] = player_matches.get('Tacles gagne', 0).fillna(0) + player_matches.get('Interception', 0).fillna(0)

            # Résumé global
            st.markdown("### 📈 Résumé Statistique Global")
            played_matches = player_matches[player_matches['Match joue'] == 1] if 'Match joue' in player_matches.columns else player_matches
            total_matches = len(played_matches)
            total_minutes = played_matches['Minute jouee'].sum() if 'Minute jouee' in played_matches.columns else 0
            avg_minutes = played_matches['Minute jouee'].mean() if total_matches > 0 and 'Minute jouee' in played_matches.columns else 0
            titularisation_rate = (played_matches['Titulaire'].sum() / total_matches * 100) if total_matches > 0 and 'Titulaire' in played_matches.columns else 0
            complete_match_rate = (played_matches['Match complet'].sum() / total_matches * 100) if total_matches > 0 and 'Match complet' in played_matches.columns else 0

            col_global1, col_global2, col_global3, col_global4, col_global5 = st.columns(5)
            with col_global1:
                st.markdown(f"""<div class="stat-box"><div class="stat-value">{total_matches}</div><div class="stat-label">Matchs Joués</div></div>""", unsafe_allow_html=True)
            with col_global2:
                st.markdown(f"""<div class="stat-box"><div class="stat-value">{int(total_minutes)}</div><div class="stat-label">Minutes Totales</div></div>""", unsafe_allow_html=True)
            with col_global3:
                st.markdown(f"""<div class="stat-box"><div class="stat-value">{avg_minutes:.0f}'</div><div class="stat-label">Moy. par Match</div></div>""", unsafe_allow_html=True)
            with col_global4:
                st.markdown(f"""<div class="stat-box"><div class="stat-value">{titularisation_rate:.0f}%</div><div class="stat-label">Taux de Titularisation</div></div>""", unsafe_allow_html=True)
            with col_global5:
                st.markdown(f"""<div class="stat-box"><div class="stat-value">{complete_match_rate:.0f}%</div><div class="stat-label">% Matchs Complétés</div></div>""", unsafe_allow_html=True)

            # Dernier match
            st.markdown("### 📊 Indicateurs de Performance du Dernier Match")
            last_match = player_matches.iloc[-1]
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                off_eff = last_match.get('Efficacité Offensive', 0)
                color = "#10b981" if off_eff > 1 else "#f59e0b" if off_eff > 0.5 else "#ef4444"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{off_eff}</div><div class="stat-label">Efficacité Offensive<br>(Buts/xG)</div></div>""", unsafe_allow_html=True)
            with col2:
                shot_acc = last_match.get('% Tirs Cadrés', 0)
                color = "#10b981" if shot_acc >= 50 else "#f59e0b" if shot_acc >= 30 else "#ef4444"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{shot_acc}%</div><div class="stat-label">% Tirs Cadrés</div></div>""", unsafe_allow_html=True)
            with col3:
                pass_rate = last_match.get('Taux Passes', 0)
                color = "#10b981" if pass_rate >= 85 else "#f59e0b" if pass_rate >= 75 else "#ef4444"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{pass_rate}%</div><div class="stat-label">Taux de Réussite<br>des Passes</div></div>""", unsafe_allow_html=True)
            with col4:
                def_impact = last_match.get('Impact Défensif', 0)
                color = "#10b981" if def_impact >= 3 else "#f59e0b" if def_impact >= 1 else "#6b7280"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{int(def_impact)}</div><div class="stat-label">Impact Défensif<br>(Tacles + Interc.)</div></div>""", unsafe_allow_html=True)
            with col5:
                prog_balls = last_match.get('Ballon sur passe progressive', 0)
                color = "#10b981" if prog_balls >= 5 else "#f59e0b" if prog_balls >= 2 else "#6b7280"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{int(prog_balls)}</div><div class="stat-label">Ballons sur Passes<br>Progressives</div></div>""", unsafe_allow_html=True)

            # 1) Efficacité offensive & finition
            st.markdown('<div class="graph-container"><div class="graph-title">🎯 Efficacité Offensive & Finition</div>', unsafe_allow_html=True)
            df_off = pd.DataFrame([{
                'Journée': f"J{int(r['Journée'])}",
                'Buts': r['Buts'] if 'Buts' in player_matches.columns and pd.notna(r.get('Buts')) else 0,
                'Tir': r['Tir'] if 'Tir' in player_matches.columns and pd.notna(r.get('Tir')) else 0,
                'Tir cadre': r['Tir cadre'] if 'Tir cadre' in player_matches.columns and pd.notna(r.get('Tir cadre')) else 0,
                'xG': r['xG'] if 'xG' in player_matches.columns and pd.notna(r.get('xG')) else 0
            } for _, r in player_matches.iterrows()])
            if not df_off.empty:
                fig_offensive = px.bar(df_off, x='Journée', y=['Buts','Tir','Tir cadre','xG'], barmode='group',
                                       title='Buts, Tirs, Tirs Cadrés, xG',
                                       color_discrete_sequence=['#ef4444','#f97316','#10b981','#f59e0b'])
                fig_offensive.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                            xaxis_title="Journée", yaxis_title="Valeur", legend_title="Métrique")
                st.plotly_chart(fig_offensive, use_container_width=True)
            else:
                st.info("Données offensives non disponibles.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 2) Circulation & Distance des passes
            st.markdown('<div class="graph-container"><div class="graph-title">🔄 Circulation & Distance des Passes</div>', unsafe_allow_html=True)
            col_pass1, col_pass2 = st.columns(2)
            with col_pass1:
                df_pass = pd.DataFrame([{
                    'Journée': f"J{int(r['Journée'])}",
                    'Passe courte': r['Passe courte complete'] if 'Passe courte complete' in player_matches.columns and pd.notna(r.get('Passe courte complete')) else 0,
                    'Passe moyenne': r['Passe moyenne complete'] if 'Passe moyenne complete' in player_matches.columns and pd.notna(r.get('Passe moyenne complete')) else 0,
                    'Passe long': r['Passe  long complete'] if 'Passe  long complete' in player_matches.columns and pd.notna(r.get('Passe  long complete')) else 0
                } for _, r in player_matches.iterrows()])
                if not df_pass.empty:
                    fig_pass = px.bar(df_pass, x='Journée', y=['Passe courte','Passe moyenne','Passe long'], barmode='stack',
                                      title='Types de Passes Complétées',
                                      color_discrete_sequence=['#3b82f6','#10b981','#f59e0b'])
                    fig_pass.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                           xaxis_title="Journée", yaxis_title="Nombre de passes", legend_title="Type de passe")
                    st.plotly_chart(fig_pass, use_container_width=True)
                else:
                    st.info("Données de passes non disponibles.")
            with col_pass2:
                df_pass_dist = pd.DataFrame([{
                    'Journée': f"J{int(r['Journée'])}",
                    'Distance (m)': r['Distance passe (m)'] if 'Distance passe (m)' in player_matches.columns and pd.notna(r.get('Distance passe (m)')) else 0
                } for _, r in player_matches.iterrows()])
                if not df_pass_dist.empty:
                    fig_pass_dist = px.line(df_pass_dist, x='Journée', y='Distance (m)',
                                            title='Distance Totale des Passes par Match',
                                            markers=True, line_shape='spline')
                    fig_pass_dist.update_traces(line_color='#8b5cf6', line_width=3, marker_size=8)
                    fig_pass_dist.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                                xaxis_title="Journée", yaxis_title="Distance (m)")
                    st.plotly_chart(fig_pass_dist, use_container_width=True)
                else:
                    st.info("Données de distance de passes non disponibles.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 3) Pression & Récupération
            st.markdown('<div class="graph-container"><div class="graph-title">🛡️ Pression & Récupération</div>', unsafe_allow_html=True)
            pressure_cols = [c for c in ['Tacle camp','Tacle camp adverse','Perte du ballon par un adversaire'] if c in player_matches.columns]
            if pressure_cols:
                df_pressure = pd.DataFrame([{
                    'Journée': f"J{int(r['Journée'])}", **{c: (r[c] if pd.notna(r.get(c)) else 0) for c in pressure_cols}
                } for _, r in player_matches.iterrows()])
                fig_pressure = px.bar(df_pressure, x='Journée', y=pressure_cols, barmode='group',
                                      title="Tacles par Zone + Pertes Adverses",
                                      color_discrete_sequence=['#ef4444','#f97316','#10b981'])
                fig_pressure.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                           xaxis_title="Journée", yaxis_title="Actions", legend_title="Action")
                st.plotly_chart(fig_pressure, use_container_width=True)
            else:
                st.info("Données de pression non disponibles.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 4) Gestion du ballon & Fiabilité
            st.markdown('<div class="graph-container"><div class="graph-title">🔁 Gestion du Ballon & Fiabilité</div>', unsafe_allow_html=True)
            col_ball1, col_ball2 = st.columns(2)
            with col_ball1:
                ball_cols = [c for c in ['Reception du ballon','Erreur technique','Perte du ballon par un adversaire'] if c in player_matches.columns]
                if ball_cols:
                    df_ball = pd.DataFrame([{
                        'Journée': f"J{int(r['Journée'])}", **{c: (r[c] if pd.notna(r.get(c)) else 0) for c in ball_cols}
                    } for _, r in player_matches.iterrows()])
                    fig_ball = px.bar(df_ball, x='Journée', y=ball_cols, barmode='group',
                                      title='Réceptions, Erreurs, Pertes Subies',
                                      color_discrete_sequence=['#3b82f6','#ef4444','#10b981'])
                    fig_ball.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                           xaxis_title="Journée", yaxis_title="Nombre d\'actions", legend_title="Action")
                    st.plotly_chart(fig_ball, use_container_width=True)
                else:
                    st.info("Données de gestion de balle non disponibles.")
            with col_ball2:
                if 'Taux Passes' in player_matches.columns:
                    df_pass_rate = pd.DataFrame({
                        'Journée': [f"J{int(j)}" for j in player_matches['Journée']],
                        'Taux de Réussite': player_matches['Taux Passes'].fillna(0)
                    })
                    fig_pass_rate = px.line(df_pass_rate, x='Journée', y='Taux de Réussite',
                                            title='Évolution du Taux de Réussite des Passes',
                                            markers=True, line_shape='spline')
                    fig_pass_rate.update_traces(line_color='#8b5cf6', line_width=3, marker_size=8)
                    fig_pass_rate.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                                xaxis_title="Journée", yaxis_title="Taux de réussite (%)", yaxis_range=[0, 100])
                    st.plotly_chart(fig_pass_rate, use_container_width=True)
                else:
                    st.info("Données de taux de passes non disponibles.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 5) Répartition des touches par zone (aire empilée)
            st.markdown('<div class="graph-container"><div class="graph-title">🗺️ Répartition des Touches par Zone</div>', unsafe_allow_html=True)
            zone_map = {
                'Camp propre': ['Ballon touche dans son camp'],
                'Milieu': ['Ballon touche milieu'],
                'Dernier tiers': ['Ballon touche dernier tiers 1/3'],
                'Surface adverse': ['Ballon touch dans surface','Ballon touche dans surface']
            }
            available_zone_keys = [label for label, opts in zone_map.items() if any(o in player_matches.columns for o in opts)]
            if available_zone_keys:
                rows = []
                for _, r in player_matches.iterrows():
                    row = {'Journée': f"J{int(r['Journée'])}"}
                    for label, opts in zone_map.items():
                        val = 0
                        for o in opts:
                            if o in player_matches.columns and pd.notna(r.get(o)):
                                val += r[o]
                        row[label] = val
                    rows.append(row)
                df_zone = pd.DataFrame(rows)
                df_zone_long = df_zone.melt(id_vars='Journée', value_vars=available_zone_keys, var_name='Zone', value_name='Touches')
                fig_zone = px.area(df_zone_long, x='Journée', y='Touches', color='Zone', title="Répartition des touches par zone (par match)")
                fig_zone.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                       xaxis_title="Journée", yaxis_title="Touches")
                st.plotly_chart(fig_zone, use_container_width=True)
            else:
                st.info("Aucune donnée de touches par zone disponible.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 6) Duels – Taux de réussite (par match + jauges globales)
            st.markdown('<div class="graph-container"><div class="graph-title">🧱 Duels – Taux de Réussite</div>', unsafe_allow_html=True)
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                lines = []
                if 'Duel 1v1 gagne' in player_matches.columns and 'Duel 1v1 total' in player_matches.columns:
                    onev1_rate = (player_matches['Duel 1v1 gagne'] / player_matches['Duel 1v1 total'].replace(0, np.nan) * 100).fillna(0)
                    lines.append(('Taux 1v1', onev1_rate))
                if all(c in player_matches.columns for c in ['Duel aérien gagne','Duel aérien perdu']):
                    aerial_total = (player_matches['Duel aérien gagne'].fillna(0) + player_matches['Duel aérien perdu'].fillna(0)).replace(0, np.nan)
                    aerial_rate = (player_matches['Duel aérien gagne'] / aerial_total * 100).fillna(0)
                    lines.append(('Taux aériens', aerial_rate))
                if lines:
                    df_duel = pd.DataFrame({'Journée': [f"J{int(j)}" for j in player_matches['Journée']]})
                    for name, series in lines:
                        df_duel[name] = series
                    fig_duel = px.line(df_duel, x='Journée', y=[n for n,_ in lines], markers=True, line_shape='spline',
                                       title="Taux de réussite des duels (par match)")
                    fig_duel.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                           xaxis_title="Journée", yaxis_title="Réussite (%)", yaxis_range=[0,100])
                    st.plotly_chart(fig_duel, use_container_width=True)
                else:
                    st.info("Pas assez de données pour tracer les taux de duels.")
            with subcol2:
                gauge_fig = go.Figure()
                if 'Duel 1v1 gagne' in player_matches.columns and 'Duel 1v1 total' in player_matches.columns:
                    tot = player_matches['Duel 1v1 total'].sum()
                    rate = (player_matches['Duel 1v1 gagne'].sum() / tot * 100) if tot > 0 else 0
                    gauge_fig.add_trace(go.Indicator(mode="gauge+number", value=rate, domain={'x':[0,0.45],'y':[0,1]},
                                                     title={'text':"1v1 – %"}, gauge={'axis':{'range':[0,100]}}))
                if all(c in player_matches.columns for c in ['Duel aérien gagne','Duel aérien perdu']):
                    tot = player_matches['Duel aérien gagne'].sum() + player_matches['Duel aérien perdu'].sum()
                    rate = (player_matches['Duel aérien gagne'].sum() / tot * 100) if tot > 0 else 0
                    gauge_fig.add_trace(go.Indicator(mode="gauge+number", value=rate, domain={'x':[0.55,1],'y':[0,1]},
                                                     title={'text':"Aériens – %"}, gauge={'axis':{'range':[0,100]}}))
                if len(gauge_fig.data) > 0:
                    st.plotly_chart(gauge_fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # 7) Défense par 90’
            st.markdown('<div class="graph-container"><div class="graph-title">🕐 Actions Défensives par 90’</div>', unsafe_allow_html=True)
            if 'Minute jouee' in player_matches.columns:
                def_cols = [c for c in ['Tacles total','Interception','Recuperation'] if c in player_matches.columns]
                if def_cols:
                    per90 = {}
                    for c in def_cols:
                        per90[c] = (player_matches[c].fillna(0) / player_matches['Minute jouee'].replace(0,np.nan) * 90).fillna(0)
                    df_def90 = pd.DataFrame({'Journée':[f"J{int(j)}" for j in player_matches['Journée']], **per90})
                    fig_def90 = px.line(df_def90, x='Journée', y=def_cols, markers=True, line_shape='spline',
                                        title="Tacles, Interceptions, Récupérations (par 90’)")
                    fig_def90.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                            xaxis_title="Journée", yaxis_title="Actions / 90’")
                    st.plotly_chart(fig_def90, use_container_width=True)
                else:
                    st.info("Colonnes défensives manquantes.")
            else:
                st.info("Pas de minutes jouées → per 90 indisponible.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 8) Tendances glissantes (3 matchs)
            st.markdown('<div class="graph-container"><div class="graph-title">📉 Tendances (Moyenne Mobile 3 matchs)</div>', unsafe_allow_html=True)
            trend_cols = []
            if 'xG' in player_matches.columns: trend_cols.append('xG')
            if '% Tirs Cadrés' in player_matches.columns: trend_cols.append('% Tirs Cadrés')
            if 'Taux Passes' in player_matches.columns: trend_cols.append('Taux Passes')
            if trend_cols:
                df_trend = pd.DataFrame({'Journée': [f"J{int(j)}" for j in player_matches['Journée']]})
                for c in trend_cols:
                    df_trend[c] = player_matches[c].fillna(0).rolling(3, min_periods=1).mean()
                fig_trend = px.line(df_trend, x='Journée', y=trend_cols, markers=True, line_shape='spline',
                                    title="Moyennes mobiles (3)")
                fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                        xaxis_title="Journée", yaxis_title="Valeur (moy. mobile)")
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Pas de variables suffisantes pour les tendances.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 9) Cumul Buts vs Cumul xG
            st.markdown('<div class="graph-container"><div class="graph-title">➕ Cumul Buts vs Cumul xG</div>', unsafe_allow_html=True)
            if all(c in player_matches.columns for c in ['Buts','xG']):
                df_cum = pd.DataFrame({
                    'Journée': [f"J{int(j)}" for j in player_matches['Journée']],
                    'Cumul Buts': player_matches['Buts'].fillna(0).cumsum(),
                    'Cumul xG': player_matches['xG'].fillna(0).cumsum()
                })
                fig_cum = px.line(df_cum, x='Journée', y=['Cumul Buts','Cumul xG'], markers=True,
                                  title="Progression cumulée")
                fig_cum.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                      xaxis_title="Journée", yaxis_title="Cumul")
                st.plotly_chart(fig_cum, use_container_width=True)
            else:
                st.info("Données insuffisantes pour le cumul.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 10) Matrice de corrélation
            st.markdown('<div class="graph-container"><div class="graph-title">🧪 Matrice de Corrélation</div>', unsafe_allow_html=True)
            cand = ['Buts','xG','Tir','Tir cadre','Passe clé','Passe progressive','Tacles total',
                    'Interception','Recuperation','Erreur technique','Taux Passes','Minute jouee',
                    'Distance parcouru avec ballon (m)','Distance passe (m)']
            cols_corr = [c for c in cand if c in player_matches.columns]
            if len(cols_corr) >= 2:
                df_corr = player_matches[cols_corr].copy()
                for c in df_corr.columns:
                    df_corr[c] = pd.to_numeric(df_corr[c], errors='coerce')
                corr = df_corr.corr(numeric_only=True)
                fig_corr = px.imshow(corr, text_auto=True, aspect='auto', color_continuous_scale='RdBu', zmin=-1, zmax=1,
                                     title="Corrélation entre métriques")
                fig_corr.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1')
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("Pas assez de variables numériques pour calculer une corrélation.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 11) Passes vers zones dangereuses
            st.markdown('<div class="graph-container"><div class="graph-title">🎯 Passes dans le Dernier Tiers & Surface</div>', unsafe_allow_html=True)
            pass_zone_cols = [c for c in ['Passe dernier tiers 1/3','Passe dans surface'] if c in player_matches.columns]
            if pass_zone_cols:
                df_pz = pd.DataFrame({
                    'Journée': [f"J{int(j)}" for j in player_matches['Journée']],
                    **{c: player_matches[c].fillna(0) for c in pass_zone_cols}
                })
                fig_pz = px.bar(df_pz, x='Journée', y=pass_zone_cols, barmode='group',
                                title='Volume de passes dans zones clés',
                                color_discrete_sequence=['#06b6d4','#f43f5e'])
                fig_pz.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                     xaxis_title="Journée", yaxis_title="Passes")
                st.plotly_chart(fig_pz, use_container_width=True)
            else:
                st.info("Pas de colonnes de passes vers zones clés.")
            st.markdown('</div>', unsafe_allow_html=True)

            # Données brutes complètes
            st.subheader("📋 Données Brutes Complètes des Matchs")
            match_cols = [
                'Journée', 'Adversaire', 'Minute jouee', 'Titulaire', 'Buts', 'xG', 'Tir', 'Tir cadre',
                'Passe décisive', 'Passe clé', 'Passe complete', 'Passe tentées', 'Taux Passes',
                'Tacles gagne', 'Tacles total', 'Interception', 'Recuperation', 'Ballon touche',
                'Distance parcouru avec ballon (m)', 'Ballon sur passe progressive',
                'Erreur technique', 'Perte du ballon par un adversaire',
                'Distance passe (m)', 'Tacle camp', 'Tacle camp adverse',
                'Duel 1v1 gagne', 'Duel 1v1 total', 'Duel aérien gagne', 'Duel aérien perdu',
                'Match joue', 'Match complet', 'Remplaçant', 'Remplaçant non rentré', 'Sortie en cours de match',
                'Passe dans surface', 'Passe dernier tiers 1/3',
                'Ballon touche dans son camp', 'Ballon touche milieu', 'Ballon touche dernier tiers 1/3', 'Ballon touch dans surface'
            ]
            available_cols = [c for c in match_cols if c in player_matches.columns]
            st.dataframe(player_matches[available_cols], use_container_width=True)

        else:
            st.warning("🚫 Pas assez de données pour générer des graphiques.")

    # --- Tab 3: Wellness ---
    with tab3:
        st.subheader("🧘 Suivi du bien-être & Forme Physique")
        if not player_wellness.empty:
            player_wellness = player_wellness.sort_values('DATE').reset_index(drop=True)
            composite_cols = ['Energie générale', 'Fraicheur musculaire', 'Humeur', 'Sommeil']
            for c in composite_cols:
                if c in player_wellness.columns:
                    player_wellness[c] = player_wellness[c].fillna(player_wellness[c].median())
            if all(c in player_wellness.columns for c in composite_cols):
                player_wellness['Composite Score'] = player_wellness[composite_cols].mean(axis=1).round(1)
            else:
                player_wellness['Composite Score'] = np.nan

            st.markdown("### 🔑 Indicateurs du dernier suivi")
            last_row = player_wellness.iloc[-1]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                energy = last_row.get('Energie générale', 0)
                color = "#10b981" if energy >= 7 else "#f59e0b" if energy >= 5 else "#ef4444"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{energy}/10</div><div class="stat-label">Énergie</div></div>""", unsafe_allow_html=True)
            with col2:
                mood = last_row.get('Humeur', 0)
                color = "#10b981" if mood >= 7 else "#f59e0b" if mood >= 5 else "#ef4444"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{mood}/10</div><div class="stat-label">Humeur</div></div>""", unsafe_allow_html=True)
            with col3:
                sleep = last_row.get('Sommeil', 0)
                color = "#10b981" if sleep >= 7 else "#f59e0b" if sleep >= 5 else "#ef4444"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{sleep}/10</div><div class="stat-label">Sommeil</div></div>""", unsafe_allow_html=True)
            with col4:
                pain = last_row.get('Intensité douleur', 0)
                color = "#10b981" if pain <= 2 else "#f59e0b" if pain <= 5 else "#ef4444"
                st.markdown(f"""<div class="stat-box" style="border-left:4px solid {color};"><div class="stat-value" style="color:{color};">{pain}/10</div><div class="stat-label">Douleur</div></div>""", unsafe_allow_html=True)

            st.markdown('<div class="graph-container"><div class="graph-title">📈 Évolution de la Forme Globale & Douleur</div>', unsafe_allow_html=True)
            fig_main = go.Figure()
            fig_main.add_trace(go.Scatter(x=player_wellness['DATE'], y=player_wellness['Composite Score'], mode='lines+markers',
                                          name='Forme Globale', line=dict(color='#3b82f6', width=3), marker=dict(size=8)))
            pain_values = player_wellness['Intensité douleur'].fillna(0) if 'Intensité douleur' in player_wellness.columns else pd.Series([0]*len(player_wellness))
            fig_main.add_trace(go.Bar(x=player_wellness['DATE'], y=pain_values, name='Intensité Douleur', marker_color='#ef4444', opacity=0.7, yaxis='y2'))
            fig_main.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                   xaxis_title="Date", yaxis_title="Forme Globale (0-10)",
                                   yaxis2=dict(title="Douleur (0-10)", overlaying='y', side='right', range=[0, 10]),
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_main, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown('<div class="graph-container"><div class="graph-title">⚡ Énergie & Fraîcheur Musculaire</div>', unsafe_allow_html=True)
                fig_energy = go.Figure()
                if 'Energie générale' in player_wellness.columns:
                    fig_energy.add_trace(go.Scatter(x=player_wellness['DATE'], y=player_wellness['Energie générale'], mode='lines+markers', name='Énergie', line=dict(color='#f59e0b', width=2)))
                if 'Fraicheur musculaire' in player_wellness.columns:
                    fig_energy.add_trace(go.Scatter(x=player_wellness['DATE'], y=player_wellness['Fraicheur musculaire'], mode='lines+markers', name='Fraîcheur Musculaire', line=dict(color='#10b981', width=2)))
                fig_energy.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1', xaxis_title="Date", yaxis_title="Score (0-10)", showlegend=True)
                st.plotly_chart(fig_energy, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with col_b:
                st.markdown('<div class="graph-container"><div class="graph-title">😌 Humeur & Sommeil</div>', unsafe_allow_html=True)
                fig_mood = go.Figure()
                if 'Humeur' in player_wellness.columns:
                    fig_mood.add_trace(go.Scatter(x=player_wellness['DATE'], y=player_wellness['Humeur'], mode='lines+markers', name='Humeur', line=dict(color='#8b5cf6', width=2)))
                if 'Sommeil' in player_wellness.columns:
                    fig_mood.add_trace(go.Scatter(x=player_wellness['DATE'], y=player_wellness['Sommeil'], mode='lines+markers', name='Sommeil', line=dict(color='#6366f1', width=2)))
                fig_mood.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1', xaxis_title="Date", yaxis_title="Score (0-10)", showlegend=True)
                st.plotly_chart(fig_mood, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown("<div class='graph-container'><div class='graph-title'>🏋️ Qualité d'Entraînement</div>", unsafe_allow_html=True)
                if 'Qualité entrainement' in player_wellness.columns:
                    fig_train = px.bar(player_wellness, x='DATE', y='Qualité entrainement', title='', color_discrete_sequence=['#3b82f6'])
                    fig_train.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1', xaxis_title="Date", yaxis_title="Qualité (0-10)", showlegend=False)
                    st.plotly_chart(fig_train, use_container_width=True)
                else:
                    st.info("Donnée non disponible.")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_d:
                st.markdown("<div class='graph-container'><div class='graph-title'>⏱️ Intensité du Match</div>", unsafe_allow_html=True)
                if 'Intensité du match' in player_wellness.columns:
                    fig_intensity = px.bar(player_wellness, x='DATE', y='Intensité du match', title='', color_discrete_sequence=['#f59e0b'])
                    fig_intensity.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1', xaxis_title="Date", yaxis_title="Intensité (0-10)", showlegend=False)
                    st.plotly_chart(fig_intensity, use_container_width=True)
                else:
                    st.info("Donnée non disponible.")
                st.markdown('</div>', unsafe_allow_html=True)

            # Timeline + alertes
            st.markdown('<div class="graph-container"><div class="graph-title">📅 Timeline Quotidienne & Alertes</div>', unsafe_allow_html=True)
            player_wellness['Alerte'] = player_wellness.apply(
                lambda row: "🔴 Alert" if (row.get('Intensité douleur', 0) > 5) or (row.get('Sommeil', 10) < 5) else
                            "🟠 Moyen" if (row.get('Composite Score', 10) < 6) else "🟢 Bon",
                axis=1
            )
            fig_timeline = px.scatter(
                player_wellness, x='DATE', y='Composite Score', color='Alerte', size='Composite Score',
                hover_data=['Energie générale', 'Humeur', 'Sommeil', 'Intensité douleur'],
                color_discrete_map={"🟢 Bon": "#10b981", "🟠 Moyen": "#f59e0b", "🔴 Alert": "#ef4444"},
                title="Vue d'ensemble quotidienne"
            )
            fig_timeline.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#cbd5e1',
                                       xaxis_title="Date", yaxis_title="Forme Globale (0-10)", showlegend=True)
            st.plotly_chart(fig_timeline, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Données brutes wellness
            st.subheader("📋 Données brutes")
            wellness_cols = [
                'DATE', 'Energie générale', 'Fraicheur musculaire',
                'Humeur', 'Sommeil', 'Intensité douleur', 'Qualité entrainement',
                'Intensité du match', 'Performance de match', 'Sensation physique de match'
            ]
            available = [c for c in wellness_cols if c in player_wellness.columns]
            st.dataframe(player_wellness[available].sort_values('DATE', ascending=False), use_container_width=True)
        else:
            st.warning("🚫 Aucune donnée de bien-être disponible pour ce joueur.")

# ------------------------------------------------------------------------------
# 8) Grille des joueurs (si pas en vue détail)
# ------------------------------------------------------------------------------
if st.session_state.selected_player_id is None:
    st.markdown('<div class="players-section">', unsafe_allow_html=True)
    st.markdown("""
    <div class="players-header">
      <h2 class="section-title">Top Joueurs</h2>
      <p class="section-subtitle">Cliquez sur un joueur pour analyser sa performance détaillée.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="players-grid">', unsafe_allow_html=True)

    for _, prow in filtered_players.iterrows():
        pm = df_matches[df_matches['PlayerID'] == prow['PlayerID']] if 'PlayerID' in df_matches.columns else pd.DataFrame()
        total_goals = int(pm['Buts'].sum()) if not pm.empty and 'Buts' in pm.columns else 0
        total_assists = int(pm['Passe décisive'].sum()) if not pm.empty and 'Passe décisive' in pm.columns else 0
        total_matches = len(pm[pm['Match joue'] == 1]) if not pm.empty and 'Match joue' in pm.columns else len(pm)
        avg_rating = float(pm['Minute/titularisation'].mean()) if not pm.empty and 'Minute/titularisation' in pm.columns else 0.0

        badges = []
        if total_goals > 0: badges.append("Buteur")
        if total_assists > 0: badges.append("Passeur")
        if avg_rating > 0.5: badges.append("Titulaire")
        if len(badges) == 0: badges.append("En progression")

        st.markdown(f"""
        <div class="player-card">
          <div class="player-card-header">
            <div class="player-avatar"><div class="player-avatar-placeholder">⚽</div></div>
            <div class="player-number">#{prow.get('PlayerID', '?')}</div>
            <div class="player-card-overlay">
              <div class="player-name">{prow.get('Prénom','')} {prow.get('Nom','')}</div>
              <div class="player-meta">{prow.get('Club','—')} • {prow.get('Poste','—')}</div>
            </div>
          </div>
          <div class="player-card-content">
            <div class="player-badges">
              <span class="badge badge-position">{prow.get('Poste','—')}</span>
              {" ".join([f'<span class="badge badge-info">{b}</span>' for b in badges])}
            </div>
            <div class="player-stats-grid">
              <div class="stat-item"><div class="stat-value">{total_goals}</div><div class="stat-label">Buts</div></div>
              <div class="stat-item"><div class="stat-value">{total_assists}</div><div class="stat-label">Passes</div></div>
              <div class="stat-item"><div class="stat-value">{total_matches}</div><div class="stat-label">Matchs</div></div>
              <div class="stat-item"><div class="stat-value">{avg_rating:.1f}</div><div class="stat-label">Note</div></div>
            </div>
            <div class="player-card-cta">Voir le profil →</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Bouton pour ouvrir le profil (affiché sous chaque carte)
        if st.button(f"Voir profil {prow['PlayerID']}", key=f"btn_{prow['PlayerID']}", use_container_width=True):
            select_player(int(prow['PlayerID']))

    st.markdown('</div></div>', unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 9) Pied de page (espace)
# ------------------------------------------------------------------------------
st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
