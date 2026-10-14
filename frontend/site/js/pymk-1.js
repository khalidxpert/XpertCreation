/* People you may know: contacts, friends of friends, same company, same city. Renders into #pymk (home and Connect). */
(function(){
  if (window.XCPYMK) return; window.XCPYMK = 1;
  var KEY = "xc_pymk_hide";
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function hidden(){ try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e){ return []; } }
  var CSS = ".pymk{margin:6px 0 14px}.pymk .hd{display:flex;align-items:center;gap:8px;margin-bottom:8px}.pymk .hd b{font-size:16px}.pymk .hd a{margin-left:auto;font-size:12.5px;font-weight:800;color:#1B4DFF;text-decoration:none}"
    + ".pymk .row{display:flex;gap:10px;overflow-x:auto;scrollbar-width:none;padding:2px 2px 6px}.pymk .row::-webkit-scrollbar{display:none}"
    + ".pymk .c{position:relative;flex:0 0 148px;background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:18px;padding:14px 10px 12px;text-align:center}"
    + ".pymk .c img,.pymk .c .l{width:62px;height:62px;border-radius:50%;object-fit:cover;margin:0 auto 6px;display:grid;place-items:center;background:#EEF2FF;color:#1B4DFF;font-weight:900;font-size:24px}"
    + ".pymk .c b{display:block;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink,#0D1424)}"
    + ".pymk .c small{display:block;font-size:11.5px;color:var(--ink-soft,#5A657C);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-height:15px}"
    + ".pymk .c .w{color:#16A34A;font-weight:700}.pymk .c a.p{text-decoration:none;color:inherit;display:block}"
    + ".pymk .c button.cn{margin-top:8px;width:100%;border:0;border-radius:10px;padding:8px;background:#1B4DFF;color:#fff;font:inherit;font-weight:800;font-size:13px;cursor:pointer}"
    + ".pymk .c button.cn[disabled]{background:#E2E8F0;color:#334155;cursor:default}"
    + ".pymk .c .x{position:absolute;top:6px;right:6px;border:0;background:none;color:#94A3B8;font-size:16px;cursor:pointer;line-height:1}";
  function draw(el, list){
    var hide = hidden(); list = list.filter(function(p){ return p.slug && hide.indexOf(p.id) < 0; });
    if (!list.length){ el.innerHTML = ""; return; }
    if (!document.getElementById("pymkcss")){ var s = document.createElement("style"); s.id = "pymkcss"; s.textContent = CSS; document.head.appendChild(s); }
    el.innerHTML = '<div class="pymk"><div class="hd"><b>👥 People you may know</b><a href="/people#ffc">Find from contacts →</a></div><div class="row">'
      + list.map(function(p){ return '<div class="c" data-id="' + p.id + '"><button class="x" data-hide="' + p.id + '" aria-label="Hide">×</button><a class="p" href="/in/' + encodeURIComponent(p.slug) + '">'
        + (p.avatar ? '<img src="' + esc(p.avatar) + '" alt="" loading="lazy">' : '<span class="l">' + esc((p.name || "?").charAt(0)) + '</span>')
        + '<b>' + esc(p.name) + '</b><small>' + esc(p.headline || "") + '</small><small class="w">' + esc(p.why || "") + '</small></a>'
        + '<button class="cn" data-slug="' + esc(p.slug) + '">Connect</button></div>'; }).join("") + '</div></div>';
    el.onclick = function(e){
      var h = e.target.closest("[data-hide]");
      if (h){ var ids = hidden(); ids.push(+h.getAttribute("data-hide")); try { localStorage.setItem(KEY, JSON.stringify(ids.slice(-300))); } catch (er){} h.parentNode.remove(); if (!el.querySelector(".c")) el.innerHTML = ""; return; }
      var b = e.target.closest("[data-slug]"); if (!b) return;
      b.disabled = true; b.textContent = "Sending…";
      fetch("/api/network/in/" + encodeURIComponent(b.getAttribute("data-slug")) + "/connect/", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: "{}"})
        .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, d: d}; }); })
        .then(function(r){ b.textContent = r.ok ? "Request sent ✓" : "Connect"; if (!r.ok){ b.disabled = false; alert(r.d.detail || "Could not send the request."); } })
        .catch(function(){ b.disabled = false; b.textContent = "Connect"; });
    };
  }
  function start(){
    var el = document.getElementById("pymk"); if (!el) return;
    fetch("/api/find/suggest/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){ if (d && d.people) draw(el, d.people); }).catch(function(){});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
