import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import uuid
import time
import json
import os
import lancedb
try:
    from deltalake import DeltaTable
except ImportError:
    DeltaTable = None

# ==========================================
# 1. CẤU HÌNH TRANG (Page Configuration)
# ==========================================
st.set_page_config(
    page_title="AI Movie Concierge & MLOps Dashboard",
    page_icon="🍿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cấu hình API Backend
API_URL = "http://localhost:3000"
MODEL_VERSION = "v1.2.0-production"

# Màu sắc chủ đạo
COLORS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692", "#B6E880"]

# ==========================================
# 2. QUẢN LÝ DỮ LIỆU THẬT (Real Data Loading)
# ==========================================
@st.cache_data(ttl=3600)
def load_real_data():
    """Tải dữ liệu thật từ dự án. KHÔNG dùng mock data."""
    data = {
        'sales': None,
        'users': None,
        'top_movies': None,
        'vector_count': 0
    }

    try:
        # 1. Đọc movies.csv
        movies_path = "dataset/ml-25m/movies.csv"
        if not os.path.exists(movies_path):
            raise FileNotFoundError(f"Missing {movies_path}")
        df_movies = pd.read_csv(movies_path)
        
        # 2. Đọc ratings.csv hoặc Delta Lake
        ratings_path = "dataset/ml-25m/ratings.csv"
        if os.path.exists(ratings_path):
            # Sampling 500k rows for performance
            df_ratings = pd.read_csv(ratings_path, nrows=1000000).sample(n=500000, random_state=42)
        else:
            delta_path = "dataset/delta_lake/silver/ratings"
            if DeltaTable and os.path.exists(delta_path):
                dt = DeltaTable(delta_path)
                df_ratings = dt.to_pandas().sample(n=500000, random_state=42)
            else:
                raise FileNotFoundError("Không tìm thấy dữ liệu Ratings thực tế (CSV hoặc Delta Lake).")

        df_ratings['Ngày'] = pd.to_datetime(df_ratings['timestamp'], unit='s')
        
        # Process Sales/Ratings data
        df_sales = df_ratings.copy()
        df_sales['Doanh thu'] = 10 
        df_sales = df_sales.merge(df_movies, on='movieId', how='left')
        df_sales['Thể loại'] = df_sales['genres'].apply(lambda x: x.split('|')[0] if isinstance(x, str) else 'Unknown')
        data['sales'] = df_sales

        # User stats
        df_user_stats = df_ratings.groupby(df_ratings['Ngày'].dt.date).agg({
            'userId': ['count', 'nunique']
        }).reset_index()
        df_user_stats.columns = ['Ngày', 'Lượt đánh giá', 'Người dùng hoạt động']
        data['users'] = df_user_stats

        # Top 10 movies
        top_10 = df_ratings.groupby('movieId').size().sort_values(ascending=False).head(10).reset_index()
        top_10.columns = ['movieId', 'Rating Count']
        data['top_movies'] = top_10.merge(df_movies, on='movieId')

        # 3. LanceDB count
        db_path = "notebooks/tmp_lancedb"
        if os.path.exists(db_path):
            db = lancedb.connect(db_path)
            table_names = db.table_names()
            if "movies_real" in table_names:
                data['vector_count'] = len(db.open_table("movies_real"))
            elif "movies" in table_names:
                data['vector_count'] = len(db.open_table("movies"))

    except Exception as e:
        st.error(f"CRITICAL ERROR: {e}. Ứng dụng yêu cầu dữ liệu thực tế để khởi chạy.")
        st.stop()

    return data

# ==========================================
# 3. CÁC HÀM GIÁM SÁT THẬT (Real Monitoring)
# ==========================================

def get_system_metrics():
    """Trích xuất các chỉ số vận hành thực tế từ logs và file system."""
    metrics = {
        'kafka_total': "0",
        'storage_mb': 0.0,
        'model_status': "Offline",
        'last_update': "N/A"
    }
    
    # Kafka Total Ingested
    try:
        log_path = "logs/kafka_producer.log"
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if "Đã gửi thành công" in line:
                        metrics['kafka_total'] = line.split("thành công ")[1].split(" tin nhắn")[0]
                        metrics['last_update'] = line.split(" - ")[0]
                        break
    except: pass

    # Delta Lake Storage Size
    try:
        total_size = 0
        delta_path = 'dataset/delta_lake'
        if os.path.exists(delta_path):
            for dirpath, dirnames, filenames in os.walk(delta_path):
                for f in filenames:
                    total_size += os.path.getsize(os.path.join(dirpath, f))
        metrics['storage_mb'] = total_size / (1024 * 1024)
    except: pass

    # Model/Service Status
    try:
        log_path = "logs/service.log"
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "Service movie_recommender_service initialized" in content:
                    metrics['model_status'] = "Online"
                if "Warning: Could not load real model" in content:
                    metrics['model_status'] = "Mock/Fallback Mode"
    except: pass

    return metrics

# ==========================================
# 4. UI MODULES
# ==========================================

def render_home():
    """Trang chủ: Kiến trúc hệ thống."""
    st.title("🎬 Big Data-driven Movie Recommendation System")
    st.markdown("""
    ### Tổng quan Hệ thống (Real-world Data Pipeline)
    Hệ thống này vận hành hoàn toàn dựa trên dữ liệu thực tế:
    
    *   **Data Lakehouse:** Lưu trữ Silver/Gold tables tại Delta Lake (Local Storage).
    *   **Ingestion:** Kafka Producer gửi dữ liệu từ MovieLens 25M.
    *   **Feature Store:** Feast quản lý online/offline features.
    *   **Vector Search:** LanceDB lưu trữ movie embeddings.
    *   **Serving:** BentoML cung cấp API cho Model Retrieval.
    """)
    st.image("https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80")

def render_concierge():
    """AI Movie Concierge."""
    col_left, col_right = st.columns([6, 4], gap="large")
    with col_left:
        st.subheader("💬 AI Cine-Assistant")
        chat_container = st.container(height=550)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Hỏi về phim..."):
            with chat_container:
                st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            try:
                payload = {"message": prompt, "session_id": st.session_state.session_id}
                start_time = time.time()
                response = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
                response.raise_for_status()
                bot_reply = response.json().get("response", "No reply.")
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

    with col_right:
        st.subheader("🌟 Gợi Ý Cá Nhân Hóa")
        if not st.session_state.recommendations:
            st.info("Sử dụng User ID ở sidebar để lấy gợi ý thực tế.")
        else:
            for movie in st.session_state.recommendations:
                st.markdown(f"""
                <div class="movie-card">
                    <div class="movie-title">{movie.get('title')}</div>
                    <div class="movie-genres">{movie.get('genres', 'N/A')}</div>
                    <div class="score-badge">Độ tương thích: {int(movie.get('score', 0)*100)}%</div>
                </div>
                """, unsafe_allow_html=True)

def render_dashboard():
    """Business Dashboard."""
    data = load_real_data()
    st.title("📊 Business Performance (MovieLens Real Data)")
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Tổng Rating (Sampled)", f"{len(data['sales']):,}")
    k2.metric("Unique Users", f"{data['users']['Người dùng hoạt động'].sum():,}")
    k3.metric("Phim đã Vector hóa", f"{data['vector_count']:,}")
    k4.metric("Model Version", MODEL_VERSION)

    t1, t2, t3 = st.tabs(["📈 Xu hướng", "📊 Thể loại", "🏆 Top Phim"])
    with t1:
        df_monthly = data['sales'].copy()
        df_monthly['Tháng'] = df_monthly['Ngày'].dt.to_period('M').astype(str)
        df_m = df_monthly.groupby('Tháng').size().reset_index(name='Lượt đánh giá')
        st.plotly_chart(px.line(df_m, x='Tháng', y='Lượt đánh giá', title="Rating Trends"), use_container_width=True)
    with t2:
        df_g = data['sales'].groupby('Thể loại').size().reset_index(name='Count').sort_values('Count', ascending=False).head(10)
        st.plotly_chart(px.bar(df_g, x='Thể loại', y='Count', color='Thể loại'), use_container_width=True)
    with t3:
        st.dataframe(data['top_movies'][['title', 'genres', 'Rating Count']].head(10), use_container_width=True)

def render_system_monitoring():
    """System Monitoring."""
    st.title("🛠️ MLOps System Monitoring (Real Logs)")
    metrics = get_system_metrics()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kafka Ingested", metrics['kafka_total'])
    m2.metric("Delta Lake Size", f"{metrics['storage_mb']:.2f} MB")
    m3.metric("Model Status", metrics['model_status'])
    m4.metric("Last Log Update", metrics['last_update'])

    st.subheader("📋 Log Streams")
    l1, l2 = st.tabs(["Kafka Producer Log", "Service Log"])
    with l1:
        if os.path.exists("logs/kafka_producer.log"):
            with open("logs/kafka_producer.log", "r", encoding="utf-8") as f:
                st.code("".join(f.readlines()[-50:]))
    with l2:
        if os.path.exists("logs/service.log"):
            with open("logs/service.log", "r", encoding="utf-8") as f:
                st.code("".join(f.readlines()[-50:]))

# ==========================================
# 5. SIDEBAR & NAVIGATION
# ==========================================
st.markdown("""
<style>
    .movie-card { background: #f9f9f9; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 10px; color: #333; }
    .movie-title { font-weight: bold; font-size: 1.1em; }
    .movie-genres { font-size: 0.9em; color: #666; font-style: italic; }
    .score-badge { color: #ff4b4b; font-weight: bold; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🎬 AI Cineplex MLOps")
    mode = st.radio("Chế độ", ["🏠 Trang chủ", "🎬 Movie Concierge", "📊 Business Dashboard", "🛠️ System Monitoring"])
    st.markdown("---")
    
    if mode == "🎬 Movie Concierge":
        uid = st.text_input("User ID", "123")
        if st.button("Lấy gợi ý thật"):
            try:
                resp = requests.post(f"{API_URL}/recommend", json={"user_id": int(uid)}, timeout=10)
                st.session_state.recommendations = resp.json().get("recommendations", [])
                st.toast("Success!")
            except: st.error("Backend offline")

if mode == "🏠 Trang chủ": render_home()
elif mode == "🎬 Movie Concierge": render_concierge()
elif mode == "📊 Business Dashboard": render_dashboard()
else: render_system_monitoring()
