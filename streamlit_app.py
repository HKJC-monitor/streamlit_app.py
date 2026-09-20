import streamlit as st
import pandas as pd
import math
import urllib.request
import json

# 頁面配置與淺色風格自定義
st.set_page_config(
    page_title="HKJC 賽馬大戶落飛監控盤",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .header-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .header-title { font-size: 20px; font-weight: 700; color: #0F172A; margin: 0; }
    .header-desc { font-size: 13px; color: #64748B; margin-top: 4px; }
    .alert-card {
        background: #FEF2F2;
        border-left: 5px solid #EF4444;
        border: 1px solid #FCA5A5;
        border-left-width: 5px;
        border-radius: 10px;
        padding: 12px 15px;
        margin-bottom: 14px;
    }
    .alert-title { font-size: 15px; font-weight: 700; color: #991B1B; }
    .alert-desc { font-size: 13px; color: #7F1D1D; margin-top: 4px; line-height: 1.4; }
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
    }
    .metric-num { font-size: 18px; font-weight: 700; color: #0F172A; }
    .metric-lbl { font-size: 12px; color: #64748B; }
</style>
""", unsafe_allow_html=True)

# 方式 B 核心運算
RETENTION_RATE = 0.825

def analyze_smart_money(runners, prev_pool, curr_pool, threshold=3.0):
    n = len(runners)
    if n == 0:
        return pd.DataFrame()
    records = []
    for r in runners:
        h_no = r['horse_no']
        h_name = r['horse_name']
        p_odds = float(r.get('prev_odds', 0))
        c_odds = float(r.get('current_odds', 0))
        prev_stake = (prev_pool * RETENTION_RATE / p_odds) if p_odds > 0 else 0.0
        curr_stake = (curr_pool * RETENTION_RATE / c_odds) if c_odds > 0 else 0.0
        delta_stake = max(0.0, curr_stake - prev_stake)
        odds_drop_pct = round(((p_odds - c_odds) / p_odds * 100), 1) if p_odds > 0 else 0.0
        records.append({
            'horse_no': h_no,
            'horse_name': h_name,
            'current_odds': c_odds,
            'prev_odds': p_odds,
            'odds_drop_pct': odds_drop_pct,
            'delta_stake': delta_stake
        })
    df = pd.DataFrame(records)
    total_delta = df['delta_stake'].sum()
    avg_delta = total_delta / n if n > 0 else 0.0
    top_cutoff = max(1, math.ceil(0.10 * n))
    df['rank'] = df['delta_stake'].rank(ascending=False, method='min').astype(int)
    df['ratio_to_avg'] = (df['delta_stake'] / avg_delta).round(2) if avg_delta > 0 else 0.0

    def get_status(row):
        if row['rank'] <= top_cutoff and row['ratio_to_avg'] >= threshold:
            return "🚨 大戶重注落飛"
        elif row['rank'] <= top_cutoff and row['ratio_to_avg'] >= 2.0:
            return "🔥 資金主要追捧"
        elif row['ratio_to_avg'] >= 1.5:
            return "📈 溫和注碼流入"
        elif row['odds_drop_pct'] > 15:
            return "⚠️ 賠率下滑"
        else:
            return "⚪ 走勢平穩"

    df['status'] = df.apply(get_status, axis=1)
    df = df.sort_values(by=['rank', 'delta_stake'], ascending=[True, False]).reset_index(drop=True)
    return df

DEFAULT_BOT_TOKEN = "8589965192:AAGGblHTUfSaCV4JuGwsgNC4pLNJ2nPpQE0"

def send_telegram(bot_token, chat_id, msg):
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status == 200
    except Exception:
        return False

st.markdown("""
<div class="header-box">
    <div class="header-title">🏇 賽馬大戶落飛即時監控網站</div>
    <div class="header-desc">前 10% 資金異動倍數模型 · 手機專屬獨立版</div>
</div>
""", unsafe_allow_html=True)

col_s1, col_s2 = st.columns([1, 1])
with col_s1:
    race_options = [f"第 {i} 場" for i in range(1, 12)]
    selected_race = st.selectbox("選擇賽事場次", race_options, index=4)
    race_num = int(selected_race.replace("第 ", "").replace(" 場", ""))

with col_s2:
    threshold = st.slider("大戶倍數門檻 (高於平均倍數)", 2.0, 5.0, 3.0, 0.5)

sample_runners = [
    {"horse_no": 1, "horse_name": "金鑽貴人", "prev_odds": 2.4, "current_odds": 2.1},
    {"horse_no": 2, "horse_name": "福逸", "prev_odds": 6.8, "current_odds": 7.2},
    {"horse_no": 3, "horse_name": "好眼光", "prev_odds": 14.0, "current_odds": 6.5},
    {"horse_no": 4, "horse_name": "韋小寶", "prev_odds": 22.0, "current_odds": 24.0},
    {"horse_no": 5, "horse_name": "聚才", "prev_odds": 18.0, "current_odds": 19.0},
    {"horse_no": 6, "horse_name": "蟲草成名", "prev_odds": 9.5, "current_odds": 8.0},
    {"horse_no": 7, "horse_name": "顯心星", "prev_odds": 12.0, "current_odds": 13.0},
    {"horse_no": 8, "horse_name": "速遞奇兵", "prev_odds": 35.0, "current_odds": 38.0},
    {"horse_no": 9, "horse_name": "八仟師", "prev_odds": 15.0, "current_odds": 16.5},
    {"horse_no": 10, "horse_name": "勝不驕", "prev_odds": 28.0, "current_odds": 30.0},
    {"horse_no": 11, "horse_name": "駿馬風采", "prev_odds": 45.0, "current_odds": 48.0},
    {"horse_no": 12, "horse_name": "狀元及第", "prev_odds": 50.0, "current_odds": 55.0},
    {"horse_no": 13, "horse_name": "紅運帝王", "prev_odds": 32.0, "current_odds": 33.0},
    {"horse_no": 14, "horse_name": "知道必勝", "prev_odds": 60.0, "current_odds": 65.0},
]

prev_pool = 12500000.0
curr_pool = 14300000.0

df = analyze_smart_money(sample_runners, prev_pool, curr_pool, threshold=threshold)
smart_horses = df[df['status'].str.contains("大戶")]

if not smart_horses.empty:
    for _, row in smart_horses.iterrows():
        st.markdown(f"""
        <div class="alert-card">
            <div class="alert-title">🚨 【第 {race_num} 場】大戶落飛鎖定：{row['horse_no']}號 「{row['horse_name']}」</div>
            <div class="alert-desc">
                • <b>新增注碼</b>：HK$ {row['delta_stake']:,.0f}（資金流入全場第 {row['rank']} 名）<br>
                • <b>強度倍數</b>：達到全場平均注碼的 <b>{row['ratio_to_avg']} 倍</b><br>
                • <b>賠率跳水</b>：{row['prev_odds']} ➔ <b>{row['current_odds']}</b>（跌幅 <b>{row['odds_drop_pct']}%</b>）
            </div>
        </div>
        """, unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""<div class="metric-card"><div class="metric-num">HK$ {curr_pool:,.0f}</div><div class="metric-lbl">當前彩池總額</div></div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""<div class="metric-card"><div class="metric-num">HK$ {curr_pool - prev_pool:,.0f}</div><div class="metric-lbl">近3分鐘增量</div></div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""<div class="metric-card"><div class="metric-num">HK$ {(curr_pool - prev_pool)/len(df):,.0f}</div><div class="metric-lbl">全場平均注碼</div></div>""", unsafe_allow_html=True)
with m4:
    cnt = len(smart_horses)
    st.markdown(f"""<div class="metric-card"><div class="metric-num" style="color: {'#DC2626' if cnt > 0 else '#16A34A'};">{cnt} 匹</div><div class="metric-lbl">大戶觸發馬匹</div></div>""", unsafe_allow_html=True)

st.write("")
st.subheader("📋 全場馬匹資金流向排行 (方式 B)")

show_df = df[['rank', 'horse_no', 'horse_name', 'current_odds', 'prev_odds', 'odds_drop_pct', 'delta_stake', 'ratio_to_avg', 'status']].copy()
show_df.columns = ['排名', '馬號', '馬名', '即時獨贏', '上個賠率', '跌幅(%)', '新增注碼(HK$)', '平均倍數', '狀態']

show_df['即時獨贏'] = show_df['即時獨贏'].apply(lambda x: f"{x:.1f}")
show_df['上個賠率'] = show_df['上個賠率'].apply(lambda x: f"{x:.1f}")
show_df['跌幅(%)'] = show_df['跌幅(%)'].apply(lambda x: f"{x:+.1f}%" if x != 0 else "0.0%")
show_df['新增注碼(HK$)'] = show_df['新增注碼(HK$)'].apply(lambda x: f"${x:,.0f}")
show_df['平均倍數'] = show_df['平均倍數'].apply(lambda x: f"{x:.1f}x")

st.dataframe(show_df, use_container_width=True, hide_index=True)

with st.sidebar:
    st.header("📲 Telegram 手機推送設定")
    c_id = st.text_input("輸入你的 Telegram Chat ID", value="")
    if st.button("發送測試訊息到手機"):
        if not c_id:
            st.error("請先輸入 Chat ID")
        else:
            ok = send_telegram(DEFAULT_BOT_TOKEN, c_id, f"✅ 【HKJC 網站連結成功】第 {race_num} 場落飛測試訊息！")
            if ok:
                st.success("已成功發送至你手機 Telegram！")
            else:
                st.error("發送失敗，請確認在 Telegram 點擊過機器人的 Start。")


