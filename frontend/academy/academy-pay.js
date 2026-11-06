/* XpertAcademy paid courses (setup_academy_pay_v1): lock screen, buy (card / wallet or JazzCash), coupons, coupon requests.
   The academy page calls XAPay.locked() / XAPay.wall() / XAPay.after() from its render(). */
(function(){
"use strict";
var A = {loaded: false, paywall: false, courses: {}, price: 0, signed_in: false, ask: {}}, last = 0, busy = false;
function esc(s){ var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
function csrf(){ var m = document.cookie.match(/(?:^|;)\s*xc_csrf=([^;]+)/); return m ? decodeURIComponent(m[1]) : ""; }
function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-US"); }
function post(url, body, form){
  var o = {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": csrf()}};
  if (form) o.body = form; else { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(body || {}); }
  return fetch(url, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(j){ if (!r.ok) throw new Error(j.detail || "Please try again."); return j; }); });
}
function rerender(){ try { window.dispatchEvent(new PopStateEvent("popstate")); } catch(e){} }
function load(force){
  if (busy || (!force && Date.now() - last < 20000)) return;
  busy = true;
  fetch("/api/tgacademy/access/", {credentials: "same-origin"}).then(function(r){ return r.json(); }).then(function(j){
    var was = JSON.stringify([A.paywall, A.courses, A.signed_in]);
    A.loaded = true; A.paywall = !!j.paywall; A.courses = j.courses || {}; A.price = j.price; A.signed_in = !!j.signed_in; A.ask = j.ask_text || {};
    last = Date.now(); busy = false;
    if (JSON.stringify([A.paywall, A.courses, A.signed_in]) !== was) rerender();
  }).catch(function(){ busy = false; });
}
function locked(slug){ var c = A.courses[slug]; return A.paywall && !!c && !c.open; }

function wall(c, name){
  var slug = c.id, info = A.courses[slug] || {};
  var h = '<div class="xapay" data-xaslug="' + esc(slug) + '" style="--accent:' + esc(c.accent || "#1B4DFF") + '">'
    + '<div class="xa-ic">🔒</div><h2>' + esc(name || slug) + '</h2>'
    + '<p class="xa-lead">This course is <b>' + rs(A.price) + '</b> (about $15) — pay once, keep it for life, with the quiz and the certificate.</p>';
  var pay = info.pay || null;
  if (pay && pay.status === "pending"){
    return '<div class="xapay" data-xaslug="' + esc(slug) + '" style="--accent:' + esc(c.accent || "#1B4DFF") + '">'
      + '<div class="xa-ic">⏳</div><h2>' + esc(name || slug) + '</h2>'
      + '<div class="xa-pend"><b>Your payment is being checked</b><div>JazzCash / Raast · TID <b>' + esc(pay.txn) + '</b> · sent ' + when(pay.when) + '</div>'
      + '<p>The course opens as soon as our team approves it — you will get a 🔔 notification. Usually within a few hours.</p>'
      + '<p class="xa-ur" lang="ur" dir="rtl">آپ کی ادائیگی چیک ہو رہی ہے۔ منظوری کے بعد کورس کھل جائے گا اور آپ کو اطلاع ملے گی۔</p></div>'
      + '<details class="xa-cp"><summary>Wrong details? Send them again</summary><div class="xa-btns"><button class="primary" data-xa="buy">💳 Pay again / send new details</button></div><div class="xa-pay" hidden></div></details>'
      + '<div class="xa-out"></div></div>';
  }
  if (pay && pay.status === "rejected"){
    h += '<div class="xa-rej">❌ Your last payment (TID ' + esc(pay.txn) + ') was not approved' + (pay.reason ? ': ' + esc(pay.reason).replace(/\.?$/, '.') : '.') + ' Please pay again or contact support.</div>';
  }
  if (!A.signed_in){
    h += '<button class="primary" data-act="signin">Sign in to buy or use a coupon</button>';
  } else {
    h += '<div class="xa-btns"><button class="primary" data-xa="buy">💳 Buy this course</button></div><div class="xa-pay" hidden></div>'
      + '<details class="xa-cp"><summary>🎟 I have a coupon</summary><div class="xa-row"><input class="xa-code" maxlength="24" placeholder="Coupon code" autocapitalize="characters"><button data-xa="redeem">Open course</button></div></details>';
  }
  h += '<div class="xa-ask"><p>' + esc(A.ask.en || "Can't pay? Ask the admin for a free coupon code.") + '</p><p class="xa-ur" lang="ur" dir="rtl">' + esc(A.ask.ur || "") + '</p>';
  if (A.signed_in){
    h += info.asked === "open" ? '<p class="xa-ok">✓ Request sent — the admin will reply in your notifications 🔔</p>'
      : '<textarea class="xa-msg" maxlength="400" placeholder="Why do you need it? (optional)"></textarea><button data-xa="ask">🙏 Request a coupon</button>';
  }
  h += '</div><div class="xa-out"></div></div>';
  return h;
}
function when(iso){ try { return new Date(iso).toLocaleString("en-GB", {day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"}); } catch(e){ return ""; } }
function out(box, t, ok){ var o = box.querySelector(".xa-out"); if (o){ o.textContent = t; o.className = "xa-out " + (ok ? "ok" : "err"); } }

function jazz(box, order){
  var p = box.querySelector(".xa-pay");
  fetch("/api/payproof/info/", {credentials: "same-origin"}).then(function(r){ return r.json(); }).then(function(a){
    p.innerHTML = '<div class="xa-jc"><b>Pay ' + rs(order.amount) + ' by JazzCash / Raast</b>'
      + (a.title ? '<div>To: <b>' + esc(a.title) + '</b> (' + esc(a.bank || "") + ')</div>' : "")
      + (a.till ? '<div>Till ID: <b>' + esc(a.till) + '</b></div>' : "") + (a.account ? '<div>Account: <b>' + esc(a.account) + '</b></div>' : "")
      + (a.iban ? '<div>IBAN: <b>' + esc(a.iban) + '</b></div>' : "") + (a.note ? '<div class="xa-note">' + esc(a.note) + '</div>' : "")
      + '<p>Then send the transaction ID (TID) and a screenshot. The course opens when our team checks it (you get a 🔔).</p>'
      + '<input class="xa-tid" maxlength="40" placeholder="Transaction ID (TID)"><input class="xa-from" maxlength="60" placeholder="Paid from (name or number)">'
      + '<input class="xa-shot" type="file" accept="image/*,application/pdf"><button class="primary" data-xa="sendjc" data-order="' + order.id + '">Send payment details</button></div>';
    p.hidden = false;
  });
}

document.addEventListener("click", function(e){
  var b = e.target.closest && e.target.closest("[data-xa]"); if (!b) return;
  var box = b.closest(".xapay"); if (!box) return;
  var slug = box.getAttribute("data-xaslug"), a = b.getAttribute("data-xa");
  e.preventDefault(); b.disabled = true;
  var done = function(){ b.disabled = false; }, fail = function(x){ out(box, x.message, false); done(); };
  if (a === "buy"){
    post("/api/tgacademy/buy/" + encodeURIComponent(slug) + "/").then(function(j){
      var p = box.querySelector(".xa-pay");
      p.innerHTML = (j.checkout ? '<a class="primary xa-a" href="' + esc(j.checkout) + '">Pay ' + rs(j.amount) + ' by card / wallet</a>' : "")
        + (j.jazzcash ? '<button data-xa="jc" data-order="' + j.order.id + '" data-amount="' + j.amount + '">Pay by JazzCash / Raast</button>' : "");
      p.hidden = false; p.style.display = ""; b.style.display = "none";
      if (!j.checkout && j.jazzcash) jazz(box, {id: j.order.id, amount: j.amount});
    }).catch(fail);
  } else if (a === "jc"){
    jazz(box, {id: b.getAttribute("data-order"), amount: b.getAttribute("data-amount")});
  } else if (a === "sendjc"){
    var f = new FormData(), file = box.querySelector(".xa-shot").files[0];
    f.append("txn", box.querySelector(".xa-tid").value); f.append("sender", box.querySelector(".xa-from").value); if (file) f.append("file", file);
    post("/api/payproof/orders/" + b.getAttribute("data-order") + "/", null, f).then(function(){
      box.querySelector(".xa-pay").innerHTML = '<p class="xa-ok">✓ Payment details sent. We will open the course after checking — you will get a notification 🔔</p>';
      var tid = box.querySelector(".xa-tid"); A.courses[slug] = A.courses[slug] || {};
      A.courses[slug].pay = {status: "pending", txn: f.get("txn"), when: new Date().toISOString()};
      setTimeout(function(){ load(true); rerender(); }, 2500);
    }).catch(fail);
  } else if (a === "redeem"){
    post("/api/tgacademy/redeem/", {code: box.querySelector(".xa-code").value, course: slug}).then(function(){ out(box, "✓ Course opened!", true); load(true); }).catch(fail);
  } else if (a === "ask"){
    var m = box.querySelector(".xa-msg");
    post("/api/tgacademy/ask/", {course: slug, message: m ? m.value : ""}).then(function(){ (A.courses[slug] || {}).asked = "open"; rerender(); }).catch(fail);
  } else done();
});

/* after every academy render: lock badges on the course cards, lock screen on the course page */
function after(view, app, course){
  load(false);
  if (!A.paywall) return;
  if (view.page === "home"){
    [].forEach.call(app.querySelectorAll("[data-course]"), function(card){
      var sl = card.getAttribute("data-course"), pi = (A.courses[sl] || {}).pay;
      if (locked(sl) && !card.querySelector(".xa-badge")) card.insertAdjacentHTML("beforeend", pi && pi.status === "pending"
        ? '<span class="xa-badge xa-wait">⏳ Payment pending</span>' : '<span class="xa-badge">🔒 ' + rs(A.price) + "</span>");
    });
  }
  if (view.page === "course" && locked(view.c) && !app.querySelector(".xapay")){
    var cta = app.querySelector(".cta"); if (cta) cta.hidden = true;
    var hero = app.querySelector(".chero");
    var c = course || {id: view.c};
    if (hero) hero.insertAdjacentHTML("afterend", wall(c, (hero.querySelector("h2") || {}).textContent));
    [].forEach.call(app.querySelectorAll(".llist [data-lesson]"), function(x){ x.removeAttribute("data-lesson"); x.style.opacity = ".6"; });
  }
}

var css = document.createElement("style");
css.textContent = ".xapay{background:#fff;border:1px solid #E4E8F2;border-radius:18px;padding:20px;margin:16px 0;text-align:center;box-shadow:0 6px 24px rgba(13,20,36,.06)}"
  + ".xapay .primary,.xapay a.xa-a{background:var(--accent,#1B4DFF)!important;color:#fff!important;border:0!important;font-weight:700;border-radius:12px;padding:12px 18px}.xapay [hidden]{display:none!important}"
  + ".xapay h2{margin:6px 0}.xa-ic{font-size:34px}.xa-lead{color:#5A657C;margin:6px 0 14px}.xapay .primary,.xapay .xa-a{display:inline-block;margin:6px 4px;text-decoration:none}"
  + ".xapay button{font:inherit;cursor:pointer;border-radius:12px;padding:11px 16px;border:1px solid #CBD5E1;background:#fff;margin:6px 4px}"
  + ".xapay input,.xapay textarea{font:inherit;width:100%;max-width:420px;padding:11px;border:1px solid #CBD5E1;border-radius:12px;margin:6px auto;display:block;box-sizing:border-box}"
  + ".xa-cp{margin-top:10px}.xa-cp summary{cursor:pointer;font-weight:600;color:var(--accent,#1B4DFF)}.xa-row{display:flex;gap:6px;justify-content:center;flex-wrap:wrap}.xa-row input{max-width:220px;margin:6px 0}"
  + ".xa-ask{margin-top:16px;padding-top:14px;border-top:1px dashed #E4E8F2}.xa-ask p{margin:4px 0}.xa-ur{font-family:'Noto Nastaliq Urdu',serif;font-size:17px;line-height:2}"
  + ".xa-ok{color:#047857;font-weight:600}.xa-out.ok{color:#047857;font-weight:600}.xa-out.err{color:#B91C1C}.xa-jc{text-align:left;max-width:440px;margin:10px auto;background:#F6F7FB;border-radius:14px;padding:14px;line-height:1.7}.xa-note{color:#5A657C;font-size:13px}"
  + ".xa-pend{background:#FFF8E6;border:1px solid #F3D27A;border-radius:14px;padding:14px;margin:8px auto;max-width:460px;line-height:1.6}.xa-pend p{margin:8px 0 0;color:#5A657C}"
  + ".xa-rej{background:#FEF2F2;border:1px solid #FCA5A5;color:#B91C1C;border-radius:12px;padding:10px 12px;margin:8px auto 12px;max-width:460px}.xa-badge.xa-wait{background:#F59E0B;color:#111}"
  + ".xa-badge{display:inline-block;margin-top:6px;font-size:12px;font-weight:700;padding:3px 9px;border-radius:99px;background:#0D1424;color:#FEBD19}";
document.head.appendChild(css);
window.XAPay = {locked: locked, wall: wall, after: after, load: load};
load(true);
})();
