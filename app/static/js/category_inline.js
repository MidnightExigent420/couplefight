(function () {
  const btn = document.getElementById("new-cat-btn");
  if (!btn) return;
  const input = document.getElementById("new-cat-input");
  const select = document.getElementById("cat-select");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  btn.addEventListener("click", async () => {
    const name = (input.value || "").trim();
    if (!name) return;
    const res = await fetch("/categories/", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) {
      alert("Could not add category.");
      return;
    }
    const data = await res.json();
    let opt = Array.from(select.options).find((o) => parseInt(o.value, 10) === data.id);
    if (!opt) {
      opt = new Option(data.name, data.id, true, true);
      select.add(opt);
    }
    select.value = String(data.id);
    input.value = "";
  });
})();
