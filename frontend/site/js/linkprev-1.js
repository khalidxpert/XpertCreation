/* Link preview cards under XpertConnect posts: picture, site, title and description of the first link (setup_linkprev_v1). */
(function(){
  "use strict";
  var css = document.createElement("style");
  css.textContent = ".xlp{display:block;margin:10px 0 4px;border:1px solid var(--line,#E4E8F2);border-radius:14px;overflow:hidden;text-decoration:none!important;color:var(--ink,#0D1424)!important;background:var(--card,#fff)}"
    + ".xlp img{display:block;width:100%;max-height:320px;object-fit:cover;background:#EEF2F7}"
    + ".xlp .t{padding:10px 12px;background:var(--paper,#F6F8FC)}.xlp small{display:block;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-soft,#5A657C)}"
    + ".xlp b{display:block;font-size:15px;line-height:1.3;margin:3px 0;white-space:normal}.xlp span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:13.5px;line-height:1.45;color:var(--ink-soft,#5A657C);white-space:normal}";
  css.textContent += ".xlpv{position:relative;margin:10px auto 4px;max-width:340px;border-radius:16px;overflow:hidden;background:#000}.xlpv video{display:block;width:100%;aspect-ratio:9/16;max-height:560px;object-fit:cover;background:#000;cursor:pointer}.xlpv .snd{position:absolute;right:10px;top:10px;width:38px;height:38px;border-radius:50%;border:0;background:rgba(0,0,0,.55);color:#fff;font-size:17px;cursor:pointer}.xlpv .cap{position:absolute;left:0;right:0;bottom:0;padding:26px 12px 10px;background:linear-gradient(transparent,rgba(0,0,0,.75));color:#fff!important;font-weight:700;font-size:13.5px;text-decoration:none!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}";
  document.head.appendChild(css);
  var memo = {};
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function get(url){
    if (!memo[url]) memo[url] = fetch("/api/linkpreview/?url=" + encodeURIComponent(url), {credentials: "same-origin"})
      .then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; });
    return memo[url];
  }
  function add(el){
    if (el.getAttribute("data-xlp")) return;
    el.setAttribute("data-xlp", "1");
    var a = el.querySelector('a[href^="http"]'); if (!a) return;
    var after = el, n = el.nextElementSibling;
    while (n && (n.classList.contains("xtr") || n.classList.contains("xtro") || n.classList.contains("xtrm"))){ after = n; n = n.nextElementSibling; }
    if (n && n.classList.contains("fimgs")) return;        // the post has its own pictures
    var cm = /^https?:\/\/(?:www\.)?xpertcreation\.com\/clips\?(?:[^#]*&)?id=(\d+)/.exec(a.href);
    if (cm && window.IntersectionObserver){
      fetch("/api/clips/" + cm[1] + "/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }).then(function(c){
        if (!c || !c.video || el.parentNode.querySelector(".xlpv")) return;
        var box = document.createElement("div"); box.className = "xlpv";
        box.innerHTML = '<video src="' + esc(c.video) + '"' + (c.thumb ? ' poster="' + esc(c.thumb) + '"' : '') + ' playsinline muted loop preload="metadata"></video>'
          + '<button type="button" class="snd" aria-label="Sound">🔇</button>'
          + '<a class="cap" href="/clips?id=' + c.id + '">▶ XpertClips · @' + esc(c.username || c.user) + (c.caption ? ' — ' + esc(c.caption.slice(0, 80)) : '') + '</a>';
        var last = after; n = after.nextElementSibling;
        while (n && (n.classList.contains("xtr") || n.classList.contains("xtro") || n.classList.contains("xtrm"))){ last = n; n = n.nextElementSibling; }
        last.insertAdjacentElement("afterend", box);
        var v = box.querySelector("video"), s = box.querySelector(".snd");
        new IntersectionObserver(function(es){ es.forEach(function(x){ if (x.intersectionRatio >= .6){ var p = v.play(); if (p && p.catch) p.catch(function(){}); } else v.pause(); }); }, {threshold: [0, .6]}).observe(v);
        s.onclick = function(e){ e.stopPropagation(); v.muted = !v.muted; s.textContent = v.muted ? "🔇" : "🔊"; if (!v.muted) v.play(); };
        v.onclick = function(){ if (v.paused) v.play(); else v.pause(); };
      });
      return;
    }
    get(a.href).then(function(d){
      if (!d || !d.title || el.parentNode.querySelector(".xlp")) return;
      var card = document.createElement("a");
      card.className = "xlp"; card.href = d.url;
      if (!d.ours){ card.target = "_blank"; card.rel = "noopener nofollow ugc"; }
      card.innerHTML = (d.image ? '<img src="' + esc(d.image) + '" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">' : "")
        + '<div class="t"><small>' + esc(d.site || "") + '</small><b>' + esc(d.title) + '</b>' + (d.description ? "<span>" + esc(d.description) + "</span>" : "") + "</div>";
      var last = after; n = after.nextElementSibling;
      while (n && (n.classList.contains("xtr") || n.classList.contains("xtro") || n.classList.contains("xtrm"))){ last = n; n = n.nextElementSibling; }
      last.insertAdjacentElement("afterend", card);
    });
  }
  function scan(){ [].forEach.call(document.querySelectorAll(".fbody"), add); }
  new MutationObserver(scan).observe(document.body, {childList: true, subtree: true}); scan();
})();
