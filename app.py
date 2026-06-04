
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="WM MAP BI v63+")

GIANTS = {"4725001168","7705034202","7701215046","7729101200"}

STATUS_ORDER = {
    "Активный":0,
    "Неактивный":1,
    "Потенциальный":2
}

def clean_num(v):
    if pd.isna(v):
        return 0.0
    s = str(v).replace(" ", "").replace("\xa0","").replace(",",".").strip()
    if s in ["","-","nan"]:
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

def years_from_columns(cols):
    years=set()
    for c in cols:
        found = re.findall(r"20\d{2}", str(c))
        for y in found:
            years.add(int(y))
    return sorted(list(years))

def fmt(v):
    if abs(v)>=1_000_000_000:
        return f"{v/1_000_000_000:.2f}B$"
    if abs(v)>=1_000_000:
        return f"{v/1_000_000:.2f}M$"
    if abs(v)>=1_000:
        return f"{v/1_000:.1f}K$"
    return f"{v:.0f}$"

st.title("WM MAP BI v63+ FIXED")

uploaded = st.sidebar.file_uploader(
    "Загрузить XLSX/CSV",
    type=["xlsx","xls","csv"]
)

if uploaded is None:
    st.info("Загрузите файл")
    st.stop()

if uploaded.name.endswith(".csv"):
    df = pd.read_csv(uploaded)
else:
    df = pd.read_excel(uploaded)

df.columns = [str(c).strip() for c in df.columns]

years = years_from_columns(df.columns)
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
        if f"Оборот {y}" in c and "долл" in c.lower()
    ][0]

    sales_col = [
        c for c in df.columns
        if f"Продажи {y}" in c and "без НДС" in c
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
        (df[f"sales_{current_year}"] == 0) & (all_sales > 0)
    ],
    ["Активный","Неактивный"],
    default="Потенциальный"
)

df["Категория"] = ""

df.loc[df["ИНН"].isin(GIANTS),"Категория"] = "ГИГАНТ"

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

df.loc[regular.index,"Категория"] = regular["Категория"]

ranked = df[df[f"sales_{current_year}"] > 0].copy()

ranked["Место"] = (
    ranked[f"sales_{current_year}"]
    .rank(method="min", ascending=False)
    .astype(int)
)

df["Место"] = np.nan
df.loc[ranked.index,"Место"] = ranked["Место"]

categories = sorted(df["Категория"].unique())
managers = sorted(df["Менеджер"].unique())
statuses = sorted(df["Статус"].unique())

selected_categories = st.sidebar.multiselect(
    "Категории",
    categories,
    default=categories
)

selected_managers = st.sidebar.multiselect(
    "Менеджеры",
    managers,
    default=managers
)

selected_statuses = st.sidebar.multiselect(
    "Статусы",
    statuses,
    default=statuses
)

mode = st.sidebar.radio(
    "Режим",
    ["Один клиент","Сводный"]
)

filtered = df[
    (df["Категория"].isin(selected_categories))
    &
    (df["Менеджер"].isin(selected_managers))
    &
    (df["Статус"].isin(selected_statuses))
]

if len(filtered) == 0:
    st.warning("Нет данных")
    st.stop()

if mode == "Один клиент":

    client = st.selectbox(
        "Клиент",
        filtered["Клиент"].tolist()
    )

    filtered = filtered[filtered["Клиент"] == client]

row = filtered.iloc[0]

total_turnover = filtered[f"turnover_{current_year}"].sum()
total_sales = filtered[f"sales_{current_year}"].sum()
total_potential = filtered[f"potential_{current_year}"].sum()

kup_total = (
    (total_sales / total_potential) * 100
    if total_potential > 0 else 0
)

prev_year = years[-2] if len(years) > 1 else current_year

prev_turnover = filtered[f"turnover_{prev_year}"].sum()
prev_sales = filtered[f"sales_{prev_year}"].sum()

turnover_yoy = (
    ((total_turnover-prev_turnover)/prev_turnover)*100
    if prev_turnover > 0 else 0
)

sales_yoy = (
    ((total_sales-prev_sales)/prev_sales)*100
    if prev_sales > 0 else 0
)

c1,c2,c3,c4 = st.columns(4)

c1.metric("Оборот", fmt(total_turnover))
c2.metric("Продажи", fmt(total_sales))
c3.metric("КУП", f"{kup_total:.2f}%")
c4.metric("Клиентов", len(filtered))

st.divider()

h1,h2,h3,h4,h5,h6 = st.columns(6)

h1.markdown(f"### {row['Клиент']}")
h2.markdown(f"**Менеджер:** {row['Менеджер']}")
h3.markdown(f"**Категория:** {row['Категория']}")

place = (
    f"ТОП-{int(row['Место'])}"
    if pd.notna(row["Место"])
    else "нет"
)

h4.markdown(f"**Место:** {place}")
h5.markdown(f"**Статус:** {row['Статус']}")
h6.markdown(
    f"Продажи YoY: {sales_yoy:.1f}%  
"
    f"Оборот YoY: {turnover_yoy:.1f}%"
)

st.divider()

max_sales = max([filtered[f"sales_{y}"].sum() for y in years] + [1])
max_turnover = max([filtered[f"turnover_{y}"].sum() for y in years] + [1])

cols = st.columns(len(years))

prev_s = None
prev_t = None

for idx, y in enumerate(years):

    sales = filtered[f"sales_{y}"].sum()
    turnover = filtered[f"turnover_{y}"].sum()
    potential = filtered[f"potential_{y}"].sum()

    kup = (
        (sales / potential) * 100
        if potential > 0 else 0
    )

    sales_growth = None
    turnover_growth = None

    if prev_s is not None and prev_s > 0:
        sales_growth = ((sales-prev_s)/prev_s)*100

    if prev_t is not None and prev_t > 0:
        turnover_growth = ((turnover-prev_t)/prev_t)*100

    prev_s = sales
    prev_t = turnover

    with cols[idx]:

        st.markdown(f"## {y}")

        sales_df = pd.DataFrame({
            "x":["Продажи"],
            "y":[sales]
        })

        fig_sales = px.bar(
            sales_df,
            x="x",
            y="y",
            text="y"
        )

        fig_sales.update_traces(
            texttemplate="%{text:.2s}",
            marker_color="#16a34a"
        )

        fig_sales.update_layout(
            showlegend=False,
            height=220,
            yaxis_range=[0,max_sales*1.15]
        )

        st.plotly_chart(
            fig_sales,
            use_container_width=True,
            key=f"sales_chart_{idx}_{y}"
        )

        turnover_df = pd.DataFrame({
            "x":["Оборот"],
            "y":[turnover]
        })

        fig_turnover = px.bar(
            turnover_df,
            x="x",
            y="y",
            text="y"
        )

        fig_turnover.update_traces(
            texttemplate="%{text:.2s}",
            marker_color="#2563eb"
        )

        fig_turnover.update_layout(
            showlegend=False,
            height=220,
            yaxis_range=[0,max_turnover*1.15]
        )

        st.plotly_chart(
            fig_turnover,
            use_container_width=True,
            key=f"turnover_chart_{idx}_{y}"
        )

        if sales_growth is not None:

            bg = "#dcfce7" if sales_growth >= 0 else "#fee2e2"

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
                Продажи YoY<br>{sales_growth:.1f}%
                </div>
                ''',
                unsafe_allow_html=True
            )

        if turnover_growth is not None:

            bg = "#dcfce7" if turnover_growth >= 0 else "#fee2e2"

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
                Оборот YoY<br>{turnover_growth:.1f}%
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
        ["По активности","По обороту"],
        horizontal=True
    )

    table = filtered.copy()

    if sort_mode == "По активности":

        table["sort_status"] = table["Статус"].map(STATUS_ORDER)

        table = table.sort_values(
            ["sort_status", f"turnover_{current_year}"],
            ascending=[True, False]
        )

    else:

        table = table.sort_values(
            f"turnover_{current_year}",
            ascending=False
        )

    table["Место"] = table["Место"].apply(
        lambda x:
        f"ТОП-{int(x)}"
        if pd.notna(x)
        else "нет"
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
