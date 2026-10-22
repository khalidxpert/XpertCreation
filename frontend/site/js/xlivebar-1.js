/* XpertConnect: a "Go Live" button and who is live now, above the post box (setup_live_v1). */
(function(){
  if (window.XLBAR) return; window.XLBAR = 1;
  var D = document;
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  var css = D.createElement("style");
  css.textContent = ".xlbar{display:flex;gap:10px;align-items:center;overflow-x:auto;scrollbar-width:none;padding:4px 2px 12px}.xlbar::-webkit-scrollbar{display:none}"
    + ".xlbar a{flex:0 0 auto;display:flex;flex-direction:column;align-items:center;gap:4px;text-decoration:none;color:inherit;font-size:11.5px;font-weight:700;width:66px;text-align:center}"
    + ".xlbar a .r{position:relative;width:58px;height:58px;border-radius:50%;border:3px solid #E11D48;padding:2px;box-sizing:border-box}"
    + ".xlbar a .r>*{width:100%;height:100%;border-radius:50%;object-fit:cover;display:grid;place-items:center;background:#1B4DFF;color:#fff;font-size:22px}"
    + ".xlbar a .r em{position:absolute;left:50%;bottom:-7px;transform:translateX(-50%);width:auto;height:auto;background:#E11D48;color:#fff;font-style:normal;font-size:9.5px;font-weight:900;padding:1px 5px;border-radius:5px;letter-spacing:.04em}"
    + ".xlbar a span.n{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:66px}"
    + ".xlbar a.go .r{border-color:#E4E8F2;border-style:dashed}.xlbar a.go .r>*{background:#FDE8EC;color:#E11D48;font-size:24px}";
  D.head.appendChild(css);
  function draw(){
    var anchor = D.getElementById("composer"); if (!anchor) return;
    fetch("/api/live/", {credentials: "same-origin"}).then(function(r){ return r.json(); }).then(function(d){
      var bar = D.querySelector(".xlbar");
      if (!bar){ bar = D.createElement("div"); bar.className = "xlbar"; anchor.parentNode.insertBefore(bar, anchor); }
      bar.innerHTML = '<a class="go" href="' + (d.mine ? "/live?id=" + d.mine : "/live?go=1") + '"><span class="r"><b>🔴</b></span><span class="n">' + (d.mine ? "Your live" : "Go Live") + "</span></a>"
        + (d.lives || []).filter(function(l){ return !l.mine; }).map(function(l){
          return '<a href="' + l.url + '" title="' + esc(l.title) + '"><span class="r">' + (l.host.avatar ? '<img src="' + esc(l.host.avatar) + '" alt="">' : "<b>" + esc(l.host.name.charAt(0)) + "</b>") + "<em>LIVE</em></span><span class=\"n\">" + esc(l.host.name.split(" ")[0]) + "</span></a>";
        }).join("") + '<a href="/live"><span class="r" style="border-color:#E4E8F2"><b style="background:#F1F4FA;color:#0D1424">📺</b></span><span class="n">All lives</span></a>';
    }).catch(function(){});
  }
  if (D.readyState === "loading") D.addEventListener("DOMContentLoaded", draw); else draw();
  setInterval(draw, 45000);
})();
