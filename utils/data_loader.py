import streamlit as st
import pandas as pd
import io

@st.cache_data
def load_default(path='uploaded_files/all_stocks.csv'):
    df = pd.read_csv(path, parse_dates=['date'])
    df.columns = df.columns.str.lower()
    df.dropna(subset=['stock'], inplace=True)
    df['stock'] = df['stock'].astype(str)
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(['stock','date'], inplace=True)
    df.set_index('date', inplace=True)
    return df

@st.cache_data
def load_custom(files):
    dfs = []
    for file in files:
        raw = file.read()
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(raw))
        else:
            df = pd.read_excel(io.BytesIO(raw))
        df.columns = df.columns.str.lower()
        if 'date' not in df.columns:
            st.error(f"❌ {file.name} must contain a 'date' column.")
            continue
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df.dropna(subset=['date'], inplace=True)
        df.sort_values('date', inplace=True)
        df.set_index('date', inplace=True)
        dfs.append((file.name, df))
    return dfs
