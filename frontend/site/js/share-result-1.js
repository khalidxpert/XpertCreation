/* "Share your result" card, for any page: quiz scores, calculator results, reports...
   XCResult.show({host: element, title: "Daily MCQs", big: "8 / 10", sub: "Today's score",
                  text: "I scored 8/10 ...", url: "https://xpertcreation.com/mcq"})
   Buttons: post on my XpertConnect wall (with a preview first), WhatsApp, Facebook, X, LinkedIn,
   Telegram, copy, and a picture of the result (phone share sheet, or download). */
(function(){
  "use strict";
  if (window.XCResult) return;
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  var css = document.createElement("style");
  css.textContent = ".xres{margin:12px 0;padding:16px;border-radius:18px;background:linear-gradient(135deg,#0D1424,#1B2E5C);color:#fff}"
    + ".xres h4{margin:0;font-size:12px;letter-spacing:.06em;text-transform:uppercase;opacity:.75}"
    + ".xres .big{font-size:34px;font-weight:900;letter-spacing:-.02em;margin:2px 0}"
    + ".xres .sub{font-size:13.5px;opacity:.85;margin-bottom:12px}"
    + ".xres .row{display:flex;gap:7px;flex-wrap:wrap}"
    + ".xres a,.xres button{display:inline-flex;align-items:center;gap:6px;padding:9px 12px;border-radius:11px;border:0;font:inherit;font-size:13px;"
    + "font-weight:700;color:#fff;text-decoration:none;cursor:pointer}"
    + ".xres .wall{background:#1B4DFF}.xres .wa{background:#25D366}.xres .fb{background:#1877F2}.xres .x{background:#000;border:1px solid #333}"
    + ".xres .li{background:#0A66C2}.xres .tg{background:#229ED9}.xres .cp,.xres .img{background:rgba(255,255,255,.14)}"
    + ".xresm{position:fixed;inset:0;z-index:300;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}"
    + ".xresm .bx{background:#fff;color:#0D1424;width:100%;max-width:520px;border-radius:20px 20px 0 0;padding:18px}"
    + "@media(min-width:600px){.xresm{align-items:center}.xresm .bx{border-radius:20px}}"
    + ".xresm textarea{width:100%;min-height:120px;border:1.5px solid #E4E8F2;border-radius:12px;padding:11px;font:inherit;font-size:14.5px;margin:10px 0}"
    + ".xresm .bt{display:flex;gap:8px}.xresm .bt button{flex:1;padding:12px;border-radius:12px;border:1.5px solid #E4E8F2;background:#fff;font:inherit;font-weight:800;cursor:pointer}"
    + ".xresm .bt .go{background:#1B4DFF;color:#fff;border-color:#1B4DFF}.xresm .msg{font-size:13px;min-height:18px;color:#B91C1C}";
  document.head.appendChild(css);

  function picture(o){
    return new Promise(function(done){
      var c = document.createElement("canvas"); c.width = 1080; c.height = 1080;
      var g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 1080, 1080);
      gr.addColorStop(0, "#0D1424"); gr.addColorStop(1, "#1B3A8C"); g.fillStyle = gr; g.fillRect(0, 0, 1080, 1080);
      g.fillStyle = "rgba(255,255,255,.06)"; g.beginPath(); g.arc(940, 160, 260, 0, 7); g.fill();
      g.textAlign = "center"; g.fillStyle = "#fff";
      function wrap(t, y, size, weight, maxW, lh){
        g.font = weight + " " + size + "px system-ui,Segoe UI,Roboto,sans-serif";
        var words = String(t).split(/\s+/), line = "", lines = [];
        words.forEach(function(w){ var tt = line ? line + " " + w : w; if (g.measureText(tt).width > maxW && line){ lines.push(line); line = w; } else line = tt; });
        if (line) lines.push(line);
        lines.slice(0, 4).forEach(function(l, i){ g.fillText(l, 540, y + i * lh); });
        return y + Math.min(lines.length, 4) * lh;
      }
      g.globalAlpha = .8; wrap(String(o.title || "").toUpperCase(), 250, 40, "700", 900, 50); g.globalAlpha = 1;
      wrap(o.big || "", 470, o.big && o.big.length > 9 ? 110 : 170, "900", 980, 150);
      g.globalAlpha = .9; wrap(o.sub || "", 640, 44, "600", 900, 56); g.globalAlpha = 1;
      g.fillStyle = "#1B4DFF"; g.fillRect(0, 960, 1080, 120);
      g.fillStyle = "#fff"; g.font = "800 44px system-ui,Segoe UI,Roboto,sans-serif";
      g.fillText((o.url || location.href).replace(/^https?:\/\//, "").replace(/\/$/, ""), 540, 1036);
      var logo = new Image();
      logo.onload = function(){ g.drawImage(logo, 476, 60, 128, 128); c.toBlob(done, "image/png"); };
      logo.onerror = function(){ c.toBlob(done, "image/png"); };
      logo.src = "/brand/logo-64.png";
    });
  }

  function wall(o){
    var m = document.createElement("div"); m.className = "xresm";
    m.innerHTML = '<div class="bx"><b style="font-size:16px">Post on my XpertConnect wall</b>'
      + '<p style="font-size:12.5px;color:#5A657C;margin:4px 0 0">You can change the words before posting.</p>'
      + '<textarea maxlength="1900">' + esc(o.text + "\n" + o.url) + '</textarea><div class="msg"></div>'
      + '<div class="bt"><button type="button" data-c>Cancel</button><button type="button" class="go" data-p>Post</button></div></div>';
    document.body.appendChild(m);
    m.addEventListener("click", function(e){
      if (e.target === m || e.target.closest("[data-c]")){ m.remove(); return; }
      var p = e.target.closest("[data-p]"); if (!p || p.disabled) return;
      p.disabled = true; p.textContent = "Posting…";
      fetch("/api/share/wall/", {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")},
        body: JSON.stringify({text: m.querySelector("textarea").value, page: location.pathname})})
        .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {s: r.status, d: d}; }); })
        .then(function(r){
          if (r.s === 200){
            m.querySelector(".bx").innerHTML = '<b style="font-size:16px">✔ Posted on your wall</b>'
              + '<p style="margin:8px 0 14px;font-size:14px">Your friends can see it on XpertConnect.</p>'
              + '<div class="bt"><button type="button" data-c>Close</button><a class="go" href="/feed" style="flex:1;text-align:center;padding:12px;border-radius:12px;background:#1B4DFF;color:#fff;font-weight:800;text-decoration:none">Open XpertConnect</a></div>';
          } else if (r.s === 401 || r.s === 403){
            m.querySelector(".msg").innerHTML = 'Please <a href="/login?next=' + encodeURIComponent(location.pathname + location.search) + '">sign in</a> to post on your wall.';
            p.disabled = false; p.textContent = "Post";
          } else {
            m.querySelector(".msg").textContent = (r.d && r.d.detail) || "Could not post. Please try again.";
            p.disabled = false; p.textContent = "Post";
          }
        }).catch(function(){ m.querySelector(".msg").textContent = "No internet. Please try again."; p.disabled = false; p.textContent = "Post"; });
    });
  }

  function show(o){
    o = o || {}; o.url = o.url || location.href.split("#")[0]; o.text = o.text || o.title;
    var host = o.host || document.getElementById("xres"); if (!host) return;
    var full = o.text + " " + o.url, u = encodeURIComponent(o.url);
    var L = {wa: "https://wa.me/?text=" + encodeURIComponent(full), fb: "https://www.facebook.com/sharer/sharer.php?u=" + u,
             x: "https://x.com/intent/tweet?text=" + encodeURIComponent(o.text) + "&url=" + u,
             li: "https://www.linkedin.com/sharing/share-offsite/?url=" + u, tg: "https://t.me/share/url?url=" + u + "&text=" + encodeURIComponent(o.text)};
    host.innerHTML = '<div class="xres"><h4>' + esc(o.title) + '</h4>' + (o.big ? '<div class="big">' + esc(o.big) + '</div>' : '')
      + (o.sub ? '<div class="sub">' + esc(o.sub) + '</div>' : '') + '<div class="row">'
      + '<button type="button" class="wall" data-r="wall"><img src="/brand/xpertconnect/xc-icon-64.png?v=3" alt="" style="width:16px;height:16px;border-radius:4px">Post on my wall</button>'
      + '<a class="wa" href="' + L.wa + '" target="_blank" rel="noopener">WhatsApp</a>'
      + '<a class="fb" href="' + L.fb + '" target="_blank" rel="noopener">Facebook</a>'
      + '<a class="x" href="' + L.x + '" target="_blank" rel="noopener">X</a>'
      + '<a class="li" href="' + L.li + '" target="_blank" rel="noopener">LinkedIn</a>'
      + '<a class="tg" href="' + L.tg + '" target="_blank" rel="noopener">Telegram</a>'
      + '<button type="button" class="img" data-r="img">🖼️ Picture</button>'
      + '<button type="button" class="cp" data-r="copy">🔗 Copy</button></div></div>';
    host.onclick = function(e){
      var b = e.target.closest("[data-r]"); if (!b) return;
      var k = b.getAttribute("data-r");
      if (k === "wall") return wall(o);
      if (k === "copy"){
        var ok = function(){ b.textContent = "✓ Copied"; setTimeout(function(){ b.textContent = "🔗 Copy"; }, 1800); };
        if (navigator.clipboard) navigator.clipboard.writeText(full).then(ok, function(){ prompt("Copy this:", full); }); else prompt("Copy this:", full);
      }
      if (k === "img"){
        picture(o).then(function(blob){
          if (!blob) return;
          var f = null;
          try { f = new File([blob], "xpertcreation-result.png", {type: "image/png"}); } catch (er) {}
          if (f && navigator.canShare && navigator.canShare({files: [f]})){
            navigator.share({files: [f], text: full}).catch(function(){});
          } else {
            var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "xpertcreation-result.png";
            document.body.appendChild(a); a.click(); setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 1500);
          }
        });
      }
    };
  }
  window.XCResult = {show: show};
})();
