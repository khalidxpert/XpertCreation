/* XpertCreation digital business cards: draws a card (editor preview and public page) and styled QR codes. */
(function(){
  "use strict";
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;"); }
  function media(p){ return !p ? "" : /^(https?:|\/)/.test(p) ? p : "/media/" + p; }
  var I = {
    mobile: '<path d="M7 2h10a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/><path d="M11 18h2"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    whatsapp: '<path d="M3 21l1.6-4.7A8.5 8.5 0 1 1 7.8 19.4z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1.2-1.2-1.7-1-1 .7a4 4 0 0 1-2.5-2.5l.7-1-1-1.7z"/>',
    email: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    sms: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/><path d="M8 11h.01M12 11h.01M16 11h.01"/>',
    website: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    location: '<path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    save: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>',
    share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
    qr: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3h-3zM20 14v.01M14 20h.01M17 20h4v-3"/>',
    link: '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
    doc: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    nav: '<path d="M3 11l18-8-8 18-2-8z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    chev: '<path d="M9 6l6 6-6 6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>'
  };
  function ic(n, s){ return '<svg viewBox="0 0 24 24" width="' + (s || 20) + '" height="' + (s || 20) + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (I[n] || I.link) + '</svg>'; }
  function href(c){
    var v = c.value, d = String(v).replace(/[^\d+]/g, "");
    return c.type === "mobile" || c.type === "phone" ? "tel:" + d : c.type === "whatsapp" ? "https://wa.me/" + d.replace(/\D/g, "").replace(/^0/, "92") : c.type === "email" ? "mailto:" + v
      : c.type === "sms" ? "sms:" + d : c.type === "location" ? "https://maps.google.com/?q=" + encodeURIComponent(v) : (/^https?:/i.test(v) ? v : "https://" + v);
  }
  var FONTS = {system: "system-ui,-apple-system,'Segoe UI',Roboto,sans-serif", serif: "Georgia,'Times New Roman',serif", rounded: "'Trebuchet MS','Segoe UI',sans-serif", mono: "'Courier New',monospace"};
  var CSS = ".xcb{--p:#1B4DFF;--bg:#F4F6FB;--tx:#0D1424;font-family:var(--ff);color:var(--tx);background:var(--bg);background-size:cover;background-position:center;min-height:100%;padding-bottom:84px;position:relative}"
    + ".xcb *{box-sizing:border-box}.xcb a{color:inherit;text-decoration:none}"
    + ".xcb .hd{padding:34px 20px 22px;text-align:center;position:relative}"
    + ".xcb .ph{width:118px;height:118px;border-radius:50%;object-fit:cover;border:4px solid #fff;box-shadow:0 8px 24px rgba(0,0,0,.18);display:block;margin:0 auto 12px;background:#E5E7EB}"
    + ".xcb .lg{height:36px;max-width:150px;object-fit:contain;display:block;margin:0 auto 10px}"
    + ".xcb h1{margin:0;font-size:26px;line-height:1.2}.xcb .h2{margin-top:4px;font-weight:700;opacity:.85}.xcb .h3{font-size:14px;opacity:.75;margin-top:2px}"
    + ".xcb .bio{margin:10px auto 0;max-width:420px;font-size:14.5px;line-height:1.6;opacity:.85}"
    + ".xcb .cn{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:16px}"
    + ".xcb .cn a{width:48px;height:48px;border-radius:50%;display:grid;place-items:center;background:var(--p);color:#fff;box-shadow:0 6px 16px rgba(0,0,0,.15)}"
    + ".xcb .sec{margin:12px 14px;background:rgba(255,255,255,.94);color:#0D1424;border-radius:var(--r);padding:16px;box-shadow:0 4px 18px rgba(13,20,36,.07)}"
    + ".xcb .sec h2{margin:0 0 10px;font-size:16px;display:flex;gap:8px;align-items:center;color:var(--p)}"
    + ".xcb .row{display:flex;gap:12px;align-items:center;padding:9px 0;border-top:1px solid #EEF1F6}.xcb .row:first-of-type{border-top:0}.xcb .row small{display:block;color:#64748B;font-size:12px}"
    + ".xcb .ri{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:color-mix(in srgb,var(--p) 12%,#fff);color:var(--p);flex:0 0 38px}"
    + ".xcb .btn{display:flex;align-items:center;gap:10px;padding:12px 14px;border-radius:12px;border:1.5px solid #E4E8F2;margin-top:8px;font-weight:700}"
    + ".xcb .soc{display:flex;flex-wrap:wrap;gap:8px}.xcb .soc a{padding:9px 13px;border-radius:99px;background:color-mix(in srgb,var(--p) 10%,#fff);color:var(--p);font-weight:700;font-size:13.5px}"
    + ".xcb .gal{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.xcb .gal img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px}"
    + ".xcb .hr{display:flex;justify-content:space-between;padding:5px 0;font-size:14px;border-top:1px solid #EEF1F6}.xcb .hr:first-of-type{border-top:0}"
    + ".xcb .vid{display:block;position:relative;border-radius:12px;overflow:hidden}.xcb .vid img{width:100%;display:block}.xcb .vid span{position:absolute;inset:0;display:grid;place-items:center;font-size:44px;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.5)}"
    + ".xcb .txt{white-space:pre-wrap;line-height:1.65;font-size:14.5px;margin:0}"
    + ".xcb .sec h2.c{justify-content:center;flex-direction:column;gap:2px;font-size:24px;color:inherit;text-align:center}.xcb .sec h2 .ho{width:44px;height:44px;border-radius:50%;background:#0D1424;color:#fff;display:grid;place-items:center;flex:0 0 44px}"
    + ".xcb .sec h2.l{font-size:18px;color:inherit;border-bottom:1px solid #EEF1F6;padding-bottom:12px;gap:14px}.xcb .sub{color:#64748B;font-size:15px;text-align:center;margin:-4px 0 10px}"
    + ".xcb .ct{padding:10px 0}.xcb .ct b{display:block;font-size:17px;font-weight:600}.xcb .ct span{color:#475569;font-size:14px;white-space:pre-wrap}"
    + ".xcb .pill{display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:99px;background:#1F2937;color:#fff!important;font-size:13.5px;font-weight:600;margin-top:8px}"
    + ".xcb .lk{display:flex;align-items:center;gap:12px;padding:12px 0;border-top:1px solid #EEF1F6}.xcb .lk:first-of-type{border-top:0}.xcb .lk .li{width:44px;height:44px;border-radius:50%;border:1px solid #E4E8F2;display:grid;place-items:center;flex:0 0 44px}.xcb .lk .tt{flex:1;min-width:0}.xcb .lk .tt b{display:block;font-weight:600}.xcb .lk .tt small{color:#64748B;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
    + ".xcb .mbtn{display:block;text-align:center;padding:12px;border-radius:99px;background:var(--p);color:#fff!important;font-weight:700;margin-top:10px}"
    + ".xcb .fab{position:fixed;left:50%;transform:translateX(-50%);bottom:max(14px,env(safe-area-inset-bottom));width:min(452px,calc(100% - 20px));display:flex;gap:10px;align-items:center;z-index:20;pointer-events:none}"
    + ".xcb .fab>*{pointer-events:auto}.xcb .fab .rb{width:50px;height:50px;border-radius:50%;border:0;background:rgba(17,24,39,.88);color:#fff;display:grid;place-items:center;cursor:pointer;box-shadow:0 6px 18px rgba(0,0,0,.3)}"
    + ".xcb .fab .ac{margin-left:auto;display:flex;align-items:center;gap:10px;padding:6px 6px 6px 18px;border-radius:99px;background:rgba(17,24,39,.9);color:#fff!important;font-weight:600;font-size:13.5px;line-height:1.15;box-shadow:0 6px 18px rgba(0,0,0,.3)}.xcb .fab .ac i{width:40px;height:40px;border-radius:50%;background:#fff;color:#111;display:grid;place-items:center}"
    + ".xcb .mn{position:absolute;top:14px;right:14px;width:44px;height:44px;border-radius:50%;border:2px solid #fff;background:#0B1F4B;color:#fff;display:grid;place-items:center;cursor:pointer;z-index:6}"
    + ".xcb .mnl{position:absolute;top:64px;right:14px;background:#fff;color:#0D1424;border-radius:14px;box-shadow:0 12px 30px rgba(0,0,0,.25);padding:6px 0;z-index:7;min-width:190px}.xcb .mnl a{display:block;padding:10px 16px;font-weight:600}.xcb .mnl[hidden]{display:none}"
    + ".xcb .promo{display:flex;justify-content:center;margin:20px 0 0}.xcb .promo a{padding:12px 18px;border-radius:99px;background:rgba(100,116,139,.35);color:inherit;font-size:13.5px;text-decoration:underline}"
    + ".xcb[data-t=hero],.xcb[data-t=dark]{--bg:#050507}.xcb[data-t=hero] .hd{min-height:78vh}.xcb[data-t=hero] h1{font-size:34px}"
    + ".xcb .bar{position:sticky;bottom:12px;margin:18px 14px 0;display:flex;gap:8px;z-index:3}"
    + ".xcb .bar a,.xcb .bar button{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;padding:13px;border-radius:14px;border:0;font:inherit;font-weight:800;cursor:pointer;background:#fff;color:#0D1424;box-shadow:0 8px 22px rgba(13,20,36,.18)}"
    + ".xcb .bar .pri{background:var(--p);color:#fff;flex:2}"
    + ".xcb .ft{text-align:center;font-size:12px;opacity:.6;margin-top:18px}.xcb .ft a{text-decoration:underline}"
    /* templates */
    + ".xcb[data-t=classic] .hd{background:var(--p);color:#fff;border-radius:0 0 28px 28px;padding-bottom:28px}.xcb[data-t=classic] .cn a{background:#fff;color:var(--p)}"
    + ".xcb[data-t=hero] .hd{padding:0;text-align:left;color:#fff;min-height:360px;display:flex;flex-direction:column;justify-content:flex-end;background:linear-gradient(180deg,rgba(0,0,0,0) 30%,rgba(0,0,0,.82)),var(--hero) center/cover,var(--p)}"
    + ".xcb[data-t=hero] .hd .in{padding:20px}.xcb[data-t=hero] .ph{display:none}.xcb[data-t=hero] .lg{margin:0 0 10px}.xcb[data-t=hero] .cn{justify-content:flex-start}.xcb[data-t=hero] .cn a{background:rgba(255,255,255,.18);backdrop-filter:blur(6px)}"
    + ".xcb[data-t=minimal] .ph{border-color:var(--p)}.xcb[data-t=minimal] .sec{box-shadow:none;border:1px solid #E4E8F2}"
    + ".xcb[data-t=dark]{--bg:#0B1020;--tx:#F1F5F9}.xcb[data-t=dark] .sec{background:#141B2E;color:#E2E8F0}.xcb[data-t=dark] .row,.xcb[data-t=dark] .hr{border-color:#243049}.xcb[data-t=dark] .ri{background:#1E293B}.xcb[data-t=dark] .btn{border-color:#243049}.xcb[data-t=dark] .soc a{background:#1E293B}"
    + ".xcb[data-t=gradient] .hd{background:linear-gradient(135deg,var(--p),#7C3AED 60%,#EC4899);color:#fff;border-radius:0 0 40% 40% / 0 0 36px 36px;padding-bottom:34px}.xcb[data-t=gradient] .cn a{background:#fff;color:var(--p)}"
    + ".xcb[data-t=corporate] .hd{text-align:left;display:grid;grid-template-columns:auto 1fr;gap:4px 16px;align-items:center;background:#fff;color:#0D1424;border-bottom:5px solid var(--p)}"
    + ".xcb[data-t=corporate] .ph{width:92px;height:92px;margin:0;grid-row:span 4;border-radius:18px}.xcb[data-t=corporate] .lg{margin:0}.xcb[data-t=corporate] .cn{grid-column:1/-1;justify-content:flex-start}.xcb[data-t=corporate] .bio{grid-column:1/-1;margin:8px 0 0}";
  function injectCss(){ if (document.getElementById("xcb-css")) return; var s = document.createElement("style"); s.id = "xcb-css"; s.textContent = CSS; document.head.appendChild(s); }
  function section(s){
    var T = s.title || {about: "About me", contact: "Contact us", social: "Follow me", links: "Web links", gallery: "Gallery", hours: "Business hours", video: "Video", pdf: "Documents", meeting: "Schedule a meeting"}[s.type];
    var h = '<div class="sec" id="xs-' + (s._i || 0) + '">' + (s.type === "contact" ? '<h2 class="l"><span class="ho">' + ic("mobile", 20) + '</span>' + esc(T) + '</h2>' : '<h2 class="c">' + esc(T) + '</h2>') + (s.sub ? '<p class="sub">' + esc(s.sub) + '</p>' : '');
    if (s.type === "about") h += '<p class="txt" style="text-align:center">' + esc(s.text) + '</p>';
    if (s.type === "contact"){
      if (s.phone) h += '<a class="ct" href="tel:' + esc(String(s.phone).replace(/[^\d+]/g, "")) + '" data-lbl="phone" style="display:block"><b>Call us</b><span>' + esc(s.phone) + '</span></a>';
      if (s.email) h += '<a class="ct" href="mailto:' + esc(s.email) + '" data-lbl="email" style="display:block"><b>Email</b><span>' + esc(s.email) + '</span></a>';
      if (s.company) h += '<div class="ct"><b>Company</b><span>' + esc(s.company) + '</span></div>';
      if (s.address) h += '<div class="ct"><b>Address</b><span>' + esc(s.address) + '</span><br><a class="pill" href="https://maps.google.com/?q=' + encodeURIComponent(s.address) + '" target="_blank" rel="noopener" data-lbl="directions">' + ic("nav", 15) + 'Directions</a></div>';
    }
    if (s.type === "social") h += '<div class="soc">' + (s.items || []).map(function(i){ return '<a href="' + esc(i.url) + '" target="_blank" rel="noopener" data-lbl="' + esc(i.label || i.net) + '">' + esc(i.label || i.net || "Link") + '</a>'; }).join("") + '</div>';
    if (s.type === "links" || s.type === "pdf") h += (s.items || []).map(function(i){ var host = String(i.url).replace(/^https?:\/\//, "").split("/")[0]; return '<a class="lk" href="' + esc(i.url) + '" target="_blank" rel="noopener" data-lbl="' + esc(i.label) + '"><span class="li">' + ic(s.type === "pdf" ? "doc" : "link", 20) + '</span><span class="tt"><b>' + esc(i.label || host) + '</b><small>' + esc(host) + '</small></span>' + ic("chev", 20) + '</a>'; }).join("");
    if (s.type === "meeting"){ if (s.text) h += '<p class="txt" style="text-align:center">' + esc(s.text) + '</p>'; if (s.url) h += '<a class="mbtn" href="' + esc(s.url) + '" target="_blank" rel="noopener" data-lbl="meeting">' + esc(s.button || "Book a meeting") + '</a>'; }
    if (s.type === "gallery") h += '<div class="gal">' + (s.images || []).map(function(i){ return '<a href="' + esc(media(i)) + '" target="_blank" rel="noopener"><img src="' + esc(media(i)) + '" alt="" loading="lazy"></a>'; }).join("") + '</div>';
    if (s.type === "hours") h += (s.days || []).map(function(d){ return '<div class="hr"><b>' + esc(d.d) + '</b><span>' + (d.closed ? "Closed" : esc(d.open) + " \u2013 " + esc(d.close)) + '</span></div>'; }).join("");
    if (s.type === "video" && s.yt) h += '<a class="vid" href="https://www.youtube.com/watch?v=' + esc(s.yt) + '" target="_blank" rel="noopener" data-lbl="video"><img src="https://img.youtube.com/vi/' + esc(s.yt) + '/hqdefault.jpg" alt="" loading="lazy"><span>\u25B6</span></a>';
    return h + '</div>';
  }
  function render(el, d, o){
    injectCss(); o = o || {};
    var p = d.profile || {}, dz = d.design || {}, t = dz.template || "classic";
    el.className = "xcb"; el.setAttribute("data-t", t);
    el.style.setProperty("--p", dz.primary || "#1B4DFF");
    if (t !== "dark"){ el.style.setProperty("--bg", dz.bg || "#F4F6FB"); el.style.setProperty("--tx", dz.text || "#0D1424"); } else { el.style.removeProperty("--bg"); el.style.removeProperty("--tx"); }
    el.style.setProperty("--ff", FONTS[dz.font] || FONTS.system);
    el.style.setProperty("--r", dz.shape === "square" ? "6px" : dz.shape === "pill" ? "26px" : "18px");
    el.style.backgroundImage = dz.background ? "url('" + media(dz.background).replace(/'/g, "") + "')" : "";
    if (p.photo) el.style.setProperty("--hero", "url('" + media(p.photo).replace(/'/g, "") + "')");
    var head = (p.photo ? '<img class="ph" src="' + esc(media(p.photo)) + '" alt="">' : '') + (p.logo ? '<img class="lg" src="' + esc(media(p.logo)) + '" alt="">' : '')
      + '<h1>' + esc(p.name || "Your name") + '</h1>' + (p.heading ? '<div class="h2">' + esc(p.heading) + '</div>' : '') + (p.sub ? '<div class="h3">' + esc(p.sub) + '</div>' : '')
      + ((d.connect || []).length ? '<div class="cn">' + d.connect.map(function(c){ return '<a href="' + esc(href(c)) + '" target="_blank" rel="noopener" data-lbl="' + esc(c.type) + '" aria-label="' + esc(c.type) + '">' + ic(c.type, 22) + '</a>'; }).join("") + '</div>' : '')
      + (p.bio ? '<p class="bio">' + esc(p.bio) + '</p>' : '');
    var secs = (d.sections || []).filter(function(s){ return s.on !== false; }).map(function(s, i){ var c = JSON.parse(JSON.stringify(s)); c._i = i; return c; });
    var names = {about: "About me", contact: "Contact us", social: "Follow me", links: "Web links", gallery: "Gallery", hours: "Business hours", video: "Video", pdf: "Documents", meeting: "Schedule a meeting"};
    el.innerHTML = (secs.length ? '<button type="button" class="mn" data-xmenu aria-label="Menu">' + ic("menu", 20) + '</button><div class="mnl" hidden>' + secs.map(function(s){ return '<a href="#xs-' + s._i + '" data-xjump>' + esc(s.title || names[s.type]) + '</a>'; }).join("") + '</div>' : '')
      + '<div class="hd">' + (t === "hero" ? '<div class="in">' + head + '</div>' : head) + '</div>'
      + secs.map(section).join("")
      + '<div class="promo"><a href="https://xpertcreation.com/cards" target="_blank" rel="noopener">Get your own card for free</a></div>'
      + '<p class="ft">XpertCreation Cards' + (o.report ? ' \u00b7 <a href="#" data-xreport>Report</a>' : '') + '</p>'
      + '<div class="fab"' + (o.preview ? ' style="position:sticky;transform:none;left:0;width:auto;margin:0 10px"' : '') + '><button type="button" class="rb" data-xqr aria-label="QR code">' + ic("qr", 22) + '</button><button type="button" class="rb" data-xshare aria-label="Share">' + ic("share", 20) + '</button>'
      + '<a class="ac" href="' + esc(o.vcf || "#") + '" data-lbl="save">Add to<br>contacts<i>' + ic("plus", 22) + '</i></a></div>';
    if (!el.getAttribute("data-mn")){ el.setAttribute("data-mn", "1"); el.addEventListener("click", function(e){ var m = el.querySelector(".mnl"); if (!m) return; if (e.target.closest("[data-xmenu]")){ m.hidden = !m.hidden; } else if (e.target.closest("[data-xjump]")){ e.preventDefault(); m.hidden = true; var tg = el.querySelector(e.target.closest("[data-xjump]").getAttribute("href")); if (tg) tg.scrollIntoView({behavior: "smooth", block: "start"}); } else if (!e.target.closest(".mnl")) m.hidden = true; }); }
  }
  /* styled QR: dots square|rounded|dots, eyes square|rounded|circle, optional logo and frame text */
  function drawQR(q, st, px, logoImg){
    var n = q.getModuleCount(), m = 4, frame = st.frame ? Math.round(px * 0.16) : 0, cv = document.createElement("canvas"), cell = px / (n + m * 2);
    cv.width = px; cv.height = px + frame;
    var x = cv.getContext("2d"); x.fillStyle = st.bg || "#fff"; x.fillRect(0, 0, cv.width, cv.height); x.fillStyle = st.fg || "#000";
    function eye(r, c){ return (r < 7 && c < 7) || (r < 7 && c >= n - 7) || (r >= n - 7 && c < 7); }
    // alignment and timing patterns stay square so every phone scanner can lock on, whatever the dot style
    var AP = [[], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50], [6, 30, 54], [6, 32, 58], [6, 34, 62], [6, 26, 46, 66], [6, 26, 48, 70], [6, 26, 50, 74], [6, 30, 54, 78], [6, 30, 56, 82], [6, 30, 58, 86], [6, 34, 62, 90], [6, 28, 50, 72, 94], [6, 26, 50, 74, 98], [6, 30, 54, 78, 102], [6, 28, 54, 80, 106], [6, 32, 58, 84, 110], [6, 30, 58, 86, 114], [6, 34, 62, 90, 118], [6, 26, 50, 74, 98, 122], [6, 30, 54, 78, 102, 126], [6, 26, 52, 78, 104, 130], [6, 30, 56, 82, 108, 134], [6, 34, 60, 86, 112, 138], [6, 30, 58, 86, 114, 142], [6, 34, 62, 90, 118, 146], [6, 30, 54, 78, 102, 126, 150], [6, 24, 50, 76, 102, 128, 154], [6, 28, 54, 80, 106, 132, 158], [6, 32, 58, 84, 110, 136, 162], [6, 26, 54, 82, 110, 138, 166], [6, 30, 58, 86, 114, 142, 170]][(n - 17) / 4 - 1] || [];
    function solid(r, c){
      if (r === 6 || c === 6) return true;
      for (var i = 0; i < AP.length; i++) for (var j = 0; j < AP.length; j++){
        var ar = AP[i], acol = AP[j];
        if ((ar < 9 && acol < 9) || (ar < 9 && acol > n - 10) || (ar > n - 10 && acol < 9)) continue;
        if (Math.abs(r - ar) <= 2 && Math.abs(c - acol) <= 2) return true;
      }
      return false;
    }
    function rr(X, Y, W, H, R){ x.beginPath(); x.moveTo(X + R, Y); x.arcTo(X + W, Y, X + W, Y + H, R); x.arcTo(X + W, Y + H, X, Y + H, R); x.arcTo(X, Y + H, X, Y, R); x.arcTo(X, Y, X + W, Y, R); x.closePath(); }
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++){
      if (!q.isDark(r, c) || eye(r, c)) continue;
      var X = (c + m) * cell, Y = (r + m) * cell;
      if (st.dots === "dots" && !solid(r, c)){ x.beginPath(); x.arc(X + cell / 2, Y + cell / 2, cell * 0.5, 0, 6.3); x.fill(); }
      else if (st.dots === "rounded" && !solid(r, c)){ rr(X, Y, cell, cell, cell * 0.3); x.fill(); }
      else x.fillRect(Math.floor(X), Math.floor(Y), Math.ceil(cell) + 1, Math.ceil(cell) + 1);
    }
    [[0, 0], [0, n - 7], [n - 7, 0]].forEach(function(e){
      var X = (e[1] + m) * cell, Y = (e[0] + m) * cell, s = 7 * cell;
      x.fillStyle = st.fg || "#000";
      if (st.eyes === "circle"){ x.beginPath(); x.arc(X + s / 2, Y + s / 2, s / 2, 0, 6.3); x.fill(); x.fillStyle = st.bg || "#fff"; x.beginPath(); x.arc(X + s / 2, Y + s / 2, s / 2 - cell, 0, 6.3); x.fill(); x.fillStyle = st.fg || "#000"; x.beginPath(); x.arc(X + s / 2, Y + s / 2, cell * 1.5, 0, 6.3); x.fill(); }
      else { var R = st.eyes === "rounded" ? cell * 2 : 0; rr(X, Y, s, s, R); x.fill(); x.fillStyle = st.bg || "#fff"; rr(X + cell, Y + cell, s - 2 * cell, s - 2 * cell, R * 0.6); x.fill(); x.fillStyle = st.fg || "#000"; rr(X + 2 * cell, Y + 2 * cell, 3 * cell, 3 * cell, R * 0.5); x.fill(); }
    });
    if (logoImg && logoImg.complete && logoImg.naturalWidth){
      var L = px * 0.22, lx = (px - L) / 2; x.fillStyle = st.bg || "#fff"; rr(lx - 6, lx - 6, L + 12, L + 12, 12); x.fill();
      var k = Math.min(L / logoImg.naturalWidth, L / logoImg.naturalHeight), w = logoImg.naturalWidth * k, h = logoImg.naturalHeight * k;
      x.drawImage(logoImg, (px - w) / 2, (px - h) / 2, w, h);
    }
    if (frame){ x.fillStyle = st.fg || "#000"; rr(px * 0.12, px + frame * 0.1, px * 0.76, frame * 0.72, frame * 0.36); x.fill(); x.fillStyle = st.bg || "#fff"; x.font = "800 " + Math.round(frame * 0.36) + "px system-ui,sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText(st.frame, px / 2, px + frame * 0.46); }
    return cv;
  }
  function qr(text, st, px, logoUrl, cb){
    function go(){
      var q = qrcode(0, st.logo ? "H" : "M"); q.addData(text, "Byte"); q.make();
      if (st.logo && logoUrl){ var im = new Image(); im.onload = function(){ cb(drawQR(q, st, px, im)); }; im.onerror = function(){ cb(drawQR(q, st, px, null)); }; im.src = logoUrl; }
      else cb(drawQR(q, st, px, null));
    }
    if (window.qrcode) go(); else { var s = document.createElement("script"); s.src = "/js/qrgen-1.js?v=1"; s.onload = go; document.head.appendChild(s); }
  }
  window.XCCard = {render: render, qr: qr, media: media, esc: esc, icon: ic};
})();
