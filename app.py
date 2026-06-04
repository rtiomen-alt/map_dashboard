
import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="WM MAP BI")

st.title("WM MAP BI — WORKING BUILD")

def clean_num(v):
    if pd.isna(v):
        return 0.0
    s = str(v).replace(" ", "").replace(",", ".").strip()
    if s in ["", "-", "nan"]:
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

uploaded = st.sidebar.file_uploader(
    "Загрузить XLSX/CSV",
    type=["xlsx", "xls", "csv"]
)

if uploaded is None:
    st.info("Загрузите файл")
    st.stop()

if uploaded.name.endswith(".csv"):
    df = pd.read_csv(uploaded)
else:
    df = pd.read_excel(uploaded)

df.columns = [str(c).strip() for c in df.columns]

years = sorted(
    list(
        {
            int(y)
            for c in df.columns
            for y in re.findall(r"20\d{2}", str(c))
        }
    )
)

if len(years) == 0:
    st.error("Не найдены годы в колонках")
    st.stop()

current_year = max(years)

clients = df["Наименование"].astype(str).tolist()

selected_client = st.selectbox(
    "Клиент",
    clients
)

row = df[df["Наименование"].astype(str) == selected_client].iloc[0]

sales_data = []
turnover_data = []

for y in years:

    turnover_col = [
        c for c in df.columns
        if f"Оборот {y}" in c
    ]

    sales_col = [
        c for c in df.columns
        if f"Продажи {y}" in c
    ]

    turnover = 0
    sales = 0

    if len(turnover_col) > 0:
        turnover = clean_num(row[turnover_col[0]])

    if len(sales_col) > 0:
        sales = clean_num(row[sales_col[0]])

    sales_data.append({
        "Год": y,
        "Продажи": sales
    })

    turnover_data.append({
        "Год": y,
        "Оборот": turnover
    })

sales_df = pd.DataFrame(sales_data)
turnover_df = pd.DataFrame(turnover_data)

c1, c2 = st.columns(2)

with c1:

    st.subheader("Продажи")

    fig_sales = px.bar(
        sales_df,
        x="Год",
        y="Продажи",
        text="Продажи"
    )

    fig_sales.update_layout(height=400)

    st.plotly_chart(
        fig_sales,
        use_container_width=True,
        key="sales_chart"
    )

with c2:

    st.subheader("Оборот")

    fig_turnover = px.bar(
        turnover_df,
        x="Год",
        y="Оборот",
        text="Оборот"
    )

    fig_turnover.update_layout(height=400)

    st.plotly_chart(
        fig_turnover,
        use_container_width=True,
        key="turnover_chart"
    )

st.subheader("Исходные данные клиента")

st.dataframe(
    row.to_frame(),
    use_container_width=True
)
