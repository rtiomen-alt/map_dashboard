
import streamlit as st
import pandas as pd
import re

st.set_page_config(layout="wide", page_title="WM MAP BI v63.2")

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

current_year = max(years)

for y in years:

    sales_col = [
        c for c in df.columns
        if f"Продажи {y}" in c and "без НДС" in c
    ]

    if len(sales_col) > 0:
        df[f"sales_{y}"] = df[sales_col[0]].apply(clean_num)
    else:
        df[f"sales_{y}"] = 0

def calc_status(row):

    current_sales = row[f"sales_{current_year}"]

    total_sales = sum(
        row[f"sales_{y}"]
        for y in years
    )

    if current_sales > 0:
        return "Активный"

    if total_sales == 0:
        return "Потенциальный"

    return "Неактивный"

df["Статус"] = df.apply(calc_status, axis=1)

statuses = [
    "Активный",
    "Неактивный",
    "Потенциальный"
]

selected_statuses = st.sidebar.multiselect(
    "Статус клиента",
    statuses,
    default=statuses
)

filtered = df[
    df["Статус"].isin(selected_statuses)
]

if len(filtered) == 0:
    st.warning("Нет данных")
    st.stop()

clients = filtered["Наименование"].astype(str).tolist()

selected_client = st.selectbox(
    "Клиент",
    clients
)

row = filtered[
    filtered["Наименование"].astype(str) == selected_client
].iloc[0]

st.subheader(selected_client)

c1, c2 = st.columns(2)

c1.metric(
    "Статус",
    row["Статус"]
)

c2.metric(
    "Последний год",
    current_year
)

st.success("WM MAP BI v63.2 STATUS PATCH")
