import pandas as pd
import numpy as np
import os
from datetime import datetime
import streamlit as st

def init_data():
    """Initialize data files if they don't exist"""
    if not os.path.exists("dossiers.csv"):
        pd.DataFrame(columns=[
            "Code_Demande", "Description", "Type", "Articles", "Fournisseurs_Etrangers",
            "Fournisseurs_Total", "Buyer", "Status", "Assigned_Date", "Closed_Date",
            "Type_AO", "Devise", "Montant_Estime", "Complexite"
        ]).to_csv("dossiers.csv", index=False)
    
    if not os.path.exists("buyers.csv"):
        pd.DataFrame(columns=["Name", "Email"]).to_csv("buyers.csv", index=False)

@st.cache_data(ttl=60)
def load_data():
    """Load data from CSV files"""
    try:
        dossiers = pd.read_csv("dossiers.csv", parse_dates=["Assigned_Date", "Closed_Date"])
    except:
        dossiers = pd.DataFrame(columns=[
            "Code_Demande", "Description", "Type", "Articles", "Fournisseurs_Etrangers",
            "Fournisseurs_Total", "Buyer", "Status", "Assigned_Date", "Closed_Date",
            "Type_AO", "Devise", "Montant_Estime", "Complexite"
        ])
    
    try:
        buyers = pd.read_csv("buyers.csv")
    except:
        buyers = pd.DataFrame(columns=["Name", "Email"])
    
    return dossiers, buyers

def save_data():
    """Save data to CSV files"""
    st.session_state.dossiers.to_csv("dossiers.csv", index=False)
    st.session_state.buyers.to_csv("buyers.csv", index=False)

def generate_demande_code():
    """Generate a unique request code"""
    today = datetime.now().strftime("%Y%m%d")
    if not st.session_state.dossiers.empty:
        last_code = st.session_state.dossiers["Code_Demande"].max()
        num = int(last_code.split("-")[-1]) + 1 if "-" in last_code else 1
    else:
        num = 1
    return f"DA-{today}-{num:03d}"

def export_to_excel(df):
    """Convert DataFrame to Excel for download"""
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dossiers')
    return buffer.getvalue()