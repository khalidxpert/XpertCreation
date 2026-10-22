/* Passkeys: sign in with fingerprint, face or screen lock (account.html sign-in screen + safety.html box). */
(function(){
  "use strict";
  if (!window.PublicKeyCredential || !navigator.credentials) return;
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function api(p, body, method){
    return fetch("/api/passkey/" + p, {method: method || "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: body === undefined || method === "GET" ? undefined : JSON.stringify(body || {})})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, s: r.status, d: d}; }); });
  }
  function b2a(s){ s = String(s).replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; var b = atob(s), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u.buffer; }
  function a2b(buf){ var u = new Uint8Array(buf), s = ""; for (var i = 0; i < u.length; i++) s += String.fromCharCode(u[i]); return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
  function why(e){
    var n = e && e.name;
    if (n === "NotAllowedError") return "Cancelled, or the time ran out. Try again.";
    if (n === "InvalidStateError") return "This device already has a passkey for your account.";
    if (n === "SecurityError") return "Passkeys only work on xpertcreation.com.";
    return (e && e.message) || "Something went wrong.";
  }

  function create(){
    return api("register/options/").then(function(r){
      if (!r.ok) throw new Error(r.d.detail || "Could not start.");
      var o = r.d; o.challenge = b2a(o.challenge); o.user.id = b2a(o.user.id);
      (o.excludeCredentials || []).forEach(function(c){ c.id = b2a(c.id); });
      return navigator.credentials.create({publicKey: o});
    }).then(function(c){
      var res = c.response;
      var cred = {id: c.id, rawId: a2b(c.rawId), type: c.type, authenticatorAttachment: c.authenticatorAttachment || null,
        clientExtensionResults: c.getClientExtensionResults ? c.getClientExtensionResults() : {},
        response: {clientDataJSON: a2b(res.clientDataJSON), attestationObject: a2b(res.attestationObject), transports: res.getTransports ? res.getTransports() : []}};
      return api("register/verify/", {credential: cred});
    }).then(function(r){ if (!r.ok) throw new Error(r.d.detail || "Could not save the passkey."); return r.d; });
  }

  function signin(){
    return api("login/options/").then(function(r){
      if (!r.ok) throw new Error(r.d.detail || "Could not start.");
      var o = r.d; o.challenge = b2a(o.challenge); (o.allowCredentials || []).forEach(function(c){ c.id = b2a(c.id); });
      return navigator.credentials.get({publicKey: o});
    }).then(function(c){
      var res = c.response;
      var cred = {id: c.id, rawId: a2b(c.rawId), type: c.type, authenticatorAttachment: c.authenticatorAttachment || null,
        clientExtensionResults: c.getClientExtensionResults ? c.getClientExtensionResults() : {},
        response: {clientDataJSON: a2b(res.clientDataJSON), authenticatorData: a2b(res.authenticatorData), signature: a2b(res.signature), userHandle: res.userHandle ? a2b(res.userHandle) : null}};
      return api("login/verify/", {credential: cred});
    }).then(function(r){ if (!r.ok) throw new Error(r.d.detail || "Could not sign in."); return r.d; });
  }
  window.XCPasskey = {create: create, signin: signin};

  // ---- sign-in screen (account.html): a "Sign in with a passkey" button under the normal one
  var card = document.getElementById("card");
  if (card){
    var put = function(){
      var b = card.querySelector('[data-a="login"]');
      if (!b || !document.getElementById("pass") || document.getElementById("pkgo")) return;
      var w = document.createElement("div");
      w.innerHTML = '<div style="display:flex;align-items:center;gap:10px;margin:14px 0 10px;color:#5A657C;font-size:13px"><span style="flex:1;height:1px;background:#E4E8F2"></span>or<span style="flex:1;height:1px;background:#E4E8F2"></span></div>'
        + '<button type="button" id="pkgo" style="width:100%;padding:14px;border-radius:14px;border:1.5px solid #0D1424;background:#fff;color:#0D1424;font:inherit;font-weight:800;font-size:15px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px">&#128273; Sign in with a passkey</button>'
        + '<p style="margin:6px 0 0;font-size:12.5px;color:#5A657C;text-align:center">Use your fingerprint, face or phone screen lock. No password.</p><div id="pkmsg" style="font-size:13.5px;margin-top:8px;text-align:center"></div>';
      b.parentNode.insertBefore(w, b.nextSibling);
    };
    new MutationObserver(put).observe(card, {childList: true, subtree: true}); put();
    card.addEventListener("click", function(e){
      var b = e.target.closest("#pkgo"); if (!b) return;
      e.stopPropagation();
      var m = document.getElementById("pkmsg"); b.disabled = true; m.style.color = "#5A657C"; m.textContent = "Waiting for your device…";
      signin().then(function(){
        m.style.color = "#166534"; m.textContent = "✔ Signed in.";
        var q = new URLSearchParams(location.search).get("next");
        location.href = q && /^https:\/\/[a-z0-9-]+\.xpertcreation\.com\//.test(q) ? q : "/feed";
      }).catch(function(err){ b.disabled = false; m.style.color = "#B91C1C"; m.textContent = why(err); });
    }, true);
  }

  // ---- safety page: list, add and remove passkeys
  var sfb = document.getElementById("sfb");
  if (sfb){
    var draw = function(box){
      api("mine/", undefined, "GET").then(function(r){
        if (!r.ok){ box.remove(); return; }
        var k = r.d.keys || [];
        box.innerHTML = '<h2>🔑 Passkeys</h2><p>Sign in with your fingerprint, face or phone screen lock instead of your password. A passkey stays on your device and can\'t be stolen like a password. Add one on each phone or computer you use.</p>'
          + (k.length ? k.map(function(x){ return '<div class="sf-row"><span class="l">🔑</span><a>' + esc(x.name) + ' <small style="color:#5A657C;font-weight:500">· added ' + new Date(x.created).toLocaleDateString() + (x.last_used ? ' · last used ' + new Date(x.last_used).toLocaleDateString() : '') + '</small></a><button data-pkdel="' + x.id + '">Remove</button></div>'; }).join("") : '<div class="sf-e">No passkeys yet.</div>')
          + '<div class="sf-in"><button class="sf-btn" id="pkadd">+ Add a passkey on this device</button></div><div class="sf-m" id="pkm"></div>';
      });
    };
    var add = function(){
      var two = document.getElementById("two");
      if (!two || document.getElementById("passkeys")) return;
      var box = document.createElement("div"); box.className = "sf-b"; box.id = "passkeys"; box.innerHTML = "<h2>🔑 Passkeys</h2><p>Loading…</p>";
      two.parentNode.insertBefore(box, two.nextSibling); draw(box);
      if (location.hash === "#passkeys") box.scrollIntoView();
    };
    new MutationObserver(add).observe(sfb, {childList: true}); add();
    sfb.addEventListener("click", function(e){
      var box = document.getElementById("passkeys"), m = document.getElementById("pkm");
      if (e.target.id === "pkadd"){
        e.target.disabled = true; m.style.color = "#5A657C"; m.textContent = "Follow the steps on your device…";
        create().then(function(){ draw(box); }).catch(function(err){ e.target.disabled = false; m.style.color = "#B91C1C"; m.textContent = why(err); });
      }
      var d = e.target.closest("[data-pkdel]");
      if (d && confirm("Remove this passkey? You can still sign in with your password.")){
        api(d.getAttribute("data-pkdel") + "/", {}, "DELETE").then(function(){ draw(box); });
      }
    });
  }
})();
