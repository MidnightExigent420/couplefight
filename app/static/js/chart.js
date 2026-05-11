(function () {
  const canvas = document.getElementById("spend-chart");
  if (!canvas) return;
  const rangeSel = document.getElementById("chart-range");

  let chart = null;
  let lastData = null;

  const PALETTE = [
    "#0ea5e9", "#16a34a", "#e11d48", "#a855f7", "#f59e0b",
    "#0891b2", "#65a30d", "#db2777", "#7c3aed", "#d97706",
  ];

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

  function render() {
    if (!lastData) return;
    const { labels, overall, items, currency } = lastData;
    const { goalIds, twIds } = visibleIds();

    const datasets = [{
      label: `Overall (${currency})`,
      data: overall,
      borderColor: "#334155",
      backgroundColor: "rgba(51,65,85,0.10)",
      fill: true,
      borderWidth: 2,
      tension: 0.2,
      pointRadius: 0,
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
        data: it.cumulative,
        borderColor: color,
        backgroundColor: "transparent",
        borderWidth: 2,
        tension: 0.2,
        pointRadius: 0,
        spanGaps: false,
      });
      datasets.push({
        label: `${it.label} threshold`,
        data: labels.map(() => it.threshold),
        borderColor: color,
        borderDash: [4, 4],
        borderWidth: 1,
        pointRadius: 0,
        fill: false,
      });
    });

    if (chart) {
      chart.data.labels = labels;
      chart.data.datasets = datasets;
      chart.update();
    } else {
      chart = new Chart(canvas, {
        type: "line",
        data: { labels, datasets },
        options: {
          responsive: true,
          animation: { duration: 400 },
          interaction: { mode: "index", intersect: false },
          scales: {
            x: { title: { display: true, text: "Date" } },
            y: { beginAtZero: true, title: { display: true, text: `Amount (${currency})` } },
          },
          plugins: { legend: { position: "bottom", labels: { boxWidth: 10 } } },
        },
      });
    }
  }

  async function load() {
    const rng = rangeSel ? rangeSel.value : "1m";
    const url = new URL("/api/spend-series", window.location.origin);
    url.searchParams.set("range", rng);
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) return;
    lastData = await r.json();
    render();
  }

  if (rangeSel) rangeSel.addEventListener("change", load);
  document.addEventListener("activity-panel:changed", render);

  load();
})();
