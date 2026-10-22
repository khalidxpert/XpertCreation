/* Group roles like Discord (xroles-1.js) - coloured role names in XpertChat groups.
   Admins make roles (name, colour, emoji) and give them to members. Names show in the role colour in chat,
   with a small role tag, and the member list is grouped by role. */
(function(){
  "use strict";
  if (window.XROLES || !/^\/group\/\d+/.test(location.pathname)) return;
  var D = document, B = D.body;
  var SW = ["#5865F2", "#57F287", "#FEE75C", "#EB459E", "#ED4245", "#F47B67", "#E67E22", "#1ABC9C", "#3498DB", "#9B59B6", "#E91E63", "#11806A", "#1F8B4C", "#206694", "#71368A", "#AD1457", "#C27C0E", "#A84300", "#979C9F", "#607D8B"];
  var R = {roles: [], members: {}, can_manage: false}, byId = {};
  function gid(){ return (window.XCG && XCG.gid && XCG.gid()) || (location.pathname.match(/\/group\/(\d+)/) || [])[1]; }
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function api(p, body, method){
    var o = {method: method || (body === undefined ? "GET" : "POST"), credentials: "same-origin", headers: {"Accept": "application/json"}};
    if (body !== undefined){ o.headers["Content-Type"] = "application/json"; o.headers["X-CSRFToken"] = ck("xc_csrf") || ck("csrftoken"); o.body = JSON.stringify(body); }
    return fetch("/api/groupx/" + gid() + "/roles/" + p, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ if (!r.ok) throw new Error(d.detail || "Error " + r.status); return d; }); });
  }
  function set(d){ R = d; byId = {}; (d.roles || []).forEach(function(r){ byId[r.id] = r; }); paint(true); }
  function load(){ return api("").then(set).catch(function(){}); }
  function rolesOf(uid){ return (R.members[String(uid)] || []).map(function(id){ return byId[id]; }).filter(Boolean); }
  function tag(r, small){ return '<span class="xrtag' + (small ? " s" : "") + '" style="--rc:' + r.color + '">' + (r.icon ? esc(r.icon) + " " : "") + esc(r.name) + "</span>"; }

  var st = D.createElement("style");
  st.textContent = ".xrtag{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:700;line-height:1;padding:3px 7px;border-radius:10px;margin-left:6px;color:var(--rc);background:color-mix(in srgb,var(--rc) 16%,transparent);border:1px solid color-mix(in srgb,var(--rc) 45%,transparent);vertical-align:middle;white-space:nowrap}"
    + ".xrtag.s{font-size:10px;padding:2px 6px;margin-left:5px}"
    + ".xrtags{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}.xrtags .xrtag{margin-left:0}"
    + ".xrh{font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-soft,#6b7280);margin:14px 0 4px;display:flex;align-items:center;gap:6px}.xrh i{width:9px;height:9px;border-radius:50%;background:var(--rc);display:inline-block}"
    + ".xrbtn{border:1px solid var(--line,#d8dee9);background:transparent;border-radius:10px;padding:5px 9px;font:inherit;font-size:12px;cursor:pointer;color:inherit}"
    + ".xrov{position:fixed;inset:0;z-index:2147482000;background:rgba(0,0,0,.45);display:flex;align-items:flex-end;justify-content:center}"
    + ".xrbox{background:var(--card,#fff);color:var(--ink,#111);width:100%;max-width:480px;max-height:88vh;overflow:auto;border-radius:18px 18px 0 0;padding:16px 16px calc(18px + env(safe-area-inset-bottom))}"
    + "@media(min-width:700px){.xrov{align-items:center}.xrbox{border-radius:18px}}"
    + ".xrbox h3{margin:0 0 10px;display:flex;justify-content:space-between;align-items:center}.xrrow{display:flex;align-items:center;gap:8px;padding:9px 0;border-bottom:1px solid var(--line,#eef1f5)}"
    + ".xrrow .dot{width:14px;height:14px;border-radius:50%;background:var(--rc);flex:0 0 auto}.xrrow b{flex:1;color:var(--rc)}.xrrow small{color:var(--ink-soft,#6b7280)}"
    + ".xrsw{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.xrsw button{width:28px;height:28px;border-radius:50%;border:2px solid transparent;cursor:pointer;background:var(--rc)}.xrsw button.on{border-color:var(--ink,#111);box-shadow:0 0 0 2px var(--card,#fff) inset}"
    + ".xrbox input[type=text]{width:100%;box-sizing:border-box;padding:10px;border-radius:10px;border:1px solid var(--line,#d8dee9);font:inherit;background:transparent;color:inherit}"
    + ".xrbox label{display:block;font-weight:600;font-size:13px;margin-top:10px}.xrbox .xrok{margin-top:12px;display:flex;gap:8px;justify-content:flex-end}"
    + ".xrp{padding:9px 14px;border-radius:10px;border:0;background:#5865F2;color:#fff;font:inherit;font-weight:700;cursor:pointer}.xrp.o{background:transparent;color:inherit;border:1px solid var(--line,#d8dee9)}.xrp.r{background:#ED4245}"
    + ".xrcb{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--line,#eef1f5);cursor:pointer}.xrcb input{width:20px;height:20px}.xrer{color:#ED4245;font-size:13px;min-height:1em}";
  D.head.appendChild(st);

  /* -------- colour names in the chat and in the member list */
  function paint(force){
    [].forEach.call(D.querySelectorAll(".gm[data-aid]"), function(el){
      var w = el.querySelector(".who"); if (!w) return;
      var rs = rolesOf(el.getAttribute("data-aid")), key = rs.map(function(r){ return r.id + r.color + r.name + r.icon; }).join("|");
      if (!force && w.dataset.xr === key) return; w.dataset.xr = key;
      var old = w.querySelector(".xrtag"); if (old) old.remove();
      if (rs.length){ w.style.color = rs[0].color; w.insertAdjacentHTML("beforeend", tag(rs[0], true)); } else w.style.color = "";
    });
    var rows = D.querySelectorAll(".gmem[data-uid]");
    if (!rows.length) return;
    var host = rows[0].parentNode, first = true;
    [].forEach.call(rows, function(row){
      var rs = rolesOf(row.getAttribute("data-uid")), key = rs.map(function(r){ return r.id + r.color + r.name + r.icon; }).join("|");
      if (force || row.dataset.xr !== key){
        row.dataset.xr = key;
        var nm = row.querySelector('b[class*="rk-"]') || row.querySelector("span b"); if (nm && rs.length) nm.style.color = rs[0].color; else if (nm) nm.style.color = "";
        var old = row.querySelector(".xrtags"); if (old) old.remove();
        if (rs.length){ var t = D.createElement("div"); t.className = "xrtags"; t.innerHTML = rs.map(function(r){ return tag(r); }).join(""); ((nm && nm.parentNode) || row).appendChild(t); }
      }
      if (R.can_manage && !row.querySelector("[data-xrgive]")){
        var b = D.createElement("button"); b.className = "gbtn"; b.type = "button"; b.setAttribute("data-xrgive", row.getAttribute("data-uid")); b.textContent = "🎭 Roles";
        var anchor = row.querySelector(".gbtn"); if (anchor) row.insertBefore(b, anchor); else row.appendChild(b);
      }
    });
    group(host, rows, force);
    if (!host.parentNode.querySelector("[data-xrmanage]") && !D.querySelector("[data-xrmanage]")){
      var h = [].filter.call(host.querySelectorAll("h3"), function(x){ return /members/i.test(x.textContent); })[0];
      if (h){ var mb = D.createElement("button"); mb.className = "xrbtn"; mb.type = "button"; mb.setAttribute("data-xrmanage", "1"); mb.textContent = R.can_manage ? "🎭 Manage roles" : "🎭 Roles"; mb.style.marginLeft = "8px"; h.appendChild(mb); }
    }
  }
  // the member list, grouped by role (roles that are shown separately), top role first
  function group(host, rows, force){
    var sig = R.roles.map(function(r){ return r.id + ":" + r.hoist; }).join(",") + "/" + JSON.stringify(R.members) + "/" + rows.length;
    if (!force && host.dataset.xrg === sig) return; host.dataset.xrg = sig;
    [].forEach.call(host.querySelectorAll(".xrh"), function(x){ x.remove(); });
    var buckets = {}, order = [];
    R.roles.forEach(function(r){ if (r.hoist){ buckets[r.id] = []; order.push(r); } });
    var rest = [];
    [].forEach.call(rows, function(row){ var top = rolesOf(row.getAttribute("data-uid")).filter(function(r){ return r.hoist; })[0]; (top ? buckets[top.id] : rest).push(row); });
    if (!order.some(function(r){ return buckets[r.id].length; })) return;
    var at = rows[0];
    var before = at.previousSibling, frag = D.createDocumentFragment();
    order.forEach(function(r){
      if (!buckets[r.id].length) return;
      var h = D.createElement("div"); h.className = "xrh"; h.style.setProperty("--rc", r.color); h.innerHTML = "<i></i>" + esc((r.icon ? r.icon + " " : "") + r.name) + " — " + buckets[r.id].length; frag.appendChild(h);
      buckets[r.id].forEach(function(x){ frag.appendChild(x); });
    });
    if (rest.length){ var h2 = D.createElement("div"); h2.className = "xrh"; h2.style.setProperty("--rc", "#979C9F"); h2.innerHTML = "<i></i>Members — " + rest.length; frag.appendChild(h2); rest.forEach(function(x){ frag.appendChild(x); }); }
    host.insertBefore(frag, before ? before.nextSibling : host.firstChild);
  }

  /* -------- panels */
  function sheet(html){
    var ov = D.createElement("div"); ov.className = "xrov"; ov.innerHTML = '<div class="xrbox">' + html + "</div>";
    ov.addEventListener("click", function(e){ if (e.target === ov || e.target.closest("[data-xrclose]")) ov.remove(); });
    B.appendChild(ov); return ov;
  }
  function manage(){
    var ov = sheet("");
    var draw = function(){
      var h = '<h3>🎭 Roles <button class="xrp o" data-xrclose>✕</button></h3>';
      if (!R.roles.length) h += '<p style="color:var(--ink-soft,#6b7280)">No roles yet.' + (R.can_manage ? " Make one, like “Teacher”, “VIP” or “Seller”, then give it to members from the member list." : "") + "</p>";
      R.roles.forEach(function(r, i){
        h += '<div class="xrrow" style="--rc:' + r.color + '"><span class="dot"></span><b>' + esc((r.icon ? r.icon + " " : "") + r.name) + '</b><small>' + r.count + " member" + (r.count === 1 ? "" : "s") + "</small>"
          + (R.can_manage ? '<button class="xrbtn" data-up="' + i + '" aria-label="Move up"' + (i ? "" : " disabled") + '>▲</button><button class="xrbtn" data-dn="' + i + '" aria-label="Move down"' + (i < R.roles.length - 1 ? "" : " disabled") + '>▼</button><button class="xrbtn" data-ed="' + r.id + '">✏️</button>' : "") + "</div>";
      });
      if (R.can_manage) h += '<div class="xrok"><button class="xrp" data-xnew>+ New role</button></div>';
      ov.firstChild.innerHTML = h;
    };
    draw();
    ov.addEventListener("click", function(e){
      var b = e.target.closest("button"); if (!b) return;
      if (b.dataset.xnew != null) return edit(null, draw);
      if (b.dataset.ed) return edit(byId[b.dataset.ed], draw);
      if (b.dataset.up || b.dataset.dn){ var i = +(b.dataset.up || b.dataset.dn), j = b.dataset.up ? i - 1 : i + 1, ids = R.roles.map(function(r){ return r.id; }); var t = ids[i]; ids[i] = ids[j]; ids[j] = t; api("order/", {ids: ids}).then(function(d){ set(d); draw(); }).catch(function(){}); }
    });
  }
  function edit(r, after){
    var col = r ? r.color : SW[Math.floor(Math.random() * 10)];
    var ov = sheet('<h3>' + (r ? "Edit role" : "New role") + ' <button class="xrp o" data-xrclose>✕</button></h3>'
      + '<label>Role name</label><input type="text" maxlength="30" data-n placeholder="e.g. Teacher, VIP, Seller" value="' + esc(r ? r.name : "") + '">'
      + '<label>Colour</label><div class="xrsw">' + SW.map(function(c){ return '<button type="button" data-c="' + c + '" style="--rc:' + c + '" aria-label="' + c + '"></button>'; }).join("") + '<input type="color" data-cc value="' + col + '" aria-label="Any colour" style="width:34px;height:30px;border:0;background:none;padding:0"></div>'
      + '<label>Emoji (optional)</label><input type="text" maxlength="4" data-i placeholder="⭐ 👑 🎓 🛠" value="' + esc(r ? r.icon : "") + '">'
      + '<label style="display:flex;gap:8px;align-items:center"><input type="checkbox" data-h' + (!r || r.hoist ? " checked" : "") + '> Show these members in their own section of the member list</label>'
      + '<p style="margin:12px 0 4px">Preview: <b data-pv></b></p><p class="xrer"></p>'
      + '<div class="xrok">' + (r ? '<button class="xrp r" data-xdel>Delete</button>' : "") + '<button class="xrp" data-xsave>Save</button></div>');
    var box = ov.firstChild, pv = function(){ var n = box.querySelector("[data-n]").value.trim() || "Role", ic = box.querySelector("[data-i]").value.trim();
      box.querySelector("[data-pv]").innerHTML = '<span style="color:' + col + '">Ayesha</span>' + tag({name: n, color: col, icon: ic}, true);
      [].forEach.call(box.querySelectorAll("[data-c]"), function(x){ x.classList.toggle("on", x.dataset.c.toLowerCase() === col.toLowerCase()); }); };
    pv();
    box.addEventListener("input", function(e){ if (e.target.dataset.cc != null) col = e.target.value; pv(); });
    box.addEventListener("click", function(e){
      var b = e.target.closest("button"); if (!b) return;
      if (b.dataset.c){ col = b.dataset.c; box.querySelector("[data-cc]").value = col; return pv(); }
      var er = box.querySelector(".xrer");
      if (b.dataset.xdel != null){ if (!window.confirm("Delete the role “" + r.name + "”? Members keep everything else.")) return; return api(r.id + "/", undefined, "DELETE").then(function(d){ set(d); ov.remove(); after && after(); }).catch(function(x){ er.textContent = x.message; }); }
      if (b.dataset.xsave != null){
        b.disabled = true;
        var body = {name: box.querySelector("[data-n]").value, color: col, icon: box.querySelector("[data-i]").value, hoist: box.querySelector("[data-h]").checked};
        api(r ? r.id + "/" : "", body).then(function(d){ set(d); ov.remove(); after && after(); }).catch(function(x){ b.disabled = false; er.textContent = x.message; });
      }
    });
  }
  function giveRoles(uid){
    if (!R.roles.length) return manage();
    var name = (((D.querySelector('.gmem[data-uid="' + uid + '"] b[class*="rk-"]') || {}).firstChild || {}).textContent || "").replace(/^(\uD83D\uDC51|\uD83D\uDEE1\uFE0F?|\u2B50)\s*/, "").trim();
    var ov = sheet('<h3>Roles for ' + esc(name || "this member") + ' <button class="xrp o" data-xrclose>✕</button></h3><div data-list></div><p class="xrer"></p><div class="xrok"><button class="xrp o" data-mng>Manage roles</button><button class="xrp" data-xrclose>Done</button></div>');
    var box = ov.firstChild, draw = function(){
      var have = R.members[String(uid)] || [];
      box.querySelector("[data-list]").innerHTML = R.roles.map(function(r){ return '<label class="xrcb" style="--rc:' + r.color + '"><input type="checkbox" data-rid="' + r.id + '"' + (have.indexOf(r.id) > -1 ? " checked" : "") + ">" + tag(r) + "</label>"; }).join("");
    };
    draw();
    box.addEventListener("change", function(e){ var rid = e.target.dataset.rid; if (!rid) return; e.target.disabled = true;
      api(rid + "/members/", {uid: +uid, on: e.target.checked}).then(function(d){ set(d); draw(); }).catch(function(x){ box.querySelector(".xrer").textContent = x.message; draw(); }); });
    box.addEventListener("click", function(e){ if (e.target.closest("[data-mng]")){ ov.remove(); manage(); } });
  }
  D.addEventListener("click", function(e){
    var g = e.target.closest("[data-xrgive]"); if (g){ e.preventDefault(); e.stopPropagation(); return giveRoles(g.getAttribute("data-xrgive")); }
    var m = e.target.closest("[data-xrmanage]"); if (m){ e.preventDefault(); e.stopPropagation(); return manage(); }
  }, true);

  window.XROLES = {reload: load, state: function(){ return R; }};
  var t = null;
  new MutationObserver(function(){ clearTimeout(t); t = setTimeout(function(){ paint(false); }, 60); }).observe(B, {childList: true, subtree: true});
  var tries = 0, boot = function(){ if (gid()) { load(); setInterval(load, 60000); } else if (tries++ < 20) setTimeout(boot, 500); };
  boot();
})();
