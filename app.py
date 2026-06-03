
import streamlit as st
import pandas as pd
import numpy as np
import re

st.set_page_config(page_title="Client Analytics Dashboard", layout="wide")

GIANTS = {
    "7705034202",
    "7701215046",
    "4725001168",
    "7729101200"
}

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)

    df.columns = [c.strip() for c in df.columns]

    def clean_num(x):
        if pd.isna(x):
            return 0
        x = str(x).replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
        if x in ["-", "", "nan"]:
            return 0
        try:
            return float(x)
        except:
            return 0

    df["ИНН"] = (
        df["ИНН"]
        .astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )

    years = [2022, 2023, 2024, 2025]

    for y in years:
        turnover_col = [c for c in df.columns if f"Оборот {y}, долл" in c][0]
        sales_col = [c for c in df.columns if f"Продажи {y} без НДС" in c][0]
        potential_col = [c for c in df.columns if f"Потенциал по ароме {y}" in c][0]

        df[f"turnover_{y}"] = df[turnover_col].apply(clean_num)
        df[f"sales_{y}"] = df[sales_col].apply(clean_num)
        df[f"potential_{y}"] = df[potential_col].apply(clean_num)

        df[f"kup_{y}"] = np.where(
            df[f"sales_{y}"] > 0,
            (df[f"potential_{y}"] / df[f"sales_{y}"]) * 100,
            0
        )

    current_year = max(years)

    df["category"] = ""

    df.loc[df["ИНН"].isin(GIANTS), "category"] = "Гигант"

    regular = df[~df["ИНН"].isin(GIANTS)].copy()
    regular = regular.sort_values(f"turnover_{current_year}", ascending=False)

    total_turnover = regular[f"turnover_{current_year}"].sum()
    regular["cum_share"] = regular[f"turnover_{current_year}"].cumsum() / total_turnover

    regular["category"] = np.select(
        [
            regular["cum_share"] <= 0.80,
            regular["cum_share"] <= 0.95
        ],
        ["A", "Б"],
        default="В"
    )

    df.loc[regular.index, "category"] = regular["category"]

    rank_year = current_year - 1
    df["rank"] = (
        df[f"sales_{rank_year}"]
        .rank(method="min", ascending=False)
        .fillna(0)
        .astype(int)
    )

    return df

st.title("Client Analytics Dashboard MVP")

uploaded = st.file_uploader("Загрузить CSV", type=["csv"])

if uploaded:
    df = load_data(uploaded)

    managers = sorted(df["Менеджер"].dropna().astype(str).unique())

    col1, col2, col3 = st.columns(3)

    with col1:
        category_filter = st.multiselect(
            "Категория",
            options=["Гигант", "A", "Б", "В"],
            default=["Гигант", "A", "Б", "В"]
        )

    with col2:
        manager_filter = st.multiselect(
            "Менеджер",
            options=managers,
            default=managers
        )

    with col3:
        search = st.text_input("Поиск клиента")

    filtered = df[
        (df["category"].isin(category_filter)) &
        (df["Менеджер"].astype(str).isin(manager_filter))
    ]

    if search:
        filtered = filtered[
            filtered["Наименование"].str.contains(search, case=False, na=False)
        ]

    st.subheader("KPI")

    k1, k2, k3, k4 = st.columns(4)

    current_year = 2025

    total_turnover = filtered[f"turnover_{current_year}"].sum()
    total_sales = filtered[f"sales_{current_year}"].sum()

    prev_turnover = filtered[f"turnover_{current_year-1}"].sum()
    prev_sales = filtered[f"sales_{current_year-1}"].sum()

    turnover_growth = (
        ((total_turnover - prev_turnover) / prev_turnover) * 100
        if prev_turnover > 0 else 0
    )

    sales_growth = (
        ((total_sales - prev_sales) / prev_sales) * 100
        if prev_sales > 0 else 0
    )

    with k1:
        st.metric(
            "Оборот 2025 ($)",
            f"{total_turnover:,.0f}"
        )

    with k2:
        st.metric(
            "Продажи 2025 без НДС ($)",
            f"{total_sales:,.0f}"
        )

    with k3:
        st.metric(
            "Рост оборота YoY",
            f"{turnover_growth:.1f}%"
        )

    with k4:
        st.metric(
            "Рост продаж YoY",
            f"{sales_growth:.1f}%"
        )

    st.subheader("Клиенты")

    table = filtered[[
        "ИНН",
        "Наименование",
        "Менеджер",
        "category",
        "rank"
    ]].copy()

    table["Место"] = "ТОП-" + table["rank"].astype(str)

    st.dataframe(
        table.rename(columns={
            "category": "Категория"
        }),
        use_container_width=True
    )

    st.subheader("Карточка клиента")

    selected = st.selectbox(
        "Выбери клиента",
        filtered["Наименование"].tolist()
    )

    if selected:
        client = filtered[filtered["Наименование"] == selected].iloc[0]

        st.markdown(f"## {client['Наименование']}")
        st.markdown(f"**ИНН:** {client['ИНН']}")
        st.markdown(f"**Менеджер:** {client['Менеджер']}")
        st.markdown(f"**Категория:** {client['category']}")
        st.markdown(f"**Место:** ТОП-{client['rank']}")

        years = [2022, 2023, 2024, 2025]

        rows = []

        for y in years:
            turnover = client[f"turnover_{y}"]
            sales = client[f"sales_{y}"]
            kup = client[f"kup_{y}"]

            prev_turnover = client.get(f"turnover_{y-1}", 0)
            prev_sales = client.get(f"sales_{y-1}", 0)

            turnover_yoy = (
                ((turnover - prev_turnover) / prev_turnover) * 100
                if prev_turnover > 0 else 0
            )

            sales_yoy = (
                ((sales - prev_sales) / prev_sales) * 100
                if prev_sales > 0 else 0
            )

            rows.append({
                "Год": y,
                "Оборот $": round(turnover, 0),
                "Рост оборота %": round(turnover_yoy, 1),
                "Продажи без НДС $": round(sales, 0),
                "Рост продаж %": round(sales_yoy, 1),
                "КУП %": round(kup, 1)
            })

        result = pd.DataFrame(rows)

        def color_growth(v):
            try:
                v = float(v)
            except:
                return ""
            color = "green" if v > 0 else "red" if v < 0 else "black"
            return f"color: {color}"

        styled = result.style.map(
            color_growth,
            subset=["Рост оборота %", "Рост продаж %"]
        )

        st.dataframe(styled, use_container_width=True)

        chart_df = result.set_index("Год")[["Оборот $", "Продажи без НДС $"]]
        st.line_chart(chart_df)
