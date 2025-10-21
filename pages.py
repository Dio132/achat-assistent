import streamlit as st
import math
import pandas as pd
import numpy as np
from datetime import datetime
from data_management import save_data, generate_demande_code, export_to_excel
from utils import calculate_dossier_score, get_buyer_total_workload, assign_smart_immediate, optimize_batch_assignment

def show_home_page():
    """Display the home page"""
    st.markdown("### Bienvenue dans Achat Assistant")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Dossiers", len(st.session_state.dossiers))
    with col2:
        active_count = len(st.session_state.dossiers[st.session_state.dossiers["Status"] == "Affecté"])
        st.metric("Dossiers Actifs", active_count)
    with col3:
        st.metric("Acheteurs Actifs", len(st.session_state.buyers))
    
    st.info("""
    1. **Ajoutez des acheteurs** dans la barre latérale  
    2. **Créez des dossiers** dans 'Créer un Dossier'  
    3. L'outil attribue **automatiquement** ou vous choisissez  
    4. Suivez la charge et les KPIs
    """)

def show_create_dossier_page():
    """Display the create dossier page"""
    st.markdown("### 📝 Créer un nouveau dossier d'achat")
    
    # Reset logic
    if 'form_submitted' in st.session_state and st.session_state.form_submitted:
        st.session_state.form_submitted = False
        
        # Clear ALL form values
        keys_to_clear = [
            "manual_code", "desc",
            "n_articles", "n_suppliers_total", "n_foreign_suppliers",
            "effort_level", "montant_estime", "devise", "type_ao", "manual_buyer_select"
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Force rerun to reflect cleared state
        st.rerun()
    
    if st.session_state.buyers.empty:
        st.warning("⚠️ Aucun acheteur configuré. Veuillez ajouter des acheteurs dans la barre latérale.")
    else:
        # Step 1: Choose Dossier Type
        st.markdown("#### 🔹 1. Sélectionner le type de dossier")
        dossier_type = st.radio(
            "Type de dossier",
            ["Pièce de rechange", "Marché", "Equipement"],
            key="dossier_type_select"
        )
        
        st.markdown('<hr style="margin: 1rem 0; border-color: #e2e8f0;">', unsafe_allow_html=True)
        
        # Step 2: Fill Parameters
        st.markdown(f"#### 📦 2. Remplir les paramètres — {dossier_type}")
        
        # Code Demande d'Achat
        st.text_input(
            "Code Demande d'Achat",
            key="manual_code"
        )
        
        st.text_area(
            "Description du besoin",
            help="Décrivez clairement le besoin",
            key="desc"
        )
        
        # Type-Specific Fields
        if dossier_type in ["Pièce de rechange", "Equipement"]:
            col1, col2 = st.columns(2)
            with col1:
                st.number_input("Nombre d'articles", min_value=1, value=1, step=1, key="n_articles")
            with col2:
                st.number_input("Nombre total de fournisseurs", min_value=1, value=1, step=1, key="n_suppliers_total")
            
            st.number_input("Nombre de fournisseurs étrangers", min_value=0, value=0, step=1, key="n_foreign_suppliers")
        
        elif dossier_type == "Marché":
            st.markdown("#### 🔍 Niveau d'effort attendu (facultatif)")
            st.slider(
                "Complexité du marché (1–5, 3 = moyen)",
                min_value=1,
                max_value=5,
                value=3,
                help="Facultatif : 1 = simple, 5 = très complexe",
                key="effort_level"
            )
            
            st.number_input("Nombre total de fournisseurs", min_value=1, value=1, step=1, key="n_suppliers_total")
            st.number_input("Nombre de fournisseurs étrangers", min_value=0, value=0, step=1, key="n_foreign_suppliers")

        # Common Fields
        st.markdown("#### 🏢 Processus d'achat")
        col3, col4 = st.columns(2)
        with col3:
            st.number_input("Montant estimé", min_value=0.0, value=0.0, step=100.0, format="%.2f", key="montant_estime")
        with col4:
            st.selectbox("Devise", ["MAD", "EUR", "USD", "GBP", "Autre"], index=0, key="devise")
        
        st.selectbox(
            "Type AO",
            ["AO Ouvert", "AO Restreint", "Autre"],
            help="Type de procédure d'appel d'offres",
            key="type_ao"
        )
        
        # Calculate Complexity
        n_articles = st.session_state.n_articles if dossier_type in ["Pièce de rechange", "Equipement"] else 1
        n_foreign_suppliers = st.session_state.n_foreign_suppliers
        n_suppliers_total = st.session_state.n_suppliers_total
        
        if dossier_type == "Marché":
            BASE_COMPLEXITY_BY_EFFORT = {
                1: 10.0,
                2: 20.0,
                3: 35.0,
                4: 60.0,
                5: 100.0
            }
            effort_level = st.session_state.get("effort_level", 3)
            base_complexity = BASE_COMPLEXITY_BY_EFFORT[effort_level]

            if n_foreign_suppliers <= 0:
                supplier_factor = 1.0
            elif n_foreign_suppliers == 1:
                supplier_factor = 1.4
            else:
                supplier_factor = min(1.4 + 0.2 * (n_foreign_suppliers - 1), 2.0)
                base_complexity *= 1.10

            if n_suppliers_total is None or n_suppliers_total < n_foreign_suppliers:
                n_suppliers_total = max(1, n_foreign_suppliers)
            compare_factor = 1.0 + 0.05 * max(0, n_suppliers_total - 1)
            compare_factor = min(compare_factor, 1.4)

            complexity_score = base_complexity * supplier_factor * compare_factor
            soft_limit = 100.0
            if complexity_score > soft_limit:
                complexity_score = soft_limit + math.log1p(complexity_score - soft_limit) * 20

        else:
            complexity_score = calculate_dossier_score(
                dossier_type, n_articles, n_foreign_suppliers, n_suppliers_total
            )
        
        st.metric("Niveau de complexité", f"{complexity_score:.1f} unités")
        
        # Assignment Control
        st.markdown('<hr style="margin: 1rem 0; border-color: #e2e8f0;">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Attribution du dossier")
        
        auto_assign = st.checkbox(
            "Laisser l'application choisir l'acheteur",
            value=True,
            help="Cochez pour une attribution intelligente basée sur la charge de travail"
        )
        
        assigned_to = None
        if auto_assign:
            assigned_to = assign_smart_immediate(complexity_score)
        else:
            buyer_names = st.session_state.buyers["Name"].tolist()
            assigned_to = st.selectbox("Sélectionner l'acheteur", buyer_names, key="manual_buyer_select")
            workload = get_buyer_total_workload()
            current_load = workload.get(assigned_to, 0)
            st.info(f"📊 Charge actuelle de {assigned_to} : {current_load:.1f} unités")
        
        # Submit Buttons
        st.markdown('<hr style="margin: 1rem 0; border-color: #e2e8f0;">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            create_and_assign = st.button("🟢 Créer et assigner", type="primary")
        with col2:
            save_as_draft = st.button("💾 Enregistrer comme brouillon")

        # Handle "Créer et assigner"
        if create_and_assign:
            if not st.session_state.desc.strip():
                st.error("❌ Veuillez entrer une description")
            else:
                manual_code_val = st.session_state.manual_code.strip() if st.session_state.manual_code else ""
                if manual_code_val:
                    if manual_code_val in st.session_state.dossiers["Code_Demande"].values:
                        st.warning(f"⚠️ Le code `{manual_code_val}` existe déjà. Veuillez en choisir un autre.")
                        st.stop()
                    new_code = manual_code_val
                else:
                    new_code = generate_demande_code()

                new_dossier = {
                    "Code_Demande": new_code,
                    "Description": st.session_state.desc,
                    "Type": dossier_type,
                    "Articles": n_articles,
                    "Fournisseurs_Etrangers": n_foreign_suppliers,
                    "Fournisseurs_Total": n_suppliers_total,
                    "Buyer": assigned_to,
                    "Status": "Affecté",
                    "Assigned_Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Closed_Date": "",
                    "Type_AO": st.session_state.type_ao or "",
                    "Devise": st.session_state.devise,
                    "Montant_Estime": st.session_state.montant_estime,
                    "Complexite": complexity_score
                }

                new_row = pd.DataFrame([new_dossier])
                st.session_state.dossiers = pd.concat([st.session_state.dossiers, new_row], ignore_index=True)
                save_data()

                st.success(f"""
                ✅ **Dossier créé avec succès !**
                - **Code Demande**: `{new_code}`
                - **Assigné à**: {assigned_to}
                - **Statut**: Affecté
                - **Complexité**: {complexity_score:.1f} unités
                """)

                buyer_email_row = st.session_state.buyers[st.session_state.buyers["Name"] == assigned_to]
                buyer_email = ""
                if not buyer_email_row.empty:
                    buyer_email = buyer_email_row["Email"].values[0]
                    if pd.isna(buyer_email):
                        buyer_email = ""

                if buyer_email:
                    mailto_url = f"mailto:{buyer_email}"
                    st.markdown(
                        f'<a href="{mailto_url}" target="_blank">'
                        '<button style="background-color:#2c7873; color:white; border:none; padding:10px 20px; '
                        'border-radius:8px; font-size:16px; width:100%; cursor:pointer;">'
                        '🟢 Ouvrir Outlook pour contacter l\'acheteur'
                        '</button></a>',
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("ℹ️ Aucun email configuré pour cet acheteur.")
                
                st.session_state.form_submitted = True

        # Handle "Enregistrer comme brouillon"
        if save_as_draft:
            if not st.session_state.desc.strip():
                st.error("❌ Veuillez entrer une description")
            else:
                manual_code_val = st.session_state.manual_code.strip() if st.session_state.manual_code else ""
                if manual_code_val:
                    if manual_code_val in st.session_state.dossiers["Code_Demande"].values:
                        st.warning(f"⚠️ Le code `{manual_code_val}` existe déjà. Veuillez en choisir un autre.")
                        st.stop()
                    new_code = manual_code_val
                else:
                    new_code = generate_demande_code()

                new_dossier = {
                    "Code_Demande": new_code,
                    "Description": st.session_state.desc,
                    "Type": dossier_type,
                    "Articles": n_articles,
                    "Fournisseurs_Etrangers": n_foreign_suppliers,
                    "Fournisseurs_Total": n_suppliers_total,
                    "Buyer": "",  # No buyer
                    "Status": "Brouillon",  # Draft status
                    "Assigned_Date": "",  # Not assigned yet
                    "Closed_Date": "",
                    "Type_AO": st.session_state.type_ao or "",
                    "Devise": st.session_state.devise,
                    "Montant_Estime": st.session_state.montant_estime,
                    "Complexite": complexity_score
                }

                new_row = pd.DataFrame([new_dossier])
                st.session_state.dossiers = pd.concat([st.session_state.dossiers, new_row], ignore_index=True)
                save_data()

                st.success(f"""
                ✅ **Brouillon enregistré avec succès !**
                - **Code Demande**: `{new_code}`
                - **Statut**: Brouillon (à affecter via 'ParallelGroup')
                - **Complexité**: {complexity_score:.1f} unités
                """)
                
                st.session_state.form_submitted = True

def show_buyer_tracking_page():
    """Display the buyer tracking page"""
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
        workload = get_buyer_total_workload()
        current_load = workload.get(selected_buyer, 0)
        
        # Show metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Charge Pondérée", f"{current_load:.1f}")
        with col2:
            # Last assignment
            active_files = st.session_state.dossiers[st.session_state.dossiers["Status"] == "Affecté"].copy()
            if not pd.api.types.is_datetime64_any_dtype(active_files["Assigned_Date"]):
                active_files["Assigned_Date"] = pd.to_datetime(active_files["Assigned_Date"], errors='coerce')
            
            buyer_files = active_files[active_files["Buyer"] == selected_buyer]
            if not buyer_files.empty:
                last_date = buyer_files["Assigned_Date"].max()
                display = last_date.strftime("%d/%m/%Y") if pd.notna(last_date) else "Jamais"
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
            (st.session_state.dossiers["Status"] == "Affecté")
        ].copy()
        
        if not buyer_dossiers.empty:
            st.markdown(f"#### 📂 Dossiers actifs de **{selected_buyer}**")
            
            # Prepare display columns
            display_df = buyer_dossiers[[
                "Code_Demande", "Description", "Type", "Status",
                "Articles", "Fournisseurs_Etrangers", "Fournisseurs_Total", 
                "Complexite", "Assigned_Date"
            ]].copy()
            
            # Rename columns for clarity
            display_df.rename(columns={
                "Code_Demande": "Code Demande",
                "Description": "Description",
                "Type": "Type",
                "Status": "Statut",
                "Articles": "Articles",
                "Fournisseurs_Etrangers": "Fourn. Étrangers",
                "Fournisseurs_Total": "Fourn. Total",
                "Complexite": "Complexité",
                "Assigned_Date": "Date d'Affectation"
            }, inplace=True)
            
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
                    closed_files[["Code_Demande", "Description", "Status", "Assigned_Date", "Closed_Date"]],
                    hide_index=True
                )
            else:
                st.info("Aucun dossier fermé ou annulé.")

def show_management_page():
    """Display the management page"""
    st.markdown("### 🔧 Gestion des Dossiers")
    
    if st.session_state.dossiers.empty:
        st.info("ℹ️ Aucun dossier créé. Allez dans 'Créer un Dossier' pour commencer.")
    else:
        st.markdown("### 🔍 Sélectionner un dossier")
        
        # Option 1: Manual input
        manual_code = st.text_input(
            "Tapez le code de la demande",
            placeholder="Ex: DA-20250405-001",
            help="Utile si vous connaissez déjà le code"
        )
        
        # Option 2: Dropdown selection
        auto_code = st.selectbox(
            "Ou choisissez dans la liste",
            options=[""] + st.session_state.dossiers["Code_Demande"].tolist(),
            format_func=lambda x: "Sélectionnez un dossier" if x == "" else x
        )
        
        # Priority: manual input > dropdown
        if manual_code:
            selected_code = manual_code
        elif auto_code:
            selected_code = auto_code
        else:
            selected_code = None
        
        # Validate and process
        if selected_code:
            if selected_code in st.session_state.dossiers["Code_Demande"].values:
                dossier = st.session_state.dossiers[st.session_state.dossiers["Code_Demande"] == selected_code].iloc[0]
                
                with st.expander("📄 Détails du dossier", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Code Demande**: `{dossier['Code_Demande']}`")
                        st.write(f"**Description**: {dossier['Description']}")
                        st.write(f"**Type**: {dossier['Type']}")
                        st.write(f"**Articles**: {dossier['Articles']}")
                        st.write(f"**Fournisseurs Étrangers**: {dossier['Fournisseurs_Etrangers']}")
                        st.write(f"**Fournisseurs Total**: {dossier['Fournisseurs_Total']}")
                    with col2:
                        st.write(f"**Acheteur**: {dossier['Buyer']}")
                        st.write(f"**Statut actuel**: {dossier['Status']}")
                        st.write(f"**Date d'attribution**: {dossier['Assigned_Date']}")
                        st.write(f"**Complexité**: {dossier['Complexite']:.1f} unités")
                        if pd.notna(dossier.get("Closed_Date", None)):
                            st.write(f"**Date de clôture**: {dossier['Closed_Date']}")
                
                # Status update
                st.subheader("✏️ Mettre à jour le statut")
                new_status = st.radio(
                    "Nouveau statut",
                    ["Affecté", "Closed", "Cancelled"],
                    format_func=lambda x: {
                        "Affecté": "Affecté",
                        "Closed": "Fermé",
                        "Cancelled": "Annulé"
                    }[x],
                    index=["Affecté", "Closed", "Cancelled"].index(dossier["Status"])
                )
                
                if new_status != dossier["Status"]:
                    reason = st.text_area("Commentaire (optionnel)")
                    if st.button("💾 Enregistrer les modifications", type="primary"):
                        # Update status
                        st.session_state.dossiers.loc[st.session_state.dossiers["Code_Demande"] == selected_code, "Status"] = new_status
                        
                        # Update closed date if needed
                        if new_status in ["Closed", "Cancelled"] and (pd.isna(dossier["Closed_Date"]) or dossier["Closed_Date"] == ""):
                            st.session_state.dossiers.loc[st.session_state.dossiers["Code_Demande"] == selected_code, "Closed_Date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        save_data()
                        st.success(f"✅ Statut mis à jour : `{selected_code}` → {new_status}")
                        st.rerun()
            else:
                st.warning(f"❌ Aucun dossier trouvé avec le code : `{selected_code}`")
                st.info("Vérifiez l'orthographe ou utilisez la liste déroulante.")
        else:
            st.info("👉 Veuillez entrer un code ou sélectionner un dossier dans la liste.")

def show_kpi_page():
    """Display the KPI page"""
    st.markdown("### 📈 KPI & Améliorations")
    
    if st.session_state.dossiers.empty:
        st.info("ℹ️ Aucune donnée disponible. Créez des dossiers pour voir les KPIs.")
    else:
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Dossiers", len(st.session_state.dossiers))
        with col2:
            active_count = len(st.session_state.dossiers[st.session_state.dossiers["Status"] == "Affecté"])
            st.metric("Dossiers Actifs", active_count)
        with col3:
            closed_count = len(st.session_state.dossiers[st.session_state.dossiers["Status"] == "Closed"])
            st.metric("Dossiers Fermés", closed_count)
        with col4:
            cancelled_count = len(st.session_state.dossiers[st.session_state.dossiers["Status"] == "Cancelled"])
            st.metric("Dossiers Annulés", cancelled_count)
        
        # Charts
        st.subheader("Répartition des charges (pondérée)")
        workload = get_buyer_total_workload()
        if not workload.empty:
            workload_df = workload.reset_index()
            workload_df.columns = ["Buyer", "Charge"]
            st.bar_chart(workload_df.set_index("Buyer"))
        else:
            st.info("Aucune donnée de charge disponible")
        
        st.subheader("Évolution des dossiers")
        if not st.session_state.dossiers.empty and "Assigned_Date" in st.session_state.dossiers.columns:
            st.session_state.dossiers["Date"] = pd.to_datetime(
                st.session_state.dossiers["Assigned_Date"], 
                format="%Y-%m-%d %H:%M",
                errors='coerce'
            ).dt.date
            daily_counts = st.session_state.dossiers.groupby(["Date", "Status"]).size().unstack(fill_value=0)
            st.line_chart(daily_counts)
        else:
            st.info("Pas assez de données pour l'évolution temporelle")
        
        # Status analysis
        st.subheader("Analyse par statut")
        status_counts = st.session_state.dossiers["Status"].value_counts()
        st.bar_chart(status_counts)

def show_batch_assignment_page():
    """Display the batch assignment page"""
    st.markdown("### 📦 Affectation par lot (optimisation globale)")
    
    if st.session_state.dossiers.empty:
        st.info("ℹ️ Aucun dossier disponible.")
    elif st.session_state.buyers.empty:
        st.warning("⚠️ Veuillez configurer des acheteurs.")
    else:
        # Filter: only unassigned dossiers (Status != "Affecté")
        unassigned = st.session_state.dossiers[st.session_state.dossiers["Status"] != "Affecté"].copy()
        
        if unassigned.empty:
            st.success("✅ Tous les dossiers sont déjà affectés.")
        else:
            st.info(f"📁 {len(unassigned)} dossier(s) non affecté(s) disponibles.")
            
            # Let user select which to include in batch
            st.markdown("#### Sélectionner les dossiers à affecter")
            selected_indices = []
            for idx, row in unassigned.iterrows():
                if st.checkbox(f"`{row['Code_Demande']}` - {row['Description'][:50]}...", key=f"select_{idx}"):
                    selected_indices.append(idx)
            
            if not selected_indices:
                st.warning("⚠️ Veuillez sélectionner au moins un dossier.")
            else:
                selected_dossiers = unassigned.loc[selected_indices]
                st.write(f"**{len(selected_dossiers)} dossier(s) sélectionné(s)**")
                
                if st.button("🚀 Lancer l'optimisation", type="primary"):
                    assignments, result = optimize_batch_assignment(selected_dossiers)
                    
                    if assignments is not None:
                        # Update session state
                        for d_idx, buyer in assignments.items():
                            st.session_state.dossiers.loc[d_idx, "Buyer"] = buyer
                            st.session_state.dossiers.loc[d_idx, "Status"] = "Affecté"
                            st.session_state.dossiers.loc[d_idx, "Assigned_Date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        save_data()
                        
                        # Show results
                        st.success(f"✅ Affectation optimale terminée ! Max workload = {result:.1f}")
                        
                        # Display assignment
                        result_df = pd.DataFrame([
                            {
                                "Code Demande": st.session_state.dossiers.loc[d, "Code_Demande"],
                                "Acheteur": buyer,
                                "Complexité": st.session_state.dossiers.loc[d, "Complexite"]
                            }
                            for d, buyer in assignments.items()
                        ])
                        st.dataframe(result_df, use_container_width=True, hide_index=True)
                    else:
                        st.error(f"❌ {result}")