/*
 * Service worker for XpertCreation.
 *
 * Pages are cached so the site opens without a connection. API responses are
 * not: a stale leaderboard or an out-of-date donor list is worse than an
 * honest "you are offline", and blood requests in particular must never be
 * answered from a cache.
 */
const VERSION = "xc-v82";
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
  var d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = {body: event.data ? event.data.text() : ""}; }
  event.waitUntil(self.registration.showNotification(d.title || "XpertCreation", {
    body: d.body || "", icon: "/brand/icon-512.png", badge: "/brand/logo-64.png",
    tag: d.tag || "xc", renotify: true, data: {url: d.url || "/"}
  }));
});
self.addEventListener("notificationclick", function(event){
  event.notification.close();
  var url = new URL((event.notification.data && event.notification.data.url) || "/", self.location.origin).href;
  event.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(function(list){
    for (var i = 0; i < list.length; i++){
      if (list[i].url === url && "focus" in list[i]) return list[i].focus();
    }
    return self.clients.openWindow ? self.clients.openWindow(url) : null;
  }));
});
