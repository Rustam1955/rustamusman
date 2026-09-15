// Единая кнопка настроек в шапке — как в приложении IlmNur: три строки
// (язык с флагом, день/ночь, фон экрана); язык и фон открываются панелями.
// Тема и фон живут в localStorage и ставятся атрибутами на <html>; раннее
// применение — во встроенном скрипте в <head>, чтобы страница не мигала.
// Фоны — тот же набор, что в приложении: список и превью отдаёт служба
// IlmNur на этом же домене (/backgrounds), выбранный хранится как «img:<имя>».
(function () {
  const root = document.documentElement;
  const btn = document.getElementById("settings-btn");
  const menu = document.getElementById("settings-menu");
  if (!btn || !menu) return;
  const themeBtn = document.getElementById("set-theme");
  const grid = document.getElementById("set-bg-grid");
  let backgroundsLoaded = false;

  function read(key, fallback) {
    try { return localStorage.getItem(key) || fallback; } catch (e) { return fallback; }
  }

  function save(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { }
  }

  function currentTheme() {
    return root.getAttribute("data-theme")
      || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }

  // Прежний вариант «photo» — та же картинка, она есть в наборе приложения
  function currentBackground() {
    const bg = read("bg", "glow");
    return bg === "photo" ? "img:site_bg.jpg" : bg;
  }

  function applyBackground(value) {
    if (value.indexOf("img:") === 0) {
      root.style.setProperty("--bg-image",
        'url("/backgrounds/' + encodeURIComponent(value.slice(4)) + '")');
      root.setAttribute("data-bg", "img");
    } else {
      root.style.removeProperty("--bg-image");
      root.setAttribute("data-bg", value);
    }
  }

  // Меню показывает текущее состояние: солнце или луна с подписью, как в
  // приложении, и рамка у выбранного фона
  function sync() {
    const night = currentTheme() === "dark";
    if (themeBtn) {
      themeBtn.classList.toggle("is-night", night);
      themeBtn.querySelector(".set-theme-text").textContent =
        night ? themeBtn.dataset.night : themeBtn.dataset.day;
    }
    if (grid) {
      const bg = currentBackground();
      grid.querySelectorAll("[data-bg-value]").forEach((el) => {
        el.classList.toggle("active", el.dataset.bgValue === bg);
      });
    }
  }

  function show(panel) {
    menu.querySelectorAll("[data-panel]").forEach((p) => {
      p.hidden = p.dataset.panel !== panel;
    });
    if (panel === "bg") loadBackgrounds();
  }

  function open(state) {
    menu.hidden = !state;
    btn.setAttribute("aria-expanded", String(state));
    if (state) show("main");
  }

  // Картинки набора — один раз, при первом открытии панели фона: 45 превью
  // незачем грузить каждому, кто просто читает страницу
  async function loadBackgrounds() {
    if (backgroundsLoaded || !grid) return;
    backgroundsLoaded = true;
    try {
      const answer = await fetch(grid.dataset.list);
      if (!answer.ok) throw new Error(String(answer.status));
      const list = await answer.json();
      list.forEach((item) => {
        const tile = document.createElement("button");
        tile.type = "button";
        tile.className = "set-bg-tile";
        tile.dataset.bgValue = "img:" + item.id;
        tile.title = item.name;
        const picture = document.createElement("img");
        picture.loading = "lazy";
        picture.alt = "";
        picture.src = "/backgrounds/" + encodeURIComponent(item.id) + "/thumb";
        tile.appendChild(picture);
        grid.appendChild(tile);
      });
      sync();
    } catch (e) {
      // Службы IlmNur рядом нет (сайт запущен сам по себе) — остаются
      // «Сияние» и «Без фона»; при следующем открытии попробуем снова
      backgroundsLoaded = false;
    }
  }

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    open(menu.hidden);
  });

  menu.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-open]");
    if (opener) {
      show(opener.dataset.open);
      return;
    }
    if (e.target.closest("#set-theme")) {
      const next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      save("theme", next);
      sync();
      return;
    }
    const tile = e.target.closest("[data-bg-value]");
    if (tile) {
      applyBackground(tile.dataset.bgValue);
      save("bg", tile.dataset.bgValue);
      sync();
    }
    // ссылки языков не перехватываем — это обычный переход
  });

  document.addEventListener("click", (e) => {
    if (!menu.hidden && !menu.contains(e.target) && e.target !== btn) open(false);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !menu.hidden) {
      open(false);
      btn.focus();
    }
  });

  sync();
})();
