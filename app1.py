import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="台股強勢股篩選器", layout="wide")

st.title("🚀 台股全自動快速篩選器")

@st.cache_data(ttl=3600) # 快取一小時，避免重複抓取
def get_tw_stock_list():
    url_twse = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    url_tpex = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    stocks = []
    for url, suffix in [(url_twse, ".TW"), (url_tpex, ".TWO")]:
        res = requests.get(url)
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        df['code'] = df['有價證券代號及名稱'].str.split('　').str[0]
        code_list = df[df['code'].str.len() == 4]['code'].tolist()
        stocks.extend([s + suffix for s in code_list])
    return stocks

def process_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if len(hist) < 3: return None
        
        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        prev2_close = hist['Close'].iloc[-3]
        volume_lots = hist['Volume'].iloc[-1] / 1000
        change_pct = ((last_close - prev_close) / prev_close) * 100
        
        # 核心邏輯：成交量 > 1000 且 連續兩天漲
        if volume_lots > 1000 and last_close > prev_close and prev_close > prev2_close:
            return {"代號": ticker, "收盤價": round(last_close, 2), "漲幅(%)": round(change_pct, 2), "成交量(張)": int(volume_lots)}
    except:
        return None
    return None

if st.button('執行全市場掃描'):
    all_stocks = get_tw_stock_list()
    results = []
    
    with st.spinner(f'正在並行掃描 {len(all_stocks)} 檔股票...'):
        # 使用 10 個執行緒同時抓取資料，大幅提升速度
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_stock, s) for s in all_stocks]
            for future in futures:
                res = future.result()
                if res: results.append(res)
    
    if results:
        df = pd.DataFrame(results).sort_values(by="漲幅(%)", ascending=False).head(20)
        st.success(f"掃描完畢！共找到 {len(results)} 檔符合條件。")
        st.table(df)
    else:
        st.warning("查無符合條件之股票。")
