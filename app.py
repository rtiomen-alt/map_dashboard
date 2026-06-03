
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="WM MAP Dashboard v3.1 FULL", layout="wide")

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
    return str(x).replace("\xa0", "").strip()

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

def compact(v):
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M$"
    if v >= 1_000:
        return f"{v/1_000:.1f}K$"
    return f"{v:.0f}$"

@st.cache_data
def load_data(file):

    if file.name.endswith(".csv"):
        df = pd.read_csv(file, encoding="utf-8-sig")
    else:
        df = pd.read_excel(file)

    df.columns = [clean_text(c) for c in df.columns]

    df["ИНН"] = df["ИНН"].apply(clean_text)
    df["Наименование"] = df["Наименование"].apply(clean_text)

    manager_col = [c for c in df.columns if "менедж" in c.lower()]
    df["Менеджер"] = (
        df[manager_col[0]].apply(clean_text)
        if manager_col else ""
    )

    for y in YEARS:

        turnover_col = [
            c for c in df.columns
            if f"Оборот {y}" in c and "долл" in c
        ][0]

        sales_col = [
            c for c in df.columns
            if str(y) in c and "без НДС" in c
        ][0]

        potential_col = [
            c for c in df.columns
            if "Потенциал по ароме 2022" in c
        ][0]

        df[f"turnover_{y}"] = df[turnover_col].apply(clean_num)
        df[f"sales_{y}"] = df[sales_col].apply(clean_num)
        df[f"potential_{y}"] = df[potential_col].apply(clean_num)

        df[f"kup_{y}"] = np.where(
            df[f"potential_{y}"] > 0,
            (df[f"sales_{y}"] / df[f"potential_{y}"]) * 100,
            0
        )

    current_year = 2025

    df["category"] = ""

    df.loc[df["ИНН"].isin(GIANTS), "category"] = "Гигант"

    regular = df[~df["ИНН"].isin(GIANTS)].copy()

    regular = regular.sort_values(
        f"turnover_{current_year}",
        ascending=False
    )

    total_turnover = regular[f"turnover_{current_year}"].sum()

    regular["cum_share"] = (
        regular[f"turnover_{current_year}"].cumsum()
        / total_turnover
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

    ranked = df[df[f"sales_{current_year}"] > 0].copy()

    ranked["rank"] = (
        ranked[f"sales_{current_year}"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df["rank"] = None
    df.loc[ranked.index, "rank"] = ranked["rank"]

    def calc_status(row):

        sales = row[f"sales_{current_year}"]
        turnover = row[f"turnover_{current_year}"]

        if sales > 0:
            return "Активный"

        if turnover > 0:
            return "Потенциал"

        return "Неактивный"

    df["status"] = df.apply(calc_status, axis=1)

    return df

st.title("WM MAP Dashboard v3.1 FULL")

uploaded = st.file_uploader(
    "Загрузить CSV/XLSX",
    type=["csv", "xlsx", "xls"]
)

if uploaded:

    df = load_data(uploaded)

    current_year = 2025

    st.sidebar.header("Фильтры")

    categories = st.sidebar.multiselect(
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

    search = st.sidebar.text_input("Поиск клиента")

    filtered = df[
        (df["category"].isin(categories))
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

    k1.metric(
        "Оборот 2025",
        compact(filtered["turnover_2025"].sum())
    )

    k2.metric(
        "Продажи 2025",
        compact(filtered["sales_2025"].sum())
    )

    k3.metric(
        "Средний КУП",
        f"{filtered['kup_2025'].mean():.1f}%"
    )

    k4.metric(
        "Клиентов",
        len(filtered)
    )

    st.subheader("Список клиентов")

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
        height=350
    )

    st.subheader("Карточка клиента")

    selected_client = st.selectbox(
        "Выберите клиента",
        filtered["Наименование"].tolist()
    )

    if selected_client:

        client = filtered[
            filtered["Наименование"] == selected_client
        ].iloc[0]

        left, right = st.columns([4, 1])

        with right:

            place = (
                f"ТОП-{int(client['rank'])}"
                if pd.notna(client["rank"])
                else "нет"
            )

            st.metric("Категория", client["category"])
            st.metric("Место", place)
            st.metric("Статус", client["status"])
            st.metric(
                "КУП 2025",
                f"{client['kup_2025']:.1f}%"
            )

        with left:

            turnover = []
            sales = []
            kup = []
            growth_sales = []
            growth_turnover = []

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
                    growth_turnover.append(
                        ((t-prev_t)/prev_t)*100
                    )
                else:
                    growth_turnover.append(None)

                if prev_s and prev_s > 0:
                    growth_sales.append(
                        ((s-prev_s)/prev_s)*100
                    )
                else:
                    growth_sales.append(None)

                prev_t = t
                prev_s = s

            fig = go.Figure()

            fig.add_bar(
                x=YEARS,
                y=turnover,
                name="Оборот, тыс.$",
                yaxis="y"
            )

            fig.add_bar(
                x=YEARS,
                y=sales,
                name="Продажи, тыс.$",
                yaxis="y2"
            )

            fig.add_trace(
                go.Scatter(
                    x=YEARS,
                    y=growth_turnover,
                    mode="lines+markers+text",
                    text=[
                        f"{v:.0f}%" if v else ""
                        for v in growth_turnover
                    ],
                    textposition="top center",
                    name="Прирост оборота %",
                    yaxis="y3"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=YEARS,
                    y=growth_sales,
                    mode="lines+markers+text",
                    text=[
                        f"{v:.0f}%" if v else ""
                        for v in growth_sales
                    ],
                    textposition="bottom center",
                    name="Прирост продаж %",
                    yaxis="y3"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=YEARS,
                    y=kup,
                    mode="text",
                    text=[
                        f"KUP {v:.0f}%"
                        for v in kup
                    ],
                    textposition="middle center",
                    name="КУП"
                )
            )

            fig.update_layout(
                template="plotly_dark",
                height=650,
                barmode="group",
                title=selected_client,
                xaxis=dict(
                    tickmode="array",
                    tickvals=YEARS
                ),
                yaxis=dict(
                    title="Оборот, тыс.$",
                    side="left"
                ),
                yaxis2=dict(
                    title="Продажи, тыс.$",
                    overlaying="y",
                    side="right"
                ),
                yaxis3=dict(
                    title="Прирост %",
                    anchor="free",
                    overlaying="y",
                    side="right",
                    position=0.95
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

else:

    st.info("Загрузите CSV/XLSX файл.")
