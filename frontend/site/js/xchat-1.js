/* Chat: edit and delete messages. Keeps edits / deletes in step on both sides while the chat is open. */
(function(){
  if (window.XCCHATX) return; window.XCCHATX = 1;
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function api(p, b){ var o = {credentials: "same-origin", headers: {}}; if (b !== undefined){ o.method = "POST"; o.headers["Content-Type"] = "application/json"; o.headers["X-CSRFToken"] = ck("xc_csrf"); o.body = JSON.stringify(b); }
    return fetch("/api/xsocial/" + p, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, d: d}; }); }); }
  function closePanel(){ var p = document.getElementById("panel3"); if (p) p.remove(); }
  function deletedHtml(el){ var mine = el.classList.contains("mine"), sm = el.querySelector("small"), when = sm ? sm.textContent.replace(/\s*·\s*edited/, "").replace(/[✓\s]+$/, "") : "";
    el.style.opacity = ".7"; el.innerHTML = '<div class="cb"><i>🚫 ' + (mine ? "You deleted this message" : "This message was deleted") + '</i></div><small>' + esc(when) + '</small>'; el.setAttribute("data-xdel", "1"); }
  function setBody(el, body){ var cb = el.querySelector(".cb"); if (cb) cb.textContent = body; var sm = el.querySelector("small"); if (sm && !/edited/.test(sm.textContent)) sm.insertAdjacentHTML("afterbegin", '<span class="xed">edited · </span>'); }
  document.addEventListener("click", function(e){
    var t = e.target.closest("[data-xedit],[data-xdelme],[data-xdelall]"); if (!t) return;
    var id = t.getAttribute("data-xedit") || t.getAttribute("data-xdelme") || t.getAttribute("data-xdelall"), el = document.querySelector('.msg8[data-mid="' + id + '"]');
    if (t.hasAttribute("data-xedit")){
      var cb = el && el.querySelector(".cb"), now = prompt("Edit your message:", cb ? cb.textContent : ""); if (now === null) return;
      api("msg/" + id + "/edit/", {body: now}).then(function(r){ closePanel(); if (!r.ok) return alert(r.d.detail || "Could not edit."); if (el) setBody(el, r.d.body); });
    } else if (t.hasAttribute("data-xdelme")){
      api("msg/" + id + "/delete/", {everyone: false}).then(function(r){ closePanel(); if (r.ok && el) el.remove(); });
    } else {
      if (!confirm("Delete this message for everyone?")) return;
      api("msg/" + id + "/delete/", {everyone: true}).then(function(r){ closePanel(); if (!r.ok) return alert(r.d.detail || "Could not delete."); if (el) deletedHtml(el); });
    }
  }, true);
  // keep edits / deletes from the other side in step
  setInterval(function(){
    if (document.hidden) return;
    var ids = [].map.call(document.querySelectorAll(".msg8[data-mid]:not([data-xdel])"), function(x){ return x.getAttribute("data-mid"); }).slice(-150);
    if (!ids.length) return;
    api("msg/states/?ids=" + ids.join(",")).then(function(r){
      var s = (r.d && r.d.states) || {};
      Object.keys(s).forEach(function(id){ var el = document.querySelector('.msg8[data-mid="' + id + '"]'), x = s[id]; if (!el) return;
        if (x.hidden) el.remove(); else if (x.deleted) deletedHtml(el); else if (x.edited){ var cb = el.querySelector(".cb"); if (cb && cb.textContent !== x.body) cb.textContent = x.body; setBody(el, x.body); } });
    });
  }, 5000);
})();
