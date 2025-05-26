import streamlit as st
import pandas as pd
import numpy as np
import calendar
from datetime import datetime

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

@st.cache_data
def compute_correlation(df):
    wide = df.pivot_table(values='close', index=df.index, columns='stock').ffill()
    returns = wide.pct_change().dropna()
    corr = returns.corr() * 100  # percentages
    return corr, returns
