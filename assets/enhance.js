/* Анимации поверх оригинального дизайна helpautism.ru */
(function () {
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var sel = [
    "section .section-header", ".pt-cv-content-item", ".one-client", ".focus-box", ".team-member",
    ".our-job .col-md-4", ".our-job .col-lg-4", "#footer .col-md-4", "#footer .col-md-3",
    ".site-main article", ".widget", ".master-slider-parent"
  ].join(",");
  function reveal() {
    var els = document.querySelectorAll(sel);
    if (reduced || !("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("ha-in"); io.unobserve(e.target); } });
    }, { threshold: 0.1, rootMargin: "0px 0px -30px 0px" });
    var groups = new Map();
    els.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top < innerHeight) return;                // уже видимое не прячем
      var p = el.parentNode, i = groups.get(p) || 0; groups.set(p, i + 1);
      el.style.setProperty("--ha-d", Math.min(i, 6) * 0.08 + "s");
      el.classList.add("ha-reveal"); io.observe(el);
    });
  }
  function topButton() {
    var b = document.createElement("button");
    b.className = "ha-top"; b.setAttribute("aria-label", "Наверх"); b.innerHTML = "&#8593;";
    b.onclick = function () { window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" }); };
    document.body.appendChild(b);
    var on = function () {
      document.body.classList.toggle("ha-scrolled", scrollY > 20);
      b.classList.toggle("ha-show", scrollY > 600);
    };
    addEventListener("scroll", on, { passive: true }); on();
  }
  function start() { reveal(); topButton(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
