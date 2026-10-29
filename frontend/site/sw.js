/*
 * Service worker for XpertCreation.
 *
 * Pages are cached so the site opens without a connection. API responses are
 * not: a stale leaderboard or an out-of-date donor list is worse than an
 * honest "you are offline", and blood requests in particular must never be
 * answered from a cache.
 */
const VERSION = "xc-v355";
const SHELL = VERSION + "-shell";

// Pages worth having offline. Each is small and self-contained.
const PAGES = [
  "/",
  "/games",
  "/zodiac",
  "/vibe",
  "/typing",
  "/blood",
  "/birthdays",
  "/weather",
  "/account",
  "/privacy",
  "/terms",
  "/offline",
  "/nearby",
  "/js/jsqr-1.js",
  "/brand/logo-64.png",
  "/brand/icon-192.png",
  "/brand/icon-512.png",
  "/brand/favicon-v2.ico",
  "/brand/vibes.json",
  "/brand/zodiac.json"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(SHELL).then(function (cache) {
      // addAll fails the whole install if one file 404s, so they go in
      // individually and a missing one is simply skipped.
      return Promise.all(PAGES.map(function (url) {
        return cache.add(url).catch(function () { return null; });
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(names.map(function (n) {
        return n.startsWith(VERSION) ? null : caches.delete(n);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // Never serve the API from a cache. A donor list, a leaderboard or a session
  // check answered from disk would be quietly wrong.
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(req).catch(function () {
        return new Response(
          JSON.stringify({ detail: "You are offline." }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        );
      })
    );
    return;
  }

  // Pages: network first, so a signed-in visitor sees the live version, with
  // the cache as a fallback when there is nothing.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).then(function (res) {
        const copy = res.clone();
        caches.open(SHELL).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match("/offline") || caches.match("/");
        });
      })
    );
    return;
  }

  // Everything else: cache first. Fonts, icons and JSON do not change often.
  event.respondWith(
    caches.match(req).then(function (hit) {
      return hit || fetch(req).then(function (res) {
        if (res && res.status === 200 && res.type === "basic") {
          const copy = res.clone();
          caches.open(SHELL).then(function (c) { c.put(req, copy); });
        }
        return res;
      });
    }).catch(function () { return caches.match("/offline"); })
  );
});

/* ---- push notifications: show them, and open the right page when tapped ---- */
self.addEventListener("push", function(event){
  var d = {}, R = self.registration;
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = {body: event.data ? event.data.text() : ""}; }
  if (d.call){                        /* a call ringing: stays on screen, long vibration, Answer / Decline */
    var tag = d.tag || ("xc-call-" + d.call), at = Date.now();
    event.waitUntil(R.showNotification(d.title || "Incoming call", {
      body: d.body || "", icon: "/brand/icon-512.png", badge: "/brand/badge-96.png", tag: tag, renotify: true,
      requireInteraction: true, silent: false, timestamp: at, vibrate: [900, 400, 900, 400, 900, 400, 900],
      actions: [{action: "answer", title: d.video ? "Answer video" : "Answer"}, {action: "decline", title: "Decline"}],
      data: {url: d.url || "/", call: d.call, dec: d.dec || "", at: at}
    }).then(function(){ return new Promise(function(ok){ setTimeout(ok, 30000); }); }).then(function(){
      return R.getNotifications({tag: tag}).then(function(ns){ ns.forEach(function(n){ if (n.data && n.data.at === at) n.close(); }); });
    }).catch(function(){}));
    return;
  }
  var clear = d.kind === "call" ? R.getNotifications().then(function(ns){ ns.forEach(function(n){ if (n.tag && n.tag.indexOf("xc-call-") === 0) n.close(); }); }).catch(function(){}) : Promise.resolve();
  event.waitUntil(clear.then(function(){ return R.showNotification(d.title || "XpertCreation", {
    body: d.body || "", icon: "/brand/icon-512.png", badge: "/brand/badge-96.png",
    tag: d.tag || "xc", renotify: true, data: {url: d.url || "/"}
  }); }));
});
self.addEventListener("notificationclick", function(event){
  var nd = event.notification.data || {};
  if (event.action === "decline" && nd.call){
    event.notification.close();
    event.waitUntil(fetch("/api/calls/" + nd.call + "/decline-push/", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({t: nd.dec || ""})}).catch(function(){}));
    return;
  }
  event.notification.close();
  var url = new URL((event.notification.data && event.notification.data.url) || "/", self.location.origin).href;
  event.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(function(list){
    for (var i = 0; i < list.length; i++){
      if (list[i].url === url && "focus" in list[i]) return list[i].focus();
    }
    return self.clients.openWindow ? self.clients.openWindow(url) : null;
  }));
});
