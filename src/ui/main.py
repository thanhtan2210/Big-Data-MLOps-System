import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import requests

# Cấu hình trang
st.set_page_config(
    page_title="Big Data Movie Recommendation System",
    page_icon="🎬",
    layout="wide"
)

# Sidebar điều hướng
st.sidebar.title("🚀 MLOps Navigation")
page = st.sidebar.radio("Go to", ["🏠 Home", "🎬 Movie Recommendation", "📊 System Monitoring"])

# --- TRANG CHỦ ---
if page == "🏠 Home":
    st.title("🎬 Big Data-driven Movie Recommendation System")
    st.markdown("""
    ### Chào mừng bạn đến với Hệ thống Gợi ý Phim quy mô lớn!
    Hệ thống này được xây dựng trên nền tảng **Lakehouse Architecture** và quy trình **MLOps** hiện đại nhất:
    
    *   **Big Data Engine:** Apache Spark & Delta Lake (MinIO).
    *   **Real-time Ingestion:** Kafka.
    *   **MLOps Lifecycle:** Feast (Feature Store) & MLflow.
    *   **AI Model:** Two-Tower Retrieval & Ranking (BentoML).
    *   **Vector Search:** LanceDB.
    
    **Hướng dẫn sử dụng:**
    1. Chọn trang **Movie Recommendation** để thử nghiệm tính năng gợi ý.
    2. Chọn trang **System Monitoring** để xem các chỉ số vận hành Big Data thời gian thực.
    """)
    st.image("https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80")

# --- TRANG GỢI Ý PHIM ---
elif page == "🎬 Movie Recommendation":
    st.title("🎬 Personalized Movie Recommendations")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("User Input")
        user_id = st.text_input("Enter User ID", value="101")
        btn_recommend = st.button("Get Recommendations")
        
    with col2:
        if btn_recommend:
            with st.spinner(f"Fetching features from Feast and searching Vector DB..."):
                time.sleep(1) # Giả lập độ trễ mạng
                
                # Mock data gọi từ BentoML Service
                recommendations = [
                    {"movie_id": 1, "title": "Toy Story (1995)", "genre": "Animation|Children|Comedy", "score": 0.98},
                    {"movie_id": 2, "title": "Jumanji (1995)", "genre": "Adventure|Children|Fantasy", "score": 0.95},
                    {"movie_id": 3, "title": "Heat (1995)", "genre": "Action|Crime|Thriller", "score": 0.91},
                    {"movie_id": 4, "title": "GoldenEye (1995)", "genre": "Action|Adventure|Thriller", "score": 0.88},
                    {"movie_id": 5, "title": "Casino (1995)", "genre": "Crime|Drama", "score": 0.85}
                ]
                
                st.subheader(f"Top 5 Recommendations for User {user_id}")
                for i, rec in enumerate(recommendations):
                    with st.expander(f"#{i+1}: {rec['title']} - Score: {rec['score']}"):
                        st.write(f"**Genres:** {rec['genre']}")
                        st.progress(rec['score'])

# --- TRANG GIÁM SÁT HỆ THỐNG ---
elif page == "📊 System Monitoring":
    st.title("📊 Big Data & MLOps Dashboard")
    
    # Hàng 1: Chỉ số tổng quan
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kafka Ingestion", "1.2k req/s", "+15%")
    m2.metric("Delta Lake Storage", "25.4 GB", "ACID: OK")
    m3.metric("Retrieval Latency", "4.2 ms", "LanceDB")
    m4.metric("Active Models", "2", "Production")
    
    # Hàng 2: Biểu đồ luồng dữ liệu
    st.subheader("📈 Real-time Data Pipeline Throughput")
    chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['Bronze Layer', 'Silver Layer', 'Gold Layer']
    )
    st.line_chart(chart_data)
    
    # Hàng 3: Chất lượng dữ liệu & Mô hình
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🛡️ Data Quality Gate Status")
        quality_df = pd.DataFrame({
            'Category': ['Valid', 'Null Removed', 'Invalid Rating'],
            'Count': [950, 30, 20]
        })
        fig = px.pie(quality_df, values='Count', names='Category', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.subheader("🎯 Model Performance (Recall@100)")
        recall_data = pd.DataFrame({
            'Epoch': [1, 2, 3, 4, 5],
            'Recall': [0.45, 0.58, 0.65, 0.72, 0.78]
        })
        fig2 = px.bar(recall_data, x='Epoch', y='Recall', color='Recall')
        st.plotly_chart(fig2, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.info("Developed for Big Data & MLOps Thesis Project")
