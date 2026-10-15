/* Pay by JazzCash / Raast for Freelance and Store orders.
   XCJazz.open(kind, ref, onDone)  kind: "freelance" (ref = order id) or "store" (ref = cart group).
   Shows the amount, our QR / Till ID / IBAN, then takes the transaction ID and a screenshot. */
(function(){
  if (window.XCJazz) return;
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-PK"); }
  var css = document.createElement("style");
  css.textContent = ".jc-sh{position:fixed;inset:0;z-index:9010;background:rgba(13,20,36,.55);display:flex;align-items:flex-end;justify-content:center}@media(min-width:700px){.jc-sh{align-items:center}}"
    + ".jc-sh .in{background:#fff;width:100%;max-width:480px;max-height:92vh;overflow:auto;border-radius:20px 20px 0 0;padding:16px;color:#0D1424;font-family:inherit;font-size:14px}@media(min-width:700px){.jc-sh .in{border-radius:20px}}"
    + ".jc-sh h3{margin:0 0 4px;font-size:19px}.jc-amt{font-size:30px;font-weight:900;letter-spacing:-.02em;margin:6px 0 2px}.jc-sub{font-size:13px;color:#5A657C}"
    + ".jc-qr{display:flex;justify-content:center;margin:12px 0;padding:10px;background:#FFFBEB;border-radius:16px}.jc-qr svg{width:200px;height:200px;background:#fff;border-radius:10px}"
    + ".jc-row{display:flex;align-items:center;gap:8px;padding:9px 0;border-top:1px solid #EEF2F7}.jc-row span{color:#5A657C;min-width:96px}.jc-row b{flex:1;word-break:break-all;font-family:ui-monospace,Menlo,monospace}"
    + ".jc-row button{border:1px solid #E2E8F0;background:#fff;border-radius:8px;padding:5px 9px;font:inherit;font-size:12px;font-weight:700;cursor:pointer}"
    + ".jc-steps{font-size:13.5px;line-height:1.55;padding-left:20px;margin:10px 0}"
    + ".jc-sh label.l{display:block;font-size:11px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:#5A657C;margin:10px 0 5px}"
    + ".jc-sh input[type=text]{width:100%;box-sizing:border-box;padding:11px 12px;border-radius:12px;border:1.5px solid #E4E8F2;font:inherit;font-size:15px;background:#F8FAFC}"
    + ".jc-file{display:block;text-align:center;padding:12px;border:1.5px dashed #CBD5E1;border-radius:12px;font-weight:800;cursor:pointer;color:#334155}"
    + ".jc-bt{display:flex;gap:8px;margin-top:12px}.jc-bt button{flex:1;padding:13px;border-radius:12px;border:0;font:inherit;font-weight:800;cursor:pointer}.jc-go{background:#C8102E;color:#fff}.jc-no{background:#F1F5F9;color:#0D1424}"
    + ".jc-msg{font-size:13px;font-weight:700;color:#B91C1C;margin-top:8px}.jc-box{border-radius:14px;padding:12px 14px;margin:10px 0;font-size:14px;line-height:1.5}.jc-box.wait{background:#FEF3C7;color:#92400E}.jc-box.bad{background:#FEE2E2;color:#991B1B}";
  document.head.appendChild(css);

  function done(sh, html){ sh.querySelector(".in").innerHTML = html + '<div class="jc-bt"><button type="button" class="jc-no">Close</button></div>'; }

  function open(kind, ref, onDone){
    var sh = document.createElement("div"); sh.className = "jc-sh";
    sh.innerHTML = '<div class="in"><h3>💳 Pay by JazzCash / Raast</h3><p class="jc-sub">Loading…</p></div>';
    document.body.appendChild(sh);
    var closed = false;
    function close(){ if (closed) return; closed = true; sh.remove(); if (onDone) onDone(); }
    sh.addEventListener("click", function(e){
      var c = e.target.closest("[data-copy]");
      if (c){ try { navigator.clipboard.writeText(c.getAttribute("data-copy")); } catch (er){} c.textContent = "Copied ✓"; return; }
      if (e.target === sh || e.target.classList.contains("jc-no")) close();
    });
    fetch("/api/payproof/pay/" + kind + "/" + encodeURIComponent(ref) + "/", {credentials: "same-origin"})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, d: d}; }); })
      .then(function(r){
        if (!r.ok){ done(sh, '<h3>💳 Pay by JazzCash</h3><div class="jc-box bad">' + esc(r.d.detail || "Could not open the payment.") + '</div>'); return; }
        var d = r.d, a = d.account || {}, p = d.proof;
        if (!a.enabled){ done(sh, '<h3>💳 Pay by JazzCash</h3><div class="jc-box bad">JazzCash payments are switched off right now.</div>'); return; }
        if (p && p.status === "pending"){ done(sh, '<h3>⏳ Payment being checked</h3><div class="jc-box wait">You sent <b>' + rs(p.amount) + '</b> (TID ' + esc(p.txn) + '). Our team is checking it and will switch your order on, usually within a few hours.</div>'); return; }
        if (!d.pending){ done(sh, '<h3>✅ Paid</h3><p>This order is not waiting for payment any more.</p>'); return; }
        var qr = "";
        if (a.qr && window.qrcode){ try { var q = qrcode(0, "M"); q.addData(a.qr); q.make(); qr = q.createSvgTag({cellSize: 4, margin: 2, scalable: true}); } catch (e){} }
        function row(l, v){ return v ? '<div class="jc-row"><span>' + l + '</span><b>' + esc(v) + '</b><button type="button" data-copy="' + esc(v) + '">Copy</button></div>' : ""; }
        sh.querySelector(".in").innerHTML = '<h3>💳 Pay by JazzCash / Raast</h3><div class="jc-amt">' + rs(d.amount) + '</div><div class="jc-sub">' + esc(d.label) + ' · pay this exact amount</div>'
          + (p && p.status === "rejected" ? '<div class="jc-box bad">Your last payment details were not confirmed: ' + esc(p.reason) + '. Please check and send again.</div>' : '')
          + (qr ? '<div class="jc-qr">' + qr + '</div><div class="jc-sub" style="text-align:center">Scan with JazzCash, EasyPaisa or any bank app (Raast QR)</div>' : '')
          + '<div style="margin-top:10px">' + row("Account title", a.title) + row("Till ID", a.till) + row("IBAN", a.iban) + row("Account no.", a.account) + '</div>'
          + '<ol class="jc-steps"><li>Send <b>' + rs(d.amount) + '</b> by scanning the QR, or to the Till ID / IBAN above.</li><li>If the app lets you add a note, write <b>' + esc(d.label) + '</b>.</li><li>Copy the transaction ID (TID) and take a screenshot.</li><li>Fill in below and tap Send. We check it and switch your order on, usually within a few hours. Your money is held safely until the work or delivery is done.</li></ol>'
          + (a.note ? '<p class="jc-sub">' + esc(a.note) + '</p>' : '')
          + '<label class="l">Transaction ID (TID)</label><input type="text" id="jctxn" maxlength="40" placeholder="e.g. 012345678901">'
          + '<label class="l">Paid from (name or number, optional)</label><input type="text" id="jcfrom" maxlength="60" placeholder="e.g. Ali Khan, 0300…">'
          + '<label class="l">Screenshot of the payment</label><label class="jc-file" id="jcfl"><span>📎 Choose screenshot</span><input type="file" id="jcfile" accept="image/*,application/pdf" hidden></label>'
          + '<div class="jc-msg" id="jcmsg"></div><div class="jc-bt"><button type="button" class="jc-no">Later</button><button type="button" class="jc-go">Send</button></div>';
        sh.querySelector("#jcfile").onchange = function(){ var f = this.files[0]; sh.querySelector("#jcfl span").textContent = f ? "✓ " + f.name : "📎 Choose screenshot"; };
        sh.querySelector(".jc-go").onclick = function(){
          var b = this, f = sh.querySelector("#jcfile").files[0], m = sh.querySelector("#jcmsg");
          if (sh.querySelector("#jctxn").value.replace(/\s/g, "").length < 6){ m.textContent = "Write the transaction ID (TID) from your JazzCash or bank message."; return; }
          if (!f){ m.textContent = "Add a screenshot of the payment."; return; }
          var fd = new FormData(); fd.append("txn", sh.querySelector("#jctxn").value); fd.append("sender", sh.querySelector("#jcfrom").value); fd.append("file", f);
          b.disabled = true; b.textContent = "Sending…";
          fetch("/api/payproof/pay/" + kind + "/" + encodeURIComponent(ref) + "/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}, body: fd})
            .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(x){ return {ok: r.ok, d: x}; }); })
            .then(function(r){
              if (!r.ok){ b.disabled = false; b.textContent = "Send"; m.textContent = r.d.detail || "Could not send."; return; }
              done(sh, '<h3>✅ Sent</h3><p style="font-size:15px;line-height:1.5">Thank you! The team will check your payment and switch your order on, usually within a few hours. You will get a notification.</p>');
            }).catch(function(){ b.disabled = false; b.textContent = "Send"; m.textContent = "Network problem. Try again."; });
        };
      }).catch(function(){ done(sh, '<h3>💳 Pay by JazzCash</h3><div class="jc-box bad">No internet. Try again.</div>'); });
  }
  window.XCJazz = {open: open};
})();
