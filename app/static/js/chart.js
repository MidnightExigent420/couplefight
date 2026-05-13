// Dashboard spend chart — Google-Finance-style viewer.
// One fetch per page load (always 1 year of data); the viewport, zoom and pan are all client-side.
(function () {
  const canvas = document.getElementById("spend-chart");
  if (!canvas) return;

  const rangeToggle = document.getElementById("chart-range-toggle");
  const zoomInBtn   = document.getElementById("zoom-in");
  const zoomOutBtn  = document.getElementById("zoom-out");

  let chart = null;
  let lastData = null;

  const PALETTE = [
    "#0ea5e9", "#16a34a", "#e11d48", "#a855f7", "#f59e0b",
    "#0891b2", "#65a30d", "#db2777", "#7c3aed", "#d97706",
  ];

  // Half-width in days for each preset. Total visible window = 2 * value + 1.
  const RANGE_HALF_DAYS = { "1w": 3, "1m": 15, "1y": 182 };
  const DAY_MS = 86_400_000;
  const FUTURE_PAN_BUFFER_DAYS = 365;

  // ---- Crosshair plugin (inline; no extra CDN). Draws dashed guides from the
  // cursor to both axes, mirroring Google Finance's hover behavior.
  const crosshairPlugin = {
    id: "crosshair",
    afterEvent(chart, args) {
      const e = args.event;
      if (e.type === "mousemove" && args.inChartArea) {
        chart._cursor = { x: e.x, y: e.y };
      } else if (e.type === "mouseout" || !args.inChartArea) {
        chart._cursor = null;
      }
    },
    afterDatasetsDraw(chart) {
      const c = chart._cursor;
      if (!c) return;
      const { ctx, chartArea } = chart;
      ctx.save();
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(100,116,139,0.55)"; // slate-500
      ctx.beginPath();
      ctx.moveTo(c.x, chartArea.top);
      ctx.lineTo(c.x, chartArea.bottom);
      ctx.moveTo(chartArea.left, c.y);
      ctx.lineTo(chartArea.right, c.y);
      ctx.stroke();
      ctx.restore();
    },
  };
  // Register once — registering twice is a no-op in Chart.js but we guard anyway.
  if (window.Chart && !Chart.registry.plugins.get("crosshair")) {
    Chart.register(crosshairPlugin);
  }

  function visibleIds() {
    const goalIds = new Set();
    const twIds = new Set();
    document.querySelectorAll("#ap-list .ap-item").forEach((li) => {
      if (li.style.display === "none") return;
      const id = li.dataset.id;
      if (!id) return;
      if (li.dataset.kind === "goal") goalIds.add(id);
      else if (li.dataset.kind === "tripwire") twIds.add(id);
    });
    return { goalIds, twIds };
  }

  // Map a parallel (labels, values) pair into Chart.js {x, y} time-series points.
  function toXY(labels, vals) {
    return labels.map((d, i) => ({ x: d, y: vals[i] }));
  }

  // Currency formatter used by the tooltip; closes over the latest fetched currency.
  function fmtCurrency(value) {
    const cur = (lastData && lastData.currency) || "USD";
    try {
      return value.toLocaleString(undefined, { style: "currency", currency: cur });
    } catch {
      return `${cur} ${value.toFixed(2)}`;
    }
  }

  // Earliest date with non-zero cumulative spend, used as the left pan boundary
  // so users cannot drag into pre-spending dead zones.
  function panMinISO() {
    if (!lastData) return null;
    const { labels, overall } = lastData;
    const firstSpendIdx = overall.findIndex((v) => v > 0);
    return labels[firstSpendIdx >= 0 ? firstSpendIdx : 0];
  }

  function panMaxISO() {
    const future = new Date(Date.now() + FUTURE_PAN_BUFFER_DAYS * DAY_MS);
    return future.toISOString().slice(0, 10);
  }

  function todayISO() {
    return new Date().toISOString().slice(0, 10);
  }

  function render() {
    if (!lastData) return;
    const { labels, overall, items, currency } = lastData;
    const { goalIds, twIds } = visibleIds();

    const datasets = [{
      label: `Overall (${currency})`,
      data: toXY(labels, overall),
      borderColor: "#334155",
      backgroundColor: "rgba(51,65,85,0.10)",
      fill: true,
      borderWidth: 2,
      tension: 0.2,
      pointRadius: 0,
      spanGaps: false,
    }];

    let colorIdx = 0;
    items.forEach((it) => {
      const idStr = String(it.id);
      const isVisible = (it.kind === "goal" && goalIds.has(idStr))
        || (it.kind === "tripwire" && twIds.has(idStr));
      if (!isVisible) return;
      const color = PALETTE[colorIdx % PALETTE.length];
      colorIdx += 1;
      const labelPrefix = it.kind === "goal"
        ? (it.goal_type === "target" ? "Goal (target)" : "Goal (cap)")
        : "Tripwire";
      datasets.push({
        label: `${labelPrefix}: ${it.label}`,
        data: toXY(labels, it.cumulative),
        borderColor: color,
        backgroundColor: "transparent",
        borderWidth: 2,
        tension: 0.2,
        pointRadius: 0,
        spanGaps: false,
      });
      // Threshold line: two-point segment spanning the item's own start/end
      // (not the chart range), so the dashed line stops at the goal/tripwire's
      // actual end_date rather than running off into the future.
      datasets.push({
        label: `${it.label} threshold`,
        data: [
          { x: it.start, y: it.threshold },
          { x: it.end,   y: it.threshold },
        ],
        borderColor: color,
        borderDash: [4, 4],
        borderWidth: 1,
        pointRadius: 0,
        fill: false,
      });
    });

    // "Today" dot — find by date string so any backend change to range boundaries doesn't silently misplace it.
    const today = todayISO();
    const overallSeries = toXY(labels, overall);
    const todayPoint = overallSeries.find((p) => p.x === today);
    datasets.push({
      label: "Today",
      data: todayPoint ? [todayPoint] : [],
      borderColor: "#dc2626",      // red-600
      backgroundColor: "#dc2626",
      pointRadius: 6,
      pointHoverRadius: 8,
      showLine: false,
      order: -1, // draw above the area fill
    });

    if (chart) {
      chart.data.datasets = datasets;
      // Refresh pan limits since panMinISO depends on the freshly rebuilt data.
      const zoomOpts = chart.options.plugins.zoom;
      if (zoomOpts && zoomOpts.limits && zoomOpts.limits.x) {
        zoomOpts.limits.x.min = panMinISO();
        zoomOpts.limits.x.max = panMaxISO();
      }
      chart.update();
    } else {
      chart = new Chart(canvas, {
        type: "line",
        data: { datasets },
        options: {
          responsive: true,
          animation: { duration: 400 },
          interaction: { mode: "index", intersect: false },
          scales: {
            x: {
              type: "time",
              time: { unit: "day", tooltipFormat: "PP" },
              grid: { color: "rgba(226,232,240,0.6)" },
              title: { display: false },
            },
            y: {
              beginAtZero: true,
              grid: { color: "rgba(226,232,240,0.6)" },
              title: { display: true, text: `Amount (${currency})` },
            },
          },
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 10 } },
            tooltip: {
              mode: "index",
              intersect: false,
              backgroundColor: "rgba(15,23,42,0.92)", // slate-900/90
              titleFont: { size: 11, weight: "600" },
              bodyFont:  { size: 12 },
              padding: 8,
              displayColors: false,
              callbacks: {
                title: (items) => new Date(items[0].parsed.x).toLocaleDateString(undefined, {
                  month: "short", day: "numeric", year: "numeric",
                }),
                label: (item) => `${item.dataset.label}: ${fmtCurrency(item.parsed.y)}`,
              },
            },
            zoom: {
              pan: { enabled: true, mode: "x" },
              zoom: {
                wheel: { enabled: true },   // plain scroll-wheel zoom, Google-Maps style
                pinch: { enabled: true },
                mode:  "x",
              },
              limits: {
                x: { min: panMinISO(), max: panMaxISO(), minRange: 2 * DAY_MS },
              },
            },
          },
        },
      });
    }
  }

  // Set the visible x-axis window to today ± half_days. Clears wheel-zoom state
  // first so the explicit min/max isn't fighting plugin-internal zoom level.
  function setViewport(rangeKey) {
    if (!chart) return;
    const half = RANGE_HALF_DAYS[rangeKey];
    if (half == null) return;
    chart.resetZoom();
    const now = Date.now();
    chart.options.scales.x.min = new Date(now - half * DAY_MS).toISOString();
    chart.options.scales.x.max = new Date(now + half * DAY_MS).toISOString();
    chart.update();
  }

  function updatePillStyling(activeKey) {
    if (!rangeToggle) return;
    rangeToggle.querySelectorAll(".range-pill").forEach((btn) => {
      const active = btn.dataset.range === activeKey;
      btn.classList.toggle("bg-slate-800", active);
      btn.classList.toggle("text-white", active);
      btn.classList.toggle("text-slate-600", !active);
      btn.classList.toggle("hover:bg-slate-100", !active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  async function load() {
    const url = new URL("/api/spend-series", window.location.origin);
    url.searchParams.set("range", "1y"); // always fetch max; viewport is client-side
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) return;
    lastData = await r.json();
    render();
    // Enforce Monthly as the default viewport regardless of cached state.
    setViewport("1m");
    updatePillStyling("1m");
  }

  if (rangeToggle) {
    rangeToggle.addEventListener("click", (e) => {
      const btn = e.target.closest(".range-pill");
      if (!btn) return;
      const key = btn.dataset.range;
      setViewport(key);
      updatePillStyling(key);
    });
  }
  if (zoomInBtn)  zoomInBtn.addEventListener("click",  () => chart && chart.zoom(1.25));
  if (zoomOutBtn) zoomOutBtn.addEventListener("click", () => chart && chart.zoom(0.8));

  document.addEventListener("activity-panel:changed", render);

  load();
})();
