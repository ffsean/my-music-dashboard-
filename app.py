import streamlit as st
import pandas as pd
import os, pickle, time, unicodedata, re

# --- 頁面配置 ---
st.set_page_config(layout="wide", page_title="全球音樂數據管理站", page_icon="🌎")

# --- 💡 設定 Google Drive 檔案 ID ---
FILE_ID = "1_0MMLCoiJLWe-alF6BV7TGwxndba_DDp"
direct_url = f"https://drive.google.com/u/0/uc?id={FILE_ID}&export=download"

# --- 🛠️ 強化版分類邏輯 (新增剪輯與關鍵字原創) ---
def clean_and_classify(title):
    original_title = str(title)
    # 1. 將全形轉半形並轉小寫
    norm_title = unicodedata.normalize('NFKC', original_title).lower()
    # 2. 移除常見符號以便比對
    clean_text = re.sub(r'[\s\-\[\]\(\)\【\】\?\!\.\_\,\/\\]', '', norm_title)

    # 3. 定義關鍵字庫
    cover_keys = ["cover", "歌ってみた", "翻唱", "歌い手", "唄ってみた", "vocaloidcover", "utattemita", "翻唱曲", "커버", "試唱", "弾き語り"]
    original_keys = ["original", "mv", "originalsong", "オリジナル", "原創", "公式", "official"]
    clip_keys = ["切り抜き", "切抜き", "剪輯", "kirinuki", "highlights", "精華"]

    # 4. 判定優先順序：剪輯 > 翻唱 > 原創
    if any(k in clean_text for k in clip_keys):
        return "✂️ 剪輯 (Kirinuki)"
    if any(k in clean_text for k in cover_keys):
        return "🎤 翻唱 (Cover)"
    if any(k in clean_text for k in original_keys):
        return "✨ 原創 (Original/MV)"
    
    return "🎵 其他影片"

# --- 語言判定 ---
def detect_language(text):
    text = str(text)
    if any('\u3040' <= c <= '\u30ff' for c in text): return "🇯🇵 日語"
    if any('\uac00' <= c <= '\ud7af' for c in text): return "🇰🇷 韓語"
    if any('\u4e00' <= c <= '\u9fff' for c in text): return "🇨🇳 中文"
    return "🌐 其他/英文"

if 'active_vid' not in st.session_state:
    st.session_state['active_vid'] = None

st.title("🌎 全球音樂數據管理站 (超連結版)")

try:
    @st.cache_data(ttl=3600)
    def load_data(url):
        return pd.read_csv(url, encoding='utf-8-sig')

    df = load_data(direct_url)
    
    # 數據預處理
    df['發布日期'] = pd.to_datetime(df['發布日期'])
    df['週次'] = df['發布日期'].dt.isocalendar().week
    df['類別'] = df['標題'].apply(clean_and_classify)
    df['語言'] = df['標題'].apply(detect_language)
    df['觀看數'] = pd.to_numeric(df['觀看數'], errors='coerce').fillna(0).astype(int)

    # 2. 側邊欄控制
    st.sidebar.header("🎯 篩選與排序")
    weeks = sorted(df['週次'].unique())
    selected_week = st.sidebar.select_slider("選擇週次", options=weeks)

    selected_langs = st.sidebar.multiselect("語言過濾",
                                          options=["🇯🇵 日語", "🇰🇷 韓語", "🇨🇳 中文", "🌐 其他/英文"],
                                          default=["🇯🇵 日語", "🇰🇷 韓語", "🇨🇳 中文", "🌐 其他/英文"])

    content_filter = st.sidebar.radio("內容分類", ["全部", "僅看原創 (Original)", "僅看翻唱 (Cover)", "僅看剪輯 (Kirinuki)"])
    sort_order = st.sidebar.radio("排序方式", ["🔥 按觀看數", "📅 按日期時間"])

    # 執行過濾
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

    # 3. 播放器 (置頂)
    if st.session_state['active_vid']:
        st.video(f"https://www.youtube.com/watch?v={st.session_state['active_vid']}")
        if st.button("❌ 關閉播放器"):
            st.session_state['active_vid'] = None
            st.rerun()
        st.divider()

    # 4. 數據列表
    st.subheader(f"📊 篩選結果: {len(view_df)} 支影片")

    for _, row in view_df.iterrows():
        # 建立 YouTube 網址
        yt_link = f"https://www.youtube.com/watch?v={row['ID']}"
        
        c = st.columns([1, 4, 1, 1, 1, 0.5])
        c[0].write(row['發布日期'].strftime('%m/%d'))
        
        # --- 💡 修改標題為超連結 ---
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
    st.error(f"❌ 讀取失敗：{e}")
