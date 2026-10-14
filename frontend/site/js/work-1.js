/* On an XpertConnect profile (/in/<slug>): this member's shop, freelance services and properties. */
window.XCWORK = function(uid, name){
  if (!uid || document.getElementById("xcwork")) return;
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-PK"); }
  fetch("/api/brand/work/" + uid + "/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
    if (!d || (!d.shop && !d.gigs.length && !d.properties.length)) return;
    var css = document.createElement("style");
    css.textContent = ".xw{background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:18px;padding:16px;margin:14px 0}.xw h3{margin:0 0 10px;font-size:17px}"
      + ".xw .shop{display:flex;gap:12px;align-items:center;padding:12px;border-radius:14px;background:linear-gradient(135deg,#FFF7ED,#FEF3C7);text-decoration:none;color:#0D1424;margin-bottom:12px}"
      + ".xw .shop img,.xw .shop .l{width:54px;height:54px;border-radius:14px;object-fit:cover;background:#fff;display:grid;place-items:center;font-weight:900;font-size:22px;color:#F85606;flex:0 0 54px}"
      + ".xw .shop b{display:block;font-size:15.5px}.xw .shop small{display:block;font-size:12.5px;color:#7C2D12}.xw .shop i{margin-left:auto;font-style:normal;font-weight:800;color:#F85606;font-size:13px}"
      + ".xw .lbl{font-size:12px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-soft,#5A657C);margin:12px 0 8px;display:flex}.xw .lbl a{margin-left:auto;text-transform:none;letter-spacing:0;color:#1B4DFF;text-decoration:none}"
      + ".xw .row{display:flex;gap:10px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px}.xw .row::-webkit-scrollbar{display:none}"
      + ".xw .it{flex:0 0 170px;border:1px solid var(--line,#E4E8F2);border-radius:14px;overflow:hidden;text-decoration:none;color:var(--ink,#0D1424);background:var(--card,#fff)}"
      + ".xw .it .im{aspect-ratio:3/2;background:#F1F5F9}.xw .it img{width:100%;height:100%;object-fit:cover;display:block}.xw .it .t{padding:8px 10px}"
      + ".xw .it b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:13px;line-height:1.3;min-height:34px}.xw .it small{display:block;font-weight:800;color:#1B4DFF;font-size:13px;margin-top:2px}";
    document.head.appendChild(css);
    var h = '<div class="xw" id="xcwork"><h3>💼 ' + esc((name || "").split(" ")[0] || "Their") + ' on XpertCreation</h3>';
    if (d.shop) h += '<a class="shop" href="/shop/' + encodeURIComponent(d.shop.slug) + '">' + (d.shop.logo ? '<img src="' + esc(d.shop.logo) + '" alt="">' : '<span class="l">' + esc(d.shop.name.charAt(0)) + '</span>')
      + '<span><b>🛍️ ' + esc(d.shop.name) + '</b><small>' + esc(d.shop.city) + ' · ' + d.shop.products + ' products</small></span><i>Visit shop →</i></a>';
    if (d.gigs.length) h += '<div class="lbl">Freelance services' + (d.username ? '<a href="/market#seller-' + encodeURIComponent(d.username) + '">See all →</a>' : '') + '</div><div class="row">'
      + d.gigs.map(function(g){ return '<a class="it" href="/market#gig-' + g.id + '"><div class="im">' + (g.image ? '<img src="' + esc(g.image) + '" alt="" loading="lazy">' : '') + '</div><div class="t"><b>' + esc(g.title) + '</b><small>From ' + rs(g.price) + (g.rating ? ' · ★ ' + g.rating : '') + '</small></div></a>'; }).join("") + '</div>';
    if (d.properties.length) h += '<div class="lbl">Property</div><div class="row">'
      + d.properties.map(function(p){ return '<a class="it" href="/market#prop-' + p.id + '"><div class="im">' + (p.image ? '<img src="' + esc(p.image) + '" alt="" loading="lazy">' : '') + '</div><div class="t"><b>' + esc(p.title) + '</b><small>' + rs(p.price) + ' · ' + esc(p.city) + '</small></div></a>'; }).join("") + '</div>';
    h += '</div>';
    var prof = document.getElementById("prof"); if (!prof) return;
    var w = document.createElement("div"); w.innerHTML = h; prof.parentNode.insertBefore(w.firstChild, prof.nextSibling);
  }).catch(function(){});
};
