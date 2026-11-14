/* MiniMe Atlas theme bootstrap (P01). Load synchronously in <head>, before any stylesheet paints.
   Order: saved choice (localStorage.minime_theme) > OS light preference on reader pages only > dark. */
(function (d, w) {
  var K = "minime_theme", r = d.documentElement, t = null;
  try { t = localStorage.getItem(K); } catch (e) {}
  if (t !== "dark" && t !== "paper")
    t = r.dataset.layout === "reader" && w.matchMedia && w.matchMedia("(prefers-color-scheme: light)").matches ? "paper" : "dark";
  r.dataset.theme = t;
  w.minimeTheme = {
    get: function () { return r.dataset.theme; },
    set: function (v) {
      if (v !== "dark" && v !== "paper") return;
      r.dataset.theme = v;
      try { localStorage.setItem(K, v); } catch (e) {}
      d.dispatchEvent(new CustomEvent("minime:theme", { detail: v }));
    },
    cycle: function () { this.set(r.dataset.theme === "dark" ? "paper" : "dark"); }
  };
})(document, window);
