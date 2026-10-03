/* "Share your success": when a game shows a win message, offer to post it on the player's XpertConnect wall or WhatsApp.
   Never posts by itself. Watches for win text that appears after the page has loaded. */
(function(){
  "use strict";
  var GAMES = {pool: "8-Ball Pool", chess: "Chess", carrom: "Carrom", cricket: "Cricket", ludo: "Ludo", connect4: "Connect Four", tictactoe: "Tic-tac-toe",
               "2048": "2048", snake: "Snake", sudoku: "Sudoku", minesweeper: "Minesweeper", simon: "Simon", wordgame: "Word Game", arrows: "Arrow Escape", memory: "Memory Match"};
  var path = location.pathname.replace(/^\/+|\/+$/g, "").split("/")[0], game = GAMES[path] || "a game";
  var WIN = /(you win|you won|you beat|you've won|you have won|solved|level \d+ complete|level complete|victory)/i;
  var NOT = /(can be solved|every level|how to|rules|fouls)/i;
  var ready = false, last = 0;
  setTimeout(function(){ ready = true; }, 1500);
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
  var css = document.createElement("style");
  css.textContent = ".xws{position:fixed;left:50%;bottom:max(18px,env(safe-area-inset-bottom));transform:translateX(-50%);z-index:700;width:min(420px,calc(100% - 24px));background:#fff;color:#0D1424;border-radius:20px;box-shadow:0 18px 50px rgba(13,20,36,.35);padding:16px;font-family:inherit;animation:xwsin .25s ease-out}"
    + "@keyframes xwsin{from{transform:translate(-50%,30px);opacity:0}}.xws h3{margin:0 0 4px;font-size:19px}.xws p{margin:0 0 12px;color:#5A657C;font-size:14px}"
    + ".xws .b{display:flex;gap:8px;flex-wrap:wrap}.xws button,.xws a{flex:1;min-width:110px;border:0;border-radius:12px;padding:11px 12px;font:inherit;font-weight:800;cursor:pointer;text-align:center;text-decoration:none}"
    + ".xws .w{background:#1B4DFF;color:#fff}.xws .g{background:#25D366;color:#fff}.xws .n{background:#F1F4FA;color:#0D1424}";
  document.head.appendChild(css);
  function text(win){
    return "\uD83C\uDFC6 " + win.replace(/\s+/g, " ").trim().replace(/[.!]*$/, "!") + " \u2014 " + game + " on XpertCreation.\nCan you beat me? Play free: https://xpertcreation.com/" + path + "\n#XpertGames #XpertCreation";
  }
  function show(win){
    if (document.querySelector(".xws")) return;
    var t = text(win), box = document.createElement("div"); box.className = "xws"; box.setAttribute("role", "dialog");
    box.innerHTML = "<h3>\uD83C\uDFC6 Well played!</h3><p>Share your success with your friends?</p><div class=\"b\"><button class=\"w\" data-xws=\"wall\">Post on my wall</button>"
      + "<a class=\"g\" target=\"_blank\" rel=\"noopener\" href=\"https://wa.me/?text=" + encodeURIComponent(t) + "\">WhatsApp</a><button class=\"n\" data-xws=\"no\">Not now</button></div>";
    box.setAttribute("data-text", t); document.body.appendChild(box);
  }
  function post(box){
    var t = box.getAttribute("data-text"), p = box.querySelector("p"), btn = box.querySelector("[data-xws=wall]"); btn.disabled = true; p.textContent = "Posting\u2026";
    function send(vis){ return fetch("/api/feed/posts/", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify({body: t, visibility: vis})}); }
    send("public").then(function(r){ return r.status === 400 ? send("members") : r; }).then(function(r){
      if (r.status === 401 || r.status === 403){ p.innerHTML = "Sign in to post on your wall. <a href=\"/login\">Sign in</a>"; btn.disabled = false; return; }
      if (!r.ok){ p.textContent = "Could not post right now. Try again later."; btn.disabled = false; return; }
      p.innerHTML = "\u2714 Posted on your wall. <a href=\"/feed\">See it on XpertConnect</a>"; btn.remove(); setTimeout(function(){ box.remove(); }, 6000);
    }).catch(function(){ p.textContent = "Could not post. Check your connection."; btn.disabled = false; });
  }
  document.addEventListener("click", function(e){
    var b = e.target.closest("[data-xws]"); if (!b) return;
    var box = b.closest(".xws"); if (b.getAttribute("data-xws") === "no") box.remove(); else post(box);
  });
  function check(node){
    if (!ready || Date.now() - last < 60000) return;
    var el = node.nodeType === 3 ? node.parentNode : node; if (!el || el.closest && el.closest(".xws, header, footer, nav, .xcfoot")) return;
    var s = (node.nodeType === 3 ? node.nodeValue : (el.textContent || "")).slice(0, 300);
    var m = s.match(WIN); if (!m || NOT.test(s)) return;
    var line = s.split(/\n|\. (?=[A-Z])/).filter(function(x){ return WIN.test(x); })[0] || m[0];
    last = Date.now(); setTimeout(function(){ show(line.slice(0, 80)); }, 900);
  }
  new MutationObserver(function(list){
    list.forEach(function(mu){
      if (mu.type === "characterData") check(mu.target);
      else [].forEach.call(mu.addedNodes, function(n){ if (n.nodeType === 1 || n.nodeType === 3) check(n); });
    });
  }).observe(document.body, {childList: true, subtree: true, characterData: true});
})();
