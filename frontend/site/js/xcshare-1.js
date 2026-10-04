/* "Share on XpertConnect": next to every WhatsApp share button, a button that posts the same text to the member's wall. */
(function(){
  "use strict";
  if (window.__xcshare) return; window.__xcshare = 1;
  var ICON = "/brand/xpertconnect/xc-icon-64.png";
  var css = document.createElement("style");
  css.textContent = ".xcsh{display:inline-flex;align-items:center;gap:6px;cursor:pointer}.xcsh img{width:18px;height:18px;border-radius:5px;flex:0 0 auto}"
    + ".xcsh-plain{border:1.5px solid #C7D2FE;background:#EEF2FF;color:#1B4DFF;border-radius:12px;padding:9px 13px;font:inherit;font-weight:800;text-decoration:none;margin:4px 0 4px 6px}"
    + ".xcshm{position:fixed;inset:0;z-index:900;background:rgba(13,20,36,.55);display:flex;align-items:flex-end;justify-content:center}"
    + ".xcshm>div{background:#fff;color:#0D1424;width:min(520px,100%);border-radius:20px 20px 0 0;padding:16px 16px max(16px,env(safe-area-inset-bottom));box-shadow:0 -10px 40px rgba(0,0,0,.25);font-family:inherit}"
    + "@media(min-width:640px){.xcshm{align-items:center}.xcshm>div{border-radius:20px}}"
    + ".xcshm h3{margin:0 0 8px;display:flex;align-items:center;gap:8px;font-size:18px}.xcshm h3 img{width:28px;height:28px;border-radius:8px}"
    + ".xcshm textarea{width:100%;box-sizing:border-box;min-height:120px;border:1.5px solid #E4E8F2;border-radius:12px;padding:10px;font:inherit;font-size:15px;resize:vertical}"
    + ".xcshm .b{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}.xcshm button{border:0;border-radius:12px;padding:10px 16px;font:inherit;font-weight:800;cursor:pointer}"
    + ".xcshm .go{background:#1B4DFF;color:#fff}.xcshm .no{background:#F1F4FA;color:#0D1424}.xcshm .m{min-height:20px;font-size:14px;margin-top:6px}";
  document.head.appendChild(css);
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function shareText(el){
    var href = el.getAttribute("href") || "", m = href.match(/[?&]text=([^&]*)/);
    var t = ""; try { t = m ? decodeURIComponent(m[1].replace(/\+/g, " ")) : ""; } catch (e) { t = ""; }
    if (!t){ var title = (document.querySelector("h1") || {}).textContent || document.title; t = title.trim() + "\n" + location.href; }
    if (t.indexOf("http") < 0) t += "\n" + location.href;
    return t.slice(0, 2900);
  }
  function isShare(a){
    var h = (a.getAttribute && a.getAttribute("href")) || "";
    return /(^https?:\/\/)?(wa\.me\/\?|api\.whatsapp\.com\/send\?(?![^#]*phone=\d))[^#]*text=/i.test(h);
  }
  function add(a){
    if (a.getAttribute("data-xcsh") || a.closest(".xcshm, .fbody, .cb, .afr")) return;
    a.setAttribute("data-xcsh", "1");
    var b = document.createElement("button"); b.type = "button";
    var styled = a.className && /btn|afb|share|wa|go|pill/i.test(a.className);
    b.className = "xcsh " + (styled ? a.className.replace(/\b(wa|whatsapp|green)\S*/gi, "") : "xcsh-plain");
    if (styled){ b.style.background = "#1B4DFF"; b.style.color = "#fff"; b.style.borderColor = "#1B4DFF"; }
    b.innerHTML = '<img src="' + ICON + '" alt="">XpertConnect';
    b.setAttribute("aria-label", "Share on XpertConnect");
    b.addEventListener("click", function(e){ e.preventDefault(); e.stopPropagation(); open(shareText(a)); });
    a.insertAdjacentElement("afterend", b);
  }
  function open(text){
    var m = document.createElement("div"); m.className = "xcshm";
    m.innerHTML = '<div role="dialog" aria-label="Share on XpertConnect"><h3><img src="' + ICON + '" alt="">Share on XpertConnect</h3><textarea maxlength="3000"></textarea>'
      + '<div class="m"></div><div class="b"><button class="no" type="button">Cancel</button><button class="go" type="button">Post on my wall</button></div></div>';
    document.body.appendChild(m); var ta = m.querySelector("textarea"), msg = m.querySelector(".m"), go = m.querySelector(".go");
    ta.value = text; ta.focus();
    function close(){ m.remove(); }
    m.addEventListener("click", function(e){ if (e.target === m || e.target.classList.contains("no")) close(); });
    go.addEventListener("click", function(){
      var body = ta.value.trim(); if (!body){ msg.textContent = "Write something to share."; return; }
      go.disabled = true; msg.textContent = "Posting\u2026";
      function send(vis){ return fetch("/api/feed/posts/", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify({body: body, visibility: vis})}); }
      send("public").then(function(r){ return r.status === 400 ? send("members") : r; }).then(function(r){
        if (r.status === 401 || r.status === 403){ msg.innerHTML = 'Sign in to share on your wall. <a href="/login?next=' + encodeURIComponent(location.pathname + location.search) + '">Sign in</a>'; go.disabled = false; return; }
        if (!r.ok){ msg.textContent = "Could not post right now. Please try again."; go.disabled = false; return; }
        m.querySelector("div").innerHTML = '<h3><img src="' + ICON + '" alt="">Shared \u2714</h3><p style="margin:4px 0 12px">It\u2019s on your wall now.</p><div class="b"><button class="no" type="button">Close</button><a class="go" href="/feed" style="text-decoration:none;border-radius:12px;padding:10px 16px;font-weight:800;background:#1B4DFF;color:#fff">View on XpertConnect</a></div>';
        setTimeout(close, 8000);
      }).catch(function(){ msg.textContent = "Could not post. Check your connection."; go.disabled = false; });
    });
  }
  function scan(root){ [].forEach.call((root || document).querySelectorAll ? (root || document).querySelectorAll("a[href*='wa.me'], a[href*='api.whatsapp.com']") : [], function(a){ if (isShare(a)) add(a); }); }
  new MutationObserver(function(list){ list.forEach(function(mu){ [].forEach.call(mu.addedNodes, function(n){ if (n.nodeType === 1){ if (n.matches && n.matches("a") && isShare(n)) add(n); else scan(n); } }); }); })
    .observe(document.body, {childList: true, subtree: true});
  scan(document);
})();
