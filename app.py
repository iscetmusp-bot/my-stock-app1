import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="台股每日強勢股篩選", layout="wide")

st.title("📈 台股全自動篩選器")
st.write("邏輯：1.成交量>1000張 2.漲幅前20名 3.連續上漲第二天")

# --- 1. 自動獲取全台股代碼清單 ---
@st.cache_data # 增加快取，避免重複抓取浪費時間
def get_tw_stock_list():
    # 抓取上市清單
    url_twse = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    # 抓取上櫃清單
    url_tpex = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    
    stocks = []
    for url, suffix in [(url_twse, ".TW"), (url_tpex, ".TWO")]:
        res = requests.get(url)
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        df['code'] = df['有價證券代號及名稱'].str.split('　').str[0]
        # 篩選 4 位數的普通股
        code_list = df[df['code'].str.len() == 4]['code'].tolist()
        stocks.extend([s + suffix for s in code_list])
    
    return stocks

# --- 2. 核心篩選邏輯 ---
def fast_filter(stock_list):
    results = []
    progress_bar = st.progress(0)
    total = len(stock_list)
    
    # 為了示範速度，我們取前 100 檔跑測試，若要全跑請移除 [:100]
    # 注意：全跑需要一段時間，yfinance 有流量限制
    test_list = stock_list[:100] 
    
    for i, ticker in enumerate(test_list):
        try:
            stock = yf.Ticker(ticker)
            # 抓取 5 天資料
            hist = stock.history(period="5d")
            if len(hist) < 3: continue
            
            # 數據準備
            last_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            prev2_close = hist['Close'].iloc[-3]
            volume_shares = hist['Volume'].iloc[-1]
            volume_lots = volume_shares / 1000  # 換算成張
            change_pct = ((last_close - prev_close) / prev_close) * 100
            
            # 判斷邏輯
            # 條件：成交量 > 1000張 且 連續兩天收盤價上漲
            if volume_lots > 1000 and last_close > prev_close and prev_close > prev2_close:
                results.append({
                    "代號": ticker,
                    "收盤價": round(last_close, 2),
                    "漲幅(%)": round(change_pct, 2),
                    "成交量(張)": int(volume_lots)
                })
        except:
            continue
        progress_bar.progress((i + 1) / len(test_list))
        
    return pd.DataFrame(results)

# --- 3. 介面按鈕 ---
if st.button('開始全市場掃描 (測試前100檔)'):
    with st.spinner('正在獲取最新清單並計算中...'):
        all_stocks = get_tw_stock_list()
        final_df = fast_filter(all_stocks)
        
        if not final_df.empty:
            # 漲幅前 20 名
            top_20 = final_df.sort_values(by="漲幅(%)", ascending=False).head(20)
            st.success(f"掃描完成！符合條件共 {len(final_df)} 檔")
            st.table(top_20)
        else:
            st.warning("目前範圍內無符合條件股票（可能今日尚未開盤或量能不足）")
