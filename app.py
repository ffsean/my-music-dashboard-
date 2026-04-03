import streamlit as st
import pandas as pd
import os, pickle, time, unicodedata, re
import datetime

# --- 1. 工具函數定義 ---

def get_week_range(year, week):
    # 關鍵修正：確保 week 是普通整數以避免 timedelta 報錯
    week_int = int(week)
    # 根據年份與週次計算週一的日期
    first_day_of_epoch = datetime.date(year, 1, 4)
    start_of_week = first_day_of_epoch + datetime.timedelta(days=(week_int - 1) * 7 - first_day_of_epoch.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    return f"W{week_int:02d} ({start_of_week.strftime('%m/%d')} - {end_of_week.strftime('%m/%d')})"

def clean_and_classify(title):
    original_title = str(title)
    norm_title = unicodedata.normalize('NFKC', original_title).lower()
    clean_text = re.sub(r'[\s\-\[\]\(\)\【\】\?\!\.\_\,\/\\]', '', norm_title)

    cover_keys = ["cover", "歌ってみた", "翻唱", "歌い手", "唄ってみた", "vocaloidcover", "utattemita", "翻唱曲", "커버", "試唱", "弾き語り"]
    original_keys = ["original", "mv", "originalsong", "オリジナル", "原創", "公式", "official"]
    clip_keys = ["切り抜き", "切抜き", "剪輯", "kirinuki", "highlights", "精華"]

    if any(k in clean_text for k in clip_keys):
        return "✂️ 剪輯 (Kirinuki)"
    if any(k in clean_text for k in cover_keys):
        return "🎤 翻唱 (Cover)"
    if any(k in clean_text for k in original_keys):
        return "✨ 原創 (Original/MV)"
    return "🎵 其他影片"

JAPANESE_SINGER_KEYWORDS = [
    "坂本真綾", "一ノ瀬トキヤ", "一十木音也", "三浦あずさ", "如月千早", 
    "秋月律子", "四条貴音", "我那覇響", "天海春香", "萩原雪歩", 
    "菊地真", "水瀬伊織", "高槻やよい", "雙海亜美", "雙海真美",
    "島村卯月", "渋谷凛", "本田未央", "白石紬", "桜守歌織",
    "千石撫子", "花澤香菜", "早見沙織", "水瀬いのり", "悠木碧",
    "星街すいせい", "宝鐘マリン", "兎田ぺこら", "湊あくあ", "不破湊",
    "中島みゆき", "松任谷由実", "荒井由実", "米津玄師", "星野源",
    "藤井風", "椎名林檎", "宇多田ヒカル", "坂本九", "山口百恵"
]

def detect_language(text):
    text = str(text)
    if any('\u3040' <= c <= '\u30ff' for c in text): 
        return "🇯🇵 日語"
    if any(name in text for name in JAPANESE_SINGER_KEYWORDS):
        return "🇯🇵 日語"
    jp_eng_hints = ["covered", "official", "original", "mv", "utattemita", "kirinuki"]
    if any(hint in text.lower() for hint in jp_eng_hints):
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return "🇯🇵 日語"
    if any('\uac00' <= c <= '\ud7af' for c in text): 
        return "🇰🇷 韓語"
    if any('\u4e00' <= c <= '\u9fff' for c in text): 
        return "🇨🇳 中文"
    return "🌐 其他/英文"

# --- 2. 頁面配置 ---
st.set_page_config(layout="wide", page_title="全球音樂數據管理站", page_icon="🌎")

if 'active_vid' not in st.session_state:
    st.session_state['active_vid'] = None

st.title("🌎 全球音樂數據管理站 ")

# --- 3. 資料讀取與處理 ---
try:
    @st.cache_data(ttl=3600)
    def load_data(url):
        data = pd.read_csv(url, encoding='utf-8-sig')
        data['發布日期'] = pd.to_datetime(data['發布日期'])
        # 修正：確保週次與月份是整數
        data['週次'] = data['發布日期'].dt.isocalendar().week.astype(int)
        data['月份'] = data['發布日期'].dt.month.astype(int)
        
        # 執行判定邏輯
        data['語言'] = data['標題'].apply(detect_language)
        data['類別'] = data['標題'].apply(clean_and_classify)
        return data

    FILE_ID = "1_0MMLCoiJLWe-alF6BV7TGwxndba_DDp"
    direct_url = f"https://drive.google.com/u/0/uc?id={FILE_ID}&export=download"
    df = load_data(direct_url)

    # --- 4. 側邊欄控制 (修正變數定義順序) ---
    st.sidebar.header("🎯 篩選與排序")
    
    # 月份選擇
    month_options = sorted(df['月份'].unique())
    selected_month = st.sidebar.selectbox("📅 選擇月份", options=month_options, format_func=lambda x: f"{x} 月")
    
    # 根據月份過濾週次
    month_df = df[df['月份'] == selected_month]
    weeks_in_month = sorted(month_df['週次'].unique())
    
    # 週次選擇
    current_year = 2026 
    week_labels = {w: get_week_range(current_year, w) for w in weeks_in_month}
    
    selected_week = st.sidebar.select_slider(
        "🗓️ 選擇週次", 
        options=weeks_in_month, 
        format_func=lambda x: week_labels[x]
    )

    # 語言與內容篩選 (先定義變數，再進行過濾)
    selected_langs = st.sidebar.multiselect("語言過濾",
                                          options=["🇯🇵 日語", "🇰🇷 韓語", "🇨🇳 中文", "🌐 其他/英文"],
                                          default=["🇯🇵 日語", "🇰🇷 韓語", "🇨🇳 中文", "🌐 其他/英文"])

    content_filter = st.sidebar.radio("內容分類", ["全部", "僅看原創 (Original)", "僅看翻唱 (Cover)", "僅看剪輯 (Kirinuki)"])
    sort_order = st.sidebar.radio("排序方式", ["🔥 按觀看數", "📅 按日期時間"])

    # --- 5. 執行過濾邏輯 ---
    view_df = df[(df['週次'] == selected_week) & (df['語言'].isin(selected_langs))]
    
    if content_filter == "僅看原創 (Original)":
        view_df = view_df[view_df['類別'] == "✨ 原創 (Original/MV)"]
    elif content_filter == "僅看翻唱 (Cover)":
        view_df = view_df[view_df['類別'] == "🎤 翻唱 (Cover)"]
    elif content_filter == "僅看剪輯 (Kirinuki)":
        view_df = view_df[view_df['類別'] == "✂️ 剪輯 (Kirinuki)"]

    if sort_order == "🔥 按觀看數":
        view_df = view_df.sort_values(by="觀看數", ascending=False)
    else:
        view_df = view_df.sort_values(by="發布日期", ascending=False)

    # --- 6. 播放器區 ---
    if st.session_state['active_vid']:
        st.video(f"https://www.youtube.com/watch?v={st.session_state['active_vid']}")
        if st.button("❌ 關閉播放器"):
            st.session_state['active_vid'] = None
            st.rerun()
        st.divider()

    # --- 7. 顯示數據列表 ---
    st.subheader(f"📊 篩選結果: {len(view_df)} 支影片")

    for _, row in view_df.iterrows():
        yt_link = f"https://www.youtube.com/watch?v={row['ID']}"
        c = st.columns([1, 4, 1, 1, 1, 0.5])
        c[0].write(row['發布日期'].strftime('%m/%d'))
        c[1].markdown(f"**[{row['標題']}]({yt_link})**")
        c[1].caption(f"👤 {row['頻道']}")
        c[2].write(row['語言'])
        c[3].write(row['類別'])
        c[4].write(f"{row['觀看數']:,}")
        
        if c[5].button("▶️", key=f"p_{row['ID']}"):
            st.session_state['active_vid'] = row['ID']
            st.rerun()
        st.divider()

except Exception as e:
    st.error(f"❌ 發生錯誤：{e}")
    # 除錯用：印出詳細錯誤
    import traceback
    st.code(traceback.format_exc())
