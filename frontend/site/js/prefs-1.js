/* XpertConnect: your interests as chips at the top (each opens its hashtag page), or a prompt to pick some. */
(function(){
  "use strict";
  if (location.pathname.replace(/\/+$/, "") !== "/feed" || /[?&]user=/.test(location.search)) return;
  fetch("/api/prefs/me/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
    if (!d) return;
    var c = document.getElementById("composer"); if (!c) return;
    var row = document.createElement("div");
    row.style.cssText = "display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;margin:2px 0 8px;padding-bottom:2px";
    var by = {}; (d.catalog || []).forEach(function(x){ by[x.key] = x; });
    var chip = "flex:0 0 auto;padding:7px 12px;border-radius:99px;background:var(--paper,#EEF1F6);color:var(--ink,#0D1424);font-weight:700;font-size:13.5px;text-decoration:none;white-space:nowrap";
    row.innerHTML = (d.interests || []).length
      ? d.interests.map(function(k){ var x = by[k] || {icon: "#", label: k}; return '<a href="/tag/' + k + '" style="' + chip + '">' + x.icon + ' ' + x.label + '</a>'; }).join("") + '<a href="/me/preferences" style="' + chip + ';background:none;color:#1B4DFF">\u270F\uFE0F</a>'
      : '<a href="/me/preferences" style="' + chip + ';background:#EEF2FF;color:#1B4DFF">\u2728 Pick your interests</a>';
    c.parentNode.insertBefore(row, c);
  }).catch(function(){});
})();
