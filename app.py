import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import calendar
from datetime import datetime

# App setup
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    body { background-color: #111; color: #eee; }
    .stDataFrame thead tr th { font-size: 16px !important; color: #eee !important; background-color: #222 !important; }
    .stDataFrame tbody tr td { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

st.title("Return Analyzer: Monthly, Weekday & Seasonality")

# ---------- Caching Logic ----------
@st.cache_data
def load_data(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file, parse_dates=["Date"])
    else:
        df = pd.read_excel(file, parse_dates=["Date"])
    df.sort_values("Date", inplace=True)
    df.set_index("Date", inplace=True)
    return df

@st.cache_data
def compute_monthly_returns(df, start_day, end_day):
    df2 = df.copy()
    df2['Year'] = df2.index.year; df2['Month'] = df2.index.month; df2['Day'] = df2.index.day
    month_names = calendar.month_abbr[1:]
    results = {}
    for i, m in enumerate(range(1, 13)):
        vals = []
        md = df2[df2['Month'] == m]
        for y in md['Year'].unique():
            d = md[md['Year'] == y].sort_index()
            sr = d[d['Day'] >= start_day]; er = d[d['Day'] <= end_day]
            if not sr.empty and not er.empty:
                p0 = sr['Close'].iloc[0]
                p1 = er['Close'].iloc[-1]
                vals.append((p1 - p0) / p0 * 100)
        if vals:
            results[month_names[i]] = np.mean(vals)
    return pd.DataFrame({'Month': list(results.keys()), 'Avg Return (%)': [round(v, 2) for v in results.values()]})

@st.cache_data
def compute_weekday_returns(df, sp, ep):
    start_dt = datetime(sp.year, sp.month, 1)
    last = calendar.monthrange(ep.year, ep.month)[1]
    end_dt = datetime(ep.year, ep.month, last)
    df2 = df.loc[start_dt:end_dt].copy()
    if 'Open' not in df2.columns:
        return None
    df2['Return'] = (df2['Close'] - df2['Open']) / df2['Open'] * 100
    df2['Weekday'] = df2.index.day_name()
    means = df2.groupby('Weekday')['Return'].mean().reindex(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    ).dropna()
    return means.reset_index().rename(columns={'Return': 'Avg Return (%)'})

@st.cache_data
def compute_seasonality_heatmap(df):
    df2 = df.copy()
    df2['Year'] = df2.index.year
    df2['Month'] = df2.index.month
    monthly = df2.groupby(['Year', 'Month']).agg(
        first_close=('Close', lambda x: x.iloc[0]),
        last_close=('Close', lambda x: x.iloc[-1])
    ).reset_index()
    # Correctly reference columns to compute returns
    monthly['Return'] = (monthly['last_close'] - monthly['first_close']) / monthly['first_close'] * 100
    pivot = monthly.pivot(index='Month', columns='Year', values='Return').reindex(range(1, 13))
    pivot.index = calendar.month_abbr[1:]
    return pivot.round(2)

# ---------- Main ----------
uploaded = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
if uploaded:
    df = load_data(uploaded)
    if 'Close' not in df.columns:
        st.error("Uploaded file must contain 'Close' column.")
    else:
        st.subheader("Raw Data Preview")
        st.dataframe(df.head())

        # prepare period labels
        dmin = df.index.min().replace(day=1)
        dmax = df.index.max().replace(day=1)
        periods = pd.date_range(dmin, dmax, freq='MS')
        labels = [d.strftime('%m/%Y') for d in periods]

        tab1, tab2, tab3 = st.tabs(["Monthly Window", "Weekday Intraday", "Seasonality Heatmap"])

        with tab1:
            st.markdown("### Monthly Buy & Hold Window")
            c1, c2, _, _ = st.columns(4)
            with c1:
                sd = st.number_input("Start Day", min_value=1, max_value=28, value=2)
            with c2:
                ed = st.number_input("End Day", min_value=1, max_value=31, value=13)
            st.markdown("<small style='color:#aaa;'>Includes both the start and end days.</small>", unsafe_allow_html=True)
            if sd < ed:
                summary = compute_monthly_returns(df, sd, ed)
                cA, cB = st.columns(2)
                with cA:
                    st.dataframe(summary, use_container_width=True, height=400)
                with cB:
                    colors = ['green' if v > 0 else 'red' for v in summary['Avg Return (%)']]
                    fig = go.Figure(go.Bar(
                        x=summary['Month'], y=summary['Avg Return (%)'], marker_color=colors,
                        hovertemplate="<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>"
                    ))
                    fig.update_layout(
                        plot_bgcolor='#111', paper_bgcolor='#111', font_color='#eee', height=400,
                        dragmode=False, hoverlabel=dict(font_size=16)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
            else:
                st.warning("Start day must be before end day.")

        with tab2:
            st.markdown("### Average Intraday Return by Weekday")
            c1, c2, _, _ = st.columns(4)
            with c1:
                sl = st.selectbox("Start Period", options=labels, index=0, key='sp')
            with c2:
                el = st.selectbox("End Period", options=labels, index=len(labels)-1, key='ep')
            st.markdown("<small style='color:#aaa;'>Includes both the start and end months.</small>", unsafe_allow_html=True)
            sp = periods[labels.index(sl)]
            ep = periods[labels.index(el)]
            if sp <= ep:
                res = compute_weekday_returns(df, sp, ep)
                if res is None:
                    st.error("Needs an 'Open' column.")
                else:
                    cA, cB = st.columns(2)
                    with cA:
                        st.dataframe(res, use_container_width=True)
                    with cB:
                        colors = ['green' if v > 0 else 'red' for v in res['Avg Return (%)']]
                        fig2 = go.Figure(go.Bar(
                            x=res['Weekday'], y=res['Avg Return (%)'], marker_color=colors,
                            hovertemplate="<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>"
                        ))
                        fig2.update_layout(
                            plot_bgcolor='#111', paper_bgcolor='#111', font_color='#eee', height=400,
                            dragmode=False, hoverlabel=dict(font_size=16)
                        )
                        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
            else:
                st.error("Start period must be before end period.")

        with tab3:
            st.markdown("### Seasonality Heatmap (Monthly Returns)")
            heat_df = compute_seasonality_heatmap(df)
            # Discrete dark color map for 5 categories
            def style_cell(val):
                if pd.isna(val):
                    return ''
                # thresholds in %
                if val >= 5:
                    # high positive
                    return 'background-color: #004d00; color: #fff'
                elif val > 0:
                    # low positive
                    return 'background-color: #007700; color: #fff'
                elif val == 0:
                    # neutral
                    return 'background-color: #000; color: #fff'
                elif val > -5:
                    # low negative
                    return 'background-color: #550000; color: #fff'
                else:
                    # high negative
                    return 'background-color: #330000; color: #fff'
            styled = heat_df.style.applymap(style_cell)
            st.dataframe(styled, use_container_width=True)
