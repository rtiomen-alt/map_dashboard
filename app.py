
# WM MAP BI v6.3 STABLE
# Key fixes:
# 1. Correct aggregate KUP:
#    SUM(sales) / SUM(potential) * 100
# 2. Fixed giant INN matching with trim()
# 3. Separate readable scales for sales/turnover
# 4. Comparable yearly axes
# 5. Improved sales visibility

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

st.set_page_config(page_title="WM MAP BI v6.3", layout="wide")

GIANTS = {
    "4725001168",
    "7705034202",
    "7701215046",
    "7729101200"
}

def clean_num(x):

    if pd.isna(x):
        return 0.0

    s = (
        str(x)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    if s in ["", "-", "nan"]:
        return 0.0

    try:
        return float(s)
    except:
        return 0.0


def fmt_turnover(v):

    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B$"

    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M$"

    if v >= 1_000:
        return f"{v/1_000:.1f}K$"

    return f"{v:.0f}$"


def fmt_sales(v):

    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M$"

    if v >= 1_000:
        return f"{v/1_000:.1f}K$"

    return f"{v:.0f}$"


def detect_years(cols):

    years = set()

    for c in cols:

        found = re.findall(r"20\d{2}", str(c))

        for y in found:
            years.add(int(y))

    return sorted([
        y for y in years
        if 2020 <= y <= 2035
    ])


st.title("WM MAP BI v6.3 STABLE")

uploaded = st.sidebar.file_uploader(
    "Загрузить XLS/XLSX/CSV",
    type=["xls", "xlsx", "csv"]
)

if uploaded:

    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded, encoding="utf-8-sig")
    else:
        df = pd.read_excel(uploaded)

    df.columns = [str(c).strip() for c in df.columns]

    years = detect_years(df.columns)
    current_year = max(years)

    inn_col = "ИНН"
    name_col = "Наименование"

    manager_col = [
        c for c in df.columns
        if "Менеджер" in c
    ][0]

    df["ИНН"] = (
        df[inn_col]
        .astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )

    df["Клиент"] = df[name_col].astype(str)
    df["Менеджер"] = df[manager_col].astype(str)

    for y in years:

        turnover_col = [
            c for c in df.columns
            if (
                f"Оборот {y}" in c
                and "долл" in c.lower()
                and "руб" not in c.lower()
            )
        ][0]

        sales_col = [
            c for c in df.columns
            if (
                f"Продажи {y}" in c
                and "без НДС" in c
            )
        ][0]

        potential_col = [
            c for c in df.columns
            if f"Потенциал по ароме {y}" in c
        ][0]

        df[f"turnover_{y}"] = df[turnover_col].apply(clean_num)
        df[f"sales_{y}"] = df[sales_col].apply(clean_num)
        df[f"potential_{y}"] = df[potential_col].apply(clean_num)

    # Correct KUP logic
    for y in years:

        sales = df[f"sales_{y}"].fillna(0)
        potential = df[f"potential_{y}"].fillna(0)

        df[f"kup_{y}"] = np.where(
            potential > 0,
            (sales / potential) * 100,
            0
        )

    # Categories
    df["Категория"] = ""

    df.loc[
        df["ИНН"].isin(GIANTS),
        "Категория"
    ] = "ГИГАНТ"

    regular = df[
        ~df["ИНН"].isin(GIANTS)
    ].copy()

    regular = regular.sort_values(
        f"turnover_{current_year}",
        ascending=False
    )

    total_turnover = regular[f"turnover_{current_year}"].sum()

    regular["cum"] = (
        regular[f"turnover_{current_year}"].cumsum()
        / total_turnover
    )

    regular["Категория"] = np.select(
        [
            regular["cum"] <= 0.80,
            regular["cum"] <= 0.95
        ],
        ["A", "Б"],
        default="В"
    )

    df.loc[regular.index, "Категория"] = regular["Категория"]

    # Ranking
    ranked = df[
        df[f"sales_{current_year}"] > 0
    ].copy()

    ranked["Место"] = (
        ranked[f"sales_{current_year}"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df["Место"] = None
    df.loc[ranked.index, "Место"] = ranked["Место"]


    # Client statuses
    def calc_status(row):

        current_sales = row[f"sales_{current_year}"]

        total_sales_all = sum(
            row[f"sales_{yy}"]
            for yy in years
        )

        if current_sales > 0:
            return "Активный"

        if total_sales_all == 0:
            return "Потенциальный"

        return "Неактивный"

    df["Статус"] = df.apply(calc_status, axis=1)

    # Filters
    categories = sorted(df["Категория"].unique())

    selected_categories = st.sidebar.multiselect(
        "Категории",
        categories,
        default=categories
    )

    managers = sorted(df["Менеджер"].dropna().unique())

    selected_managers = st.sidebar.multiselect(
        "Менеджеры",
        managers,
        default=managers
    )

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

    mode = st.sidebar.radio(
        "Режим",
        ["Один клиент", "Сводный"]
    )

    filtered = df[
        (df["Категория"].isin(selected_categories))
        &
        (df["Менеджер"].isin(selected_managers))
        &
        (df["Статус"].isin(selected_statuses))
    ]

    if mode == "Один клиент":

        selected_client = st.selectbox(
            "Клиент",
            filtered["Клиент"].tolist()
        )

        filtered = filtered[
            filtered["Клиент"] == selected_client
        ]

    row = filtered.iloc[0]

    # KPI
    total_turnover = filtered[f"turnover_{current_year}"].sum()
    total_sales = filtered[f"sales_{current_year}"].sum()
    total_potential = filtered[f"potential_{current_year}"].sum()

    # FIXED aggregate KUP
    aggregate_kup = (
        (total_sales / total_potential) * 100
        if total_potential > 0
        else 0
    )

    a, b, c, d = st.columns(4)

    a.metric("Оборот", fmt_turnover(total_turnover))
    b.metric("Продажи", fmt_sales(total_sales))
    c.metric("КУП", f"{aggregate_kup:.2f}%")
    d.metric("Клиентов", len(filtered))

    st.divider()

    place = (
        f"ТОП-{int(row['Место'])}"
        if pd.notna(row["Место"])
        else "нет"
    )


    # Last YoY calculations
    prev_year = sorted(years)[-2]

    current_sales = row[f"sales_{current_year}"]
    prev_sales = row[f"sales_{prev_year}"]

    current_turnover = row[f"turnover_{current_year}"]
    prev_turnover = row[f"turnover_{prev_year}"]

    if prev_sales > 0:
        sales_yoy = ((current_sales - prev_sales) / prev_sales) * 100
        sales_yoy_text = f"{sales_yoy:.1f}%"
    else:
        sales_yoy_text = "—"

    if prev_turnover > 0:
        turnover_yoy = ((current_turnover - prev_turnover) / prev_turnover) * 100
        turnover_yoy_text = f"{turnover_yoy:.1f}%"
    else:
        turnover_yoy_text = "—"


    h1, h2, h3, h4, h5, h6, h7 = st.columns(7)

    h1.markdown(f"### {row['Клиент']}")
    h2.markdown(f"**Менеджер:** {row['Менеджер']}")
    h3.markdown(f"**Категория:** {row['Категория']}")
    h4.markdown(f"**Место:** {place}")
    h5.markdown(f"**Статус:** {row['Статус']}")
    h6.markdown(f"**Рост продаж YoY:** {sales_yoy_text}")
    h7.markdown(f"**Рост оборота YoY:** {turnover_yoy_text}")

    st.divider()

    # FIXED COMMON SCALES
    max_sales = max(
        [filtered[f"sales_{y}"].sum() for y in years] + [1]
    )

    max_turnover = max(
        [filtered[f"turnover_{y}"].sum() for y in years] + [1]
    )

    cols = st.columns(len(years))

    prev_sales = None
    prev_turnover = None

    for idx, y in enumerate(years):

        with cols[idx]:

            sales = filtered[f"sales_{y}"].sum()
            turnover = filtered[f"turnover_{y}"].sum()

            potential = filtered[f"potential_{y}"].sum()

            kup = (
                (sales / potential) * 100
                if potential > 0
                else 0
            )

            sales_growth = None
            turnover_growth = None

            if prev_sales and prev_sales > 0:
                sales_growth = (
                    (sales - prev_sales)
                    / prev_sales
                ) * 100

            if prev_turnover and prev_turnover > 0:
                turnover_growth = (
                    (turnover - prev_turnover)
                    / prev_turnover
                ) * 100

            prev_sales = sales
            prev_turnover = turnover

            st.markdown(f"## {y}")

            # SALES CHART
            fig_sales = go.Figure()

            fig_sales.add_bar(
                x=["Продажи"],
                y=[sales],
                marker_color="#16a34a",
                width=[0.7],
                text=[fmt_sales(sales)],
                textposition="outside",
                hovertemplate="%{y:,.0f}$<extra></extra>"
            )

            fig_sales.update_layout(
                height=230,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                paper_bgcolor="white",
                plot_bgcolor="white",
                yaxis=dict(
                    range=[0, max_sales * 1.15],
                    tickformat=",.2s"
                )
            )

            st.plotly_chart(
                fig_sales,
                use_container_width=True,
                key=f"sales_chart_{idx}_{y}"
            )

            # TURNOVER CHART
            fig_turnover = go.Figure()

            fig_turnover.add_bar(
                x=["Оборот"],
                y=[turnover],
                marker_color="#2563eb",
                width=[0.7],
                text=[fmt_turnover(turnover)],
                textposition="outside",
                hovertemplate="%{y:,.0f}$<extra></extra>"
            )

            fig_turnover.update_layout(
                height=230,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                paper_bgcolor="white",
                plot_bgcolor="white",
                yaxis=dict(
                    range=[0, max_turnover * 1.15],
                    tickformat=",.2s"
                )
            )

            st.plotly_chart(
                fig_turnover,
                use_container_width=True,
                key=f"turnover_chart_{idx}_{y}"
            )

            if sales_growth is not None:

                css = (
                    "badge-pos"
                    if sales_growth >= 0
                    else "badge-neg"
                )

                st.markdown(
                    f'<div class="{css}">Продажи: {sales_growth:.1f}%</div>',
                    unsafe_allow_html=True
                )

            if turnover_growth is not None:

                css = (
                    "badge-pos"
                    if turnover_growth >= 0
                    else "badge-neg"
                )

                st.markdown(
                    f'<div class="{css}">Оборот: {turnover_growth:.1f}%</div>',
                    unsafe_allow_html=True
                )

            st.markdown(
                f'''
                <div style="
                    background:#7c3aed;
                    color:white;
                    border-radius:12px;
                    padding:16px;
                    text-align:center;
                    margin-top:12px;
                ">
                    <div style="font-size:34px;font-weight:700;">
                        {kup:.2f}%
                    </div>
                    <div style="font-size:14px;">
                        КУП
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

    st.divider()

    st.subheader("Контроль totals")

    x1, x2 = st.columns(2)

    x1.metric(
        "Raw turnover total",
        f"{total_turnover:,.0f}$"
    )

    x2.metric(
        "Raw sales total",
        f"{total_sales:,.0f}$"
    )

else:

    st.info("Загрузите файл.")
