// Единая кнопка настроек в шапке: язык + тема (день/ночь) + фон экрана.
// Тема и фон живут в localStorage и применяются атрибутами на <html>;
// раннее применение — во встроенном скрипте в <head>, чтобы не было мигания.
(function () {
  const root = document.documentElement;
  const btn = document.getElementById("settings-btn");
  const menu = document.getElementById("settings-menu");
  if (!btn || !menu) return;

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

  // Отмечаем активные варианты, чтобы меню показывало текущее состояние.
  function sync() {
    const theme = currentTheme();
    const bg = root.getAttribute("data-bg") || "glow";
    menu.querySelectorAll("[data-theme-value]").forEach((el) => {
      el.classList.toggle("active", el.dataset.themeValue === theme);
    });
    menu.querySelectorAll("[data-bg-value]").forEach((el) => {
      el.classList.toggle("active", el.dataset.bgValue === bg);
    });
  }

  function open(state) {
    menu.hidden = !state;
    btn.setAttribute("aria-expanded", String(state));
  }

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    open(menu.hidden);
  });

  menu.addEventListener("click", (e) => {
    const themeBtn = e.target.closest("[data-theme-value]");
    if (themeBtn) {
      root.setAttribute("data-theme", themeBtn.dataset.themeValue);
      save("theme", themeBtn.dataset.themeValue);
      sync();
      return;
    }
    const bgBtn = e.target.closest("[data-bg-value]");
    if (bgBtn) {
      root.setAttribute("data-bg", bgBtn.dataset.bgValue);
      save("bg", bgBtn.dataset.bgValue);
      sync();
    }
    // клик по ссылке языка не перехватываем — это обычный переход
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

  root.setAttribute("data-bg", read("bg", "glow"));
  sync();
})();
