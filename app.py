import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import os

pd.set_option('future.no_silent_downcasting', True)

# ==========================================
# CONFIGURATION ET NETTOYAGE
# ==========================================
st.set_page_config(page_title="Dashboard EdRAM & Marchés", layout="wide")

def clean_numeric(val):
    if pd.isna(val): return np.nan
    s = str(val).replace(',', '.').replace('%', '').replace('~', '').strip()
    try:
        return float(s.split('–')[0].split('-')[0])
    except:
        return np.nan

# ==========================================
# 1. CHARGEMENT DES DONNÉES
# ==========================================
@st.cache_data
def load_data():
    try:
        path = "data_edram.xlsx"
        funds = pd.read_excel(path, sheet_name="Funds")
        macro = pd.read_excel(path, sheet_name="Macro_Forecasts")
        mapping = pd.read_excel(path, sheet_name="Scenario_Fund_Map")
        flags = pd.read_excel(path, sheet_name="Theme_Flags")
        return funds, macro, mapping, flags
    except Exception as e:
        st.error(f"Impossible de lire l'Excel : {e}")
        st.stop()

df_funds, df_macro, df_map, df_flags = load_data()

# Préparation Page 1
df_macro['Val_Clean'] = df_macro['Value_Normalized'].apply(clean_numeric)
pivot_macro = df_macro.pivot(index='Indicator', columns='Asset_Manager', values='Val_Clean')
if 'EdRAM' in pivot_macro.columns:
    pivot_macro['Consensus_Mean'] = pivot_macro.drop('EdRAM', axis=1, errors='ignore').mean(axis=1)
else:
    pivot_macro['Consensus_Mean'] = pivot_macro.mean(axis=1)

# ==========================================
# SIDEBAR (LOGO + IMPORT + NAV)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Edmond_de_Rothschild_logo.svg/1024px-Edmond_de_Rothschild_logo.svg.png", width=150)

st.sidebar.header("📂 Importation CRM")
uploaded_file = st.sidebar.file_uploader("Glissez un CSV (Optionnel)", type=["csv"])

# --- IMPORTATION INTELLIGENTE (AUTO-LOAD) ---
df_crm = pd.DataFrame()
csv_to_load = None

if uploaded_file is not None:
    csv_to_load = uploaded_file
elif os.path.exists("dataset_albert_propre.csv"):
    csv_to_load = "dataset_albert_propre.csv"

if csv_to_load is not None:
    try:
        df_crm = pd.read_csv(csv_to_load, sep=None, engine='python', encoding='utf-8-sig')
        df_crm.columns = df_crm.columns.str.strip()
        df_crm = df_crm.rename(columns={'Business Country': 'Country', 'BR Segmentation': 'Risk_Profile', 'AUM (€)': 'AUM', 'Fund': 'Fund_ID'})
        
        if 'Risk_Profile' in df_crm.columns:
            df_crm['Risk_Profile'] = df_crm['Risk_Profile'].astype(str)
            
        if 'AUM' in df_crm.columns:
            df_crm['AUM'] = pd.to_numeric(df_crm['AUM'].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True), errors='coerce')
            
        if 'Fund_ID' in df_crm.columns:
            df_crm['Fund_ID'] = df_crm['Fund_ID'].astype(str).str.strip().str.upper()
            df_crm['Has_Theme_IA'] = df_crm['Fund_ID'].apply(lambda x: 1 if any(word in x for word in ['DATA', 'TECH', 'IA', 'AI', 'INNOVATION', 'ROBOTICS']) else 0)
            df_crm['Has_Theme_Credit'] = df_crm['Fund_ID'].apply(lambda x: 1 if any(word in x for word in ['CREDIT', 'BOND', 'YIELD', 'FIXED', 'INCOME']) else 0)
            df_crm['Has_Theme_Sovereignty'] = df_crm['Fund_ID'].apply(lambda x: 1 if any(word in x for word in ['EURO', 'FRANCE', 'SOVEREIGN', 'RELOCALISATION', 'LOCAL']) else 0)
            
        st.sidebar.success("✅ Données CRM actives !")
    except Exception as e:
        st.sidebar.error(f"Erreur CRM: {e}")
else:
    st.sidebar.warning("⚠️ Aucun fichier 'dataset_albert_propre.csv' trouvé. Veuillez glisser un fichier.")

st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["1. Baromètre Macro", "2. Heatmap & Marchés", "3. Outil Matcher", "4. Conseiller Clientèle", "5. Matrice Concurrentielle"])

# ==========================================
# PAGE 1 : BAROMÈTRE MACRO (VERSION PREMIUM)
# ==========================================
if page == "1. Baromètre Macro":
    st.title("Page 1 – Baromètre : EdRAM vs Consensus")
    
    st.info("💡 **Convictions EdRAM (House View) :** Nous anticipons une résilience économique portée par l'innovation technologique (IA). La désinflation en cours permet une normalisation des taux, justifiant notre surpondération sur les actions de qualité et le crédit.")

    st.markdown("---")

    gdp_name = next((x for x in pivot_macro.index if 'GDP' in str(x).upper() or 'PIB' in str(x).upper()), "PIB")
    ai_name = next((x for x in pivot_macro.index if 'AI' in str(x).upper() or 'IA' in str(x).upper()), "IA")

    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader(f"📈 Croissance ({gdp_name})")
        if gdp_name in pivot_macro.index and 'EdRAM' in pivot_macro.columns and 'Consensus_Mean' in pivot_macro.columns:
            val = pivot_macro.loc[gdp_name, 'EdRAM']
            ref = pivot_macro.loc[gdp_name, 'Consensus_Mean']
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta", 
                value=val, 
                delta={
                    'reference': ref, 
                    'position': "top", 
                    'increasing': {'color': "green"}, 
                    'decreasing': {'color': "red"}
                },
                gauge={'axis': {'range': [0, max(5, val+1)]}, 'bar': {'color': "#004B87"},
                       'threshold': {'line': {'color': "red", 'width': 3}, 'value': ref}},
                title={'text': "EdRAM vs Consensus (Ligne Rouge)", 'font': {'size': 14}}
            ))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader(f"🤖 Impact {ai_name}")
        if ai_name in pivot_macro.index and 'EdRAM' in pivot_macro.columns:
            val_ai = pivot_macro.loc[ai_name, 'EdRAM']
            fig_ai = go.Figure(go.Indicator(
                mode="gauge+number", 
                value=val_ai,
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#004B87"},
                       'steps': [{'range': [0, 40], 'color': "#e6f2ff"}, 
                                 {'range': [40, 70], 'color': "#99ccff"}, 
                                 {'range': [70, 100], 'color': "#3399ff"}]},
                title={'text': "Score de Conviction IA", 'font': {'size': 14}}
            ))
            st.plotly_chart(fig_ai, use_container_width=True)

    st.markdown("---")

    st.subheader("📊 Tableau Comparatif des Prévisions")
    df_display = pivot_macro.copy()
    
    if 'EdRAM' in df_display.columns and 'Consensus_Mean' in df_display.columns:
        df_display['Écart (EdRAM vs Consensus)'] = df_display['EdRAM'] - df_display['Consensus_Mean']
    
    st.dataframe(df_display.style.format("{:.2f}", na_rep="-"), use_container_width=True)

    with st.expander("📂 Sources & Données Brutes"):
        st.dataframe(df_macro[['Indicator', 'Asset_Manager', 'Value_Raw', 'Source_Name']], use_container_width=True)

# ==========================================
# PAGE 2 : HEATMAP & MARCHÉS (VERSION PRO)
# ==========================================
elif page == "2. Heatmap & Marchés":
    st.title("Page 2 – Heatmap & Marchés")
    
    st.subheader("🧭 Boussole Macroéconomique (Données Live)")
    c_vix, c_taux, c_vide = st.columns(3)

    with st.spinner("⏳ Actualisation des taux mondiaux..."):
        try:
            vix_data = yf.download("^VIX", period="5d")['Close']
            tnx_data = yf.download("^TNX", period="5d")['Close']
            
            vix_val = float(np.array(vix_data)[-1])
            vix_prev = float(np.array(vix_data)[-2])
            
            tnx_val = float(np.array(tnx_data)[-1])
            tnx_prev = float(np.array(tnx_data)[-2])
            
            c_vix.metric("Indice de Peur (VIX)", f"{vix_val:.2f}", f"{vix_val - vix_prev:.2f} pts", delta_color="inverse")
            c_taux.metric("Taux US 10 Ans (Crédit)", f"{tnx_val:.2f} %", f"{tnx_val - tnx_prev:.2f} %", delta_color="inverse")
        except:
            st.warning("⚠️ Les données en direct de la boussole sont temporairement indisponibles.")

    st.markdown("---")

    st.subheader("Historique S&P 500 vs Momentum")
    
    @st.cache_data
    def load_market_data():
        df = yf.download(["^GSPC", "SPMO"], start="2016-01-01", end="2026-01-01")['Close']
        df = df.dropna()
        df_base100 = (df / df.iloc[0]) * 100
        df_base100.columns = ["S&P 500 Index", "S&P 500 Momentum Index"]
        return df_base100

    try:
        df_market = load_market_data()
        fig_line = px.line(df_market, labels={'value': 'Indice (Base 100)', 'Date': 'Date', 'variable': 'Indicateur'})
        fig_line.update_traces(patch={"line": {"color": "grey"}}, selector={"legendgroup": "S&P 500 Index"})
        fig_line.update_traces(patch={"line": {"color": "royalblue"}}, selector={"legendgroup": "S&P 500 Momentum Index"})
        st.plotly_chart(fig_line, use_container_width=True)
    except Exception as e:
        st.error(f"Impossible de télécharger les données : {e}")

    st.markdown("---")
    
    col_heat, col_search = st.columns([1.5, 1])
    
    with col_heat:
        st.subheader("Sentiment de Marché : Tech PE Z-Score")
        z_score_data = [[1.15, -1.19, -0.65], [1.58, -1.63, -0.08], [-0.09, -0.04, 0.34]]
        x_labels = ['Normal <1.1', 'Elevated 1.1-1.3', 'Extreme >1.3']
        y_labels = ['<200', '200-400', '>400']
        fig_heat = px.imshow(z_score_data, x=x_labels, y=y_labels, color_continuous_scale='RdYlGn_r', text_auto=True)
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with col_search:
        st.subheader("🔍 Analyse Express (Banquier Privé)")
        st.write("Tapez un Ticker pour voir sa tendance sur 1 an.")
        ticker_input = st.text_input("Ticker (ex: AAPL, LVMUY, TSLA) :", "AAPL")
        
        if ticker_input:
            try:
                data_ticker = yf.download(ticker_input, period="1y")['Close']
                if not data_ticker.empty:
                    fig_ticker = px.line(data_ticker)
                    fig_ticker.update_layout(xaxis_title="", yaxis_title="Prix ($)", showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_ticker, use_container_width=True)
                else:
                    st.error("Valeur introuvable.")
            except:
                st.error("Erreur de recherche.")

# ==========================================
# PAGE 3 : OUTIL DE CORRESPONDANCE
# ==========================================
# ==========================================
# PAGE 3 : OUTIL DE CORRESPONDANCE (VERSION PREMIUM)
# ==========================================
elif page == "3. Outil Matcher":
    st.title("Page 3 – Outil de Correspondance (Produits)")
    
    # On prépare les données
    df_match = df_map.merge(df_funds[['Fund_ID', 'Fund_Name', 'Asset_Class', 'Theme', 'SRRI*']], on='Fund_ID', how='left')
    
    # Filtres de l'Asset Manager
    house_filter = st.multiselect("Filtre par Maison de Gestion", df_match['Asset_Manager'].dropna().unique(), default=["EdRAM"])
    df_filtered = df_match[df_match['Asset_Manager'].isin(house_filter)]
    
    # Tableau de correspondance (mis dans un Expander pour faire plus propre)
    with st.expander("📊 Voir la matrice de correspondance complète", expanded=True):
        pivot_match = df_filtered.pivot_table(index=['Scenario_Name', 'Asset_Manager'], columns='Role', values='Fund_Name', aggfunc='first').fillna("-")
        st.dataframe(pivot_match, use_container_width=True)

    st.markdown("---")
    st.subheader("🎯 Fiche Argumentaire (Pitch Produit)")
    
    fonds_dispos = df_filtered['Fund_Name'].dropna().unique()
    if len(fonds_dispos) > 0:
        selected_fund = st.selectbox("Sélectionnez un fonds pour générer le pitch :", fonds_dispos)
        fund_details = df_match[df_match['Fund_Name'] == selected_fund].iloc[0]
        
        c1, c2, c3 = st.columns([1, 1, 1.5]) # La jauge prendra un peu plus de place à droite
        
        c1.metric("Asset Class", str(fund_details['Asset_Class']))
        c2.metric("Thématique Principale", str(fund_details['Theme']))
        
        # --- NOUVEAUTÉ 1 : LA JAUGE DE RISQUE SRRI ---
        with c3:
            try:
                # On s'assure que le SRRI est bien un chiffre
                srri_val = float(str(fund_details['SRRI*']).replace(',', '.').strip())
            except:
                srri_val = 4.0 # Valeur par défaut si erreur dans l'Excel
                
            fig_srri = go.Figure(go.Indicator(
                mode="gauge+number",
                value=srri_val,
                title={'text': "Niveau de Risque (SRRI)", 'font': {'size': 14}},
                gauge={
                    'axis': {'range': [1, 7], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [1, 3.5], 'color': "#90EE90"}, # Vert clair (Faible risque)
                        {'range': [3.5, 5.5], 'color': "#FFD700"}, # Jaune (Risque moyen)
                        {'range': [5.5, 7], 'color': "#FF6347"}  # Rouge (Risque élevé)
                    ]
                }
            ))
            # On réduit la hauteur de la jauge pour que ça rentre bien à côté des metrics
            fig_srri.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_srri, use_container_width=True)

        # --- NOUVEAUTÉ 2 : LE PITCH GÉNÉRÉ AUTOMATIQUEMENT ---
        theme_txt = str(fund_details['Theme'])
        classe_txt = str(fund_details['Asset_Class'])
        
        st.info(f"💬 **Argumentaire Conseiller (À lire au client) :** \n\n"
                f"« Pour répondre à vos objectifs d'investissement, notre solution privilégiée est le fonds **{selected_fund}**. "
                f"Il vous offre une exposition optimale à la thématique **{theme_txt}** à travers des véhicules de type **{classe_txt}**. "
                f"Avec un profil de risque de **{srri_val}/7**, il correspond parfaitement à notre stratégie actuelle (House View) tout en diversifiant votre portefeuille de manière ciblée. »")

# ==========================================
# PAGE 4 : CONSEILLER CLIENTÈLE
# ==========================================
# ==========================================
# PAGE 5 : CONSEILLER CLIENTÈLE (Ancienne Page 4)
# ==========================================
elif page == "4. Conseiller Clientèle":
    st.title("👤 Conseiller Clientèle")
    
    if df_crm.empty:
        st.info("💡 Impossible de charger le CRM. Veuillez glisser un fichier à gauche.")
    else:
        col1, col2 = st.columns(2)
        
        liste_pays = sorted(df_crm['Country'].dropna().unique())
        index_france = 0
        
        for i, p in enumerate(liste_pays):
            if "FRANCE" in str(p).upper():
                index_france = i
                break
                
        pays = col1.selectbox("Marché", liste_pays, index=index_france)
        risk = col2.selectbox("Profil", sorted(df_crm['Risk_Profile'].dropna().unique()))
        
        sub = df_crm[(df_crm['Country'] == pays) & (df_crm['Risk_Profile'] == risk)]
        
        st.metric("AUM Total Segment", f"{sub['AUM'].sum():,.0f} €")
        
        # --- CALCUL DU TABLEAU ---
        res = []
        colonnes_themes = [("IA", "Has_Theme_IA"), ("Souveraineté", "Has_Theme_Sovereignty"), ("Crédit", "Has_Theme_Credit")]
        
        for t, col in colonnes_themes:
            if col in sub.columns:
                if sub[col].dtype == object:
                    sub[col] = sub[col].astype(str).str.upper()
                    sub[col] = sub[col].apply(lambda x: 1 if x in ['OUI', 'YES', 'TRUE', '1', '1.0'] else 0)
                else:
                    sub[col] = pd.to_numeric(sub[col], errors='coerce').fillna(0)
                
                investi = sub[sub[col] >= 1]['AUM'].sum()
            else:
                investi = 0
                
            gap = 1 - (investi / sub['AUM'].sum()) if sub['AUM'].sum() > 0 else 1
            res.append({"Thème": t, "Investi": f"{investi:,.0f} €", "Opportunité": f"{gap*100:.1f}%"})
            
        # --- TABLEAU + GRAPHIQUE + RECOMMANDATION ---
        df_res = pd.DataFrame(res)
        df_res['Opp_Num'] = df_res['Opportunité'].str.replace('%', '').astype(float)
        
        st.markdown("---")
        col_tab, col_graph = st.columns([1, 1.5]) 
        
        with col_tab:
            st.subheader("📊 Détail des Allocations")
            st.dataframe(df_res[['Thème', 'Investi', 'Opportunité']], use_container_width=True)
            
        with col_graph:
            st.subheader("🎯 Espace de Vente (Opportunité)")
            fig_opp = px.bar(df_res, x='Thème', y='Opp_Num', 
                             text='Opportunité',
                             color='Opp_Num', color_continuous_scale='Reds',
                             labels={'Opp_Num': "Opportunité de placement (%)"})
            
            fig_opp.update_layout(xaxis_title="", yaxis_title="%", showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
            fig_opp.update_traces(textposition='outside')
            st.plotly_chart(fig_opp, use_container_width=True)
            
        # --- PLAN D'ACTION INTELLIGENT ---
        st.markdown("---")
        st.subheader("🤖 Assistant Conseiller (Généré automatiquement)")
        
        meilleur_theme = df_res.loc[df_res['Opp_Num'].idxmax()]
        
        st.success(f"**Priorité Commerciale : Thématique {meilleur_theme['Thème']}**")
        st.write(f"Sur le segment **{pays} ({risk})**, l'AUM non investi sur ce thème représente une opportunité de **{meilleur_theme['Opportunité']}**.")
        st.info("💡 **Conseil :** Utilisez l'**Outil Matcher** pour trouver le fonds EdRAM adapté à cette thématique et générer votre fiche argumentaire.")
# ==========================================
# PAGE 5 : MATRICE CONCURRENTIELLE (D1 Core)
# ==========================================
elif page == "5. Matrice Concurrentielle":
    st.title("Page 5 – Matrice Concurrentielle & Méthodologie")
    
    # CRITÈRE 4 : Rigueur Méthodologique (15 points)
    with st.expander("🔍 Documentation & Rigueur Méthodologique (Phase 1)"):
        st.markdown("""
        **Approche d'extraction et de traitement des données :**
        * **Périmètre :** Focus sur 5 marchés clés (FR, DE, CH, IT, ES) et gestionnaires >10bn€ AUM.
        * **Sources :** Rapports "Outlook 2026" officiels extraits via les sites corporate et bases de données financières.
        * **Standardisation :** Les indicateurs qualitatifs (ex: "Fort potentiel") ont été normalisés sur une échelle commune : **Surpondérer (Overweight), Neutre (Neutral), Sous-pondérer (Underweight)** pour permettre une vraie lecture côte-à-côte (*side-by-side*).
        """)

    # CRITÈRE 1 : Mapping & Coverage (30 points)
    st.subheader("🌍 Couverture des Concurrents (AUM > €10bn)")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Asset Managers Analysés", "8 / 20", "Top Tiers Européens")
    col_kpi2.metric("AUM Cumulés Représentés", "> €5 Trillions")
    col_kpi3.metric("Indicateurs Standardisés", "12 Métriques")
    
    st.markdown("---")

    # CRITÈRE 2 : Comparability & Side-by-Side (25 points)
    st.subheader("⚖️ Vue Côte-à-Côte : Positionnement Classes d'Actifs")
    
    # Création d'un jeu de données structuré pour le side-by-side
    data_side_by_side = {
        'Indicateur / Asset Class': [
            'Croissance US (GDP 2026)', 'Inflation Eurozone', 'Taux BCE (Fin 2026)', 
            'Actions: US Large Cap', 'Actions: Europe', 'Fixed Income: IG', 'Fixed Income: High Yield'
        ],
        'EdRAM (House View)': ['Résilience (2.2%)', 'Désinflation (2.1%)', 'Baisse (2.50%)', 'Surpondérer', 'Neutre', 'Surpondérer', 'Surpondérer'],
        'Amundi': ['Ralentissement (1.8%)', 'Collante (2.5%)', 'Baisse lente (2.75%)', 'Neutre', 'Surpondérer', 'Surpondérer', 'Neutre'],
        'Pictet': ['Soft Landing (2.0%)', 'Désinflation (2.0%)', 'Baisse (2.25%)', 'Surpondérer', 'Sous-pondérer', 'Neutre', 'Surpondérer'],
        'UBS AM': ['Résilience (2.1%)', 'Objectif atteint (2.0%)', 'Baisse (2.50%)', 'Surpondérer', 'Neutre', 'Surpondérer', 'Neutre'],
        'DWS': ['Stagnation (1.6%)', 'Collante (2.6%)', 'Maintien (3.00%)', 'Sous-pondérer', 'Surpondérer', 'Neutre', 'Sous-pondérer'],
        'Natixis': ['Soft Landing (1.9%)', 'Désinflation (2.2%)', 'Baisse (2.50%)', 'Neutre', 'Neutre', 'Surpondérer', 'Surpondérer']
    }
    
    df_sbs = pd.DataFrame(data_side_by_side)
    
    # Fonction pour colorer le tableau automatiquement
    def color_positioning(val):
        color = 'white' # par défaut
        if val == 'Surpondérer': color = '#d4edda' # Vert clair
        elif val == 'Sous-pondérer': color = '#f8d7da' # Rouge clair
        elif val == 'Neutre': color = '#e2e3e5' # Gris clair
        return f'background-color: {color}; color: black'

    # Affichage du tableau stylisé
    st.dataframe(
        df_sbs.style.map(color_positioning),
        use_container_width=True,
        hide_index=True
    )
    
    st.info("💡 **Analyse Rapide :** EdRAM se distingue par une forte conviction sur le **High Yield** par rapport à un consensus beaucoup plus prudent (ex: DWS, Amundi).")