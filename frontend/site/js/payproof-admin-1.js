/* Payments admin: JazzCash / Raast payments to check (approve / reject) and the account details people pay to. */
(function(){
  if (window.XCPPADMIN) return; window.XCPPADMIN = 1;
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-PK"); }
  function post(u, b){ return fetch(u, {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify(b || {})}).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, d: d}; }); }); }
  var st = document.createElement("style");
  st.textContent = ".ppa{margin-top:18px}.ppa h2{font-size:20px;margin:0 0 6px}.ppa .s{color:#5A657C;font-size:13.5px;margin:0 0 10px}"
    + ".ppa .tabs{display:flex;gap:6px;margin-bottom:10px}.ppa .tabs button{padding:7px 12px;border-radius:99px;border:1px solid #E4E8F2;background:#fff;font:inherit;font-weight:700;cursor:pointer}.ppa .tabs button.on{background:#0D1424;color:#fff}"
    + ".ppa .c{background:#fff;border:1px solid #E4E8F2;border-radius:16px;padding:12px 14px;margin-bottom:10px;display:grid;grid-template-columns:110px 1fr;gap:12px}"
    + "@media(max-width:560px){.ppa .c{grid-template-columns:1fr}}.ppa .c img{width:110px;height:150px;object-fit:cover;border-radius:10px;background:#F1F5F9;cursor:zoom-in}"
    + ".ppa .c b.a{font-size:20px}.ppa .c small{display:block;color:#5A657C}.ppa .c .bt{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}"
    + ".ppa .c .bt button{padding:9px 14px;border-radius:10px;border:0;font:inherit;font-weight:800;cursor:pointer}.ppa .ok{background:#16A34A;color:#fff}.ppa .no{background:#FEE2E2;color:#991B1B}"
    + ".ppa .tag{display:inline-block;font-size:12px;font-weight:800;padding:3px 8px;border-radius:99px;background:#FEF3C7;color:#92400E}.ppa .tag.approved{background:#DCFCE7;color:#166534}.ppa .tag.rejected{background:#FEE2E2;color:#991B1B}"
    + ".ppa .acct{background:#fff;border:1px solid #E4E8F2;border-radius:16px;padding:14px;margin-top:14px}.ppa .acct label{display:block;font-size:11px;font-weight:800;text-transform:uppercase;color:#5A657C;margin:8px 0 4px}"
    + ".ppa .acct input,.ppa .acct textarea{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:10px;border:1.5px solid #E4E8F2;font:inherit;font-size:14px}"
    + ".ppa .acct .r2{display:grid;grid-template-columns:1fr 1fr;gap:8px}";
  document.head.appendChild(st);
  var box = document.createElement("div"); box.className = "ppa"; box.id = "jazzcash";
  var host = document.getElementById("pa"); if (!host) return;
  host.parentNode.appendChild(box);
  var TAB = "pending";
  function load(){
    fetch("/api/payproof/team/?status=" + TAB, {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
      if (!d){ box.innerHTML = ""; return; }
      var a = d.account;
      box.innerHTML = '<h2>💳 JazzCash / Raast payments' + (d.waiting ? ' <span class="tag">' + d.waiting + ' to check</span>' : '') + '</h2>'
        + '<p class="s">Set the payments mode to <b>MANUAL</b> above so everyone can pay by JazzCash for Promote, Freelance and Store orders. Check each payment in the JazzCash Business app (amount and TID), then approve. Approving switches the item on and emails the receipt.</p>'
        + '<div class="tabs">' + [["pending", "To check"], ["approved", "Approved"], ["rejected", "Rejected"]].map(function(t){ return '<button data-t="' + t[0] + '" class="' + (TAB === t[0] ? "on" : "") + '">' + t[1] + '</button>'; }).join("") + '</div>'
        + (d.proofs.length ? d.proofs.map(function(p){
          return '<div class="c">' + (p.has_file ? '<a href="/api/payproof/file/' + p.id + '/" target="_blank"><img src="/api/payproof/file/' + p.id + '/" alt="screenshot" onerror="this.style.display=\'none\'"></a>' : '<div></div>')
            + '<div><b class="a">' + rs(p.amount) + '</b> <span class="tag ' + p.status + '">' + p.status + '</span>' + (p.amount !== p.order_amount ? ' <span class="tag rejected">order is ' + rs(p.order_amount) + '</span>' : '')
            + '<small><b>TID ' + esc(p.txn) + '</b>' + (p.sender ? ' · from ' + esc(p.sender) : '') + '</small><small>' + (p.kind === "promote" || !p.kind ? 'Promote order ' : '') + esc(p.order) + ' · ' + esc(p.item) + (p["for"] ? ' · for ' + esc(p["for"]) : '') + '</small>'
            + '<small>' + esc(p.user) + ' · ' + esc(p.email) + ' · ' + new Date(p.when).toLocaleString("en-PK") + '</small>' + (p.reason ? '<small>Reason: ' + esc(p.reason) + '</small>' : '')
            + (p.status === "pending" ? '<div class="bt"><button class="ok" data-ok="' + p.id + '">✓ Approve</button><button class="no" data-no="' + p.id + '">Reject</button></div>' : '') + '</div></div>'; }).join("")
          : '<p class="s">Nothing here.</p>')
        + '<div class="acct"><h2 style="font-size:17px">Account people pay to</h2>'
        + '<label><input type="checkbox" id="ppen"' + (a.enabled ? " checked" : "") + ' style="width:auto"> JazzCash payments switched on</label>'
        + '<div class="r2"><div><label>Account title</label><input id="ppt" value="' + esc(a.title) + '"></div><div><label>Bank / wallet</label><input id="ppb" value="' + esc(a.bank) + '"></div></div>'
        + '<div class="r2"><div><label>Till ID</label><input id="ppl" value="' + esc(a.till) + '"></div><div><label>Account number</label><input id="ppa" value="' + esc(a.account) + '"></div></div>'
        + '<label>IBAN</label><input id="ppi" value="' + esc(a.iban) + '"><label>QR code text (from the JazzCash Business QR)</label><textarea id="ppq" rows="3">' + esc(a.qr) + '</textarea>'
        + '<label>Note for buyers (optional)</label><input id="ppn" value="' + esc(a.note) + '" placeholder="e.g. Payments are checked 9 am - 11 pm">'
        + '<p><button class="ok" id="ppsave" style="padding:10px 16px;border-radius:10px;border:0;font-weight:800;cursor:pointer;margin-top:10px">Save</button> <span id="ppmsg" class="s"></span></p></div>';
    });
  }
  box.addEventListener("click", function(e){
    var t = e.target.closest("[data-t]"); if (t){ TAB = t.getAttribute("data-t"); load(); return; }
    var ok = e.target.closest("[data-ok]");
    if (ok){ if (!confirm("You checked the JazzCash app and this money arrived?")) return; ok.disabled = true; post("/api/payproof/team/" + ok.getAttribute("data-ok") + "/approve/").then(function(r){ if (!r.ok) alert(r.d.detail || "Could not approve."); load(); }); return; }
    var no = e.target.closest("[data-no]");
    if (no){ var why = prompt("Why? The buyer sees this (e.g. TID not found, amount is less)"); if (!why) return; post("/api/payproof/team/" + no.getAttribute("data-no") + "/reject/", {reason: why}).then(function(r){ if (!r.ok) alert(r.d.detail || "Could not reject."); load(); }); return; }
    if (e.target.id === "ppsave"){
      post("/api/payproof/team/account/", {enabled: document.getElementById("ppen").checked, title: document.getElementById("ppt").value, bank: document.getElementById("ppb").value,
        till: document.getElementById("ppl").value, account: document.getElementById("ppa").value, iban: document.getElementById("ppi").value, qr: document.getElementById("ppq").value, note: document.getElementById("ppn").value})
        .then(function(r){ document.getElementById("ppmsg").textContent = r.ok ? "Saved ✓" : (r.d.detail || "Could not save."); });
    }
  });
  load();
})();
