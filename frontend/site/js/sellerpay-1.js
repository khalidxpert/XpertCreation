/* Pay the seller directly: JazzCash / EasyPaisa / bank / Raast details of a shop or restaurant, the buyer's screenshot
   upload, and the seller's "payment received" check. Used by the Store and Food delivery pages. XCSellerPay.* */
(function(){
  if (window.XCSellerPay) return;
  var css = document.createElement("style");
  css.textContent = ".xsp{border:1.5px solid #FDE68A;background:#FFFBEB;border-radius:16px;padding:14px;margin:12px 0;color:#0D1424;font-size:14.5px}.xsp h3{margin:0 0 6px;font-size:17px}"
    + ".xsp .amt{font-size:26px;font-weight:900;margin:2px 0 8px}.xsp .rw{display:flex;gap:8px;align-items:center;padding:8px 0;border-top:1px solid #FDE68A}.xsp .rw span{min-width:92px;color:#78350F;font-size:13px;font-weight:700}"
    + ".xsp .rw b{flex:1;word-break:break-all;font-family:ui-monospace,Menlo,monospace}.xsp .rw button,.xsp .sb{border:1px solid #E5E7EB;background:#fff;border-radius:9px;padding:6px 10px;font:inherit;font-size:12.5px;font-weight:800;cursor:pointer}"
    + ".xsp .qr{text-align:center;margin:8px 0}.xsp .qr img{max-width:220px;width:100%;border-radius:12px;background:#fff;border:1px solid #FDE68A}"
    + ".xsp label{display:block;font-size:12px;font-weight:800;color:#78350F;margin:10px 0 4px}.xsp input{width:100%;box-sizing:border-box;border:1.5px solid #E5E7EB;border-radius:11px;padding:10px;font:inherit;background:#fff}"
    + ".xsp .go{width:100%;margin-top:10px;border:0;border-radius:12px;padding:12px;font:inherit;font-weight:900;background:#C8102E;color:#fff;cursor:pointer}.xsp .go:disabled{opacity:.5}"
    + ".xsp .pf{display:flex;gap:10px;align-items:center;padding:8px 0;border-top:1px solid #FDE68A}.xsp .pf img{width:64px;height:64px;object-fit:cover;border-radius:10px;cursor:zoom-in}"
    + ".xsp .st{display:inline-block;padding:3px 8px;border-radius:99px;font-size:12px;font-weight:800}.xsp .st.pending{background:#FEF3C7;color:#92400E}.xsp .st.ok{background:#DCFCE7;color:#166534}.xsp .st.bad{background:#FEE2E2;color:#991B1B}"
    + ".xsp .m{padding:8px 10px;border-radius:10px;margin:8px 0;font-size:13.5px}.xsp .m.ok{background:#DCFCE7;color:#166534}.xsp .m.bad{background:#FEE2E2;color:#991B1B}.xsp .m.i{background:#EFF6FF;color:#1E3A8A}"
    + ".xspf h2{margin:0 0 6px}.xspf .g2{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:560px){.xspf .g2{grid-template-columns:1fr}}.xspf .bx{background:#fff;border:1px solid #E8EBF2;border-radius:16px;padding:14px;margin-bottom:10px}"
    + ".xspf label{display:block;font-weight:700;font-size:13px;margin:8px 0 4px}.xspf input,.xspf textarea{width:100%;box-sizing:border-box;border:1.5px solid #E8EBF2;border-radius:11px;padding:10px;font:inherit;background:#fff}";
  document.head.appendChild(css);
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var m = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return m ? m.pop() : ""; }
  function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-US"); }
  function api(u, body, method){
    var o = {credentials: "same-origin", headers: {}};
    if (body instanceof FormData){ o.method = "POST"; o.headers = {"X-CSRFToken": ck("xc_csrf")}; o.body = body; }
    else if (method === "DELETE"){ o.method = "DELETE"; o.headers = {"X-CSRFToken": ck("xc_csrf")}; }
    else if (body !== undefined){ o.method = "POST"; o.headers = {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}; o.body = JSON.stringify(body); }
    return fetch("/api/sellerpay/" + u, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, d: d}; }); })
      .catch(function(){ return {ok: false, d: {detail: "No internet. Try again."}}; });
  }
  function row(label, v, copy){ return v ? '<div class="rw"><span>' + label + '</span><b>' + esc(v) + '</b>' + (copy ? '<button type="button" data-cp="' + esc(v) + '">Copy</button>' : '') + '</div>' : ''; }
  var SP = {
    avail: function(kind, ids, cb){ api("avail/?kind=" + kind + (kind === "food" ? "&slug=" + encodeURIComponent(ids) : "&ids=" + ids.join(","))).then(function(r){ cb(r.ok ? r.d : {}); }); },
    // The pay box on an order. role "buyer": where to pay + upload; "seller": check the uploads.
    box: function(kind, oid, el, done){
      if (!el) return;
      el.removeAttribute("data-spbusy");
      api("order/" + kind + "/" + oid + "/").then(function(r){
        if (!r.ok){ el.innerHTML = ""; return; }
        var d = r.d, h = '<div class="xsp">';
        if (d.role === "buyer"){
          if (d.paid) h += '<h3>&#9989; Payment confirmed</h3><div>The seller confirmed your payment of <b>' + rs(d.amount) + '</b>.</div>';
          else if (!d.pay) h += '<h3>&#128179; Pay the seller</h3><div class="m bad">The seller has switched off JazzCash / bank payments. Contact them, or cancel and order again with another way to pay.</div>';
          else {
            var p = d.pay, wait = d.proofs.filter(function(x){ return x.status === "pending"; }).length;
            h += '<h3>&#128179; Pay the seller directly</h3><div style="font-size:13.5px;color:#78350F">Send exactly this amount from your JazzCash, EasyPaisa or bank app, then upload the screenshot below.</div><div class="amt">' + rs(d.amount) + '</div>'
              + (p.qr ? '<div class="qr"><img src="' + esc(p.qr) + '" alt="Payment QR code"><div style="font-size:12.5px;color:#78350F">Scan with your banking or wallet app</div></div>' : '')
              + row("JazzCash", p.jazzcash ? p.jazzcash + (p.jazzcash_name ? " (" + p.jazzcash_name + ")" : "") : "", false) + (p.jazzcash ? '<div style="text-align:right;margin-top:-6px"><button type="button" class="sb" data-cp="' + esc(p.jazzcash) + '">Copy number</button></div>' : '')
              + row("EasyPaisa", p.easypaisa ? p.easypaisa + (p.easypaisa_name ? " (" + p.easypaisa_name + ")" : "") : "", false) + (p.easypaisa ? '<div style="text-align:right;margin-top:-6px"><button type="button" class="sb" data-cp="' + esc(p.easypaisa) + '">Copy number</button></div>' : '')
              + row("Bank", p.bank, false) + row("Account title", p.title, false) + row("IBAN", p.iban, true) + row("Raast ID", p.raast, true) + (p.note ? '<div class="m i">' + esc(p.note) + '</div>' : '')
              + d.proofs.map(function(x){ return '<div class="pf"><span class="st ' + x.status + '">' + ({pending: "Waiting for the seller", ok: "Confirmed", bad: "Not received"})[x.status] + '</span><span>TID ' + esc(x.txn) + (x.reason ? '<br><small>' + esc(x.reason) + '</small>' : '') + '</span></div>'; }).join("")
              + (wait ? '<div class="m i">&#9203; Your screenshot was sent. The seller will check their account and confirm.</div>'
                : '<label>Transaction ID (TID)</label><input data-spf="txn" placeholder="From your payment SMS / app"><label>Paid from (name or number, optional)</label><input data-spf="sender"><label>Screenshot of the payment</label><input type="file" accept="image/*" data-spf="file"><button type="button" class="go" data-sgo="1">Send payment proof</button>')
              + '<div class="m i" style="font-size:12.5px">This money goes straight to the seller. XpertCreation does not hold it. Pay only for orders you have placed here.</div>';
          }
        } else {
          h += '<h3>&#128179; JazzCash / bank payment: ' + rs(d.amount) + '</h3>' + (d.paid ? '<div class="m ok">&#9989; You confirmed this payment.</div>' : '')
            + (d.proofs.length ? d.proofs.map(function(x){ return '<div class="pf">' + (x.shot ? '<a href="' + esc(x.shot) + '" target="_blank" rel="noopener"><img src="' + esc(x.shot) + '" alt="Screenshot"></a>' : '') + '<div style="flex:1"><span class="st ' + x.status + '">' + ({pending: "Check it", ok: "Received", bad: "Not received"})[x.status] + '</span> <b>' + rs(x.amount) + '</b><br><small>TID <b>' + esc(x.txn) + '</b>' + (x.sender ? ' &middot; from ' + esc(x.sender) : '') + '</small>' + (x.reason ? '<br><small>' + esc(x.reason) + '</small>' : '')
                + (x.status === "pending" ? '<div style="display:flex;gap:6px;margin-top:6px"><button type="button" class="sb" style="background:#16A34A;color:#fff;border-color:#16A34A" data-pok="' + x.id + '">&#10004; Money received</button><button type="button" class="sb" data-pbad="' + x.id + '">Not received</button></div>' : '') + '</div></div>'; }).join("")
              : '<div class="m i">&#9203; Waiting for the buyer to pay and upload the screenshot. Check your account before you send the order.</div>');
        }
        el.innerHTML = h + '<div data-spm></div></div>';
        el.onclick = function(e){
          e.stopPropagation();
          var c = e.target.closest("[data-cp]"); if (c){ var v = c.getAttribute("data-cp"); if (navigator.clipboard) navigator.clipboard.writeText(v).then(function(){ c.textContent = "Copied"; }); else prompt("Copy:", v); return; }
          var ok = e.target.closest("[data-pok]"), bad = e.target.closest("[data-pbad]");
          if (ok || bad){ var body = {}; if (bad){ var why = prompt("What is wrong? (the buyer sees this)", "The money did not reach our account."); if (why === null) return; body.reason = why; }
            api("proof/" + (ok || bad).getAttribute(ok ? "data-pok" : "data-pbad") + "/" + (ok ? "ok" : "bad") + "/", body).then(function(){ SP.box(kind, oid, el, done); if (done) done(); }); return; }
          if (e.target.closest("[data-sgo]")){
            var f = el.querySelector('[data-spf="file"]').files[0], m = el.querySelector("[data-spm]");
            if (!f){ m.innerHTML = '<div class="m bad">Choose the screenshot first.</div>'; return; }
            var fd = new FormData(); fd.append("file", f); fd.append("txn", el.querySelector('[data-spf="txn"]').value); fd.append("sender", el.querySelector('[data-spf="sender"]').value);
            e.target.disabled = true; m.innerHTML = '<div class="m i">Sending…</div>';
            api("order/" + kind + "/" + oid + "/", fd).then(function(x){ e.target.disabled = false; if (!x.ok){ m.innerHTML = '<div class="m bad">' + esc(x.d.detail || "Could not send.") + '</div>'; return; } SP.box(kind, oid, el, done); if (done) done(); });
          }
        };
        el.onchange = function(e){ if (e.target.getAttribute("data-spf") === "file") el.setAttribute("data-spbusy", "1"); };
        el.oninput = function(){ el.setAttribute("data-spbusy", "1"); };
      });
    },
    // The seller's settings: where buyers send money.
    settings: function(el){
      if (!el) return;
      api("me/").then(function(r){
        if (!r.ok){ el.innerHTML = '<p>Sign in first.</p>'; return; }
        var d = r.d, f = function(id, label, v, ph){ return '<label for="xs-' + id + '">' + label + '</label><input id="xs-' + id + '" value="' + esc(v) + '" placeholder="' + esc(ph || "") + '">'; };
        el.innerHTML = '<div class="xspf"><div class="bx"><h2>&#128179; Take payments in your own account</h2><p style="color:#5A657C;font-size:14px;margin:0 0 8px">Buyers can choose <b>JazzCash / bank</b> at checkout, pay you directly, and upload a screenshot. You check your account and tap <b>Money received</b>. XpertCreation does not hold this money and takes no cut.</p>'
          + '<label style="display:flex;gap:8px;align-items:center;font-size:15px"><input type="checkbox" id="xs-on"' + (d.on ? ' checked' : '') + ' style="width:auto"> Let buyers pay me by JazzCash / EasyPaisa / bank</label></div>'
          + '<div class="bx"><h2 style="font-size:16px">Mobile wallets</h2><div class="g2"><div>' + f("jc", "JazzCash number", d.jazzcash, "03001234567") + '</div><div>' + f("jcn", "JazzCash account name", d.jazzcash_name, "Name on the account") + '</div>'
          + '<div>' + f("ep", "EasyPaisa number", d.easypaisa, "03451234567") + '</div><div>' + f("epn", "EasyPaisa account name", d.easypaisa_name) + '</div></div></div>'
          + '<div class="bx"><h2 style="font-size:16px">Bank account</h2><div class="g2"><div>' + f("bk", "Bank", d.bank, "Meezan Bank") + '</div><div>' + f("tt", "Account title", d.title, "As written by the bank") + '</div></div>' + f("ib", "IBAN", d.iban, "PK36SCBL0000001123456702") + f("ra", "Raast ID (optional)", d.raast, "Your Raast ID or mobile number") + '</div>'
          + '<div class="bx"><h2 style="font-size:16px">QR code (optional)</h2><p style="color:#5A657C;font-size:13.5px;margin:0 0 6px">A picture of your JazzCash, EasyPaisa or Raast QR. Buyers can scan it to pay.</p>' + (d.qr ? '<img src="' + esc(d.qr) + '" alt="" style="width:160px;border-radius:12px;border:1px solid #E8EBF2;display:block;margin-bottom:6px"><button type="button" class="sb" id="xs-qrx" style="border:1px solid #E5E7EB;background:#fff;border-radius:9px;padding:6px 10px;font-weight:800;cursor:pointer">Remove QR</button> ' : '') + '<input type="file" accept="image/*" id="xs-qr" style="margin-top:6px"></div>'
          + '<div class="bx">' + f("nt", "Note for buyers (optional)", d.note, "e.g. Send the screenshot here; we ship after the money arrives") + '</div>'
          + '<div id="xs-m"></div><button type="button" id="xs-sv" style="border:0;border-radius:12px;padding:13px 22px;font:inherit;font-weight:900;background:#C8102E;color:#fff;cursor:pointer">Save payment details</button>'
          + '<p style="font-size:12.5px;color:#5A657C">Your details are shown only to buyers who choose this way to pay on an order with you.</p></div>';
        var m = function(t, k){ el.querySelector("#xs-m").innerHTML = '<div class="xsp" style="padding:0;border:0;background:none"><div class="m ' + k + '">' + t + '</div></div>'; };
        el.querySelector("#xs-sv").onclick = function(){
          var g = function(i){ return el.querySelector("#xs-" + i).value; };
          api("me/", {on: el.querySelector("#xs-on").checked, jazzcash: g("jc"), jazzcash_name: g("jcn"), easypaisa: g("ep"), easypaisa_name: g("epn"), bank: g("bk"), title: g("tt"), iban: g("ib"), raast: g("ra"), note: g("nt")})
            .then(function(x){ if (x.ok) m("&#10004; Saved." + (x.d.on ? " Buyers can now pay you directly." : " Direct payments are off."), "ok"); else m(esc(x.d.detail || "Could not save."), "bad"); });
        };
        el.querySelector("#xs-qr").onchange = function(){ if (!this.files[0]) return; var fd = new FormData(); fd.append("file", this.files[0]); api("me/qr/", fd).then(function(x){ if (x.ok) SP.settings(el); else m(esc(x.d.detail || "Could not upload."), "bad"); }); };
        var qx = el.querySelector("#xs-qrx"); if (qx) qx.onclick = function(){ api("me/qr/", undefined, "DELETE").then(function(){ SP.settings(el); }); };
      });
    }
  };
  window.XCSellerPay = SP;
})();
