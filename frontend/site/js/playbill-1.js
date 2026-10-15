/* Google Play Billing on the Promote page, only inside the Android app.
   Off until the server says it is switched on and Google returns the products. */
(function(){
  if (window.XCPBJS) return; window.XCPBJS = 1;
  function inApp(){
    try {
      if (/[?&]src=app/.test(location.search) || /^android-app:\/\//.test(document.referrer)) sessionStorage.setItem("xc_inapp", "1");
      return sessionStorage.getItem("xc_inapp") === "1" || (window.matchMedia && matchMedia("(display-mode: standalone)").matches);
    } catch (e){ return false; }
  }
  if (!inApp() || !("getDigitalGoodsService" in window) || !window.PaymentRequest) return;
  window.XCPB = "wait";                         // payproof-1.js waits instead of showing "Not available in the app"
  var SVC = null, CFG = null, PRICE = {}, busy = false;
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function post(u, b){ return fetch(u, {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify(b || {})})
    .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, s: r.status, d: d}; }); }); }
  function off(){ window.XCPB = "off"; var x = document.createElement("i"); document.body.appendChild(x); setTimeout(function(){ x.remove(); }, 50); }   // wake payproof up
  function fmt(p){ try { return new Intl.NumberFormat(navigator.language || "en", {style: "currency", currency: p.currency}).format(+p.value); } catch (e){ return p.currency + " " + p.value; } }
  function toast(t, bad){
    var n = document.getElementById("xcpbmsg");
    if (!n){ n = document.createElement("div"); n.id = "xcpbmsg"; n.style.cssText = "position:fixed;left:12px;right:12px;bottom:16px;z-index:9020;padding:13px 16px;border-radius:14px;font-weight:700;font-size:14px;box-shadow:0 10px 30px rgba(0,0,0,.25);text-align:center"; document.body.appendChild(n); }
    n.style.background = bad ? "#FEE2E2" : "#0D1424"; n.style.color = bad ? "#991B1B" : "#fff"; n.textContent = t; n.hidden = false;
    clearTimeout(toast.t); if (!/…$/.test(t)) toast.t = setTimeout(function(){ n.hidden = true; }, 6000);
  }
  function label(){
    [].forEach.call(document.querySelectorAll(".pm-buy[data-buy]"), function(b){
      var sku = ((CFG.skus[b.getAttribute("data-buy")] || {})[b.getAttribute("data-plan")] || "");
      if (b.getAttribute("data-pbsku") === sku) return;
      b.setAttribute("data-pbsku", sku);
      if (PRICE[sku]){ b.disabled = false; b.innerHTML = "&#9654; Buy with Google Play &middot; " + PRICE[sku]; }
      else { b.disabled = true; b.textContent = "Not available in the app yet"; }
    });
    [].forEach.call(document.querySelectorAll("[data-sim]"), function(b){ b.remove(); });
  }
  function verify(o, sku, token){
    return post("/api/playbill/verify/", {order: o, sku: sku, token: token});
  }
  function buy(b){
    if (busy) return; busy = true;
    var k = b.getAttribute("data-buy"), plan = b.getAttribute("data-plan"), sel = document.getElementById("tg_" + k), was = b.innerHTML;
    b.disabled = true; b.textContent = "Opening Google Play…";
    var done = function(){ busy = false; b.disabled = false; b.innerHTML = was; };
    post("/api/playbill/order/", {product: k, plan: plan, target: sel ? sel.value : null}).then(function(r){
      if (!r.ok){ done(); toast(r.d.detail || "Could not start the purchase.", true); return; }
      var oid = r.d.order, sku = r.d.sku;
      var req = new PaymentRequest([{supportedMethods: "https://play.google.com/billing", data: {sku: sku}}], {total: {label: "Total", amount: {currency: "PKR", value: "0"}}});
      var paid = false;
      return req.show().then(function(resp){
        var token = resp.details && resp.details.purchaseToken; paid = !!token;
        toast("Confirming your payment…");
        return verify(oid, sku, token).then(function(v){
          return resp.complete(v.ok ? "success" : "fail").then(function(){
            done();
            if (v.ok){ toast("Payment received - your item is now active."); setTimeout(function(){ location.href = "/promote?paid=" + v.d.order; }, 1200); }
            else toast(v.d.detail || "We could not confirm the payment. If you were charged, it will be checked again.", true);
          });
        });
      }).catch(function(e){
        done();
        if (paid){ toast("Your payment is being checked. Open this page again in a minute.", true); return; }
        post("/api/shop/orders/" + oid + "/cancel/");
        if (!(e && e.name === "AbortError")) toast("The purchase did not finish. Nothing was charged.", true);
      });
    }).catch(function(){ done(); toast("Network problem. Please try again.", true); });
  }
  function restore(){                             // a payment that finished while the app was closed
    if (!SVC.listPurchases) return;
    SVC.listPurchases().then(function(list){
      (list || []).forEach(function(p){ verify(null, p.itemId, p.purchaseToken).then(function(v){ if (v.ok && !v.d.already) toast("A finished Google Play payment was added to your account."); }); });
    }).catch(function(){});
  }
  document.addEventListener("click", function(e){
    if (window.XCPB !== "on") return;
    var b = e.target.closest && e.target.closest(".pm-buy[data-buy]"); if (!b) return;
    e.preventDefault(); e.stopImmediatePropagation(); buy(b);
  }, true);
  fetch("/api/playbill/config/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(c){
    if (!c || !c.enabled){ off(); return; }
    CFG = c;
    return window.getDigitalGoodsService("https://play.google.com/billing").then(function(s){
      SVC = s; var all = [];
      Object.keys(c.skus).forEach(function(k){ Object.keys(c.skus[k]).forEach(function(p){ all.push(c.skus[k][p]); }); });
      return s.getDetails(all);
    }).then(function(items){
      (items || []).forEach(function(it){ PRICE[it.itemId] = fmt(it.price); });
      if (!Object.keys(PRICE).length){ off(); return; }
      window.XCPB = "on"; label(); restore();
      new MutationObserver(function(){ clearTimeout(label.t); label.t = setTimeout(label, 60); }).observe(document.body, {childList: true, subtree: true});
    });
  }).catch(function(){ off(); });
})();
