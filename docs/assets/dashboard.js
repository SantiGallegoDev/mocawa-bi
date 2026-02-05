/* ═══════════════════════════════════════════════════════════
   Mocawa Cafe — Static Dashboard JS
   ═══════════════════════════════════════════════════════════ */

const COLORS = ["#ff5023","#ff8c61","#ffc09f","#2ec4b6","#3d5a80","#ee6c4d","#293241","#98c1d9"];
const PASTEL = Plotly.d3 ? null : ["#b5e8d5","#f9d5bb","#d4a5ff","#a5d8ff","#ffd6a5","#ffadad","#caffbf","#bdb2ff"];
const SET2 = ["#66c2a5","#fc8d62","#8da0cb","#e78ac3","#a6d854","#ffd92f","#e5c494","#b3b3b3"];

const plotlyLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#fafafa", size: 12 },
    margin: { l: 50, r: 50, t: 30, b: 50 },
    xaxis: { gridcolor: "#2a2a3e", zerolinecolor: "#2a2a3e" },
    yaxis: { gridcolor: "#2a2a3e", zerolinecolor: "#2a2a3e" },
};
const plotlyConfig = { responsive: true, displayModeBar: false };

// ─── Helpers ──────────────────────────────────────────────
const cache = {};
async function fetchJSON(name) {
    if (cache[name]) return cache[name];
    const resp = await fetch(`data/${name}`);
    const data = await resp.json();
    cache[name] = data;
    return data;
}

function fmt$(v) {
    if (v == null) return "—";
    return "$" + Math.round(v).toLocaleString("es-CO");
}
function fmtN(v, d) {
    if (v == null) return "—";
    if (d !== undefined) return Number(v).toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
    return Math.round(v).toLocaleString("es-CO");
}
function fmtPct(v) {
    if (v == null) return "—";
    return v.toFixed(1) + "%";
}

function L(base, overrides) {
    return Object.assign({}, plotlyLayout, overrides, {
        xaxis: Object.assign({}, plotlyLayout.xaxis, (overrides && overrides.xaxis) || {}),
        yaxis: Object.assign({}, plotlyLayout.yaxis, (overrides && overrides.yaxis) || {}),
    });
}

function buildTable(headers, rows, alignments) {
    let html = '<table class="data-table"><thead><tr>';
    headers.forEach((h, i) => {
        const cls = (alignments && alignments[i] === "r") ? ' class="num"' : "";
        html += `<th${cls}>${h}</th>`;
    });
    html += "</tr></thead><tbody>";
    rows.forEach(row => {
        html += "<tr>";
        row.forEach((cell, i) => {
            const cls = (alignments && alignments[i] === "r") ? ' class="num"' : "";
            html += `<td${cls}>${cell}</td>`;
        });
        html += "</tr>";
    });
    html += "</tbody></table>";
    return html;
}

// ─── KPI Rendering ────────────────────────────────────────
async function renderKPIs() {
    const d = await fetchJSON("kpis.json");

    const setKPI = (id, val) => {
        const el = document.querySelector(`#${id} .kpi-value`);
        if (el) el.textContent = val;
    };

    setKPI("kpi-revenue", fmt$(d.total_revenue));
    setKPI("kpi-sales", fmtN(d.total_sales));
    setKPI("kpi-ticket", fmt$(d.avg_ticket));
    setKPI("kpi-items", fmtN(d.total_items));
    setKPI("kpi-margin", fmtPct(d.gross_margin_pct));
    setKPI("kpi-profit", fmt$(d.gross_margin_abs));
    setKPI("kpi-daily-rev", fmt$(d.avg_daily_revenue));
    setKPI("kpi-daily-sales", fmtN(d.avg_daily_sales, 1));
    setKPI("kpi-items-ticket", fmtN(d.items_per_ticket, 1));
    setKPI("kpi-peak", d.peak_hour_label);
    setKPI("kpi-canceled", fmtN(d.canceled_count));
    setKPI("kpi-duration", Math.round(d.avg_duration) + " min");

    const deltaEl = document.querySelector("#kpi-canceled .kpi-delta");
    if (deltaEl) deltaEl.textContent = fmtPct(d.cancel_rate);

    document.getElementById("dateRange").textContent =
        `Datos: ${d.min_date} a ${d.max_date} (${d.days_in_range} dias) — Solo ventas CLOSED`;

    document.getElementById("footer").textContent =
        `Mocawa Cafe BI Dashboard | ${fmtN(d.total_sales)} ventas | ${d.min_date} a ${d.max_date} | Datos de FUDO POS`;
}

// ─── Tab Switching ────────────────────────────────────────
const loadedTabs = {};

document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        btn.classList.add("active");
        const tab = btn.dataset.tab;
        document.getElementById("tab-" + tab).classList.add("active");
        loadTab(tab);
    });
});

function loadTab(tab) {
    if (loadedTabs[tab]) return;
    loadedTabs[tab] = true;
    const renderers = {
        overview: renderOverview,
        products: renderProducts,
        payments: renderPayments,
        staff: renderStaff,
        time: renderTime,
        profit: renderProfit,
        detail: renderDetail,
    };
    if (renderers[tab]) renderers[tab]();
}

// ═══════════════════════════════════════════════════════════
//  TAB: OVERVIEW
// ═══════════════════════════════════════════════════════════
let overviewData = null;

async function renderOverview() {
    const d = await fetchJSON("overview.json");
    overviewData = d;

    renderRevenueChart("monthly");
    renderYoY(d);
    renderTypeTrend(d);
    renderDoW(d);
    renderTypeDist(d);
    renderCumulative(d);
    renderGrowth(d);
    renderHistogram(d);
    renderBoxplot(d);

    // Granularity toggle
    document.querySelectorAll('#granularity input[name="gran"]').forEach(radio => {
        radio.addEventListener("change", () => renderRevenueChart(radio.value));
    });
}

function renderRevenueChart(gran) {
    const d = overviewData;
    const src = gran === "daily" ? d.rev_daily : gran === "weekly" ? d.rev_weekly : d.rev_monthly;
    const traces = [
        {
            x: src.dates, y: src.ingresos, name: "Ingresos",
            type: "scatter", fill: "tozeroy", fillcolor: "rgba(255,80,35,0.1)",
            line: { color: "#ff5023" },
        },
        {
            x: src.dates, y: src.ventas, name: "# Ventas",
            type: "bar", marker: { color: "rgba(46,196,182,0.5)" },
            yaxis: "y2",
        },
    ];
    const layout = L({
        yaxis: { title: "Ingresos ($)", gridcolor: "#2a2a3e" },
        yaxis2: { title: "# Ventas", overlaying: "y", side: "right", gridcolor: "#2a2a3e" },
        hovermode: "x unified",
        height: 420,
        legend: { orientation: "h", y: 1.12 },
    });
    Plotly.react("chart-revenue", traces, layout, plotlyConfig);
}

function renderYoY(d) {
    const traces = [];
    d.yoy.years.forEach((yr, i) => {
        const yrData = d.yoy.data.filter(r => r.year === yr);
        traces.push({
            x: yrData.map(r => r.month),
            y: yrData.map(r => r.ingresos),
            name: yr, mode: "lines+markers",
            line: { color: COLORS[i % COLORS.length] },
            marker: { color: COLORS[i % COLORS.length] },
        });
    });
    const tickVals = [1,2,3,4,5,6,7,8,9,10,11,12];
    const tickText = Object.values(d.month_names);
    const layout = L({
        xaxis: { tickmode: "array", tickvals: tickVals, ticktext: tickText, gridcolor: "#2a2a3e" },
        height: 400, hovermode: "x unified",
    });
    Plotly.react("chart-yoy", traces, layout, plotlyConfig);
}

function renderTypeTrend(d) {
    const types = [...new Set(d.type_trend.map(r => r.tipo))];
    const traces = types.map((t, i) => {
        const rows = d.type_trend.filter(r => r.tipo === t);
        return {
            x: rows.map(r => r.mes), y: rows.map(r => r.ventas),
            name: t, stackgroup: "one", fillcolor: SET2[i % SET2.length] + "80",
            line: { color: SET2[i % SET2.length] },
        };
    });
    Plotly.react("chart-type-trend", traces, L({ height: 400, hovermode: "x unified" }), plotlyConfig);
}

function renderDoW(d) {
    const traces = [{
        x: d.dow.map(r => r.dia), y: d.dow.map(r => r.ingresos),
        type: "bar", marker: { color: "#ff5023" },
        text: d.dow.map(r => fmtN(r.ventas) + " ventas"),
        textposition: "outside",
    }];
    Plotly.react("chart-dow", traces, L({ height: 400, yaxis: { title: "Ingresos ($)", gridcolor: "#2a2a3e" } }), plotlyConfig);
}

function renderTypeDist(d) {
    Plotly.react("chart-type-dist", [{
        values: d.type_dist.map(r => r.ingresos),
        labels: d.type_dist.map(r => r.sale_type),
        type: "pie", hole: 0.45,
        marker: { colors: COLORS },
        textinfo: "label+percent+value",
        texttemplate: "%{label}<br>%{percent}<br>$%{value:,.0f}",
        textfont: { color: "#fafafa" },
    }], L({ height: 400 }), plotlyConfig);
}

function renderCumulative(d) {
    Plotly.react("chart-cumulative", [{
        x: d.cum_rev.dates, y: d.cum_rev.values,
        type: "scatter", fill: "tozeroy", fillcolor: "rgba(46,196,182,0.15)",
        line: { color: "#2ec4b6" },
    }], L({ height: 380, hovermode: "x unified" }), plotlyConfig);
}

function renderGrowth(d) {
    const colors = d.growth.values.map(v => v >= 0 ? "#2ec4b6" : "#ee6c4d");
    Plotly.react("chart-growth", [{
        x: d.growth.dates, y: d.growth.values,
        type: "bar", marker: { color: colors },
    }], L({ height: 380, yaxis: { title: "Crecimiento %", gridcolor: "#2a2a3e" }, hovermode: "x unified" }), plotlyConfig);
}

function renderHistogram(d) {
    // Convert bin edges+counts to bar chart
    const x = d.histogram.edges.slice(0, -1).map((e, i) => (e + d.histogram.edges[i + 1]) / 2);
    const widths = d.histogram.edges.slice(0, -1).map((e, i) => d.histogram.edges[i + 1] - e);
    Plotly.react("chart-histogram", [{
        x: x, y: d.histogram.counts, type: "bar",
        marker: { color: "#ff5023" }, width: widths,
    }], L({
        height: 350, title: { text: "Histograma de Ticket", font: { color: "#fafafa", size: 14 } },
        xaxis: { title: "Monto ($)", gridcolor: "#2a2a3e" },
        yaxis: { title: "Frecuencia", gridcolor: "#2a2a3e" },
        bargap: 0.05,
    }), plotlyConfig);
}

function renderBoxplot(d) {
    const traces = d.boxplot.map((b, i) => ({
        type: "box", name: b.sale_type,
        q1: [b.q1], median: [b.median], q3: [b.q3],
        lowerfence: [b.whisker_lo], upperfence: [b.whisker_hi],
        marker: { color: COLORS[i % COLORS.length] },
    }));
    const maxY = Math.max(...d.boxplot.map(b => b.p95));
    Plotly.react("chart-boxplot", traces, L({
        height: 350, title: { text: "Ticket por Tipo de Venta", font: { color: "#fafafa", size: 14 } },
        showlegend: false,
        yaxis: { range: [0, maxY * 1.1], gridcolor: "#2a2a3e" },
    }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: PRODUCTS
// ═══════════════════════════════════════════════════════════
async function renderProducts() {
    const d = await fetchJSON("products.json");

    // Top 20 by revenue
    Plotly.react("chart-top-rev", [{
        y: d.top_revenue.map(r => r.product_name),
        x: d.top_revenue.map(r => r.revenue),
        type: "bar", orientation: "h", marker: { color: "#ff5023" },
        text: d.top_revenue.map(r => fmt$(r.revenue)), textposition: "outside",
    }], L({
        height: 550, yaxis: { autorange: "reversed", gridcolor: "#2a2a3e" },
        xaxis: { title: "Ingresos ($)", gridcolor: "#2a2a3e" },
        margin: { l: 200 },
    }), plotlyConfig);

    // Top 20 by quantity
    Plotly.react("chart-top-qty", [{
        y: d.top_qty.map(r => r.product_name),
        x: d.top_qty.map(r => r.qty),
        type: "bar", orientation: "h", marker: { color: "#2ec4b6" },
        text: d.top_qty.map(r => fmtN(r.qty)), textposition: "outside",
    }], L({
        height: 550, yaxis: { autorange: "reversed", gridcolor: "#2a2a3e" },
        xaxis: { title: "Cantidad", gridcolor: "#2a2a3e" },
        margin: { l: 200 },
    }), plotlyConfig);

    // Category pie
    Plotly.react("chart-cat-pie", [{
        values: d.category_breakdown.map(r => r.revenue),
        labels: d.category_breakdown.map(r => r.product_category),
        type: "pie", hole: 0.4,
        marker: { colors: SET2 },
        textinfo: "label+percent+value",
        texttemplate: "%{label}<br>%{percent}<br>$%{value:,.0f}",
        textfont: { color: "#fafafa" },
    }], L({ height: 400 }), plotlyConfig);

    // Category trend
    const cats = [...new Set(d.category_trend.map(r => r.categoria))];
    const catTraces = cats.map((c, i) => {
        const rows = d.category_trend.filter(r => r.categoria === c);
        return {
            x: rows.map(r => r.mes), y: rows.map(r => r.ingresos),
            name: c, stackgroup: "one",
            fillcolor: SET2[i % SET2.length] + "80",
            line: { color: SET2[i % SET2.length] },
        };
    });
    Plotly.react("chart-cat-trend", catTraces, L({ height: 400, hovermode: "x unified" }), plotlyConfig);

    // Treemap
    const labels = [], parents = [], values = [];
    const catSet = [...new Set(d.treemap.map(r => r.product_category))];
    catSet.forEach(cat => {
        labels.push(cat);
        parents.push("");
        const catTotal = d.treemap.filter(r => r.product_category === cat).reduce((s, r) => s + r.revenue, 0);
        values.push(catTotal);
    });
    d.treemap.forEach(r => {
        labels.push(r.product_name);
        parents.push(r.product_category);
        values.push(r.revenue);
    });
    Plotly.react("chart-treemap", [{
        type: "treemap", labels, parents, values,
        marker: { colorscale: "Oranges" },
        textinfo: "label+value", texttemplate: "%{label}<br>$%{value:,.0f}",
    }], L({ height: 500 }), plotlyConfig);

    // Product table
    const headers = ["Categoria", "Producto", "Cantidad", "Ingresos", "Costo", "Margen $", "Margen %", "Precio Prom."];
    const aligns = ["l","l","r","r","r","r","r","r"];
    const rows = d.product_table.map(r => [
        r.product_category, r.product_name, fmtN(r.qty),
        fmt$(r.revenue), fmt$(r.cost), fmt$(r.margin),
        fmtPct(r.margin_pct), fmt$(r.avg_price),
    ]);
    document.getElementById("product-table").innerHTML = buildTable(headers, rows, aligns);
}


// ═══════════════════════════════════════════════════════════
//  TAB: PAYMENTS
// ═══════════════════════════════════════════════════════════
async function renderPayments() {
    const d = await fetchJSON("payments.json");
    if (!d.distribution.length) {
        document.getElementById("tab-payments").innerHTML = "<p>No hay datos de pagos.</p>";
        return;
    }

    const PAY_COLORS = ["#b5e8d5","#f9d5bb","#d4a5ff","#a5d8ff","#ffd6a5","#ffadad","#caffbf","#bdb2ff"];

    // Distribution pie
    Plotly.react("chart-pay-dist", [{
        values: d.distribution.map(r => r.amount),
        labels: d.distribution.map(r => r.method),
        type: "pie", hole: 0.4,
        marker: { colors: PAY_COLORS },
        textinfo: "label+percent+value",
        texttemplate: "%{label}<br>%{percent}<br>$%{value:,.0f}",
        textfont: { color: "#333" },
    }], L({ height: 420 }), plotlyConfig);

    // Transaction count
    Plotly.react("chart-pay-count", [{
        x: d.transaction_count.map(r => r.method),
        y: d.transaction_count.map(r => r.transactions),
        type: "bar",
        marker: { color: PAY_COLORS.slice(0, d.transaction_count.length) },
    }], L({ height: 420, showlegend: false }), plotlyConfig);

    // Payment trend
    const methods = [...new Set(d.trend.map(r => r.method))];
    const trendTraces = methods.map((m, i) => {
        const rows = d.trend.filter(r => r.method === m);
        return {
            x: rows.map(r => r.year_month), y: rows.map(r => r.amount),
            name: m, stackgroup: "one",
            fillcolor: PAY_COLORS[i % PAY_COLORS.length] + "cc",
            line: { color: PAY_COLORS[i % PAY_COLORS.length] },
        };
    });
    Plotly.react("chart-pay-trend", trendTraces, L({
        height: 400, hovermode: "x unified",
        xaxis: { title: "Mes", gridcolor: "#2a2a3e" },
        yaxis: { title: "Monto ($)", gridcolor: "#2a2a3e" },
    }), plotlyConfig);

    // Payment share %
    const shareTraces = methods.map((m, i) => {
        const rows = d.share.filter(r => r.method === m);
        return {
            x: rows.map(r => r.year_month), y: rows.map(r => r.pct),
            name: m, stackgroup: "one", groupnorm: "percent",
            fillcolor: PAY_COLORS[i % PAY_COLORS.length] + "cc",
            line: { color: PAY_COLORS[i % PAY_COLORS.length] },
        };
    });
    Plotly.react("chart-pay-share", shareTraces, L({
        height: 400, hovermode: "x unified",
        yaxis: { title: "% del Total", gridcolor: "#2a2a3e" },
    }), plotlyConfig);

    // Average per method
    Plotly.react("chart-pay-avg", [{
        x: d.avg_per_method.map(r => r.method),
        y: d.avg_per_method.map(r => r.avg_amount),
        type: "bar",
        marker: { color: PAY_COLORS.slice(0, d.avg_per_method.length) },
        text: d.avg_per_method.map(r => fmt$(r.avg_amount)),
        textposition: "outside",
    }], L({
        height: 380, showlegend: false,
        yaxis: { title: "Monto Promedio ($)", gridcolor: "#2a2a3e" },
    }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: STAFF
// ═══════════════════════════════════════════════════════════
async function renderStaff() {
    const d = await fetchJSON("staff.json");

    const top15 = d.waiter_stats.slice(0, 15);

    // Revenue by waiter
    Plotly.react("chart-waiter-rev", [{
        y: top15.map(r => r.waiter),
        x: top15.map(r => r.ingresos),
        type: "bar", orientation: "h", marker: { color: "#ff5023" },
        text: top15.map(r => fmt$(r.ingresos)), textposition: "outside",
    }], L({
        height: 480, yaxis: { autorange: "reversed", gridcolor: "#2a2a3e" },
        margin: { l: 160 },
    }), plotlyConfig);

    // Avg ticket by waiter
    const byTicket = [...d.waiter_stats].sort((a, b) => b.ticket_prom - a.ticket_prom).slice(0, 15);
    Plotly.react("chart-waiter-ticket", [{
        y: byTicket.map(r => r.waiter),
        x: byTicket.map(r => r.ticket_prom),
        type: "bar", orientation: "h", marker: { color: "#2ec4b6" },
        text: byTicket.map(r => fmt$(r.ticket_prom)), textposition: "outside",
    }], L({
        height: 480, yaxis: { autorange: "reversed", gridcolor: "#2a2a3e" },
        xaxis: { title: "Ticket Promedio ($)", gridcolor: "#2a2a3e" },
        margin: { l: 160 },
    }), plotlyConfig);

    // Waiter table
    const headers = ["Mesero/a", "Ventas", "Ingresos", "Ticket Prom.", "Items Vendidos"];
    const aligns = ["l","r","r","r","r"];
    const rows = d.waiter_stats.map(r => [
        r.waiter, fmtN(r.ventas), fmt$(r.ingresos), fmt$(r.ticket_prom), fmtN(r.items),
    ]);
    document.getElementById("waiter-table").innerHTML = buildTable(headers, rows, aligns);

    // Staff activity over time
    const traces = d.top_waiters.map((w, i) => {
        const rows2 = d.waiter_time.filter(r => r.mesero === w);
        return {
            x: rows2.map(r => r.mes), y: rows2.map(r => r.ventas),
            name: w, mode: "lines+markers",
            line: { color: COLORS[i % COLORS.length] },
            marker: { color: COLORS[i % COLORS.length] },
        };
    });
    Plotly.react("chart-waiter-time", traces, L({ height: 400, hovermode: "x unified" }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: TIME PATTERNS
// ═══════════════════════════════════════════════════════════
async function renderTime() {
    const d = await fetchJSON("time_patterns.json");

    // Revenue heatmap
    Plotly.react("chart-heatmap-rev", [{
        z: d.heatmap_revenue.z,
        x: d.heatmap_revenue.hours.map(h => h + ":00"),
        y: d.heatmap_revenue.days,
        type: "heatmap", colorscale: "YlOrRd",
        hovertemplate: "Dia: %{y}<br>Hora: %{x}<br>Ingresos: $%{z:,.0f}<extra></extra>",
    }], L({ height: 380 }), plotlyConfig);

    // Hourly revenue
    Plotly.react("chart-hourly", [{
        x: d.hourly.map(r => r.hour),
        y: d.hourly.map(r => r.ingresos),
        type: "bar", marker: { color: "#ff5023" },
        text: d.hourly.map(r => fmtN(r.ventas)),
        textposition: "outside",
    }], L({
        height: 380,
        xaxis: { title: "Hora", gridcolor: "#2a2a3e" },
        yaxis: { title: "Ingresos ($)", gridcolor: "#2a2a3e" },
    }), plotlyConfig);

    // DoW sales
    Plotly.react("chart-dow2", [{
        x: d.dow.map(r => r.dia),
        y: d.dow.map(r => r.ventas),
        type: "bar", marker: { color: "#2ec4b6" },
        text: d.dow.map(r => fmt$(r.ingresos)),
        textposition: "outside",
    }], L({
        height: 380,
        yaxis: { title: "Cantidad de Ventas", gridcolor: "#2a2a3e" },
    }), plotlyConfig);

    // Sales count heatmap
    Plotly.react("chart-heatmap-sales", [{
        z: d.heatmap_sales.z,
        x: d.heatmap_sales.hours.map(h => h + ":00"),
        y: d.heatmap_sales.days,
        type: "heatmap", colorscale: "Blues",
        hovertemplate: "Dia: %{y}<br>Hora: %{x}<br>Ventas: %{z:,}<extra></extra>",
    }], L({ height: 380 }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: PROFITABILITY
// ═══════════════════════════════════════════════════════════
async function renderProfit() {
    const d = await fetchJSON("profitability.json");

    // Margin % by category
    Plotly.react("chart-cat-margin", [{
        y: d.category_margin.map(r => r.product_category),
        x: d.category_margin.map(r => r.margin_pct),
        type: "bar", orientation: "h",
        marker: { color: d.category_margin.map(r => r.margin_pct), colorscale: "RdYlGn", cmin: 0, cmax: 100 },
        text: d.category_margin.map(r => fmtPct(r.margin_pct)),
        textposition: "outside",
    }], L({ height: 380, margin: { l: 160 } }), plotlyConfig);

    // Profit $ by category
    Plotly.react("chart-cat-profit", [{
        y: d.category_profit.map(r => r.product_category),
        x: d.category_profit.map(r => r.margin_abs),
        type: "bar", orientation: "h",
        marker: { color: "#2ec4b6" },
        text: d.category_profit.map(r => fmt$(r.margin_abs)),
        textposition: "outside",
    }], L({
        height: 380, margin: { l: 160 },
        xaxis: { title: "Ganancia ($)", gridcolor: "#2a2a3e" },
    }), plotlyConfig);

    // Margin over time (dual axis)
    Plotly.react("chart-margin-time", [
        {
            x: d.margin_time.map(r => r.year_month),
            y: d.margin_time.map(r => r.margin_abs),
            type: "bar", name: "Ganancia ($)",
            marker: { color: "rgba(46,196,182,0.6)" },
        },
        {
            x: d.margin_time.map(r => r.year_month),
            y: d.margin_time.map(r => r.margin_pct),
            type: "scatter", mode: "lines+markers",
            name: "Margen %", yaxis: "y2",
            line: { color: "#ff5023" },
            marker: { color: "#ff5023" },
        },
    ], L({
        yaxis: { title: "Ganancia ($)", gridcolor: "#2a2a3e" },
        yaxis2: { title: "Margen %", overlaying: "y", side: "right", gridcolor: "#2a2a3e" },
        height: 400, hovermode: "x unified",
        legend: { orientation: "h", y: 1.12 },
    }), plotlyConfig);

    // Top margin table
    const mHeaders = ["Producto", "Ingresos", "Costo", "Ganancia", "Margen %", "Cantidad"];
    const mAligns = ["l","r","r","r","r","r"];
    document.getElementById("top-margin-table").innerHTML = buildTable(mHeaders,
        d.top_margin.map(r => [r.product_name, fmt$(r.revenue), fmt$(r.cost), fmt$(r.margin), fmtPct(r.margin_pct), fmtN(r.qty)]),
        mAligns
    );
    document.getElementById("bot-margin-table").innerHTML = buildTable(mHeaders,
        d.bottom_margin.map(r => [r.product_name, fmt$(r.revenue), fmt$(r.cost), fmt$(r.margin), fmtPct(r.margin_pct), fmtN(r.qty)]),
        mAligns
    );

    // Scatter: Revenue vs Margin %
    Plotly.react("chart-scatter", [{
        x: d.scatter.map(r => r.revenue),
        y: d.scatter.map(r => r.margin_pct),
        text: d.scatter.map(r => r.product_name),
        mode: "markers",
        marker: {
            size: d.scatter.map(r => Math.min(Math.max(r.qty / 5, 5), 40)),
            color: d.scatter.map(r => r.margin_pct),
            colorscale: "RdYlGn", cmin: 0, cmax: 100,
            colorbar: { title: "Margen %" },
        },
        hovertemplate: "%{text}<br>Ingresos: $%{x:,.0f}<br>Margen: %{y:.1f}%<extra></extra>",
    }], L({
        height: 450,
        xaxis: { title: "Ingresos ($)", gridcolor: "#2a2a3e" },
        yaxis: { title: "Margen %", gridcolor: "#2a2a3e" },
    }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: DETAIL
// ═══════════════════════════════════════════════════════════
async function renderDetail() {
    const d = await fetchJSON("detail.json");
    const s = d.summary;

    // Summary cards
    document.getElementById("detail-summary").innerHTML = `
        <div class="detail-card">
            <h3>Resumen del Periodo</h3>
            <ul>
                <li>Ventas: <strong>${fmtN(s.total_sales)}</strong></li>
                <li>Ingresos: <strong>${fmt$(s.total_revenue)}</strong></li>
                <li>Costo: <strong>${fmt$(s.total_item_cost)}</strong></li>
                <li>Ganancia bruta: <strong>${fmt$(s.gross_margin_abs)}</strong></li>
                <li>Descuentos: <strong>${fmt$(s.total_discounts)}</strong></li>
                <li>Propinas: <strong>${fmt$(s.total_tips)}</strong></li>
            </ul>
        </div>
        <div class="detail-card">
            <h3>Promedios</h3>
            <ul>
                <li>Ticket promedio: <strong>${fmt$(s.avg_ticket)}</strong></li>
                <li>Items/ticket: <strong>${fmtN(s.items_per_ticket, 1)}</strong></li>
                <li>Ingreso diario: <strong>${fmt$(s.avg_daily_revenue)}</strong></li>
                <li>Ventas/dia: <strong>${fmtN(s.avg_daily_sales, 1)}</strong></li>
                <li>Duracion prom: <strong>${Math.round(s.avg_duration)} min</strong></li>
            </ul>
        </div>
        <div class="detail-card">
            <h3>Productos</h3>
            <ul>
                <li>Productos vendidos: <strong>${fmtN(s.n_products)}</strong></li>
                <li>Categorias: <strong>${fmtN(s.n_categories)}</strong></li>
                <li>Meseros activos: <strong>${fmtN(s.n_waiters)}</strong></li>
                <li>Producto top: <strong>${s.top_product}</strong></li>
                <li>Cancelaciones: <strong>${fmtN(s.canceled_count)} (${fmtPct(s.cancel_rate)})</strong></li>
            </ul>
        </div>
    `;

    // Expenses
    const expDiv = document.getElementById("detail-expenses");
    if (d.expenses.rows.length) {
        const expHeaders = Object.keys(d.expenses.rows[0]);
        const expRows = d.expenses.rows.map(r => expHeaders.map(h => r[h] != null ? String(r[h]) : ""));
        expDiv.innerHTML = `
            <h2>Gastos</h2>
            <div class="expense-metric">
                <span class="kpi-label">Total Gastos</span><br>
                <span class="kpi-value">${fmt$(d.expenses.total)}</span>
            </div>
            <div class="table-container">${buildTable(expHeaders, expRows)}</div>
            <hr class="divider">
        `;
    }

    // Recent sales
    const sHeaders = ["ID", "Fecha", "Total", "Tipo", "Estado", "Producto", "Categoria", "Cant.", "Precio", "Mesero", "Pago"];
    const sAligns = ["r","l","r","l","l","l","l","r","r","l","l"];
    const sRows = d.recent_sales.map(r => [
        r.sale_id, r.created_at, fmt$(r.sale_total), r.sale_type, r.sale_state,
        r.product_name, r.product_category, fmtN(r.item_quantity), fmt$(r.item_price),
        r.waiter, r.payment_methods || "",
    ]);
    document.getElementById("recent-sales-table").innerHTML = buildTable(sHeaders, sRows, sAligns);
}


// ═══════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════
(async function init() {
    await renderKPIs();
    loadTab("overview");
})();
