/* One menu for every page with the small header. Change the links here, and every page follows. */
(function(){
  "use strict";
  var head = document.querySelector("header.top") || document.querySelector("header.topbar");
  if (!head || head.querySelector(".tmenu")) return;
  var isHome = head.classList.contains("topbar");      // the home page has its own links; add only the menu button
  var LINKS = [["Home", "/"], ["Academy", "/academy/"], ["Tools", "/tools"], ["Connect", "/feed"], ["Jobs", "/jobs"], ["Pets", "/pets"],
               ["Shows", "/shows"], ["Games", "/games"], ["Chat", "/chat"], ["\uD83E\uDD16 Assistant", "/assistant"], ["Guide", "/docs"]];
  var path = location.pathname.replace(/\/+$/, "") || "/";
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
    "@media(max-width:820px){.tnav,header.topbar .xnav{display:none}.tmenu{display:inline-grid;place-items:center}}";
  document.head.appendChild(css);
  css.textContent += ".tic{width:16px;height:16px;flex:0 0 16px;vertical-align:-3px;margin-right:6px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}" +
    ".tnav a,.tdrop a{display:inline-flex;align-items:center}";
  if (getComputedStyle(head).position === "static") head.style.position = "relative";
  // One set of drawn icons, so the menu looks the same on Android, iPhone and Windows.
  var IC = {
    "/": '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    "/academy/": '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"/>',
    "/tools": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    "/people": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><path d="M16 5a3 3 0 0 1 0 6"/><path d="M17 15c2 .5 4 2 4 5"/>',
    "/feed": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><path d="M16 5a3 3 0 0 1 0 6"/><path d="M17 15c2 .5 4 2 4 5"/>',
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
    return "<a href='" + l[1] + "'" + (here(l[1]) ? " class='on' aria-current='page'" : "") + ">" + icon(l[1]) + l[0].replace(/^[^A-Za-z]+/, "") + "</a>";
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
  if (isHome){ var g = head.querySelector(".gear"); if (g) head.insertBefore(btn, g); else head.appendChild(btn); }
  else if (sp){ head.insertBefore(nav, sp); head.insertBefore(btn, sp); } else { head.appendChild(nav); head.appendChild(btn); }
  head.appendChild(drop);
  btn.onclick = function(e){ e.stopPropagation(); drop.classList.toggle("open"); };
  // "System log" - only for the super admin. The server decides; the answer is remembered for this visit.
  function addAdmin(){
    var link = '<a href="/system-log"' + (path === "/system-log" ? ' class="on"' : '') + '>\uD83D\uDEE1 System log</a>';
    link += '<a href="/broadcast"' + (path === "/broadcast" ? ' class="on"' : '') + '>\uD83D\uDCE2 Broadcast</a>';
    [head.querySelector(".tnav"), head.querySelector(".xnav"), drop].forEach(function(el){
      if (el && !el.querySelector('a[href="/system-log"]')) el.insertAdjacentHTML("beforeend", link);
    });
  }
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
