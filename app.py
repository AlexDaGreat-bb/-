import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="서울 기온 분석",
    page_icon="🌡️",
    layout="wide",
)

# ---------- 테마: 머스타드 옐로우 + 청록색 ----------
MUSTARD = "#F0C674"
TURQ = "#008080"
STROKE = "#333333"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: #FFF8E1;
    }}
    .sidebar .sidebar-content {{
        background-color: #FFF8E1;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- 데이터 로드 ----------
@st.cache_data
def load_data(content: str) -> pd.DataFrame:
    from io import StringIO
    df = pd.read_csv(
        StringIO(content),
        dtype={"날짜": str},
        on_bad_lines="skip",
    )
    # 날짜 값 앞의 탭 문자 등 공백 제거
    df["날짜"] = df["날짜"].str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"], format="%Y-%m-%d")
    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["연도"] = df["날짜"].dt.year
    return df

# ---------- 파일 읽기 ----------
uploaded = st.file_uploader(
    "CSV 파일 업로드",
    type="csv",
    help="파일을 올리지 않으면 같은 폴더의 seoul_temperature.csv를 자동 사용합니다.",
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
    st.warning(
        "CSV 파일이 없습니다. Streamlit Cloud에서는 파일 업로드 기능을 사용하거나, "
        "로컬 실행 시 seoul_temperature.csv를 앱 파일과 같은 폴더에 넣어 주세요."
    )
    st.stop()

TEMP_COLS = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]

# ---------- 연도별 결측치 집계 (결측 셀 기준: 온도 3개 컬럼의 빈칸 수) ----------
raw_year_min = int(df["연도"].min())
raw_year_max = int(df["연도"].max())
missing_cells_per_year = (
    df.groupby("연도")[TEMP_COLS]
    .isnull()
    .sum()
    .sum(axis=1)
)

# 결측치 20개 이상인 연도는 분석·그래프에서 제외
excluded_years = missing_cells_per_year[missing_cells_per_year >= 20]
valid_years = missing_cells_per_year[missing_cells_per_year < 20]
df = df[df["연도"].isin(valid_years.index)]

# ---------- 연평균 & 5년 이동평균 ----------
annual = (
    df.groupby("연도")[TEMP_COLS]
    .mean()
    .reset_index()
    .sort_values("연도")
)
annual["5년이동평균"] = annual["평균기온(℃)"].rolling(window=5, min_periods=1).mean()

# ---------- 데이터 진단 (사이드바에서 확인 가능) ----------
with st.sidebar.expander("📦 데이터 진단"):
    st.write(f"원본 데이터 행 수: {len(df)}")
    st.write(f"연도 범위: {raw_year_min}~{raw_year_max}년")
    st.write("연도별 행 수:")
    st.write(df.groupby("연도").size().to_dict())
    st.write("연도별 결측(셀) 수:")
    st.write(missing_cells_per_year.to_dict())
    st.write("제외된 연도(결측 20개 이상):", excluded_years.index.tolist())
    st.write("분석 대상 연도:", sorted(valid_years.index.tolist()))
    st.write("분석 대상 연도 목록:")
    st.write(annual[["연도", "평균기온(℃)", "5년이동평균"]])

# ---------- 연도 범위 ----------
year_min = int(annual["연도"].min())
year_max = int(annual["연도"].max())
year_range = st.sidebar.slider(
    "연도 범위",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
    key="year_range",
    help="그래프를 볼 연도 범위를 선택하세요.",
)

# ---------- 전체 연도로 초기화 ----------
if st.sidebar.button("전체 연도로 되돌리기", key="reset_year"):
    st.session_state["year_range"] = (year_min, year_max)

# ---------- 선택 구간 통계 ----------
sel = annual[
    (annual["연도"] >= year_range[0]) & (annual["연도"] <= year_range[1])
]
metrics = {
    "평균기온": sel["평균기온(℃)"].mean(),
    "최저기온": sel["최저기온(℃)"].mean(),
    "최고기온": sel["최고기온(℃)"].mean(),
}

# ---------- 본문 ----------
st.title("서울 연평균기온 분석")
st.markdown(
    f"데이터: {len(df)}개 관측치 | 분석 대상 연도: {year_min}~{year_max}년 | "
    f"제외 연도(결측 20개 이상): {excluded_years.index.tolist() if len(excluded_years) else '없음'}"
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
    fig.update_layout(
        title="연도별 평균기온 및 5년 이동평균",
        xaxis_title="연도",
        yaxis_title="평균기온 (℃)",
        hovermode="x unified",
        paper_bgcolor="#FFF8E1",
        plot_bgcolor="#FFF8E1",
        font=dict(
            family="Malgun Gothic, Apple SD Gothic Neo, NanumGothic, sans-serif",
            size=12,
        ),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("### 📊 선택 구간 통계")
    st.markdown("| 항목 | 값 (℃) |", unsafe_allow_html=True)
    for k, v in metrics.items():
        st.markdown(f"| {k} | {v:,.1f} |", unsafe_allow_html=True)
    st.markdown(f"**선택 연도 수**: {len(sel)}년")
    if len(excluded_years):
        st.warning(f"결측치 20개 이상 연도 → 분석에서 제외: {excluded_years.index.tolist()}")

# ---------- 상세 데이터 표 ----------
st.markdown("### 📋 연도별 상세 데이터")
st.dataframe(annual, use_container_width=True)
