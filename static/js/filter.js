// Клиентская фильтрация публикаций: по типу, году и поиску по названию.
(function () {
  const list = document.getElementById("pub-list");
  if (!list) return;
  const items = Array.from(list.querySelectorAll(".pub-item"));
  const empty = document.getElementById("empty-state");
  const search = document.getElementById("pub-search");
  const yearSel = document.getElementById("year-filter");
  const typeBtns = Array.from(document.querySelectorAll("#type-filters .chip"));

  const sortSel = document.getElementById("sort-filter");
  const state = { type: "all", year: "all", q: "", sort: "year_desc" };

  function sortItems() {
    const cmp = {
      year_desc: (a, b) => (b.dataset.year || "").localeCompare(a.dataset.year || ""),
      year_asc: (a, b) => (a.dataset.year || "").localeCompare(b.dataset.year || ""),
      type: (a, b) =>
        (a.dataset.typelabel || "").localeCompare(b.dataset.typelabel || "") ||
        (b.dataset.year || "").localeCompare(a.dataset.year || ""),
      journal: (a, b) =>
        (a.dataset.journal || "я").localeCompare(b.dataset.journal || "я") ||
        (b.dataset.year || "").localeCompare(a.dataset.year || ""),
    }[state.sort];
    items.slice().sort(cmp).forEach((el) => list.appendChild(el));
  }

  function apply() {
    let visible = 0;
    items.forEach((el) => {
      const okType = state.type === "all" || el.dataset.type === state.type;
      const okYear = state.year === "all" || el.dataset.year === state.year;
      const okQ = !state.q || (el.dataset.title || "").includes(state.q);
      const show = okType && okYear && okQ;
      el.hidden = !show;
      if (show) visible++;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  typeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      typeBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.type = btn.dataset.type;
      apply();
    });
  });

  if (yearSel) yearSel.addEventListener("change", () => { state.year = yearSel.value; apply(); });
  if (search) search.addEventListener("input", () => { state.q = search.value.trim().toLowerCase(); apply(); });
  if (sortSel) sortSel.addEventListener("change", () => { state.sort = sortSel.value; sortItems(); });
})();
