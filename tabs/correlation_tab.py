import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Wrap tabs in your main app to preserve state across reruns:
# if 'active_tab' not in st.session_state:
#     st.session_state.active_tab = 0
# tabs = st.tabs(["Correlation","Other Tab"], key="main_tabs")
# with tabs[st.session_state.active_tab]:
#     if st.session_state.active_tab == 0:
#         correlation_tab(df)
#     else:
#         other_tab(df)

def correlation_tab(default_df):
    """Render the Correlation and Returns comparison tab with interactive features."""
    # Copy and strip column names
    df = default_df.copy()
    df.columns = df.columns.str.strip()

    # Lowercase mapping
    cols_lower = {col.lower(): col for col in df.columns}

    # Identify ticker, date, and price columns
    ticker_col = cols_lower.get('stock') or cols_lower.get('symbol')
    date_col = cols_lower.get('date')
    if date_col is None and isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        date_col = df.columns[0]
    price_col = next((cols_lower[opt] for opt in ['close', 'adj_close', 'adjusted_close', 'close_price', 'price'] if opt in cols_lower), None)

    # Validate
    if not (ticker_col and date_col and price_col):
        missing = []
        if not ticker_col: missing.append("'stock' or 'symbol'")
        if not date_col: missing.append("'date' or DatetimeIndex'")
        if not price_col: missing.append("price-like column")
        st.error(f"Missing required column(s): {', '.join(missing)}.")
        return

    # Ensure date dtype
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])

    # Prepare tickers list
    tickers = sorted(df[ticker_col].unique())

    # Compute returns
    df = df.sort_values([ticker_col, date_col])
    df['return'] = df.groupby(ticker_col)[price_col].pct_change()

    # Pivot returns matrix
    returns = df.pivot(index=date_col, columns=ticker_col, values='return')
    returns = returns.reindex(columns=tickers)

    # Compute correlation in percent
    corr = returns.corr() * 100
    corr = corr.reindex(index=tickers, columns=tickers)

    # Heatmap setup
    st.markdown("### Correlation Heatmap: Default Stocks")
    heatmap = go.Heatmap(
        z=corr.values,
        x=tickers,
        y=tickers,
        colorscale='RdBu_r',
        zmid=0,
        zmin=-100,
        zmax=100,
        hovertemplate="%{x} vs %{y}: %{z:.1f}%<extra></extra>",
        colorbar=dict(lenmode='fraction', len=0.75, y=0.5, yanchor='middle')
    )
    fig = go.Figure(data=heatmap)
    fig.update_layout(
        xaxis=dict(tickangle=-45, tickfont=dict(size=12), constrain='domain'),
        yaxis=dict(autorange='reversed', tickfont=dict(size=12), scaleanchor='x'),
        margin=dict(l=0, r=0, t=10, b=10),
        width=1600, height=1600,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='var(--fg)'
    )
    st.plotly_chart(fig, use_container_width=False, config={'displayModeBar': False})
    st.caption("*Correlation values are percentage points from -100% to 100%.*")
    st.markdown("---")

    # Top correlated pairs
    pairs = [(s1, s2, corr.loc[s1, s2]) for i, s1 in enumerate(tickers) for j, s2 in enumerate(tickers) if j > i]
    top10 = sorted(pairs, key=lambda x: x[2], reverse=True)[:10]

    st.markdown("### Top 10 Correlated Pairs")
    # Table header including Sr.No and Action
    header_cols = st.columns([1,2,2,1,1])
    header_cols[0].markdown("**Sr.No**")
    header_cols[1].markdown("**Stock 1**")
    header_cols[2].markdown("**Stock 2**")
    header_cols[3].markdown("**Corr %**")
    header_cols[4].markdown("**Action**")

    # Function to select pair
    def select_pair(s1, s2):
        st.session_state['selection'] = [s1, s2]
        st.session_state['_show_chart'] = True

    # Table rows with Plot button in Action column
    for idx, (s1, s2, val) in enumerate(top10, start=1):
        row_cols = st.columns([1,2,2,1,1])
        row_cols[0].write(idx)
        row_cols[1].write(s1)
        row_cols[2].write(s2)
        row_cols[3].write(f"{val:.1f}%")
        row_cols[4].button("Plot", key=f"btn_{s1}_{s2}", on_click=select_pair, args=(s1, s2))

    # Returns comparison
    if st.session_state.get('_show_chart', False):
        st.markdown("### Compare Returns of Selected Stocks")
        default_sel = st.session_state.get('selection', tickers[:2])
        selection = st.multiselect("Select 2 or 3 Tickers to Compare", tickers, default=default_sel, max_selections=3, key='cor_sel')
        if len(selection) >= 2:
            sel_returns = returns[selection]
            cum_returns = sel_returns.cumsum() * 100
            fig2 = go.Figure()
            for t in selection:
                fig2.add_trace(go.Scatter(x=cum_returns.index, y=cum_returns[t], mode='lines', name=t))
            # Unified hover tooltip
            fig2.update_layout(
                title="Cumulative Returns (%)",
                xaxis_title="Date", yaxis_title="Cumulative Return (%)",
                hovermode='x unified',
                margin=dict(l=20, r=20, t=30, b=20), height=400,
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='var(--fg)'
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Please select at least 2 tickers to compare.")
    else:
        st.empty()
