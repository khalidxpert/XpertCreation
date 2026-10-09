/* XpertCreation ads: counts a view when a boosted post is at least half on screen for 1 second,
   and a click when a link or button inside it is used. Step 2 wires XCAds.watch(el, token) into the feed. */
(function(){
  if (window.XCAds) return;
  var sent = {};
  function send(path, t){
    var body = JSON.stringify({t: t});
    try { if (navigator.sendBeacon && navigator.sendBeacon(path, new Blob([body], {type: "application/json"}))) return; } catch (e) {}
    try { fetch(path, {method: "POST", credentials: "same-origin", keepalive: true, headers: {"Content-Type": "application/json"}, body: body}); } catch (e) {}
  }
  var io = ("IntersectionObserver" in window) ? new IntersectionObserver(function(list){
    list.forEach(function(en){
      var el = en.target, t = el.getAttribute("data-ad");
      if (!t || sent["v" + t]) return;
      var seen = en.intersectionRatio >= 0.5 || (en.isIntersecting && en.intersectionRect.height >= window.innerHeight * 0.5);
      if (seen) {
        if (!el._adTimer) el._adTimer = setTimeout(function(){ sent["v" + t] = 1; send("/api/ads/view/", t); io.unobserve(el); }, 1000);
      } else if (el._adTimer) { clearTimeout(el._adTimer); el._adTimer = null; }
    });
  }, {threshold: [0, 0.25, 0.5, 0.75, 1]}) : null;
  window.XCAds = {
    watch: function(el, t){
      if (!el || !t || !io || el.getAttribute("data-ad")) return;
      el.setAttribute("data-ad", t);
      io.observe(el);
      el.addEventListener("click", function(ev){
        if (sent["c" + t]) return;
        var a = ev.target && ev.target.closest ? ev.target.closest("a,button") : null;
        if (!a) return;
        sent["c" + t] = 1; send("/api/ads/click/", t);
      }, true);
    }
  };
})();
