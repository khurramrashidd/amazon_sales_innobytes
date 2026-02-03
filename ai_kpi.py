import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# --- AI Configuration (Placeholder Keys) ---
import streamlit as st

# Load Gemini keys securely from Streamlit Secrets
try:
    API_KEYS = st.secrets["GEMINI_KEYS"]
except Exception:
    API_KEYS = []

# --- AI Key Rotation ---
def get_gemini_model():
    """Configures and returns a Gemini model, rotating keys if necessary."""
    if st.session_state.gemini_model is not None:
        return st.session_state.gemini_model

    index = st.session_state.api_key_index   
    try:
        api_key = API_KEYS[index]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-flash-preview') # Gemini flash model
        st.session_state.gemini_model = model
        return model
    except Exception as e:
        st.session_state.api_key_index = (index + 1) % len(API_KEYS)
        
        if st.session_state.api_key_index == 0:
            return None
            
        time.sleep(0.5)
        st.session_state.gemini_model = None
        return get_gemini_model()

def get_gemini_response(prompt: str) -> str:
    """Gets a response from the Gemini model, handling API key rotation on failure."""
    model = get_gemini_model()
    if model is None:
        return "Error: Could not configure AI model. All API keys failed."

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Fallback to general error message
        return "Error: AI request failed (Quota or API issue). Please wait or check keys."


# --- KPI Calculations & Display (Used in Step 7) ---
def calculate_kpis_and_display(df: pd.DataFrame):
    """Calculates and displays the final set of KPIs."""
    
    total_sales = df['Amount'].sum() if 'Amount' in df.columns else 0
    sales_in_cr = total_sales / 1_00_00_000
    formatted_sales = f"₹{sales_in_cr:.2f} Cr"
    
    total_orders = df['Order ID'].nunique() if 'Order ID' in df.columns else 0
    avg_order = df['Amount'].mean() if 'Amount' in df.columns else 0

    # Helper for safe access to max values
    def get_max_value(col):
        if col in df.columns and not df[col].empty:
            return df[col].value_counts().idxmax()
        return "N/A"

    kpis = {
        "💰 Total Sales": formatted_sales,
        "🛒 Total Orders": f"{total_orders:,}",
        "👕 Top Category": get_max_value('Category'),
        "📏 Most Demanded Size": get_max_value('Size'),
        "📍 Top State": get_max_value('ship-state'),
        "🏙️ Top City": get_max_value('ship-city'),
        "📦 Most Used Fulfillment": get_max_value('Fulfilment'),
        "💵 Avg. Order Value": f"₹{avg_order:,.2f}"
    }

    # Display KPIs in two rows of 4 columns
    cols1 = st.columns(4)
    cols2 = st.columns(4)
    
    items = list(kpis.items())
    
    for i in range(4):
        cols1[i].metric(items[i][0], items[i][1])
    for i in range(4):
        cols2[i].metric(items[i+4][0], items[i+4][1])

# --- AI Insights Generation (Used in Step 7) ---
def generate_insights_report(df: pd.DataFrame):
    """Generates a comprehensive AI-powered business insight report."""
    
    # Check for critical columns needed for AI context
    required_cols_for_final = ['Amount', 'Order ID', 'Category', 'ship-state', 'Fulfilment', 'Month']
    if not all(col in df.columns for col in required_cols_for_final):
        st.warning("Cannot generate detailed AI report: One or more critical analysis columns are missing.")
        return

    # 1. Prepare aggregated data samples
    monthly_sales = df.groupby('Month')['Amount'].sum().to_dict()
    top_categories = df['Category'].value_counts().nlargest(5).to_dict()
    top_states = df.groupby('ship-state')['Amount'].sum().nlargest(5).to_dict()
    
    # 2. Construct prompt
    prompt = f"""
    Act as a Senior Business Strategist. Analyze the provided Amazon Sales data snapshots and generate a concise business insight report with 3 key findings and 3 actionable recommendations.
    
    --- Data Context ---
    Total Records: {len(df):,}
    Total Sales: {df['Amount'].sum():,.0f}
    Avg. Order Value: {df['Amount'].mean():,.2f}
    
    Monthly Sales Trend (Month: Total Sales): {monthly_sales}
    Top 5 Categories (Category: Count): {top_categories}
    Top 5 States by Sales (State: Total Sales): {top_states}
    ---
    
    Focus on inventory strategy (based on categories), regional expansion (based on states), and sales trends.
    """
    
    # 3. Get response
    with st.spinner("🤖 Consulting Gemini AI for final insights..."):
        response = get_gemini_response(prompt)
        
    st.markdown("#### 🤖 Final AI Business Insights")
    st.info(response)
