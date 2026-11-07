/* Искра надежды — статический сайт. Контент берётся из data/*.json */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s = "") => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const main = $("#main");
  const state = { site: null, projects: [], news: [], pages: [] };

  const ICONS = {
    puzzle: '<path d="M10 3h4v3a2 2 0 1 0 4 0V3h3v7h-3a2 2 0 1 0 0 4h3v7h-7v-3a2 2 0 1 0-4 0v3H3v-7h3a2 2 0 1 0 0-4H3V3h7z"/>',
    family: '<circle cx="8" cy="6" r="3"/><circle cx="17" cy="8" r="2.5"/><path d="M3 21v-4a5 5 0 0 1 10 0v4M13 21v-3a4 4 0 0 1 8 0v3"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    hands: '<path d="M7 11V5a1.5 1.5 0 0 1 3 0v5M10 10V4a1.5 1.5 0 0 1 3 0v6M13 10V5a1.5 1.5 0 0 1 3 0v6M16 11V8a1.5 1.5 0 0 1 3 0v6a7 7 0 0 1-7 7h-1a7 7 0 0 1-6-3.4L3 14a1.5 1.5 0 0 1 2.6-1.5L7 14"/>',
    home: '<path d="M3 11 12 3l9 8v10h-6v-6H9v6H3z"/>',
    shield: '<path d="M12 2 4 5v6c0 5 3.4 9.5 8 11 4.6-1.5 8-6 8-11V5z"/><path d="m9 12 2 2 4-4"/>',
    heart: '<path d="M12 21s-8-5.3-8-11a5 5 0 0 1 8-4 5 5 0 0 1 8 4c0 5.7-8 11-8 11z"/>',
    phone: '<path d="M5 3h4l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    pin: '<path d="M12 22s7-6.5 7-12a7 7 0 0 0-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    star: '<path d="M12 2l2.6 7.4H22l-6 4.6 2.3 7.4L12 17l-6.3 4.4L8 14 2 9.4h7.4z"/>',
    vk: '<path d="M3 7h3.5c.3 4 2 6 3.5 6.4V7H13v3.6c1.5-.2 3-2 3.5-3.6H20c-.5 2.3-2.2 4-3.4 4.8 1.2.6 3 2 3.8 4.2h-3.7c-.7-1.6-2-2.8-3.7-3V16C6.6 16 3.3 12.6 3 7z" fill="currentColor" stroke="none"/>'
  };
  const icon = (n, size = 26) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n] || ICONS.star}</svg>`;

  const fmtDate = d => {
    if (!d) return "";
    const dt = new Date(d + "T12:00:00");
    return isNaN(dt) ? d : dt.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
  };
  const splitWords = (t, cls = "", off = 0) => esc(t).split(" ").map((w, i) => `<span class="w ${cls}" style="--i:${i + off}">${w}</span>`).join(" ");
  const tel = p => "tel:" + p.replace(/[^\d+]/g, "").replace(/^8/, "+7");

  async function load() {
    const get = f => fetch(`data/${f}.json`, { cache: "no-cache" }).then(r => { if (!r.ok) throw new Error(f); return r.json(); });
    [state.site, state.projects, state.news, state.pages] = await Promise.all([get("site"), get("projects"), get("news"), get("pages").catch(() => [])]);
    state.news.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  }

  /* ---------- layout ---------- */
  function renderChrome() {
    const s = state.site;
    $("#nav").innerHTML = s.menu.map(m => `<a href="${m.href}">${esc(m.title)}</a>`).join("");
    const c = s.contacts;
    $("#footer").innerHTML = `
      <div>
        <a class="logo" href="#/"><img src="assets/img/logo.svg" alt="" width="40" height="40"><span>Искра<br>надежды</span></a>
        <p>${esc(s.fullName)}</p>
      </div>
      <div><h4>Разделы</h4><ul>${s.menu.map(m => `<li><a href="${m.href}">${esc(m.title)}</a></li>`).join("")}</ul></div>
      <div><h4>Контакты</h4><ul>
        <li>${esc(c.address)}</li>
        ${c.phones.slice(0, 2).map(p => `<li><a href="${tel(p)}">${esc(p)}</a></li>`).join("")}
        ${c.emails.map(e => `<li><a href="mailto:${esc(e)}">${esc(e)}</a></li>`).join("")}
        ${s.social.map(x => `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a></li>`).join("")}
      </ul></div>
      <div class="footer__bottom"><span>© ${new Date().getFullYear()} ${esc(s.shortName)}</span><span>Сделано с заботой о каждом ребёнке</span></div>`;
  }

  const sectionHead = (kicker, title, text = "", link = "") => `
    <div class="section__head reveal">
      <div><span class="kicker">${kicker}</span><h2>${title}</h2></div>
      ${text ? `<p>${text}</p>` : ""}${link}
    </div>`;

  const projectCard = (p, i) => `
    <article class="card reveal tilt" style="--d:${(i % 3) * .1}s">
      <div class="card__icon">${icon(p.icon)}</div>
      <h3><a class="stretched" href="#/projects/${p.id}">${esc(p.title)}</a></h3>
      <p>${esc(p.short)}</p>
    </article>`;

  const newsCard = (n, i) => `
    <a class="news-card reveal" style="--d:${(i % 3) * .1}s" href="#/news/${encodeURIComponent(n.slug)}">
      <div class="news-card__img">${n.image ? `<img src="${esc(n.image)}" alt="" loading="lazy">` : icon("puzzle", 70)}</div>
      <div class="news-card__body">
        ${n.date ? `<time datetime="${n.date}">${fmtDate(n.date)}</time>` : ""}
        <h3>${esc(n.title)}</h3>
        <p>${esc(n.excerpt)}</p>
      </div>
    </a>`;

  const donateBlock = () => {
    const d = state.site.donate;
    return `<section class="section"><div class="container">
      <div class="donate reveal">
        <div class="donate__sparks">${Array.from({ length: 18 }, (_, i) => `<i style="left:${(i * 53) % 100}%;top:${60 + (i * 37) % 40}%;animation-delay:${(i * .37) % 4}s"></i>`).join("")}</div>
        <span class="kicker" style="color:#ffd9a8">Каждая помощь важна</span>
        <h2>${esc(d.title)}</h2>
        <p>${esc(d.text)}</p>
        <div class="hero__actions"><a class="btn" href="${esc(d.url)}" target="_blank" rel="noopener">${icon("heart", 20)} ${esc(d.button)}</a>
        <a class="btn btn--ghost" style="color:#fff;box-shadow:inset 0 0 0 2px rgba(255,255,255,.5)" href="#/help">Другие способы</a></div>
      </div></div></section>`;
  };

  /* ---------- pages ---------- */
  const pages = {
    home() {
      const s = state.site;
      return `
      <section class="hero">
        <canvas id="sparks" aria-hidden="true"></canvas>
        <div class="hero__blob hero__blob--1"></div><div class="hero__blob hero__blob--2"></div><div class="hero__blob hero__blob--3"></div>
        <div class="container hero__grid">
          <div>
            <span class="eyebrow">${esc(s.shortName)} · Воронеж</span>
            <h1 class="split-text">${splitWords(s.heroTitle.split(".")[0] + ".")} ${splitWords(s.heroTitle.split(".").slice(1).join(".").trim(), "grad", 1)}</h1>
            <p class="hero__lead reveal">${esc(s.heroText)}</p>
            <div class="hero__actions reveal" style="--d:.15s">
              <a class="btn" href="#/projects">Наши проекты</a>
              <a class="btn btn--ghost" href="#/contacts">Записаться на занятия</a>
            </div>
          </div>
          <div class="hero__art reveal" style="--d:.2s" aria-hidden="true">
            <div class="puzzle"><div>Занятия ABA</div><div>Поддержка семьи</div><div>Правовая помощь</div><div>Взрослая жизнь</div></div>
          </div>
        </div>
        <svg class="hero__wave" viewBox="0 0 1440 80" preserveAspectRatio="none"><path fill="currentColor" d="M0 40c240 40 480 40 720 20s480-50 720-20v40H0z"/></svg>
      </section>
      <div class="container stats">
        ${s.stats.map((st, i) => `<div class="stat reveal" style="--d:${i * .1}s"><b class="grad" data-count="${st.value}" data-suffix="${st.suffix}" ${st.plain ? "data-plain" : ""}>${st.plain ? st.value : 0}${st.suffix}</b><span>${esc(st.label)}</span></div>`).join("")}
      </div>
      <section class="section"><div class="container">
        ${sectionHead("Чем мы занимаемся", "Проекты и направления", "Мы помогаем ребёнку, семье и взрослому человеку с аутизмом на каждом этапе жизни.", '<a class="btn btn--ghost" href="#/projects">Все проекты</a>')}
        <div class="cards">${state.projects.slice(0, 6).map(projectCard).join("")}</div>
      </div></section>
      <section class="section section--tint"><div class="container">
        ${sectionHead("Новости", "Что у нас происходит", "", '<a class="btn btn--ghost" href="#/news">Все новости</a>')}
        <div class="news">${state.news.slice(0, 3).map(newsCard).join("")}</div>
      </div></section>
      ${donateBlock()}`;
    },

    about() {
      const s = state.site;
      return `
      <section class="page-hero"><div class="container">
        <div class="breadcrumbs"><a href="#/">Главная</a> / О нас</div>
        <h1 class="split-text">${splitWords("О нас")}</h1>
      </div></section>
      <section class="section" style="padding-top:20px"><div class="container split">
        <div class="reveal">
          <span class="kicker">${esc(s.shortName)}</span>
          <h2>Родители, которые объединились, чтобы помогать</h2>
          <p>${esc(s.fullName)}.</p>
          <p>Организация объединяет семьи, которые воспитывают детей с расстройствами аутистического спектра. Мы проводим занятия, поддерживаем родителей, защищаем права людей с инвалидностью и создаём условия для самостоятельной взрослой жизни.</p>
          <ul class="values">
            <li>Ранняя помощь и занятия для детей дошкольного и младшего школьного возраста</li>
            <li>Поддержка и обучение родителей</li>
            <li>Помощь подросткам и взрослым: занятость, общение, сопровождаемое проживание</li>
            <li>Правовая защита и консультации</li>
          </ul>
        </div>
        <div class="quote-card reveal" style="--d:.15s">
          <p>Мы хотим, чтобы каждый человек с аутизмом мог учиться, работать, дружить и жить рядом со всеми.</p>
          <span>${esc(s.contacts.head)}</span>
        </div>
      </div></section>
      ${donateBlock()}`;
    },

    projects(id) {
      if (id) {
        const p = state.projects.find(x => x.id === id);
        if (!p) return pages.notFound();
        return `
        <section class="page-hero"><div class="container">
          <div class="breadcrumbs"><a href="#/">Главная</a> / <a href="#/projects">Проекты</a> / ${esc(p.title)}</div>
          <h1 class="split-text">${splitWords(p.title)}</h1>
        </div></section>
        <div class="container"><article class="article reveal">
          <p style="font-size:1.2rem;color:var(--muted)">${esc(p.short)}</p>
          ${p.html || `<p>${esc(p.text)}</p>`}
          <p><a class="btn" href="#/contacts">Связаться с нами</a></p>
        </article></div>`;
      }
      return `
      <section class="page-hero"><div class="container">
        <div class="breadcrumbs"><a href="#/">Главная</a> / Проекты</div>
        <h1 class="split-text">${splitWords("Наши проекты")}</h1>
      </div></section>
      <section class="section" style="padding-top:20px"><div class="container">
        <div class="cards">${state.projects.map(projectCard).join("")}</div>
      </div></section>
      ${donateBlock()}`;
    },

    news(slug) {
      if (slug) {
        slug = decodeURIComponent(slug);
        const n = state.news.find(x => x.slug === slug) || state.pages.find(x => x.slug === slug);
        if (!n) return pages.notFound();
        return `
        <section class="page-hero"><div class="container">
          <div class="breadcrumbs"><a href="#/">Главная</a> / <a href="#/news">Новости</a></div>
          ${n.date ? `<time style="color:var(--accent);font-weight:700">${fmtDate(n.date)}</time>` : ""}
          <h1 style="font-size:clamp(1.7rem,4vw,2.8rem);max-width:900px" class="split-text">${splitWords(n.title)}</h1>
        </div></section>
        <div class="container"><article class="article reveal">
          ${n.image ? `<img src="${esc(n.image)}" alt="">` : ""}
          ${n.content || `<p>${esc(n.excerpt)}</p>`}
          ${n.restored ? "" : `<div class="notice">Полный текст материала переносится со старого сайта и скоро появится здесь.</div>`}
          <p><a class="btn btn--ghost" href="#/news">← Все новости</a></p>
        </article></div>`;
      }
      return `
      <section class="page-hero"><div class="container">
        <div class="breadcrumbs"><a href="#/">Главная</a> / Новости</div>
        <h1 class="split-text">${splitWords("Новости и статьи")}</h1>
      </div></section>
      <section class="section" style="padding-top:20px"><div class="container">
        <div class="news">${state.news.map(newsCard).join("")}</div>
      </div></section>`;
    },

    help() {
      const s = state.site;
      const ways = [
        ["heart", "Пожертвование", "Разовое или ежемесячное пожертвование на платформе Благо.ру. Деньги идут на занятия с детьми и содержание помещения.", `<a class="btn" href="${esc(s.donate.url)}" target="_blank" rel="noopener">Пожертвовать</a>`],
        ["hands", "Стать волонтёром", "Помогайте на мероприятиях, во встречах молодёжного клуба и в летних сменах.", `<a class="btn btn--ghost" href="#/contacts">Написать нам</a>`],
        ["star", "Помочь профессионально", "Юристы, психологи, дизайнеры, фотографы: ваши навыки очень нужны организации.", `<a class="btn btn--ghost" href="mailto:${esc(s.contacts.emails[0])}">Предложить помощь</a>`],
        ["family", "Рассказать о нас", "Поделитесь нашими новостями. Так о нас узнает ещё одна семья, которой нужна поддержка.", s.social.map(x => `<a class="btn btn--ghost" href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>`).join(" ")]
      ];
      return `
      <section class="page-hero"><div class="container">
        <div class="breadcrumbs"><a href="#/">Главная</a> / Помочь</div>
        <h1 class="split-text">${splitWords("Как помочь")}</h1>
      </div></section>
      <section class="section" style="padding-top:20px"><div class="container ways">
        ${ways.map((w, i) => `<article class="card reveal tilt" style="--d:${(i % 2) * .1}s"><div class="card__icon">${icon(w[0])}</div><h3>${w[1]}</h3><p style="margin-bottom:20px">${w[2]}</p>${w[3]}</article>`).join("")}
      </div></section>
      ${donateBlock()}`;
    },

    contacts() {
      const c = state.site.contacts;
      const item = (ic, label, val) => `<div class="contact-item reveal">${icon(ic)}<div><small>${label}</small>${val}</div></div>`;
      return `
      <section class="page-hero"><div class="container">
        <div class="breadcrumbs"><a href="#/">Главная</a> / Контакты</div>
        <h1 class="split-text">${splitWords("Контакты")}</h1>
      </div></section>
      <section class="section" style="padding-top:20px"><div class="container contacts">
        <div>
          <div class="contact-list">
            ${item("pin", "Адрес", `<span>${esc(c.address)}</span>`)}
            ${item("phone", "Телефоны", c.phones.map(p => `<a href="${tel(p)}">${esc(p)}</a>`).join("<br>"))}
            ${item("mail", "Почта", c.emails.map(e => `<a href="mailto:${esc(e)}">${esc(e)}</a>`).join("<br>"))}
            ${item("user", "Руководитель", `<span>${esc(c.head)}</span>`)}
          </div>
          <form class="form reveal" id="contact-form">
            <h3 style="margin:0">Написать нам</h3>
            <label>Ваше имя<input name="name" required autocomplete="name"></label>
            <label>Телефон или e-mail<input name="contact" required></label>
            <label>Сообщение<textarea name="msg" rows="4" required></textarea></label>
            <button class="btn" type="submit">Отправить</button>
            <small>Письмо откроется в вашем почтовом приложении.</small>
          </form>
        </div>
        <div class="map reveal" style="--d:.15s">
          <iframe title="Карта" loading="lazy" src="https://yandex.ru/map-widget/v1/?text=${encodeURIComponent(c.mapQuery)}&z=16"></iframe>
        </div>
      </div></section>`;
    },

    notFound() {
      return `<section class="page-hero"><div class="container" style="text-align:center;padding:80px 0">
        <h1 class="grad" style="font-size:6rem">404</h1><p>Такой страницы нет. Возможно, она ещё переносится со старого сайта.</p>
        <a class="btn" href="#/">На главную</a></div></section>`;
    }
  };

  /* ---------- router ---------- */
  function route() {
    const [, name = "", param] = (location.hash.replace(/^#/, "") || "/").split("/");
    const fn = name === "" ? pages.home : pages[name];
    main.innerHTML = fn ? fn(param) : pages.notFound();
    main.classList.remove("page-enter"); void main.offsetWidth; main.classList.add("page-enter");
    $$("#nav a").forEach(a => a.classList.toggle("is-active", a.getAttribute("href") === "#/" + name));
    const titles = { about: "О нас", projects: "Проекты", news: "Новости", help: "Помочь", contacts: "Контакты" };
    const art = name === "news" && param && [...state.news, ...state.pages].find(n => n.slug === decodeURIComponent(param));
    document.title = (art ? art.title : titles[name] ? titles[name] : "Помощь семьям с детьми с аутизмом, Воронеж") + " — Искра надежды";
    closeMenu();
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
    enhance();
  }

  /* ---------- effects ---------- */
  let io;
  function enhance() {
    io && io.disconnect();
    io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } }), { threshold: .12, rootMargin: "0px 0px -40px 0px" });
    $$(".reveal").forEach(el => reduced ? el.classList.add("is-in") : io.observe(el));

    const co = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return; co.unobserve(e.target);
      const el = e.target, to = +el.dataset.count, suf = el.dataset.suffix || "";
      if (el.hasAttribute("data-plain") || reduced) { el.textContent = to + suf; return; }
      const t0 = performance.now(), dur = 1600;
      const step = t => { const k = Math.min(1, (t - t0) / dur), v = Math.round(to * (1 - Math.pow(1 - k, 3))); el.textContent = v + suf; k < 1 && requestAnimationFrame(step); };
      requestAnimationFrame(step);
    }), { threshold: .5 });
    $$("[data-count]").forEach(el => co.observe(el));

    if (!reduced && matchMedia("(hover: hover)").matches) {
      $$(".tilt").forEach(card => {
        card.addEventListener("pointermove", e => {
          const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
          card.style.setProperty("--mx", x * 100 + "%"); card.style.setProperty("--my", y * 100 + "%");
          card.style.transform = `perspective(900px) rotateX(${(.5 - y) * 6}deg) rotateY(${(x - .5) * 8}deg) translateY(-4px)`;
        });
        card.addEventListener("pointerleave", () => { card.style.transform = ""; });
      });
    }

    const form = $("#contact-form");
    form && form.addEventListener("submit", e => {
      e.preventDefault();
      const f = new FormData(form);
      const body = `Имя: ${f.get("name")}\nКонтакт: ${f.get("contact")}\n\n${f.get("msg")}`;
      location.href = `mailto:${state.site.contacts.emails[0]}?subject=${encodeURIComponent("Сообщение с сайта helpautism.ru")}&body=${encodeURIComponent(body)}`;
    });

    sparks();
  }

  let rafId;
  function sparks() {
    cancelAnimationFrame(rafId);
    const cv = $("#sparks"); if (!cv || reduced) return;
    const ctx = cv.getContext("2d"), dpr = Math.min(2, devicePixelRatio || 1);
    let W, H, pts, mouse = { x: -999, y: -999 };
    const resize = () => {
      W = cv.clientWidth; H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.round(Math.min(70, W * H / 16000));
      pts = Array.from({ length: n }, () => ({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .3, vy: (Math.random() - .5) * .3, r: Math.random() * 2 + .8, h: [250, 195, 15, 35][Math.random() * 4 | 0] }));
    };
    resize(); addEventListener("resize", resize, { passive: true });
    cv.parentElement.addEventListener("pointermove", e => { const r = cv.getBoundingClientRect(); mouse = { x: e.clientX - r.left, y: e.clientY - r.top }; });
    const tick = () => {
      if (!document.body.contains(cv)) return;
      ctx.clearRect(0, 0, W, H);
      for (const p of pts) {
        const dx = p.x - mouse.x, dy = p.y - mouse.y, d = Math.hypot(dx, dy);
        if (d < 120) { p.vx += dx / d * .05; p.vy += dy / d * .05; }
        p.vx *= .99; p.vy *= .99; p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H) p.vy *= -1;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7); ctx.fillStyle = `hsla(${p.h},85%,62%,.8)`; ctx.fill();
      }
      for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i], b = pts[j], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 110) { ctx.strokeStyle = `hsla(250,70%,60%,${(1 - d / 110) * .22})`; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); }
      }
      rafId = requestAnimationFrame(tick);
    };
    tick();
  }

  /* ---------- menu, header ---------- */
  const burger = $("#burger"), nav = $("#nav");
  function closeMenu() { nav.classList.remove("is-open"); burger.setAttribute("aria-expanded", "false"); }
  burger.addEventListener("click", () => { const o = nav.classList.toggle("is-open"); burger.setAttribute("aria-expanded", String(o)); });
  const header = $("#header"), bar = $(".progress");
  addEventListener("scroll", () => {
    header.classList.toggle("is-scrolled", scrollY > 10);
    const h = document.documentElement.scrollHeight - innerHeight;
    bar.style.transform = `scaleX(${h > 0 ? scrollY / h : 0})`;
  }, { passive: true });

  /* ---------- boot ---------- */
  load().then(() => { renderChrome(); route(); addEventListener("hashchange", route); })
    .catch(err => { console.error(err); main.innerHTML = `<div class="container" style="padding:80px 0"><h2>Не удалось загрузить данные</h2><p>Обновите страницу.</p></div>`; });
})();
