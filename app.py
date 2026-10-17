import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="서울 기온 분석",
    page_icon="🌡️",
    layout="wide",
)

MUSTARD = "#F0C674"
TURQ = "#008080"
BG = "#FFF8E1"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {BG}; }}
    .sidebar .sidebar-content {{ background-color: {BG}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- 데이터 로드 ----------
@st.cache_data
def load_data(content: str) -> pd.DataFrame:
    from io import StringIO
    df = pd.read_csv(StringIO(content), dtype={"날짜": str}, on_bad_lines="skip")
    df["날짜"] = df["날짜"].str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["날짜"])
    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["연도"] = df["날짜"].dt.year
    return df

# ---------- 파일 읽기 ----------
uploaded = st.file_uploader(
    "CSV 파일 업로드",
    type="csv",
    help="파일 미선택 시 같은 폴더의 seoul_temperature.csv를 자동으로 사용합니다.",
)

if uploaded is not None:
    raw = uploaded.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("cp949")
    df = load_data(content)
elif os.path.exists("seoul_temperature.csv"):
    with open("seoul_temperature.csv", "rb") as f:
        raw = f.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("cp949")
    df = load_data(content)
else:
    st.warning("CSV 파일이 없습니다. Streamlit Cloud에서는 파일을 업로드하거나, 로컬에서는 seoul_temperature.csv를 앱과 같은 폴더에 두세요.")
    st.stop()

if df.empty:
    st.warning("CSV에 데이터가 없습니다. 파일 내용을 확인해 주세요.")
    st.stop()

TEMP_COLS = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]

# ---------- 결측치 집계 ----------
# 연도별로 온도 3개 컬럼 중 하나라도 결측인 행 수를 집계
missing_per_year = df[df[TEMP_COLS].isnull().any(axis=1)].groupby("연도").size()

# 결측치 20개 이상인 연도는 제외
excluded_years = missing_per_year[missing_per_year >= 20].index.tolist()
valid_years = missing_per_year[missing_per_year < 20].index.tolist()
df = df[df["연도"].isin(valid_years)]

if df.empty:
    st.warning("결측치 제외 후 남은 데이터가 없습니다.")
    st.stop()

# ---------- 연평균 & 5년 이동평균 ----------
annual = df.groupby("연도")[TEMP_COLS].mean().reset_index().sort_values("연도")
annual["5년이동평균"] = annual["평균기온(℃)"].rolling(window=5, min_periods=1).mean()

year_min = int(annual["연도"].min())
year_max = int(annual["연도"].max())

# ---------- 진단 정보 (어떤 연도가 남았는지 확인하기 위한 표시) ----------
st.caption(
    f"전체 관측치: {len(df)}개 | 분석 연도: {year_min}~{year_max}년 | "
    f"분석 연도 목록: {', '.join(str(y) for y in annual['연도'].tolist())} | "
    f"제외 연도(결측 20일 이상): {excluded_years if excluded_years else '없음'}"
)

# ---------- 사이드바 ----------
st.sidebar.title("🌡️ 서울 기온 분석")
st.sidebar.markdown("---")
st.sidebar.markdown("**분석 대상 연도**")
year_range = st.sidebar.slider(
    "연도 범위",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
    step=1,
)

# ---------- 선택 구간 통계 ----------
sel = annual[(annual["연도"] >= year_range[0]) & (annual["연도"] <= year_range[1])]
metrics = {
    "평균기온": sel["평균기온(℃)"].mean(),
    "최저기온": sel["최저기온(℃)"].mean(),
    "최고기온": sel["최고기온(℃)"].mean(),
}

# ---------- 본문 ----------
st.title("서울 연평균기온 분석")
st.markdown(
    f"데이터: {len(df)}개 관측치 | 분석 대상 연도: {year_min}~{year_max}년 | "
    f"제외 연도(결측 20일 이상): {excluded_years if excluded_years else '없음'}"
)

c1, c2 = st.columns([3, 1])

with c1:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=annual["연도"],
            y=annual["평균기온(℃)"],
            mode="lines+markers",
            name="연평균기온",
            line=dict(color=TURQ, width=2.5),
            marker=dict(color=TURQ, size=6),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=annual["연도"],
            y=annual["5년이동평균"],
            mode="lines",
            name="5년 이동평균",
            line=dict(color=MUSTARD, width=3, dash="dash"),
        )
    )
    # 선택 구간을 반투명하게 표시 (슬라이드바 동작 확인용)
    fig.add_vrect(
        x0=year_range[0],
        x1=year_range[1],
        fillcolor="#FFF8E1",
        opacity=0.5,
        line_width=0,
        layer="below",
        name="선택 구간",
    )
    fig.update_layout(
        title="연도별 평균기온 및 5년 이동평균",
        xaxis_title="연도",
        yaxis_title="평균기온 (℃)",
        hovermode="x unified",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(
            family="Malgun Gothic, Apple SD Gothic Neo, NanumGothic, sans-serif",
            size=12,
        ),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("### 📊 선택 구간 통계")
    st.markdown("| 항목 | 값 (℃) |", unsafe_allow_html=True)
    for k, v in metrics.items():
        st.markdown(f"| {k} | {v:,.1f} |", unsafe_allow_html=True)
    st.markdown(f"**선택 연도 수**: {len(sel)}년")
    if excluded_years:
        st.warning(f"결측치 20개 이상 연도 → 제외: {excluded_years}")

# ---------- 상세 데이터 표 ----------
st.markdown("### 📋 연도별 상세 데이터")
st.dataframe(annual, use_container_width=True)
