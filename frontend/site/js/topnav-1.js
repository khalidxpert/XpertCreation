/* One menu for every page with the small header. Change the links here, and every page follows. */
(function(){
  "use strict";
  var head = document.querySelector("header.top") || document.querySelector("header.topbar");
  if (!head || head.querySelector(".tmenu")) return;
  var isHome = head.classList.contains("topbar");      // the home page has its own links; add only the menu button
  var LINKS = [["Home", "/"], ["XpertConnect", "/feed"], ["Clips", "/clips"], ["Chat rooms", "/chat-rooms"], ["Academy", "/academy/"], ["Vocabulary", "/vocabulary"], ["MCQs", "/mcq"], ["Islamic", "/islamic"], ["Tools", "/tools"], ["Translate", "/translate"], ["Jobs", "/jobs"], ["Freelance", "/market"], ["Store", "/store"], ["Gov jobs", "/board"], ["Pets", "/pets"],
               ["Shows", "/shows"], ["Kids", "/kids"], ["News", "/news"], ["Sports", "/sports"], ["Predict", "/predict"], ["Rates", "/rates"], ["Recipes", "/recipes"], ["Poetry", "/poetry"], ["Afsanay", "/afsanay"], ["Library", "/library"], ["Bills", "/bills"], ["Travel", "/travel"], ["Games", "/games"], ["Chat", "/chat"], ["Groups", "/groups"], ["\uD83E\uDD16 Assistant", "/assistant"], ["Guide", "/docs"]];
  var path = location.pathname.replace(/\/+$/, "") || "/";
  try { if (/[?&]guest=1/.test(location.search)) sessionStorage.setItem("xc_guest", "1"); } catch (e) {}
  function here(u){
    var b = u.replace(/\/+$/, "") || "/";
    if (b === "/") return path === "/";
    if (b === "/people") return path === "/people" || path.indexOf("/in/") === 0 || path === "/me/profile";
    if (b === "/pets") return path === "/pets" || path === "/lost" || path.indexOf("/pet/") === 0;
    if (b === "/feed") return path === "/feed" || path.indexOf("/post/") === 0 || path === "/people" || path.indexOf("/in/") === 0 || path === "/me/profile";
    if (b === "/jobs") return path === "/jobs" || path.indexOf("/jobs/") === 0 || path.indexOf("/job/") === 0;
    if (b === "/shows") return path === "/shows" || path.indexOf("/show/") === 0;
    return path === b || path.indexOf(b + "/") === 0;
  }
  var css = document.createElement("style");
  css.textContent =
    ".tnav{display:flex;gap:2px;align-items:center;margin-left:10px;min-width:0;overflow-x:auto;scrollbar-width:none}" +
    ".tnav::-webkit-scrollbar{display:none}" +
    ".tnav a{padding:7px 10px;border-radius:9px;font-size:14px;font-weight:600;text-decoration:none;color:var(--ink-soft,#5A657C);white-space:nowrap}" +
    ".tnav a:hover{background:var(--paper,#F6F7FB);color:var(--ink,#0D1424)}" +
    ".tnav a.on{color:var(--brand,#1B4DFF);background:rgba(27,77,255,.08)}" +
    ".tmenu{display:none;border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);border-radius:10px;" +
      "width:38px;height:38px;font-size:18px;cursor:pointer;color:var(--ink,#0D1424)}" +
    ".tdrop{display:none;position:absolute;left:10px;right:10px;top:calc(100% + 6px);background:var(--card,#fff);" +
      "border:1px solid var(--line,#E4E8F2);border-radius:14px;box-shadow:0 14px 34px rgba(13,20,36,.16);padding:6px;z-index:80}" +
    ".tdrop.open{display:grid;grid-template-columns:1fr 1fr;gap:4px}" +
    ".tdrop a{padding:11px 12px;border-radius:10px;text-decoration:none;font-weight:600;color:var(--ink,#0D1424)}" +
    ".tdrop a.on{background:rgba(27,77,255,.08);color:var(--brand,#1B4DFF)}" +
    "@media(max-width:820px){.tnav,header.topbar .xnav{display:none}.tmenu{display:inline-grid;place-items:center}}" +
    ".tacct{margin-left:6px;display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:10px;background:var(--brand,#1B4DFF);color:#fff;font-weight:700;font-size:14px;text-decoration:none;white-space:nowrap;flex:0 0 auto}" +
    ".tacct .tic{margin:0;stroke:#fff}" +
    ".tacct.me{padding:0;width:36px;height:36px;border-radius:50%;overflow:hidden;justify-content:center;background:#EEF2FF;color:var(--brand,#1B4DFF);border:0;box-shadow:0 0 0 2px #fff,0 0 0 3px var(--line,#E4E8F2)}" +
    ".tacct.me img{width:100%;height:100%;object-fit:cover;display:block}" +
    ".tamenu{display:none;position:absolute;right:10px;top:calc(100% + 6px);min-width:200px;background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:14px;box-shadow:0 14px 34px rgba(13,20,36,.16);padding:6px;z-index:81}" +
    ".tamenu.open{display:block}.tamenu b{display:block;padding:8px 12px 6px;font-size:13px;color:var(--ink-soft,#5A657C)}.tamenu b small{font-weight:600}" +
    ".tamenu a,.tamenu button{display:block;width:100%;text-align:left;padding:10px 12px;border-radius:10px;border:0;background:none;font:inherit;font-weight:600;color:var(--ink,#0D1424);text-decoration:none;cursor:pointer}" +
    ".tamenu a:hover,.tamenu button:hover{background:var(--paper,#F6F7FB)}.tamenu .tout{color:#B91C1C;font-weight:800}" +
    ".tmore{display:none}" +
    "@media(max-width:600px){.tacct .tlbl{display:none}.tacct{padding:8px}header.topbar .gear[href='/'],header.topbar #gearBtn{display:none}" +
      "header.topbar{gap:6px}.tdrop.open .tmore{display:block;grid-column:1/-1;border-top:1px solid var(--line,#E4E8F2);margin-top:4px;padding-top:6px}" +
      ".tmore a{display:block;padding:11px 12px;border-radius:10px;text-decoration:none;font-weight:600;color:var(--ink,#0D1424)}.tmore select{width:100%;margin-top:4px;padding:9px;border-radius:10px}}";
  document.head.appendChild(css);
  css.textContent += ".tnav a.thi,.tdrop a.thi{background:var(--brand,#1B4DFF);color:#fff!important}.tnav a.thi:hover{background:#1640D6}.tnav a.thi .tic,.tdrop a.thi .tic{stroke:#fff}";
  css.textContent += ".tic{width:16px;height:16px;flex:0 0 16px;vertical-align:-3px;margin-right:6px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}" +
    ".tnav a,.tdrop a{display:inline-flex;align-items:center}";
  if (getComputedStyle(head).position === "static") head.style.position = "relative";
  // One set of drawn icons, so the menu looks the same on Android, iPhone and Windows.
  var IC = {
    "/rates": '<circle cx="12" cy="12" r="9"/><path d="M14.5 9.5A2.5 2.5 0 0 0 12 8c-1.4 0-2.5.8-2.5 2s1.1 1.6 2.5 1.9 2.5.8 2.5 2.1-1.1 2-2.5 2a2.5 2.5 0 0 1-2.5-1.5M12 6.5V8M12 16v1.5"/>',
    "/mcq": '<path d="M10 6h10M10 12h10M10 18h10"/><path d="M4 6l1.2 1.2L7.5 5M4 12l1.2 1.2L7.5 11M4 18l1.2 1.2L7.5 17"/>',
    "/board": '<path d="M4 10v4h3l6 4V6L7 10H4z"/><path d="M16.5 9.5a3.5 3.5 0 0 1 0 5M19 7a7 7 0 0 1 0 10"/>',
    "/islamic": '<path d="M19.5 14.5A8 8 0 1 1 9.5 4.5a6.2 6.2 0 0 0 10 10z"/>',
    "/recipes": '<path d="M4 11h16a8 8 0 0 1-16 0z"/><path d="M8.5 7.5c0-1 1-1 1-2.5M12 7.5c0-1 1-1 1-2.5M15.5 7.5c0-1 1-1 1-2.5"/>',
    "/poetry": '<path d="M20 4C13 4 8 9 8 16v4"/><path d="M8 16c4.5 0 9-3 10.5-9"/>',
    "/predict": '<circle cx="12" cy="12" r="8"/><path d="M8.5 6.5c2 1.5 2 9.5 0 11M15.5 6.5c-2 1.5-2 9.5 0 11"/>',
    "/bills": '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
    "/travel": '<rect x="5" y="3" width="14" height="14" rx="3"/><path d="M5 11h14M8 21l2-4M16 21l-2-4"/><circle cx="9" cy="14" r=".5"/><circle cx="15" cy="14" r=".5"/>',
    "/kids": '<circle cx="12" cy="8" r="3.5"/><path d="M6 20c.5-3.5 3-5.5 6-5.5s5.5 2 6 5.5"/><path d="M4 5l1.5 1.5M20 5l-1.5 1.5"/>',
    "/news": '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    "/afsanay": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/>',
    "/library": '<path d="M4 5c2-1 5-1 8 1v14c-3-2-6-2-8-1z"/><path d="M20 5c-2-1-5-1-8 1v14c3-2 6-2 8-1z"/>',
    "/clips": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 9l5 3-5 3z"/>',
    "/translate": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    "/chat-rooms": '<path d="M4 5h16v10H9l-5 4z"/><path d="M8 9h8M8 12h5"/>',
    "/sports": '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3a3 3 0 0 1-3 4M7 5H4a3 3 0 0 0 3 4"/>',
    "/": '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    "/academy/": '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"/>',
    "/tools": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    "/people": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><path d="M16 5a3 3 0 0 1 0 6"/><path d="M17 15c2 .5 4 2 4 5"/>',
    "/feed": '<image href="/brand/xpertconnect/xc-icon-64.png?v=3" x="0" y="0" width="24" height="24"/>',
    "/store": '<path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/>',
    "/market": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    "/jobs": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M3 12h18"/>',
    "/pets": '<circle cx="7" cy="9" r="1.6"/><circle cx="12" cy="6" r="1.6"/><circle cx="17" cy="9" r="1.6"/><path d="M12 12c-3 0-5 3-5 5 0 1.5 1 2.5 2.5 2.5 1 0 1.7-.5 2.5-.5s1.5.5 2.5.5c1.5 0 2.5-1 2.5-2.5 0-2-2-5-5-5z"/>',
    "/shows": '<rect x="3" y="5" width="18" height="13" rx="2"/><path d="M10 9l5 2.5-5 2.5z"/><path d="M8 21h8"/>',
    "/games": '<rect x="2" y="8" width="20" height="10" rx="5"/><path d="M7 11v4M5 13h4"/><path d="M15.5 12h.01M17.5 14h.01"/>',
    "/chat": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    "/assistant": '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4"/><path d="M9.5 13h.01M14.5 13h.01"/><path d="M9.5 16.5h5"/>',
    "/docs": '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>'
  };
  function icon(href){ return '<svg class="tic" viewBox="0 0 24 24" aria-hidden="true">' + (IC[href] || '<circle cx="12" cy="12" r="3"/>') + '</svg>'; }
  var links = LINKS.map(function(l){
    var cl = ((l[1] === "/feed" ? "thi " : "") + (here(l[1]) ? "on" : "")).trim();
    return "<a href='" + l[1] + "'" + (cl ? " class='" + cl + "'" : "") + (here(l[1]) ? " aria-current='page'" : "") + ">" + icon(l[1]) + l[0].replace(/^[^A-Za-z]+/, "") + "</a>";
  }).join("");
  var nav = document.createElement("nav");
  nav.className = "tnav";
  nav.setAttribute("aria-label", "Main");
  nav.innerHTML = links;
  var btn = document.createElement("button");
  btn.type = "button";
  btn.className = "tmenu";
  btn.setAttribute("aria-label", "Menu");
  btn.innerHTML = "&#9776;";
  var drop = document.createElement("div");
  drop.className = "tdrop";
  drop.innerHTML = links;
  var sp = head.querySelector(".sp");
  if (isHome){
    // The home page now shows the same menu as every other page: its own short link row is replaced.
    var xn = head.querySelector(".xnav"), g = head.querySelector(".gear");
    if (xn){ head.insertBefore(nav, xn); xn.remove(); } else if (g) head.insertBefore(nav, g); else head.appendChild(nav);
    if (g) head.insertBefore(btn, g); else head.appendChild(btn);
  }
  else if (sp){ head.insertBefore(nav, sp); head.insertBefore(btn, sp); } else { head.appendChild(nav); head.appendChild(btn); }
  head.appendChild(drop);
  btn.onclick = function(e){ e.stopPropagation(); drop.classList.toggle("open"); };
  // Account icon - the same on every page. Signed out: a sign-in icon. Signed in: your photo; tap it for
  // Sign out, My profile, Settings. The home page's old sign-in button is hidden so there is only one.
  (function(){
    var old = head.querySelector("#sessBtn"); if (old) old.style.display = "none";
    var IN = '<svg class="tic" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/></svg>';
    var acct = document.createElement("a"); acct.className = "tacct"; acct.href = "/login"; acct.setAttribute("aria-label", "Sign in");
    acct.innerHTML = IN + '<span class="tlbl">Sign in</span>';
    head.insertBefore(acct, drop);
    var menu = document.createElement("div"); menu.className = "tamenu"; head.appendChild(menu);
    function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
    fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(u){
      if (!u || !u.email){                                          // signed out: the sign-in icon stays
        // In the installed app, the home page opens on Sign in (once per visit; "Continue as guest" skips it).
        try {
          var inApp = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || /[?&]src=app/.test(location.search);
          if (inApp && path === "/" && sessionStorage.getItem("xc_guest") !== "1") location.replace("/login");
        } catch (e) {}
        return;
      }
      // In the installed app, the first screen of a visit is XpertConnect; after that Home works normally.
      try {
        var inApp2 = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || /[?&]src=app/.test(location.search);
        var first = sessionStorage.getItem("xc_opened") !== "1"; sessionStorage.setItem("xc_opened", "1");
        if (inApp2 && first && path === "/"){ location.replace("/feed"); return; }
      } catch (e) {}
      var nm = u.full_name || u.email, pic = u.avatar_url || "";
      acct.className = "tacct me"; acct.href = "/account"; acct.setAttribute("aria-label", "My account");
      acct.innerHTML = pic ? '<img src="' + String(pic).replace(/"/g, "") + '" alt="">' : '<span>' + nm.charAt(0).toUpperCase() + '</span>';
      menu.innerHTML = '<b>' + nm.replace(/</g, "&lt;") + (u.username ? ' <small>@' + String(u.username).replace(/</g, "") + '</small>' : '') + '</b>'
        + '<a href="/feed?user=' + u.id + '">\uD83E\uDDF1 My wall</a><a href="/company/manage">\uD83C\uDFE2 My company</a><a href="/get-verified">\u2714\uFE0F Blue tick</a><a href="/me/preferences">\u2699\uFE0F Interests &amp; privacy</a><a href="/whats-new">\u2728 What\u2019s new</a><button type="button" class="tout">\uD83D\uDEAA Sign out</button><a href="/me/profile">My profile</a><a href="/account">Settings</a>';
      acct.addEventListener("click", function(e){ e.preventDefault(); e.stopPropagation(); drop.classList.remove("open"); menu.classList.toggle("open"); });
      menu.querySelector(".tout").onclick = function(){
        fetch("/api/auth/logout/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}})
          .then(function(){ try { sessionStorage.clear(); } catch (e) {} location.href = "/"; });
      };
    }).catch(function(){});
    document.addEventListener("click", function(e){ if (!menu.contains(e.target)) menu.classList.remove("open"); });
    // Phones: Settings and the language box move into the menu so the header fits.
    var extra = document.createElement("div"); extra.className = "tmore";
    extra.innerHTML = '<a href="/account">\u2699\uFE0F Settings</a>';
    var lang = head.querySelector("#langSel");
    drop.appendChild(extra);
    var mq = window.matchMedia ? window.matchMedia("(max-width:600px)") : null;
    var spot = lang ? document.createComment("lang") : null;
    if (lang) lang.parentNode.insertBefore(spot, lang);
    function place(){ if (!lang) return; if (mq && mq.matches){ if (lang.parentNode !== extra) extra.appendChild(lang); } else if (lang.parentNode !== head) spot.parentNode.insertBefore(lang, spot); }
    place(); if (mq && mq.addEventListener) mq.addEventListener("change", place);
  })();

  // "System log" - only for the super admin. The server decides; the answer is remembered for this visit.
  function addAdmin(){
    var link = '<a href="/system-log"' + (path === "/system-log" ? ' class="on"' : '') + '>\uD83D\uDEE1 System log</a>';
    link += '<a href="/broadcast"' + (path === "/broadcast" ? ' class="on"' : '') + '>\uD83D\uDCE2 Broadcast</a>';
    [head.querySelector(".tnav"), head.querySelector(".xnav"), drop].forEach(function(el){
      if (el && !el.querySelector('a[href="/system-log"]')) el.insertAdjacentHTML("beforeend", link);
    });
  }
  // "Moderation" in the menu - only for moderators (the same role check the home page used).
  function addMod(){
    var link = '<a href="/moderate"' + (path === "/moderate" ? ' class="on"' : '') + '>\uD83D\uDEE1\uFE0F Moderation</a>'
      + '<a href="/company-review"' + (path === "/company-review" ? ' class="on"' : '') + '>\uD83C\uDFE2 Company KYC</a>';
    [head.querySelector(".tnav"), drop].forEach(function(el){ if (el && !el.querySelector('a[href="/moderate"]')) el.insertAdjacentHTML("beforeend", link); });
  }
  var modK = null;
  try { modK = sessionStorage.getItem("xc_mod"); } catch (e) {}
  if (modK === "1") addMod();
  else if (modK !== "0") fetch("/api/auth/role/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
    var yes = !!(d && d.moderator);
    try { sessionStorage.setItem("xc_mod", yes ? "1" : "0"); } catch (e) {}
    if (yes) addMod();
  }).catch(function(){});
  var sup = null;
  try { sup = sessionStorage.getItem("xc_super"); } catch (e) {}
  if (sup === "1") addAdmin();
  else fetch("/api/auditlog/events/?from=2000-01-01&to=2000-01-01", {credentials: "same-origin"}).then(function(r){
    if (!r.ok) return;
    try { sessionStorage.setItem("xc_super", "1"); } catch (e) {}
    addAdmin();
  }).catch(function(){});
  document.addEventListener("click", function(e){ if (!drop.contains(e.target)) drop.classList.remove("open"); });  // Unread chat messages as a badge on "Chat", for signed-in members. Checked every minute.
  function chatBadge(){
    if (document.hidden) return;
    fetch("/api/notify/threads/unread/", {credentials: "same-origin"})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){
        var n = d && d.unread ? d.unread : 0;
        [].forEach.call(document.querySelectorAll(".tnav a[href='/chat'], .tdrop a[href='/chat']"), function(a){
          var b = a.querySelector(".tbadge");
          if (!n){ if (b) b.remove(); return; }
          if (!b){ b = document.createElement("span"); b.className = "tbadge"; a.appendChild(b); }
          b.textContent = n > 99 ? "99+" : String(n);
        });
      }).catch(function(){});
  }
  css.textContent += ".tbadge{display:inline-block;min-width:18px;height:18px;padding:0 5px;margin-left:5px;border-radius:99px;" +
    "background:#DC2626;color:#fff;font-size:11px;font-weight:800;line-height:18px;text-align:center;vertical-align:1px}";
  setTimeout(chatBadge, 800);
  setInterval(chatBadge, 60000);
})();

/* xcNavArrows: small arrows when the menu row is longer than the screen */
(function(){
  function setup(){
    var n = document.querySelector(".tnav"); if (!n || n.getAttribute("data-arr")) return !!n;
    n.setAttribute("data-arr", "1");
    var st = document.createElement("style");
    st.textContent = ".xcna{flex:0 0 auto;width:28px;height:28px;border-radius:50%;border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);color:var(--ink,#0D1424);font-size:18px;line-height:1;cursor:pointer;display:none;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(13,20,36,.12);padding:0}"
      + ".xcna.on{display:flex}@media(max-width:820px){.xcna{display:none!important}}";
    document.head.appendChild(st);
    function mk(t, d){ var b = document.createElement("button"); b.type = "button"; b.className = "xcna"; b.textContent = t; b.setAttribute("aria-label", d < 0 ? "Scroll menu left" : "Scroll menu right");
      b.addEventListener("click", function(){ n.scrollBy({left: d * Math.max(200, n.clientWidth * 0.6), behavior: "smooth"}); }); return b; }
    var l = mk("\u2039", -1), r = mk("\u203A", 1);
    n.parentNode.insertBefore(l, n); n.parentNode.insertBefore(r, n.nextSibling);
    function upd(){ l.classList.toggle("on", n.scrollLeft > 4); r.classList.toggle("on", n.scrollLeft + n.clientWidth < n.scrollWidth - 4); }
    n.addEventListener("scroll", upd, {passive: true}); window.addEventListener("resize", upd); setTimeout(upd, 50); setTimeout(upd, 600);
    var on = n.querySelector(".on, [aria-current], .thi"); if (on && on.offsetLeft + on.offsetWidth > n.clientWidth) n.scrollLeft = on.offsetLeft - 40;
    return true;
  }
  if (!setup()){ var mo = new MutationObserver(function(){ if (setup()) mo.disconnect(); }); mo.observe(document.documentElement, {childList: true, subtree: true}); }
})();
/* Share on XpertConnect, next to every WhatsApp share button */
(function(){ if (document.querySelector("script[src*='xcshare-1.js']")) return; var s = document.createElement("script"); s.src = "/js/xcshare-1.js?v=3"; s.defer = true; document.head.appendChild(s); })();

/* XpertCreation rewards: active time, tools and reading. Counts only while this tab is visible and was used
   in the last minute, once a minute. Stops by itself for guests or when the campaign is off. */
(function(){
  if (window.XCRW) return; window.XCRW = 1;
  var last = 0, sent = {};
  function mark(){ last = Date.now(); }
  ["scroll", "click", "keydown", "touchstart", "mousemove"].forEach(function(e){ window.addEventListener(e, mark, {passive: true}); });
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  var TOOLS = /^\/(tools\/[a-z0-9-]+|weather|translate|rates|bills|travel|air|bus|money|business|cards|zodiac|typing|vocabulary)$/;
  var READ = /^\/(library|afsanay|quran|recipes|poetry)\/./;
  function section(){
    var p = location.pathname.replace(/\/+$/, "");
    if (TOOLS.test(p)) return "tool:" + p.slice(1);
    if (READ.test(p)) return "read:" + p.slice(1);
    return "";
  }
  var t;
  function beat(){
    if (document.visibilityState !== "visible" || Date.now() - last > 60000) return;
    var s = section(), body = {s: ""};
    if (s && !sent[s]){ body.s = s; sent[s] = 1; }
    fetch("/api/rewards/beat/", {method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify(body)})
      .then(function(r){ if (r.status === 401 || r.status === 403 || r.status === 404) clearInterval(t); })
      .catch(function(){});
  }
  t = setInterval(beat, 60000);
})();

/* xcCartIcon: the Store cart in the header on every page, for everyone. The cart is kept on this phone. */
(function(){
  if (window.XCCART) return; window.XCCART = 1;
  function put(){
    var head = document.querySelector("header.top") || document.querySelector("header.topbar");
    if (!head || head.querySelector(".tcart")) return !!head;
    var st = document.createElement("style");
    st.textContent = ".tcart{position:relative;flex:0 0 auto;width:36px;height:36px;margin-left:6px;border-radius:11px;display:inline-grid;place-items:center;background:#FFF4ED;border:1px solid #FED7C3;color:#F85606;text-decoration:none}"
      + ".tcart:hover{background:#FFE8DA}.tcart svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}"
      + ".tcart b{position:absolute;top:-6px;right:-6px;min-width:18px;height:18px;padding:0 4px;border-radius:99px;background:#DC2626;color:#fff;font-size:10.5px;font-weight:800;line-height:18px;text-align:center;box-shadow:0 0 0 2px #fff}"
      + "@media(max-width:600px){.tcart{width:34px;height:34px;margin-left:4px}}";
    document.head.appendChild(st);
    var a = document.createElement("a"); a.className = "tcart"; a.href = "/store#cart"; a.setAttribute("aria-label", "Shopping cart"); a.title = "Shopping cart";
    a.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/></svg><b hidden></b>';
    var acct = head.querySelector(".tacct"), drop = head.querySelector(".tdrop");
    if (acct) head.insertBefore(a, acct); else if (drop) head.insertBefore(a, drop); else head.appendChild(a);
    function count(){
      var n = 0; try { (JSON.parse(localStorage.getItem("xc_store_cart") || "[]") || []).forEach(function(x){ n += +x.qty || 0; }); } catch (e) {}
      var b = a.querySelector("b"); b.hidden = !n; b.textContent = n > 99 ? "99+" : String(n);
      a.setAttribute("aria-label", n ? "Shopping cart, " + n + " items" : "Shopping cart");
    }
    count();
    window.addEventListener("storage", function(e){ if (!e.key || e.key === "xc_store_cart") count(); });
    window.addEventListener("xc-cart", count); window.addEventListener("pageshow", count);
    document.addEventListener("visibilitychange", function(){ if (!document.hidden) count(); });
    return true;
  }
  if (!put()) document.addEventListener("DOMContentLoaded", put);
})();
