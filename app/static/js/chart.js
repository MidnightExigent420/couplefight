(function () {
  const canvas = document.getElementById("spend-chart");
  if (!canvas) return;
  const picker = document.getElementById("chart-pick");
  const replayPanel = document.getElementById("replay-panel");
  const prevBtn = document.getElementById("replay-prev");
  const nextBtn = document.getElementById("replay-next");
  const resetBtn = document.getElementById("replay-reset");
  const dayLabel = document.getElementById("replay-day");
  const emptyMsg = document.getElementById("chart-empty");

  let chart = null;
  let current = null; // { kind, id, start, end, upTo }

  function plotData(data) {
    emptyMsg.classList.add("hidden");
    replayPanel.classList.remove("hidden");

    const datasets = [{
      label: `${data.label} (${data.currency})`,
      data: data.values,
      borderColor: "#0ea5e9",
      backgroundColor: "rgba(14,165,233,0.15)",
      fill: true,
      tension: 0.2,
    }];
    if (data.goal_threshold !== null && data.goal_threshold !== undefined) {
      datasets.push({
        label: `Goal threshold (${data.goal_threshold} ${data.currency})`,
        data: data.labels.map(() => data.goal_threshold),
        borderColor: "#16a34a",
        borderDash: [6, 4],
        pointRadius: 0,
      });
    }
    (data.tripwire_thresholds || []).forEach((t, i) => {
      datasets.push({
        label: `Trip wire ${i + 1} (${t} ${data.currency})`,
        data: data.labels.map(() => t),
        borderColor: "#e11d48",
        borderDash: [4, 4],
        pointRadius: 0,
      });
    });

    if (chart) {
      chart.data.labels = data.labels;
      chart.data.datasets = datasets;
      chart.update();
    } else {
      chart = new Chart(canvas, {
        type: "line",
        data: { labels: data.labels, datasets },
        options: {
          responsive: true,
          animation: { duration: 600 },
          scales: { y: { beginAtZero: true } },
        },
      });
    }
  }

  async function load(kind, id, upTo) {
    const url = new URL("/api/chart", window.location.origin);
    url.searchParams.set("kind", kind);
    url.searchParams.set("id", id);
    if (upTo) url.searchParams.set("up_to", upTo);
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) return;
    const data = await r.json();
    current = { kind, id, start: data.start, end: data.end, upTo: upTo || data.end };
    dayLabel.textContent = "Showing through: " + current.upTo;
    plotData(data);
  }

  picker.addEventListener("change", () => {
    const v = picker.value;
    if (!v) return;
    const [kind, id] = v.split(":");
    load(kind, id, null);
  });

  function shiftDay(days) {
    if (!current) return;
    const d = new Date(current.upTo + "T00:00:00");
    d.setUTCDate(d.getUTCDate() + days);
    const start = new Date(current.start + "T00:00:00");
    const end = new Date(current.end + "T00:00:00");
    if (d < start) return;
    if (d > end) return;
    const iso = d.toISOString().slice(0, 10);
    load(current.kind, current.id, iso);
  }
  prevBtn.addEventListener("click", () => shiftDay(-1));
  nextBtn.addEventListener("click", () => shiftDay(1));
  resetBtn.addEventListener("click", () => {
    if (current) load(current.kind, current.id, null);
  });
})();
