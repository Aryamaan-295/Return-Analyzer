import streamlit as st
import plotly.graph_objects as go
from utils.computations import compute_monthly_returns
import pandas as pd

def monthly_window_tab(default_df, custom_dfs):
    st.markdown("### Monthly Buy & Hold Window")
    c1, c2, _, _ = st.columns(4)
    sd = c1.number_input("Start Day", 1, 28, 2, key='sd_mon')
    ed = c2.number_input("End Day", 1, 31, 13, key='ed_mon')
    st.markdown("<small style='color:#aaa;'>Includes both start & end days.</small>", unsafe_allow_html=True)
    stocks = sorted(default_df['stock'].unique()) + [f"User File: {n}" for n, _ in custom_dfs]
    selected = st.selectbox("Select Stock Dataset", stocks, key='sel_mon')
    df_sel = (
        dict(custom_dfs).get(selected.replace("User File: ", "")) 
        if selected.startswith("User File:") 
        else default_df[default_df['stock']==selected].drop(columns=['stock'])
    )
    if sd < ed:
        df_mon = compute_monthly_returns(df_sel, sd, ed)
        cA, cB = st.columns(2)
        with cA:
            styled = df_mon.style.apply(
                lambda r: [
                    'color: green' if 'Positive' in c and v>0 
                    else 'color: red' if 'Negative' in c and v>0 
                    else '' 
                    for v, c in zip(r.values, df_mon.columns)
                ], axis=1
            )
            st.dataframe(styled, use_container_width=True)
        with cB:
            colors = ['green' if v>0 else 'red' for v in df_mon['Avg Return (%)']]
            fig = go.Figure(go.Bar(x=df_mon['Month'], y=df_mon['Avg Return (%)'], marker_color=colors))
            fig.update_layout(
                plot_bgcolor='var(--bg)',
                paper_bgcolor='var(--bg)',
                font_color='var(--fg)',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Start day must precede end day.")
