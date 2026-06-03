
import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go

st.set_page_config(page_title="WM MAP Dashboard", layout="wide")

GIANTS = {
    "7705034202",
    "7701215046",
    "4725001168",
    "7729101200"
}

YEARS = [2022, 2023, 2024, 2025]

def clean_text(x):
    if pd.isna(x):
        return ""
    return (
        str(x)
        .replace("\xa0", "")
        .replace("  ", " ")
        .strip()
    )

def clean_num(x):

    if pd.isna(x):
        return 0

    s = (
        str(x)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    if s in ["", "-", "-.", "nan"]:
        return 0

    try:
        return float(s)
    except:
        return 0

def compact_money(v):

    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M$"

    if v >= 1_000:
        return f"{v/1_000:.1f}K$"

    return f"{v:.0f}$"

@st.cache_data
def load_data(file):

    if file.name.endswith(".csv"):
        df = pd.read_csv(
            file,
            encoding="utf-8-sig",
            engine="python"
        )
    else:
        df = pd.read_excel(file)

    df.columns = [clean_text(c) for c in df.columns]

    df["ИНН"] = df["ИНН"].apply(clean_text)
    df["Наименование"] = df["Наименование"].apply(clean_text)

    manager_col = [c for c in df.columns if "менедж" in c.lower()]
    if manager_col:
        df["Менеджер"] = df[manager_col[0]].apply(clean_text)
    else:
        df["Менеджер"] = ""

    for y in YEARS:

        turnover_col = [
            c for c in df.columns
            if f"Оборот {y}, долл" in c
        ][0]

        potential_col = [
            c for c in df.columns
            if f"Потенциал по ароме {y}" in c
        ][0]

        sales_candidates = [
            c for c in df.columns
            if str(y) in c
            and "без ндс" in c.lower()
        ]

        sales_col = sales_candidates[0]

        df[f"turnover_{y}"] = df[turnover_col].apply(clean_num)
        df[f"sales_{y}"] = df[sales_col].apply(clean_num)
        df[f"potential_{y}"] = df[potential_col].apply(clean_num)

        df[f"kup_{y}"] = np.where(
            df[f"sales_{y}"] > 0,
            (df[f"potential_{y}"] / df[f"sales_{y}"]) * 100,
            0
        )

    current_year = max(YEARS)

    df["category"] = ""

    df.loc[df["ИНН"].isin(GIANTS), "category"] = "Гигант"

    regular = df[~df["ИНН"].isin(GIANTS)].copy()

    regular = regular.sort_values(
        f"turnover_{current_year}",
        ascending=False
    )

    total = regular[f"turnover_{current_year}"].sum()

    regular["cum_share"] = (
        regular[f"turnover_{current_year}"].cumsum() / total
    )

    regular["category"] = np.select(
        [
            regular["cum_share"] <= 0.80,
            regular["cum_share"] <= 0.95
        ],
        ["A", "Б"],
        default="В"
    )

    df.loc[regular.index, "category"] = regular["category"]

    rank_year = current_year

    df["rank"] = None

    ranked = df[df[f"sales_{rank_year}"] > 0].copy()

    ranked["rank"] = (
        ranked[f"sales_{rank_year}"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df.loc[ranked.index, "rank"] = ranked["rank"]

    def get_status(row):

        sales = row[f"sales_{current_year}"]
        turnover = row[f"turnover_{current_year}"]

        if sales > 0:
            return "Активный"

        if turnover > 0:
            return "Потенциал"

        return "Неактивный"

    df["status"] = df.apply(get_status, axis=1)

    return df

st.title("WM MAP Dashboard v2.1 FIXED")

uploaded = st.file_uploader(
    "Загрузить CSV/XLSX",
    type=["csv", "xlsx", "xls"]
)

if uploaded:

    df = load_data(uploaded)

    current_year = max(YEARS)

    st.sidebar.header("Фильтры")

    cats = st.sidebar.multiselect(
        "Категория",
        ["Гигант", "A", "Б", "В"],
        default=["Гигант", "A", "Б", "В"]
    )

    statuses = st.sidebar.multiselect(
        "Статус",
        ["Активный", "Потенциал", "Неактивный"],
        default=["Активный", "Потенциал", "Неактивный"]
    )

    managers = sorted(df["Менеджер"].dropna().unique())

    selected_managers = st.sidebar.multiselect(
        "Менеджер",
        managers,
        default=managers
    )

    search = st.sidebar.text_input("Поиск")

    filtered = df[
        (df["category"].isin(cats))
        &
        (df["status"].isin(statuses))
        &
        (df["Менеджер"].isin(selected_managers))
    ]

    if search:
        filtered = filtered[
            filtered["Наименование"]
            .str.contains(search, case=False, na=False)
        ]

    k1, k2, k3, k4 = st.columns(4)

    total_turnover = filtered[f"turnover_{current_year}"].sum()
    total_sales = filtered[f"sales_{current_year}"].sum()
    avg_kup = filtered[f"kup_{current_year}"].mean()

    k1.metric(
        "Оборот",
        compact_money(total_turnover)
    )

    k2.metric(
        "Продажи",
        compact_money(total_sales)
    )

    k3.metric(
        "Средний КУП",
        f"{avg_kup:.1f}%"
    )

    k4.metric(
        "Клиентов",
        len(filtered)
    )

    st.subheader("Клиенты")

    table = filtered[[
        "ИНН",
        "Наименование",
        "Менеджер",
        "category",
        "status",
        "rank"
    ]].copy()

    table["Место"] = table["rank"].apply(
        lambda x: f"ТОП-{int(x)}"
        if pd.notna(x)
        else "нет"
    )

    table = table.rename(columns={
        "category": "Категория",
        "status": "Статус"
    })

    st.dataframe(
        table.drop(columns=["rank"]),
        use_container_width=True,
        height=400
    )

    st.subheader("Карточка клиента")

    selected = st.selectbox(
        "Клиент",
        filtered["Наименование"].tolist()
    )

    if selected:

        client = filtered[
            filtered["Наименование"] == selected
        ].iloc[0]

        place = (
            f"ТОП-{int(client['rank'])}"
            if pd.notna(client["rank"])
            else "нет"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Категория", client["category"])
        c2.metric("Место", place)
        c3.metric("Статус", client["status"])
        c4.metric(
            "КУП 2025",
            f"{client['kup_2025']:.1f}%"
        )

        turnover = []
        sales = []
        kup = []
        turnover_growth = []
        sales_growth = []

        prev_t = None
        prev_s = None

        for y in YEARS:

            t = client[f"turnover_{y}"] / 1000
            s = client[f"sales_{y}"] / 1000
            k = client[f"kup_{y}"]

            turnover.append(t)
            sales.append(s)
            kup.append(k)

            if prev_t and prev_t > 0:
                turnover_growth.append(
                    ((t - prev_t) / prev_t) * 100
                )
            else:
                turnover_growth.append(None)

            if prev_s and prev_s > 0:
                sales_growth.append(
                    ((s - prev_s) / prev_s) * 100
                )
            else:
                sales_growth.append(None)

            prev_t = t
            prev_s = s

        fig = go.Figure()

        fig.add_bar(
            x=YEARS,
            y=turnover,
            name="Оборот, тыс.$"
        )

        fig.add_bar(
            x=YEARS,
            y=sales,
            name="Продажи, тыс.$"
        )

        fig.add_trace(
            go.Scatter(
                x=YEARS,
                y=kup,
                mode="lines+markers+text",
                name="КУП %",
                yaxis="y2",
                line=dict(width=5),
                text=[f"{v:.0f}%" for v in kup],
                textposition="top center"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=YEARS,
                y=turnover_growth,
                mode="lines+markers",
                name="Прирост оборота %",
                yaxis="y2"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=YEARS,
                y=sales_growth,
                mode="lines+markers",
                name="Прирост продаж %",
                yaxis="y2"
            )
        )

        fig.update_layout(
            template="plotly_dark",
            height=650,
            barmode="group",
            title=client["Наименование"],
            yaxis=dict(
                title="тыс.$"
            ),
            yaxis2=dict(
                title="%",
                overlaying="y",
                side="right"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )
