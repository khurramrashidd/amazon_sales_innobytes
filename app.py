import streamlit as st
import pandas as pd
import time
import os

# Ensure src is in path for modular imports
import sys
# Set up relative path for modular import compatibility
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_processing import load_raw_data, inspect_missing_values, drop_missing_columns, convert_date_and_derive
from visuals import plot_missing_values, plot_monthly_sales_trend, plot_top_categories, plot_fulfillment_status
from ui_helpers import make_snapshot, paginated_table_viewer, show_df_info, export_summary_report
from ai_kpi import get_gemini_response, calculate_kpis_and_display, generate_insights_report
from custom_dashboard import render_custom_dashboard

st.set_page_config(page_title="Data Analyst Pipeline", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Data Analyst Pipeline: Step-by-Step Sales Analysis")
st.sidebar.markdown("### Controls")

# --- 1. CONFIGURATION & STATE MANAGEMENT (INITIALIZATION) ---
REQUIRED_COLS = {
    'Date': 'Date Column', 'Amount': 'Sales Amount', 'Qty': 'Quantity Sold', 
    'Category': 'Product Category', 'Size': 'Product Size', 'ship-state': 'Shipping State',
    'ship-city': 'Shipping City', 'Fulfilment': 'Fulfillment Method', 'Status': 'Order Status',
    'Order ID': 'Order ID', 'B2B': 'B2B Flag (Optional)'
}
CRITICAL_COLS = ['Date', 'Amount', 'Order ID']

def init_state():
    if 'current_step' not in st.session_state: st.session_state.current_step = 0
    if 'df_raw' not in st.session_state: st.session_state.df_raw = pd.DataFrame()
    if 'df_current' not in st.session_state: st.session_state.df_current = pd.DataFrame()
    if 'snapshots' not in st.session_state: st.session_state.snapshots = {}
    if 'column_mapping' not in st.session_state: st.session_state.column_mapping = {}
    if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
    if 'mapped' not in st.session_state: st.session_state.mapped = False
    if 'missing_threshold' not in st.session_state: st.session_state.missing_threshold = 10
    if 'step_output' not in st.session_state: st.session_state.step_output = {} 
    if 'step_summaries' not in st.session_state: st.session_state.step_summaries = {}
    if 'show_null_sample' not in st.session_state: st.session_state.show_null_sample = False
    if 'show_custom_dashboard' not in st.session_state: st.session_state.show_custom_dashboard = False
    if 'api_key_index' not in st.session_state: st.session_state.api_key_index = 0
    if 'gemini_model' not in st.session_state: st.session_state.gemini_model = None

init_state()

# --- 2. STEP ACTION HANDLERS ---
def run_step(step_num, run_all_flag=False):
    df = st.session_state.df_current.copy()
    mapping = st.session_state.column_mapping
    new_step = step_num
    
    summary = {}
    
    try:
        if step_num == 1:
            df, summary = inspect_missing_values(df)
        elif step_num == 2:
            df, summary = drop_missing_columns(df, st.session_state.missing_threshold)
        elif step_num == 3:
            df, summary = convert_date_and_derive(df, mapping)
        elif step_num in [4, 5, 6, 7]:
            summary = {"data_ready": True} 
        
        st.session_state.step_summaries[new_step] = summary

        make_snapshot(df, new_step)
        st.session_state.df_current = df
        st.session_state.current_step = new_step
        
        if run_all_flag:
            st.session_state.step_output = {"run_all_output": new_step}
        else:
            st.session_state.step_output = {} 
        
    except Exception as e:
        st.error(f"Error executing Step {step_num}: {e}")
        st.session_state.step_output = {"error": str(e)}

def run_all_steps():
    if not st.session_state.mapped:
        st.error("Please complete Data Ingestion (Step 0) and Schema Mapping before running the full pipeline.")
        return

    st.session_state.df_current = st.session_state.df_raw.copy()
    make_snapshot(st.session_state.df_current, 0)
    
    for step in range(1, 8):
        run_step(step, run_all_flag=True)
        time.sleep(0.1) 

def undo_last_step():
    prev_step = st.session_state.current_step - 1
    if prev_step >= 0:
        st.session_state.df_current = st.session_state.snapshots[prev_step].copy()
        st.session_state.current_step = prev_step
        st.session_state.step_output = {"undo": True, "step": prev_step}
        st.session_state.show_custom_dashboard = False 
    else:
        st.warning("Cannot undo further. At initial state.")

# --- 3. SIDEBAR CONTROLS (CONDITIONAL RENDERING) ---
if not st.session_state.show_custom_dashboard:
    st.sidebar.markdown("### Step 0: Data Ingestion")
    uploaded_file = st.sidebar.file_uploader("Upload CSV (or use default)", type=["csv"])

    if st.sidebar.button("▶️ Load Raw Data from File (Step 0)"):
        df_raw = load_raw_data(uploaded_file)
        if not df_raw.empty:
            st.session_state.df_raw = df_raw
            st.session_state.df_current = df_raw.copy()
            make_snapshot(df_raw.copy(), 0)
            st.session_state.data_loaded = True
            st.session_state.mapped = False
            st.session_state.current_step = 0
            st.session_state.step_output = {"load": True}
            st.success("Raw data loaded. Proceed to Schema Mapping.")
        else:
            st.error("Failed to load data.")

    if st.session_state.data_loaded:
        st.sidebar.markdown("### Global Settings")
        st.session_state.missing_threshold = st.sidebar.slider(
            "Missing Value % Threshold (Step 2)", 0, 100, st.session_state.missing_threshold, 
            key='missing_threshold_slider'
        )
        st.session_state.show_null_sample = st.sidebar.checkbox(
            "Show Null Value Row Samples (Step 1)", 
            value=st.session_state.show_null_sample
        )
        
        st.sidebar.markdown("### Full Pipeline")
        if st.sidebar.button("▶️ Run All Steps (1-7)", type="primary"):
            run_all_steps()
        if st.sidebar.button("↩️ Undo Last Step"):
            undo_last_step()

    st.sidebar.markdown("---")
    st.sidebar.info(f"Current Step: **{st.session_state.current_step}**")
    st.sidebar.info(f"Rows: **{len(st.session_state.df_current):,}**")
else:
    # Custom dashboard sidebar elements (Back button)
    st.sidebar.header("Back to Pipeline")
    if st.sidebar.button("↩️ Back to Analysis Pipeline", key='sidebar_back_to_steps'):
        st.session_state.show_custom_dashboard = False
        st.rerun()

# --- 4. STEP CARD RENDERING FUNCTION ---
def render_step_card(step_num, title, run_func, button_label):
    is_executed = st.session_state.current_step >= step_num
    is_run_all_output = st.session_state.step_output.get('run_all_output') == step_num
    
    expander_title = f"Step {step_num}: {title} {'✅' if is_executed else ''}"
    
    with st.expander(expander_title, expanded=(is_executed or is_run_all_output)):
        if not is_executed or is_run_all_output: 
            if st.button(button_label, key=f"run_step_{step_num}", on_click=run_func, args=(step_num,)):
                st.session_state.step_output = {"run_all_output": step_num}

        if is_executed or is_run_all_output:
            df = st.session_state.df_current
            output = st.session_state.step_summaries.get(step_num, {})
            
            if 'error' in st.session_state.step_output:
                st.error("Previous step failed. Please check console for details.")
                return

            st.markdown(f"#### Snapshot Data ({len(df):,} Rows)")
            paginated_table_viewer(df, key_context=f"{step_num}_current_frame")
            
            # Helper for layout common to most steps
            st.markdown("---")
            col_d, col_ai = st.columns([1, 2])

            if step_num == 1:
                st.markdown("#### Missing Value Inspection")
                st.markdown(output.get('note', ''))
                if 'missing_summary' in output:
                    plot_missing_values(output['missing_summary'])
                if st.session_state.show_null_sample and 'sample_missing_rows' in output:
                    with st.container(border=True): 
                        st.markdown(f"**Sample Rows with Missing Data**")
                        paginated_table_viewer(output['sample_missing_rows'], max_rows=100, key_context=f"{step_num}_sample_rows")
                
                with col_d: export_summary_report(df, step_num)

            elif step_num == 2:
                st.markdown("#### Column Dropping Summary")
                st.markdown(output.get('note', ''))
                if 'dropped_summary' in output:
                    st.dataframe(output['dropped_summary'])
                with st.container(border=True):
                    st.markdown("**Compare Before/After Row Count**")
                    st.info(f"Rows before step: {output.get('rows_before'):,}. Rows after step: {output.get('rows_after'):,}")
                
                with col_d: export_summary_report(df, step_num)

            elif step_num == 3:
                st.markdown("#### Date Conversion & Feature Engineering")
                st.markdown(output.get('note', ''))
                with st.container(border=True):
                    st.markdown("**New Columns and Data Types**")
                    display_cols = ['Date', 'Month', 'Year', 'DayOfWeek']
                    valid_cols = [col for col in display_cols if col in df.columns]
                    st.dataframe(df[valid_cols].tail())
                    st.code(df.dtypes.to_string())

                with col_d: export_summary_report(df, step_num)

            elif step_num == 4:
                st.markdown("#### Sales Trend Analysis")
                st.plotly_chart(plot_monthly_sales_trend(df))
                
                with col_d: export_summary_report(df, step_num)
                with col_ai:
                    if st.button("📈 Get AI Insights for Sales Trends", key=f"ai_step_{step_num}"):
                        st.info("AI Feature Placeholder - See Step 7 for consolidated AI Report.")

            elif step_num == 5:
                st.markdown("#### Product Analysis (Category & Size)")
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plot_top_categories(df))
                with c2: st.plotly_chart(plot_top_categories(df, col='Size', title="Top Sizes by Order Count"))
                
                with col_d: export_summary_report(df, step_num)
                with col_ai:
                    if st.button("👕 Get AI Insights for Product Allocation", key=f"ai_step_{step_num}"):
                        st.info("AI Feature Placeholder - See Step 7 for consolidated AI Report.")

            elif step_num == 6:
                st.markdown("#### Fulfillment & Status Check")
                st.plotly_chart(plot_fulfillment_status(df))
                
                with col_d: export_summary_report(df, step_num)
                with col_ai:
                    if st.button("📦 Get AI Insights for Fulfillment", key=f"ai_step_{step_num}"):
                        st.info("AI Feature Placeholder - See Step 7 for consolidated AI Report.")

            elif step_num == 7:
                st.markdown("#### Final Business Insights & KPIs")
                st.success("Analysis Complete. Generating Final Insights...")
                calculate_kpis_and_display(df)
                generate_insights_report(df)
                
                st.markdown("---")
                # Button to switch to Custom Dashboard view
                if st.button("See More Customised View ➡️", key="switch_to_custom_dashboard", type="primary"):
                    st.session_state.show_custom_dashboard = True
                    st.rerun()

# --- 5. MAIN PAGE LAYOUT ---

# Render Custom Dashboard View (If toggle is set AND pipeline is finished)
if st.session_state.show_custom_dashboard and st.session_state.current_step >= 7:
    df_cleaned = st.session_state.df_current
    render_custom_dashboard(df_cleaned, get_gemini_response)

# Render Step-by-Step Pipeline View (Default view)
else:
    # Stage 1: Initial State / Raw Data View
    if st.session_state.data_loaded:
        st.markdown("---")
        st.subheader("Current Working DataFrame")
        if st.session_state.current_step == 0:
            st.info("Raw Data Loaded. Please complete Schema Mapping below.")
            show_df_info(st.session_state.df_raw)
        else:
            st.info(f"DataFrame after Step {st.session_state.current_step}:")
            paginated_table_viewer(st.session_state.df_current, key_context="step_0_current")

    # Stage 2: Schema Mapping
    if st.session_state.data_loaded and not st.session_state.mapped:
        st.markdown("---")
        st.header("Stage 2: Schema Mapping")
        st.info("Please confirm or select the correct column names for the analysis.")

        df_raw = st.session_state.df_raw
        current_cols = ['SKIP'] + list(df_raw.columns)
        
        col_map = {}
        cols = st.columns(4)
        col_index = 0
        
        for std_name, description in REQUIRED_COLS.items():
            default_idx = current_cols.index(std_name) if std_name in current_cols else 0
            
            with cols[col_index % 4]:
                selected = st.selectbox(f"{std_name} ({description})", options=current_cols, index=default_idx, key=f'map_{std_name}')
                if selected != 'SKIP':
                    col_map[selected] = std_name
            col_index += 1
        
        if st.button("🚀 Apply Mapping and Proceed to Steps 1-7", type="primary"):
            missing = [c for c in CRITICAL_COLS if c not in col_map.values()]
            if missing:
                st.error(f"Critical columns must be mapped: {', '.join(missing)}.")
            else:
                st.session_state.column_mapping = col_map
                st.session_state.mapped = True
                st.session_state.data_ready = True
                st.success("Mapping applied! You can now run the analysis steps below.")
                st.rerun()

    # Stage 3: Analysis Steps
    if st.session_state.data_loaded and st.session_state.mapped:
        st.markdown("---")
        st.header("Stage 3: Step-by-Step Analysis")

        render_step_card(1, "Inspect Missing Values", run_step, "▶️ Run Step 1: Missing Value Inspection")
        render_step_card(2, "Drop Columns by Threshold", run_step, "▶️ Run Step 2: Drop Missing Columns")
        render_step_card(3, "Feature Engineering (Date/Time)", run_step, "▶️ Run Step 3: Convert Dates & Derive Features")
        render_step_card(4, "Sales Trend Analysis", run_step, "▶️ Run Step 4: Sales Trend Visualization")
        render_step_card(5, "Product & Size Distribution", run_step, "▶️ Run Step 5: Product Analysis")
        render_step_card(6, "Fulfillment & Status Check", run_step, "▶️ Run Step 6: Fulfillment Analysis")
        render_step_card(7, "Final KPI & AI Insights Report", run_step, "▶️ Run Step 7: Generate Final Report")

        # Step X: Export/Download at the bottom of the pipeline
        st.markdown("---")
        st.header("Step X: Export & Download")
        col1, col2 = st.columns(2)
        with col1:
            csv_data = st.session_state.df_current.to_csv(index=False).encode()
            st.download_button("🔽 Download Cleaned Dataset (CSV)", csv_data, "cleaned_data_snapshot.csv", mime="text/csv")
        with col2:
            export_summary_report(st.session_state.df_current, st.session_state.current_step)