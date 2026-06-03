
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="WM MAP Dashboard", layout="wide")

GIANTS = {
    "7705034202",
    "7701215046",
    "4725001168",
    "7729101200"
}

def clean_num(x):
    if pd.isna(x):
        return 0

    x = str(x).replace("\\xa0", "").replace(" ", "").replace(",", ".").strip()

    if x in ["-", "", "nan"]:
        return 0

    try:
        return float(x)
    except:
        return 0

@st.cache_data
def load_data(file):

    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    df.columns = [c.strip() for c in df.columns]

    df["ИНН"] = (
        df["ИНН"]
        .astype(str)
        .str.replace("\\xa0", "", regex=False)
        .str.strip()
    )

    years = [2022, 2023, 2024, 2025]

    for y in years:

        turnover_col = [c for c in df.columns if f"Оборот {y}, долл" in c][0]
        sales_col = [c for c in df.columns if f"Продажи {y} без НДС" in c][0]
        potential_col = [c for c in df.columns if "Потенциал" in c and str(y) in c][0]

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

    rank_year = current_year

    sales_col = f"sales_{rank_year}"

    df["rank"] = None

    ranked = df[df[sales_col] > 0].copy()

    ranked["rank"] = (
        ranked[sales_col]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df.loc[ranked.index, "rank"] = ranked["rank"]

    def calc_status(row):

        turnover = row[f"turnover_{current_year}"]
        sales = row[f"sales_{current_year}"]

        if sales > 0:
            return "Активный"

        if turnover > 0 and sales == 0:
            return "Потенциал"

        return "Неактивный"

    df["status"] = df.apply(calc_status, axis=1)

    return df

def compact_money(v):

    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M $"

    if v >= 1_000:
        return f"{v/1_000:.1f}K $"

    return f"{v:.0f} $"

st.title("WM MAP Dashboard")

uploaded = st.file_uploader(
    "Загрузить CSV/XLSX",
    type=["csv", "xlsx", "xls"]
)

if uploaded:

    df = load_data(uploaded)

    current_year = 2025

    st.sidebar.header("Фильтры")

    category_filter = st.sidebar.multiselect(
        "Категория",
        options=["Гигант", "A", "Б", "В"],
        default=["Гигант", "A", "Б", "В"]
    )

    manager_filter = st.sidebar.multiselect(
        "Менеджер",
        options=sorted(df["Менеджер"].dropna().astype(str).unique()),
        default=sorted(df["Менеджер"].dropna().astype(str).unique())
    )

    status_filter = st.sidebar.multiselect(
        "Статус",
        options=["Активный", "Потенциал", "Неактивный"],
        default=["Активный", "Потенциал", "Неактивный"]
    )

    search = st.sidebar.text_input("Поиск")

    filtered = df[
        (df["category"].isin(category_filter))
        &
        (df["Менеджер"].astype(str).isin(manager_filter))
        &
        (df["status"].isin(status_filter))
    ]

    if search:
        filtered = filtered[
            filtered["Наименование"]
            .str.contains(search, case=False, na=False)
        ]

    total_turnover = filtered[f"turnover_{current_year}"].sum()
    total_sales = filtered[f"sales_{current_year}"].sum()

    avg_kup = (
        filtered[f"kup_{current_year}"].mean()
        if len(filtered) > 0 else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(f"Оборот {current_year}", compact_money(total_turnover))
    c2.metric(f"Продажи {current_year}", compact_money(total_sales))
    c3.metric("Средний КУП", f"{avg_kup:.1f}%")
    c4.metric("Клиентов", len(filtered))

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
        lambda x: f"ТОП-{int(x)}" if pd.notna(x) else "нет"
    )

    st.dataframe(
        table.rename(columns={
            "category": "Категория",
            "status": "Статус"
        }),
        use_container_width=True
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

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.markdown(f"### {client['Наименование']}")
        col2.metric("Категория", client["category"])
        col3.metric("Место", place)
        col4.metric("КУП", f"{client[f'kup_{current_year}']:.1f}%")
        col5.metric("Статус", client["status"])

        years = [2022, 2023, 2024, 2025]

        turnover = []
        sales = []
        kup = []
        turnover_growth = []
        sales_growth = []

        prev_t = None
        prev_s = None

        for y in years:

            t = client[f"turnover_{y}"] / 1000
            s = client[f"sales_{y}"] / 1000
            k = client[f"kup_{y}"]

            turnover.append(t)
            sales.append(s)
            kup.append(k)

            if prev_t and prev_t > 0:
                turnover_growth.append(((t - prev_t) / prev_t) * 100)
            else:
                turnover_growth.append(None)

            if prev_s and prev_s > 0:
                sales_growth.append(((s - prev_s) / prev_s) * 100)
            else:
                sales_growth.append(None)

            prev_t = t
            prev_s = s

        fig = go.Figure()

        fig.add_bar(
            x=years,
            y=turnover,
            name="Оборот, тыс.$"
        )

        fig.add_bar(
            x=years,
            y=sales,
            name="Продажи без НДС, тыс.$"
        )

        fig.add_trace(
            go.Scatter(
                x=years,
                y=turnover_growth,
                mode="lines+markers+text",
                name="Прирост оборота %",
                yaxis="y2",
                text=[f"{v:.1f}%" if v is not None else "" for v in turnover_growth],
                textposition="top center"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=years,
                y=sales_growth,
                mode="lines+markers+text",
                name="Прирост продаж %",
                yaxis="y2",
                text=[f"{v:.1f}%" if v is not None else "" for v in sales_growth],
                textposition="bottom center"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=years,
                y=kup,
                mode="lines+markers+text",
                line=dict(width=4),
                name="КУП %",
                yaxis="y2",
                text=[f"{v:.1f}%" for v in kup],
                textposition="top right"
            )
        )

        fig.update_layout(
            title="Динамика показателей",
            barmode="group",
            height=600,
            yaxis=dict(title="тыс.$"),
            yaxis2=dict(
                title="%",
                overlaying="y",
                side="right"
            )
        )

        st.plotly_chart(fig, use_container_width=True)
