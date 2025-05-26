import streamlit as st
import plotly.graph_objects as go
from utils.computations import compute_weekday_returns
import pandas as pd

def weekday_intraday_tab(default_df, custom_dfs, labels, periods):
    st.markdown("### Average Intraday Return by Weekday")
    c1, c2, _, _ = st.columns(4)
    sp_label = c1.selectbox("Start Period", labels, 0, key='sp_wd')
    ep_label = c2.selectbox("End Period", labels, len(labels)-1, key='ep_wd')
    st.markdown("<small style='color:#aaa;'>Includes both start & end months.</small>", unsafe_allow_html=True)
    sp, ep = periods[labels.index(sp_label)], periods[labels.index(ep_label)]
    stocks = sorted(default_df['stock'].unique()) + [f"User File: {n}" for n, _ in custom_dfs]
    selected = st.selectbox("Select Stock Dataset", stocks, key='sel_wd')
    df_sel = (
        dict(custom_dfs).get(selected.replace("User File: ", "")) 
        if selected.startswith("User File:") 
        else default_df[default_df['stock']==selected].drop(columns=['stock'])
    )
    if sp <= ep:
        df_wd = compute_weekday_returns(df_sel, sp, ep)
        if df_wd is None:
            st.error("Needs 'open' & 'close' columns in data.")
        else:
            cA, cB = st.columns(2)
            with cA:
                styled = df_wd.style.apply(
                    lambda r: [
                        'color: green' if 'Positive' in c and v>0 
                        else 'color: red' if 'Negative' in c and v>0 
                        else '' 
                        for v, c in zip(r.values, df_wd.columns)
                    ], axis=1
                )
                st.dataframe(styled, use_container_width=True)
            with cB:
                colors = ['green' if v>0 else 'red' for v in df_wd['Avg Return (%)']]
                fig = go.Figure(go.Bar(x=df_wd['Weekday'], y=df_wd['Avg Return (%)'], marker_color=colors))
                fig.update_layout(
                    plot_bgcolor='var(--bg)',
                    paper_bgcolor='var(--bg)',
                    font_color='var(--fg)',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Start period must precede end period.")
