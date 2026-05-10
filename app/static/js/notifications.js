(function () {
  const bellBtn = document.getElementById("bell-btn");
  if (!bellBtn) return;

  const drawer = document.getElementById("bell-drawer");
  const list = document.getElementById("bell-list");
  const count = document.getElementById("bell-count");
  const markAllBtn = document.getElementById("mark-all");
  const pointsPill = document.getElementById("points-pill");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  const escape = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  async function poll() {
    try {
      const r = await fetch("/api/notifications", { credentials: "same-origin" });
      if (!r.ok) return;
      const data = await r.json();
      render(data);
    } catch (e) { /* swallow */ }
  }

  function render(data) {
    if (data.unread > 0) {
      count.textContent = data.unread;
      count.classList.remove("hidden");
    } else {
      count.classList.add("hidden");
    }
    if (pointsPill) pointsPill.textContent = "★ " + (data.points ?? 0) + " pts";

    list.innerHTML = "";
    if (!data.items.length) {
      list.innerHTML = '<li class="px-4 py-3 text-sm text-slate-500">No notifications.</li>';
      return;
    }
    for (const n of data.items) {
      const li = document.createElement("li");
      li.className = "px-4 py-3 text-sm " + (n.read ? "opacity-60" : "bg-rose-50");
      let actions = "";
      if (n.type === "goal_pending" && n.payload && n.payload.startsWith("goal:")) {
        const gid = parseInt(n.payload.split(":")[1], 10);
        if (Number.isInteger(gid)) {
          actions = `
            <div class="mt-2 flex gap-2">
              <form method="post" action="/goals/${gid}/approve">
                <input type="hidden" name="csrf_token" value="${escape(csrf)}">
                <button class="text-xs bg-emerald-600 text-white px-2 py-1 rounded">Approve</button>
              </form>
              <form method="post" action="/goals/${gid}/reject">
                <input type="hidden" name="csrf_token" value="${escape(csrf)}">
                <button class="text-xs bg-rose-600 text-white px-2 py-1 rounded">Reject</button>
              </form>
            </div>`;
        }
      }
      li.innerHTML = `
        <div class="flex items-start justify-between gap-2">
          <div>
            <p class="${n.read ? "" : "font-semibold"}">${escape(n.message)}</p>
            <p class="text-xs text-slate-500">${escape(n.created_at || "")}</p>
            ${actions}
          </div>
          ${n.read ? "" : `<button data-id="${n.id}" class="mark-one text-xs text-rose-600">Mark</button>`}
        </div>`;
      list.appendChild(li);
    }
    list.querySelectorAll(".mark-one").forEach((b) => {
      b.addEventListener("click", async () => {
        const id = parseInt(b.dataset.id, 10);
        await fetch(`/api/notifications/${id}/read`, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": csrf },
        });
        poll();
      });
    });
  }

  bellBtn.addEventListener("click", () => drawer.classList.toggle("hidden"));
  document.addEventListener("click", (e) => {
    if (!drawer.contains(e.target) && !bellBtn.contains(e.target)) drawer.classList.add("hidden");
  });
  markAllBtn.addEventListener("click", async () => {
    await fetch("/api/notifications/read-all", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf },
    });
    poll();
  });

  poll();
  setInterval(poll, 30000);
})();
