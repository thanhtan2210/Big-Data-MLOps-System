import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Config
st.set_page_config(page_title="System Health Dashboard", page_icon="📊", layout="wide")
API_BASE_URL = "http://localhost:8001"

def fetch_data(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi kết nối tới {endpoint}: {e}")
        return None

st.title("🎛️ Health Data System Dashboard")
st.markdown("Giám sát trạng thái dữ liệu thực từ LanceDB.")

health_data = fetch_data("/health")
quality_data = fetch_data("/quality/report")

if health_data and quality_data:
    st.subheader("1. Tổng quan hệ thống")
    st.info(f"Trạng thái: **{health_data['overall_status']}**")
    st.metric("Số lượng phim (LanceDB)", f"{health_data['movies_count']:,}")

    st.subheader("2. Chi tiết chất lượng dữ liệu")
    st.write(f"Trạng thái Quality: {quality_data['status']}")
    st.write(f"Số chiều Vector: {quality_data['vector_dimension']}")
    st.write(f"Columns: {quality_data['columns']}")
    
    st.divider()
    st.caption(f"Cập nhật: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.warning("Đang kết nối backend...")
