(function () {
  const panel = document.getElementById("activity-panel");
  if (!panel) return;

  const list = document.getElementById("ap-list");
  const search = document.getElementById("ap-search");
  const chips = panel.querySelectorAll(".ap-chip");
  const sortBtns = panel.querySelectorAll(".ap-sort");
  const toggleBtn = document.getElementById("activity-panel-toggle");
  const closeBtn = document.getElementById("activity-panel-close");

  const STATE_KEY = "cf.activity-panel.v1";

  const state = loadState() || {
    kind: { goal: true, tripwire: true },
    bucket: { active: true, pending: true, completed: false, inactive: false },
    sort: { col: "created", dir: "desc" },
    search: "",
  };

  function loadState() {
    try {
      const raw = localStorage.getItem(STATE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }
  function saveState() {
    try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); } catch (e) {}
  }

  function applyChipUI() {
    chips.forEach((btn) => {
      const group = btn.dataset.chip;
      const val = btn.dataset.value;
      const on = !!(state[group] && state[group][val]);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.classList.toggle("ap-chip-on", on);
    });
  }

  function applySortUI() {
    sortBtns.forEach((b) => {
      if (b.dataset.sortCol === state.sort.col) {
        b.dataset.active = state.sort.dir;
      } else {
        delete b.dataset.active;
      }
    });
  }

  function applyFilter() {
    const q = (state.search || "").trim().toLowerCase();
    const items = list.querySelectorAll(".ap-item");
    items.forEach((li) => {
      const kind = li.dataset.kind;
      const buckets = (li.dataset.bucket || "").split(/\s+/).filter(Boolean);
      const label = li.dataset.label || "";
      let show = true;
      if (!state.kind[kind]) show = false;
      if (show) {
        const anyBucket = buckets.some((b) => state.bucket[b]);
        if (!anyBucket) show = false;
      }
      if (show && q && !label.includes(q)) show = false;
      li.style.display = show ? "" : "none";
    });
  }

  function applySort() {
    const col = state.sort.col;
    const dir = state.sort.dir === "asc" ? 1 : -1;
    const items = Array.from(list.querySelectorAll(".ap-item"));
    items.sort((a, b) => {
      const av = a.dataset[col === "created" ? "created" : col === "end" ? "end" : col] || "";
      const bv = b.dataset[col === "created" ? "created" : col === "end" ? "end" : col] || "";
      if (col === "status" || col === "label") {
        return dir * av.localeCompare(bv);
      }
      // ISO date strings sort lexicographically.
      return dir * (av < bv ? -1 : av > bv ? 1 : 0);
    });
    items.forEach((li) => list.appendChild(li));
  }

  function refresh() {
    applyChipUI();
    applySortUI();
    applyFilter();
    applySort();
    saveState();
    document.dispatchEvent(new CustomEvent("activity-panel:changed"));
  }

  chips.forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = btn.dataset.chip;
      const val = btn.dataset.value;
      state[group][val] = !state[group][val];
      refresh();
    });
  });

  sortBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const col = btn.dataset.sortCol;
      if (state.sort.col === col) {
        state.sort.dir = state.sort.dir === "asc" ? "desc" : "asc";
      } else {
        state.sort.col = col;
        state.sort.dir = col === "label" || col === "status" ? "asc" : "desc";
      }
      refresh();
    });
  });

  if (search) {
    search.value = state.search || "";
    search.addEventListener("input", () => {
      state.search = search.value;
      applyFilter();
      saveState();
      document.dispatchEvent(new CustomEvent("activity-panel:changed"));
    });
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      panel.classList.toggle("translate-x-full");
    });
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      panel.classList.add("translate-x-full");
    });
  }

  refresh();
})();
