import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="로그 예외 분석 대시보드", layout="wide")

st.title("📊 로그 예외 분석 대시보드")
uploaded_file = st.file_uploader("📂 요약된 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.subheader("1️⃣ 전체 예외 발생 빈도 (Top 10)")
    top_exceptions = df.groupby("exception")["count"].sum().sort_values(ascending=False).head(10)
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    sns.barplot(x=top_exceptions.values, y=top_exceptions.index, palette="Reds_d", ax=ax1)
    ax1.set_xlabel("발생 횟수")
    ax1.set_ylabel("예외 종류")
    st.pyplot(fig1)

    st.subheader("2️⃣ 예외 종류별 전체 비율")
    fig2, ax2 = plt.subplots()
    ax2.pie(top_exceptions.values, labels=top_exceptions.index, autopct="%1.1f%%", startangle=140)
    ax2.axis("equal")
    st.pyplot(fig2)

    st.subheader("3️⃣ 파일별 예외 발생 Heatmap")
    heatmap_data = df.pivot_table(index="filename", columns="exception", values="count", aggfunc="sum", fill_value=0)
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    sns.heatmap(heatmap_data, annot=True, fmt="d", cmap="YlGnBu", ax=ax3)
    st.pyplot(fig3)

    st.subheader("4️⃣ 상세 로그 조회")
    col1, col2 = st.columns(2)
    file_filter = col1.selectbox("파일명 선택", options=["전체"] + sorted(df["filename"].dropna().unique().tolist()))
    exception_filter = col2.selectbox("예외 종류 선택", options=["전체"] + sorted(df["exception"].dropna().unique().tolist()))

    filtered_df = df.copy()
    if file_filter != "전체":
        filtered_df = filtered_df[filtered_df["filename"] == file_filter]
    if exception_filter != "전체":
        filtered_df = filtered_df[filtered_df["exception"] == exception_filter]

    st.dataframe(filtered_df.sort_values(by="count", ascending=False), use_container_width=True)

    st.download_button("📥 필터링된 데이터 다운로드", filtered_df.to_csv(index=False).encode("utf-8-sig"),
                       file_name="filtered_summary.csv", mime="text/csv")

else:
    st.info("좌측 상단에서 요약된 로그 CSV 파일을 업로드하세요.")
