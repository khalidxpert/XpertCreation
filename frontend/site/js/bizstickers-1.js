/* Business stickers: a sticker set made from your company logo and name (Thank you, Order confirmed, Sale, Eid Mubarak...).
   Pick colours and words, add your own, then save them to My stickers (they show in XpertChat on every phone)
   and download the pack for WhatsApp, Telegram or Discord. Open with XCBiz.open(), or any element with data-bizstk. */
(function(){
  "use strict";
  if (window.XCBiz) return;
  var D = document;
  var TEXTS = [
    ["Thank you!", "شکریہ", 1], ["Order confirmed ✅", "", 1], ["Welcome!", "خوش آمدید", 1], ["SALE 🔥", "", 1],
    ["New arrival ✨", "", 1], ["We're open", "", 1], ["On the way 🚚", "", 1], ["Thanks for shopping", "", 1],
    ["Eid Mubarak 🌙", "عید مبارک", 1], ["Happy 14 August 🇵🇰", "جشنِ آزادی مبارک", 1],
    ["Jummah Mubarak", "جمعہ مبارک", 0], ["Ramadan Kareem", "رمضان کریم", 0],
    ["Closed today", "", 0], ["Call us 📞", "", 0], ["Out of stock", "", 0], ["Free delivery 🚚", "", 0]
  ];
  var COLORS = ["auto", "#1B4DFF", "#0F766E", "#01411C", "#B91C1C", "#EA580C", "#7C3AED", "#DB2777", "#0D1424", "#B8892D"];
  var S = {logo: null, name: "", color: "auto", auto: "#1B4DFF", style: "card", texts: TEXTS.map(function(t){ return {en: t[0], ur: t[1], on: !!t[2]}; })};

  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function api(url, opt){
    opt = opt || {};
    return fetch(url, {method: opt.method || "GET", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}, body: opt.body})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, status: r.status, d: d}; }); });
  }
  function loadImg(src){ return new Promise(function(res, rej){ var im = new Image(); im.onload = function(){ res(im); }; im.onerror = rej; im.src = src; }); }
  function avgColor(im){
    try {
      var c = D.createElement("canvas"); c.width = c.height = 40; var g = c.getContext("2d"); g.drawImage(im, 0, 0, 40, 40);
      var d = g.getImageData(0, 0, 40, 40).data, r = 0, gg = 0, b = 0, n = 0;
      for (var i = 0; i < d.length; i += 4){
        var R = d[i], G = d[i + 1], B2 = d[i + 2], A = d[i + 3], mx = Math.max(R, G, B2), mn = Math.min(R, G, B2);
        if (A < 128 || (mx > 225 && mn > 225) || mx - mn < 28) continue;      // skip see-through, white and grey
        r += R; gg += G; b += B2; n++;
      }
      if (!n) return "#1B4DFF";
      r = r / n; gg = gg / n; b = b / n;
      var l = (0.299 * r + 0.587 * gg + 0.114 * b); if (l > 150){ var k = 150 / l; r *= k; gg *= k; b *= k; }   // dark enough for white words
      return "#" + [r, gg, b].map(function(v){ return ("0" + Math.round(v).toString(16)).slice(-2); }).join("");
    } catch (e){ return "#1B4DFF"; }
  }
  function shade(hex, f){
    var n = parseInt(hex.slice(1), 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    return "rgb(" + [r, g, b].map(function(v){ return Math.max(0, Math.min(255, Math.round(v * f))); }).join(",") + ")";
  }
  function rr(g, x, y, w, h, r){ g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
  function fitText(g, text, max, size, weight, fam){
    var s = size; do { g.font = weight + " " + s + "px " + fam; s -= 2; } while (g.measureText(text).width > max && s > 14);
    return s + 2;
  }

  /* one sticker, 512 x 512, see-through outside the card */
  function draw(t){
    var c = D.createElement("canvas"); c.width = c.height = 512; var g = c.getContext("2d");
    var col = S.color === "auto" ? S.auto : S.color, FAM = "system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif";
    g.save(); g.translate(256, 256); g.rotate(-0.06); g.translate(-256, -256);
    if (S.style === "round"){
      g.beginPath(); g.arc(256, 256, 236, 0, Math.PI * 2); g.fillStyle = "#fff"; g.fill();
      g.beginPath(); g.arc(256, 256, 220, 0, Math.PI * 2);
    } else {
      rr(g, 26, 66, 460, 380, 70); g.fillStyle = "#fff"; g.fill();
      rr(g, 42, 82, 428, 348, 58);
    }
    var gr = g.createLinearGradient(40, 60, 470, 450); gr.addColorStop(0, col); gr.addColorStop(1, shade(col, 0.55)); g.fillStyle = gr; g.fill();
    var top = S.style === "round" ? 92 : 104, ls = S.style === "round" ? 132 : 124;
    if (S.logo){
      g.beginPath(); g.arc(256, top + ls / 2, ls / 2 + 8, 0, Math.PI * 2); g.fillStyle = "#fff"; g.fill();
      g.save(); g.beginPath(); g.arc(256, top + ls / 2, ls / 2, 0, Math.PI * 2); g.clip();
      var im = S.logo, k = Math.min(ls / im.width, ls / im.height); g.drawImage(im, 256 - im.width * k / 2, top + ls / 2 - im.height * k / 2, im.width * k, im.height * k);
      g.restore();
    }
    g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle";
    var y = top + ls + 52, max = S.style === "round" ? 330 : 380;
    fitText(g, t.en, max, 50, "900", FAM); g.fillText(t.en, 256, y);
    if (t.ur){ fitText(g, t.ur, max, 36, "700", "'Noto Nastaliq Urdu','Jameel Noori Nastaleeq'," + FAM); g.fillText(t.ur, 256, y + 50); }
    if (S.name){ g.globalAlpha = .9; fitText(g, S.name, max - 40, 24, "800", FAM); g.fillText(S.name, 256, S.style === "round" ? 420 : (t.ur ? y + 98 : y + 62)); g.globalAlpha = 1; }
    g.restore();
    return c;
  }

  function sheet(html){
    var ov = D.createElement("div"); ov.className = "xbz-sh"; ov.innerHTML = '<div class="xbz-box">' + html + "</div>";
    ov.addEventListener("click", function(e){ if (e.target === ov || e.target.closest("[data-bzx]")) ov.remove(); });
    D.body.appendChild(ov); return ov;
  }
  var css = D.createElement("style");
  css.textContent = [
    ".xbz-sh{position:fixed;inset:0;z-index:2147483100;background:rgba(13,20,36,.55);display:flex;align-items:flex-end;justify-content:center;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}",
    ".xbz-box{background:#fff;color:#0D1424;width:100%;max-width:620px;max-height:94vh;overflow:auto;border-radius:22px 22px 0 0;padding:16px 16px calc(18px + env(safe-area-inset-bottom))}",
    "@media(min-width:700px){.xbz-sh{align-items:center}.xbz-box{border-radius:22px}}",
    ".xbz-box h3{margin:0 0 4px;font-size:19px}.xbz-box p.s{margin:0 0 10px;font-size:13px;color:#5A657C}",
    ".xbz-box label.l{display:block;font-size:11.5px;font-weight:800;color:#5A657C;text-transform:uppercase;letter-spacing:.03em;margin:12px 0 6px}",
    ".xbz-box input[type=text]{width:100%;box-sizing:border-box;padding:11px 12px;border:1.5px solid #E4E8F2;border-radius:12px;font:inherit;font-size:15px;background:#F6F7FB}",
    ".xbz-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}",
    ".xbz-co{border:1.5px solid #E4E8F2;background:#fff;border-radius:12px;padding:7px 10px;display:flex;gap:8px;align-items:center;font:inherit;font-size:13.5px;font-weight:700;cursor:pointer}",
    ".xbz-co img{width:28px;height:28px;border-radius:8px;object-fit:contain;background:#F6F7FB}.xbz-co.on{border-color:#1B4DFF;background:#EEF2FF}",
    ".xbz-c{width:34px;height:34px;border-radius:50%;border:3px solid #fff;box-shadow:0 0 0 1.5px #D6DCE8;cursor:pointer;font-size:10px;font-weight:800;color:#fff}.xbz-c.on{box-shadow:0 0 0 3px #0D1424}",
    ".xbz-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;margin-top:8px}",
    ".xbz-t{position:relative;border:2px solid #E4E8F2;border-radius:16px;padding:4px;background:repeating-conic-gradient(#F1F4FA 0 25%,#fff 0 50%) 0 0/16px 16px;cursor:pointer}",
    ".xbz-t canvas{width:100%;display:block}.xbz-t.on{border-color:#16A34A}.xbz-t i{position:absolute;top:6px;right:6px;width:24px;height:24px;border-radius:50%;background:#fff;border:2px solid #C9D1E3;font-style:normal;display:grid;place-items:center;font-size:13px;font-weight:900;color:#fff}",
    ".xbz-t.on i{background:#16A34A;border-color:#16A34A}",
    ".xbz-btn{border:0;border-radius:13px;padding:12px 16px;font:inherit;font-weight:800;font-size:14.5px;cursor:pointer;background:#0D1424;color:#fff}",
    ".xbz-btn.g{background:#16A34A}.xbz-btn.o{background:#fff;color:#0D1424;border:1.5px solid #E4E8F2}.xbz-btn:disabled{opacity:.5}",
    ".xbz-msg{font-size:13.5px;margin-top:10px;color:#0B6B47}.xbz-msg.bad{color:#B91C1C}",
    ".xbz-sw{display:flex;border:1.5px solid #E4E8F2;border-radius:12px;overflow:hidden}.xbz-sw button{border:0;background:#fff;padding:8px 14px;font:inherit;font-weight:700;cursor:pointer}.xbz-sw button.on{background:#0D1424;color:#fff}"
  ].join("\n");
  D.head.appendChild(css);

  function open(){
    var ov = sheet('<h3>🏢 Business stickers</h3><p class="s">A sticker set with your logo and name. Send them to customers in XpertChat, or download the pack for WhatsApp, Telegram or Discord.</p><div class="xbz-body"><p class="s">Loading…</p></div>');
    var box = ov.querySelector(".xbz-body"), cos = [];
    api("/api/companies/mine/").then(function(r){
      if (r.status === 401 || r.status === 403){ box.innerHTML = '<p class="s">Please <a href="/login?next=' + encodeURIComponent(location.pathname) + '">sign in</a> first.</p>'; return; }
      cos = ((r.d && r.d.companies) || []).filter(function(c){ return c.logo; });
      var first = cos[0];
      (first ? loadImg(first.logo).then(function(im){ S.logo = im; S.auto = avgColor(im); S.name = first.name; S.co = first.id; }).catch(function(){}) : Promise.resolve()).then(render);
    });
    function render(){
      var h = '<label class="l">Logo</label><div class="xbz-row">' + cos.map(function(c){ return '<button type="button" class="xbz-co' + (S.co === c.id ? " on" : "") + '" data-co="' + c.id + '"><img src="' + esc(c.logo) + '" alt="">' + esc(c.name) + "</button>"; }).join("")
        + '<button type="button" class="xbz-co' + (S.co === "up" ? " on" : "") + '" data-up="1">⬆️ Upload a logo</button></div>'
        + (cos.length ? "" : '<p class="s" style="margin-top:6px">No company logo found. Upload your logo, or add one on your <a href="/company/manage">company page</a>.</p>')
        + '<label class="l">Business name on the stickers</label><input type="text" data-k="name" maxlength="40" value="' + esc(S.name) + '" placeholder="e.g. Ali Mobiles">'
        + '<label class="l">Colour and shape</label><div class="xbz-row">' + COLORS.map(function(c){ var v = c === "auto" ? S.auto : c; return '<button type="button" class="xbz-c' + (S.color === c ? " on" : "") + '" data-col="' + c + '" style="background:' + v + '" title="' + (c === "auto" ? "From your logo" : c) + '">' + (c === "auto" ? "LOGO" : "") + "</button>"; }).join("")
        + '<span class="xbz-sw" style="margin-left:auto"><button type="button" data-st="card" class="' + (S.style === "card" ? "on" : "") + '">▭ Card</button><button type="button" data-st="round" class="' + (S.style === "round" ? "on" : "") + '">◯ Round</button></span></div>'
        + '<label class="l">Stickers (tap to pick)</label><div class="xbz-g"></div>'
        + '<label class="l">Add your own words</label><div class="xbz-row"><input type="text" data-k="own" maxlength="28" placeholder="e.g. 20% off today — English or اردو" style="flex:1"><button type="button" class="xbz-btn o" data-add="1">＋ Add</button></div>'
        + '<div class="xbz-row" style="margin-top:14px"><button type="button" class="xbz-btn g" data-save="1" style="flex:1">Save to My stickers</button><button type="button" class="xbz-btn o" data-bzx="1">Close</button></div><div class="xbz-msg"></div>';
      box.innerHTML = h; grid();
    }
    function grid(){
      var g = box.querySelector(".xbz-g"); if (!g) return; g.innerHTML = "";
      S.texts.forEach(function(t, i){
        var d = D.createElement("div"); d.className = "xbz-t" + (t.on ? " on" : ""); d.setAttribute("data-ti", i);
        d.appendChild(draw(t)); d.insertAdjacentHTML("beforeend", "<i>✓</i>"); g.appendChild(d);
      });
      var n = S.texts.filter(function(t){ return t.on; }).length, b = box.querySelector("[data-save]");
      if (b){ b.textContent = "Save " + n + " to My stickers"; b.disabled = !n; }
    }
    var tmo;
    box.addEventListener("input", function(e){ if (e.target.getAttribute("data-k") === "name"){ S.name = e.target.value.trim(); clearTimeout(tmo); tmo = setTimeout(grid, 250); } });
    box.addEventListener("click", function(e){
      var t = e.target, el;
      if ((el = t.closest("[data-co]"))){ var c = cos.filter(function(x){ return String(x.id) === el.getAttribute("data-co"); })[0]; if (c) loadImg(c.logo).then(function(im){ S.logo = im; S.auto = avgColor(im); S.co = c.id; if (!S.name || cos.some(function(x){ return x.name === S.name; })) S.name = c.name; render(); }); return; }
      if (t.closest("[data-up]")){
        var inp = D.createElement("input"); inp.type = "file"; inp.accept = "image/*";
        inp.onchange = function(){ var f = inp.files[0]; if (!f) return; var u = URL.createObjectURL(f); loadImg(u).then(function(im){ S.logo = im; S.auto = avgColor(im); S.co = "up"; render(); }); };
        inp.click(); return;
      }
      if ((el = t.closest("[data-col]"))){ S.color = el.getAttribute("data-col"); render(); return; }
      if ((el = t.closest("[data-st]"))){ S.style = el.getAttribute("data-st"); render(); return; }
      if ((el = t.closest("[data-ti]"))){ var x = S.texts[+el.getAttribute("data-ti")]; x.on = !x.on; el.classList.toggle("on", x.on); var n = S.texts.filter(function(t){ return t.on; }).length, b = box.querySelector("[data-save]"); b.textContent = "Save " + n + " to My stickers"; b.disabled = !n; return; }
      if (t.closest("[data-add]")){ var o = box.querySelector("[data-k=own]"), v = o.value.trim(); if (!v) return; var ur = /[؀-ۿ]/.test(v); S.texts.unshift({en: ur ? "" : v, ur: ur ? v : "", on: true}); o.value = ""; grid(); return; }
      if (t.closest("[data-save]")) save(t.closest("[data-save]"));
    });
    function save(btn){
      var msg = box.querySelector(".xbz-msg"), list = S.texts.filter(function(t){ return t.on; });
      btn.disabled = true; msg.className = "xbz-msg"; msg.textContent = "Checking your stickers…";
      api("/api/notify/stickers/mine/").then(function(r){
        if (!r.ok){ throw new Error(r.status === 401 || r.status === 403 ? "Please sign in first." : "Could not reach your stickers."); }
        var room = (r.d.max || 40) - (r.d.stickers || []).length;
        if (room <= 0) throw new Error("You already have " + (r.d.max || 40) + " stickers. Remove some in My stickers first.");
        var todo = list.slice(0, room), skipped = list.length - todo.length, done = 0;
        return todo.reduce(function(p, t){
          return p.then(function(){
            msg.textContent = "Saving " + (done + 1) + " of " + todo.length + "…";
            return new Promise(function(res){ draw(t).toBlob(res, "image/webp", 0.86); }).then(function(bl){
              if (!bl || bl.type !== "image/webp") return new Promise(function(res){ draw(t).toBlob(res, "image/png"); });
              return bl;
            }).then(function(bl){
              var fd = new FormData(); fd.append("file", bl, "biz.webp");
              return api("/api/notify/stickers/mine/", {method: "POST", body: fd}).then(function(x){ if (!x.ok) throw new Error((x.d && x.d.detail) || "Could not save."); done++; });
            });
          });
        }, Promise.resolve()).then(function(){
          msg.innerHTML = "✅ " + done + " business sticker" + (done === 1 ? "" : "s") + " saved to My stickers." + (skipped ? " " + skipped + " left out (40 at most)." : "")
            + ' <a href="/api/notify/stickers/pack/" download style="font-weight:800;color:#16A34A">⬇ Download the pack (ZIP)</a> for WhatsApp, Telegram or Discord.';
          if (window.XCStk && XCStk.reload) try { XCStk.reload(); } catch (e) {}
          btn.disabled = false;
        });
      }).catch(function(e){ msg.className = "xbz-msg bad"; msg.textContent = e.message; btn.disabled = false; });
    }
  }
  D.addEventListener("click", function(e){ var t = e.target.closest && e.target.closest("[data-bizstk]"); if (!t) return; e.preventDefault(); e.stopPropagation(); open(); }, true);
  window.XCBiz = {open: open, _draw: draw, _state: S};
})();
