import streamlit as st
import pandas as pd
import numpy as np
import os
import urllib.parse

# Import modules
from config import setup_page_config, load_custom_css, display_header, display_footer
from data_management import init_data, load_data, save_data, export_to_excel
from pages import (
    show_home_page, show_create_dossier_page, show_buyer_tracking_page,
    show_management_page, show_kpi_page, show_batch_assignment_page
)

# --- PAGE CONFIG ---
setup_page_config()

# --- CUSTOM CSS ---
load_custom_css()

# --- HEADER ---
display_header()

# --- INIT DATA ---
init_data()

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_data_cached():
    return load_data()

# --- SESSION STATE INIT ---
if 'dossiers' not in st.session_state:
    dossiers_df, buyers_df = load_data_cached()
    st.session_state.dossiers = dossiers_df
    st.session_state.buyers = buyers_df

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2986/2986820.png", width=80)
st.sidebar.title("🛒 Achat Assistant")
st.sidebar.markdown("### Navigation")

menu = st.sidebar.radio(
    "Menu",
    ["🏠 Accueil", "📝 Créer un Dossier", "👥 Suivi des Acheteurs", "ParallelGroup", "🔧 Gestion", "📈 KPI"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Configuration")

# Lead name for reference
ly_name = st.sidebar.text_input("Votre nom (pour référence)", "Mme Touhami Zahra")

# Buyer management
if st.sidebar.toggle("Gérer les acheteurs", False):
    with st.sidebar.expander("➕ Ajouter un acheteur", expanded=True):
        new_buyer = st.text_input("Nom de l'acheteur")
        new_email = st.text_input("Email (optionnel)")
        
        if st.button("Ajouter", use_container_width=True):
            if new_buyer and new_buyer not in st.session_state.buyers["Name"].values:
                new_row = pd.DataFrame([{"Name": new_buyer, "Email": new_email}])
                st.session_state.buyers = pd.concat([st.session_state.buyers, new_row], ignore_index=True)
                save_data()
                st.success(f"✅ {new_buyer} ajouté !")
                st.rerun()
            elif new_buyer in st.session_state.buyers["Name"].values:
                st.warning("⚠️ Cet acheteur existe déjà")

# Excel export
if not st.session_state.dossiers.empty:
    excel_data = export_to_excel(st.session_state.dossiers)
    st.sidebar.download_button(
        label="💾 Exporter en Excel",
        data=excel_data,
        file_name="dossiers_achat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# --- MAIN CONTENT ---
if menu == "🏠 Accueil":
    show_home_page()
elif menu == "📝 Créer un Dossier":
    show_create_dossier_page()
elif menu == "👥 Suivi des Acheteurs":
    show_buyer_tracking_page()
elif menu == "🔧 Gestion":
    show_management_page()
elif menu == "📈 KPI":
    show_kpi_page()
elif menu == "ParallelGroup":
    show_batch_assignment_page()

# --- FOOTER ---
display_footer()