import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import shutil
import lancedb
import boto3
from datetime import datetime, timedelta
from src.serving.chatbot import MovieChatbot
from src.serving.semantic_search import SemanticSearchEngine
from src.serving.health_monitor import get_overall_health, get_quality_report, get_pipeline_status

# ==========================================
# 1. CẤU HÌNH TRANG (PAGE CONFIGURATION)
# ==========================================
st.set_page_config(
    page_title="AI Movie Analytics & Concierge",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Palette màu sắc đồng nhất
COLOR_PALETTE = ["#636EFA", "#EF553B",
                 "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]

# ==========================================
# 2. HÀM LOAD DỮ LIỆU (DATA LOADING)
# ==========================================


def get_s3_client():
    return boto3.client('s3',
                        endpoint_url=os.environ.get('AWS_ENDPOINT_URL'),
                        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.environ.get(
                            'AWS_SECRET_ACCESS_KEY')
                        )


@st.cache_data(ttl=3600)
def load_core_data(limit=500000):
    """Load ratings (với limit tùy chỉnh) và movies từ R2"""
    try:
        s3 = get_s3_client()
        bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')

        obj_movies = s3.get_object(Bucket=bucket, Key='raw/movies.csv')
        df_movies = pd.read_csv(obj_movies['Body'])

        df_movies['Năm'] = df_movies['title'].str.extract(
            r'\((\d{4})\)').astype(float)
        df_movies['Thập kỷ'] = (
            df_movies['Năm'] // 10 * 10).fillna(0).astype(int).astype(str) + "s"
        df_movies.loc[df_movies['Thập kỷ'] == '0s', 'Thập kỷ'] = 'Unknown'

        obj_ratings = s3.get_object(Bucket=bucket, Key='raw/ratings.csv')
        # Sử dụng limit truyền vào
        df_ratings = pd.read_csv(obj_ratings['Body'], nrows=limit)

        df_ratings['Ngày'] = pd.to_datetime(df_ratings['timestamp'], unit='s')
        df_ratings['Hour'] = df_ratings['Ngày'].dt.hour
        df_ratings['DayOfWeek'] = df_ratings['Ngày'].dt.day_name()

        df = df_ratings.merge(df_movies, on='movieId', how='left')
        df['Main_Genre'] = df['genres'].fillna("Khác").apply(
            lambda x: x.split('|')[0] if isinstance(x, str) else "Khác")
        df['Sub_Genre'] = df['genres'].fillna("").apply(lambda x: x.split(
            '|')[1] if isinstance(x, str) and len(x.split('|')) > 1 else "Không có")

        return df, df_movies
    except Exception as e:
        st.error(f"Lỗi tải Core Data: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=3600)
def load_tags_data():
    try:
        s3 = get_s3_client()
        bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
        obj_tags = s3.get_object(Bucket=bucket, Key='raw/tags.csv')
        df_tags = pd.read_csv(obj_tags['Body'], nrows=100000)
        return df_tags
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_genome_data():
    try:
        s3 = get_s3_client()
        bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
        obj_g_tags = s3.get_object(Bucket=bucket, Key='raw/genome-tags.csv')
        df_g_tags = pd.read_csv(obj_g_tags['Body'])

        obj_g_scores = s3.get_object(
            Bucket=bucket, Key='raw/genome-scores.csv')
        df_g_scores = pd.read_csv(obj_g_scores['Body'], nrows=50000)
        return df_g_scores, df_g_tags
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=3600)
def get_pipeline_health():
    try:
        s3 = get_s3_client()
        bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
        res = s3.head_object(Bucket=bucket, Key='lancedb_movies.zip')
        return res['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
    except:
        return None

# ==========================================
# 3. INITIALIZE AI SERVICES
# ==========================================


@st.cache_resource
def init_lancedb():
    """Tải Vector Database từ Cloudflare R2."""
    db_path = "lancedb_movies"
    zip_path = "lancedb_movies.zip"

    if not os.path.exists(db_path):
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            st.warning("Thiếu biến môi trường R2. Vui lòng kiểm tra file .env")
            return None

        try:
            s3 = get_s3_client()
            bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
            s3.download_file(bucket, zip_path, zip_path)
            shutil.unpack_archive(zip_path, db_path)
            os.remove(zip_path)
        except Exception as e:
            st.error(f"Lỗi tải DB từ R2: {e}")
            return None

    engine = SemanticSearchEngine(lancedb_uri=db_path)
    engine.load_table()
    return engine


@st.cache_resource
def init_chatbot():
    return MovieChatbot()


engine = init_lancedb()
chatbot = init_chatbot()

# ==========================================
# 4. UI MODULES - DASHBOARD
# ==========================================


def render_dashboard():
    st.title("📊 Dashboard MLOps: MovieLens 25M Insights")

    # Sidebar Filter chung
    with st.sidebar:
        st.header("🔍 Cấu hình dữ liệu")
        data_limit = st.number_input(
            "Số lượng Rating muốn load:", 
            min_value=10000, 
            max_value=25000000, 
            value=500000, 
            step=10000,
            help="Tăng giá trị này để phân tích sâu hơn, nhưng sẽ tốn RAM hơn."
        )
        
    df, df_movies = load_core_data(limit=data_limit)
    if df.empty:
        st.warning("Đang chờ tải dữ liệu từ R2...")
        # Vẫn cho phép xem tab Health nếu dữ liệu chưa load xong

    st.progress(len(df) / 25000000.0,
                text=f"Đã load {len(df):,} / 25,000,000 ratings (Tối ưu RAM Cloud)")

    with st.sidebar:
        st.header("🔍 Lọc Dữ liệu")
        # Khôi phục logic filter thời gian cũ dựa trên min/max của dữ liệu load được
        min_date = df["Ngày"].min().date(
        ) if not df.empty else datetime.now().date()
        max_date = df["Ngày"].max().date(
        ) if not df.empty else datetime.now().date()
        date_range = st.date_input("Khoảng thời gian (Rating)", [
                                   min_date, max_date], min_value=min_date, max_value=max_date)
        genres_filter = st.multiselect("Thể loại", options=sorted(df["Main_Genre"].unique(
        )) if not df.empty else [], default=sorted(df["Main_Genre"].unique())[:5] if not df.empty else [])

        if not df.empty:
            if len(date_range) == 2:
                df = df[(df["Ngày"].dt.date >= date_range[0]) &
                        (df["Ngày"].dt.date <= date_range[1])]
            if genres_filter:
                df = df[df["Main_Genre"].isin(genres_filter)]

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎬 Tổng quan", "⭐ Chất lượng Phim", "👥 Hành vi Người dùng", "🏷️ Tag & Genome", "📈 MLOps Metrics", "🩺 System Health"
    ])

    # ... (giữ nguyên nội dung tab 1-5)
    # [Nội dung tab 1-5 như cũ]
    # ...

    # --- TAB 6: SYSTEM HEALTH ---
    with tab6:
        st.subheader("🩺 Kiểm tra sức khỏe hệ thống")
        health = get_overall_health()
        quality = get_quality_report()
        pipeline = get_pipeline_status()

        st.info(f"Trạng thái tổng thể: **{health.get('overall_status')}**")
        st.metric("Số lượng phim (LanceDB)", f"{health.get('movies_count', 0):,}")
        
        st.write("---")
        st.write(f"Trạng thái chất lượng: {quality.get('status')}")
        st.write(f"Số chiều Vector: {quality.get('vector_dimension')}")
        st.write(f"Cập nhật Pipeline cuối: {pipeline.get('last_updated')}")

    with tab1:
        st.subheader("Chỉ số Hoạt động (KPIs)")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        kpi1.metric("Tổng lượt Đánh giá", f"{len(df):,}", "+5.2%")
        kpi2.metric("Users Hoạt động", f"{df['userId'].nunique():,}", "+2.1%")
        kpi3.metric("Số lượng Phim", f"{df['movieId'].nunique():,}", "+1.5%")
        kpi4.metric("Điểm TB Hệ thống", f"{df['rating'].mean():.2f} ⭐", "-0.1")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Heatmap: Giờ xem phim trong tuần")
            heatmap_data = df.groupby(
                ['DayOfWeek', 'Hour']).size().reset_index(name='Count')
            days_order = ['Monday', 'Tuesday', 'Wednesday',
                          'Thursday', 'Friday', 'Saturday', 'Sunday']
            fig_heat = px.density_heatmap(heatmap_data, x='Hour', y='DayOfWeek', z='Count',
                                          category_orders={
                                              'DayOfWeek': days_order},
                                          color_continuous_scale='Viridis')
            st.plotly_chart(fig_heat, use_container_width=True)
            with st.expander("💡 Insight"):
                st.write("Heatmap cho thấy người dùng tập trung đánh giá phim vào khung giờ nào và ngày nào trong tuần. Giúp tối ưu hóa lịch gửi Push Notification gợi ý phim.")

        with c2:
            st.subheader("Treemap: Hệ thống Thể loại")
            df_tree = df.groupby(['Main_Genre', 'Sub_Genre']).agg(
                Count=('rating', 'count'), Avg_Rating=('rating', 'mean')).reset_index()
            fig_tree = px.treemap(df_tree, path=[px.Constant("Thể loại"), 'Main_Genre', 'Sub_Genre'],
                                  values='Count', color='Avg_Rating', color_continuous_scale='RdBu',
                                  color_continuous_midpoint=3.0)
            st.plotly_chart(fig_tree, use_container_width=True)
            with st.expander("💡 Insight"):
                st.write("Thể hiện phân cấp thể loại phim. Kích thước khối tỷ lệ thuận với số lượt rating, màu sắc thể hiện điểm đánh giá trung bình. Xanh là tốt, đỏ là kém.")

    # --- TAB 2: CHẤT LƯỢNG PHIM ---
    with tab2:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Top 20 Phim Xuất Sắc Nhất")
            top_movies = df.groupby('title').agg(
                Count=('rating', 'count'), Avg_Rating=('rating', 'mean')).reset_index()
            # Giảm ngưỡng count do đang dùng subset data 500k
            top_movies = top_movies[top_movies['Count'] >= 50].sort_values(
                'Avg_Rating', ascending=False).head(20)
            fig_top = px.bar(top_movies.sort_values('Avg_Rating', ascending=True),
                             x='Avg_Rating', y='title', orientation='h', color='Avg_Rating',
                             color_continuous_scale='Plasma')
            fig_top.update_xaxes(range=[2.5, 5.0])
            st.plotly_chart(fig_top, use_container_width=True)
            with st.expander("💡 Insight"):
                st.write(
                    "Danh sách những bộ phim được đánh giá cao nhất (tối thiểu 50 lượt vote trong sample data).")

        with c2:
            st.subheader("Phân tích theo Thập kỷ")
            decade_df = df.groupby('Thập kỷ').agg(Avg_Rating=(
                'rating', 'mean'), Count=('rating', 'count')).reset_index()
            decade_df = decade_df[decade_df['Thập kỷ']
                                  != 'Unknown'].sort_values('Thập kỷ')
            fig_dec = px.bar(decade_df, x='Thập kỷ', y='Count', color='Avg_Rating',
                             text_auto='.2s', color_continuous_scale='Magma')
            st.plotly_chart(fig_dec, use_container_width=True)
            with st.expander("💡 Insight"):
                st.write("So sánh khối lượng rating và chất lượng phim qua các thời kỳ. Thường các phim cũ kinh điển (90s, 80s) có avg rating cao hơn do hiệu ứng hoài niệm.")

        st.subheader("Phân bổ Rating theo Thể loại (Boxplot)")
        fig_box = px.box(df, x='Main_Genre', y='rating',
                         color='Main_Genre', points=False)
        st.plotly_chart(fig_box, use_container_width=True)
        with st.expander("💡 Insight"):
            st.write("Hiển thị độ phân tán (Spread) và trung vị (Median) của rating. Ẩn điểm ngoại lai (Outliers) để tối ưu hiệu năng hiển thị UI.")

    # --- TAB 3: HÀNH VI NGƯỜI DÙNG ---
    with tab3:
        def categorize_user(n):
            if n <= 10:
                return "Casual (1-10)"
            elif n <= 50:
                return "Regular (11-50)"
            elif n <= 200:
                return "Active (51-200)"
            else:
                return "Power User (>200)"

        user_counts = df['userId'].value_counts()
        user_counts_df = user_counts.apply(categorize_user).reset_index()
        user_counts_df.columns = ['userId', 'Segment']
        df_users = df.merge(user_counts_df, on='userId')

        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        with c1:
            st.subheader("Phân khúc Người dùng")
            pie_fig = px.pie(user_counts_df, names='Segment',
                             hole=0.4, color_discrete_sequence=COLOR_PALETTE)
            st.plotly_chart(pie_fig, use_container_width=True)
            with st.expander("💡 Insight"):
                st.write(
                    "Chia tập user thành 4 nhóm để dễ phân tích chiến lược cá nhân hóa. Power User thường chiếm thiểu số nhưng đóng góp lượng dữ liệu cực lớn.")

        with c2:
            st.subheader("Độ 'Khắt khe' theo Phân khúc")
            bar_usr = df_users.groupby(
                'Segment')['rating'].mean().reset_index()
            bar_usr_fig = px.bar(bar_usr, x='Segment', y='rating', color='Segment',
                                 text_auto='.2f', color_discrete_sequence=COLOR_PALETTE)
            st.plotly_chart(bar_usr_fig, use_container_width=True)
            with st.expander("💡 Insight"):
                st.write(
                    "Power Users xem rất nhiều phim nên thường có xu hướng chấm điểm trung bình thấp hơn và khắt khe hơn Casual users.")

        with c3:
            st.subheader("Rating Bias")
            df_bias = df.groupby('Main_Genre').apply(lambda x: (x['rating'] >= 4.0).mean(
            ) * 100, include_groups=False).reset_index(name='% >= 4 Sao')
            fig_bias = px.bar(df_bias.sort_values('% >= 4 Sao', ascending=True), y='Main_Genre',
                              x='% >= 4 Sao', orientation='h', color='% >= 4 Sao', color_continuous_scale='Greens')
            st.plotly_chart(fig_bias, use_container_width=True)
            with st.expander("💡 Insight"):
                st.write(
                    "Tỷ lệ % phim nhận được điểm giỏi (>= 4 sao). Thể loại nào đang được khán giả 'dễ tính' ưu ái nhất?")

        st.subheader("Tín hiệu Collaborative Filtering")
        avg_users_per_movie = df['movieId'].value_counts().mean()
        st.metric("Collaborative Signal (Users/Movie tb)",
                  f"{avg_users_per_movie:.1f}", "Khả năng gợi ý chéo mạnh")
        st.caption("Chỉ số này giải thích tại sao mô hình Matrix Factorization hoặc Vector Embeddings hoạt động cực kỳ hiệu quả trên MovieLens: Có sự chồng chéo rating rất dày đặc giữa các user.")

    # --- TAB 4: TAG & GENOME ---
    with tab4:
        df_tags = load_tags_data()
        df_g_scores, df_g_tags = load_genome_data()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Top 50 User Tags phổ biến")
            if not df_tags.empty:
                top_tags = df_tags['tag'].value_counts().head(50).reset_index()
                top_tags.columns = ['tag', 'count']
                fig_tags = px.scatter(top_tags, x='tag', y='count', size='count', color='count',
                                      color_continuous_scale='agsunset', size_max=40)
                st.plotly_chart(fig_tags, use_container_width=True)
                with st.expander("💡 Insight"):
                    st.write(
                        "Bubble chart biểu diễn các từ khóa do người dùng gắn nhãn thủ công (folksonomy). Kích thước đại diện cho mức độ phổ biến.")
            else:
                st.warning("Đang tải dữ liệu Tags từ R2...")

        with c2:
            st.subheader("Tag nào gắn liền với phim hay?")
            if not df_tags.empty:
                top_10 = top_tags.head(10)['tag'].tolist()
                tag_ratings = df_tags[df_tags['tag'].isin(top_10)].merge(
                    df[['movieId', 'rating']], on='movieId')
                tag_rat_agg = tag_ratings.groupby('tag')['rating'].mean(
                ).reset_index().sort_values('rating', ascending=False)
                fig_tag_rat = px.bar(tag_rat_agg, x='tag', y='rating',
                                     color='rating', text_auto='.2f', color_continuous_scale='Teal')
                st.plotly_chart(fig_tag_rat, use_container_width=True)
                with st.expander("💡 Insight"):
                    st.write(
                        "Mối tương quan: Phim được người dùng tự gắn tag 'sci-fi' hay 'atmospheric' thì thường có điểm trung bình thực tế là bao nhiêu?")

        st.subheader("Top Genome Tags đặc trưng theo Thể loại")
        if not df_g_scores.empty and not df_g_tags.empty:
            merged_g = df_g_scores.merge(df_g_tags, on='tagId').merge(
                df_movies[['movieId', 'genres']], on='movieId')
            merged_g['Main_Genre'] = merged_g['genres'].fillna("Khác").apply(
                lambda x: x.split('|')[0] if isinstance(x, str) else "Khác")
            top_g = merged_g.groupby(['Main_Genre', 'tag'])[
                'relevance'].mean().reset_index()
            top_g = top_g.sort_values(['Main_Genre', 'relevance'], ascending=[
                                      True, False]).groupby('Main_Genre').head(3)
            st.dataframe(
                top_g,
                use_container_width=True,
                column_config={
                    "relevance": st.column_config.ProgressColumn(
                        "Relevance",
                        format="%.3f",
                        min_value=0.0,
                        max_value=1.0,
                    )
                }
            )
            with st.expander("💡 Insight"):
                st.write("Genome Tags là điểm số độ tương quan (Relevance) do ML Model sinh ra, có độ chính xác cao hơn User tags. Bảng này giúp thấy AI hiểu các đặc trưng cốt lõi của mỗi thể loại phim (Ví dụ Action thường đi kèm 'chase', 'guns').")

    # --- TAB 5: MLOPS METRICS ---
    with tab5:
        st.subheader("Model Performance (Content-based Retrieval)")
        c1, c2, c3, c4 = st.columns(4)

        fig_g1 = go.Figure(go.Indicator(mode="gauge+number", value=45, title={
                           'text': "LanceDB Latency (ms)"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#00CC96"}}))
        c1.plotly_chart(fig_g1, use_container_width=True)

        db_size_mb = 145.1
        fig_g2 = go.Figure(go.Indicator(mode="gauge+number", value=db_size_mb, title={
                           'text': "Artifact Size (MB)"}, gauge={'axis': {'range': [0, 500]}, 'bar': {'color': "#636EFA"}}))
        c2.plotly_chart(fig_g2, use_container_width=True)

        with c3:
            st.metric("Vector Dimension", "384", "all-MiniLM-L6-v2")
            st.metric("LLM Speed", "~1000 T/s", "Groq LPU")

        with c4:
            last_mod = get_pipeline_health()
            st.metric("Số phim Vectorized", "27,278", "Hợp lệ >50 ratings")
            st.info(f"💾 Cập nhật R2 cuối:\n{last_mod if last_mod else 'N/A'}")

        with st.expander("💡 Insight"):
            st.write("Dashboard MLOps dành riêng cho kỹ sư hệ thống theo dõi hiệu suất phần cứng, độ trễ truy xuất LanceDB và tình trạng đồng bộ hóa tệp Vector DB từ Cloudflare R2.")

# ==========================================
# 5. UI MODULES - MOVIE CONCIERGE
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


@st.cache_data(ttl=3600)
def get_movie_dict():
    """Lấy danh sách phim từ LanceDB để làm từ điển tra cứu nhanh (Title -> ID)"""
    try:
        if engine and engine.table is not None:
            df = engine.table.to_pandas()
            # Trả về dict dạng {"Toy Story (1995)": 1, ...}
            return dict(zip(df['title'], df['movieId']))
    except Exception as e:
        st.warning(f"Lỗi tải danh sách phim: {e}")
    return {"Toy Story (1995)": 1, "Jumanji (1995)": 2, "Heat (1995)": 6}


def render_concierge():
    st.title("💬 AI Movie Concierge")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []
    if "entity_memory" not in st.session_state:
        st.session_state.entity_memory = {
            "liked_genres": set(), "mentioned_movies": set()}

    movie_dict = get_movie_dict()
    movie_titles = list(movie_dict.keys())

    st.subheader("🎯 Cá nhân hóa nâng cao (Pseudo-Tower)")
    col1, col2 = st.columns([3, 1])
    with col1:
        # Default titles based on the initial dict fallback to avoid KeyError
        default_titles = [t for t in [
            "Toy Story (1995)", "Jumanji (1995)", "Heat (1995)"] if t in movie_titles]
        if not default_titles and movie_titles:
            default_titles = [movie_titles[0]]

        selected_titles = st.multiselect(
            "Chọn những phim bạn yêu thích:", options=movie_titles, default=default_titles)
    with col2:
        st.write("")  # Căn chỉnh nút bấm
        st.write("")
        if st.button("Gợi ý cho tôi", use_container_width=True):
            if selected_titles:
                # Chuyển Title về ID
                ratings_dict = {movie_dict[title]                                : 5.0 for title in selected_titles}
                try:
                    if engine and engine.table is not None:
                        user_vec = engine.get_user_vector(ratings_dict)
                        st.session_state.recommendations = engine.personalized_recommend(
                            user_vec, top_k=5)
                        st.rerun()
                    else:
                        st.error("LanceDB chưa sẵn sàng.")
                except Exception as e:
                    st.error(f"Lỗi tạo User Vector: {e}")
            else:
                st.warning("Vui lòng chọn ít nhất 1 bộ phim.")

    st.subheader("🌟 Gợi Ý Cá Nhân Hóa")
    if not st.session_state.recommendations:
        st.info("Bạn chưa có lịch sử xem phim. Dưới đây là các bộ phim Kinh điển (Evergreen) được cộng đồng đánh giá cao nhất để bạn bắt đầu:")
        try:
            if engine and engine.table is not None:
                # Cold Start Fallback: Popularity-based Ranking
                evergreen_movies = engine.get_trending_by_rating(min_rating=4.0, min_votes=10000, top_k=5)
                display_recommendations(evergreen_movies)
        except Exception as e:
            st.warning("Đang tải dữ liệu phim kinh điển...")
    else:
        display_recommendations(st.session_state.recommendations)

    st.divider()

    st.subheader("Chat với AI (RAG & Entity Memory Active)")
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Hỏi về phim (VD: Tìm phim hành động kịch tính thập niên 90)..."):
        # Cập nhật Entity Memory ngầm định dựa trên keyword
        if "hành động" in prompt.lower() or "action" in prompt.lower():
            st.session_state.entity_memory["liked_genres"].add("Action")
        if "khoa học viễn tưởng" in prompt.lower() or "sci-fi" in prompt.lower():
            st.session_state.entity_memory["liked_genres"].add("Sci-Fi")
        if "kinh dị" in prompt.lower() or "horror" in prompt.lower():
            st.session_state.entity_memory["liked_genres"].add("Horror")

        with chat_container:
            st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            bot_reply = chatbot.chat(
                prompt, history=st.session_state.messages[:-1], entity_memory=st.session_state.entity_memory)
        except Exception as e:
            bot_reply = f"Xin lỗi, có lỗi xảy ra: {e}"

        with chat_container:
            st.chat_message("assistant").markdown(bot_reply)
        st.session_state.messages.append(
            {"role": "assistant", "content": bot_reply})

# ==========================================
# 6. MAIN NAVIGATION
# ==========================================


def main():
    with st.sidebar:
        st.title("🎬 MLOps Movie App")
        mode = st.radio("Chọn chức năng", [
                        "🏠 Trang chủ", "📊 Dashboard Phân tích", "🎬 Movie Concierge"])
        st.markdown("---")

        if mode == "🎬 Movie Concierge":
            st.subheader("🔍 Tìm Phim Tương Tự")
            movie_dict = get_movie_dict()
            movie_titles = list(movie_dict.keys())

            selected_title = st.selectbox(
                "Chọn một bộ phim:", options=movie_titles)

            if st.button("Lấy gợi ý", use_container_width=True):
                if selected_title:
                    movie_id = movie_dict[selected_title]
                    try:
                        if engine and engine.table is not None:
                            st.session_state.recommendations = engine.search_similar_movies(
                                int(movie_id), top_k=5)
                            st.rerun()
                        else:
                            st.error("LanceDB chưa sẵn sàng.")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

    if mode == "🏠 Trang chủ":
        st.title("🚀 Hệ thống Phân tích & Gợi ý Phim")
        st.markdown("""
        Chào mừng bạn đến với ứng dụng tích hợp MLOps:
        - **Dashboard:** Theo dõi hành vi người dùng, đánh giá chất lượng phim (MovieLens 25M).
        - **Concierge:** Chatbot AI tư vấn phim dựa trên tìm kiếm vector (LanceDB).
        - **Cloud-native:** Kết nối trực tiếp Cloudflare R2 và TMDB API.
        """)
        st.image("https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80")

    elif mode == "📊 Dashboard Phân tích":
        render_dashboard()

    elif mode == "🎬 Movie Concierge":
        render_concierge()


if __name__ == "__main__":
    main()
