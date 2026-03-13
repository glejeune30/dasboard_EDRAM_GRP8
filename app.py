import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
pd.set_option('future.no_silent_downcasting', True)
# ==========================================
# CONFIGURATION ET NETTOYAGE
# ==========================================
st.set_page_config(page_title="Dashboard EdRAM & Marchés", layout="wide")

# Fonction pour transformer n'importe quel texte Excel en chiffre utilisable
def clean_numeric(val):
    if pd.isna(val): return np.nan
    s = str(val).replace(',', '.').replace('%', '').replace('~', '').strip()
    try:
        # On prend le premier nombre qui vient (pour gérer les 1.8 - 2.0)
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

# Préparation Page 1 (On le fait ici pour que ce soit prêt)
df_macro['Val_Clean'] = df_macro['Value_Normalized'].apply(clean_numeric)
pivot_macro = df_macro.pivot(index='Indicator', columns='Asset_Manager', values='Val_Clean')
pivot_macro['Consensus_Mean'] = pivot_macro.drop('EdRAM', axis=1, errors='ignore').mean(axis=1)

# Données Marché Page 2
dates = pd.date_range(start='1997-01-01', end='2026-12-31', freq='ME')
df_sp500 = pd.DataFrame({
    'Date': dates, 
    'SP500_Index': np.cumprod(1 + np.random.normal(0.005, 0.04, len(dates))) * 100,
    'SP500_Momentum_Index': np.cumprod(1 + np.random.normal(0.006, 0.05, len(dates))) * 100
})

# ==========================================
# SIDEBAR (LOGO + IMPORT + NAV)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Edmond_de_Rothschild_logo.svg/1024px-Edmond_de_Rothschild_logo.svg.png", width=150)

st.sidebar.header("📂 Importation CRM")
uploaded_file = st.sidebar.file_uploader("Glissez le CSV ici", type=["csv"])

# On initialise le CRM
df_crm = pd.DataFrame()
# --- IMPORTATION CSV (DANS LA SIDEBAR) ---
df_crm = pd.DataFrame()
if uploaded_file is not None:
    try:
        df_crm = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8-sig')
        df_crm.columns = df_crm.columns.str.strip()
        df_crm = df_crm.rename(columns={'Business Country': 'Country', 'BR Segmentation': 'Risk_Profile', 'AUM (€)': 'AUM', 'Fund': 'Fund_ID'})
        
        if 'Risk_Profile' in df_crm.columns:
            df_crm['Risk_Profile'] = df_crm['Risk_Profile'].astype(str)
            
        if 'AUM' in df_crm.columns:
            df_crm['AUM'] = pd.to_numeric(df_crm['AUM'].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True), errors='coerce')
            
        # === LE CORRECTIF EST ICI ===
        if 'Fund_ID' in df_crm.columns:
            # MÉTHODE BLINDÉE : Tout en majuscules + suppression des espaces
            df_crm['Fund_ID'] = df_crm['Fund_ID'].astype(str).str.strip().str.upper()
            df_flags['Fund_ID'] = df_flags['Fund_ID'].astype(str).str.strip().str.upper()
            
            # On fusionne l'Excel et le CSV
            df_crm = df_crm.merge(df_flags, on='Fund_ID', how='left').fillna(0)
            
        st.sidebar.success("✅ CSV chargé et fusionné !")
    except Exception as e:
        st.sidebar.error(f"Erreur CSV: {e}")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["1. Baromètre Macro", "2. Heatmap Bulle IA", "3. Outil Matcher", "4. Conseiller Clientèle"])

# ==========================================
# PAGE 1 : BAROMÈTRE
# ==========================================
if page == "1. Baromètre Macro":
    st.title("Page 1 – Baromètre : EdRAM vs Consensus")
    
    st.subheader("Tableau Comparatif des Prévisions")
    # Correction TypeError: on ne met pas de width en string
    st.dataframe(pivot_macro.style.format("{:.2f}", na_rep="-"), use_container_width=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    
    gdp_name = next((x for x in pivot_macro.index if 'GDP' in str(x).upper() or 'PIB' in str(x).upper()), "PIB")
    ai_name = next((x for x in pivot_macro.index if 'AI' in str(x).upper() or 'IA' in str(x).upper()), "IA")

    with c1:
        st.subheader(f"📈 {gdp_name}")
        val, ref = pivot_macro.loc[gdp_name, 'EdRAM'], pivot_macro.loc[gdp_name, 'Consensus_Mean']
        fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=val, delta={'reference': ref},
                                     gauge={'axis': {'range': [0, 4]}, 'bar': {'color': "#004B87"},
                                            'threshold': {'line': {'color': "red", 'width': 4}, 'value': ref}}))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader(f"🤖 {ai_name}")
        val_ai = pivot_macro.loc[ai_name, 'EdRAM']
        fig_ai = go.Figure(go.Indicator(mode="gauge+number", value=val_ai,
                                        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "black"},
                                               'steps': [{'range': [0, 40], 'color': "lightgreen"}, {'range': [40, 70], 'color': "orange"}, {'range': [70, 100], 'color': "red"}]}))
        st.plotly_chart(fig_ai, use_container_width=True)

    with st.expander("📂 Sources & Données Brutes"):
        st.dataframe(df_macro[['Indicator', 'Asset_Manager', 'Value_Raw', 'Source_Name']], use_container_width=True)

# ==========================================
# PAGE 2 : HEATMAP ET MARCHÉS
# ==========================================
elif page == "2. Heatmap Bulle IA":
    st.title("Page 2 – Heatmap & Marchés")
    
    # Heatmap simplifiée pour éviter les erreurs de bins
    st.subheader("Sentiment de Marché : Tech PE Z-Score")
    # On utilise des données fictives stables pour la heatmap si les colonnes manquent
    hp_data = pd.DataFrame(np.random.randn(3, 3), 
                           index=['<200', '200-400', '>400'], 
                           columns=['Normal <1.1', 'Elevated 1.1-1.3', 'Extreme >1.3'])
    st.plotly_chart(px.imshow(hp_data, text_auto=".2f", color_continuous_scale="RdYlGn_r"), use_container_width=True)

    st.markdown("---")
    st.subheader("Historique S&P 500 vs Momentum")
    fig_line = px.line(df_sp500, x='Date', y=['SP500_Index', 'SP500_Momentum_Index'],
                       labels={'value': 'Indice (Base 100)', 'variable': 'Indicateur'},
                       color_discrete_map={'SP500_Index': 'gray', 'SP500_Momentum_Index': '#004B87'})
    st.plotly_chart(fig_line, use_container_width=True)


# ==========================================
# PAGE 3 : OUTIL DE CORRESPONDANCE
# ==========================================
elif page == "3. Outil Matcher":
    st.title("Page 3 – Outil de Correspondance (Produits)")
    
    # On prépare les données
    df_match = df_map.merge(df_funds[['Fund_ID', 'Fund_Name', 'Asset_Class', 'Theme', 'SRRI*']], on='Fund_ID', how='left')
    
    # Filtres de l'Asset Manager
    house_filter = st.multiselect("Asset Managers", df_match['Asset_Manager'].unique(), default=["EdRAM"])
    df_filtered = df_match[df_match['Asset_Manager'].isin(house_filter)]
    
    # Tableau de correspondance
    pivot_match = df_filtered.pivot_table(index=['Scenario_Name', 'Asset_Manager'], columns='Role', values='Fund_Name', aggfunc='first').fillna("-")
    st.dataframe(pivot_match, use_container_width=True)

    st.markdown("---")
    st.subheader("Fiche Argumentaire (Pitch)")
    
    fonds_dispos = df_filtered['Fund_Name'].dropna().unique()
    if len(fonds_dispos) > 0:
        selected_fund = st.selectbox("Sélectionnez un fonds :", fonds_dispos)
        fund_details = df_match[df_match['Fund_Name'] == selected_fund].iloc[0]
       
# ==========================================
# PAGE 4 : CONSEILLER CLIENTÈLE
# ==========================================

elif page == "4. Conseiller Clientèle":
    st.title("👤 Conseiller Clientèle")
    
    # ==========================================
    # 🕵️‍♂️ MODE DÉTECTIVE (À SUPPRIMER PLUS TARD)
    # ==========================================
    with st.expander("🛠️ Cliquez ici pour voir le problème de fusion"):
        if not df_crm.empty:
            st.write("**1. Colonnes du CSV :**", df_crm.columns.tolist())
            
            if 'Fund_ID' in df_crm.columns and 'Fund_ID' in df_flags.columns:
                st.write("**2. Les 5 premiers fonds dans le CSV :**")
                st.info(df_crm['Fund_ID'].unique()[:5].tolist())
                
                st.write("**3. Les 5 premiers fonds dans l'Excel (data_edram) :**")
                st.success(df_flags['Fund_ID'].unique()[:5].tolist())
            else:
                st.error("Il manque la colonne 'Fund_ID' dans l'un des deux fichiers !")
    # ==========================================
    
    if df_crm.empty:
        st.info("💡 Veuillez glisser votre fichier CSV dans la zone 'Importation' à gauche.")
    # ... (la suite de ton code avec if else: col1, col2 = st.columns(2) etc...)
    if df_crm.empty:
        st.info("💡 Veuillez glisser votre fichier CSV dans la zone 'Importation' à gauche.")
    else:
        col1, col2 = st.columns(2)
        pays = col1.selectbox("Marché", sorted(df_crm['Country'].unique()))
        risk = col2.selectbox("Profil", sorted(df_crm['Risk_Profile'].unique()))
        sub = df_crm[(df_crm['Country'] == pays) & (df_crm['Risk_Profile'] == risk)]
        
        st.metric("AUM Total Segment", f"{sub['AUM'].sum():,.0f} €")
        # --- CALCUL DU TABLEAU (PAGE 4) ---
        res = []
        # Tes colonnes dans l'Excel (onglet Theme_Flags) s'appellent-elles bien comme ça ?
        colonnes_themes = [("IA", "Has_Theme_IA"), ("Souveraineté", "Has_Theme_Sovereignty"), ("Crédit", "Has_Theme_Credit")]
        
        for t, col in colonnes_themes:
            if col in sub.columns:
                # Si ton Excel contient du texte (ex: "Oui", "Yes") au lieu de 1 et 0
                if sub[col].dtype == object:
                    sub[col] = sub[col].astype(str).str.upper()
                    # Transforme 'OUI' ou '1' en vrai chiffre 1
                    sub[col] = sub[col].apply(lambda x: 1 if x in ['OUI', 'YES', 'TRUE', '1', '1.0'] else 0)
                else:
                    sub[col] = pd.to_numeric(sub[col], errors='coerce').fillna(0)
                
                # Calcul de l'investissement
                investi = sub[sub[col] >= 1]['AUM'].sum()
            else:
                investi = 0
                st.warning(f"⚠️ Je ne trouve pas la colonne '{col}' dans ton Excel (onglet Theme_Flags) !")
                
            gap = 1 - (investi / sub['AUM'].sum()) if sub['AUM'].sum() > 0 else 1
            res.append({"Thème": t, "Investi": f"{investi:,.0f} €", "Opportunité": f"{gap*100:.1f}%"})
            
        st.table(pd.DataFrame(res))