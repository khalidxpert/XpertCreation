/* Footer numbers: members, countries, online now, newest members.
   Reads /api/auth/footer-stats/ - public, cached for a minute on the server. */
(function(){
  var box = document.getElementById("xcstats");
  if (!box || !window.fetch) return;

  var css = document.createElement("style");
  css.textContent =
    ".xcstats{margin:18px 0 6px;padding-top:14px;border-top:1px solid rgba(127,127,127,.25);font-size:14px}" +
    ".xcstats .xs-row{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center}" +
    ".xcstats .xs-big{font-weight:700}" +
    ".xcstats .xs-on{color:#00B37E;font-weight:600}" +
    ".xcstats .xs-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#00B37E;" +
      "margin-right:6px;vertical-align:1px;animation:xsPulse 2s infinite}" +
    ".xcstats .xs-flags{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}" +
    ".xcstats .xs-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:999px;" +
      "background:rgba(127,127,127,.15);font-size:13px}" +
    ".xcstats .xs-chip b{color:#00B37E;font-weight:600}" +
    ".xcstats .xs-tick{margin-top:10px;overflow:hidden;white-space:nowrap;opacity:.85;font-size:13px;" +
      "-webkit-mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);" +
      "mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent)}" +
    ".xcstats .xs-track{display:inline-flex;white-space:nowrap;animation:xsRoll 45s linear infinite;will-change:transform}" +
    ".xcstats .xs-tick:hover .xs-track{animation-play-state:paused}" +
    ".xcstats .xs-item{margin-right:30px}" +
    "@keyframes xsRoll{from{transform:translateX(0)}to{transform:translateX(-50%)}}" +
    "@keyframes xsPulse{0%,100%{opacity:1}50%{opacity:.35}}" +
    "@media (prefers-reduced-motion:reduce){.xcstats .xs-track{animation:none;white-space:normal;flex-wrap:wrap}.xcstats .xs-dup{display:none}" +
      ".xcstats .xs-dot{animation:none}}";
  document.head.appendChild(css);

  function esc(s){
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function fimg(code){
    code = String(code || "").toLowerCase();
    if (!/^[a-z]{2}$/.test(code)) return "";
    return "<img src='/flags/" + code + ".png' alt='' width='20' height='15' loading='lazy' "
      + "style='vertical-align:-2px;border-radius:2px;object-fit:cover' onerror='this.remove()'>";
  }

  function draw(d){
    if (!d || !d.members){ box.innerHTML = ""; return; }
    var h = "<div class='xs-row'><span class='xs-big'>\uD83C\uDF0D " + d.country_count
      + (d.country_count === 1 ? " country" : " countries") + "</span>"
      + "<span>" + d.members + " members</span>"
      + "<span class='xs-on'><span class='xs-dot'></span>" + d.online + " online</span></div>";
    if (d.countries && d.countries.length){
      h += "<div class='xs-flags'>";
      d.countries.forEach(function(c){
        h += "<span class='xs-chip' title='" + esc(c.name) + "'>" + fimg(c.code) + " " + c.members
          + (c.online ? " <b>\u25CF " + c.online + "</b>" : "") + "</span>";
      });
      h += "</div>";
    }
    if (d.recent && d.recent.length){
      var items = d.recent.map(function(r){
        return "<span class='xs-item'>" + esc(r.name) + " " + fimg(r.code) + " joined " + esc(r.ago) + "</span>";
      }).join("");
      // Two copies side by side, moved by half their width: the loop never shows a gap.
      h += "<div class='xs-tick'><div class='xs-track'>" + items
        + "<span class='xs-dup' aria-hidden='true'>" + items + "</span></div></div>";
    }
    box.innerHTML = h;
  }

  function load(){
    fetch("/api/auth/footer-stats/", {credentials: "same-origin"})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(draw)
      .catch(function(){});
  }
  load();
  setInterval(function(){ if (!document.hidden) load(); }, 60000);
})();
