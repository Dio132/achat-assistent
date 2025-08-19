import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import urllib.parse

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Achat Assistant",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- CUSTOM CSS (LIGHT MODE ONLY) ---
st.markdown("""
<style>
/* Import Inter font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global styles */
body {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 15px;
}

/* Headers */
h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    color: #1e293b;
}

/* Sidebar */
.css-1d391kg {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}

/* Cards */
[data-testid="stMetric"] {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    border: 1px solid #e2e8f0;
}

/* Buttons */
.stButton>button {
    background-color: #2c7873;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
}

.stButton>button:hover {
    background-color: #235d5e;
}

/* Tables */
.stDataFrame, .stTable {
    background-color: #ffffff;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}

/* Progress bars */
.stProgress > div > div > div > div {
    background-color: #2c7873;
}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div style="text-align: center; margin-bottom: 1.5rem;">
  <h1 style="display: flex; align-items: center; justify-content: center; gap: 10px;">
    <span>🛒</span> Achat Assistant
  </h1>
  <p style="color: #64748b; max-width: 600px; margin: 0 auto;">
    Attribution intelligente des dossiers d'achat • Optimisation de la charge de travail
  </p>
</div>
""", unsafe_allow_html=True)

st.markdown('<hr style="margin: 1rem 0; border-color: #e2e8f0;">', unsafe_allow_html=True)

# --- INIT DATA ---
def init_data():
    if not os.path.exists("dossiers.csv"):
        pd.DataFrame(columns=[
            "ID", "Description", "Category", "Urgency", 
            "Buyer", "Status", "Assigned_Date", "Closed_Date",
            "Type_AO", "Devise", "Montant_Ajustement", "Date_Ajustement"
        ]).to_csv("dossiers.csv", index=False)
    
    if not os.path.exists("buyers.csv"):
        pd.DataFrame(columns=["Name", "Email"]).to_csv("buyers.csv", index=False)

init_data()

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_data():
    try:
        dossiers = pd.read_csv("dossiers.csv", parse_dates=["Assigned_Date", "Closed_Date"])
    except:
        dossiers = pd.DataFrame(columns=[
            "ID", "Description", "Category", "Urgency", 
            "Buyer", "Status", "Assigned_Date", "Closed_Date",
            "Type_AO", "Devise", "Montant_Ajustement", "Date_Ajustement"
        ])
    
    try:
        buyers = pd.read_csv("buyers.csv")
    except:
        buyers = pd.DataFrame(columns=["Name", "Email"])
    
    return dossiers, buyers

# --- SESSION STATE INIT ---
if 'dossiers' not in st.session_state:
    dossiers_df, buyers_df = load_data()
    st.session_state.dossiers = dossiers_df
    st.session_state.buyers = buyers_df

# --- HELPER FUNCTIONS ---
def ensure_datetime(df, col):
    if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def generate_dossier_id():
    today = datetime.now().strftime("%Y%m%d")
    if not st.session_state.dossiers.empty:
        last_id = st.session_state.dossiers["ID"].max()
        num = int(last_id.split("-")[-1]) + 1 if "-" in last_id else 1
    else:
        num = 1
    return f"PR-{today}-{num:03d}"

def get_buyer_workload():
    if st.session_state.dossiers.empty:
        return pd.Series(dtype=int)
    
    open_files = st.session_state.dossiers[st.session_state.dossiers["Status"] == "Open"]
    if open_files.empty:
        return pd.Series(0, index=st.session_state.buyers["Name"])
    
    workload = open_files["Buyer"].value_counts().reindex(st.session_state.buyers["Name"], fill_value=0)
    return workload

def get_last_assignment():
    if st.session_state.dossiers.empty:
        return pd.Series(dtype='datetime64[ns]')
    
    open_files = st.session_state.dossiers[st.session_state.dossiers["Status"] == "Open"].copy()
    
    if not pd.api.types.is_datetime64_any_dtype(open_files["Assigned_Date"]):
        open_files["Assigned_Date"] = pd.to_datetime(open_files["Assigned_Date"], errors='coerce')
    
    open_files = open_files.dropna(subset=["Assigned_Date"])
    
    if open_files.empty:
        return pd.Series(dtype='datetime64[ns]')
    
    last_assign = open_files.groupby("Buyer")["Assigned_Date"].max()
    return last_assign

def assign_to_least_busy():
    workload = get_buyer_workload()
    last_assign = get_last_assignment()
    
    if workload.empty:
        return st.session_state.buyers["Name"].iloc[0] if not st.session_state.buyers.empty else "N/A"
    
    min_work = workload.min()
    candidates = workload[workload == min_work].index.tolist()
    
    if len(candidates) > 1 and not last_assign.empty:
        candidate_assign = last_assign.reindex(candidates)
        sorted_candidates = candidate_assign.sort_values().index.tolist()
        return sorted_candidates[0]
    
    return candidates[0]

def save_data():
    st.session_state.dossiers.to_csv("dossiers.csv", index=False)
    st.session_state.buyers.to_csv("buyers.csv", index=False)

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2986/2986820.png", width=80)
st.sidebar.title("🛒 Achat Assistant")
st.sidebar.markdown("### Navigation")

menu = st.sidebar.radio(
    "Menu",
    ["🏠 Accueil", "📝 Créer un Dossier", "👥 Suivi des Acheteurs", "🔧 Gestion", "📈 KPI"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Configuration")

# Lead name for emails
ly_name = st.sidebar.text_input("Votre nom (pour les emails)", "Ly")

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
    @st.cache_data
    def convert_df_to_excel(df):
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Dossiers')
        return buffer.getvalue()
    
    excel_data = convert_df_to_excel(st.session_state.dossiers)
    st.sidebar.download_button(
        label="💾 Exporter en Excel",
        data=excel_data,
        file_name="dossiers_achat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# --- MAIN CONTENT ---
if menu == "🏠 Accueil":
    st.markdown("### Bienvenue dans Achat Assistant")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Dossiers", len(st.session_state.dossiers))
    with col2:
        open_count = len(st.session_state.dossiers[st.session_state.dossiers["Status"] == "Open"])
        st.metric("Dossiers Ouverts", open_count)
    with col3:
        st.metric("Acheteurs Actifs", len(st.session_state.buyers))
    
    st.info("""
    1. **Ajoutez des acheteurs** dans la barre latérale  
    2. **Créez des dossiers** dans 'Créer un Dossier'  
    3. L'outil attribue **automatiquement** au moins chargé  
    4. Suivez la charge et les KPIs
    """)

elif menu == "📝 Créer un Dossier":
    st.markdown("### 📝 Créer un nouveau dossier d'achat")
    
    if st.session_state.buyers.empty:
        st.warning("⚠️ Aucun acheteur configuré. Veuillez ajouter des acheteurs dans la barre latérale.")
    else:
        with st.form("new_dossier_form"):
            st.markdown("#### 🔹 Informations du dossier")

            # Manual ID input (optional)
            manual_id = st.text_input(
                "ID du dossier (optionnel)",
                placeholder="Ex: PR-20250405-001",
                help="Laissez vide pour générer un ID automatiquement"
            )

            desc = st.text_area(
                "Description du besoin",
                placeholder="Ex: 'Ordinateur portable pour nouveau collaborateur'",
                help="Décrivez clairement le besoin"
            )

            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox(
                    "Catégorie",
                    ["Informatique", "Pièce de rechange", "Service", "Matériel", "Autre"]
                )
            with col2:
                urgency = st.selectbox(
                    "Urgence",
                    ["Élevée", "Moyenne", "Faible"],
                    index=1
                )

            # Procurement fields
            st.markdown("#### 🏢 Processus d'achat")

            col3, col4 = st.columns(2)
            with col3:
                type_ao = st.selectbox(
                    "Type AO",
                    ["", "AO Ouvert", "AO Restreint", "Dialogue Compétitif", "Marché à Procédure Adaptée (MPA)", "Pas d'AO"],
                    help="Type de procédure d'appel d'offres"
                )
            with col4:
                devise = st.selectbox(
                    "Devise",
                    ["MAD", "EUR", "USD", "GBP", "Autre"],
                    index=0
                )

            st.markdown("#### 🔄 Ajustements (si applicable)")

            col5, col6 = st.columns(2)
            with col5:
                montant_ajustement = st.number_input(
                    "Montant d'ajustement",
                    value=0.0,
                    step=100.0,
                    format="%.2f",
                    help="Montant ajouté (+) ou retiré (-) du montant initial"
                )
            with col6:
                date_ajustement = st.date_input(
                    "Date d'ajustement",
                    value=None,
                    help="Date à laquelle l'ajustement a été appliqué"
                )

            submitted = st.form_submit_button("🟢 Créer et assigner", type="primary")

            if submitted:
                if not desc.strip():
                    st.error("❌ Veuillez entrer une description")
                else:
                    # Generate or use manual ID
                    if manual_id:
                        new_id = manual_id.strip()
                        if new_id in st.session_state.dossiers["ID"].values:
                            st.warning(f"⚠️ L'ID `{new_id}` existe déjà. Veuillez en choisir un autre.")
                            st.stop()
                    else:
                        new_id = generate_dossier_id()

                    # Auto-assign buyer
                    assigned_to = assign_to_least_busy()

                    # Get current datetime for assignment
                    assigned_date = datetime.now().strftime("%Y-%m-%d %H:%M")

                    # Prepare new dossier
                    new_dossier = {
                        "ID": new_id,
                        "Description": desc,
                        "Category": category,
                        "Urgency": urgency,
                        "Buyer": assigned_to,
                        "Status": "Open",
                        "Assigned_Date": assigned_date,
                        "Closed_Date": "",
                        "Type_AO": type_ao or "",
                        "Devise": devise,
                        "Montant_Ajustement": montant_ajustement,
                        "Date_Ajustement": date_ajustement.strftime("%Y-%m-%d") if date_ajustement else ""
                    }

                    # Add to session state
                    new_row = pd.DataFrame([new_dossier])
                    st.session_state.dossiers = pd.concat([st.session_state.dossiers, new_row], ignore_index=True)
                    save_data()

                    # Success message
                    st.success(f"""
                    ✅ **Dossier créé avec succès !**
                    - **ID**: `{new_id}`
                    - **Assigné à**: {assigned_to}
                    - **Statut**: Ouvert
                    """)

                    # Show assignment details
                    st.info(f"""
                    **Détails d'affectation**:
                    - Type AO: {type_ao or 'Non spécifié'}
                    - Devise: {devise}
                    - Ajustement: {montant_ajustement:+.2f} {devise}
                    - Date d'affectation: {assigned_date}
                    """)

                    # --- EMAIL NOTIFICATION ---
                    st.markdown("### 📧 Envoyer une notification")
                    
                    # Get buyer email
                    buyer_email_row = st.session_state.buyers[st.session_state.buyers["Name"] == assigned_to]
                    buyer_email = ""
                    if not buyer_email_row.empty:
                        buyer_email = buyer_email_row["Email"].values[0]
                        if pd.isna(buyer_email):
                            buyer_email = ""
                    
                    # Email content
                    subject = f"[Achat] Nouveau dossier assigné : {new_id}"
                    body = f"""Bonjour {assigned_to},

Un nouveau dossier d'achat vous a été attribué automatiquement :

- **ID du dossier** : {new_id}
- **Description** : {desc}
- **Catégorie** : {category}
- **Urgence** : {urgency}
- **Date d'affectation** : {datetime.now().strftime("%d/%m/%Y à %H:%M")}

Merci de prendre en charge ce dossier dans les plus brefs délais.

Cordialement,
{ly_name}"""
                    
                    # Create mailto link
                    mailto_url = f"mailto:{buyer_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                    
                    # Email button
                    st.markdown(
                        f'<a href="{mailto_url}" target="_blank">'
                        '<button style="background-color:#2c7873; color:white; border:none; padding:10px 20px; '
                        'border-radius:8px; font-size:16px; width:100%; cursor:pointer;">'
                        '🟢 Ouvrir l\'email dans Outlook'
                        '</button></a>',
                        unsafe_allow_html=True
                    )
                    
                    if not buyer_email:
                        st.warning("ℹ️ Aucun email configuré pour cet acheteur. Veuillez compléter l'email dans 'Gérer les acheteurs'.")

elif menu == "👥 Suivi des Acheteurs":
    st.markdown("### 👥 Suivi des Acheteurs")
    
    if st.session_state.buyers.empty:
        st.info("ℹ️ Aucun acheteur configuré. Veuillez ajouter des acheteurs dans la barre latérale.")
    else:
        # Select buyer
        selected_buyer = st.selectbox(
            "Sélectionner un acheteur",
            st.session_state.buyers["Name"],
            help="Choisissez un acheteur pour voir ses dossiers en cours"
        )

        # Get workload
        workload = get_buyer_workload()
        current_load = workload.get(selected_buyer, 0)

        # Show metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Dossiers Actifs", current_load)
        with col2:
            # Last assignment
            last_assign = get_last_assignment()
            last_date = last_assign.get(selected_buyer)
            if pd.notna(last_date) and last_date is not None:
                display = last_date.strftime("%d/%m/%Y")
            else:
                display = "Jamais"
            st.metric("Dernière Attribution", display)
        with col3:
            total_assigned = len(st.session_state.dossiers[st.session_state.dossiers["Buyer"] == selected_buyer])
            st.metric("Total Traité", total_assigned)

        st.markdown("---")

        # Filter active dossiers for this buyer
        buyer_dossiers = st.session_state.dossiers[
            (st.session_state.dossiers["Buyer"] == selected_buyer) &
            (st.session_state.dossiers["Status"] == "Open")
        ].copy()

        if not buyer_dossiers.empty:
            st.markdown(f"#### 📂 Dossiers actifs de **{selected_buyer}**")

            # Format date for display
            buyer_dossiers["Date_Ajustement"] = pd.to_datetime(buyer_dossiers["Date_Ajustement"], errors='coerce').dt.strftime("%d/%m/%Y").fillna("")

            # Prepare display columns
            display_df = buyer_dossiers[[
                "ID", "Description", "Category", "Urgency", "Status",
                "Type_AO", "Devise", "Montant_Ajustement", "Date_Ajustement", "Assigned_Date"
            ]].copy()

            # Rename columns for clarity
            display_df.rename(columns={
                "ID": "Dossier ID",
                "Description": "Description",
                "Category": "Catégorie",
                "Urgency": "Urgence",
                "Status": "Statut",
                "Type_AO": "Type AO",
                "Devise": "Devise",
                "Montant_Ajustement": "Montant Ajustement (devise)",
                "Date_Ajustement": "Date Ajustement",
                "Assigned_Date": "Date d'Affectation"
            }, inplace=True)

            # Format numeric column
            display_df["Montant Ajustement (devise)"] = display_df["Montant Ajustement (devise)"].apply(
                lambda x: f"{x:+,.2f}"
            )

            # Display as table
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            # Export option for this buyer
            buyer_data = buyer_dossiers.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Exporter les dossiers de " + selected_buyer,
                buyer_data,
                f"dossiers_{selected_buyer.lower().replace(' ', '_')}.csv",
                "text/csv",
                use_container_width=True
            )

        else:
            st.info(f"✅ {selected_buyer} n'a aucun dossier actif en ce moment.")

        # Closed files
        with st.expander("📋 Voir les dossiers terminés (fermés ou annulés)"):
            closed_files = st.session_state.dossiers[
                (st.session_state.dossiers["Buyer"] == selected_buyer) &
                (st.session_state.dossiers["Status"].isin(["Closed", "Cancelled"]))
            ]

            if not closed_files.empty:
                st.dataframe(
                    closed_files[["ID", "Description", "Status", "Assigned_Date", "Closed_Date"]],
                    hide_index=True
                )
            else:
                st.info("Aucun dossier fermé ou annulé.")

elif menu == "🔧 Gestion":
    st.markdown("### 🔧 Gestion des Dossiers")
    
    if st.session_state.dossiers.empty:
        st.info("ℹ️ Aucun dossier créé. Allez dans 'Créer un Dossier' pour commencer.")
    else:
        st.markdown("### 🔍 Sélectionner un dossier")
        
        # Option 1: Manual input
        manual_id = st.text_input(
            "Tapez l'ID du dossier",
            placeholder="Ex: PR-20250405-001",
            help="Utile si vous connaissez déjà l'ID"
        )
        
        # Option 2: Dropdown selection
        auto_id = st.selectbox(
            "Ou choisissez dans la liste",
            options=[""] + st.session_state.dossiers["ID"].tolist(),
            format_func=lambda x: "Sélectionnez un dossier" if x == "" else x
        )
        
        # Priority: manual input > dropdown
        if manual_id:
            selected_id = manual_id
        elif auto_id:
            selected_id = auto_id
        else:
            selected_id = None
        
        # Validate and process
        if selected_id:
            if selected_id in st.session_state.dossiers["ID"].values:
                dossier = st.session_state.dossiers[st.session_state.dossiers["ID"] == selected_id].iloc[0]
                
                with st.expander("📄 Détails du dossier", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID**: `{dossier['ID']}`")
                        st.write(f"**Description**: {dossier['Description']}")
                        st.write(f"**Catégorie**: {dossier['Category']}")
                        st.write(f"**Urgence**: {dossier['Urgency']}")
                    with col2:
                        st.write(f"**Acheteur**: {dossier['Buyer']}")
                        st.write(f"**Statut actuel**: {dossier['Status']}")
                        st.write(f"**Date d'attribution**: {dossier['Assigned_Date']}")
                        if pd.notna(dossier.get("Closed_Date", None)):
                            st.write(f"**Date de clôture**: {dossier['Closed_Date']}")
                
                # Status update
                st.subheader("✏️ Mettre à jour le statut")
                new_status = st.radio(
                    "Nouveau statut",
                    ["Open", "In Progress", "Closed", "Cancelled"],
                    index=["Open", "In Progress", "Closed", "Cancelled"].index(dossier["Status"])
                )
                
                if new_status != dossier["Status"]:
                    reason = st.text_area("Commentaire (optionnel)")
                    if st.button("💾 Enregistrer les modifications", type="primary"):
                        # Update status
                        st.session_state.dossiers.loc[st.session_state.dossiers["ID"] == selected_id, "Status"] = new_status
                        
                        # Update closed date if needed
                        if new_status == "Closed" and (pd.isna(dossier["Closed_Date"]) or dossier["Closed_Date"] == ""):
                            st.session_state.dossiers.loc[st.session_state.dossiers["ID"] == selected_id, "Closed_Date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        save_data()
                        st.success(f"✅ Statut mis à jour : `{selected_id}` → {new_status}")
                        st.rerun()
            else:
                st.warning(f"❌ Aucun dossier trouvé avec l'ID : `{selected_id}`")
                st.info("Vérifiez l'orthographe ou utilisez la liste déroulante.")
        else:
            st.info("👉 Veuillez entrer un ID ou sélectionner un dossier dans la liste.")

elif menu == "📈 KPI":
    st.markdown("### 📈 KPI & Améliorations")
    
    if st.session_state.dossiers.empty:
        st.info("ℹ️ Aucune donnée disponible. Créez des dossiers pour voir les KPIs.")
    else:
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Dossiers", len(st.session_state.dossiers))
        with col2:
            open_count = len(st.session_state.dossiers[st.session_state.dossiers["Status"] == "Open"])
            st.metric("Dossiers Ouverts", open_count)
        with col3:
            closed_count = len(st.session_state.dossiers[st.session_state.dossiers["Status"] == "Closed"])
            st.metric("Dossiers Terminés", closed_count)
        with col4:
            if closed_count > 0:
                time_diff = pd.to_datetime(st.session_state.dossiers["Closed_Date"]) - pd.to_datetime(st.session_state.dossiers["Assigned_Date"])
                avg_time = time_diff.mean().days
                st.metric("Temps moyen", f"{avg_time:.1f} jours")
            else:
                st.metric("Temps moyen", "N/A")
        
        # Charts
        st.subheader("Répartition des charges")
        workload = get_buyer_workload()
        if not workload.empty:
            workload_df = workload.reset_index()
            workload_df.columns = ["Buyer", "Active Files"]
            st.bar_chart(workload_df.set_index("Buyer"))
        else:
            st.info("Aucune donnée de charge disponible")
        
        st.subheader("Évolution des dossiers")
        if not st.session_state.dossiers.empty and "Assigned_Date" in st.session_state.dossiers.columns:
            st.session_state.dossiers["Date"] = pd.to_datetime(st.session_state.dossiers["Assigned_Date"]).dt.date
            daily_counts = st.session_state.dossiers.groupby(["Date", "Status"]).size().unstack(fill_value=0)
            st.line_chart(daily_counts)
        else:
            st.info("Pas assez de données pour l'évolution temporelle")
        
        # Fairness indicator
        st.subheader("Équité dans la répartition")
        if not workload.empty:
            max_load = workload.max()
            min_load = workload.min()
            fairness = 100 - ((max_load - min_load) / max_load * 100) if max_load > 0 else 100
            
            st.progress(int(fairness))
            st.markdown(f"**Indice d'équité** : `{fairness:.1f}%`")
            
            if fairness > 80:
                st.success("✅ **Répartition très équitable** des charges")
            elif fairness > 60:
                st.warning("⚠️ **Répartition acceptable**, à surveiller")
            else:
                st.error("❌ **Répartition inégale** - à corriger")
            
            # Improvement suggestion
            if min_load < max_load * 0.7:
                most_busy = workload.idxmax()
                least_busy = workload.idxmin()
                st.info(f"""
                **Recommandation d'ajustement** :  
                - Transférer des dossiers de **{most_busy}** vers **{least_busy}**  
                - {least_busy} a **{int(max_load - min_load)} dossier(s)** de moins que {most_busy}
                """)

# --- FOOTER ---
st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)
