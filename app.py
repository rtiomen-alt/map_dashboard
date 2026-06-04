
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

st.set_page_config(page_title="WM MAP BI v6.4 FULL STABLE", layout="wide")

GIANTS = {
    "4725001168",
    "7705034202",
    "7701215046",
    "7729101200"
}

STATUS_ORDER = {
    "Активный": 0,
    "Неактивный": 1,
    "Потенциальный": 2
}

def clean_num(x):
    if pd.isna(x):
        return 0.0
    s = str(x).replace("\xa0","").replace(" ","").replace(",",".").strip()
    if s in ["", "-", "nan"]:
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

def detect_years(cols):
    years=set()
    for c in cols:
        for y in re.findall(r"20\d{2}", str(c)):
            years.add(int(y))
    return sorted([y for y in years if 2020 <= y <= 2035])

def fmt_money(v):
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B$"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M$"
    if v >= 1_000:
        return f"{v/1_000:.1f}K$"
    return f"{v:.0f}$"

st.title("WM MAP BI v6.4 FULL STABLE")

uploaded = st.sidebar.file_uploader(
    "Загрузить файл",
    type=["xlsx","xls","csv"]
)

if uploaded:

    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded, encoding="utf-8-sig")
    else:
        df = pd.read_excel(uploaded)

    df.columns = [str(c).strip() for c in df.columns]

    years = detect_years(df.columns)
    current_year = max(years)

    manager_col = [c for c in df.columns if "Менеджер" in c][0]

    df["ИНН"] = (
        df["ИНН"]
        .astype(str)
        .str.replace("\xa0","", regex=False)
        .str.strip()
    )

    df["Клиент"] = df["Наименование"].astype(str)
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

        df[f"kup_{y}"] = np.where(
            df[f"potential_{y}"] > 0,
            (df[f"sales_{y}"] / df[f"potential_{y}"]) * 100,
            0
        )

    all_sales = sum(df[f"sales_{y}"] for y in years)

    df["Статус"] = np.select(
        [
            df[f"sales_{current_year}"] > 0,
            ((df[f"sales_{current_year}"] == 0) & (all_sales > 0))
        ],
        ["Активный", "Неактивный"],
        default="Потенциальный"
    )

    df["Категория"] = ""

    df.loc[df["ИНН"].isin(GIANTS), "Категория"] = "ГИГАНТ"

    regular = df[~df["ИНН"].isin(GIANTS)].copy()

    regular = regular.sort_values(
        f"turnover_{current_year}",
        ascending=False
    )

    total_regular = regular[f"turnover_{current_year}"].sum()

    regular["cum"] = (
        regular[f"turnover_{current_year}"].cumsum()
        / total_regular
    )

    regular["Категория"] = np.select(
        [
            regular["cum"] <= 0.80,
            regular["cum"] <= 0.95
        ],
        ["A","Б"],
        default="В"
    )

    df.loc[regular.index, "Категория"] = regular["Категория"]

    ranked = df[df[f"sales_{current_year}"] > 0].copy()

    ranked["Место"] = (
        ranked[f"sales_{current_year}"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df["Место"] = np.nan
    df.loc[ranked.index, "Место"] = ranked["Место"]

    selected_categories = st.sidebar.multiselect(
        "Категории",
        sorted(df["Категория"].unique()),
        default=sorted(df["Категория"].unique())
    )

    selected_managers = st.sidebar.multiselect(
        "Менеджеры",
        sorted(df["Менеджер"].unique()),
        default=sorted(df["Менеджер"].unique())
    )

    selected_statuses = st.sidebar.multiselect(
        "Статусы",
        sorted(df["Статус"].unique()),
        default=sorted(df["Статус"].unique())
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

    if len(filtered) == 0:
        st.warning("Нет данных.")
        st.stop()

    if mode == "Один клиент":

        selected_client = st.selectbox(
            "Клиент",
            filtered["Клиент"].tolist()
        )

        filtered = filtered[
            filtered["Клиент"] == selected_client
        ]

    row = filtered.iloc[0]

    total_turnover = filtered[f"turnover_{current_year}"].sum()
    total_sales = filtered[f"sales_{current_year}"].sum()
    total_potential = filtered[f"potential_{current_year}"].sum()

    kup_total = (
        (total_sales / total_potential) * 100
        if total_potential > 0 else 0
    )

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Оборот", fmt_money(total_turnover))
    c2.metric("Продажи", fmt_money(total_sales))
    c3.metric("КУП", f"{kup_total:.2f}%")
    c4.metric("Клиентов", len(filtered))

    prev_year = years[-2] if len(years) > 1 else current_year

    sales_growth = 0
    turnover_growth = 0

    prev_sales = filtered[f"sales_{prev_year}"].sum()
    prev_turnover = filtered[f"turnover_{prev_year}"].sum()

    if prev_sales > 0:
        sales_growth = ((total_sales - prev_sales) / prev_sales) * 100

    if prev_turnover > 0:
        turnover_growth = ((total_turnover - prev_turnover) / prev_turnover) * 100

    st.divider()

    h1,h2,h3,h4,h5,h6 = st.columns(6)

    h1.markdown(f"### {row['Клиент']}")
    h2.markdown(f"**Менеджер:** {row['Менеджер']}")
    h3.markdown(f"**Категория:** {row['Категория']}")
    h4.markdown(f"**Статус:** {row['Статус']}")

    place = (
        f"ТОП-{int(row['Место'])}"
        if pd.notna(row["Место"])
        else "нет"
    )

    h5.markdown(f"**Место:** {place}")

    h6.markdown(
        f"Продажи YoY: **{sales_growth:.1f}%**  
Оборот YoY: **{turnover_growth:.1f}%**"
    )

    st.divider()

    max_sales = max([filtered[f"sales_{y}"].sum() for y in years] + [1])
    max_turnover = max([filtered[f"turnover_{y}"].sum() for y in years] + [1])

    cols = st.columns(len(years))

    prev_sales_y = None
    prev_turnover_y = None

    for idx,y in enumerate(years):

        with cols[idx]:

            sales = filtered[f"sales_{y}"].sum()
            turnover = filtered[f"turnover_{y}"].sum()
            potential = filtered[f"potential_{y}"].sum()

            kup = ((sales / potential) * 100) if potential > 0 else 0

            st.markdown(f"## {y}")

            fig1 = go.Figure()

            fig1.add_bar(
                x=["Продажи"],
                y=[sales],
                marker_color="#16a34a",
                text=[fmt_money(sales)],
                textposition="outside"
            )

            fig1.update_layout(
                height=200,
                showlegend=False,
                margin=dict(l=5,r=5,t=5,b=5),
                yaxis=dict(range=[0, max_sales * 1.15])
            )

            st.plotly_chart(
                fig1,
                use_container_width=True,
                key=f"sales_chart_{idx}_{y}"
            )

            fig2 = go.Figure()

            fig2.add_bar(
                x=["Оборот"],
                y=[turnover],
                marker_color="#2563eb",
                text=[fmt_money(turnover)],
                textposition="outside"
            )

            fig2.update_layout(
                height=200,
                showlegend=False,
                margin=dict(l=5,r=5,t=5,b=5),
                yaxis=dict(range=[0, max_turnover * 1.15])
            )

            st.plotly_chart(
                fig2,
                use_container_width=True,
                key=f"turnover_chart_{idx}_{y}"
            )

            sales_yoy = None
            turnover_yoy = None

            if prev_sales_y is not None and prev_sales_y > 0:
                sales_yoy = ((sales - prev_sales_y) / prev_sales_y) * 100

            if prev_turnover_y is not None and prev_turnover_y > 0:
                turnover_yoy = ((turnover - prev_turnover_y) / prev_turnover_y) * 100

            prev_sales_y = sales
            prev_turnover_y = turnover

            if sales_yoy is not None:
                bg = "#dcfce7" if sales_yoy >= 0 else "#fee2e2"

                st.markdown(
                    f'''
                    <div style="
                    background:{bg};
                    padding:8px;
                    border-radius:8px;
                    text-align:center;
                    font-weight:700;
                    margin-top:8px;
                    ">
                    Продажи YoY<br>{sales_yoy:.1f}%
                    </div>
                    ''',
                    unsafe_allow_html=True
                )

            if turnover_yoy is not None:
                bg = "#dcfce7" if turnover_yoy >= 0 else "#fee2e2"

                st.markdown(
                    f'''
                    <div style="
                    background:{bg};
                    padding:8px;
                    border-radius:8px;
                    text-align:center;
                    font-weight:700;
                    margin-top:8px;
                    ">
                    Оборот YoY<br>{turnover_yoy:.1f}%
                    </div>
                    ''',
                    unsafe_allow_html=True
                )

            st.markdown(
                f'''
                <div style="
                background:#7c3aed;
                color:white;
                border-radius:10px;
                padding:12px;
                text-align:center;
                margin-top:8px;
                ">
                <div style="font-size:30px;font-weight:700;">
                {kup:.2f}%
                </div>
                <div>КУП</div>
                </div>
                ''',
                unsafe_allow_html=True
            )

    if mode == "Сводный":

        st.divider()

        sort_mode = st.radio(
            "Сортировка",
            ["По активности", "По обороту"],
            horizontal=True
        )

        table = filtered.copy()

        if sort_mode == "По активности":
            table["status_sort"] = table["Статус"].map(STATUS_ORDER)

            table = table.sort_values(
                ["status_sort", f"turnover_{current_year}"],
                ascending=[True, False]
            )
        else:
            table = table.sort_values(
                f"turnover_{current_year}",
                ascending=False
            )

        table["Место"] = table["Место"].apply(
            lambda x: f"ТОП-{int(x)}" if pd.notna(x) else "нет"
        )

        st.dataframe(
            table[
                [
                    "Клиент",
                    "Менеджер",
                    "Категория",
                    "Статус",
                    "Место",
                    f"turnover_{current_year}",
                    f"sales_{current_year}"
                ]
            ],
            use_container_width=True,
            height=500
        )

else:
    st.info("Загрузите файл.")
