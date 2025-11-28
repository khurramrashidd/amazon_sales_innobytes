import pandas as pd
import streamlit as st
import numpy as np

# --- 1. Load Data ---

@st.cache_data(show_spinner="Loading data from source...")
def load_raw_data(data_file) -> pd.DataFrame:
    """Loads raw data from file uploader or default path."""
    path = "Amazon Sale Report.csv" # Default path
    
    if data_file:
        try:
            df = pd.read_csv(data_file, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(data_file, encoding='latin1')
    else:
        try:
            df = pd.read_csv(path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding='latin1')
        except FileNotFoundError:
            st.error(f"Default file '{path}' not found. Please upload a file.")
            return pd.DataFrame() 

    return df

# --- 2. Inspection & Missing Values (Step 1) ---

def inspect_missing_values(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Inspects and summarizes missing values across the DataFrame."""
    
    # Calculate missing values
    missing_counts = df.isnull().sum()
    missing_percentage = (df.isnull().sum() / len(df)) * 100
    
    missing_summary = pd.DataFrame({
        'Missing Count': missing_counts,
        'Missing Percentage': missing_percentage.round(2)
    }).reset_index().rename(columns={'index': 'Column'})
    
    missing_summary = missing_summary[missing_summary['Missing Count'] > 0].sort_values(
        'Missing Count', ascending=False
    ).reset_index(drop=True)

    # Sample rows with missing data (for demonstration)
    missing_mask = df.isnull().any(axis=1)
    sample_missing_rows = df[missing_mask].head(100).copy()

    note = f"Found **{len(missing_summary)}** columns with missing data across **{missing_mask.sum():,}** total rows. The following summary shows the count and percentage of NaN values per column."
    
    return df, {"missing_summary": missing_summary, "sample_missing_rows": sample_missing_rows, "note": note}

# --- 3. Column Dropping (Step 2) ---

def drop_missing_columns(df: pd.DataFrame, threshold: int) -> tuple[pd.DataFrame, dict]:
    """Drops columns where the percentage of missing values exceeds the threshold."""
    
    rows_before = len(df)
    missing_percentage = (df.isnull().sum() / len(df)) * 100
    
    cols_to_drop = missing_percentage[missing_percentage > threshold].index.tolist()
    
    # Create summary before dropping
    dropped_summary = pd.DataFrame({
        'Column': cols_to_drop,
        'Missing %': missing_percentage[cols_to_drop].round(2)
    })

    df_new = df.drop(columns=cols_to_drop, errors='ignore').copy()
    rows_after = len(df_new)
    
    note = f"Columns with > **{threshold}%** missing values were dropped. **{len(cols_to_drop)}** columns removed."
    if not cols_to_drop:
        note = f"No columns exceeded the **{threshold}%** missing threshold."
        
    return df_new, {
        "dropped_summary": dropped_summary, 
        "note": note,
        "rows_before": rows_before,
        "rows_after": rows_after
    }

# --- 4. Date Conversion & Feature Engineering (Step 3) ---

def convert_date_and_derive(df: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, dict]:
    """Converts the Date column and derives time-based features."""

    df_new = df.copy()
    
    # 1. Rename columns based on mapping for standardization
    reverse_map = {v: k for k, v in mapping.items()}
    df_new.rename(columns=reverse_map, inplace=True)

    if 'Date' in df_new.columns:
        # 2. Drop specific columns from original dataset that are unused/messy
        df_new = df_new.drop(columns=['New', 'PendingS'], errors='ignore')
        
        # 3. Drop rows with missing Amount data
        if 'Amount' in df_new.columns:
            df_new = df_new.dropna(subset=['Amount'])
        
        # 4. Convert 'Date' column to datetime objects
        df_new['Date'] = pd.to_datetime(df_new['Date'], format='%m-%d-%y', errors='coerce')
        df_new = df_new.dropna(subset=['Date']) # Drop rows where date conversion failed

        # 5. Convert B2B column to boolean
        if 'B2B' in df_new.columns:
            df_new['B2B'] = df_new['B2B'].map({True: True, False: False, 'Yes': True, 'No': False})
            
        # 6. Derive columns
        df_new['Month'] = df_new['Date'].dt.to_period('M').astype(str)
        df_new['Year'] = df_new['Date'].dt.year
        df_new['DayOfWeek'] = df_new['Date'].dt.day_name()
        
        note = "The 'Date' column was converted to datetime objects. Derived columns ('Month', 'Year', 'DayOfWeek') added for trend analysis. Critical rows (missing Date/Amount) were dropped."
    else:
        note = "Date conversion skipped: 'Date' column not found in DataFrame after mapping."

    return df_new, {"note": note}
