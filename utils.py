import pandas as pd
import numpy as np
import math
import streamlit as st

def calculate_dossier_score(
    dossier_type,
    n_articles,
    n_foreign_suppliers,
    n_suppliers_total=None,
):
    """Calculate complexity score for a dossier"""
    params = {
        "Marché": {"base": 6.0, "a": 0.2, "b": 1.0},
        "Pièce de rechange": {"base": 0.0, "a": 1.0, "b": 1.05},
        "Equipement": {"base": 0.5, "a": 0.8, "b": 1.03}
    }

    p = params.get(dossier_type, params["Pièce de rechange"])
    n_articles = max(1, n_articles)
    core = p["base"] + p["a"] * (n_articles ** p["b"])

    # Supplier factor
    if n_foreign_suppliers <= 0:
        supplier_factor = 1.0
    elif n_foreign_suppliers == 1:
        supplier_factor = 1.4
    else:
        supplier_factor = min(1.4 + 0.2 * (n_foreign_suppliers - 1), 2.0)
        core *= 1.10

    # Comparison factor
    if n_suppliers_total is None or n_suppliers_total < n_foreign_suppliers:
        n_suppliers_total = max(1, n_foreign_suppliers)
    compare_factor = 1.0 + 0.05 * max(0, n_suppliers_total - 1)
    compare_factor = min(compare_factor, 1.4)

    # Preliminary complexity
    complexity = core * supplier_factor * compare_factor 

    # Soft cap: logarithmic damping for very large dossiers
    soft_limit = 100.0
    if complexity > soft_limit:
        complexity = soft_limit + math.log1p(complexity - soft_limit) * 20

    return complexity

def get_buyer_total_workload():
    """Get total workload per buyer = sum of complexity scores of active dossiers"""
    if st.session_state.dossiers.empty:
        return pd.Series(dtype=float)
    
    active_files = st.session_state.dossiers[st.session_state.dossiers["Status"] == "Affecté"].copy()
    
    # Ensure complexity is numeric
    active_files["Complexite"] = pd.to_numeric(active_files["Complexite"], errors='coerce')
    
    # Sum scores per buyer
    workload = active_files.groupby("Buyer")["Complexite"].sum()
    
    # Ensure all buyers appear (even with 0)
    for buyer in st.session_state.buyers["Name"]:
        if buyer not in workload.index:
            workload[buyer] = 0.0
    
    return workload

def assign_smart_immediate(complexity_score):
    """Assign to buyer with lowest workload AFTER assignment"""
    # Get current workload of each buyer
    workload = get_buyer_total_workload()
    
    if workload.empty:
        return st.session_state.buyers["Name"].iloc[0] if not st.session_state.buyers.empty else "N/A"
    
    # Simulate: what will each buyer's workload be AFTER assignment?
    projected_loads = {}
    for buyer in workload.index:
        projected_loads[buyer] = workload[buyer] + complexity_score
    
    # Return buyer with lowest projected load
    return min(projected_loads, key=projected_loads.get)

def optimize_batch_assignment(selected_dossiers):
    """Optimize batch assignment using ILP"""
    try:
        import pulp
        
        # Prepare data
        D = selected_dossiers.index.tolist()
        A = st.session_state.buyers["Name"].tolist()
        C = {d: selected_dossiers.loc[d, "Complexite"] for d in D}
        
        # Create problem
        prob = pulp.LpProblem("BatchAssignment", pulp.LpMinimize)
        
        # Decision variables
        x = pulp.LpVariable.dicts("assign", [(d, a) for d in D for a in A], cat='Binary')
        Z = pulp.LpVariable("max_load", lowBound=0)
        
        # Objective: minimize max load
        prob += Z
        
        # Each dossier assigned once
        for d in D:
            prob += pulp.lpSum(x[(d, a)] for a in A) == 1
        
        # Max load definition
        for a in A:
            prob += pulp.lpSum(C[d] * x[(d, a)] for d in D) <= Z
        
        # Solve
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=30)
        result = prob.solve(solver)
        
        if pulp.LpStatus[prob.status] == "Optimal" or pulp.LpStatus[prob.status] == "Not Solved":
            # Extract solution
            assignments = {}
            for d in D:
                for a in A:
                    if pulp.value(x[(d, a)]) > 0.5:
                        assignments[d] = a
            
            return assignments, pulp.value(Z)
        else:
            return None, f"Impossible de résoudre le problème : {pulp.LpStatus[prob.status]}"
    
    except Exception as e:
        return None, f"Erreur lors de l'optimisation : {str(e)}"