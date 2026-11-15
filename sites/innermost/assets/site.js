/* «Сокровенный человек»: меню, анимации появления, прогресс прокрутки, лайтбокс, копирование реквизитов */
(function () {
  "use strict";
  var d = document, b = d.body;
  d.documentElement.classList.add("js");
  b.classList.add("js");

  // мобильное меню
  var burger = d.querySelector(".burger"), menu = d.getElementById("menu");
  function setMenu(on) { b.classList.toggle("menu-open", on); if (burger) burger.setAttribute("aria-expanded", on ? "true" : "false"); }
  if (burger) burger.addEventListener("click", function () { setMenu(!b.classList.contains("menu-open")); });
  if (menu) menu.addEventListener("click", function (e) { if (e.target.closest("a")) setMenu(false); });
  d.addEventListener("keydown", function (e) { if (e.key === "Escape") { setMenu(false); closeLb(); } });

  // шапка и прогресс
  var bar = d.querySelector(".progress"), ticking = false;
  function onScroll() {
    ticking = false;
    var y = window.scrollY, h = d.documentElement.scrollHeight - innerHeight;
    b.classList.toggle("scrolled", y > 8);
    if (bar) bar.style.transform = "scaleX(" + (h > 0 ? Math.min(1, y / h) : 0) + ")";
  }
  addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  // появление при прокрутке
  var els = d.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }); },
      { rootMargin: "0px 0px -8% 0px", threshold: .08 });
    els.forEach(function (el) { io.observe(el); });
  } else els.forEach(function (el) { el.classList.add("in"); });

  // лёгкий параллакс фигур на первом экране
  var shapes = d.querySelectorAll(".shape");
  if (shapes.length && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    addEventListener("scroll", function () {
      var y = scrollY; if (y > 900) return;
      shapes.forEach(function (s, i) { s.style.transform = "translateY(" + (y * (i ? .18 : -.12)) + "px) rotate(" + (y * (i ? .02 : -.03)) + "deg)"; });
    }, { passive: true });
  }

  // лайтбокс
  var lb = d.querySelector(".lb"), lbImg = lb && lb.querySelector("img");
  function closeLb() { if (lb) { lb.hidden = true; lbImg.src = ""; } }
  d.addEventListener("click", function (e) {
    var a = e.target.closest(".zoom, .content a[href$='.jpg'], .content a[href$='.jpeg'], .content a[href$='.png'], .content a[href$='.webp']");
    if (a && lb) { e.preventDefault(); lbImg.src = a.getAttribute("href"); lb.hidden = false; return; }
    if (lb && !lb.hidden && (e.target === lb || e.target.closest(".lb-x"))) closeLb();
  });

  // копирование реквизитов
  d.querySelectorAll(".copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var t = btn.getAttribute("data-copy") || "", old = btn.textContent;
      function done() { btn.textContent = "Скопировано ✓"; setTimeout(function () { btn.textContent = old; }, 2000); }
      if (navigator.clipboard) navigator.clipboard.writeText(t).then(done, function () { prompt("Скопируйте реквизиты:", t); });
      else prompt("Скопируйте реквизиты:", t);
    });
  });
})();
