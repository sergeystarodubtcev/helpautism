/* «Искра надежды» — анимации и интерактив поверх оригинального сайта */
(function () {
  "use strict";
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var finePointer = window.matchMedia && matchMedia("(hover: hover) and (pointer: fine)").matches;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- картинки, которых нет в веб-архиве ---------- */
  function brokenImages() {
    var logo = $(".ha-site-brand img");
    var logoSrc = logo ? logo.src : "";
    function handle(img) {
      if (img.dataset.haFixed) return; img.dataset.haFixed = "1";
      var unavailable = img.closest('a[href$="/404.html"][referrerpolicy="same-origin"], a[href="404.html"][referrerpolicy="same-origin"]');
      if (unavailable && !unavailable.textContent.trim()) {
        unavailable.textContent = img.alt.trim() || "Материал недоступен";
        return;
      }
      var card = img.closest(".ha-card__media");
      if (card) { img.remove(); var sp = document.createElement("span"); sp.className = "ha-card__noimg"; card.appendChild(sp); return; }
      var thumb = img.closest(".pt-cv-ifield, .post-img-wrap") || /thumbnail|wp-post-image/.test(img.className);
      if (thumb && logoSrc && img.src !== logoSrc) { img.src = logoSrc; img.classList.add("ha-placeholder"); }
      else {
        var g = img.closest(".ha-gallery__item");
        (g || img).style.display = "none";
      }
    }
    $$("img").forEach(function (img) { if (img.complete && img.naturalWidth === 0 && img.getAttribute("src")) handle(img); });
    window.addEventListener("error", function (e) { if (e.target && e.target.tagName === "IMG") handle(e.target); }, true);
  }

  /* ---------- шапка, прогресс, «наверх» ---------- */
  function chrome() {
    var bar = document.createElement("div"); bar.className = "ha-progress"; document.body.appendChild(bar);
    var top = document.createElement("button"); top.className = "ha-top"; top.setAttribute("aria-label", "Наверх"); top.innerHTML = "&#8593;";
    top.onclick = function () { window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" }); };
    document.body.appendChild(top);
    var ticking = false;
    function update() {
      ticking = false;
      var y = window.scrollY || window.pageYOffset, h = document.documentElement.scrollHeight - innerHeight;
      top.classList.toggle("ha-show", y > 700);
      bar.style.transform = "scaleX(" + (h > 0 ? y / h : 0) + ")";
    }
    addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    update();
  }

  /* ---------- навигация в закреплённой шапке ---------- */
  function siteNavigation() {
    var menu = $(".ha-navigation");
    if (!menu) return;
    var toggle = $(".ha-navigation__toggle", menu);

    document.addEventListener("click", function (e) {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
    document.addEventListener("focusin", function (e) {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
    menu.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" || !menu.open) return;
      var submenu = e.target.closest(".ha-submenu[open]");
      var disclosure = submenu || menu;
      disclosure.open = false;
      $(":scope > summary", disclosure).focus();
      e.preventDefault();
    });
    menu.addEventListener("click", function (e) {
      if (!e.target.closest("a")) return;
      menu.open = false;
      toggle.focus();
    });
  }

  /* ---------- партнёры: бегущая лента ---------- */
  function marquee() {
    var list = $(".client-list"); if (!list) return;
    var items = $$(".client-list > *, .client-list .one-client").filter(function (el) { return el.tagName === "A" || el.tagName === "IMG" || el.querySelector("img"); });
    var top = $$(":scope > *", list); if (!top.length) return;
    var track = document.createElement("div"); track.className = "ha-marquee";
    top.forEach(function (el) { track.appendChild(el); });
    if (!reduced) top.forEach(function (el) { var c = el.cloneNode(true); c.setAttribute("aria-hidden", "true"); track.appendChild(c); });
    list.appendChild(track);
    var n = top.length; track.style.animationDuration = Math.max(20, n * 3) + "s";
    void items;
  }

  /* ---------- плавное появление блоков ---------- */
  function reveal() {
    if (reduced || !("IntersectionObserver" in window)) return;
    var sel = [
      "section .section-header", ".ha-card", ".ha-listhead", ".focus-box", ".team-member", ".our-job .mk > div",
      ".purchase-now .btn", "#footer .container.hundred > div", ".site-main article", ".ha-gallery__item",
      ".nav-links > div", ".ha-notice", ".our-clients"
    ].join(",");
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("ha-in"); io.unobserve(e.target); } });
    }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    var groups = new Map();
    $$(sel).forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top < innerHeight * 0.95) return;          // то, что уже на экране, не прячем
      var p = el.parentNode, i = groups.get(p) || 0; groups.set(p, i + 1);
      el.style.setProperty("--ha-d", Math.min(i, 5) * 0.09 + "s");
      el.classList.add("ha-reveal"); io.observe(el);
    });
    // страховка: если что-то не сработало, через 4 секунды после прокрутки до блока он всё равно появится
    setTimeout(function () {
      $$(".ha-reveal:not(.ha-in)").forEach(function (el) { if (el.getBoundingClientRect().top < innerHeight) el.classList.add("ha-in"); });
    }, 4000);
  }

  /* ---------- искры на первом экране ---------- */
  function sparks() {
    var header = $(".ha-home .header"); if (!header || reduced) return;
    var cv = document.createElement("canvas"); cv.className = "ha-sparks"; header.insertBefore(cv, header.firstChild);
    var ctx = cv.getContext("2d"), dpr = Math.min(2, window.devicePixelRatio || 1), W, H, pts = [], running = true;
    var colors = ["255,194,61", "255,138,92", "236,90,76", "79,179,246", "255,255,255"];
    function spawn(p, initial) {
      p.x = Math.random() * W; p.y = initial ? Math.random() * H : H + 10;
      p.r = Math.random() * 2.2 + .6; p.vy = -(Math.random() * .6 + .25); p.vx = (Math.random() - .5) * .3;
      p.life = 0; p.max = 260 + Math.random() * 320; p.c = colors[(Math.random() * colors.length) | 0]; p.tw = Math.random() * 6.28;
      return p;
    }
    function resize() {
      W = header.clientWidth; H = header.clientHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.round(Math.min(90, W * H / 14000)); pts = []; for (var i = 0; i < n; i++) pts.push(spawn({}, true));
    }
    resize(); addEventListener("resize", resize, { passive: true });
    new IntersectionObserver(function (e) { running = e[0].isIntersecting; if (running) requestAnimationFrame(tick); }).observe(header);
    function tick() {
      if (!running) return;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (var i = 0; i < pts.length; i++) {
        var p = pts[i]; p.life++; p.x += p.vx + Math.sin((p.life + p.tw * 50) / 60) * .15; p.y += p.vy; p.tw += .05;
        var a = Math.sin(Math.PI * p.life / p.max) * (.55 + .45 * Math.sin(p.tw));
        if (p.life > p.max || p.y < -10) spawn(p, false);
        var g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 5);
        g.addColorStop(0, "rgba(" + p.c + "," + (a * .9) + ")"); g.addColorStop(1, "rgba(" + p.c + ",0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 5, 0, 6.283); ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
    // лёгкий параллакс фона при прокрутке
    addEventListener("scroll", function () {
      var y = Math.min(window.scrollY, H); header.style.setProperty("--ha-par", y * .25 + "px");
    }, { passive: true });
  }

  /* ---------- наклон карточек за курсором (компьютер) ---------- */
  function tilt() {
    if (reduced || !finePointer) return;
    $$(".pt-cv-ifield, .focus-box, .team-member, .our-job .mk > div").forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        var r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        el.style.transform = "perspective(900px) rotateX(" + (-y * 5) + "deg) rotateY(" + (x * 6) + "deg) translateY(-8px)";
      });
      el.addEventListener("pointerleave", function () { el.style.transform = ""; });
    });
    // «магнитные» кнопки
    $$(".header-content-wrap .btn, .purchase-now .btn").forEach(function (b) {
      b.addEventListener("pointermove", function (e) {
        var r = b.getBoundingClientRect();
        b.style.transform = "translate(" + ((e.clientX - r.left - r.width / 2) * .15) + "px," + ((e.clientY - r.top - r.height / 2) * .25 - 3) + "px)";
      });
      b.addEventListener("pointerleave", function () { b.style.transform = ""; });
    });
  }

  /* ---------- текущий раздел в меню ---------- */
  function currentNav() {
    var here = location.pathname.replace(/index\.html$/, "");
    $$(".ha-navigation__panel > ul > li, .ha-inline-menu > ul > li").forEach(function (li) {
      var hit = $$("a", li).some(function (a) {
        var p = a.pathname.replace(/index\.html$/, "");
        return a.host === location.host && p.length > 1 && here.indexOf(p) === 0;
      });
      li.classList.toggle("ha-current", hit);
    });
    $$(".ha-navigation__panel a, .ha-inline-menu a").forEach(function (a) {
      if (a.host === location.host && a.pathname.replace(/index\.html$/, "") === here && !a.hash) {
        a.setAttribute("aria-current", "page");
      }
    });
  }

  /* ---------- фото первого экрана: плавное «приближение» ---------- */
  function heroMedia() {
    var f = $(".ha-hero__media"); if (!f) return;
    var img = $("img", f);
    var go = function () { requestAnimationFrame(function () { f.classList.add("is-ready"); }); };
    if (img.complete) go(); else img.addEventListener("load", go);
    if (reduced) return;
    addEventListener("scroll", function () {
      var y = Math.min(window.scrollY, 800);
      img.style.translate = "0 " + (y * 0.06) + "px";
    }, { passive: true });
  }

  /* ---------- формы: проверка и отправка ---------- */
  function forms() {
    var cfg = window.HA_CONFIG || {};
    $$("form.ha-form").forEach(function (form) {
      var status = $(".ha-form__status", form);
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var ok = true;
        $$("[required]", form).forEach(function (el) {
          var bad = el.type === "checkbox" ? !el.checked : !String(el.value).trim();
          if (el.type === "email" && el.value && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(el.value)) bad = true;
          el.classList.toggle("ha-invalid", bad); if (bad) ok = false;
        });
        if (!ok) { status.className = "ha-form__status is-err"; status.textContent = "Заполните обязательные поля и отметьте согласие."; return; }
        var data = {}, lines = [];
        $$("input, textarea, select", form).forEach(function (el) {
          if (!el.name || (el.type === "checkbox" && !el.checked)) return;
          data[el.name] = data[el.name] ? data[el.name] + ", " + el.value : el.value;
        });
        Object.keys(data).forEach(function (k) { lines.push(k + ": " + data[k]); });
        var title = form.dataset.formTitle;
        if (cfg.FORMS_ENDPOINT) {
          var btn = $("button[type=submit]", form); btn.disabled = true;
          status.className = "ha-form__status"; status.textContent = "Отправляем…";
          fetch(cfg.FORMS_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ form: form.dataset.formId, title: title, page: location.href, fields: data }) })
            .then(function (r) { if (!r.ok) throw new Error(r.status); form.reset(); status.className = "ha-form__status is-ok"; status.textContent = "Спасибо! Мы получили ваше сообщение и скоро ответим."; })
            .catch(function () { status.className = "ha-form__status is-err"; status.textContent = "Не удалось отправить. Напишите нам на " + form.dataset.email; })
            .then(function () { btn.disabled = false; });
        } else {
          // пока нет сервера — открываем письмо с заполненными полями
          location.href = "mailto:" + form.dataset.email + "?subject=" + encodeURIComponent("Сайт: " + title) + "&body=" + encodeURIComponent(lines.join("\n"));
          status.className = "ha-form__status is-ok"; status.textContent = "Откроется ваша почта с заполненным письмом — нажмите «Отправить».";
        }
      });
    });
  }

  /* ---------- кнопки «Поделиться»: ВКонтакте, Одноклассники, Max ---------- */
  function share() {
    var content = $(".single .entry-content"); if (!content || $(".ha-share")) return;
    var url = encodeURIComponent(location.href), title = encodeURIComponent(document.title);
    var el = document.createElement("div"); el.className = "ha-share";
    el.innerHTML = "<span>Поделиться</span>" +
      '<a class="vk" target="_blank" rel="noopener" href="https://vk.com/share.php?url=' + url + '&title=' + title + '">ВКонтакте</a>' +
      '<a class="ok" target="_blank" rel="noopener" href="https://connect.ok.ru/offer?url=' + url + '&title=' + title + '">Одноклассники</a>' +
      '<a class="max" href="#" role="button">Max</a>';
    content.appendChild(el);
    // у Max нет публичной ссылки «поделиться»: на телефоне — системное меню (там есть Max), иначе копируем ссылку и открываем web.max.ru
    $(".max", el).addEventListener("click", function (e) {
      e.preventDefault();
      var data = { title: document.title, text: document.title, url: location.href };
      if (navigator.share) { navigator.share(data).catch(function () {}); return; }
      var done = function () { alert("Ссылка скопирована. Вставьте её в чат Max."); window.open("https://web.max.ru/", "_blank", "noopener"); };
      if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(done, done); else done();
    });
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---------- карточки «Родительский час» целиком кликабельны ---------- */
  function teamLinks() {
    $$(".our-team .team-member").forEach(function (card) {
      var a = $(".social-icons a, .details a", card); if (!a) return;
      card.style.cursor = "pointer";
      card.addEventListener("click", function (e) { if (!e.target.closest("a")) a.click(); });
    });
  }

  function start() {
    brokenImages(); chrome(); siteNavigation(); currentNav(); teamLinks(); marquee(); heroMedia(); share(); forms(); reveal();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
