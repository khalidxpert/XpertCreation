/* Translate button under XpertConnect posts (.fbody) and group/channel messages (.msg8 .cb). */
(function(){
  "use strict";
  var QUICK = [["ur", "English \u2192 Urdu"], ["en", "Urdu \u2192 English"]];
  var MORE = [["ar", "Arabic"], ["hi", "Hindi"], ["pa", "Punjabi"], ["ps", "Pashto"], ["sd", "Sindhi"], ["fa", "Persian"], ["bn", "Bengali"], ["zh", "Chinese"],
              ["tr", "Turkish"], ["de", "German"], ["fr", "French"], ["es", "Spanish"], ["no", "Norwegian"], ["ru", "Russian"], ["id", "Indonesian"], ["ms", "Malay"]];
  var css = document.createElement("style");
  css.textContent = ".xtr{display:inline-block;margin:6px 0 2px;font-size:12.5px;font-weight:700;color:#1B4DFF;cursor:pointer;background:none;border:0;padding:0;font-family:inherit}"
    + ".xtrm{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}.xtrm button,.xtrm select{border:1.5px solid var(--line,#E4E8F2);background:var(--card,#fff);border-radius:99px;padding:5px 10px;font:inherit;font-size:12.5px;font-weight:700;cursor:pointer;color:inherit}"
    + ".xtro{margin:6px 0 2px;padding:8px 10px;border-radius:10px;background:var(--paper,#F1F4FA);font-size:14px;line-height:1.6;white-space:pre-wrap}.xtro small{display:block;color:var(--ink-soft,#5A657C);font-size:11.5px;margin-bottom:3px}";
  document.head.appendChild(css);
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
  function rtl(code){ return ["ur", "ar", "fa", "ps", "sd", "pa"].indexOf(code) >= 0; }
  function add(el){
    if (el.getAttribute("data-xtr") || (el.innerText || el.textContent || "").trim().length < 2) return;
    el.setAttribute("data-xtr", "1");
    var b = document.createElement("button"); b.type = "button"; b.className = "xtr"; b.textContent = "\uD83C\uDF10 Translate";
    el.insertAdjacentElement("afterend", b);
  }
  function scan(){ [].forEach.call(document.querySelectorAll(".fbody, .msg8 .cb"), add); }
  function run(btn, to, name){
    var src = btn.previousElementSibling; while (src && !src.matches(".fbody, .cb")) src = src.previousElementSibling;
    if (!src) return;
    try { localStorage.setItem("xc_tr_to", to); } catch (e) {}
    var box = btn.nextElementSibling && btn.nextElementSibling.classList.contains("xtro") ? btn.nextElementSibling : null;
    if (!box){ box = document.createElement("div"); box.className = "xtro"; btn.insertAdjacentElement("afterend", box); }
    box.innerHTML = "<small>Translating\u2026</small>"; var m = btn.parentNode.querySelector(".xtrm"); if (m) m.remove();
    fetch("/api/translate/", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify({text: (src.innerText || src.textContent || "").trim(), to: to})})
      .then(function(r){ return r.json().then(function(d){ return {ok: r.ok, d: d}; }); })
      .then(function(r){
        if (!r.ok){ box.innerHTML = "<small>" + esc(r.d.detail || "Could not translate.") + "</small>"; return; }
        box.setAttribute("dir", rtl(to) ? "rtl" : "ltr");
        box.innerHTML = "<small>Translated to " + esc(name) + " by AI \u00b7 may not be exact</small>" + esc(r.d.text);
        btn.textContent = "Show original"; btn.setAttribute("data-open", "1");
      }).catch(function(){ box.innerHTML = "<small>Could not translate. Check your connection.</small>"; });
  }
  document.addEventListener("click", function(e){
    var b = e.target.closest(".xtr");
    if (b){
      e.preventDefault(); e.stopPropagation();
      if (b.getAttribute("data-open")){ var o = b.nextElementSibling; if (o && o.classList.contains("xtro")) o.remove(); b.removeAttribute("data-open"); b.textContent = "\uD83C\uDF10 Translate"; return; }
      var old = b.parentNode.querySelector(".xtrm"); if (old){ old.remove(); return; }
      var last = ""; try { last = localStorage.getItem("xc_tr_to") || ""; } catch (x) {}
      var m = document.createElement("div"); m.className = "xtrm";
      m.innerHTML = QUICK.map(function(q){ return '<button type="button" data-to="' + q[0] + '" data-name="' + (q[0] === "ur" ? "Urdu" : "English") + '">' + q[1] + '</button>'; }).join("")
        + '<select aria-label="More languages"><option value="">More languages\u2026</option>' + MORE.map(function(q){ return '<option value="' + q[0] + '"' + (q[0] === last ? " selected" : "") + '>' + q[1] + '</option>'; }).join("") + '</select>';
      b.insertAdjacentElement("afterend", m); return;
    }
    var t = e.target.closest(".xtrm [data-to]");
    if (t){ e.preventDefault(); e.stopPropagation(); var bt = t.parentNode.previousElementSibling; run(bt, t.getAttribute("data-to"), t.getAttribute("data-name")); }
  }, true);
  document.addEventListener("change", function(e){
    var s = e.target.closest(".xtrm select"); if (!s || !s.value) return;
    run(s.parentNode.previousElementSibling, s.value, s.options[s.selectedIndex].text);
  });
  new MutationObserver(scan).observe(document.body, {childList: true, subtree: true}); scan();
})();
