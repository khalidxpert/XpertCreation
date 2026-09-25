/* One menu for every page with the small header. Change the links here, and every page follows. */
(function(){
  "use strict";
  var head = document.querySelector("header.top") || document.querySelector("header.topbar");
  if (!head || head.querySelector(".tmenu")) return;
  var isHome = head.classList.contains("topbar");      // the home page has its own links; add only the menu button
  var LINKS = [["Home", "/"], ["Academy", "/academy/"], ["Tools", "/tools"], ["Connect", "/people"], ["Pets", "/pets"],
               ["Shows", "/shows"], ["Games", "/games"], ["Chat", "/chat"], ["Guide", "/docs"]];
  var path = location.pathname.replace(/\/+$/, "") || "/";
  function here(u){
    var b = u.replace(/\/+$/, "") || "/";
    if (b === "/") return path === "/";
    if (b === "/people") return path === "/people" || path.indexOf("/in/") === 0 || path === "/me/profile";
    if (b === "/pets") return path === "/pets" || path === "/lost" || path.indexOf("/pet/") === 0;
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
  if (getComputedStyle(head).position === "static") head.style.position = "relative";
  var links = LINKS.map(function(l){
    return "<a href='" + l[1] + "'" + (here(l[1]) ? " class='on' aria-current='page'" : "") + ">" + l[0] + "</a>";
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
