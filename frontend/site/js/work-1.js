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

/* Action buttons on a profile (like a Facebook Page button): WhatsApp, Call, Shop now, Hire me, Book now, Sign up... */
window.XCBTNS = function(uid, isMe){
  if (!uid) return;
  var D = null, ICON = {whatsapp: "💬", call: "📞", email: "✉️", website: "🌐", shop: "🛍️", hire: "💼", book: "📅", signup: "✍️", order: "🛒", learn: "ℹ️"};
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function ck(n){ var x = document.cookie.match("(^|;)\\s*" + n + "\\s*=\\s*([^;]+)"); return x ? x.pop() : ""; }
  if (!document.getElementById("xbcss")){
    var st = document.createElement("style"); st.id = "xbcss";
    st.textContent = ".xbtn{display:inline-flex;align-items:center;gap:6px;padding:9px 14px;border-radius:999px;font-weight:800;font-size:14px;text-decoration:none;border:0;cursor:pointer;font-family:inherit;margin:4px 6px 0 0}"
      + ".xbtn.p{background:#16A34A;color:#fff}.xbtn.s{background:#fff;color:#0D1424;box-shadow:inset 0 0 0 1.5px #CBD5E1}.xbtn.add{background:#EEF2FF;color:#1B4DFF}"
      + ".xbsh{position:fixed;inset:0;z-index:9004;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}@media(min-width:700px){.xbsh{align-items:center}}"
      + ".xbsh .in{background:#fff;width:100%;max-width:500px;border-radius:20px 20px 0 0;padding:16px;max-height:90vh;overflow:auto;font-family:inherit;color:#0D1424}@media(min-width:700px){.xbsh .in{border-radius:20px}}"
      + ".xbsh h3{margin:0 0 4px;font-size:18px}.xbsh p{margin:0 0 10px;font-size:13px;color:#5A657C}.xbsh .row{border:1px solid #E4E8F2;border-radius:14px;padding:10px;margin-bottom:10px}"
      + ".xbsh label{display:block;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#5A657C;margin:8px 0 4px}"
      + ".xbsh select,.xbsh input{width:100%;box-sizing:border-box;padding:10px;border-radius:10px;border:1.5px solid #E4E8F2;font:inherit;font-size:14.5px;background:#F8FAFC}"
      + ".xbsh .bt{display:flex;gap:8px;margin-top:6px}.xbsh .bt button{flex:1;padding:12px;border-radius:12px;border:0;font:inherit;font-weight:800;cursor:pointer}"
      + ".xbsh .go{background:#1B4DFF;color:#fff}.xbsh .no{background:#F1F5F9}.xbsh .msg{color:#B91C1C;font-size:13px;font-weight:700;min-height:16px}";
    document.head.appendChild(st);
  }
  function place(){
    var acts = document.querySelector("#prof .acts"); if (!acts || !D) return;
    var old = acts.querySelector(".xbwrap"); if (old) old.remove();
    var w = document.createElement("span"); w.className = "xbwrap";
    w.innerHTML = D.buttons.map(function(b, i){ var ext = /^https?:/.test(b.href); return '<a class="xbtn ' + (i === 0 ? "p" : "s") + '" data-k="' + b.kind + '" href="' + esc(b.href) + '"' + (ext ? ' target="_blank" rel="noopener nofollow ugc"' : '') + '>' + (ICON[b.kind] || "") + ' ' + esc(b.label) + '</a>'; }).join("")
      + (isMe ? '<button type="button" class="xbtn add">' + (D.buttons.length ? "✎ Edit buttons" : "＋ Add a button") + '</button>' + (D.clicks ? '<small style="display:block;color:#5A657C;font-size:12px;margin-top:4px">Your buttons were tapped ' + D.month + ' times in 30 days (' + D.clicks + ' in all).</small>' : '') : '');
    acts.insertBefore(w, acts.firstChild);
    w.onclick = function(e){
      if (e.target.closest(".add")){ e.preventDefault(); editor(); return; }
      var a = e.target.closest("a.xbtn"); if (a && !isMe) navigator.sendBeacon ? navigator.sendBeacon("/api/brand/buttons/" + uid + "/click/") : fetch("/api/brand/buttons/" + uid + "/click/", {method: "POST"});
    };
  }
  function editor(){
    var items = (D.items || []).slice(0, 2); while (items.length < 2) items.push({kind: "", label: "", value: ""});
    var kinds = D.kinds || {};
    var sh = document.createElement("div"); sh.className = "xbsh";
    function row(it, i){
      return '<div class="row"><b>' + (i === 0 ? "Main button" : "Second button (optional)") + '</b><label>Button</label><select data-i="' + i + '" class="k"><option value="">— none —</option>'
        + Object.keys(kinds).filter(function(k){ return k !== "shop" || D.has_shop; }).map(function(k){ return '<option value="' + k + '"' + (it.kind === k ? " selected" : "") + '>' + (ICON[k] || "") + " " + esc(kinds[k]) + '</option>'; }).join("")
        + '</select><label>Text on the button</label><input class="l" data-i="' + i + '" maxlength="24" value="' + esc(it.label) + '"><div class="v" data-i="' + i + '"></div></div>';
    }
    sh.innerHTML = '<div class="in"><h3>Buttons on your profile</h3><p>Like a business page: people tap to WhatsApp you, call, visit your shop or website, book, sign up or hire you.</p>'
      + items.map(row).join("") + '<div class="msg"></div><div class="bt"><button type="button" class="no">Cancel</button><button type="button" class="go">Save</button></div></div>';
    document.body.appendChild(sh);
    function valBox(i){
      var k = sh.querySelector('.k[data-i="' + i + '"]').value, box = sh.querySelector('.v[data-i="' + i + '"]'), cur = items[i].kind === k ? items[i].value : "";
      var lab = {whatsapp: "WhatsApp number", call: "Phone number", email: "Email address", website: "Website link (https://...)", book: "Booking link (https://...)", signup: "Sign-up link (https://...)", order: "Order link (https://...)", learn: "Link (https://...)"}[k];
      box.innerHTML = lab ? '<label>' + lab + '</label><input class="val" maxlength="300" value="' + esc(cur) + '" placeholder="' + (k === "whatsapp" || k === "call" ? "03001234567" : k === "email" ? "you@example.com" : "https://") + '">' : (k === "shop" ? '<p style="margin:8px 0 0">Opens your shop page.</p>' : k === "hire" ? '<p style="margin:8px 0 0">Opens your freelance services.</p>' : "");
      var l = sh.querySelector('.l[data-i="' + i + '"]'); if (k && (!l.value || Object.keys(kinds).some(function(x){ return kinds[x] === l.value; }))) l.value = kinds[k] || "";
    }
    valBox(0); valBox(1);
    sh.addEventListener("change", function(e){ if (e.target.classList.contains("k")) valBox(+e.target.getAttribute("data-i")); });
    sh.onclick = function(e){
      if (e.target === sh || e.target.classList.contains("no")){ sh.remove(); return; }
      if (!e.target.classList.contains("go")) return;
      var out = [0, 1].map(function(i){ var k = sh.querySelector('.k[data-i="' + i + '"]').value, v = sh.querySelector('.v[data-i="' + i + '"] .val');
        return k ? {kind: k, label: sh.querySelector('.l[data-i="' + i + '"]').value, value: v ? v.value : ""} : null; }).filter(Boolean);
      fetch("/api/brand/buttons/", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json", "X-CSRFToken": ck("xc_csrf")}, body: JSON.stringify({items: out})})
        .then(function(r){ return r.json().then(function(d){ return {ok: r.ok, d: d}; }); }).then(function(r){
          if (!r.ok){ sh.querySelector(".msg").textContent = r.d.detail || "Could not save."; return; }
          D = r.d; sh.remove(); place(); });
    };
  }
  fetch("/api/brand/buttons/" + uid + "/", {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
    if (!d || (!d.buttons.length && !isMe)) return;
    D = d; place();
    var prof = document.getElementById("prof");
    if (prof && window.MutationObserver) new MutationObserver(function(){ var a = document.querySelector("#prof .acts"); if (a && !a.querySelector(".xbwrap")) place(); }).observe(prof, {childList: true, subtree: true});
  }).catch(function(){});
};
