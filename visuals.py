import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --- Helper for plotting missing values (Step 1) ---
def plot_missing_values(missing_summary: pd.DataFrame):
    """Generates a bar chart of missing value percentages."""
    if missing_summary.empty:
        st.success("No missing values found!")
        return
        
    fig = px.bar(
        missing_summary,
        x='Column',
        y='Missing Percentage',
        title='Percentage of Missing Values per Column',
        color='Missing Percentage',
        color_continuous_scale=px.colors.sequential.Reds,
        labels={'Missing Percentage': 'Missing %', 'Column': 'Column Name'}
    )
    fig.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig, use_container_width=True)

# --- Sales Trend (Step 4) ---
@st.cache_data
def plot_monthly_sales_trend(df: pd.DataFrame):
    """Plots the monthly sales revenue trend."""
    if 'Month' not in df.columns or 'Amount' not in df.columns:
        return go.Figure().update_layout(title="Monthly Sales Trend (Data/Amount columns missing)")
        
    # Aggregate data
    monthly = df.groupby('Month')['Amount'].sum().reset_index()
    
    # Ensure correct plotting order by period
    monthly['Period'] = pd.to_datetime(monthly['Month'])
    monthly = monthly.sort_values('Period')
    
    fig = px.line(
        monthly, 
        x='Month', 
        y='Amount', 
        title="Monthly Sales Revenue Trend", 
        markers=True,
        labels={'Amount': 'Total Sales Amount', 'Month': 'Month/Year'},
        template='plotly_white'
    )
    fig.update_traces(line_color='#008080')
    return fig

# --- Product Analysis (Step 5) ---
@st.cache_data
def plot_top_categories(df: pd.DataFrame, col='Category', title='Top 10 Categories by Orders'):
    """Plots the distribution of top categories or sizes."""
    if col not in df.columns:
        return go.Figure().update_layout(title=f"{title} ({col} column missing)")
        
    counts = df[col].value_counts().nlargest(10).reset_index()
    counts.columns = [col, 'Count']
    
    fig = px.bar(
        counts, 
        x='Count', 
        y=col, 
        orientation='h',
        title=title,
        color='Count',
        color_continuous_scale=px.colors.sequential.Teal,
        labels={'Count': 'Order Count', col: col},
        template='plotly_white'
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    return fig

# --- Fulfillment Analysis (Step 6) ---
@st.cache_data
def plot_fulfillment_status(df: pd.DataFrame):
    """Plots Order Status by Fulfillment Method (Stacked Bar)."""
    if 'Fulfilment' not in df.columns or 'Status' not in df.columns:
        return go.Figure().update_layout(title="Fulfillment Status (Fulfilment/Status columns missing)")
        
    status_ful = df.groupby(['Fulfilment', 'Status']).size().reset_index(name='Count')
    
    fig = px.bar(
        status_ful, 
        x='Fulfilment', 
        y='Count', 
        color='Status',
        title="Order Status Breakdown by Fulfillment Method",
        labels={'Count': 'Order Count', 'Fulfilment': 'Fulfillment Method'},
        template='plotly_white'
    )
    return fig