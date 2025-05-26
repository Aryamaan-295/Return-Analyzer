import streamlit as st
from utils.computations import compute_seasonality_heatmap
import pandas as pd

def seasonality_tab(default_df, custom_dfs):
    st.markdown("### Seasonality Heatmap")
    stocks = sorted(default_df['stock'].unique()) + [f"User File: {n}" for n, _ in custom_dfs]
    selected = st.selectbox("Select Stock Dataset", stocks, key='sel_sea')
    df_sel = (
        dict(custom_dfs).get(selected.replace("User File: ", "")) 
        if selected.startswith("User File:") 
        else default_df[default_df['stock']==selected].drop(columns=['stock'])
    )
    heat, pr, nr = compute_seasonality_heatmap(df_sel)
    def style_cell(v):
        if pd.isna(v): return ''
        if v >= 5: return 'background-color:#004d00;color:#fff'
        if v > 0: return 'background-color:#007700;color:#fff'
        if v == 0: return 'background-color:#000;color:#fff'
        if v > -5: return 'background-color:#550000;color:#fff'
        return 'background-color:#330000;color:#fff'
    styled_heat = heat.style.map(style_cell)
    st.dataframe(styled_heat, use_container_width=True, height=400)
    r_df = pd.DataFrame({'Positive Ratio (%)': pr, 'Negative Ratio (%)': nr}).T
    r_df.columns = heat.columns
    r_df = r_df.round(2).astype(str).add('%')
    styled_r = r_df.style.apply(
        lambda r: ['background-color:#000;color:' + ('green' if 'Positive' in r.name else 'red') for _ in r],
        axis=1
    )
    st.dataframe(styled_r, use_container_width=True)
