/* XpertConnect bar (like LinkedIn): Home, My network, Jobs, Messages, Notifications, CV, Card, Me - on every XpertConnect page. */
(function(){
  if (window.XCBAR) return; window.XCBAR = 1;
  var I = [
    ["/feed", "Home", "M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10"],
    ["/people", "Network", "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20c.6-3.6 3.3-5.5 6.5-5.5s5.9 1.9 6.5 5.5M16.5 11a3 3 0 1 0-1-5.8M18 14.6c2 .6 3.2 2.2 3.5 4.9"],
    ["/jobs", "Jobs", "M3 8h18v11H3zM8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"],
    ["/chat", "Messages", "M4 5h16v11H9l-5 4z"],
    ["#bell", "Alerts", "M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"],
    ["/market#cv", "CV", "M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h7"],
    ["/cards", "Card", "M3 6h18v12H3zM8 10.5a1.8 1.8 0 1 0 0-.01M5.5 15c.4-1.4 1.3-2.2 2.5-2.2s2.1.8 2.5 2.2M13 10h5M13 13.5h4"],
    ["/me/profile", "Me", "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c.8-4 4-6 8-6s7.2 2 8 6"]
  ];
  var here = location.pathname.replace(/\/+$/, "") || "/";
  function on(p){ return p === here || (p === "/people" && /^\/(people|groups|in\/)/.test(here)) || (p === "/me/profile" && here === "/me/profile") || (p === "/feed" && /^\/post\//.test(here)); }
  var css = ".xcb{display:flex;justify-content:space-around;gap:2px;background:var(--card,#fff);border-bottom:1px solid var(--line,#E4E8F2);padding:4px 6px 2px;position:relative;z-index:5}"
    + ".xcb a{flex:1 1 0;max-width:96px;display:flex;flex-direction:column;align-items:center;gap:2px;padding:5px 2px 6px;text-decoration:none;color:var(--ink-soft,#5A657C);font-size:11.5px;font-weight:700;border-bottom:2.5px solid transparent;position:relative;min-width:0}"
    + ".xcb a span.t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}"
    + ".xcb a.on{color:var(--ink,#0D1424);border-bottom-color:var(--ink,#0D1424)}.xcb a:hover{color:var(--ink,#0D1424)}"
    + ".xcb svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}"
    + ".xcb a.on svg{stroke-width:2.3}"
    + ".xcb .n{position:absolute;top:1px;left:50%;margin-left:5px;min-width:17px;height:17px;line-height:17px;padding:0 4px;border-radius:99px;background:#DC2626;color:#fff;font-size:10.5px;font-weight:800;text-align:center}"
    + "@media(max-width:420px){.xcb a{font-size:10px}.xcb svg{width:22px;height:22px}}";
  function start(){
    var head = document.querySelector("header.top") || document.querySelector("header.topbar") || document.querySelector("header");
    if (!head || document.querySelector(".xcb")) return;
    var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
    var bar = document.createElement("nav"); bar.className = "xcb"; bar.setAttribute("aria-label", "XpertConnect");
    bar.innerHTML = I.map(function(x){ return '<a href="' + (x[0] === "#bell" ? "#" : x[0]) + '" data-k="' + x[1] + '" class="' + (on(x[0]) ? "on" : "") + '"><svg viewBox="0 0 24 24"><path d="' + x[2] + '"/></svg><span class="t">' + x[1] + '</span></a>'; }).join("");
    head.parentNode.insertBefore(bar, head.nextSibling);
    var bell = bar.querySelector('[data-k="Alerts"]');
    bell.onclick = function(e){ e.preventDefault(); var b = document.querySelector(".bellbtn"); if (b){ b.click(); window.scrollTo({top: 0, behavior: "smooth"}); } else location.href = "/feed"; };
    function badge(k, n){ var a = bar.querySelector('[data-k="' + k + '"]'); if (!a) return; var x = a.querySelector(".n"); if (!n){ if (x) x.remove(); return; } if (!x){ x = document.createElement("span"); x.className = "n"; a.appendChild(x); } x.textContent = n > 9 ? "9+" : n; }
    function counts(){
      fetch("/api/notify/mine/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){ if (d) badge("Alerts", d.unread || 0); }).catch(function(){});
      fetch("/api/notify/threads/unread/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){ if (d) badge("Messages", d.unread || 0); }).catch(function(){});
    }
    fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(u){
      if (!u) return;
      if (u.avatar_url || u.avatar){ var me = bar.querySelector('[data-k="Me"] svg'); var src = u.avatar_url || (/^(https?:)?\//.test(u.avatar) ? u.avatar : ""); if (me && src){ var im = document.createElement("img"); im.src = src; im.alt = ""; im.style.cssText = "width:24px;height:24px;border-radius:50%;object-fit:cover"; me.replaceWith(im); } }
      counts(); setInterval(function(){ if (!document.hidden) counts(); }, 60000);
    }).catch(function(){});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
