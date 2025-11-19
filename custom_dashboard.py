import streamlit as st
import pandas as pd
import plotly.express as px
import time

# --- Helper Functions for Custom Dashboard ---

def calculate_and_display_final_kpis_custom(df: pd.DataFrame):
    """Calculates and displays the final set of KPIs based on the filtered data."""
    
    total_sales = df['Amount'].sum() if 'Amount' in df.columns else 0
    sales_in_cr = total_sales / 1_00_00_000
    formatted_sales = f"₹{sales_in_cr:.2f} Cr"
    
    total_orders = df['Order ID'].nunique() if 'Order ID' in df.columns else 0
    avg_order = df['Amount'].mean() if 'Amount' in df.columns else 0

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

def generate_insights_report_custom(df: pd.DataFrame, get_gemini_response_func):
    """Generates a comprehensive AI-powered business insight report on filtered data."""
    
    # Check for critical columns needed for AI context
    required_cols_for_final = ['Amount', 'Order ID', 'Category', 'ship-state', 'Fulfilment']
    if not all(col in df.columns for col in required_cols_for_final):
        st.warning("Cannot generate detailed AI report: One or more critical analysis columns are missing from the filtered data.")
        return

    # Prepare aggregated data samples
    # Check if Month column exists before grouping
    if 'Month' in df.columns and 'Amount' in df.columns:
        monthly_sales = df.groupby('Month')['Amount'].sum().to_dict()
    else:
        monthly_sales = "Data not available (Missing Month/Amount columns)"

    # Check if Category and ship-state columns exist
    if 'Category' in df.columns:
        top_categories = df['Category'].value_counts().nlargest(5).to_dict()
    else:
        top_categories = "Data not available (Missing Category column)"
        
    if 'ship-state' in df.columns and 'Amount' in df.columns:
        top_states = df.groupby('ship-state')['Amount'].sum().nlargest(5).to_dict()
    else:
        top_states = "Data not available (Missing ship-state/Amount columns)"
    
    prompt = f"""
    Act as a Senior Business Strategist. Analyze the user's currently filtered sales data and generate a concise business insight report with 3 key findings and 3 actionable recommendations.
    
    --- Data Context ---
    Total Records: {len(df):,}
    Total Sales: {df['Amount'].sum():,.0f}
    Avg. Order Value: {df['Amount'].mean():,.2f}
    
    Monthly Sales Trend (Month: Total Sales): {monthly_sales}
    Top 5 Categories (Category: Count): {top_categories}
    Top 5 States by Sales (State: Total Sales): {top_states}
    ---
    
    Focus on inventory strategy, regional performance, and sales trends within this specific segment.
    """
    
    with st.spinner("🤖 Consulting Gemini AI for final insights..."):
        response = get_gemini_response_func(prompt)
        
    st.markdown("#### 🤖 Final AI Business Insights")
    st.info(response)


# --- Main Rendering Function ---
def render_custom_dashboard(df_initial, get_gemini_response_func):
    """
    Renders the highly customized dashboard based on the cleaned data (df_initial).
    It includes interactive sidebar filters and integrated AI insights.
    """
    
    st.header("✨ Customizable Extended Dashboard")
    st.markdown("This view uses the cleaned data from the pipeline but provides granular filtering and dynamic AI insights. **All charts reflect current sidebar filters.**")
    
    # --- Back Button ---
    if st.button("↩️ Back to Analysis Pipeline"):
        st.session_state.show_custom_dashboard = False
        st.rerun()

    df = df_initial.copy() # Start with a clean copy of the final data

    # --- Sidebar Filters ---
    st.sidebar.markdown("### 🔎 Custom Filter Controls")
    
    # 3.2 Date Range Filter
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'].dt.date)
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        
        start_date, end_date = st.sidebar.date_input(
            "Select date range",
            [min_date, max_date],
            min_value=min_date, max_value=max_date,
            key='custom_date_range'
        )
        df = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]
    else:
        st.sidebar.warning("Cannot filter by Date: 'Date' column missing.")


    # 3.3 Category & Size Filters
    if 'Category' in df.columns and 'Size' in df.columns:
        cats = st.sidebar.multiselect(
            "Filter Categories",
            options=df['Category'].unique(),
            default=df['Category'].unique(),
            key='custom_cats'
        )
        sizes = st.sidebar.multiselect(
            "Filter Sizes",
            options=df['Size'].unique(),
            default=df['Size'].unique(),
            key='custom_sizes'
        )
        df = df[df['Category'].isin(cats) & df['Size'].isin(sizes)]
    
    # 3.4 Fulfilment & B2B Toggle
    if 'Fulfilment' in df.columns:
        fulfill_sel = st.sidebar.multiselect(
            "Fulfilment Method",
            options=df['Fulfilment'].unique(),
            default=df['Fulfilment'].unique(),
            key='custom_fulfill'
        )
        df = df[df['Fulfilment'].isin(fulfill_sel)]
    
    if 'B2B' in df.columns:
        b2b_only = st.sidebar.checkbox("Show only B2B orders", value=False, key='custom_b2b')
        if b2b_only:
            df = df[df['B2B'] == True]

    # 3.5 Top-N Controls
    top_n_state = st.sidebar.slider("Top N States", 5, 20, 10, key='custom_top_state')
    top_n_city  = st.sidebar.slider("Top N Cities", 5, 20, 10, key='custom_top_city')

    st.sidebar.markdown("---")
    st.sidebar.write(f"Filtered **{len(df):,}** orders")
    
    if df.empty:
        st.warning("No data found for the selected custom filters.")
        return

    # -------------------------------------------------------------------------
    # --- ANALYSIS SECTIONS (Including AI Buttons at each stage) ---
    # -------------------------------------------------------------------------

    # ─── 4) KPI Summary ─────────────────────────────────────────────────────────
    st.subheader("📈 Key Metrics (Filtered)")
    
    if 'Amount' in df.columns:
        total_sales  = df['Amount'].sum()
        total_orders = len(df)
        avg_order    = df['Amount'].mean()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Sales",       f"₹{total_sales:,.0f}")
        c2.metric("Total Orders",      f"{total_orders:,}")
        c3.metric("Avg. Order Value",  f"₹{avg_order:,.2f}")

        if st.button("🧠 Get AI Insights for Key Metrics (Custom Filters)", key="kpi_ai_custom"):
            with st.spinner("🤖 Generating insights..."):
                prompt = f"Analyze the following Key Performance Indicators (KPIs) filtered by the user's specific criteria: Total Sales: ₹{total_sales:,.0f}, Total Orders: {total_orders:,}, Average Order Value (AOV): ₹{avg_order:,.2f}. Provide 3 high-level, actionable insights."
                response = get_gemini_response_func(prompt)
                st.expander("🤖 AI Insights (Filtered Metrics)", expanded=True).markdown(response)

    st.markdown("---")

    # ─── 5) Sales Overview ─────────────────────────────────────────────────────
    if 'Date' in df.columns and 'Amount' in df.columns:
        st.subheader("1. Sales Overview")
        df['Month'] = df['Date'].dt.to_period('M').astype(str)
        monthly = df.groupby('Month')['Amount'].sum().reset_index()
        fig1 = px.line(monthly, x='Month', y='Amount', title="Monthly Sales Trend", markers=True)
        st.plotly_chart(fig1, use_container_width=True)
        
        if st.button("📈 Get AI Insights for Sales Trends (Custom Filters)", key="trends_ai_custom"):
            with st.spinner("🤖 Generating insights..."):
                data_sample = monthly.to_string(index=False, max_rows=24)
                prompt = f"Analyze the following monthly sales revenue data (filtered by user criteria) and provide 3 actionable insights on trends and seasonality.\n\nData (Month, Amount):\n{data_sample}"
                response = get_gemini_response_func(prompt)
                st.expander("🤖 AI Insights (Filtered Trends)", expanded=True).markdown(response)

    st.markdown("---")

    # ─── 6) Product Analysis ───────────────────────────────────────────────────
    if 'Category' in df.columns:
        st.subheader("2. Product Analysis")
        
        col_cat, col_size = st.columns(2)

        with col_cat:
            cat_df = df.groupby('Category')['Qty'].sum().nlargest(10).reset_index()
            fig2 = px.bar(cat_df, x='Category', y='Qty', title="Top 10 Categories by Quantity Sold")
            st.plotly_chart(fig2, use_container_width=True)
        
        with col_size:
            if 'Size' in df.columns:
                size_df = df['Size'].value_counts().nlargest(10).rename_axis('Size').reset_index(name='Count')
                fig3 = px.bar(size_df, x='Size', y='Count', title="Top 10 Sizes by Order Count")
                st.plotly_chart(fig3, use_container_width=True)

        if st.button("👕 Get AI Insights for Product Allocation (Custom Filters)", key="product_ai_custom"):
            with st.spinner("🤖 Generating insights..."):
                cat_sample = cat_df.to_string(index=False)
                size_sample = size_df.to_string(index=False) if 'Size' in df.columns else "N/A"
                prompt = f"Analyze the following filtered product data. Categories (Category, Qty):\n{cat_sample}\n\nSizes (Size, Count):\n{size_sample}. Provide 3 actionable insights for inventory and assortment planning."
                response = get_gemini_response_func(prompt)
                st.expander("🤖 AI Insights (Filtered Products)", expanded=True).markdown(response)

    st.markdown("---")
    
    # ─── 7) Fulfillment Analysis ────────────────────────────────────────────────
    if 'Fulfilment' in df.columns and 'Status' in df.columns:
        st.subheader("3. Fulfillment Analysis")
        
        col_pie, col_bar = st.columns(2)

        with col_pie:
            ful_df = df['Fulfilment'].value_counts().reset_index()
            ful_df.columns = ['Method', 'Count']
            fig4 = px.pie(ful_df, names='Method', values='Count', title="Fulfillment Method Split")
            st.plotly_chart(fig4, use_container_width=True)
        
        with col_bar:
            status_ful = df.groupby(['Fulfilment', 'Status']).size().reset_index(name='Count')
            fig4b = px.bar(
                status_ful, x='Fulfilment', y='Count', color='Status',
                barmode='group', title="Order Status by Fulfillment"
            )
            st.plotly_chart(fig4b, use_container_width=True)

        if st.button("📦 Get AI Insights for Fulfillment Logistics (Custom Filters)", key="fulfill_ai_custom"):
            with st.spinner("🤖 Generating insights..."):
                status_sample = status_ful.to_string(index=False, max_rows=20)
                prompt = f"Analyze the following filtered order status breakdown by fulfillment method. Provide 3 actionable insights to improve logistics efficiency.\n\nFulfillment Status Data:\n{status_sample}"
                response = get_gemini_response_func(prompt)
                st.expander("🤖 AI Insights (Filtered Logistics)", expanded=True).markdown(response)

    st.markdown("---")
    
    # ─── 8) Customer Segmentation ──────────────────────────────────────────────
    if 'B2B' in df.columns and 'Amount' in df.columns:
        st.subheader("4. Customer Segmentation")
        seg = df.groupby('B2B')['Amount'].sum().reset_index(name='TotalSales')
        seg['Type'] = seg['B2B'].map({True:'B2B', False:'B2C'})
        fig5 = px.bar(seg, x='Type', y='TotalSales', title="Total Sales: B2C vs B2B")
        st.plotly_chart(fig5, use_container_width=True)
        
        if st.button("👥 Get AI Insights for Customer Segments (Custom Filters)", key="segment_ai_custom"):
            with st.spinner("🤖 Generating insights..."):
                data_sample = seg.to_string(index=False)
                prompt = f"Analyze the following filtered sales breakdown between B2B and B2C customers. Provide 3 actionable insights on marketing strategies for each segment.\n\nData:\n{data_sample}"
                response = get_gemini_response_func(prompt)
                st.expander("🤖 AI Insights (Filtered Segments)", expanded=True).markdown(response)

    st.markdown("---")

    # ─── 9) Geographical Analysis ─────────────────────────────────────────────
    if 'ship-state' in df.columns and 'ship-city' in df.columns and 'Amount' in df.columns:
        st.subheader("5. Geographical Analysis")
        
        col_state, col_city = st.columns(2)

        with col_state:
            state_df = df.groupby('ship-state')['Amount'].sum().nlargest(top_n_state).reset_index()
            fig6 = px.bar(state_df, x='ship-state', y='Amount', title=f"Top {top_n_state} States by Sales")
            st.plotly_chart(fig6, use_container_width=True)
        
        with col_city:
            city_df = df['ship-city'].value_counts().nlargest(top_n_city).rename_axis('City').reset_index(name='Orders')
            fig7 = px.bar(city_df, x='City', y='Orders', title=f"Top {top_n_city} Cities by Orders")
            st.plotly_chart(fig7, use_container_width=True)
        
        if st.button("🗺️ Get AI Insights for Regional Markets (Custom Filters)", key="geo_ai_custom"):
            with st.spinner("🤖 Generating insights..."):
                state_sample = state_df.to_string(index=False)
                city_sample = city_df.to_string(index=False)
                prompt = f"Analyze the following sales data (States by Sales, Cities by Orders) filtered by user criteria. Provide 3 actionable insights for regional marketing and logistics.\n\nStates:\n{state_sample}\n\nCities:\n{city_sample}"
                response = get_gemini_response_func(prompt)
                st.expander("🤖 AI Insights (Filtered Geography)", expanded=True).markdown(response)

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # --- FINAL INSIGHTS (As requested to be at the bottom) ---
    # -------------------------------------------------------------------------

    st.header("🔑 Final Business Insights & KPIs (Summary of Filtered Data)")
    
    calculate_and_display_final_kpis_custom(df)
    st.markdown("---")
    generate_insights_report_custom(df, get_gemini_response_func)