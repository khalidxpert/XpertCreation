/* Notifications on this phone or computer: the "Turn on" bar, and subscribe / unsubscribe.
   Shows in any element with id="pushbar". */
(function(){
  "use strict";
  var bar = document.getElementById("pushbar");
  if (!bar) return;
  var ok = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  function cookie(n){ var m = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return m ? m.pop() : ""; }
  function post(p, body){
    return fetch("/api/notify/push/" + p, {method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-CSRFToken": cookie("xc_csrf")}, body: JSON.stringify(body || {})});
  }
  function b64(s){
    var pad = "=".repeat((4 - s.length % 4) % 4), raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
    var out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }
  function reg(){ return navigator.serviceWorker.register("/sw.js").then(function(){ return navigator.serviceWorker.ready; }); }
  function box(html){
    bar.innerHTML = html ? "<div style='display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0;padding:11px 14px;"
      + "border:1px solid var(--line,#E4E8F2);border-radius:14px;background:var(--card,#fff);font-size:14px'>" + html + "</div>" : "";
  }
  var BTN = "padding:7px 13px;border-radius:10px;font-weight:700;cursor:pointer;border:1px solid var(--line,#E4E8F2);";
  function draw(){
    if (!ok){ box(""); return; }
    if (Notification.permission === "denied"){ box("\uD83D\uDD15 Notifications are blocked for this site. Allow them in your browser's site settings to hear about new messages."); return; }
    reg().then(function(r){ return r.pushManager.getSubscription(); }).then(function(sub){
      if (sub && Notification.permission === "granted"){
        box(bar.getAttribute("data-quiet") ? "" : "\uD83D\uDD14 Notifications are on for this device. <span style='flex:1'></span>"
          + "<button data-push='test' style='" + BTN + "background:var(--card,#fff)'>Send a test</button>"
          + "<button data-push='off' style='" + BTN + "background:var(--card,#fff)'>Turn off</button>");
      } else {
        box("\uD83D\uDD14 Notifications on this device: new messages, connection requests and reminders, even when the site is closed. <span style='flex:1'></span>"
          + "<button data-push='on' style='" + BTN + "background:var(--brand,#1B4DFF);color:#fff;border-color:var(--brand,#1B4DFF)'>Turn on</button>");
      }
    }).catch(function(){ box(""); });
  }
  bar.addEventListener("click", function(e){
    var b = e.target.closest("[data-push]");
    if (!b) return;
    var what = b.getAttribute("data-push");
    b.disabled = true;
    if (what === "on"){
      Notification.requestPermission().then(function(p){
        if (p !== "granted") return draw();
        return fetch("/api/notify/push/key/").then(function(r){ return r.json(); }).then(function(k){
          if (!k.key) throw new Error("no key");
          return reg().then(function(r){ return r.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: b64(k.key)}); });
        }).then(function(sub){ return post("subscribe/", sub.toJSON()); }).then(draw);
      }).catch(function(){ b.disabled = false; alert("Could not turn on notifications on this device."); });
    } else if (what === "off"){
      reg().then(function(r){ return r.pushManager.getSubscription(); }).then(function(sub){
        if (!sub) return;
        return post("unsubscribe/", {endpoint: sub.endpoint}).then(function(){ return sub.unsubscribe(); });
      }).then(draw);
    } else if (what === "test"){
      post("test/").then(function(){ b.textContent = "Sent \u2713"; });
    }
  });
  fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ if (r.ok) draw(); }).catch(function(){});
})();
