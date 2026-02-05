import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from datetime import timedelta

st.set_page_config(
    page_title="Mocawa Cafe - BI Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    padding: 15px 20px;
    border-radius: 10px;
    border-left: 4px solid #ff5023;
}
[data-testid="stMetricValue"] { font-size: 1.4rem; }
[data-testid="stMetricDelta"] { font-size: 0.85rem; }
div[data-testid="stHorizontalBlock"] > div { padding: 0 4px; }
</style>
""", unsafe_allow_html=True)

BASE = os.path.dirname(__file__)
COLORS = ["#ff5023", "#ff8c61", "#ffc09f", "#2ec4b6", "#3d5a80", "#ee6c4d", "#293241", "#98c1d9"]


@st.cache_data
def load_sales():
    df = pd.read_csv(
        os.path.join(BASE, "fudo_sales.csv"),
        parse_dates=["created_at", "closed_at"],
        low_memory=False,
    )
    df["created_at"] = df["created_at"].dt.tz_localize(None)
    df["closed_at"] = pd.to_datetime(df["closed_at"], errors="coerce").dt.tz_localize(None)

    df["date"] = df["created_at"].dt.date
    df["hour"] = df["created_at"].dt.hour
    df["day_of_week"] = df["created_at"].dt.day_name()
    df["day_num"] = df["created_at"].dt.dayofweek
    df["year_month"] = df["created_at"].dt.to_period("M").astype(str)
    df["year"] = df["created_at"].dt.year
    df["month_num"] = df["created_at"].dt.month
    df["week"] = df["created_at"].dt.to_period("W").apply(lambda r: r.start_time).dt.date

    df["item_quantity"] = pd.to_numeric(df["item_quantity"], errors="coerce").fillna(0)
    df["item_price"] = pd.to_numeric(df["item_price"], errors="coerce").fillna(0)
    df["item_cost"] = pd.to_numeric(df["item_cost"], errors="coerce").fillna(0)
    df["sale_total"] = pd.to_numeric(df["sale_total"], errors="coerce").fillna(0)
    df["discount_total"] = pd.to_numeric(df["discount_total"], errors="coerce").fillna(0)
    df["tips_total"] = pd.to_numeric(df["tips_total"], errors="coerce").fillna(0)

    df["item_revenue"] = df["item_price"] * df["item_quantity"]
    df["item_total_cost"] = df["item_cost"] * df["item_quantity"]
    df["item_margin"] = df["item_revenue"] - df["item_total_cost"]

    # Duration in minutes
    df["duration_min"] = (df["closed_at"] - df["created_at"]).dt.total_seconds() / 60

    df["product_category"] = df["product_category"].fillna("Sin Categoria")
    df["waiter"] = df["waiter"].fillna("Sin Asignar")
    df["sale_type"] = df["sale_type"].fillna("UNKNOWN")
    df["sale_state"] = df["sale_state"].fillna("UNKNOWN")
    df["product_name"] = df["product_name"].fillna("Sin Producto")

    return df


@st.cache_data
def load_expenses():
    path = os.path.join(BASE, "fudo_expenses.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def build_payments_df(_df_sale_ids, _df_payment_cols):
    """Build payments dataframe from unique sales."""
    rows = []
    for _, row in _df_payment_cols.iterrows():
        methods = str(row.get("payment_methods", "")).split("|")
        amounts = str(row.get("payment_amounts", "")).split("|")
        for m, a in zip(methods, amounts):
            m = m.strip()
            if not m:
                continue
            try:
                a_val = float(a)
            except (ValueError, TypeError):
                a_val = 0
            rows.append({"sale_id": row["sale_id"], "date": row["date"],
                         "year_month": row["year_month"], "method": m, "amount": a_val})
    return pd.DataFrame(rows)


# ==================== LOAD DATA ====================
df = load_sales()
expenses_df = load_expenses()

# ==================== SIDEBAR FILTERS ====================
st.sidebar.title("Filtros")

min_date = df["created_at"].min().date()
max_date = df["created_at"].max().date()
date_range = st.sidebar.date_input(
    "Rango de fechas",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

sale_types = st.sidebar.multiselect(
    "Tipo de venta",
    options=sorted(df["sale_type"].unique()),
    default=sorted(df["sale_type"].unique()),
)
sale_states = st.sidebar.multiselect(
    "Estado",
    options=sorted(df["sale_state"].unique()),
    default=["CLOSED"],
)
categories = st.sidebar.multiselect(
    "Categoria",
    options=sorted(df["product_category"].unique()),
    default=sorted(df["product_category"].unique()),
)
waiters = st.sidebar.multiselect(
    "Mesero/a",
    options=sorted(df["waiter"].unique()),
    default=sorted(df["waiter"].unique()),
)

# ==================== APPLY FILTERS ====================
mask = (
    (df["date"] >= start_date)
    & (df["date"] <= end_date)
    & (df["sale_type"].isin(sale_types))
    & (df["sale_state"].isin(sale_states))
    & (df["product_category"].isin(categories))
    & (df["waiter"].isin(waiters))
)
fdf = df[mask].copy()
unique_sales = fdf.drop_duplicates(subset="sale_id")

# Compute days in range
days_in_range = max((end_date - start_date).days, 1)

# ==================== HEADER ====================
st.title("Mocawa Cafe - Dashboard BI")
st.caption(f"Datos: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')} ({days_in_range} dias)")

# ==================== KPI ROW 1 ====================
total_revenue = unique_sales["sale_total"].sum()
total_sales = unique_sales["sale_id"].nunique()
avg_ticket = total_revenue / total_sales if total_sales > 0 else 0
total_items = fdf["item_quantity"].sum()
total_item_revenue = fdf["item_revenue"].sum()
total_item_cost = fdf["item_total_cost"].sum()
gross_margin_pct = ((total_item_revenue - total_item_cost) / total_item_revenue * 100) if total_item_revenue > 0 else 0
gross_margin_abs = total_item_revenue - total_item_cost
avg_daily_revenue = total_revenue / days_in_range
avg_daily_sales = total_sales / days_in_range
items_per_ticket = total_items / total_sales if total_sales > 0 else 0
total_discounts = unique_sales["discount_total"].sum()
total_tips = unique_sales["tips_total"].sum()

# Canceled stats
all_states_mask = (
    (df["date"] >= start_date)
    & (df["date"] <= end_date)
    & (df["sale_type"].isin(sale_types))
    & (df["product_category"].isin(categories))
    & (df["waiter"].isin(waiters))
)
all_sales_in_range = df[all_states_mask].drop_duplicates(subset="sale_id")
canceled_count = all_sales_in_range[all_sales_in_range["sale_state"] == "CANCELED"]["sale_id"].nunique()
cancel_rate = (canceled_count / all_sales_in_range["sale_id"].nunique() * 100) if all_sales_in_range["sale_id"].nunique() > 0 else 0

# Avg duration
valid_duration = unique_sales[(unique_sales["duration_min"] > 0) & (unique_sales["duration_min"] < 480)]
avg_duration = valid_duration["duration_min"].mean() if len(valid_duration) > 0 else 0

# Peak hour
if not fdf.empty:
    peak_hour = fdf.groupby("hour")["item_revenue"].sum().idxmax()
    peak_hour_label = f"{peak_hour}:00"
else:
    peak_hour_label = "-"

# Top product
if not fdf.empty:
    top_product = fdf.groupby("product_name")["item_quantity"].sum().idxmax()
else:
    top_product = "-"

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Ingresos Totales", f"${total_revenue:,.0f}")
k2.metric("Total Ventas", f"{total_sales:,}")
k3.metric("Ticket Promedio", f"${avg_ticket:,.0f}")
k4.metric("Items Vendidos", f"{total_items:,.0f}")
k5.metric("Margen Bruto", f"{gross_margin_pct:.1f}%")
k6.metric("Ganancia Bruta", f"${gross_margin_abs:,.0f}")

k7, k8, k9, k10, k11, k12 = st.columns(6)
k7.metric("Ingreso Diario Prom.", f"${avg_daily_revenue:,.0f}")
k8.metric("Ventas/Dia Prom.", f"{avg_daily_sales:,.1f}")
k9.metric("Items/Ticket", f"{items_per_ticket:,.1f}")
k10.metric("Hora Pico", peak_hour_label)
k11.metric("Ventas Canceladas", f"{canceled_count:,}", delta=f"{cancel_rate:.1f}%", delta_color="inverse")
k12.metric("Duracion Prom.", f"{avg_duration:.0f} min")

st.divider()

# ==================== TABS ====================
tab_overview, tab_products, tab_payments, tab_staff, tab_time, tab_profit, tab_detail = st.tabs([
    "Resumen General", "Productos", "Pagos", "Staff", "Horarios", "Rentabilidad", "Detalle"
])

# ==================== TAB: RESUMEN GENERAL ====================
with tab_overview:

    # Revenue over time
    st.subheader("Ingresos en el Tiempo")
    time_gran = st.radio("Granularidad", ["Diario", "Semanal", "Mensual"], horizontal=True, index=2, key="tg1")

    if time_gran == "Diario":
        rev_time = unique_sales.groupby("date").agg(
            Ingresos=("sale_total", "sum"), Ventas=("sale_id", "nunique")
        ).reset_index().rename(columns={"date": "Fecha"})
    elif time_gran == "Semanal":
        rev_time = unique_sales.groupby("week").agg(
            Ingresos=("sale_total", "sum"), Ventas=("sale_id", "nunique")
        ).reset_index().rename(columns={"week": "Fecha"})
    else:
        rev_time = unique_sales.groupby("year_month").agg(
            Ingresos=("sale_total", "sum"), Ventas=("sale_id", "nunique")
        ).reset_index().rename(columns={"year_month": "Fecha"})

    fig_rev = go.Figure()
    fig_rev.add_trace(go.Scatter(
        x=rev_time["Fecha"], y=rev_time["Ingresos"], name="Ingresos",
        fill="tozeroy", fillcolor="rgba(255,80,35,0.1)", line_color="#ff5023",
    ))
    fig_rev.add_trace(go.Bar(
        x=rev_time["Fecha"], y=rev_time["Ventas"], name="# Ventas",
        yaxis="y2", marker_color="rgba(46,196,182,0.5)",
    ))
    fig_rev.update_layout(
        yaxis=dict(title="Ingresos ($)"),
        yaxis2=dict(title="# Ventas", overlaying="y", side="right"),
        hovermode="x unified", height=420, legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig_rev, key="rev_chart")

    st.divider()

    # Year over year + sale type
    col_yoy, col_type = st.columns(2)

    with col_yoy:
        st.subheader("Comparacion Anual")
        yoy = unique_sales.copy()
        month_names = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
                       7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
        yoy_summary = yoy.groupby(["year","month_num"])["sale_total"].sum().reset_index()
        yoy_summary.columns = ["Ano","Mes","Ingresos"]
        yoy_summary["Ano"] = yoy_summary["Ano"].astype(str)
        fig_yoy = px.line(yoy_summary, x="Mes", y="Ingresos", color="Ano",
                          markers=True, color_discrete_sequence=COLORS)
        fig_yoy.update_layout(
            xaxis=dict(tickmode="array", tickvals=list(range(1,13)), ticktext=list(month_names.values())),
            height=400, hovermode="x unified",
        )
        st.plotly_chart(fig_yoy, key="yoy_chart")

    with col_type:
        st.subheader("Tipo de Venta en el Tiempo")
        type_trend = unique_sales.groupby(["year_month","sale_type"])["sale_id"].nunique().reset_index()
        type_trend.columns = ["Mes","Tipo","Ventas"]
        fig_type = px.area(type_trend, x="Mes", y="Ventas", color="Tipo",
                           color_discrete_sequence=px.colors.qualitative.Set2)
        fig_type.update_layout(height=400, hovermode="x unified")
        st.plotly_chart(fig_type, key="type_chart")

    st.divider()

    # Revenue by day of week + Sale type distribution
    col_dow, col_st = st.columns(2)

    with col_dow:
        st.subheader("Ingresos por Dia de Semana")
        day_labels = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miercoles",
                      "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sabado","Sunday":"Domingo"}
        dow = unique_sales.copy()
        dow["dia"] = dow["day_of_week"].map(day_labels)
        dow["day_num"] = dow["day_num"]
        dow_rev = dow.groupby(["day_num","dia"]).agg(
            ingresos=("sale_total","sum"), ventas=("sale_id","nunique")
        ).reset_index().sort_values("day_num")
        fig_dow = px.bar(dow_rev, x="dia", y="ingresos", text="ventas",
                         color_discrete_sequence=["#ff5023"])
        fig_dow.update_traces(texttemplate="%{text:,} ventas", textposition="outside")
        fig_dow.update_layout(height=400, xaxis_title="", yaxis_title="Ingresos ($)")
        st.plotly_chart(fig_dow, key="dow_chart")

    with col_st:
        st.subheader("Distribucion por Tipo de Venta")
        type_dist = unique_sales.groupby("sale_type").agg(
            ventas=("sale_id","nunique"), ingresos=("sale_total","sum")
        ).reset_index()
        fig_st = px.pie(type_dist, values="ingresos", names="sale_type",
                        hole=0.45, color_discrete_sequence=COLORS)
        fig_st.update_traces(textinfo="label+percent+value", texttemplate="%{label}<br>%{percent}<br>$%{value:,.0f}")
        fig_st.update_layout(height=400)
        st.plotly_chart(fig_st, key="st_chart")

    st.divider()

    # Cumulative revenue + Monthly growth
    col_cum, col_growth = st.columns(2)

    with col_cum:
        st.subheader("Ingresos Acumulados")
        cum_rev = unique_sales.groupby("year_month")["sale_total"].sum().cumsum().reset_index()
        cum_rev.columns = ["Mes", "Acumulado"]
        fig_cum = px.area(cum_rev, x="Mes", y="Acumulado", color_discrete_sequence=["#2ec4b6"])
        fig_cum.update_layout(height=380, hovermode="x unified")
        st.plotly_chart(fig_cum, key="cum_chart")

    with col_growth:
        st.subheader("Crecimiento Mensual %")
        monthly_rev = unique_sales.groupby("year_month")["sale_total"].sum().reset_index()
        monthly_rev.columns = ["Mes", "Ingresos"]
        monthly_rev["Crecimiento"] = monthly_rev["Ingresos"].pct_change() * 100
        monthly_rev = monthly_rev.dropna()
        colors_growth = ["#2ec4b6" if x >= 0 else "#ee6c4d" for x in monthly_rev["Crecimiento"]]
        fig_growth = go.Figure(go.Bar(
            x=monthly_rev["Mes"], y=monthly_rev["Crecimiento"],
            marker_color=colors_growth,
        ))
        fig_growth.update_layout(height=380, yaxis_title="Crecimiento %", hovermode="x unified")
        st.plotly_chart(fig_growth, key="growth_chart")

    # Ticket size distribution
    st.subheader("Distribucion de Ticket")
    col_hist, col_box = st.columns(2)
    with col_hist:
        valid_tickets = unique_sales[unique_sales["sale_total"] > 0]["sale_total"]
        p99 = valid_tickets.quantile(0.99)
        fig_hist = px.histogram(valid_tickets[valid_tickets <= p99], nbins=50,
                                color_discrete_sequence=["#ff5023"],
                                labels={"value": "Monto ($)", "count": "Frecuencia"})
        fig_hist.update_layout(height=350, title="Histograma de Ticket", showlegend=False)
        st.plotly_chart(fig_hist, key="hist_chart")
    with col_box:
        ticket_by_type = unique_sales[unique_sales["sale_total"] > 0][["sale_type","sale_total"]]
        fig_box = px.box(ticket_by_type, x="sale_type", y="sale_total",
                         color="sale_type", color_discrete_sequence=COLORS)
        fig_box.update_layout(height=350, title="Ticket por Tipo de Venta", showlegend=False,
                              yaxis_range=[0, ticket_by_type["sale_total"].quantile(0.95)])
        st.plotly_chart(fig_box, key="box_chart")


# ==================== TAB: PRODUCTOS ====================
with tab_products:

    st.subheader("Analisis de Productos")

    # Top products by revenue and quantity side by side
    col_pr, col_pq = st.columns(2)

    with col_pr:
        st.markdown("**Top 20 por Ingresos**")
        top_rev = fdf.groupby("product_name").agg(
            revenue=("item_revenue","sum"), qty=("item_quantity","sum")
        ).sort_values("revenue", ascending=False).head(20).reset_index()
        fig_tr = px.bar(top_rev, x="revenue", y="product_name", orientation="h",
                        color_discrete_sequence=["#ff5023"],
                        text=top_rev["revenue"].apply(lambda x: f"${x:,.0f}"))
        fig_tr.update_layout(yaxis=dict(autorange="reversed"), height=550, xaxis_title="Ingresos ($)")
        fig_tr.update_traces(textposition="outside")
        st.plotly_chart(fig_tr, key="tr_chart")

    with col_pq:
        st.markdown("**Top 20 por Cantidad**")
        top_qty = fdf.groupby("product_name").agg(
            qty=("item_quantity","sum"), revenue=("item_revenue","sum")
        ).sort_values("qty", ascending=False).head(20).reset_index()
        fig_tq = px.bar(top_qty, x="qty", y="product_name", orientation="h",
                        color_discrete_sequence=["#2ec4b6"],
                        text=top_qty["qty"].apply(lambda x: f"{x:,.0f}"))
        fig_tq.update_layout(yaxis=dict(autorange="reversed"), height=550, xaxis_title="Cantidad")
        fig_tq.update_traces(textposition="outside")
        st.plotly_chart(fig_tq, key="tq_chart")

    st.divider()

    # Category breakdown
    col_cd, col_ct = st.columns(2)

    with col_cd:
        st.subheader("Ventas por Categoria")
        cat_rev = fdf.groupby("product_category").agg(
            revenue=("item_revenue","sum"), qty=("item_quantity","sum"), cost=("item_total_cost","sum")
        ).sort_values("revenue", ascending=False).reset_index()
        cat_rev["margin_pct"] = ((cat_rev["revenue"] - cat_rev["cost"]) / cat_rev["revenue"] * 100).round(1)
        fig_cd = px.pie(cat_rev, values="revenue", names="product_category",
                        hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
        fig_cd.update_traces(textinfo="label+percent+value", texttemplate="%{label}<br>%{percent}<br>$%{value:,.0f}")
        fig_cd.update_layout(height=400)
        st.plotly_chart(fig_cd, key="cd_chart")

    with col_ct:
        st.subheader("Tendencia por Categoria")
        cat_trend = fdf.groupby(["year_month","product_category"])["item_revenue"].sum().reset_index()
        cat_trend.columns = ["Mes","Categoria","Ingresos"]
        fig_ct = px.area(cat_trend, x="Mes", y="Ingresos", color="Categoria",
                         color_discrete_sequence=px.colors.qualitative.Set2)
        fig_ct.update_layout(height=400, hovermode="x unified")
        st.plotly_chart(fig_ct, key="ct_chart")

    st.divider()

    # Product treemap
    st.subheader("Treemap de Productos")
    tree_data = fdf.groupby(["product_category","product_name"]).agg(
        revenue=("item_revenue","sum")
    ).reset_index()
    tree_data = tree_data[tree_data["revenue"] > 0]
    fig_tree = px.treemap(tree_data, path=["product_category","product_name"], values="revenue",
                          color="revenue", color_continuous_scale="Oranges")
    fig_tree.update_layout(height=500)
    st.plotly_chart(fig_tree, key="tree_chart")

    st.divider()

    # Full product table
    st.subheader("Tabla Completa de Productos")
    prod_table = fdf.groupby(["product_category","product_name"]).agg(
        qty=("item_quantity","sum"),
        revenue=("item_revenue","sum"),
        cost=("item_total_cost","sum"),
        avg_price=("item_price","mean"),
    ).reset_index()
    prod_table["margin"] = prod_table["revenue"] - prod_table["cost"]
    prod_table["margin_pct"] = (prod_table["margin"] / prod_table["revenue"] * 100).round(1)
    prod_table = prod_table.sort_values("revenue", ascending=False)

    display_pt = prod_table.copy()
    for c in ["revenue","cost","margin","avg_price"]:
        display_pt[c] = display_pt[c].apply(lambda x: f"${x:,.0f}")
    display_pt["qty"] = display_pt["qty"].apply(lambda x: f"{x:,.0f}")
    display_pt["margin_pct"] = display_pt["margin_pct"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(
        display_pt.rename(columns={
            "product_category":"Categoria","product_name":"Producto",
            "qty":"Cantidad","revenue":"Ingresos","cost":"Costo",
            "margin":"Margen $","margin_pct":"Margen %","avg_price":"Precio Prom."
        }),
        hide_index=True, height=500,
    )


# ==================== TAB: PAGOS ====================
with tab_payments:

    st.subheader("Analisis de Metodos de Pago")

    pay_cols = unique_sales[["sale_id","date","year_month","payment_methods","payment_amounts"]]
    payments_df = build_payments_df(pay_cols["sale_id"], pay_cols)

    if not payments_df.empty:
        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.markdown("**Distribucion por Metodo**")
            pay_sum = payments_df.groupby("method")["amount"].sum().sort_values(ascending=False).reset_index()
            fig_p1 = px.pie(pay_sum, values="amount", names="method",
                            hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_p1.update_traces(textinfo="label+percent+value", texttemplate="%{label}<br>%{percent}<br>$%{value:,.0f}")
            fig_p1.update_layout(height=420)
            st.plotly_chart(fig_p1, key="p1_chart")

        with col_p2:
            st.markdown("**Conteo de Transacciones por Metodo**")
            pay_count = payments_df.groupby("method")["sale_id"].nunique().sort_values(ascending=False).reset_index()
            pay_count.columns = ["Metodo", "Transacciones"]
            fig_p2 = px.bar(pay_count, x="Metodo", y="Transacciones", color="Metodo",
                            color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_p2.update_layout(height=420, showlegend=False)
            st.plotly_chart(fig_p2, key="p2_chart")

        st.divider()

        st.subheader("Tendencia de Metodos de Pago")
        pay_trend = payments_df.groupby(["year_month","method"])["amount"].sum().reset_index()
        fig_pt = px.area(pay_trend, x="year_month", y="amount", color="method",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pt.update_layout(height=400, hovermode="x unified", xaxis_title="Mes", yaxis_title="Monto ($)")
        st.plotly_chart(fig_pt, key="pt_chart")

        st.divider()

        # Payment method share over time
        st.subheader("Participacion % de Metodos en el Tiempo")
        pay_share = pay_trend.copy()
        pay_total = pay_share.groupby("year_month")["amount"].transform("sum")
        pay_share["pct"] = (pay_share["amount"] / pay_total * 100).round(1)
        fig_ps = px.area(pay_share, x="year_month", y="pct", color="method",
                         color_discrete_sequence=px.colors.qualitative.Pastel, groupnorm="percent")
        fig_ps.update_layout(height=400, hovermode="x unified", yaxis_title="% del Total")
        st.plotly_chart(fig_ps, key="ps_chart")

        # Average payment per method
        st.divider()
        st.subheader("Monto Promedio por Metodo")
        pay_avg = payments_df.groupby("method")["amount"].mean().sort_values(ascending=False).reset_index()
        pay_avg.columns = ["Metodo", "Promedio"]
        fig_pa = px.bar(pay_avg, x="Metodo", y="Promedio", color="Metodo",
                        text=pay_avg["Promedio"].apply(lambda x: f"${x:,.0f}"),
                        color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pa.update_traces(textposition="outside")
        fig_pa.update_layout(height=380, showlegend=False, yaxis_title="Monto Promedio ($)")
        st.plotly_chart(fig_pa, key="pa_chart")
    else:
        st.info("No hay datos de pagos para los filtros seleccionados.")


# ==================== TAB: STAFF ====================
with tab_staff:

    st.subheader("Rendimiento por Mesero/a")

    waiter_stats = unique_sales.groupby("waiter").agg(
        ventas=("sale_id","nunique"),
        ingresos=("sale_total","sum"),
        ticket_prom=("sale_total","mean"),
    ).reset_index().sort_values("ingresos", ascending=False)

    # Items per waiter
    waiter_items = fdf.groupby("waiter")["item_quantity"].sum().reset_index()
    waiter_items.columns = ["waiter","items"]
    waiter_stats = waiter_stats.merge(waiter_items, on="waiter", how="left")

    col_w1, col_w2 = st.columns(2)

    with col_w1:
        st.markdown("**Ingresos por Mesero/a**")
        fig_w1 = px.bar(waiter_stats.head(15), x="ingresos", y="waiter", orientation="h",
                        color_discrete_sequence=["#ff5023"],
                        text=waiter_stats.head(15)["ingresos"].apply(lambda x: f"${x:,.0f}"))
        fig_w1.update_layout(yaxis=dict(autorange="reversed"), height=480)
        fig_w1.update_traces(textposition="outside")
        st.plotly_chart(fig_w1, key="w1_chart")

    with col_w2:
        st.markdown("**Ticket Promedio por Mesero/a**")
        w_sorted = waiter_stats.sort_values("ticket_prom", ascending=False).head(15)
        fig_w2 = px.bar(w_sorted, x="ticket_prom", y="waiter", orientation="h",
                        color_discrete_sequence=["#2ec4b6"],
                        text=w_sorted["ticket_prom"].apply(lambda x: f"${x:,.0f}"))
        fig_w2.update_layout(yaxis=dict(autorange="reversed"), height=480, xaxis_title="Ticket Promedio ($)")
        fig_w2.update_traces(textposition="outside")
        st.plotly_chart(fig_w2, key="w2_chart")

    st.divider()

    # Waiter performance table
    st.subheader("Tabla de Rendimiento")
    display_ws = waiter_stats.copy()
    display_ws["ingresos"] = display_ws["ingresos"].apply(lambda x: f"${x:,.0f}")
    display_ws["ticket_prom"] = display_ws["ticket_prom"].apply(lambda x: f"${x:,.0f}")
    display_ws["items"] = display_ws["items"].apply(lambda x: f"{x:,.0f}")
    st.dataframe(
        display_ws.rename(columns={
            "waiter":"Mesero/a","ventas":"Ventas","ingresos":"Ingresos",
            "ticket_prom":"Ticket Prom.","items":"Items Vendidos"
        }),
        hide_index=True, height=400,
    )

    st.divider()

    # Waiter activity over time
    st.subheader("Actividad de Staff en el Tiempo")
    waiter_time = unique_sales.groupby(["year_month","waiter"])["sale_id"].nunique().reset_index()
    waiter_time.columns = ["Mes","Mesero","Ventas"]
    top_waiters = waiter_stats.head(8)["waiter"].tolist()
    waiter_time_top = waiter_time[waiter_time["Mesero"].isin(top_waiters)]
    fig_wt = px.line(waiter_time_top, x="Mes", y="Ventas", color="Mesero",
                     markers=True, color_discrete_sequence=COLORS)
    fig_wt.update_layout(height=400, hovermode="x unified")
    st.plotly_chart(fig_wt, key="wt_chart")


# ==================== TAB: HORARIOS ====================
with tab_time:

    st.subheader("Patrones de Horario")
    day_labels = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miercoles",
                  "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sabado","Sunday":"Domingo"}

    # Heatmap
    st.markdown("**Mapa de Calor: Ingresos por Dia y Hora**")
    hm_data = fdf.copy()
    hm_data["day_label"] = hm_data["day_of_week"].map(day_labels)
    hm = hm_data.groupby(["day_num","day_label","hour"])["item_revenue"].sum().reset_index()
    hm_pivot = hm.pivot_table(index=["day_num","day_label"], columns="hour", values="item_revenue", fill_value=0)
    hm_pivot = hm_pivot.sort_index(level=0)

    fig_hm = go.Figure(data=go.Heatmap(
        z=hm_pivot.values,
        x=[f"{h}:00" for h in hm_pivot.columns],
        y=[label for _, label in hm_pivot.index],
        colorscale="YlOrRd",
        hovertemplate="Dia: %{y}<br>Hora: %{x}<br>Ingresos: $%{z:,.0f}<extra></extra>",
    ))
    fig_hm.update_layout(height=380)
    st.plotly_chart(fig_hm, key="hm_chart")

    st.divider()

    col_h1, col_h2 = st.columns(2)

    with col_h1:
        st.markdown("**Ingresos por Hora del Dia**")
        hourly = fdf.groupby("hour").agg(
            ingresos=("item_revenue","sum"), ventas=("sale_id","nunique")
        ).reset_index()
        fig_h1 = px.bar(hourly, x="hour", y="ingresos", color_discrete_sequence=["#ff5023"],
                        text=hourly["ventas"].apply(lambda x: f"{x:,}"))
        fig_h1.update_traces(textposition="outside")
        fig_h1.update_layout(height=380, xaxis_title="Hora", yaxis_title="Ingresos ($)")
        st.plotly_chart(fig_h1, key="h1_chart")

    with col_h2:
        st.markdown("**Ventas por Dia de Semana**")
        dow2 = unique_sales.copy()
        dow2["dia"] = dow2["day_of_week"].map(day_labels)
        dow2_agg = dow2.groupby(["day_num","dia"]).agg(
            ventas=("sale_id","nunique"), ingresos=("sale_total","sum")
        ).reset_index().sort_values("day_num")
        dow2_agg["ticket"] = dow2_agg["ingresos"] / dow2_agg["ventas"]
        fig_h2 = px.bar(dow2_agg, x="dia", y="ventas", color_discrete_sequence=["#2ec4b6"],
                        text=dow2_agg["ingresos"].apply(lambda x: f"${x:,.0f}"))
        fig_h2.update_traces(textposition="outside")
        fig_h2.update_layout(height=380, xaxis_title="", yaxis_title="Cantidad de Ventas")
        st.plotly_chart(fig_h2, key="h2_chart")

    st.divider()

    # Heatmap: count of sales
    st.markdown("**Mapa de Calor: Cantidad de Ventas por Dia y Hora**")
    hm2 = hm_data.drop_duplicates(subset="sale_id").groupby(["day_num","day_label","hour"])["sale_id"].nunique().reset_index()
    hm2_pivot = hm2.pivot_table(index=["day_num","day_label"], columns="hour", values="sale_id", fill_value=0)
    hm2_pivot = hm2_pivot.sort_index(level=0)
    fig_hm2 = go.Figure(data=go.Heatmap(
        z=hm2_pivot.values,
        x=[f"{h}:00" for h in hm2_pivot.columns],
        y=[label for _, label in hm2_pivot.index],
        colorscale="Blues",
        hovertemplate="Dia: %{y}<br>Hora: %{x}<br>Ventas: %{z:,}<extra></extra>",
    ))
    fig_hm2.update_layout(height=380)
    st.plotly_chart(fig_hm2, key="hm2_chart")


# ==================== TAB: RENTABILIDAD ====================
with tab_profit:

    st.subheader("Analisis de Rentabilidad")

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("**Margen Bruto % por Categoria**")
        cat_m = fdf.groupby("product_category").agg(
            revenue=("item_revenue","sum"), cost=("item_total_cost","sum")
        ).reset_index()
        cat_m["margin_pct"] = ((cat_m["revenue"] - cat_m["cost"]) / cat_m["revenue"] * 100).round(1)
        cat_m["margin_abs"] = cat_m["revenue"] - cat_m["cost"]
        cat_m = cat_m.sort_values("margin_pct", ascending=True)
        fig_m1 = px.bar(cat_m, x="margin_pct", y="product_category", orientation="h",
                        color="margin_pct", color_continuous_scale="RdYlGn", range_color=[0,100],
                        text=cat_m["margin_pct"].apply(lambda x: f"{x:.1f}%"))
        fig_m1.update_traces(textposition="outside")
        fig_m1.update_layout(height=380)
        st.plotly_chart(fig_m1, key="m1_chart")

    with col_m2:
        st.markdown("**Ganancia Bruta por Categoria ($)**")
        cat_m2 = cat_m.sort_values("margin_abs", ascending=True)
        fig_m2 = px.bar(cat_m2, x="margin_abs", y="product_category", orientation="h",
                        color_discrete_sequence=["#2ec4b6"],
                        text=cat_m2["margin_abs"].apply(lambda x: f"${x:,.0f}"))
        fig_m2.update_traces(textposition="outside")
        fig_m2.update_layout(height=380, xaxis_title="Ganancia ($)")
        st.plotly_chart(fig_m2, key="m2_chart")

    st.divider()

    # Margin over time
    st.subheader("Margen Bruto % en el Tiempo")
    margin_time = fdf.groupby("year_month").agg(
        revenue=("item_revenue","sum"), cost=("item_total_cost","sum")
    ).reset_index()
    margin_time["margin_pct"] = ((margin_time["revenue"] - margin_time["cost"]) / margin_time["revenue"] * 100).round(1)
    margin_time["margin_abs"] = margin_time["revenue"] - margin_time["cost"]

    fig_mt = go.Figure()
    fig_mt.add_trace(go.Bar(x=margin_time["year_month"], y=margin_time["margin_abs"],
                            name="Ganancia ($)", marker_color="rgba(46,196,182,0.6)"))
    fig_mt.add_trace(go.Scatter(x=margin_time["year_month"], y=margin_time["margin_pct"],
                                name="Margen %", yaxis="y2", line_color="#ff5023", mode="lines+markers"))
    fig_mt.update_layout(
        yaxis=dict(title="Ganancia ($)"),
        yaxis2=dict(title="Margen %", overlaying="y", side="right"),
        height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig_mt, key="mt_chart")

    st.divider()

    # Top/bottom margin products
    col_tp, col_bp = st.columns(2)

    prod_m = fdf[fdf["item_cost"] > 0].groupby("product_name").agg(
        revenue=("item_revenue","sum"), cost=("item_total_cost","sum"), qty=("item_quantity","sum")
    ).reset_index()
    prod_m["margin"] = prod_m["revenue"] - prod_m["cost"]
    prod_m["margin_pct"] = (prod_m["margin"] / prod_m["revenue"] * 100).round(1)

    with col_tp:
        st.markdown("**Top 15 Mas Rentables ($)**")
        top_m = prod_m.sort_values("margin", ascending=False).head(15)
        display_tm = top_m.copy()
        for c in ["revenue","cost","margin"]:
            display_tm[c] = display_tm[c].apply(lambda x: f"${x:,.0f}")
        display_tm["qty"] = display_tm["qty"].apply(lambda x: f"{x:,.0f}")
        display_tm["margin_pct"] = display_tm["margin_pct"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_tm.rename(columns={
            "product_name":"Producto","revenue":"Ingresos","cost":"Costo",
            "margin":"Ganancia","margin_pct":"Margen %","qty":"Cantidad"
        }), hide_index=True, height=450)

    with col_bp:
        st.markdown("**Top 15 Menor Margen %**")
        bot_m = prod_m[prod_m["qty"] > 10].sort_values("margin_pct", ascending=True).head(15)
        display_bm = bot_m.copy()
        for c in ["revenue","cost","margin"]:
            display_bm[c] = display_bm[c].apply(lambda x: f"${x:,.0f}")
        display_bm["qty"] = display_bm["qty"].apply(lambda x: f"{x:,.0f}")
        display_bm["margin_pct"] = display_bm["margin_pct"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_bm.rename(columns={
            "product_name":"Producto","revenue":"Ingresos","cost":"Costo",
            "margin":"Ganancia","margin_pct":"Margen %","qty":"Cantidad"
        }), hide_index=True, height=450)

    st.divider()

    # Revenue vs Cost vs Margin scatter
    st.subheader("Productos: Ingresos vs Margen % (tamano = cantidad)")
    scatter_data = prod_m[prod_m["qty"] > 5].copy()
    fig_sc = px.scatter(scatter_data, x="revenue", y="margin_pct", size="qty",
                        hover_name="product_name", color="margin_pct",
                        color_continuous_scale="RdYlGn", range_color=[0,100],
                        size_max=40)
    fig_sc.update_layout(height=450, xaxis_title="Ingresos ($)", yaxis_title="Margen %")
    st.plotly_chart(fig_sc, key="sc_chart")


# ==================== TAB: DETALLE ====================
with tab_detail:

    st.subheader("Datos Detallados")

    # Summary stats
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        st.markdown("**Resumen del Periodo**")
        st.write(f"- Ventas: **{total_sales:,}**")
        st.write(f"- Ingresos: **${total_revenue:,.0f}**")
        st.write(f"- Costo: **${total_item_cost:,.0f}**")
        st.write(f"- Ganancia bruta: **${gross_margin_abs:,.0f}**")
        st.write(f"- Descuentos: **${total_discounts:,.0f}**")
        st.write(f"- Propinas: **${total_tips:,.0f}**")
    with col_d2:
        st.markdown("**Promedios**")
        st.write(f"- Ticket promedio: **${avg_ticket:,.0f}**")
        st.write(f"- Items/ticket: **{items_per_ticket:.1f}**")
        st.write(f"- Ingreso diario: **${avg_daily_revenue:,.0f}**")
        st.write(f"- Ventas/dia: **{avg_daily_sales:.1f}**")
        st.write(f"- Duracion prom: **{avg_duration:.0f} min**")
    with col_d3:
        st.markdown("**Productos**")
        n_products = fdf["product_name"].nunique()
        n_categories = fdf["product_category"].nunique()
        n_waiters = fdf["waiter"].nunique()
        st.write(f"- Productos vendidos: **{n_products}**")
        st.write(f"- Categorias: **{n_categories}**")
        st.write(f"- Meseros activos: **{n_waiters}**")
        st.write(f"- Producto top: **{top_product}**")
        st.write(f"- Cancelaciones: **{canceled_count:,} ({cancel_rate:.1f}%)**")

    st.divider()

    # Expenses (if available)
    if not expenses_df.empty:
        st.subheader("Gastos")
        exp_total = pd.to_numeric(expenses_df["amount"], errors="coerce").sum()
        st.metric("Total Gastos", f"${exp_total:,.0f}")
        st.dataframe(expenses_df, hide_index=True, height=300)
        st.divider()

    # Raw sales data sample
    st.subheader("Ultimas 100 Ventas")
    recent = fdf.sort_values("created_at", ascending=False).head(100)[
        ["sale_id","created_at","sale_total","sale_type","sale_state","product_name",
         "product_category","item_quantity","item_price","waiter","payment_methods"]
    ]
    st.dataframe(recent, hide_index=True, height=500)


# ==================== FOOTER ====================
st.divider()
st.caption(
    f"Mocawa Cafe BI Dashboard | {total_sales:,} ventas | "
    f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')} | "
    f"Datos de FUDO POS"
)
