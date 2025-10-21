import streamlit as st

def setup_page_config():
    """Set up the Streamlit page configuration"""
    st.set_page_config(
        page_title="Achat Assistant",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="auto"
    )

def load_custom_css():
    """Load custom CSS styling"""
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

    /* Alerts */
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

def display_header():
    """Display the application header"""
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

def display_footer():
    """Display the application footer"""
    st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)