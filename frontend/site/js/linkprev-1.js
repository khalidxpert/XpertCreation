/* Link preview cards under XpertConnect posts: picture, site, title and description of the first link (setup_linkprev_v1). */
(function(){
  "use strict";
  var css = document.createElement("style");
  css.textContent = ".xlp{display:block;margin:10px 0 4px;border:1px solid var(--line,#E4E8F2);border-radius:14px;overflow:hidden;text-decoration:none!important;color:var(--ink,#0D1424)!important;background:var(--card,#fff)}"
    + ".xlp img{display:block;width:100%;max-height:320px;object-fit:cover;background:#EEF2F7}"
    + ".xlp .t{padding:10px 12px;background:var(--paper,#F6F8FC)}.xlp small{display:block;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-soft,#5A657C)}"
    + ".xlp b{display:block;font-size:15px;line-height:1.3;margin:3px 0;white-space:normal}.xlp span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:13.5px;line-height:1.45;color:var(--ink-soft,#5A657C);white-space:normal}";
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
