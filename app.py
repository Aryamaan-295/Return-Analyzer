import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import calendar
from datetime import datetime
import io

# App setup
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    body { background-color: #111; color: #eee; }
    .stDataFrame thead tr th { font-size: 16px !important; color: #eee !important; background-color: #222 !important; }
    .stDataFrame tbody tr td { font-size: 14px; }
    section[data-testid="stSidebar"] { display: none; }
    button[aria-label="Toggle sidebar"], button[data-testid="collapsedControl"] { display: none !important; }
    main > div.block-container { padding-left: 1rem; padding-right: 1rem; }
    </style>
""", unsafe_allow_html=True)
st.title("Return Analyzer: Monthly, Weekday & Seasonality")

# ---------- Data Loading ----------
@st.cache_data
def load_default(path='uploaded_files/all_stocks.csv'):
    df = pd.read_csv(path, parse_dates=['date'])
    df.columns = df.columns.str.lower()
    df = df.dropna(subset=['stock'])
    df['stock'] = df['stock'].astype(str)
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(['stock','date'], inplace=True)
    df.set_index('date', inplace=True)
    return df

@st.cache_data
def load_custom(files):
    """Return list of (filename, dataframe) for each uploaded file."""
    dfs = []
    for file in files:
        raw = file.read()
        # detect CSV vs Excel
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(raw))
        else:
            df = pd.read_excel(io.BytesIO(raw))
        df.columns = df.columns.str.lower()
        if 'date' not in df.columns:
            st.error(f"❌ {file.name} must contain a 'date' column.")
            continue
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        df.sort_values('date', inplace=True)
        df.set_index('date', inplace=True)
        dfs.append((file.name, df))
    return dfs

# ---------- Computations (unchanged) ----------
@st.cache_data
def compute_monthly_returns(df, start_day, end_day):
    df2 = df.copy()
    df2['year'], df2['month'], df2['day'] = df2.index.year, df2.index.month, df2.index.day
    data = []
    for m in range(1, 13):
        returns = []
        monthly = df2[df2['month']==m]
        for yr in monthly['year'].unique():
            d = monthly[monthly['year']==yr]
            start, end = d[d['day']>=start_day], d[d['day']<=end_day]
            if not start.empty and not end.empty:
                r = (end['close'].iloc[-1] - start['close'].iloc[0]) / start['close'].iloc[0] * 100
                returns.append(r)
        if returns:
            avg = np.mean(returns)
            pos = sum(r>0 for r in returns)/len(returns)*100
            neg = sum(r<0 for r in returns)/len(returns)*100
            data.append((calendar.month_abbr[m], round(avg,2), round(pos,2), round(neg,2)))
    return pd.DataFrame(data, columns=['Month','Avg Return (%)','Positive Ratio (%)','Negative Ratio (%)'])

@st.cache_data
def compute_weekday_returns(df, start_period, end_period):
    start_dt = datetime(start_period.year, start_period.month, 1)
    last = calendar.monthrange(end_period.year, end_period.month)[1]
    end_dt = datetime(end_period.year, end_period.month, last)
    df2 = df.loc[start_dt:end_dt]
    if 'open' not in df2.columns or 'close' not in df2.columns:
        return None
    df2['return'] = (df2['close'] - df2['open']) / df2['open'] * 100
    df2['weekday'] = df2.index.day_name()
    data = []
    for wd in ['Monday','Tuesday','Wednesday','Thursday','Friday']:
        sub = df2[df2['weekday']==wd]['return']
        if not sub.empty:
            avg, pos, neg = sub.mean(), (sub>0).sum()/len(sub)*100, (sub<0).sum()/len(sub)*100
            data.append((wd, round(avg,2), round(pos,2), round(neg,2)))
    return pd.DataFrame(data, columns=['Weekday','Avg Return (%)','Positive Ratio (%)','Negative Ratio (%)'])

@st.cache_data
def compute_seasonality_heatmap(df):
    df2 = df.copy()
    df2['year'], df2['month'] = df2.index.year, df2.index.month
    grp = df2.groupby(['year','month'])['close']
    ret = ((grp.last() - grp.first()) / grp.first() * 100).reset_index(name='return')
    pivot = ret.pivot(index='year', columns='month', values='return')
    pivot.columns = [calendar.month_abbr[m] for m in pivot.columns]
    pivot = pivot.reindex(columns=calendar.month_abbr[1:], fill_value=np.nan).round(2)
    pos = (pivot > 0).sum() / pivot.notna().sum() * 100
    neg = (pivot < 0).sum() / pivot.notna().sum() * 100
    return pivot, pos.round(2), neg.round(2)

# ---------- Main ----------
# Allow multiple files
uploaded_files = st.file_uploader("Upload CSV or Excel files", type=['csv','xlsx'], accept_multiple_files=True)

# Load data
default_df = load_default()
custom_dfs = load_custom(uploaded_files) if uploaded_files else []

# Build dropdown options
default_stocks = sorted(default_df['stock'].unique())
options = default_stocks.copy()
for fname, _ in custom_dfs:
    options.append(f"User File: {fname}")

selected = st.selectbox("Select Stock Dataset", options)

# Pick the dataframe to analyze
if selected.startswith("User File:"):
    # extract filename
    fname = selected.replace("User File: ", "")
    df = next((df for name, df in custom_dfs if name == fname), None)
    if df is None:
        st.error("⚠️ Could not find the selected file.")
        st.stop()
else:
    # default stock selection
    df = default_df[default_df['stock'] == selected].drop(columns=['stock'])

# Preview
st.subheader("Raw Data Preview")
st.dataframe(df.head())

# Build timeline labels if df not empty
if not df.empty:
    d0, d1 = df.index.min(), df.index.max()
    periods = pd.date_range(d0.replace(day=1), d1.replace(day=1), freq='MS')
    labels = [d.strftime('%m/%Y') for d in periods]

    tab1, tab2, tab3 = st.tabs(["Monthly Window","Weekday Intraday","Seasonality Heatmap"])

    with tab1:
        st.markdown("### Monthly Buy & Hold Window")
        c1, c2, _, _ = st.columns(4)
        sd = c1.number_input("Start Day", 1, 28, 2, key='sd_mon')
        ed = c2.number_input("End Day", 1, 31, 13, key='ed_mon')
        st.markdown("<small style='color:#aaa;'>Includes both start & end days.</small>", unsafe_allow_html=True)
        if sd < ed:
            df_mon = compute_monthly_returns(df, sd, ed)
            cA, cB = st.columns(2)
            with cA:
                def style_mon(v, c): return 'color:' + ('green' if 'Positive' in c else 'red') if 'Ratio' in c else ''
                styled = df_mon.style.apply(lambda r: [style_mon(v, c) for v, c in zip(r.values, df_mon.columns)], axis=1)
                st.dataframe(styled, use_container_width=True)
            with cB:
                colors = ['green' if v > 0 else 'red' for v in df_mon['Avg Return (%)']]
                fig = go.Figure(go.Bar(x=df_mon['Month'], y=df_mon['Avg Return (%)'], marker_color=colors))
                fig.update_layout(plot_bgcolor='#111', paper_bgcolor='#111', font_color='#eee', height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Start day must precede end day.")

    with tab2:
        st.markdown("### Average Intraday Return by Weekday")
        c1, c2, _, _ = st.columns(4)
        sp_label = c1.selectbox("Start Period", labels, 0, key='sp_wd')
        ep_label = c2.selectbox("End Period", labels, len(labels)-1, key='ep_wd')
        st.markdown("<small style='color:#aaa;'>Includes both start & end months.</small>", unsafe_allow_html=True)
        sp = periods[labels.index(sp_label)]
        ep = periods[labels.index(ep_label)]
        if sp <= ep:
            df_wd = compute_weekday_returns(df, sp, ep)
            if df_wd is None:
                st.error("Needs 'open' & 'close' columns in data.")
            else:
                cA, cB = st.columns(2)
                with cA:
                    def style_wd(v, c): return 'color:' + ('green' if 'Positive' in c else 'red') if 'Ratio' in c else ''
                    styled = df_wd.style.apply(lambda r: [style_wd(v, c) for v, c in zip(r.values, df_wd.columns)], axis=1)
                    st.dataframe(styled, use_container_width=True)
                with cB:
                    colors = ['green' if v > 0 else 'red' for v in df_wd['Avg Return (%)']]
                    fig = go.Figure(go.Bar(x=df_wd['Weekday'], y=df_wd['Avg Return (%)'], marker_color=colors))
                    fig.update_layout(plot_bgcolor='#111', paper_bgcolor='#111', font_color='#eee', height=400)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Start period must precede end period.")

    with tab3:
        st.markdown("### Seasonality Heatmap")
        heat, pr, nr = compute_seasonality_heatmap(df)
        # heatmap
        def style_cell(v):
            if pd.isna(v): return ''
            if v >= 5: return 'background-color:#004d00;color:#fff'
            if v > 0:  return 'background-color:#007700;color:#fff'
            if v == 0: return 'background-color:#000;color:#fff'
            if v > -5: return 'background-color:#550000;color:#fff'
            return 'background-color:#330000;color:#fff'
        styled_heat = heat.style.map(style_cell)
        st.dataframe(styled_heat, use_container_width=True, height=400)

        # positive/negative ratios
        r_df = pd.DataFrame({'Positive Ratio (%)': pr, 'Negative Ratio (%)': nr}).T
        r_df.columns = heat.columns
        r_df = r_df.round(2).astype(str).add('%')
        def style_r(v, row): return 'background-color:#000;color:' + ('green' if 'Positive' in row else 'red')
        styled_r = r_df.style.apply(lambda r: [style_r(v, r.name) for v in r], axis=1)
        st.dataframe(styled_r, use_container_width=True)

else:
    st.info("No data available to analyze. Please upload at least one file.")
