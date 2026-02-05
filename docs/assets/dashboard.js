/* ═══════════════════════════════════════════════════════════
   Mocawa Cafe — Static Dashboard JS (Premium Edition)
   ═══════════════════════════════════════════════════════════ */

// Premium color palette - sophisticated & modern
const PALETTE = {
    primary: "#ff6b3d",      // Warm orange
    secondary: "#00d4aa",    // Teal/mint
    accent: "#7c5cff",       // Purple
    success: "#22c55e",      // Green
    warning: "#f59e0b",      // Amber
    danger: "#ef4444",       // Red
    info: "#3b82f6",         // Blue
};

// Chart color sequences
const CHART_COLORS = [
    "#ff6b3d", "#00d4aa", "#7c5cff", "#f59e0b",
    "#3b82f6", "#ec4899", "#14b8a6", "#8b5cf6",
    "#06b6d4", "#f97316", "#84cc16", "#6366f1"
];

const GRADIENT_COLORS = [
    ["#ff6b3d", "#ff8f6b"],
    ["#00d4aa", "#00f5c4"],
    ["#7c5cff", "#a78bfa"],
    ["#3b82f6", "#60a5fa"],
];

// Warm sequential for heatmaps
const HEATMAP_WARM = [
    [0, "#1a1a2e"],
    [0.2, "#2d1f3d"],
    [0.4, "#6b2c5a"],
    [0.6, "#c44536"],
    [0.8, "#ff6b3d"],
    [1, "#ffd93d"]
];

const HEATMAP_COOL = [
    [0, "#0f172a"],
    [0.2, "#1e3a5f"],
    [0.4, "#0d9488"],
    [0.6, "#00d4aa"],
    [0.8, "#5eead4"],
    [1, "#ccfbf1"]
];

// Premium layout defaults
const plotlyLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
        color: "#e2e8f0",
        size: 12,
        family: "Inter, system-ui, sans-serif"
    },
    margin: { l: 60, r: 40, t: 40, b: 60 },
    xaxis: {
        gridcolor: "rgba(148, 163, 184, 0.1)",
        zerolinecolor: "rgba(148, 163, 184, 0.2)",
        linecolor: "rgba(148, 163, 184, 0.2)",
        tickfont: { color: "#94a3b8" }
    },
    yaxis: {
        gridcolor: "rgba(148, 163, 184, 0.1)",
        zerolinecolor: "rgba(148, 163, 184, 0.2)",
        linecolor: "rgba(148, 163, 184, 0.2)",
        tickfont: { color: "#94a3b8" }
    },
    hoverlabel: {
        bgcolor: "#1e293b",
        bordercolor: "#475569",
        font: { color: "#f1f5f9", size: 13 }
    },
    legend: {
        bgcolor: "rgba(0,0,0,0)",
        font: { color: "#94a3b8" }
    }
};

const plotlyConfig = {
    responsive: true,
    displayModeBar: false,
    scrollZoom: false
};

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

function L(overrides) {
    const base = JSON.parse(JSON.stringify(plotlyLayout));
    if (overrides) {
        Object.keys(overrides).forEach(key => {
            if (key === 'xaxis' || key === 'yaxis' || key === 'yaxis2') {
                base[key] = { ...base[key === 'yaxis2' ? 'yaxis' : key], ...overrides[key] };
            } else {
                base[key] = overrides[key];
            }
        });
    }
    return base;
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
            type: "scatter", fill: "tozeroy",
            fillcolor: "rgba(255, 107, 61, 0.15)",
            line: { color: PALETTE.primary, width: 3, shape: "spline" },
            marker: { size: 6 }
        },
        {
            x: src.dates, y: src.ventas, name: "# Ventas",
            type: "bar",
            marker: {
                color: "rgba(0, 212, 170, 0.4)",
                line: { color: PALETTE.secondary, width: 1 }
            },
            yaxis: "y2",
        },
    ];
    Plotly.react("chart-revenue", traces, L({
        yaxis: { title: "Ingresos ($)" },
        yaxis2: { title: "# Ventas", overlaying: "y", side: "right" },
        hovermode: "x unified",
        height: 420,
        legend: { orientation: "h", y: 1.12, x: 0.5, xanchor: "center" },
        bargap: 0.3,
    }), plotlyConfig);
}

function renderYoY(d) {
    const traces = [];
    d.yoy.years.forEach((yr, i) => {
        const yrData = d.yoy.data.filter(r => r.year === yr);
        traces.push({
            x: yrData.map(r => r.month),
            y: yrData.map(r => r.ingresos),
            name: yr,
            mode: "lines+markers",
            line: { color: CHART_COLORS[i % CHART_COLORS.length], width: 3, shape: "spline" },
            marker: { color: CHART_COLORS[i % CHART_COLORS.length], size: 8 },
        });
    });
    const tickVals = [1,2,3,4,5,6,7,8,9,10,11,12];
    const tickText = Object.values(d.month_names);
    Plotly.react("chart-yoy", traces, L({
        xaxis: { tickmode: "array", tickvals: tickVals, ticktext: tickText },
        height: 400,
        hovermode: "x unified",
        legend: { orientation: "h", y: 1.12 },
    }), plotlyConfig);
}

function renderTypeTrend(d) {
    const types = [...new Set(d.type_trend.map(r => r.tipo))];
    const traces = types.map((t, i) => {
        const rows = d.type_trend.filter(r => r.tipo === t);
        return {
            x: rows.map(r => r.mes), y: rows.map(r => r.ventas),
            name: t, stackgroup: "one",
            fillcolor: CHART_COLORS[i % CHART_COLORS.length] + "60",
            line: { color: CHART_COLORS[i % CHART_COLORS.length], width: 0 },
        };
    });
    Plotly.react("chart-type-trend", traces, L({
        height: 400,
        hovermode: "x unified",
        legend: { orientation: "h", y: 1.12 },
    }), plotlyConfig);
}

function renderDoW(d) {
    const colors = d.dow.map((_, i) => {
        const intensity = 0.5 + (i / d.dow.length) * 0.5;
        return `rgba(255, 107, 61, ${intensity})`;
    });
    const traces = [{
        x: d.dow.map(r => r.dia),
        y: d.dow.map(r => r.ingresos),
        type: "bar",
        marker: {
            color: colors,
            line: { color: PALETTE.primary, width: 2 }
        },
        text: d.dow.map(r => fmtN(r.ventas) + " ventas"),
        textposition: "outside",
        textfont: { color: "#94a3b8", size: 11 }
    }];
    Plotly.react("chart-dow", traces, L({
        height: 400,
        yaxis: { title: "Ingresos ($)" },
        bargap: 0.3,
    }), plotlyConfig);
}

function renderTypeDist(d) {
    Plotly.react("chart-type-dist", [{
        values: d.type_dist.map(r => r.ingresos),
        labels: d.type_dist.map(r => r.sale_type),
        type: "pie",
        hole: 0.55,
        marker: {
            colors: CHART_COLORS,
            line: { color: "#0f172a", width: 2 }
        },
        textinfo: "label+percent",
        textposition: "outside",
        textfont: { color: "#e2e8f0", size: 12 },
        hovertemplate: "<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
        pull: [0.02, 0, 0, 0],
    }], L({
        height: 400,
        showlegend: false,
        annotations: [{
            text: '<b>Por Tipo</b>',
            x: 0.5, y: 0.5,
            font: { size: 14, color: '#94a3b8' },
            showarrow: false
        }]
    }), plotlyConfig);
}

function renderCumulative(d) {
    Plotly.react("chart-cumulative", [{
        x: d.cum_rev.dates, y: d.cum_rev.values,
        type: "scatter",
        fill: "tozeroy",
        fillcolor: "rgba(0, 212, 170, 0.1)",
        line: { color: PALETTE.secondary, width: 3, shape: "spline" },
    }], L({
        height: 380,
        hovermode: "x unified",
        yaxis: { title: "Ingresos Acumulados ($)" }
    }), plotlyConfig);
}

function renderGrowth(d) {
    const colors = d.growth.values.map(v => v >= 0 ? PALETTE.success : PALETTE.danger);
    Plotly.react("chart-growth", [{
        x: d.growth.dates, y: d.growth.values,
        type: "bar",
        marker: {
            color: colors,
            line: { color: colors, width: 1 }
        },
    }], L({
        height: 380,
        yaxis: { title: "Crecimiento %", zeroline: true, zerolinecolor: "#475569", zerolinewidth: 2 },
        hovermode: "x unified",
        bargap: 0.4,
    }), plotlyConfig);
}

function renderHistogram(d) {
    const x = d.histogram.edges.slice(0, -1).map((e, i) => (e + d.histogram.edges[i + 1]) / 2);
    const widths = d.histogram.edges.slice(0, -1).map((e, i) => d.histogram.edges[i + 1] - e);
    const maxCount = Math.max(...d.histogram.counts);
    const colors = d.histogram.counts.map(c => {
        const ratio = c / maxCount;
        return `rgba(255, 107, 61, ${0.3 + ratio * 0.7})`;
    });

    Plotly.react("chart-histogram", [{
        x: x, y: d.histogram.counts, type: "bar",
        marker: {
            color: colors,
            line: { color: PALETTE.primary, width: 1 }
        },
        width: widths,
    }], L({
        height: 350,
        title: { text: "Distribucion del Ticket", font: { color: "#e2e8f0", size: 14 } },
        xaxis: { title: "Monto ($)" },
        yaxis: { title: "Frecuencia" },
        bargap: 0.05,
    }), plotlyConfig);
}

function renderBoxplot(d) {
    const traces = d.boxplot.map((b, i) => ({
        type: "box", name: b.sale_type,
        q1: [b.q1], median: [b.median], q3: [b.q3],
        lowerfence: [b.whisker_lo], upperfence: [b.whisker_hi],
        marker: { color: CHART_COLORS[i % CHART_COLORS.length] },
        line: { color: CHART_COLORS[i % CHART_COLORS.length] },
        fillcolor: CHART_COLORS[i % CHART_COLORS.length] + "40",
    }));
    const maxY = Math.max(...d.boxplot.map(b => b.p95));
    Plotly.react("chart-boxplot", traces, L({
        height: 350,
        title: { text: "Ticket por Tipo de Venta", font: { color: "#e2e8f0", size: 14 } },
        showlegend: false,
        yaxis: { range: [0, maxY * 1.1] },
    }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: PRODUCTS
// ═══════════════════════════════════════════════════════════
async function renderProducts() {
    const d = await fetchJSON("products.json");

    // Top 20 by revenue - gradient bars
    const revColors = d.top_revenue.map((_, i) => {
        const ratio = 1 - (i / d.top_revenue.length);
        return `rgba(255, 107, 61, ${0.4 + ratio * 0.6})`;
    });

    Plotly.react("chart-top-rev", [{
        y: d.top_revenue.map(r => r.product_name),
        x: d.top_revenue.map(r => r.revenue),
        type: "bar", orientation: "h",
        marker: {
            color: revColors,
            line: { color: PALETTE.primary, width: 1 }
        },
        text: d.top_revenue.map(r => fmt$(r.revenue)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 550,
        yaxis: { autorange: "reversed" },
        xaxis: { title: "Ingresos ($)" },
        margin: { l: 200 },
    }), plotlyConfig);

    // Top 20 by quantity
    const qtyColors = d.top_qty.map((_, i) => {
        const ratio = 1 - (i / d.top_qty.length);
        return `rgba(0, 212, 170, ${0.4 + ratio * 0.6})`;
    });

    Plotly.react("chart-top-qty", [{
        y: d.top_qty.map(r => r.product_name),
        x: d.top_qty.map(r => r.qty),
        type: "bar", orientation: "h",
        marker: {
            color: qtyColors,
            line: { color: PALETTE.secondary, width: 1 }
        },
        text: d.top_qty.map(r => fmtN(r.qty)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 550,
        yaxis: { autorange: "reversed" },
        xaxis: { title: "Cantidad" },
        margin: { l: 200 },
    }), plotlyConfig);

    // Category pie - premium donut
    Plotly.react("chart-cat-pie", [{
        values: d.category_breakdown.map(r => r.revenue),
        labels: d.category_breakdown.map(r => r.product_category),
        type: "pie",
        hole: 0.55,
        marker: {
            colors: CHART_COLORS,
            line: { color: "#0f172a", width: 3 }
        },
        textinfo: "label+percent",
        textposition: "outside",
        textfont: { color: "#e2e8f0", size: 12 },
        hovertemplate: "<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
    }], L({
        height: 400,
        showlegend: false,
        annotations: [{
            text: '<b>Categorias</b>',
            x: 0.5, y: 0.5,
            font: { size: 14, color: '#94a3b8' },
            showarrow: false
        }]
    }), plotlyConfig);

    // Category trend
    const cats = [...new Set(d.category_trend.map(r => r.categoria))];
    const catTraces = cats.map((c, i) => {
        const rows = d.category_trend.filter(r => r.categoria === c);
        return {
            x: rows.map(r => r.mes), y: rows.map(r => r.ingresos),
            name: c, stackgroup: "one",
            fillcolor: CHART_COLORS[i % CHART_COLORS.length] + "70",
            line: { color: CHART_COLORS[i % CHART_COLORS.length], width: 0 },
        };
    });
    Plotly.react("chart-cat-trend", catTraces, L({
        height: 400,
        hovermode: "x unified",
        legend: { orientation: "h", y: 1.15 },
    }), plotlyConfig);

    // Treemap
    const labels = [], parents = [], values = [], colors = [];
    const catSet = [...new Set(d.treemap.map(r => r.product_category))];
    catSet.forEach((cat, i) => {
        labels.push(cat);
        parents.push("");
        const catTotal = d.treemap.filter(r => r.product_category === cat).reduce((s, r) => s + r.revenue, 0);
        values.push(catTotal);
        colors.push(CHART_COLORS[i % CHART_COLORS.length]);
    });
    d.treemap.forEach(r => {
        labels.push(r.product_name);
        parents.push(r.product_category);
        values.push(r.revenue);
        const catIdx = catSet.indexOf(r.product_category);
        colors.push(CHART_COLORS[catIdx % CHART_COLORS.length] + "90");
    });

    Plotly.react("chart-treemap", [{
        type: "treemap", labels, parents, values,
        marker: {
            colors: colors,
            line: { color: "#0f172a", width: 2 }
        },
        textinfo: "label+value",
        texttemplate: "<b>%{label}</b><br>$%{value:,.0f}",
        textfont: { color: "#fff" },
        hovertemplate: "<b>%{label}</b><br>$%{value:,.0f}<extra></extra>",
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

    // Premium payment colors
    const PAY_COLORS = ["#00d4aa", "#7c5cff", "#f59e0b", "#3b82f6", "#ec4899", "#14b8a6", "#8b5cf6", "#06b6d4"];

    // Distribution pie
    Plotly.react("chart-pay-dist", [{
        values: d.distribution.map(r => r.amount),
        labels: d.distribution.map(r => r.method),
        type: "pie",
        hole: 0.55,
        marker: {
            colors: PAY_COLORS,
            line: { color: "#0f172a", width: 3 }
        },
        textinfo: "label+percent",
        textposition: "outside",
        textfont: { color: "#e2e8f0", size: 12 },
        hovertemplate: "<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
    }], L({
        height: 420,
        showlegend: false,
        annotations: [{
            text: '<b>Metodos</b>',
            x: 0.5, y: 0.5,
            font: { size: 14, color: '#94a3b8' },
            showarrow: false
        }]
    }), plotlyConfig);

    // Transaction count
    Plotly.react("chart-pay-count", [{
        x: d.transaction_count.map(r => r.method),
        y: d.transaction_count.map(r => r.transactions),
        type: "bar",
        marker: {
            color: PAY_COLORS.slice(0, d.transaction_count.length),
            line: { color: PAY_COLORS.slice(0, d.transaction_count.length), width: 2 }
        },
        text: d.transaction_count.map(r => fmtN(r.transactions)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 420,
        showlegend: false,
        bargap: 0.4,
    }), plotlyConfig);

    // Payment trend
    const methods = [...new Set(d.trend.map(r => r.method))];
    const trendTraces = methods.map((m, i) => {
        const rows = d.trend.filter(r => r.method === m);
        return {
            x: rows.map(r => r.year_month), y: rows.map(r => r.amount),
            name: m, stackgroup: "one",
            fillcolor: PAY_COLORS[i % PAY_COLORS.length] + "80",
            line: { color: PAY_COLORS[i % PAY_COLORS.length], width: 0 },
        };
    });
    Plotly.react("chart-pay-trend", trendTraces, L({
        height: 400,
        hovermode: "x unified",
        xaxis: { title: "Mes" },
        yaxis: { title: "Monto ($)" },
        legend: { orientation: "h", y: 1.15 },
    }), plotlyConfig);

    // Payment share %
    const shareTraces = methods.map((m, i) => {
        const rows = d.share.filter(r => r.method === m);
        return {
            x: rows.map(r => r.year_month), y: rows.map(r => r.pct),
            name: m, stackgroup: "one", groupnorm: "percent",
            fillcolor: PAY_COLORS[i % PAY_COLORS.length] + "90",
            line: { color: PAY_COLORS[i % PAY_COLORS.length], width: 0 },
        };
    });
    Plotly.react("chart-pay-share", shareTraces, L({
        height: 400,
        hovermode: "x unified",
        yaxis: { title: "% del Total" },
        legend: { orientation: "h", y: 1.15 },
    }), plotlyConfig);

    // Average per method
    Plotly.react("chart-pay-avg", [{
        x: d.avg_per_method.map(r => r.method),
        y: d.avg_per_method.map(r => r.avg_amount),
        type: "bar",
        marker: {
            color: PAY_COLORS.slice(0, d.avg_per_method.length),
            line: { color: "#0f172a", width: 2 }
        },
        text: d.avg_per_method.map(r => fmt$(r.avg_amount)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 380,
        showlegend: false,
        yaxis: { title: "Monto Promedio ($)" },
        bargap: 0.4,
    }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: STAFF
// ═══════════════════════════════════════════════════════════
async function renderStaff() {
    const d = await fetchJSON("staff.json");

    const top15 = d.waiter_stats.slice(0, 15);

    // Revenue by waiter - gradient
    const revColors = top15.map((_, i) => {
        const ratio = 1 - (i / top15.length);
        return `rgba(255, 107, 61, ${0.4 + ratio * 0.6})`;
    });

    Plotly.react("chart-waiter-rev", [{
        y: top15.map(r => r.waiter),
        x: top15.map(r => r.ingresos),
        type: "bar", orientation: "h",
        marker: {
            color: revColors,
            line: { color: PALETTE.primary, width: 1 }
        },
        text: top15.map(r => fmt$(r.ingresos)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 480,
        yaxis: { autorange: "reversed" },
        margin: { l: 160 },
    }), plotlyConfig);

    // Avg ticket by waiter
    const byTicket = [...d.waiter_stats].sort((a, b) => b.ticket_prom - a.ticket_prom).slice(0, 15);
    const ticketColors = byTicket.map((_, i) => {
        const ratio = 1 - (i / byTicket.length);
        return `rgba(0, 212, 170, ${0.4 + ratio * 0.6})`;
    });

    Plotly.react("chart-waiter-ticket", [{
        y: byTicket.map(r => r.waiter),
        x: byTicket.map(r => r.ticket_prom),
        type: "bar", orientation: "h",
        marker: {
            color: ticketColors,
            line: { color: PALETTE.secondary, width: 1 }
        },
        text: byTicket.map(r => fmt$(r.ticket_prom)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 480,
        yaxis: { autorange: "reversed" },
        xaxis: { title: "Ticket Promedio ($)" },
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
            name: w,
            mode: "lines+markers",
            line: { color: CHART_COLORS[i % CHART_COLORS.length], width: 3, shape: "spline" },
            marker: { color: CHART_COLORS[i % CHART_COLORS.length], size: 6 },
        };
    });
    Plotly.react("chart-waiter-time", traces, L({
        height: 400,
        hovermode: "x unified",
        legend: { orientation: "h", y: 1.15 },
    }), plotlyConfig);

    // Monthly waiter performance with duration
    if (d.waiter_monthly && d.all_months) {
        const select = document.getElementById("month-select");
        d.all_months.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m;
            select.appendChild(opt);
        });
        select.value = d.all_months[d.all_months.length - 2] || d.all_months[d.all_months.length - 1];
        renderWaiterMonthly(d, select.value);
        select.addEventListener("change", () => renderWaiterMonthly(d, select.value));
    }
}

function renderWaiterMonthly(d, month) {
    const rows = d.waiter_monthly.filter(r => r.year_month === month)
        .sort((a, b) => b.ingresos - a.ingresos);

    if (!rows.length) {
        document.getElementById("waiter-monthly-table").innerHTML =
            '<p style="color:#94a3b8;padding:16px;">Sin datos para este mes.</p>';
        Plotly.purge("chart-waiter-monthly-rev");
        Plotly.purge("chart-waiter-monthly-dur");
        return;
    }

    // Revenue + sales bar chart
    Plotly.react("chart-waiter-monthly-rev", [
        {
            y: rows.map(r => r.waiter),
            x: rows.map(r => r.ingresos),
            type: "bar", orientation: "h", name: "Ingresos",
            marker: { color: PALETTE.primary + "cc" },
            text: rows.map(r => fmt$(r.ingresos)),
            textposition: "outside",
            textfont: { color: "#94a3b8" },
        },
        {
            y: rows.map(r => r.waiter),
            x: rows.map(r => r.ventas),
            type: "bar", orientation: "h", name: "# Ventas",
            marker: { color: PALETTE.secondary + "80" },
            xaxis: "x2",
            text: rows.map(r => fmtN(r.ventas)),
            textposition: "outside",
            textfont: { color: "#94a3b8" },
        },
    ], L({
        height: Math.max(250, rows.length * 50 + 80),
        yaxis: { autorange: "reversed" },
        xaxis: { title: "Ingresos ($)", side: "bottom" },
        xaxis2: { title: "# Ventas", overlaying: "x", side: "top" },
        margin: { l: 140, t: 40 },
        legend: { orientation: "h", y: 1.15 },
        barmode: "group",
    }), plotlyConfig);

    // Duration bar chart
    const maxDur = Math.max(...rows.map(r => r.duracion_prom || 0));
    const durColors = rows.map(r => {
        if (r.duracion_prom == null) return "#475569";
        if (r.duracion_prom <= 2) return PALETTE.success;
        if (r.duracion_prom <= 5) return PALETTE.secondary;
        if (r.duracion_prom <= 10) return PALETTE.warning;
        return PALETTE.danger;
    });
    Plotly.react("chart-waiter-monthly-dur", [{
        y: rows.map(r => r.waiter),
        x: rows.map(r => r.duracion_prom),
        type: "bar", orientation: "h",
        marker: {
            color: durColors,
            line: { color: durColors, width: 1 }
        },
        text: rows.map(r => r.duracion_prom != null ? r.duracion_prom.toFixed(1) + " min" : "—"),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: Math.max(250, rows.length * 50 + 80),
        yaxis: { autorange: "reversed" },
        xaxis: { title: "Minutos promedio", range: [0, maxDur * 1.3] },
        margin: { l: 140 },
    }), plotlyConfig);

    // Monthly table
    const headers = ["Mesero/a", "Ventas", "Ingresos", "Ticket Prom.", "Duracion Prom."];
    const aligns = ["l", "r", "r", "r", "r"];
    const tableRows = rows.map(r => [
        r.waiter,
        fmtN(r.ventas),
        fmt$(r.ingresos),
        fmt$(r.ticket_prom),
        r.duracion_prom != null ? r.duracion_prom.toFixed(1) + " min" : "—",
    ]);
    document.getElementById("waiter-monthly-table").innerHTML = buildTable(headers, tableRows, aligns);
}


// ═══════════════════════════════════════════════════════════
//  TAB: TIME PATTERNS
// ═══════════════════════════════════════════════════════════
async function renderTime() {
    const d = await fetchJSON("time_patterns.json");

    // Revenue heatmap - premium warm colors
    Plotly.react("chart-heatmap-rev", [{
        z: d.heatmap_revenue.z,
        x: d.heatmap_revenue.hours.map(h => h + ":00"),
        y: d.heatmap_revenue.days,
        type: "heatmap",
        colorscale: HEATMAP_WARM,
        hovertemplate: "<b>%{y}</b><br>Hora: %{x}<br>Ingresos: $%{z:,.0f}<extra></extra>",
        colorbar: {
            title: { text: "Ingresos", font: { color: "#94a3b8" } },
            tickfont: { color: "#94a3b8" },
            outlinecolor: "#475569"
        }
    }], L({
        height: 380,
        xaxis: { title: "Hora", side: "bottom" },
    }), plotlyConfig);

    // Hourly revenue - gradient bars
    const maxRev = Math.max(...d.hourly.map(r => r.ingresos));
    const hourlyColors = d.hourly.map(r => {
        const ratio = r.ingresos / maxRev;
        return `rgba(255, 107, 61, ${0.3 + ratio * 0.7})`;
    });

    Plotly.react("chart-hourly", [{
        x: d.hourly.map(r => r.hour),
        y: d.hourly.map(r => r.ingresos),
        type: "bar",
        marker: {
            color: hourlyColors,
            line: { color: PALETTE.primary, width: 1 }
        },
        text: d.hourly.map(r => fmtN(r.ventas)),
        textposition: "outside",
        textfont: { color: "#94a3b8", size: 10 },
    }], L({
        height: 380,
        xaxis: { title: "Hora", dtick: 1 },
        yaxis: { title: "Ingresos ($)" },
        bargap: 0.2,
    }), plotlyConfig);

    // DoW sales
    const dowColors = d.dow.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);
    Plotly.react("chart-dow2", [{
        x: d.dow.map(r => r.dia),
        y: d.dow.map(r => r.ventas),
        type: "bar",
        marker: {
            color: dowColors,
            line: { color: "#0f172a", width: 2 }
        },
        text: d.dow.map(r => fmt$(r.ingresos)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 380,
        yaxis: { title: "Cantidad de Ventas" },
        bargap: 0.35,
    }), plotlyConfig);

    // Sales count heatmap - cool colors
    Plotly.react("chart-heatmap-sales", [{
        z: d.heatmap_sales.z,
        x: d.heatmap_sales.hours.map(h => h + ":00"),
        y: d.heatmap_sales.days,
        type: "heatmap",
        colorscale: HEATMAP_COOL,
        hovertemplate: "<b>%{y}</b><br>Hora: %{x}<br>Ventas: %{z:,}<extra></extra>",
        colorbar: {
            title: { text: "Ventas", font: { color: "#94a3b8" } },
            tickfont: { color: "#94a3b8" },
            outlinecolor: "#475569"
        }
    }], L({
        height: 380,
        xaxis: { title: "Hora" },
    }), plotlyConfig);
}


// ═══════════════════════════════════════════════════════════
//  TAB: PROFITABILITY
// ═══════════════════════════════════════════════════════════
async function renderProfit() {
    const d = await fetchJSON("profitability.json");

    // Custom RdYlGn for margins
    const marginColorscale = [
        [0, "#ef4444"],
        [0.3, "#f59e0b"],
        [0.5, "#fbbf24"],
        [0.7, "#84cc16"],
        [1, "#22c55e"]
    ];

    // Margin % by category
    Plotly.react("chart-cat-margin", [{
        y: d.category_margin.map(r => r.product_category),
        x: d.category_margin.map(r => r.margin_pct),
        type: "bar", orientation: "h",
        marker: {
            color: d.category_margin.map(r => r.margin_pct),
            colorscale: marginColorscale,
            cmin: 0, cmax: 100,
            line: { color: "#0f172a", width: 2 }
        },
        text: d.category_margin.map(r => fmtPct(r.margin_pct)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 380,
        margin: { l: 160 },
        xaxis: { title: "Margen %" }
    }), plotlyConfig);

    // Profit $ by category
    const profitColors = d.category_profit.map((_, i) => {
        const ratio = 1 - (i / d.category_profit.length);
        return `rgba(0, 212, 170, ${0.4 + ratio * 0.6})`;
    });

    Plotly.react("chart-cat-profit", [{
        y: d.category_profit.map(r => r.product_category),
        x: d.category_profit.map(r => r.margin_abs),
        type: "bar", orientation: "h",
        marker: {
            color: profitColors,
            line: { color: PALETTE.secondary, width: 1 }
        },
        text: d.category_profit.map(r => fmt$(r.margin_abs)),
        textposition: "outside",
        textfont: { color: "#94a3b8" },
    }], L({
        height: 380,
        margin: { l: 160 },
        xaxis: { title: "Ganancia ($)" },
    }), plotlyConfig);

    // Margin over time (dual axis)
    Plotly.react("chart-margin-time", [
        {
            x: d.margin_time.map(r => r.year_month),
            y: d.margin_time.map(r => r.margin_abs),
            type: "bar", name: "Ganancia ($)",
            marker: {
                color: PALETTE.secondary + "70",
                line: { color: PALETTE.secondary, width: 1 }
            },
        },
        {
            x: d.margin_time.map(r => r.year_month),
            y: d.margin_time.map(r => r.margin_pct),
            type: "scatter",
            mode: "lines+markers",
            name: "Margen %",
            yaxis: "y2",
            line: { color: PALETTE.primary, width: 3, shape: "spline" },
            marker: { color: PALETTE.primary, size: 8 },
        },
    ], L({
        yaxis: { title: "Ganancia ($)" },
        yaxis2: { title: "Margen %", overlaying: "y", side: "right" },
        height: 400,
        hovermode: "x unified",
        legend: { orientation: "h", y: 1.12 },
        bargap: 0.3,
    }), plotlyConfig);

    // Top/bottom margin tables
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

    // Scatter: Revenue vs Margin % - premium bubbles
    Plotly.react("chart-scatter", [{
        x: d.scatter.map(r => r.revenue),
        y: d.scatter.map(r => r.margin_pct),
        text: d.scatter.map(r => r.product_name),
        mode: "markers",
        marker: {
            size: d.scatter.map(r => Math.min(Math.max(r.qty / 4, 8), 50)),
            color: d.scatter.map(r => r.margin_pct),
            colorscale: marginColorscale,
            cmin: 0, cmax: 100,
            colorbar: {
                title: { text: "Margen %", font: { color: "#94a3b8" } },
                tickfont: { color: "#94a3b8" },
                outlinecolor: "#475569"
            },
            line: { color: "#0f172a", width: 1 },
            opacity: 0.85,
        },
        hovertemplate: "<b>%{text}</b><br>Ingresos: $%{x:,.0f}<br>Margen: %{y:.1f}%<extra></extra>",
    }], L({
        height: 450,
        xaxis: { title: "Ingresos ($)" },
        yaxis: { title: "Margen %" },
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
