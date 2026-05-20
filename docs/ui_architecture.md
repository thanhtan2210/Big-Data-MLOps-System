# User Interface Architecture (Streamlit UI)

The user interface of the system is centralized in a single file `app.py`, divided into two independent experiences but operated jointly on **Hugging Face Spaces**.

## 1. Analytics Dashboard
To provide deep insights into the MovieLens 25M dataset, the interface integrates 5 analytics tabs using the Plotly library:
1. **Overview**: KPI metrics, hourly viewing Heatmaps, and hierarchical genre Treemaps.
2. **Movie Quality**: Top 20 best movies, decade trend analysis, and rating distribution Boxplots.
3. **User Behavior**: User segmentation charts (Casual vs. Power User), Rating Bias indicators, and Collaborative Signals.
4. **Tag & Genome**: Bubble charts of popular tags, and Top Genome Tags simulating the AI's semantic understanding.
5. **MLOps Metrics**: Gauge charts displaying Recall@10, NDCG@10, system latency, and R2 data synchronization status.

**RAM Optimization**: Since the Hugging Face Free Tier is limited to approximately 16GB RAM, the UI applies Capped Streaming techniques, loading a maximum random sample of 500,000 `ratings.csv` rows from R2.

## 2. AI Movie Concierge (Conversational Agent)
1. **Pseudo-Tower Personalization**: A Multiselect Box allows users to type in the names of their favorite movies to construct an initial Vector Profile. Python automatically reverse maps the movie names to their IDs for calculation.
2. **Chat Interface**: A conversational box allowing users to interact freely. The interface automatically maintains message history in `st.session_state` and passes it to `chatbot.chat()`.
3. **Movie Cards**: Recommended results from the AI or Vector Search are displayed as a visually appealing grid of Poster images with scores, fetched via the TMDB API.