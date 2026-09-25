/* Share buttons at the bottom of a page: the phone's own share sheet, WhatsApp, Facebook, X, LinkedIn,
   Telegram and Copy link. Uses the page's address at the moment of tapping, so tools opened with ?t=...
   share the right tool. */
(function(){
  "use strict";
  var host = document.querySelector(".wrap") || document.querySelector("main") || document.body;
  if (!host || document.getElementById("xshare")) return;
  var css = document.createElement("style");
  css.textContent = ".xshare{margin:22px 0 8px;padding:14px 16px;border:1px solid var(--line,#E4E8F2);border-radius:18px;background:var(--card,#fff)}" +
    ".xshare b{display:block;font-size:14px;margin-bottom:10px;color:var(--ink,#0D1424)}" +
    ".xshare .row{display:flex;gap:8px;flex-wrap:wrap}" +
    ".xshare a,.xshare button{display:inline-flex;align-items:center;gap:6px;padding:9px 13px;border-radius:11px;border:0;" +
    "font:inherit;font-size:13.5px;font-weight:700;color:#fff;text-decoration:none;cursor:pointer}" +
    ".xshare .wa{background:#25D366}.xshare .fb{background:#1877F2}.xshare .x{background:#111}" +
    ".xshare .li{background:#0A66C2}.xshare .tg{background:#229ED9}" +
    ".xshare .cp,.xshare .nat{background:var(--paper,#F6F7FB);color:var(--ink,#0D1424);border:1px solid var(--line,#E4E8F2)}";
  document.head.appendChild(css);
  var box = document.createElement("div");
  box.className = "xshare";
  box.id = "xshare";
  box.innerHTML = "<b>Share this page</b><div class='row'>"
    + (navigator.share ? "<button type='button' class='nat' data-s='native'>\u2197\uFE0F Share</button>" : "")
    + "<a class='wa' data-s='wa' href='#' target='_blank' rel='noopener'>WhatsApp</a>"
    + "<a class='fb' data-s='fb' href='#' target='_blank' rel='noopener'>Facebook</a>"
    + "<a class='x' data-s='x' href='#' target='_blank' rel='noopener'>X</a>"
    + "<a class='li' data-s='li' href='#' target='_blank' rel='noopener'>LinkedIn</a>"
    + "<a class='tg' data-s='tg' href='#' target='_blank' rel='noopener'>Telegram</a>"
    + "<button type='button' class='cp' data-s='copy'>\uD83D\uDD17 Copy link</button></div>";
  host.appendChild(box);
  box.addEventListener("click", function(e){
    var el = e.target.closest("[data-s]");
    if (!el) return;
    var url = location.href.split("#")[0], title = document.title.replace(/\s+\u2014\s+XpertCreation.*$/, "");
    var u = encodeURIComponent(url), t = encodeURIComponent(title);
    var links = {
      wa: "https://wa.me/?text=" + encodeURIComponent(title + " " + url),
      fb: "https://www.facebook.com/sharer/sharer.php?u=" + u,
      x: "https://x.com/intent/tweet?url=" + u + "&text=" + t,
      li: "https://www.linkedin.com/sharing/share-offsite/?url=" + u,
      tg: "https://t.me/share/url?url=" + u + "&text=" + t
    };
    var s = el.getAttribute("data-s");
    if (links[s]){ el.href = links[s]; return; }          // the link opens in a new tab by itself
    e.preventDefault();
    if (s === "native") navigator.share({title: title, url: url}).catch(function(){});
    if (s === "copy"){
      var done = function(){ el.textContent = "\u2713 Copied"; setTimeout(function(){ el.textContent = "\uD83D\uDD17 Copy link"; }, 1800); };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function(){ prompt("Copy this link:", url); });
      else prompt("Copy this link:", url);
    }
  });
})();
