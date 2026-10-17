import os
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------- 설정 ----------
MUSTARD = "#E1AD01"   # 머스타드 옐로우
TEAL = "#008B8B"      # 청록색
DEEP_TEAL = "#005F5F"
CREAM = "#FFFBEF"
# 이모지(🧦)를 SVG 이미지로 만들어 마우스 커서로 사용
_SOCK_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'>"
    "<text x='0' y='26' font-size='26'>🧦</text></svg>"
)
SOCK_CURSOR = f'url("data:image/svg+xml,{quote(_SOCK_SVG)}") 16 16, pointer'
FONT = "Jua"  # 둥글둥글 귀여운 한글 폰트 (Google Fonts)

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seoul_temperature.csv")
MISSING_LIMIT = 20    # 결측치가 이 개수 이상인 연도는 제외
MA_WINDOW = 5         # 이동평균 기간(년)

COL_DATE, COL_AVG, COL_MIN, COL_MAX = "날짜", "평균기온(℃)", "최저기온(℃)", "최고기온(℃)"

st.set_page_config(page_title="서울 기온 분석", page_icon="🧦", layout="wide")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
    html, body, .stApp, .stMarkdown, p, h1, h2, h3, h4, label, button, input,
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
    [data-testid="stCaptionContainer"], [data-testid="stSlider"] *,
    [data-testid="stExpander"] summary p {{
        font-family: '{FONT}', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif !important;
    }}
    /* 그래프 위에서 커서를 양말 모양으로 */
    [data-testid="stPlotlyChart"],
    [data-testid="stPlotlyChart"] .draglayer *,
    [data-testid="stPlotlyChart"] .nsewdrag,
    [data-testid="stPlotlyChart"] .main-svg {{
        cursor: {SOCK_CURSOR} !important;
    }}
    [data-testid="stSidebar"] {{ background-color: {TEAL}; }}
    [data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
    h1, h2, h3 {{ color: {DEEP_TEAL}; }}
    div[data-testid="stMetric"] {{
        background: {CREAM};
        border-left: 6px solid {MUSTARD};
        border-radius: 8px;
        padding: 12px 16px;
    }}
    div[data-testid="stMetricValue"] {{ color: {TEAL}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- 데이터 로딩 ----------
@st.cache_data
def load_data(source) -> pd.DataFrame:
    df = pd.read_csv(source, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    # 날짜 앞의 탭 문자 제거 후 변환
    df[COL_DATE] = pd.to_datetime(df[COL_DATE].astype(str).str.strip(), errors="coerce")
    df = df.dropna(subset=[COL_DATE]).copy()  # 날짜 없는 빈 행 제거
    df["연도"] = df[COL_DATE].dt.year
    return df


@st.cache_data
def valid_year_table(df: pd.DataFrame):
    """연도별 평균기온(결측 20개 이상 연도 제외) + 5년 이동평균."""
    missing = df.groupby("연도")[COL_AVG].apply(lambda s: s.isna().sum())
    excluded = missing[missing >= MISSING_LIMIT].index.tolist()

    clean = df[~df["연도"].isin(excluded)]
    yearly = clean.groupby("연도")[COL_AVG].mean().rename("연평균기온").to_frame()
    # 제외된 연도는 이미 빠져 있으므로, 남은 연도 기준으로 5년 이동평균 계산
    yearly["5년 이동평균"] = yearly["연평균기온"].rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()
    return clean, yearly, excluded


if os.path.exists(CSV_PATH):
    source = CSV_PATH
else:
    source = st.file_uploader("seoul_temperature.csv 파일을 업로드하세요", type="csv")
    if source is None:
        st.info("앱과 같은 폴더에 CSV 파일을 두거나 직접 업로드해 주세요.")
        st.stop()

raw = load_data(source)
clean, yearly, excluded_years = valid_year_table(raw)

# ---------- 사이드바 ----------
st.sidebar.header("🔧 설정")
y_min, y_max = int(yearly.index.min()), int(yearly.index.max())
start, end = st.sidebar.slider(
    "연도 범위", min_value=y_min, max_value=y_max, value=(y_min, y_max), step=1
)
st.sidebar.caption(
    f"결측치 {MISSING_LIMIT}개 이상인 연도는 제외됩니다."
    + (f"\n\n제외된 연도: {', '.join(map(str, excluded_years))}" if excluded_years else "")
)

# ---------- 본문 ----------
st.title("🧦 서울 연도별 기온 분석")

sel_year = yearly.loc[start:end]
sel_daily = clean[(clean["연도"] >= start) & (clean["연도"] <= end)]

if sel_year.empty or sel_daily.empty:
    st.warning("선택한 구간에 분석 가능한 데이터가 없습니다.")
    st.stop()

# 선택 구간 요약
max_row = sel_daily.loc[sel_daily[COL_MAX].idxmax()]
min_row = sel_daily.loc[sel_daily[COL_MIN].idxmin()]

c1, c2, c3 = st.columns(3)
c1.metric("평균 기온", f"{sel_daily[COL_AVG].mean():.2f} ℃")
c2.metric("최고 기온", f"{max_row[COL_MAX]:.1f} ℃", help=f"{max_row[COL_DATE]:%Y-%m-%d}")
c3.metric("최저 기온", f"{min_row[COL_MIN]:.1f} ℃", help=f"{min_row[COL_DATE]:%Y-%m-%d}")
st.caption(
    f"선택 구간: {start}년 ~ {end}년 (분석 대상 {len(sel_year)}개 연도) · "
    f"최고 {max_row[COL_DATE]:%Y-%m-%d} / 최저 {min_row[COL_DATE]:%Y-%m-%d}"
)

# 그래프
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=sel_year.index, y=sel_year["연평균기온"], mode="lines+markers",
        name="연평균기온", line=dict(color=MUSTARD, width=2.5), marker=dict(size=6),
        hovertemplate="%{x}년: %{y:.2f}℃<extra>연평균</extra>",
    )
)
fig.add_trace(
    go.Scatter(
        x=sel_year.index, y=sel_year["5년 이동평균"], mode="lines",
        name=f"{MA_WINDOW}년 이동평균", line=dict(color=TEAL, width=4),
        hovertemplate="%{x}년: %{y:.2f}℃<extra>5년 이동평균</extra>",
    )
)
fig.update_layout(
    title="연도별 평균기온과 5년 이동평균",
    xaxis_title="연도", yaxis_title="평균기온 (℃)",
    plot_bgcolor=CREAM, paper_bgcolor="white", hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=520,
    font=dict(family=f"{FONT}, Malgun Gothic, sans-serif", size=14),
)
fig.update_xaxes(gridcolor="#EFE6C8")
fig.update_yaxes(gridcolor="#EFE6C8")
st.plotly_chart(fig, use_container_width=True)

with st.expander("📋 연도별 데이터 보기"):
    st.dataframe(sel_year.round(2), use_container_width=True)
