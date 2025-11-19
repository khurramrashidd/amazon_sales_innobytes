import pandas as pd
import streamlit as st
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

# --- Snapshot Management ---
def make_snapshot(df: pd.DataFrame, step: int):
    """Saves a copy of the current DataFrame state."""
    st.session_state.snapshots[step] = df.copy()
    
# --- Table Viewer (FIXED FOR DUPLICATE KEY ERROR) ---
def paginated_table_viewer(df: pd.DataFrame, max_rows=50, key_context=""):
    """
    Displays a DataFrame with truncation. 
    Uses a button/modal-like structure for the full view to prevent nested expander errors.
    The key_context ensures the button key is unique for this specific table instance.
    """
    
    if df.empty:
        st.warning("DataFrame is empty.")
        return
    
    if len(df) > max_rows:
        # Always show truncated view first
        st.dataframe(df.head(max_rows), use_container_width=True)
        
        # Use key_context to generate a truly unique key for the button
        key = f"full_table_view_{key_context}"
        if st.button(f"Show Full Table ({len(df):,} rows)", key=key):
            # Display full table content in a different layout element to avoid nesting
            with st.container(border=True):
                st.markdown(f"**Full Table View:**")
                st.dataframe(df, use_container_width=True)
    else:
        # Display full table if small
        st.dataframe(df, use_container_width=True)
        
# --- Data Info ---
def show_df_info(df: pd.DataFrame):
    """Shows raw data info (dtypes and head)."""
    st.markdown(f"**Shape:** {df.shape[0]:,} Rows, {df.shape[1]} Columns")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Data Types (`df.dtypes`)**")
        st.code(df.dtypes.to_string())
    with col2:
        st.markdown("**Sample Data (`df.head()`)**")
        st.dataframe(df.head())

# --- PDF Export (Step X) ---
def export_summary_report(df: pd.DataFrame, step_num: int):
    """Generates a simple PDF summary report for download."""
    
    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    styles = getSampleStyleSheet()
    
    # Title
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, f"Analysis Snapshot Report - Step {step_num}")
    
    # Key Metrics
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 80, "Key Snapshot Data:")
    c.setFont("Helvetica", 9)
    
    total_sales = df['Amount'].sum() if 'Amount' in df.columns else 0
    total_orders = df['Order ID'].nunique() if 'Order ID' in df.columns else 0
    
    text_objects = [
        f"Total Records: {len(df):,}",
        f"Total Sales: ₹{total_sales:,.2f}",
        f"Total Orders: {total_orders:,}",
        f"Current Step Completed: {step_num}",
    ]
    
    y_pos = height - 100
    for text in text_objects:
        c.drawString(70, y_pos, text)
        y_pos -= 12
        
    # Conclusion Note
    note_style = ParagraphStyle('Note', parent=styles['Normal'], fontSize=9, leading=12)
    note_text = f"This report represents the data state after completing Step {step_num} of the pipeline. Use this summary to track transformations and key performance indicators."
    p = Paragraph(note_text, note_style)
    p.wrapOn(c, width - 100, height)
    p.drawOn(c, 50, y_pos - 20)

    c.save()
    
    st.download_button(
        label=f"🔽 Download Summary Report (PDF) - Step {step_num}",
        data=buffer.getvalue(),
        file_name=f"analysis_summary_step_{step_num}.pdf",
        mime="application/pdf",
        key=f"download_pdf_{step_num}"
    )