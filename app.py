import streamlit as st
import pandas as pd
import os, pickle, time, unicodedata, re

# --- 頁面配置 ---
st.set_page_config(layout="wide", page_title="全球音樂數據管理站", page_icon="🌎")

# --- 💡 重要修改：Streamlit Cloud 專用的讀取邏輯 ---
# 因為 Streamlit Cloud 沒有 /content/drive，我們改用你剛才成功的 Google Drive 直接下載連結
FILE_ID = "1_0MMLCoiJLWe-alF6BV7TGwxndba_DDp"
direct_url = f"https://drive.google.com/u/0/uc?id={FILE_ID}&export=download"

# --- 強化版分類邏輯 --- (保留你的原始程式)
def clean_and_classify(title):
    original_title = str(title)
    norm_title = unicodedata.normalize('NFKC', original_title).lower()
    clean_text = re.sub(r'[\s\-\[\]\(\)\【\】\?\!\.\_\,\/\\]', '', norm_title)
    cover_keys = ["cover", "歌ってみた", "翻唱", "歌い手", "唄ってみた", "vocaloidcover", "utattemita", "翻唱曲", "커버", "試唱"]
    if any(k in clean_text for k in cover_keys):
        return "🎤 翻唱 (Cover)"
    return "✨ 原創 (Original/MV)"

# --- 語言判定 --- (保留你的原始程式)
def detect_language(text):
    text = str(text)
    if any('\u3040' <= c <= '\u30ff' for c in text): return "🇯🇵 日語"
    if any('\uac00' <= c <= '\ud7af' for c in text): return "🇰🇷 韓語"
    if any('\u4e00' <= c <= '\u9fff' for c in text): return "🇨🇳 中文"
    return "🌐 其他/英文"

if 'active_vid' not in st.session_state:
    st.session_state['active_vid'] = None

st.title("🌎 全球音樂數據管理站 (極致精準版)")

# --- 💡 修改讀取區塊 ---
try:
    # 直接讀取雲端硬碟的 CSV
    @st.cache_data
    def load_data(url):
        return pd.read_csv(url, encoding='utf-8-sig')

    df = load_data(direct_url)
    
    # 預處理資料 (保留你的邏輯)
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

    content_filter = st.sidebar.radio("內容分類", ["全部", "僅看原創 (Original)", "僅看翻唱 (Cover)"])
    sort_order = st.sidebar.radio("排序方式", ["🔥 按觀看數", "📅 按日期時間"])

    # 執行過濾
    view_df = df[(df['週次'] == selected_week) & (df['語言'].isin(selected_langs))]
    if content_filter == "僅看原創 (Original)":
        view_df = view_df[view_df['類別'] == "✨ 原創 (Original/MV)"]
    elif content_filter == "僅看翻唱 (Cover)":
        view_df = view_df[view_df['類別'] == "🎤 翻唱 (Cover)"]

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
        c = st.columns([1, 4, 1, 1, 1, 0.5])
        c[0].write(row['發布日期'].strftime('%m/%d'))
        c[1].markdown(f"**{row['標題']}**")
        c[1].caption(f"👤 {row['頻道']}")
        c[2].write(row['語言'])
        c[3].write(row['類別'])
        c[4].write(f"{row['觀看數']:,}")
        # ID 必須存在於 CSV 中才能播放
        if c[5].button("▶️", key=f"p_{row['ID']}"):
            st.session_state['active_vid'] = row['ID']
            st.rerun()
        st.divider()

except Exception as e:
    st.error(f"❌ 讀取資料失敗：{e}")
    st.info("請確認：1. 雲端硬碟檔案 ID 正確。 2. 已開啟『知道連結的任何人』共用權限。")
