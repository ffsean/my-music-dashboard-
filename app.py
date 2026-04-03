
import streamlit as st
import pandas as pd
import os, pickle, time, unicodedata, re
import re

def get_google_drive_direct_url(sharing_url):
    # 使用正規表達式提取 ID
    match = re.search(r'/d/([^/]+)', sharing_url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return sharing_url

# 貼上你從 Google Drive 複製出來的原始「共用連結」
original_url = "https://drive.google.com/file/d/1KXf02uOns1usXLEh06ahDYcYi6NmXnY7/view?usp=sharing"

# 2. 頁面配置 (必須放在最前面)
st.set_page_config(layout="wide", page_title="全球音樂數據管理站", page_icon="🌍")

# 3. 讀取資料
original_url = "https://drive.google.com/file/d/1KXf02uOns1usXLEh06ahDYCYi6NmXnY7/view?usp=sharing"

try:
    direct_url = get_google_drive_direct_url(original_url)
    # 使用快取，避免每次載入網頁都重新下載 CSV，速度會變快
    @st.cache_data
    def load_data(url):
        return pd.read_csv(url)

    df = load_data(direct_url)

    # --- 網頁顯示內容 ---
    st.title("🎤 2026 三月翻唱資料庫")
    
    # 搜尋功能
    search_query = st.text_input("輸入歌曲標題或頻道名稱進行搜尋")
    
    if search_query:
        # 模糊搜尋標題與頻道
        filtered_df = df[df['標題'].str.contains(search_query, case=False, na=False) | 
                         df['頻道'].str.contains(search_query, case=False, na=False)]
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"資料讀取失敗，請確認雲端硬碟共用權限。錯誤: {e}")
# --- 頁面配置 ---
st.set_page_config(layout="wide", page_title="全球音樂數據管理站", page_icon="🌎")

# 適應不同環境的路徑設定 (若本地找不到 Drive 則找當前目錄)
DRIVE_PATH = "/content/drive/MyDrive/"
if not os.path.exists(DRIVE_PATH):
    DRIVE_PATH = "./"

# --- 強化版分類邏輯 ---
def clean_and_classify(title):
    original_title = str(title)
    # 1. 正規化：將全形轉半形 (例如 Ｃｏｖｅｒ -> cover)
    norm_title = unicodedata.normalize('NFKC', original_title).lower()
    # 2. 移除所有空格與常見符號 (處理 歌 っ て み た 或 【 cover 】)
    clean_text = re.sub(r'[\s\-\[\]\(\)\【\】\?\!\.\_\,\/\\]', '', norm_title)
    
    # 3. 嚴謹關鍵字庫 (包含日、中、韓、Live映像、女性が歌う)
    cover_keys = [
        "cover", "歌ってみた", "翻唱", "歌い手", "唄ってみた", 
        "vocaloidcover", "utattemita", "翻唱曲", "커버", "試唱",
        "女性が歌う", "男性が歌う", "live映像", "演唱會", "ライブ映像",
        "歌唱", "歌枠", "concert", "blu-ray"
    ]
    
    if any(k in clean_text for k in cover_keys):
        return "🎤 翻唱/演唱 (Live & Cover)"
    return "✨ 原創 (Original/MV)"

# --- 語言判定 ---
def detect_language(text):
    text = str(text)
    if any('\u3040' <= c <= '\u30ff' for c in text): return "🇯🇵 日語"
    if any('\uac00' <= c <= '\ud7af' for c in text): return "🇰🇷 韓語"
    if any('\u4e00' <= c <= '\u9fff' for c in text): return "🇨🇳 中文"
    return "🌐 其他/英文"

if 'active_vid' not in st.session_state:
    st.session_state['active_vid'] = None

st.title("🌎 全球音樂數據管理站")

# 1. 檔案讀取 (自動抓取 CSV)
all_files = [f for f in os.listdir(DRIVE_PATH) if f.endswith(".csv") and ("youtube_data" in f or "extreme" in f)]

if not all_files:
    st.error("❌ 找不到 CSV 檔案。")
else:
    all_files.sort(key=lambda x: os.path.getsize(os.path.join(DRIVE_PATH, x)), reverse=True)
    selected_file = st.sidebar.selectbox("📂 數據來源", options=all_files)
    
    df = pd.read_csv(os.path.join(DRIVE_PATH, selected_file))
    df['發布日期'] = pd.to_datetime(df['發布日期'])
    df['週次'] = df['發布日期'].dt.isocalendar().week
    df['類別'] = df['標題'].apply(clean_and_classify)
    df['語言'] = df['標題'].apply(detect_language)
    df['觀看數'] = pd.to_numeric(df['觀看數'], errors='coerce').fillna(0).astype(int)

    # 2. 側邊欄過濾器
    st.sidebar.header("🎯 篩選與排序")
    weeks = sorted(df['週次'].unique())
    selected_week = st.sidebar.select_slider("選擇週次", options=weeks)
    selected_langs = st.sidebar.multiselect("語言", 
                                          options=["🇯🇵 日語", "🇰🇷 韓語", "🇨🇳 中文", "🌐 其他/英文"], 
                                          default=["🇯🇵 日語", "🇰🇷 韓語", "🇨🇳 中文", "🌐 其他/英文"])
    content_filter = st.sidebar.radio("內容", ["全部", "僅看原創", "僅看翻唱/Live"])
    sort_order = st.sidebar.radio("排序", ["🔥 按觀看數", "📅 按日期"])

    view_df = df[(df['週次'] == selected_week) & (df['語言'].isin(selected_langs))]
    if content_filter == "僅看原創":
        view_df = view_df[view_df['類別'] == "✨ 原創 (Original/MV)"]
    elif content_filter == "僅看翻唱/Live":
        view_df = view_df[view_df['類別'] == "🎤 翻唱/演唱 (Live & Cover)"]

    if sort_order == "🔥 按觀看數":
        view_df = view_df.sort_values(by="觀看數", ascending=False)
    else:
        view_df = view_df.sort_values(by="發布日期", ascending=False)

    # 3. 播放器
    if st.session_state['active_vid']:
        st.video(f"https://www.youtube.com/watch?v={st.session_state['active_vid']}")
        if st.button("❌ 關閉"):
            st.session_state['active_vid'] = None
            st.rerun()

    # 4. 列表展示
    st.subheader(f"📊 篩選結果: {len(view_df)} 支影片")
    for _, row in view_df.iterrows():
        c = st.columns([1, 4, 1, 1, 1, 0.5])
        c[0].write(row['發布日期'].strftime('%m/%d'))
        c[1].markdown(f"**{row['標題']}**")
        c[1].caption(f"👤 {row['頻道']}")
        c[2].write(row['語言'])
        c[3].write(row['類別'])
        c[4].write(f"{row['觀看數']:,}")
        if c[5].button("▶️", key=f"p_{row['ID']}"):
            st.session_state['active_vid'] = row['ID']
            st.rerun()
        st.divider()
