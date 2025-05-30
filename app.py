import streamlit as st
import pandas as pd
from utils.data_loader import load_default, load_custom
from utils.computations import (
    compute_monthly_returns,
    compute_weekday_returns,
    compute_seasonality_heatmap,
    compute_correlation
)
from tabs.screener_tab import stock_screener_tab
from tabs.monthly_tab import monthly_window_tab
from tabs.weekday_tab import weekday_intraday_tab
from tabs.seasonality_tab import seasonality_tab
from tabs.correlation_tab import correlation_tab

# App setup
st.set_page_config(layout="wide")

st.title("Return Analyzer: Monthly, Weekday & Seasonality")

uploaded_files = st.file_uploader("Upload CSV or Excel files", type=['csv','xlsx'], accept_multiple_files=True)

def load_data():
    default_df = load_default()
    custom_dfs = load_custom(uploaded_files) if uploaded_files else []
    return default_df, custom_dfs


def main():
    default_df, custom_dfs = load_data()
    d0, d1 = default_df.index.min(), default_df.index.max()
    periods = pd.date_range(d0.replace(day=1), d1.replace(day=1), freq='MS')
    labels = [d.strftime('%m/%Y') for d in periods]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Screener",
        "Monthly Window",
        "Weekday Intraday",
        "Seasonality Heatmap",
        "Correlation"
    ])

    with tab1:
        stock_screener_tab(default_df, custom_dfs)
    with tab2:
        monthly_window_tab(default_df, custom_dfs)
    with tab3:
        weekday_intraday_tab(default_df, custom_dfs, labels, periods)
    with tab4:
        seasonality_tab(default_df, custom_dfs)
    with tab5:
        correlation_tab(default_df)

if __name__ == '__main__':
    main()
