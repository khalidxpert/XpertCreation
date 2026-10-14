/* XpertConnect extras: Save and Repost on posts, repost previews, trending and followed hashtags,
   Follow button on hashtag pages, profile views. Loaded on /feed, /post/<id>, /tag/<name> and /in/<slug>. */
(function(){
  if (window.XCSOCIAL) return;
  var ME = null, SAVED = {}, done = {};
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  function api(p, body){
    var o = {credentials: "same-origin", headers: {}};
    if (body !== undefined){ o.method = "POST"; o.headers["Content-Type"] = "application/json"; o.headers["X-CSRFToken"] = ck("xc_csrf"); o.body = JSON.stringify(body || {}); }
    return fetch("/api/social/" + p, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ return {ok: r.ok, status: r.status, d: d}; }); })
      .catch(function(){ return {ok: false, d: {detail: "No connection. Try again."}}; });
  }
  function toast(t){ var x = document.createElement("div"); x.className = "xs-toast"; x.innerHTML = t; document.body.appendChild(x); setTimeout(function(){ x.remove(); }, 3200); }
  var css = document.createElement("style");
  css.textContent = ".fcard .facts{grid-template-columns:repeat(5,1fr)!important}.fcard .facts > button{font-size:12.5px!important;padding:9px 2px!important;white-space:nowrap}"
    + "@media(max-width:420px){.fcard .facts > button{font-size:11.5px!important}}.fcard .facts > button.xs-on{color:#B45309!important}"
    + ".xs-emb{display:block;border:1px solid var(--line,#E4E8F2);border-radius:14px;padding:10px 12px;margin-top:8px;text-decoration:none;color:var(--ink,#0D1424);background:var(--paper,#F6F7FB)}"
    + ".xs-emb .h{display:flex;gap:8px;align-items:center;font-size:13px}.xs-emb .h img,.xs-emb .h span.l{width:26px;height:26px;border-radius:50%;object-fit:cover;background:#E0E7FF;display:grid;place-items:center;font-weight:800;font-size:12px;color:#1B4DFF}"
    + ".xs-emb p{color:var(--ink,#0D1424)!important;margin:6px 0 0;font-size:14px;white-space:pre-wrap;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden}.xs-emb img.im{width:100%;max-height:300px;object-fit:cover;border-radius:10px;margin-top:8px;display:block}"
    + ".xs-rp{font-size:12.5px;color:var(--ink-soft,#5A657C);font-weight:700;margin-top:8px}"
    + ".xs-box{background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:18px;padding:12px 14px;margin:0 0 12px}.xs-box b.t{display:block;font-size:14.5px;margin-bottom:8px}"
    + ".xs-chips{display:flex;gap:6px;flex-wrap:wrap}.xs-chips a{padding:6px 11px;border-radius:99px;background:var(--paper,#F1F5F9);text-decoration:none;color:var(--ink,#0D1424);font-weight:700;font-size:13px}"
    + ".xs-chips a small{color:var(--ink-soft,#5A657C);font-weight:600;margin-left:4px}.xs-chips a.up{background:#FEF3C7}.xs-chips a.mine{background:#EEF2FF;color:#1B4DFF}"
    + ".xs-links{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px;font-size:13px;font-weight:800}.xs-links a{color:#1B4DFF;text-decoration:none}"
    + ".xs-sh{position:fixed;inset:0;z-index:9005;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}@media(min-width:700px){.xs-sh{align-items:center}}"
    + ".xs-sh .in{background:var(--card,#fff);width:100%;max-width:520px;border-radius:20px 20px 0 0;padding:16px;font-family:inherit;color:var(--ink,#0D1424)}@media(min-width:700px){.xs-sh .in{border-radius:20px}}"
    + ".xs-sh h3{margin:0 0 10px;font-size:18px}.xs-sh textarea{width:100%;box-sizing:border-box;min-height:80px;padding:10px 12px;border-radius:12px;border:1.5px solid var(--line,#E4E8F2);font:inherit;font-size:15px}"
    + ".xs-sh select{padding:9px;border-radius:10px;border:1.5px solid var(--line,#E4E8F2);font:inherit;margin-top:8px}.xs-sh .bt{display:flex;gap:8px;margin-top:10px}.xs-sh .bt button{flex:1;padding:12px;border-radius:12px;border:0;font:inherit;font-weight:800;cursor:pointer}"
    + ".xs-sh .go{background:#1B4DFF;color:#fff}.xs-sh .no{background:#F1F5F9}.xs-sh .msg{color:#B91C1C;font-size:13px;font-weight:700;margin-top:6px}"
    + ".xs-toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#0D1424;color:#fff;padding:10px 16px;border-radius:12px;font-weight:700;font-size:13.5px;z-index:9006;box-shadow:0 10px 30px rgba(0,0,0,.3)}.xs-toast a{color:#93C5FD}"
    + ".xs-tf{display:inline-flex;align-items:center;gap:6px;margin:6px 0 10px;padding:9px 16px;border-radius:99px;border:0;background:#1B4DFF;color:#fff;font:inherit;font-weight:800;font-size:14px;cursor:pointer}.xs-tf.on{background:#E2E8F0;color:#0D1424}"
    + ".xs-tfn{font-size:13px;color:var(--ink-soft,#5A657C);margin-left:8px}"
    + ".xs-pv{display:flex;align-items:center;gap:10px;background:linear-gradient(135deg,#EEF2FF,#F5F3FF);border:1px solid #C7D2FE;border-radius:16px;padding:12px 14px;margin:12px 0;text-decoration:none;color:#0D1424;font-size:14px}.xs-pv b{font-size:20px;color:#1B4DFF}.xs-pv i{margin-left:auto;font-style:normal;font-weight:800;color:#1B4DFF;font-size:13px}";
  document.head.appendChild(css);

  // ---------- feed cards
  function decorate(){
    var cards = [].slice.call(document.querySelectorAll("article.fcard[id^='post-']")).filter(function(c){ return !c.getAttribute("data-xs"); });
    if (!cards.length) return;
    var ids = [], embeds = [];
    cards.forEach(function(c){
      c.setAttribute("data-xs", "1");
      var id = +c.id.slice(5); ids.push(id);
      var f = c.querySelector(".facts");
      if (f && !f.querySelector("[data-xsave]")){
        f.insertAdjacentHTML("beforeend", '<button type="button" data-xrepost="' + id + '">🔁 Repost</button><button type="button" data-xsave="' + id + '">🔖 Save</button>');
      }
      var b = c.querySelector(".fbody");
      if (b){
        var a = [].filter.call(b.querySelectorAll("a"), function(x){ return /\/post\/(\d+)$/.test(x.getAttribute("href") || "") && /🔁 Reposted:\s*$/.test((x.previousSibling && x.previousSibling.textContent) || ""); })[0];
        if (a){
          var oid = +a.getAttribute("href").match(/\/post\/(\d+)$/)[1], prev = a.previousSibling;
          prev.textContent = prev.textContent.replace(/🔁 Reposted:\s*$/, "");
          var box = document.createElement("div"); box.className = "xs-embw"; box.setAttribute("data-oid", oid);
          box.innerHTML = '<div class="xs-rp">🔁 Reposted</div><a class="xs-emb" href="/post/' + oid + '">Loading the original post…</a>';
          a.replaceWith(box); b.innerHTML = b.innerHTML.replace(/(\s|<br>)+(<div class="xs-embw")/, "$2"); embeds.push(oid);
        }
      }
    });
    if (embeds.length) api("embed/?ids=" + embeds.join(",")).then(function(r){
      var P = (r.d && r.d.posts) || {};
      embeds.forEach(function(oid){
        [].forEach.call(document.querySelectorAll('.xs-embw[data-oid="' + oid + '"] .xs-emb'), function(e){
          var p = P[oid];
          if (!p){ e.textContent = "The original post is not available."; return; }
          e.innerHTML = '<div class="h">' + (p.author.avatar ? '<img src="' + esc(p.author.avatar) + '" alt="">' : '<span class="l">' + esc(p.author.name.charAt(0)) + '</span>') + '<b>' + esc(p.author.name) + '</b><small style="color:#5A657C">· ' + esc(p.when) + '</small></div>'
            + (p.body ? '<p>' + esc(p.body) + '</p>' : '') + (p.image ? '<img class="im" src="' + esc(p.image) + '" alt="" loading="lazy">' : '');
        });
      });
    });
    if (ME) api("saved/status/?ids=" + ids.join(",")).then(function(r){
      (r.d.saved || []).forEach(function(id){ SAVED[id] = 1; });
      ids.forEach(paintSave);
      var rc = r.d.reposts || {};
      Object.keys(rc).forEach(function(id){ var bt = document.querySelector('[data-xrepost="' + id + '"]'); if (bt) bt.textContent = "🔁 " + rc[id]; });
    });
  }
  function paintSave(id){ [].forEach.call(document.querySelectorAll('[data-xsave="' + id + '"]'), function(b){ b.classList.toggle("xs-on", !!SAVED[id]); b.textContent = SAVED[id] ? "🔖 Saved" : "🔖 Save"; }); }
  function needSign(){ toast('<a href="/login?next=' + encodeURIComponent(location.pathname) + '">Sign in</a> first.'); }
  document.addEventListener("click", function(e){
    var s = e.target.closest("[data-xsave]");
    if (s){
      e.preventDefault(); e.stopPropagation(); if (!ME){ needSign(); return; }
      var id = +s.getAttribute("data-xsave");
      api("saved/" + id + "/", {}).then(function(r){ if (!r.ok){ toast(esc(r.d.detail || "Could not save.")); return; } SAVED[id] = r.d.saved ? 1 : 0; paintSave(id); toast(r.d.saved ? 'Saved. <a href="/saved">See saved posts</a>' : "Removed from saved"); });
      return;
    }
    var rp = e.target.closest("[data-xrepost]");
    if (rp){ e.preventDefault(); e.stopPropagation(); if (!ME){ needSign(); return; } repostSheet(+rp.getAttribute("data-xrepost")); }
  }, true);
  function repostSheet(id){
    var sh = document.createElement("div"); sh.className = "xs-sh";
    sh.innerHTML = '<div class="in"><h3>🔁 Repost</h3><textarea maxlength="2500" placeholder="Add your thoughts (optional)"></textarea>'
      + '<select><option value="public">🌐 Everyone</option><option value="members" selected>👥 Members</option><option value="connections">🤝 Connections</option></select>'
      + '<div class="msg"></div><div class="bt"><button type="button" class="no">Cancel</button><button type="button" class="go">Repost</button></div></div>';
    document.body.appendChild(sh); sh.querySelector("textarea").focus();
    sh.onclick = function(e){
      if (e.target === sh || e.target.classList.contains("no")){ sh.remove(); return; }
      if (!e.target.classList.contains("go")) return;
      e.target.disabled = true;
      api("repost/" + id + "/", {text: sh.querySelector("textarea").value, visibility: sh.querySelector("select").value}).then(function(r){
        if (!r.ok){ e.target.disabled = false; sh.querySelector(".msg").textContent = r.d.detail || "Could not repost."; return; }
        sh.remove(); toast('Reposted ✓ <a href="/post/' + r.d.id + '">View</a>');
      });
    };
  }

  // ---------- trending + my hashtags on the feed
  function feedBox(){
    var list = document.getElementById("flist");
    if (!list || /^\/post\//.test(location.pathname) || document.getElementById("xs-trend")) return;
    var box = document.createElement("div"); box.className = "xs-box"; box.id = "xs-trend"; box.innerHTML = '<b class="t">🔥 Trending this week</b><div class="xs-chips" id="xs-tc"></div><div id="xs-my"></div>';
    list.parentNode.insertBefore(box, list);
    api("tags/trending/").then(function(r){
      var t = (r.d.tags || []);
      if (!t.length){ box.querySelector("#xs-tc").innerHTML = '<small style="color:#5A657C">No hashtags this week yet. Add #tags to your posts!</small>'; }
      else box.querySelector("#xs-tc").innerHTML = t.slice(0, 10).map(function(x){ return '<a href="/tag/' + encodeURIComponent(x.tag) + '" class="' + (x.up ? "up" : "") + '">#' + esc(x.tag) + '<small>' + x.posts + (x.new ? " · new" : x.up ? " ↑" : "") + '</small></a>'; }).join("");
    });
    if (ME) api("tags/mine/").then(function(r){
      var m = r.d.tags || [];
      box.querySelector("#xs-my").innerHTML = (m.length ? '<b class="t" style="margin-top:10px">🏷️ Hashtags you follow</b><div class="xs-chips">' + m.map(function(x){ return '<a class="mine" href="/tag/' + encodeURIComponent(x) + '">#' + esc(x) + '</a>'; }).join("") + '</div><small style="display:block;color:#5A657C;margin-top:6px">Their posts show in your Following tab.</small>'
        : '<small style="display:block;color:#5A657C;margin-top:8px">Open any hashtag and tap Follow to see its posts in your Following tab.</small>')
        + '<div class="xs-links"><a href="/saved">🔖 Saved posts</a><a href="/me/stats">📊 My stats</a><a href="/settings">⚙️ Settings &amp; privacy</a></div>';
    });
  }

  // ---------- hashtag page: Follow button
  function tagPage(){
    var m = location.pathname.match(/^\/tag\/([A-Za-z][A-Za-z0-9_]{1,49})/); if (!m) return;
    var h = document.querySelector(".tgh"); if (!h || document.querySelector(".xs-tf")) return;
    var tag = m[1].toLowerCase(), w = document.createElement("div");
    w.innerHTML = '<button type="button" class="xs-tf">＋ Follow #' + esc(tag) + '</button><span class="xs-tfn"></span>';
    h.parentNode.insertBefore(w, h.nextSibling);
    var b = w.querySelector("button"), n = w.querySelector(".xs-tfn");
    function paint(d){ b.classList.toggle("on", !!d.following); b.textContent = d.following ? "✓ Following #" + tag : "＋ Follow #" + tag; n.textContent = d.followers ? d.followers + " follower" + (d.followers === 1 ? "" : "s") : ""; }
    api("tags/" + tag + "/").then(function(r){ if (r.ok) paint(r.d); });
    b.onclick = function(){ if (!ME){ needSign(); return; } api("tags/" + tag + "/follow/", {}).then(function(r){ if (!r.ok){ toast(esc(r.d.detail || "Could not follow.")); return; } paint(r.d); if (r.d.following) toast("Following #" + esc(tag) + ". Its posts show in your Following tab."); }); };
  }

  // ---------- profiles
  window.XCSOCIAL = {profile: function(P){
    if (!P || !P.user_id) return;
    if (!P.is_me){ api("view/" + P.user_id + "/", {}); return; }
    api("stats/").then(function(r){
      if (!r.ok || document.querySelector(".xs-pv")) return;
      var prof = document.getElementById("prof"); if (!prof) return;
      var a = document.createElement("a"); a.className = "xs-pv"; a.href = "/me/stats";
      a.innerHTML = '📊 <span><b>' + r.d.views.d30 + '</b> profile views in 30 days' + (r.d.viewers.length ? ' · ' + esc(r.d.viewers[0].name) + (r.d.viewers.length > 1 ? " and others" : "") : "") + '</span><i>See who →</i>';
      prof.parentNode.insertBefore(a, prof.nextSibling);
    });
  }};

  function tick(){ decorate(); feedBox(); tagPage(); }
  function start(){
    fetch("/api/auth/me/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }).then(function(u){
      ME = u && (u.email || u.id) ? u : null; tick();
      if (window.MutationObserver) new MutationObserver(function(){ clearTimeout(done.t); done.t = setTimeout(tick, 120); }).observe(document.body, {childList: true, subtree: true});
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
