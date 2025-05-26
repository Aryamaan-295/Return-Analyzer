import streamlit as st
import difflib
import pandas as pd
import datetime
import calendar

# Utility: compute returns over calendar window ignoring year, using nearest trading days
def compute_period_returns(df, start_md, end_md, date_col, price_col):
    """
    Compute per-year returns from first trading >= start_md to last trading <= end_md.
    start_md, end_md are (month, day) tuples.
    """
    # parse dates and prices
    dates = pd.to_datetime(df[date_col], errors='coerce')
    prices = df[price_col]
    temp = pd.DataFrame({'date': dates, 'price': prices}).dropna()
    temp['year'] = temp['date'].dt.year
    temp['month'] = temp['date'].dt.month
    temp['day'] = temp['date'].dt.day
    records = []
    for yr, grp in temp.groupby('year'):
        grp = grp.sort_values('date')
        start_mask = (grp['month'] > start_md[0]) | ((grp['month'] == start_md[0]) & (grp['day'] >= start_md[1]))
        end_mask = (grp['month'] < end_md[0]) | ((grp['month'] == end_md[0]) & (grp['day'] <= end_md[1]))
        grp_start = grp.loc[start_mask]
        grp_end = grp.loc[end_mask]
        if not grp_start.empty and not grp_end.empty:
            p0 = grp_start.iloc[0]['price']
            p1 = grp_end.iloc[-1]['price']
            records.append({'year': int(yr), 'return': (p1 / p0 - 1) * 100})
    return pd.DataFrame(records)


def stock_screener_tab(default_df, custom_dfs):
    """Stock Screener with calendar-style inputs for DD/MM windows."""
    st.markdown("### Stock Screener: Calendar Window (Select Dates)")

    # Detect date and price columns
    df0 = default_df.copy()
    if isinstance(df0.index, pd.DatetimeIndex):
        df0 = df0.reset_index()
    cols = {c.lower(): c for c in df0.columns}
    date_col = next((v for k, v in cols.items() if 'date' in k), None)
    price_col = next((cols[k] for k in ['close', 'adj_close', 'adjusted_close', 'price'] if k in cols), None)
    if not date_col or not price_col:
        st.error("DataFrame missing a date or price column.")
        return

    # Inputs on one line: search, start month/day, end month/day
    c1, c2, c3, c4, c5 = st.columns(5)
    search = c1.text_input("Search Ticker", key='scr_search')
    # Start Date: month and day selectboxes
    start_month = c2.selectbox("Start Month", list(calendar.month_abbr)[1:], key='scr_start_month')
    start_day = c3.selectbox("Start Day", list(range(1, calendar.monthrange(2000, list(calendar.month_abbr).index(start_month))[1] + 1)), key='scr_start_day')
    # End Date: month and day selectboxes
    end_month = c4.selectbox("End Month", list(calendar.month_abbr)[1:], key='scr_end_month')
    end_day = c5.selectbox("End Day", list(range(1, calendar.monthrange(2000, list(calendar.month_abbr).index(end_month))[1] + 1)), key='scr_end_day')

    # Build month-day tuples
    sd_md = (list(calendar.month_abbr).index(start_month), start_day)
    ed_md = (list(calendar.month_abbr).index(end_month), end_day)
    if sd_md > ed_md:
        st.warning("Start date must be on or before end date.")

    # Once inputs valid, compute
    if sd_md <= ed_md:
        results = []
        # Default universe
        for stk in sorted(default_df['stock'].unique()):
            df_stk = default_df[default_df['stock'] == stk].copy()
            if isinstance(df_stk.index, pd.DatetimeIndex):
                df_stk = df_stk.reset_index()
            pr = compute_period_returns(df_stk, sd_md, ed_md, date_col, price_col)
            if not pr.empty:
                avg = pr['return'].mean()
                pos = (pr['return'] > 0).mean() * 100
                neg = (pr['return'] < 0).mean() * 100
                results.append((stk, avg, pos, neg))
        # Custom files
        for name, df in custom_dfs:
            dfc = df.copy()
            if isinstance(dfc.index, pd.DatetimeIndex):
                dfc = dfc.reset_index()
            cols2 = {c.lower(): c for c in dfc.columns}
            date2 = next((v for k, v in cols2.items() if 'date' in k), None)
            price2 = next((cols2[k] for k in ['close', 'adj_close', 'adjusted_close', 'price'] if k in cols2), None)
            if date2 and price2:
                pr = compute_period_returns(dfc, sd_md, ed_md, date2, price2)
                if not pr.empty:
                    avg = pr['return'].mean()
                    pos = (pr['return'] > 0).mean() * 100
                    neg = (pr['return'] < 0).mean() * 100
                    results.append((f"User File: {name}", avg, pos, neg))

        if results:
            scr_df = pd.DataFrame(results, columns=['Ticker', 'Avg Return (%)', 'Positive Ratio (%)', 'Negative Ratio (%)'])
            scr_df = scr_df.sort_values('Avg Return (%)', ascending=False).reset_index(drop=True)
            scr_df.insert(0, 'Sr.No', scr_df.index + 1)

            # Highlight search match
            best = None
            if search:
                cmap = {t.lower(): t for t in scr_df['Ticker']}
                match = difflib.get_close_matches(search.lower(), cmap.keys(), n=1, cutoff=0.6)
                if match:
                    best = cmap[match[0]]

            def color_ratios(val, col):
                if col == 'Positive Ratio (%)': return 'color: green'
                if col == 'Negative Ratio (%)': return 'color: red'
                return ''

            styled = scr_df.style.apply(lambda col: [color_ratios(v, col.name) for v in col], axis=0)
            if best:
                display_df = scr_df
            else:
                display_df = scr_df

            styled = display_df.style.apply(
                lambda row: ['background-color: rgba(255,255,0,0.2)' if row['Ticker'] == best else '' for _ in row],
                axis=1
            ).set_table_styles([
                {'selector': 'th.row_heading, td.row_heading', 'props': [('display', 'none')]}]
            )

            st.dataframe(styled, use_container_width=True)
        else:
            st.info("No data available for the selected window.")
