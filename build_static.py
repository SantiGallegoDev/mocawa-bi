"""
build_static.py — Pre-aggregate Mocawa Cafe data into static JSON for GitHub Pages dashboard.

Usage:
    python build_static.py

Reads:  fudo_sales.csv, fudo_expenses.csv
Writes: docs/data/{kpis,overview,products,payments,staff,time_patterns,profitability,detail}.json
"""

import json
import os
import math
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "docs", "data")
os.makedirs(OUT, exist_ok=True)


# ─── JSON encoder that handles numpy/pandas types ───────────────────────────
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            v = float(obj)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return super().default(obj)


def sanitize(obj):
    """Recursively replace NaN/Inf floats with None (JSON doesn't support NaN)."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def write_json(name, data):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sanitize(data), f, cls=NumpyEncoder, ensure_ascii=False)
    size = os.path.getsize(path)
    print(f"  {name:30s} {size/1024:7.1f} KB")


# ─── Load data ──────────────────────────────────────────────────────────────
print("Loading sales data...")
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
df["duration_min"] = (df["closed_at"] - df["created_at"]).dt.total_seconds() / 60

df["product_category"] = df["product_category"].fillna("Sin Categoria")
df["waiter"] = df["waiter"].fillna("Sin Asignar")
df["sale_type"] = df["sale_type"].fillna("UNKNOWN")
df["sale_state"] = df["sale_state"].fillna("UNKNOWN")
df["product_name"] = df["product_name"].fillna("Sin Producto")

print(f"  Total rows: {len(df):,}")

# ─── Filter to CLOSED + 2025 only ─────────────────────────────────────────
fdf = df[(df["sale_state"] == "CLOSED") & (df["year"] == 2025)].copy()
unique_sales = fdf.drop_duplicates(subset="sale_id")

from datetime import date
min_date = date(2025, 1, 1)
max_date = date(2025, 12, 31)
days_in_range = (max_date - min_date).days + 1  # 365

print(f"  CLOSED rows: {len(fdf):,}")
print(f"  Unique sales: {len(unique_sales):,}")
print(f"  Date range: {min_date} to {max_date} ({days_in_range} days)")

# ─── Load expenses ──────────────────────────────────────────────────────────
expenses_path = os.path.join(BASE, "fudo_expenses.csv")
if os.path.exists(expenses_path):
    expenses_df = pd.read_csv(expenses_path)
else:
    expenses_df = pd.DataFrame()

# ─── Build payments ─────────────────────────────────────────────────────────
print("Building payments data...")
pay_cols = unique_sales[["sale_id", "date", "year_month", "payment_methods", "payment_amounts"]]
pay_rows = []
for _, row in pay_cols.iterrows():
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
        pay_rows.append({
            "sale_id": row["sale_id"],
            "date": row["date"],
            "year_month": row["year_month"],
            "method": m,
            "amount": a_val,
        })
payments_df = pd.DataFrame(pay_rows)
print(f"  Payment rows: {len(payments_df):,}")


# ═══════════════════════════════════════════════════════════════════════════
#  1. KPIs
# ═══════════════════════════════════════════════════════════════════════════
print("\nBuilding KPIs...")
total_revenue = float(unique_sales["sale_total"].sum())
total_sales = int(unique_sales["sale_id"].nunique())
avg_ticket = total_revenue / total_sales if total_sales > 0 else 0
total_items = float(fdf["item_quantity"].sum())
total_item_revenue = float(fdf["item_revenue"].sum())
total_item_cost = float(fdf["item_total_cost"].sum())
gross_margin_pct = ((total_item_revenue - total_item_cost) / total_item_revenue * 100) if total_item_revenue > 0 else 0
gross_margin_abs = total_item_revenue - total_item_cost
avg_daily_revenue = total_revenue / days_in_range
avg_daily_sales = total_sales / days_in_range
items_per_ticket = total_items / total_sales if total_sales > 0 else 0
total_discounts = float(unique_sales["discount_total"].sum())
total_tips = float(unique_sales["tips_total"].sum())

# Canceled stats (across all states in same date range)
all_unique = df.drop_duplicates(subset="sale_id")
canceled_count = int(all_unique[all_unique["sale_state"] == "CANCELED"]["sale_id"].nunique())
total_all = int(all_unique["sale_id"].nunique())
cancel_rate = (canceled_count / total_all * 100) if total_all > 0 else 0

# Avg duration
valid_dur = unique_sales[(unique_sales["duration_min"] > 0) & (unique_sales["duration_min"] < 480)]
avg_duration = float(valid_dur["duration_min"].mean()) if len(valid_dur) > 0 else 0

# Peak hour
peak_hour = int(fdf.groupby("hour")["item_revenue"].sum().idxmax()) if not fdf.empty else 0
peak_hour_label = f"{peak_hour}:00"

# Top product
top_product = fdf.groupby("product_name")["item_quantity"].sum().idxmax() if not fdf.empty else "-"

write_json("kpis.json", {
    "total_revenue": total_revenue,
    "total_sales": total_sales,
    "avg_ticket": avg_ticket,
    "total_items": total_items,
    "gross_margin_pct": round(gross_margin_pct, 1),
    "gross_margin_abs": gross_margin_abs,
    "avg_daily_revenue": avg_daily_revenue,
    "avg_daily_sales": round(avg_daily_sales, 1),
    "items_per_ticket": round(items_per_ticket, 1),
    "peak_hour_label": peak_hour_label,
    "canceled_count": canceled_count,
    "cancel_rate": round(cancel_rate, 1),
    "avg_duration": round(avg_duration, 0),
    "total_discounts": total_discounts,
    "total_tips": total_tips,
    "min_date": str(min_date),
    "max_date": str(max_date),
    "days_in_range": days_in_range,
})


# ═══════════════════════════════════════════════════════════════════════════
#  2. Overview (Resumen General)
# ═══════════════════════════════════════════════════════════════════════════
print("Building overview...")

# Revenue over time — daily, weekly, monthly
def date_str(d):
    return str(d)

rev_daily = unique_sales.groupby("date").agg(
    ingresos=("sale_total", "sum"), ventas=("sale_id", "nunique")
).reset_index()
rev_daily["date"] = rev_daily["date"].apply(date_str)

rev_weekly = unique_sales.groupby("week").agg(
    ingresos=("sale_total", "sum"), ventas=("sale_id", "nunique")
).reset_index()
rev_weekly["week"] = rev_weekly["week"].apply(date_str)

rev_monthly = unique_sales.groupby("year_month").agg(
    ingresos=("sale_total", "sum"), ventas=("sale_id", "nunique")
).reset_index()

# Year-over-year
month_names = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
               7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
yoy = unique_sales.groupby(["year", "month_num"])["sale_total"].sum().reset_index()
yoy.columns = ["year", "month", "ingresos"]
yoy["year"] = yoy["year"].astype(str)

# Sale type over time
type_trend = unique_sales.groupby(["year_month", "sale_type"])["sale_id"].nunique().reset_index()
type_trend.columns = ["mes", "tipo", "ventas"]

# Day-of-week revenue
day_labels_map = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miercoles",
                  "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sabado","Sunday":"Domingo"}
dow = unique_sales.copy()
dow["dia"] = dow["day_of_week"].map(day_labels_map)
dow_rev = dow.groupby(["day_num", "dia"]).agg(
    ingresos=("sale_total", "sum"), ventas=("sale_id", "nunique")
).reset_index().sort_values("day_num")

# Sale type distribution (pie)
type_dist = unique_sales.groupby("sale_type").agg(
    ventas=("sale_id", "nunique"), ingresos=("sale_total", "sum")
).reset_index()

# Cumulative revenue
cum_rev = unique_sales.groupby("year_month")["sale_total"].sum().cumsum().reset_index()
cum_rev.columns = ["mes", "acumulado"]

# Monthly growth
monthly_rev = unique_sales.groupby("year_month")["sale_total"].sum().reset_index()
monthly_rev.columns = ["mes", "ingresos"]
monthly_rev["crecimiento"] = monthly_rev["ingresos"].pct_change() * 100
growth = monthly_rev.dropna(subset=["crecimiento"])

# Ticket histogram (pre-computed bins)
valid_tickets = unique_sales[unique_sales["sale_total"] > 0]["sale_total"]
p99 = float(valid_tickets.quantile(0.99))
clipped = valid_tickets[valid_tickets <= p99]
hist_counts, hist_edges = np.histogram(clipped, bins=50)

# Boxplot stats per sale_type
boxplot_data = []
for st_name, grp in unique_sales[unique_sales["sale_total"] > 0].groupby("sale_type"):
    vals = grp["sale_total"]
    q1, med, q3 = float(vals.quantile(0.25)), float(vals.median()), float(vals.quantile(0.75))
    iqr = q3 - q1
    whisker_lo = float(vals[vals >= q1 - 1.5 * iqr].min())
    whisker_hi = float(vals[vals <= q3 + 1.5 * iqr].max())
    p95 = float(vals.quantile(0.95))
    boxplot_data.append({
        "sale_type": st_name, "q1": q1, "median": med, "q3": q3,
        "whisker_lo": whisker_lo, "whisker_hi": whisker_hi, "p95": p95,
    })

write_json("overview.json", {
    "rev_daily": {"dates": rev_daily["date"].tolist(), "ingresos": rev_daily["ingresos"].tolist(), "ventas": rev_daily["ventas"].tolist()},
    "rev_weekly": {"dates": rev_weekly["week"].tolist(), "ingresos": rev_weekly["ingresos"].tolist(), "ventas": rev_weekly["ventas"].tolist()},
    "rev_monthly": {"dates": rev_monthly["year_month"].tolist(), "ingresos": rev_monthly["ingresos"].tolist(), "ventas": rev_monthly["ventas"].tolist()},
    "yoy": {"years": sorted(yoy["year"].unique().tolist()), "data": yoy.to_dict("records")},
    "month_names": month_names,
    "type_trend": type_trend.to_dict("records"),
    "dow": dow_rev.to_dict("records"),
    "type_dist": type_dist.to_dict("records"),
    "cum_rev": {"dates": cum_rev["mes"].tolist(), "values": cum_rev["acumulado"].tolist()},
    "growth": {"dates": growth["mes"].tolist(), "values": growth["crecimiento"].tolist()},
    "histogram": {"edges": hist_edges.tolist(), "counts": hist_counts.tolist()},
    "boxplot": boxplot_data,
})


# ═══════════════════════════════════════════════════════════════════════════
#  3. Products
# ═══════════════════════════════════════════════════════════════════════════
print("Building products...")

# Top 20 by revenue
top_rev = fdf.groupby("product_name").agg(
    revenue=("item_revenue", "sum"), qty=("item_quantity", "sum")
).sort_values("revenue", ascending=False).head(20).reset_index()

# Top 20 by quantity
top_qty = fdf.groupby("product_name").agg(
    qty=("item_quantity", "sum"), revenue=("item_revenue", "sum")
).sort_values("qty", ascending=False).head(20).reset_index()

# Category breakdown
cat_rev = fdf.groupby("product_category").agg(
    revenue=("item_revenue", "sum"), qty=("item_quantity", "sum"), cost=("item_total_cost", "sum")
).sort_values("revenue", ascending=False).reset_index()
cat_rev["margin_pct"] = ((cat_rev["revenue"] - cat_rev["cost"]) / cat_rev["revenue"] * 100).round(1)

# Category trend
cat_trend = fdf.groupby(["year_month", "product_category"])["item_revenue"].sum().reset_index()
cat_trend.columns = ["mes", "categoria", "ingresos"]

# Treemap data
tree_data = fdf.groupby(["product_category", "product_name"]).agg(
    revenue=("item_revenue", "sum")
).reset_index()
tree_data = tree_data[tree_data["revenue"] > 0]

# Full product table
prod_table = fdf.groupby(["product_category", "product_name"]).agg(
    qty=("item_quantity", "sum"),
    revenue=("item_revenue", "sum"),
    cost=("item_total_cost", "sum"),
    avg_price=("item_price", "mean"),
).reset_index()
prod_table["margin"] = prod_table["revenue"] - prod_table["cost"]
prod_table["margin_pct"] = (prod_table["margin"] / prod_table["revenue"] * 100).round(1)
prod_table = prod_table.sort_values("revenue", ascending=False)

write_json("products.json", {
    "top_revenue": top_rev.to_dict("records"),
    "top_qty": top_qty.to_dict("records"),
    "category_breakdown": cat_rev.to_dict("records"),
    "category_trend": cat_trend.to_dict("records"),
    "treemap": tree_data.to_dict("records"),
    "product_table": prod_table.to_dict("records"),
})


# ═══════════════════════════════════════════════════════════════════════════
#  4. Payments
# ═══════════════════════════════════════════════════════════════════════════
print("Building payments...")

if not payments_df.empty:
    pay_sum = payments_df.groupby("method")["amount"].sum().sort_values(ascending=False).reset_index()
    pay_count = payments_df.groupby("method")["sale_id"].nunique().sort_values(ascending=False).reset_index()
    pay_count.columns = ["method", "transactions"]
    pay_trend = payments_df.groupby(["year_month", "method"])["amount"].sum().reset_index()

    # Payment share %
    pay_share = pay_trend.copy()
    pay_total = pay_share.groupby("year_month")["amount"].transform("sum")
    pay_share["pct"] = (pay_share["amount"] / pay_total * 100).round(1)

    pay_avg = payments_df.groupby("method")["amount"].mean().sort_values(ascending=False).reset_index()
    pay_avg.columns = ["method", "avg_amount"]

    write_json("payments.json", {
        "distribution": pay_sum.to_dict("records"),
        "transaction_count": pay_count.to_dict("records"),
        "trend": pay_trend.to_dict("records"),
        "share": pay_share.to_dict("records"),
        "avg_per_method": pay_avg.to_dict("records"),
    })
else:
    write_json("payments.json", {
        "distribution": [], "transaction_count": [], "trend": [], "share": [], "avg_per_method": [],
    })


# ═══════════════════════════════════════════════════════════════════════════
#  5. Staff
# ═══════════════════════════════════════════════════════════════════════════
print("Building staff...")

waiter_stats = unique_sales.groupby("waiter").agg(
    ventas=("sale_id", "nunique"),
    ingresos=("sale_total", "sum"),
    ticket_prom=("sale_total", "mean"),
).reset_index().sort_values("ingresos", ascending=False)

waiter_items = fdf.groupby("waiter")["item_quantity"].sum().reset_index()
waiter_items.columns = ["waiter", "items"]
waiter_stats = waiter_stats.merge(waiter_items, on="waiter", how="left")

# Waiter activity over time (top 8)
waiter_time = unique_sales.groupby(["year_month", "waiter"])["sale_id"].nunique().reset_index()
waiter_time.columns = ["mes", "mesero", "ventas"]
top_waiters = waiter_stats.head(8)["waiter"].tolist()
waiter_time_top = waiter_time[waiter_time["mesero"].isin(top_waiters)]

# Monthly waiter performance with duration
valid_sales = unique_sales[(unique_sales["duration_min"] > 0) & (unique_sales["duration_min"] < 480)].copy()
waiter_monthly = valid_sales.groupby(["year_month", "waiter"]).agg(
    ventas=("sale_id", "nunique"),
    ingresos=("sale_total", "sum"),
    ticket_prom=("sale_total", "mean"),
    duracion_prom=("duration_min", "mean"),
).reset_index()
waiter_monthly["duracion_prom"] = waiter_monthly["duracion_prom"].round(1)
waiter_monthly["ticket_prom"] = waiter_monthly["ticket_prom"].round(0)
# Only keep waiters with meaningful activity
waiter_monthly = waiter_monthly[waiter_monthly["ventas"] >= 5]
waiter_monthly = waiter_monthly.sort_values(["year_month", "ingresos"], ascending=[True, False])

# Get all months for the selector
all_months = sorted(waiter_monthly["year_month"].unique().tolist())

write_json("staff.json", {
    "waiter_stats": waiter_stats.to_dict("records"),
    "waiter_time": waiter_time_top.to_dict("records"),
    "top_waiters": top_waiters,
    "waiter_monthly": waiter_monthly.to_dict("records"),
    "all_months": all_months,
})


# ═══════════════════════════════════════════════════════════════════════════
#  6. Time patterns
# ═══════════════════════════════════════════════════════════════════════════
print("Building time patterns...")

day_labels_map2 = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miercoles",
                   "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sabado","Sunday":"Domingo"}

# Revenue heatmap (day x hour)
hm_data = fdf.copy()
hm_data["day_label"] = hm_data["day_of_week"].map(day_labels_map2)
hm = hm_data.groupby(["day_num", "day_label", "hour"])["item_revenue"].sum().reset_index()
hm_pivot = hm.pivot_table(index=["day_num", "day_label"], columns="hour", values="item_revenue", fill_value=0)
hm_pivot = hm_pivot.sort_index(level=0)

hm_hours = [int(h) for h in hm_pivot.columns.tolist()]
hm_days = [label for _, label in hm_pivot.index]
hm_z = hm_pivot.values.tolist()

# Sales count heatmap (day x hour)
hm2 = hm_data.drop_duplicates(subset="sale_id").groupby(["day_num", "day_label", "hour"])["sale_id"].nunique().reset_index()
hm2_pivot = hm2.pivot_table(index=["day_num", "day_label"], columns="hour", values="sale_id", fill_value=0)
hm2_pivot = hm2_pivot.sort_index(level=0)

hm2_hours = [int(h) for h in hm2_pivot.columns.tolist()]
hm2_days = [label for _, label in hm2_pivot.index]
hm2_z = hm2_pivot.values.tolist()

# Hourly revenue + count
hourly = fdf.groupby("hour").agg(
    ingresos=("item_revenue", "sum"), ventas=("sale_id", "nunique")
).reset_index()

# Day of week sales (from unique_sales)
dow2 = unique_sales.copy()
dow2["dia"] = dow2["day_of_week"].map(day_labels_map2)
dow2_agg = dow2.groupby(["day_num", "dia"]).agg(
    ventas=("sale_id", "nunique"), ingresos=("sale_total", "sum")
).reset_index().sort_values("day_num")

write_json("time_patterns.json", {
    "heatmap_revenue": {"hours": hm_hours, "days": hm_days, "z": hm_z},
    "heatmap_sales": {"hours": hm2_hours, "days": hm2_days, "z": hm2_z},
    "hourly": hourly.to_dict("records"),
    "dow": dow2_agg.to_dict("records"),
})


# ═══════════════════════════════════════════════════════════════════════════
#  7. Profitability
# ═══════════════════════════════════════════════════════════════════════════
print("Building profitability...")

# Margin % by category
cat_m = fdf.groupby("product_category").agg(
    revenue=("item_revenue", "sum"), cost=("item_total_cost", "sum")
).reset_index()
cat_m["margin_pct"] = ((cat_m["revenue"] - cat_m["cost"]) / cat_m["revenue"] * 100).round(1)
cat_m["margin_abs"] = cat_m["revenue"] - cat_m["cost"]

# Margin over time
margin_time = fdf.groupby("year_month").agg(
    revenue=("item_revenue", "sum"), cost=("item_total_cost", "sum")
).reset_index()
margin_time["margin_pct"] = ((margin_time["revenue"] - margin_time["cost"]) / margin_time["revenue"] * 100).round(1)
margin_time["margin_abs"] = margin_time["revenue"] - margin_time["cost"]

# Product margin table (only products with cost > 0)
prod_m = fdf[fdf["item_cost"] > 0].groupby("product_name").agg(
    revenue=("item_revenue", "sum"), cost=("item_total_cost", "sum"), qty=("item_quantity", "sum")
).reset_index()
prod_m["margin"] = prod_m["revenue"] - prod_m["cost"]
prod_m["margin_pct"] = (prod_m["margin"] / prod_m["revenue"] * 100).round(1)

top_margin = prod_m.sort_values("margin", ascending=False).head(15)
bot_margin = prod_m[prod_m["qty"] > 10].sort_values("margin_pct", ascending=True).head(15)

# Scatter data (products with qty > 5)
scatter_data = prod_m[prod_m["qty"] > 5][["product_name", "revenue", "margin_pct", "qty"]].copy()

write_json("profitability.json", {
    "category_margin": cat_m.sort_values("margin_pct", ascending=True).to_dict("records"),
    "category_profit": cat_m.sort_values("margin_abs", ascending=True).to_dict("records"),
    "margin_time": margin_time.to_dict("records"),
    "top_margin": top_margin.to_dict("records"),
    "bottom_margin": bot_margin.to_dict("records"),
    "scatter": scatter_data.to_dict("records"),
})


# ═══════════════════════════════════════════════════════════════════════════
#  8. Detail
# ═══════════════════════════════════════════════════════════════════════════
print("Building detail...")

n_products = int(fdf["product_name"].nunique())
n_categories = int(fdf["product_category"].nunique())
n_waiters = int(fdf["waiter"].nunique())

# Recent 100 sales
recent = fdf.sort_values("created_at", ascending=False).head(100)[
    ["sale_id", "created_at", "sale_total", "sale_type", "sale_state", "product_name",
     "product_category", "item_quantity", "item_price", "waiter", "payment_methods"]
].copy()
recent["created_at"] = recent["created_at"].dt.strftime("%Y-%m-%d %H:%M")

# Expenses
if not expenses_df.empty:
    exp_total = float(pd.to_numeric(expenses_df["amount"], errors="coerce").sum())
    expenses_list = expenses_df.fillna("").to_dict("records")
else:
    exp_total = 0
    expenses_list = []

write_json("detail.json", {
    "summary": {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_item_cost": total_item_cost,
        "gross_margin_abs": gross_margin_abs,
        "total_discounts": total_discounts,
        "total_tips": total_tips,
        "avg_ticket": avg_ticket,
        "items_per_ticket": round(items_per_ticket, 1),
        "avg_daily_revenue": avg_daily_revenue,
        "avg_daily_sales": round(avg_daily_sales, 1),
        "avg_duration": round(avg_duration, 0),
        "n_products": n_products,
        "n_categories": n_categories,
        "n_waiters": n_waiters,
        "top_product": top_product,
        "canceled_count": canceled_count,
        "cancel_rate": round(cancel_rate, 1),
    },
    "expenses": {"total": exp_total, "rows": expenses_list},
    "recent_sales": recent.to_dict("records"),
})

print("\nDone! All JSON files written to docs/data/")
total_size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".json"))
print(f"Total size: {total_size/1024:.1f} KB")
