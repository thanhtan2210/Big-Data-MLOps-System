import streamlit as st
import pandas as pd
import os
import shutil
import lancedb
import boto3
from src.serving.chatbot import MovieChatbot
from src.serving.semantic_search import SemanticSearchEngine

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="AI Movie Concierge (Cloud)",
    page_icon="🍿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. DOWNLOAD LANCEDB FROM CLOUDFLARE R2
# ==========================================
@st.cache_resource
def init_lancedb():
    """Download LanceDB index from Cloudflare R2 on startup."""
    db_path = "lancedb_movies"
    zip_path = "lancedb_movies.zip"
    
    if not os.path.exists(db_path):
        st.info("Đang tải Vector Database từ Cloudflare R2. Vui lòng đợi khoảng 5 giây...")
        s3 = boto3.client('s3',
            endpoint_url=os.environ.get('AWS_ENDPOINT_URL'),
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
        
        # Tải 1 file ZIP duy nhất
        s3.download_file(bucket, zip_path, zip_path)
        # Giải nén
        shutil.unpack_archive(zip_path, db_path)
        # Dọn dẹp file zip để tiết kiệm RAM/Disk
        os.remove(zip_path)
        
    engine = SemanticSearchEngine(lancedb_uri=db_path)
    engine.load_table()
    return engine

@st.cache_resource
def init_chatbot():
    return MovieChatbot()

try:
    engine = init_lancedb()
except Exception as e:
    st.warning(f"Không thể kết nối R2 hoặc LanceDB: {e}")
    engine = None

try:
    chatbot = init_chatbot()
except Exception as e:
    st.error(f"Lỗi khởi tạo Chatbot: {e}")
    chatbot = None

# ==========================================
# 3. TMDB INTEGRATION
# ==========================================
def get_movie_poster(poster_path):
    if not poster_path or pd.isna(poster_path):
        return "https://via.placeholder.com/300x450"
    return f"https://image.tmdb.org/t/p/w300{poster_path}"

def display_recommendations(recommendations):
    cols = st.columns(5)
    for i, rec in enumerate(recommendations[:5]):
        with cols[i % 5]:
            st.image(get_movie_poster(rec.get('poster_path', '')))
            vote = rec.get('vote_average', 0.0)
            st.caption(f"⭐ {vote:.1f}" if vote else "⭐ N/A")
            st.write(rec.get('title', 'Unknown'))

# ==========================================
# 4. UI MODULES
# ==========================================
def render_home():
    st.title("🎬 AI Movie Concierge (Cloud Version)")
    st.markdown("""
    ### Hybrid Architecture Demo
    Hệ thống gợi ý phim ứng dụng công nghệ Cloud-native:
    
    *   **Tracking:** DagsHub (MLflow)
    *   **Storage:** Cloudflare R2
    *   **Serving:** Hugging Face Spaces (Streamlit + BentoML)
    *   **Vector Search:** LanceDB
    *   **Metadata:** TMDB API Real-time
    """)
    st.image("https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80")

def render_concierge():
    st.title("💬 AI Movie Concierge")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
        
    st.subheader("🌟 Gợi Ý Cá Nhân Hóa")
    if not st.session_state.recommendations:
        st.info("Sử dụng User ID ở sidebar để lấy gợi ý thực tế.")
    else:
        display_recommendations(st.session_state.recommendations)

    st.divider()

    st.subheader("Chat với AI")
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Hỏi về phim (VD: Tìm phim khoa học viễn tưởng hay nhất)..."):
        with chat_container:
            st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        try:
            # Truyền history xuống chatbot (bỏ tin nhắn hiện tại vừa add)
            bot_reply = chatbot.chat(prompt, history=st.session_state.messages[:-1])
        except Exception as e:
            bot_reply = f"Xin lỗi, có lỗi xảy ra: {e}"

        with chat_container:
            st.chat_message("assistant").markdown(bot_reply)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

# ==========================================
# 5. SIDEBAR & NAVIGATION
# ==========================================
with st.sidebar:
    st.title("🎬 Cloud MLOps")
    mode = st.radio("Chế độ", ["🏠 Trang chủ", "🎬 Movie Concierge"])
    st.markdown("---")
    
    if mode == "🎬 Movie Concierge":
        movie_id_input = st.text_input("Movie ID để lấy gợi ý (Content-based)", "1")
        if st.button("Lấy gợi ý"):
            try:
                if engine and engine.table is not None:
                    # Truy vấn trực tiếp từ LanceDB engine cục bộ
                    st.session_state.recommendations = engine.search_similar_movies(int(movie_id_input), top_k=5)
                    st.rerun()
                else:
                    st.error("LanceDB chưa sẵn sàng.")
            except Exception as e:
                st.error(f"Lỗi: {e}")

if mode == "🏠 Trang chủ":
    render_home()
elif mode == "🎬 Movie Concierge":
    render_concierge()
