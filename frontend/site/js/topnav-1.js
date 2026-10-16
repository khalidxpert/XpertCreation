/* One menu for every page with the small header. Change the links here, and every page follows. */
(function(){
  "use strict";
  var head = document.querySelector("header.top") || document.querySelector("header.topbar");
  if (!head || head.querySelector(".tmenu")) return;
  var isHome = head.classList.contains("topbar");      // the home page has its own links; add only the menu button
  var LINKS = [["Home", "/"], ["XpertConnect", "/feed"], ["Clips", "/clips"], ["Chat rooms", "/chat-rooms"], ["Meetups", "/meetups"], ["Nearby chat", "/nearby"], ["Academy", "/academy/"], ["Vocabulary", "/vocabulary"], ["MCQs", "/mcq"], ["Islamic", "/islamic"], ["Tools", "/tools"], ["Translate", "/translate"], ["Jobs", "/jobs"], ["Freelance", "/market"], ["Store", "/store"], ["Rides", "/rides"], ["Roots of Love", "/roots"], ["Gov jobs", "/board"], ["Pets", "/pets"], ["Help", "/help"],
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
    "/meetups": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><circle cx="12" cy="15.5" r="2"/>',
    "/nearby": '<path d="M2 8.5a15 15 0 0 1 20 0"/><path d="M5 12a10 10 0 0 1 14 0"/><path d="M8.5 15.5a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1"/>',
    "/sports": '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3a3 3 0 0 1-3 4M7 5H4a3 3 0 0 0 3 4"/>',
    "/": '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    "/academy/": '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"/>',
    "/tools": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    "/people": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><path d="M16 5a3 3 0 0 1 0 6"/><path d="M17 15c2 .5 4 2 4 5"/>',
    "/feed": '<image href="/brand/xpertconnect/xc-icon-64.png?v=3" x="0" y="0" width="24" height="24"/>',
    "/roots": '<path d="M12 21v-7"/><path d="M12 14l-3-3M12 14l3-2.5"/><circle cx="12" cy="7.5" r="4.5"/><path d="M7 21h10"/>',
    "/rides": '<path d="M5 16h14l-1.5-5.2A2 2 0 0 0 15.6 9H8.4a2 2 0 0 0-1.9 1.8L5 16z"/><circle cx="8" cy="17.5" r="1.6"/><circle cx="16" cy="17.5" r="1.6"/><path d="M12 3.5a2 2 0 1 1 0 .01"/>',
    "/store": '<path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/>',
    "/market": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    "/jobs": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M3 12h18"/>',
    "/help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6"/><path d="M12 17h.01"/>',
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
  else if (sp){ sp.parentNode.insertBefore(nav, sp); sp.parentNode.insertBefore(btn, sp); } else { head.appendChild(nav); head.appendChild(btn); }
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
        + '<a href="/feed?user=' + u.id + '">\uD83E\uDDF1 My wall</a><a href="/company/manage">\uD83C\uDFE2 My company</a><a href="/get-verified">\u2714\uFE0F Blue tick</a><a href="/settings">\u2699\uFE0F Settings &amp; privacy</a><a href="/me/preferences">\uD83C\uDFAF Interests</a><a href="/saved">\uD83D\uDD16 Saved posts</a><a href="/whats-new">\u2728 What\u2019s new</a><button type="button" class="tout">\uD83D\uDEAA Sign out</button><a href="/me/profile">My profile</a><a href="/account">Settings</a>';
      acct.addEventListener("click", function(e){ e.preventDefault(); e.stopPropagation(); drop.classList.remove("open"); menu.classList.toggle("open"); });
      menu.querySelector(".tout").onclick = function(){
        fetch("/api/auth/logout/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}})
          .then(function(){ try { sessionStorage.clear(); } catch (e) {} location.href = "/"; });
      };
    }).catch(function(){});
    document.addEventListener("click", function(e){ if (!menu.contains(e.target)) menu.classList.remove("open"); });
    // Phones: Settings and the language box move into the menu so the header fits.
    var extra = document.createElement("div"); extra.className = "tmore";
    extra.innerHTML = '<a href="/settings">\u2699\uFE0F Settings</a>';
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

/* xcPushPrompt: phone / desktop notifications for every signed-in member, on every page.
   Asks once (a small card, "Not now" hides it for 5 days); if allowed before, makes sure this device is subscribed. */
(function(){
  if (window.XCPUSH) return; window.XCPUSH = 1;
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return;
  if (location.pathname.replace(/\/+$/, "") === "/account") return;            // the Account page has its own switch
  var KEY = "xc_push_later";
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function b64(s){ var pad = "=".repeat((4 - s.length % 4) % 4), raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/")), out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i); return out; }
  function reg(){ return navigator.serviceWorker.register("/sw.js").then(function(){ return navigator.serviceWorker.ready; }); }
  function subscribe(){
    return fetch("/api/notify/push/key/").then(function(r){ return r.json(); }).then(function(k){
      if (!k.key) throw new Error("no key");
      return reg().then(function(r){ return r.pushManager.getSubscription().then(function(s){ return s || r.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: b64(k.key)}); }); });
    }).then(function(sub){
      return fetch("/api/notify/push/subscribe/", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify(sub.toJSON())});
    });
  }
  function later(){ try { return Date.now() < +(localStorage.getItem(KEY) || 0); } catch (e){ return false; } }
  function card(){
    var st = document.createElement("style");
    st.textContent = ".xcpp{position:fixed;left:12px;right:12px;bottom:86px;max-width:440px;margin:0 auto;z-index:9000;background:#0D1424;color:#fff;border-radius:18px;padding:14px 16px;box-shadow:0 18px 44px rgba(13,20,36,.35);display:flex;gap:12px;align-items:flex-start;font-family:inherit;animation:xcppin .35s ease-out}"
      + "@keyframes xcppin{from{transform:translateY(30px);opacity:0}to{transform:none;opacity:1}}"
      + ".xcpp i{font-style:normal;font-size:26px;line-height:1}.xcpp b{display:block;font-size:15px;margin-bottom:3px}.xcpp p{margin:0;font-size:13px;opacity:.85;line-height:1.45}"
      + ".xcpp .bt{display:flex;gap:8px;margin-top:10px}.xcpp button{border:0;border-radius:11px;padding:9px 14px;font:inherit;font-weight:800;font-size:13.5px;cursor:pointer}"
      + ".xcpp .on{background:#1B4DFF;color:#fff}.xcpp .no{background:rgba(255,255,255,.12);color:#fff}";
    document.head.appendChild(st);
    var c = document.createElement("div"); c.className = "xcpp"; c.setAttribute("role", "dialog");
    c.innerHTML = '<i>🔔</i><div><b>Turn on notifications?</b><p>Hear about new offers, orders, messages and connection requests on this phone, even when XpertCreation is closed.</p>'
      + '<div class="bt"><button class="on">Turn on</button><button class="no">Not now</button></div></div>';
    document.body.appendChild(c);
    c.querySelector(".no").onclick = function(){ try { localStorage.setItem(KEY, String(Date.now() + 5 * 864e5)); } catch (e){} c.remove(); };
    c.querySelector(".on").onclick = function(){
      var b = this; b.disabled = true; b.textContent = "…";
      Notification.requestPermission().then(function(p){
        if (p !== "granted"){ c.remove(); return; }
        return subscribe().then(function(){ c.innerHTML = '<i>✅</i><div><b>Notifications are on</b><p>You can turn them off any time in Account.</p></div>'; setTimeout(function(){ c.remove(); }, 3500); });
      }).catch(function(){ c.remove(); });
    };
  }
  fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(u){
    if (!u || !u.email) return;
    if (Notification.permission === "granted"){
      var once = false; try { once = sessionStorage.getItem("xc_push_sync") === "1"; sessionStorage.setItem("xc_push_sync", "1"); } catch (e){}
      if (!once) subscribe().catch(function(){});                                // re-register this device quietly
      return;
    }
    if (Notification.permission === "default" && !later()) setTimeout(card, 6000);
  }).catch(function(){});
})();

/* xcPins: pin up to 3 pages (any tool or section). Pins show first in the menu and at the top of the home page.
   Saved on this device, and on the account when signed in, so they follow the member everywhere. */
(function(){
  if (window.XCPINS) return; window.XCPINS = 1;
  var MAX = 3, KEY = "xc_pins", path = location.pathname.replace(/\/+$/, "") || "/", signed = false;
  var NOPIN = /^\/($|login|register|account|logout|me\/preferences|offline|system-log|broadcast|moderate)/;
  var PIN_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 3h6l-1 6 4 4H6l4-4z"/><path d="M12 13v8"/></svg>';
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function local(){ try { return JSON.parse(localStorage.getItem(KEY) || "[]").slice(0, MAX); } catch (e){ return []; } }
  var P = local();
  function save(push){
    try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e){}
    if (push && signed) fetch("/api/pins/", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify({items: P})}).catch(function(){});
    draw();
  }
  function label(){
    var n = document.querySelector(".tnav a[href='" + path + "'], .tnav a[href='" + path + "/']");
    if (n && n.textContent.trim()) return n.textContent.trim().slice(0, 24);
    var h = document.querySelector("main h1, .wrap h1, h1"), t = (document.title || "").split(/\s+[\u2014|\-]\s+/)[0].trim();
    var s = (h && h.textContent.trim()) || (t && !/^XpertCreation$/i.test(t) ? t : path.slice(1));
    s = s.replace(/^[^\w\u0600-\u06FF]+/, "").replace(/\s+/g, " ");
    return (s.length > 24 ? s.slice(0, 23).replace(/\s+\S*$/, "") + "\u2026" : s) || path;
  }
  function pinned(p){ return P.some(function(x){ return x.path === p; }); }
  function icon(p){
    var a = document.querySelector(".tnav a[href='" + p + "'] svg, .tnav a[href='" + p + "/'] svg");
    return a ? a.outerHTML : '<svg class="tic" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 3h6l-1 6 4 4H6l4-4z"/><path d="M12 13v8"/></svg>';
  }
  var st = document.createElement("style");
  st.textContent = ".tpin{flex:0 0 auto;width:36px;height:36px;margin-left:6px;border-radius:11px;display:inline-grid;place-items:center;background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);color:var(--ink-soft,#5A657C);cursor:pointer;padding:0}"
    + ".tpin svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}"
    + ".tpin.on{background:#FEF3C7;border-color:#FCD34D;color:#B45309}.tpin.on svg{fill:#FCD34D}"
    + "@media(max-width:600px){.tpin{width:34px;height:34px;margin-left:4px}}"
    + ".tnav a.tpinned,.tdrop a.tpinned{background:#FFFBEB;color:#92400E!important;box-shadow:inset 0 0 0 1px #FCD34D}"
    + ".xcpinpop{position:fixed;z-index:9001;right:12px;top:62px;width:290px;background:#fff;border:1px solid #E4E8F2;border-radius:16px;box-shadow:0 18px 44px rgba(13,20,36,.25);padding:12px;font-family:inherit;color:#0D1424}"
    + ".xcpinpop b{display:block;font-size:14px;margin-bottom:4px}.xcpinpop p{margin:0 0 8px;font-size:12.5px;color:#5A657C}"
    + ".xcpinpop button{display:flex;width:100%;align-items:center;gap:8px;text-align:left;border:1px solid #E4E8F2;background:#F8FAFC;border-radius:10px;padding:9px 10px;margin-top:6px;font:inherit;font-size:13.5px;cursor:pointer}"
    + ".xcpinpop button:hover{border-color:#DC2626;background:#FEF2F2}.xcpinpop button i{margin-left:auto;font-style:normal;color:#DC2626;font-weight:800}"
    + ".xcpins{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:6px 0 14px}"
    + ".xcpins a{position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:6px;padding:14px 12px;border-radius:16px;text-decoration:none;color:#0D1424;background:linear-gradient(135deg,#FFFBEB,#FEF3C7);border:1px solid #FDE68A;font-weight:800;font-size:13.5px;line-height:1.25;min-height:78px}"
    + ".xcpins a svg{width:24px;height:24px;fill:none;stroke:#B45309;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;margin:0}"
    + ".xcpins a .x{position:absolute;top:6px;right:6px;width:22px;height:22px;border-radius:50%;border:0;background:rgba(0,0,0,.06);color:#92400E;font-weight:900;cursor:pointer;line-height:22px;padding:0}"
    + ".xcpins .hd{grid-column:1/-1;display:flex;align-items:center;gap:6px;font-size:13px;font-weight:800;color:#92400E;margin-bottom:-2px}"
    + ".xcpins .hd small{margin-left:auto;font-weight:600;color:#A16207}"
    + "header.top:has(> .in){display:flex;align-items:center;justify-content:flex-end;gap:4px;flex-wrap:wrap}header.top:has(> .in) > .in{flex:1 1 auto;min-width:0}"
    + "@media(max-width:600px){header.top:has(> .in) > .in{flex-basis:100%}header.top:has(> .in){padding-bottom:6px}}"
    + ".xcpinpick{position:fixed;inset:0;z-index:9003;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}"
    + "@media(min-width:700px){.xcpinpick{align-items:center}}"
    + ".xcpinpick .in{background:#fff;width:100%;max-width:520px;max-height:86vh;display:flex;flex-direction:column;border-radius:20px 20px 0 0;padding:14px 14px 10px;font-family:inherit;color:#0D1424}"
    + "@media(min-width:700px){.xcpinpick .in{border-radius:20px}}"
    + ".xcpinpick .hd{display:flex;align-items:center;margin-bottom:10px}.xcpinpick .hd b{font-size:17px}.xcpinpick .x{margin-left:auto;border:0;background:#F1F5F9;width:34px;height:34px;border-radius:50%;font-size:18px;cursor:pointer}"
    + ".xcpinpick input{width:100%;box-sizing:border-box;padding:11px 12px;border-radius:12px;border:1.5px solid #E4E8F2;font:inherit;font-size:15px;background:#F8FAFC;margin-bottom:8px}"
    + ".xcpinpick .ls{overflow:auto;display:grid;grid-template-columns:1fr 1fr;gap:6px;padding-bottom:6px}"
    + ".xcpinpick .ls button{display:flex;align-items:center;gap:8px;border:1.5px solid #E4E8F2;background:#fff;border-radius:12px;padding:10px;font:inherit;font-size:13.5px;font-weight:700;cursor:pointer;text-align:left;color:#0D1424}"
    + ".xcpinpick .ls button svg{width:18px;height:18px;fill:none;stroke:#1B4DFF;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:0 0 18px;margin:0}"
    + ".xcpinpick .ls button span{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.xcpinpick .ls button i{font-style:normal;font-size:11.5px;color:#1B4DFF}"
    + ".xcpinpick .ls button.on{background:#FFFBEB;border-color:#FCD34D}.xcpinpick .ls button.on i{color:#B45309}"
    + ".xcpins .add{background:#fff;border:1.5px dashed #FCD34D;color:#A16207;font-weight:700;justify-content:center;align-items:center;text-align:center;font-size:12.5px}";
  document.head.appendChild(st);
  var btn = null;
  function draw(){
    var head = document.querySelector("header.top") || document.querySelector("header.topbar");
    if (head && !NOPIN.test(path)){
      if (!btn){
        btn = document.createElement("button"); btn.type = "button"; btn.className = "tpin"; btn.innerHTML = PIN_SVG;
        var before = head.querySelector(".tcart") || head.querySelector(".tacct") || head.querySelector(".tdrop");
        if (before) before.parentNode.insertBefore(btn, before); else (head.querySelector(".in") || head).appendChild(btn);
        btn.onclick = toggle;
      }
      var on = pinned(path); btn.classList.toggle("on", on);
      btn.title = on ? "Unpin this page" : "Pin this page (up to " + MAX + ")"; btn.setAttribute("aria-label", btn.title);
    }
    [".tnav", ".tdrop"].forEach(function(sel){
      var n = document.querySelector(sel); if (!n) return;
      [].forEach.call(n.querySelectorAll("a.tpinned"), function(a){ a.remove(); });
      P.slice().reverse().forEach(function(x){
        var a = document.createElement("a"); a.href = x.path; a.className = "tpinned"; a.title = "Pinned";
        a.innerHTML = icon(x.path).replace("<svg", '<svg class="tic"') + esc(x.label);
        n.insertBefore(a, n.firstChild);
      });
    });
    if (path === "/") home();
  }
  function home(){
    var old = document.getElementById("xcpins"); if (old) old.remove();
    var anchor = document.getElementById("xcshow") || document.querySelector("a.xcgold");
    if (!anchor) return;
    var w = document.createElement("div"); w.id = "xcpins"; w.className = "xcpins";
    var h = '<div class="hd">📌 Your pins<small>' + (P.length ? "Tap the pin on any page to change" : "Pin up to " + MAX + " pages you use most") + '</small></div>';
    h += P.map(function(x, i){ return '<a href="' + esc(x.path) + '">' + icon(x.path) + esc(x.label) + '<button class="x" data-unpin="' + i + '" aria-label="Unpin">&times;</button></a>'; }).join("");
    for (var k = P.length; k < MAX; k++) h += '<a class="add" href="#" data-pickpin>+ Pin a tool or section<br><small style="font-weight:600">tap to choose</small></a>';
    w.innerHTML = h;
    anchor.parentNode.insertBefore(w, anchor);
    w.onclick = function(e){ if (e.target.closest("[data-pickpin]")){ e.preventDefault(); picker(); return; } var x = e.target.closest("[data-unpin]"); if (!x) return; e.preventDefault(); e.stopPropagation(); P.splice(+x.getAttribute("data-unpin"), 1); save(true); };
  }
  function toggle(e){
    e.stopPropagation();
    var old = document.querySelector(".xcpinpop"); if (old){ old.remove(); return; }
    if (pinned(path)){ P = P.filter(function(x){ return x.path !== path; }); save(true); return; }
    var item = {path: path, label: label()};
    if (P.length < MAX){ P.push(item); save(true); flashPin(); return; }
    var pop = document.createElement("div"); pop.className = "xcpinpop";
    pop.innerHTML = '<b>You can pin ' + MAX + ' pages</b><p>Tap one to replace it with &ldquo;' + esc(item.label) + '&rdquo;.</p>'
      + P.map(function(x, i){ return '<button type="button" data-rep="' + i + '">' + esc(x.label) + '<i>Replace</i></button>'; }).join("");
    document.body.appendChild(pop);
    pop.onclick = function(ev){ var b = ev.target.closest("[data-rep]"); if (!b) return; P[+b.getAttribute("data-rep")] = item; pop.remove(); save(true); flashPin(); };
    setTimeout(function(){ document.addEventListener("click", function c(ev){ if (!pop.contains(ev.target)){ pop.remove(); document.removeEventListener("click", c); } }); }, 0);
  }
  var EXTRA = [["XpertConnect", "/feed"], ["Money", "/money"], ["Freelance", "/market"], ["Property", "/market#property"], ["Store", "/store"], ["Jobs", "/jobs"],
    ["Rides", "/rides"], ["Roots of Love", "/roots"], ["Brand kit", "/brand"], ["Business cards", "/cards"], ["My CV", "/market#cv"], ["Step counter", "/steps"],
    ["Weather", "/weather"], ["Rates", "/rates"], ["Translate", "/translate"], ["Quran", "/quran"], ["Islamic", "/islamic"], ["Typing tutor", "/typing"],
    ["Games", "/games"], ["Blood bank", "/blood"], ["Donate", "/donate"], ["Pets", "/pets"], ["News", "/news"], ["Birthdays", "/birthdays"], ["Chat", "/chat"],
    ["Rewards", "/rewards"], ["Help", "/help"], ["Tools", "/tools"], ["Academy", "/academy/"], ["Vocabulary", "/vocabulary"], ["MCQs", "/mcq"], ["Clips", "/clips"]];
  function choices(){
    var seen = {}, out = [];
    function add(label, href){
      if (!href || href.charAt(0) !== "/" || href === "/" || NOPIN.test(href.split("#")[0])) return;
      var p = href.replace(/\/+(#|$)/, "$1") || href; if (p === "/academy") p = "/academy/";
      if (seen[p]) return; seen[p] = 1; out.push({path: p, label: String(label || "").replace(/^[^A-Za-z0-9]+/, "").trim().slice(0, 24) || p});
    }
    [].forEach.call(document.querySelectorAll(".tnav a:not(.tpinned), .tdrop a:not(.tpinned)"), function(a){ add(a.textContent, a.getAttribute("href")); });
    EXTRA.forEach(function(x){ add(x[0], x[1]); });
    return out.sort(function(a, b){ return a.label.localeCompare(b.label, "en", {sensitivity: "base"}); });
  }
  function picker(){
    var old = document.querySelector(".xcpinpick"); if (old) old.remove();
    var list = choices(), pop = document.createElement("div"); pop.className = "xcpinpick";
    pop.innerHTML = '<div class="in"><div class="hd"><b>📌 Pin a page</b><button type="button" class="x" aria-label="Close">×</button></div>'
      + '<input type="search" placeholder="Search: money, freelance, weather…" autocomplete="off"><div class="ls"></div></div>';
    document.body.appendChild(pop);
    var q = pop.querySelector("input"), ls = pop.querySelector(".ls");
    function draw2(){
      var t = q.value.trim().toLowerCase();
      ls.innerHTML = list.filter(function(x){ return !t || x.label.toLowerCase().indexOf(t) >= 0 || x.path.indexOf(t) >= 0; }).map(function(x){
        var on = pinned(x.path);
        return '<button type="button" data-path="' + esc(x.path) + '" data-label="' + esc(x.label) + '"' + (on ? ' class="on"' : '') + '>' + icon(x.path) + '<span>' + esc(x.label) + '</span><i>' + (on ? "Pinned" : "Pin") + '</i></button>'; }).join("") || '<p>Nothing found.</p>';
    }
    draw2(); q.oninput = draw2; setTimeout(function(){ q.focus(); }, 50);
    pop.onclick = function(e){
      if (e.target === pop || e.target.closest(".x")){ pop.remove(); return; }
      var b = e.target.closest("[data-path]"); if (!b) return;
      var p = b.getAttribute("data-path");
      if (pinned(p)){ P = P.filter(function(x){ return x.path !== p; }); save(true); draw2(); return; }
      if (P.length >= MAX){ alert("You can pin " + MAX + " pages. Unpin one first (tap × on its card)."); return; }
      P.push({path: p, label: b.getAttribute("data-label")}); save(true); flashPin();
      if (P.length >= MAX) pop.remove(); else draw2();
    };
  }
  function flashPin(){
    var t = document.createElement("div");
    t.style.cssText = "position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#0D1424;color:#fff;padding:10px 16px;border-radius:12px;font-weight:700;font-size:13.5px;z-index:9002;box-shadow:0 10px 30px rgba(0,0,0,.3)";
    t.textContent = "📌 Pinned. It shows first in the menu and on the home page.";
    document.body.appendChild(t); setTimeout(function(){ t.remove(); }, 2600);
  }
  function start(){
    draw();
    fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(u){
      if (!u || !(u.email || u.username || u.id)) return;
      signed = true;
      return fetch("/api/pins/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
        if (!d) return;
        if ((d.items || []).length){ P = d.items.slice(0, MAX); save(false); }
        else if (P.length) save(true);              // first time signed in: keep the pins made on this device
      });
    }).catch(function(){});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function(){ setTimeout(start, 50); }); else setTimeout(start, 50);
})();

/* setup_navback_v1: back button, logo goes home, menu never squeezed to nothing */
(function(){
  "use strict";
  function run(){
    var head = document.querySelector("header.top");
    if (!head || head.getAttribute("data-xcnb")) return;
    head.setAttribute("data-xcnb", "1");
    var row = head.querySelector(".in") || head;
    var st = document.createElement("style");
    st.textContent = ".xcback{flex:0 0 auto;width:34px;height:34px;border-radius:50%;border:1px solid var(--line,#E4E8F2);background:var(--card,#fff);color:var(--ink,#0D1424);font-size:19px;line-height:1;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;margin-right:6px;padding:0}"
      + ".xcback:hover{background:#EEF2FF;border-color:#C7D2FE}"
      + "header.top a.xchome{border:0!important;background:none!important;padding:0!important;box-shadow:none!important;height:auto!important;min-height:0!important}a.xchome{display:inline-flex;align-items:center;gap:8px;color:inherit;text-decoration:none;flex:0 0 auto}a.xchome:hover b{color:#1B4DFF}"
      + "header.top.xcnarrow .tnav,header.top.xcnarrow .xcna{display:none!important}header.top.xcnarrow .tmenu{display:inline-grid!important;place-items:center}"
      + "@media(max-width:600px){header.top > .in{flex-wrap:wrap;row-gap:6px}}";
    document.head.appendChild(st);
    /* logo + page name -> home */
    var img = row.querySelector(":scope > img");
    if (img && !img.closest("a")) {
      var a = document.createElement("a"); a.href = "/"; a.className = "xchome"; a.title = "Home";
      var name = img.nextElementSibling && img.nextElementSibling.tagName === "B" ? img.nextElementSibling : null;
      row.insertBefore(a, img); a.appendChild(img); if (name) a.appendChild(name);
    }
    /* back button */
    if ((location.pathname.replace(/\/+$/, "") || "/") !== "/" && !row.querySelector(".xcback")) {
      var b = document.createElement("button"); b.type = "button"; b.className = "xcback"; b.textContent = "←";
      b.title = "Back"; b.setAttribute("aria-label", "Back");
      b.onclick = function(){
        var same = document.referrer && document.referrer.indexOf(location.origin) === 0;
        if (same && history.length > 1) history.back(); else location.href = "/";
      };
      row.insertBefore(b, row.firstChild);
    }
    /* when the page's own buttons leave no room, use the menu button instead of a squeezed menu */
    function fit(){
      var n = head.querySelector(".tnav"); if (!n) return;
      head.classList.remove("xcnarrow");
      if (window.innerWidth > 820 && n.clientWidth < 170) head.classList.add("xcnarrow");
    }
    [300, 1200, 2500].forEach(function(t){ setTimeout(fit, t); });
    window.addEventListener("resize", function(){ clearTimeout(fit.t); fit.t = setTimeout(fit, 150); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function(){ setTimeout(run, 120); }); else setTimeout(run, 120);
})();
