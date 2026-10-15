/* Promote page: "Pay by JazzCash / Raast" on waiting orders, and no buying inside the Play Store app
   (Google Play rule for digital items). */
(function(){
  if (window.XCPAYPROOF) return; window.XCPAYPROOF = 1;
  function inApp(){
    try {
      if (/[?&]src=app/.test(location.search) || /^android-app:\/\//.test(document.referrer)) sessionStorage.setItem("xc_inapp", "1");
      return sessionStorage.getItem("xc_inapp") === "1" || (window.matchMedia && matchMedia("(display-mode: standalone)").matches);
    } catch (e){ return false; }
  }
  var APP = inApp(), MODE = "", ACCT = null, PROOFS = {};
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-PK"); }
  var css = document.createElement("style");
  css.textContent = ".pp-btn{background:#C8102E!important;color:#fff!important;border:0!important;border-radius:10px;padding:8px 12px;font-weight:800;cursor:pointer;font-family:inherit}"
    + ".pp-st{display:inline-block;font-size:12.5px;font-weight:800;padding:5px 10px;border-radius:99px;background:#FEF3C7;color:#92400E;margin-right:6px}.pp-st.bad{background:#FEE2E2;color:#991B1B}"
    + ".pp-note{display:flex;gap:10px;align-items:center;background:#FFF7ED;border:1px solid #FED7AA;border-radius:14px;padding:12px 14px;margin:10px 0;font-size:14px;color:#7C2D12}"
    + ".pp-app{background:#F1F5F9;border:1px solid #E2E8F0;color:#334155}"
    + ".pp-sh{position:fixed;inset:0;z-index:9010;background:rgba(13,20,36,.55);display:flex;align-items:flex-end;justify-content:center}@media(min-width:700px){.pp-sh{align-items:center}}"
    + ".pp-sh .in{background:#fff;width:100%;max-width:480px;max-height:92vh;overflow:auto;border-radius:20px 20px 0 0;padding:16px;color:#0D1424;font-family:inherit}@media(min-width:700px){.pp-sh .in{border-radius:20px}}"
    + ".pp-sh h3{margin:0 0 4px;font-size:19px}.pp-amt{font-size:30px;font-weight:900;letter-spacing:-.02em;margin:6px 0 2px}.pp-sub{font-size:13px;color:#5A657C}"
    + ".pp-qr{display:flex;justify-content:center;margin:12px 0;padding:10px;background:#FFFBEB;border-radius:16px}.pp-qr svg{width:200px;height:200px;background:#fff;border-radius:10px}"
    + ".pp-row{display:flex;align-items:center;gap:8px;padding:9px 0;border-top:1px solid #EEF2F7;font-size:14px}.pp-row span{color:#5A657C;min-width:96px}.pp-row b{flex:1;word-break:break-all;font-family:ui-monospace,Menlo,monospace}"
    + ".pp-row button{border:1px solid #E2E8F0;background:#fff;border-radius:8px;padding:5px 9px;font:inherit;font-size:12px;font-weight:700;cursor:pointer}"
    + ".pp-steps{font-size:13.5px;line-height:1.55;padding-left:20px;margin:10px 0}"
    + ".pp-sh label{display:block;font-size:11px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:#5A657C;margin:10px 0 5px}"
    + ".pp-sh input[type=text]{width:100%;box-sizing:border-box;padding:11px 12px;border-radius:12px;border:1.5px solid #E4E8F2;font:inherit;font-size:15px;background:#F8FAFC}"
    + ".pp-file{display:block;text-align:center;padding:12px;border:1.5px dashed #CBD5E1;border-radius:12px;font-weight:800;font-size:14px;cursor:pointer;color:#334155}"
    + ".pp-bt{display:flex;gap:8px;margin-top:12px}.pp-bt button{flex:1;padding:13px;border-radius:12px;border:0;font:inherit;font-weight:800;cursor:pointer}.pp-go{background:#C8102E;color:#fff}.pp-no{background:#F1F5F9}"
    + ".pp-msg{font-size:13px;font-weight:700;color:#B91C1C;margin-top:8px}";
  document.head.appendChild(css);

  function sheet(id, amount){
    var a = ACCT || {}, sh = document.createElement("div"); sh.className = "pp-sh";
    var qr = "";
    if (a.qr && window.qrcode){ try { var q = qrcode(0, "M"); q.addData(a.qr); q.make(); qr = q.createSvgTag({cellSize: 4, margin: 2, scalable: true}); } catch (e){} }
    function row(l, v){ return v ? '<div class="pp-row"><span>' + l + '</span><b>' + esc(v) + '</b><button type="button" data-copy="' + esc(v) + '">Copy</button></div>' : ""; }
    sh.innerHTML = '<div class="in"><h3>💳 Pay by JazzCash / Raast</h3><div class="pp-amt">' + rs(amount) + '</div><div class="pp-sub">Order ' + id + ' · pay this exact amount</div>'
      + (qr ? '<div class="pp-qr">' + qr + '</div><div class="pp-sub" style="text-align:center">Scan with JazzCash, EasyPaisa or any bank app (Raast QR)</div>' : '')
      + '<div style="margin-top:10px">' + row("Account title", a.title) + row("Till ID", a.till) + row("IBAN", a.iban) + row("Account no.", a.account) + '</div>'
      + '<ol class="pp-steps"><li>Send <b>' + rs(amount) + '</b> by scanning the QR, or to the Till ID / IBAN above.</li><li>If the app lets you add a note, write <b>Order ' + id + '</b>.</li><li>Copy the transaction ID (TID) and take a screenshot.</li><li>Fill in below and tap Send. We check it and switch your item on, usually within a few hours.</li></ol>'
      + (a.note ? '<p class="pp-sub">' + esc(a.note) + '</p>' : '')
      + '<label>Transaction ID (TID)</label><input type="text" id="pptxn" maxlength="40" placeholder="e.g. 012345678901">'
      + '<label>Paid from (name or number, optional)</label><input type="text" id="ppfrom" maxlength="60" placeholder="e.g. Ali Khan, 0300…">'
      + '<label>Screenshot of the payment</label><label class="pp-file" id="ppfl">📎 Choose screenshot<input type="file" id="ppfile" accept="image/*,application/pdf" hidden></label>'
      + '<div class="pp-msg" id="ppmsg"></div><div class="pp-bt"><button type="button" class="pp-no">Later</button><button type="button" class="pp-go">Send</button></div></div>';
    document.body.appendChild(sh);
    sh.querySelector("#ppfile").onchange = function(){ var f = this.files[0]; sh.querySelector("#ppfl").firstChild.textContent = f ? "✓ " + f.name : "📎 Choose screenshot"; };
    sh.onclick = function(e){
      var c = e.target.closest("[data-copy]");
      if (c){ try { navigator.clipboard.writeText(c.getAttribute("data-copy")); } catch (er){} c.textContent = "Copied ✓"; return; }
      if (e.target === sh || e.target.classList.contains("pp-no")){ sh.remove(); return; }
      if (!e.target.classList.contains("pp-go")) return;
      var b = e.target, f = sh.querySelector("#ppfile").files[0], m = sh.querySelector("#ppmsg");
      if (!f){ m.textContent = "Add a screenshot of the payment."; return; }
      var fd = new FormData(); fd.append("txn", sh.querySelector("#pptxn").value); fd.append("sender", sh.querySelector("#ppfrom").value); fd.append("file", f);
      b.disabled = true; b.textContent = "Sending…";
      fetch("/api/payproof/orders/" + id + "/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}, body: fd})
        .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, d: d}; }); })
        .then(function(r){
          if (!r.ok){ b.disabled = false; b.textContent = "Send"; m.textContent = r.d.detail || "Could not send."; return; }
          PROOFS[id] = r.d; sh.querySelector(".in").innerHTML = '<h3>✅ Sent</h3><p style="font-size:15px;line-height:1.5">Thank you! The team will check your payment and switch your item on, usually within a few hours. You will get a notification.</p><div class="pp-bt"><button type="button" class="pp-no">Close</button></div>';
          paint();
        }).catch(function(){ b.disabled = false; b.textContent = "Send"; m.textContent = "Network problem. Try again."; });
    };
  }

  function paint(){
    if (APP){
      [].forEach.call(document.querySelectorAll(".pm-buy, [data-sim], .pp-btn"), function(b){
        if (b.getAttribute("data-ppapp")) return; b.setAttribute("data-ppapp", "1");
        var s = document.createElement("span"); s.className = "pm-buy"; s.setAttribute("data-ppapp", "1"); s.style.cssText = "opacity:.75;cursor:default;background:#E2E8F0;color:#334155"; s.textContent = "Not available in the app";
        b.replaceWith(s);
      });
      if (!document.querySelector(".pp-app") && document.querySelector(".pm-card")){
        var n = document.createElement("div"); n.className = "pp-note pp-app"; n.innerHTML = "ℹ️ <span>Paid items can't be bought in the app. You can see the prices and your earlier orders here.</span>";
        var first = document.querySelector(".pm-card"); first.parentNode.insertBefore(n, first);
      }
      return;
    }
    if (MODE !== "manual" || !ACCT || !ACCT.enabled) return;
    if (!document.querySelector(".pp-top") && document.querySelector(".pm-card")){
      var t = document.createElement("div"); t.className = "pp-note pp-top"; t.innerHTML = "💳 <span><b>Pay by JazzCash or any bank app (Raast).</b> Choose an item, then tap <b>Pay by JazzCash</b> on your order and send the transaction ID.</span>";
      var c = document.querySelector(".pm-card"); c.parentNode.insertBefore(t, c);
    }
    [].forEach.call(document.querySelectorAll("[data-cancel]"), function(cb){
      var id = +cb.getAttribute("data-cancel"), wrap = cb.parentNode;
      if (wrap.querySelector('[data-pp="' + id + '"]')) return;
      var p = PROOFS[id], el;
      if (p && p.status === "pending"){ el = document.createElement("span"); el.className = "pp-st"; el.textContent = "⏳ Payment sent — being checked"; }
      else {
        el = document.createElement("button"); el.type = "button"; el.className = "pp-btn"; el.textContent = "💳 Pay by JazzCash";
        el.onclick = function(){ sheet(id, +cb.getAttribute("data-amount") || amountOf(cb)); };
        if (p && p.status === "rejected"){ var r = document.createElement("span"); r.className = "pp-st bad"; r.textContent = "Not confirmed: " + p.reason; r.setAttribute("data-pp", id); wrap.insertBefore(r, cb); }
      }
      el.setAttribute("data-pp", id); wrap.insertBefore(el, cb);
    });
  }
  var ORD = {}, KNOWN = {};   // a new pending order (just bought) opens the payment sheet by itself
  function amountOf(cb){ var id = +cb.getAttribute("data-cancel"); return ORD[id] || 0; }
  function load(){
    fetch("/api/shop/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
      if (!d) return; MODE = d.mode || ""; (d.orders || []).forEach(function(o){ ORD[o.id] = o.amount; KNOWN[o.id] = 1; });
      if (MODE !== "manual" || APP) { paint(); return; }
      return Promise.all([fetch("/api/payproof/info/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }),
                          fetch("/api/payproof/mine/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; })]).then(function(x){
        ACCT = x[0]; ((x[1] && x[1].proofs) || []).forEach(function(p){ if (!PROOFS[p.order] || PROOFS[p.order].id < p.id) PROOFS[p.order] = p; });
        paint();
      });
    }).catch(function(){});
  }
  function start(){
    load();
    if (window.MutationObserver) new MutationObserver(function(){ clearTimeout(start.t); start.t = setTimeout(function(){ paint(); if (MODE === "manual") fetch("/api/shop/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){ if (d) (d.orders || []).forEach(function(o){ ORD[o.id] = o.amount; if (!KNOWN[o.id]){ KNOWN[o.id] = 1; if (o.status === "pending" && ACCT && ACCT.enabled && !APP) sheet(o.id, o.amount); } }); }).catch(function(){}); }, 150); }).observe(document.body, {childList: true, subtree: true});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
