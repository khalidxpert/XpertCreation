/* Country, state and city pickers - chosen from lists, with flags. Data: /geo/*.json
   (from dr5hn/countries-states-cities-database, ODbL). Usage:
   GeoPicker(el, {country:"PK", state:"Punjab", city:"Lahore", onChange:function(g){...}}) */
(function(){
  "use strict";
  var cache = {};
  function getJSON(u){
    if (!cache[u]) cache[u] = fetch(u).then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); });
    return cache[u];
  }
  function esc(s){
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function flagImg(c){
    c = String(c || "").toLowerCase();
    return /^[a-z]{2}$/.test(c) ? "<img src='/flags/" + c + ".png' alt='' width='20' height='15' onerror='this.remove()'>" : "";
  }
  function fold(s){ return String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, ""); }

  if (!document.getElementById("gp-css")){
    var st = document.createElement("style");
    st.id = "gp-css";
    st.textContent =
      ".gp-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}" +
      "@media(max-width:620px){.gp-row{grid-template-columns:1fr}}" +
      ".gp{position:relative}" +
      ".gp-btn{width:100%;display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--line,#E4E8F2);" +
        "border-radius:11px;background:var(--card,#fff);color:var(--ink,#0D1424);font:inherit;text-align:left;cursor:pointer;min-height:42px}" +
      ".gp-btn[disabled]{opacity:.55;cursor:default}" +
      ".gp-btn span{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" +
      ".gp-btn span.ph{color:var(--ink-soft,#5A657C)}" +
      ".gp-btn:after{content:'\\25BE';opacity:.6}" +
      ".gp-pan{position:absolute;z-index:50;left:0;right:0;top:calc(100% + 4px);background:var(--card,#fff);" +
        "border:1px solid var(--line,#E4E8F2);border-radius:12px;box-shadow:0 12px 30px rgba(13,20,36,.16);padding:8px}" +
      ".gp-q{width:100%;box-sizing:border-box;padding:9px 11px;border:1px solid var(--line,#E4E8F2);border-radius:9px;font:inherit}" +
      ".gp-list{max-height:260px;overflow:auto;margin-top:6px}" +
      ".gp-it{display:flex;align-items:center;gap:8px;padding:8px 9px;border-radius:8px;cursor:pointer;font-size:14.5px}" +
      ".gp-it:hover,.gp-it.on{background:var(--paper,#F6F7FB)}" +
      ".gp-it img,.gp-btn img{border-radius:2px;flex:0 0 auto}" +
      ".gp-none{padding:8px 9px;color:var(--ink-soft,#5A657C);font-size:13.5px}";
    document.head.appendChild(st);
  }

  var OPEN = null;
  document.addEventListener("click", function(e){
    if (OPEN && !OPEN.wrap.contains(e.target)) OPEN.close();
  });

  function Drop(host, placeholder){
    var wrap = document.createElement("div");
    wrap.className = "gp";
    wrap.innerHTML = "<button type='button' class='gp-btn'><span class='ph'>" + esc(placeholder) + "</span></button>";
    host.appendChild(wrap);
    var btn = wrap.firstChild, items = [], value = "", pan = null, self = {wrap: wrap, onPick: null};
    function label(){
      var it = items.filter(function(x){ return x.v === value; })[0];
      btn.innerHTML = value ? (it && it.flag ? flagImg(it.flag) : "") + "<span>" + esc(it ? it.label : value) + "</span>"
                            : "<span class='ph'>" + esc(placeholder) + "</span>";
    }
    function list(q){
      var f = fold(q), a = [], b = [];
      items.forEach(function(x){
        var l = fold(x.label);
        if (!f || l.indexOf(f) === 0) a.push(x); else if (l.indexOf(f) > 0) b.push(x);
      });
      var all = a.concat(b).slice(0, 300);
      pan.querySelector(".gp-list").innerHTML = all.length ? all.map(function(x){
        return "<div class='gp-it" + (x.v === value ? " on" : "") + "' data-v='" + esc(x.v) + "'>"
          + (x.flag ? flagImg(x.flag) : "") + esc(x.label) + "</div>";
      }).join("") : "<div class='gp-none'>Nothing matches.</div>";
    }
    self.close = function(){ if (pan){ pan.remove(); pan = null; } if (OPEN === self) OPEN = null; };
    btn.onclick = function(e){
      e.stopPropagation();
      if (pan){ self.close(); return; }
      if (OPEN) OPEN.close();
      pan = document.createElement("div");
      pan.className = "gp-pan";
      pan.innerHTML = "<input class='gp-q' placeholder='Search\u2026' autocomplete='off'><div class='gp-list'></div>";
      wrap.appendChild(pan);
      OPEN = self;
      var q = pan.querySelector(".gp-q");
      q.oninput = function(){ list(q.value); };
      q.onkeydown = function(ev){
        if (ev.key === "Enter"){ ev.preventDefault(); var first = pan.querySelector(".gp-it"); if (first) first.click(); }
        if (ev.key === "Escape") self.close();
      };
      pan.querySelector(".gp-list").onclick = function(ev){
        var it = ev.target.closest(".gp-it");
        if (!it) return;
        value = it.getAttribute("data-v");
        label(); self.close();
        if (self.onPick) self.onPick(value);
      };
      list("");
      q.focus();
    };
    self.set = function(newItems, v, disabled){
      items = newItems || [];
      value = v || "";
      btn.disabled = !!disabled;
      label();
    };
    self.get = function(){ return value; };
    return self;
  }

  window.GeoPicker = function(el, o){
    o = o || {};
    el.innerHTML = "<div class='gp-row'></div>";
    var row = el.firstChild;
    var dc = Drop(row, "Country"), ds = Drop(row, "State / province"), dy = Drop(row, "City");
    var g = {country: String(o.country || "").toUpperCase(), state: o.state || "", city: o.city || "", lat: null, lng: null};
    var data = null;
    dc.set([], g.country, true); ds.set([], g.state, true); dy.set([], g.city, true);
    function emit(){ if (o.onChange) o.onChange({country: g.country, state: g.state, city: g.city, lat: g.lat, lng: g.lng}); }
    function stateObj(){ return data ? data.s.filter(function(s){ return s.n === g.state; })[0] : null; }
    function fillCities(){
      var s = stateObj();
      var cities = s ? s.c : [];
      var hit = cities.filter(function(c){ return c[0] === g.city; })[0];
      g.lat = hit ? hit[1] : null; g.lng = hit ? hit[2] : null;
      dy.set(cities.map(function(c){ return {v: c[0], label: c[0]}; }), g.city, !s || !cities.length);
    }
    function loadCountry(first){
      data = null;
      ds.set([], first ? g.state : "", true); dy.set([], first ? g.city : "", true);
      if (!g.country) return;
      getJSON("/geo/" + g.country + ".json").then(function(d){
        data = d;
        if (first && g.city && !g.state){          // older profiles saved only a city - find its state
          var fc = fold(g.city);
          d.s.forEach(function(s){ if (!g.state && s.c.some(function(c){ return fold(c[0]) === fc; })) g.state = s.n; });
          d.s.forEach(function(s){ s.c.forEach(function(c){ if (fold(c[0]) === fc) g.city = c[0]; }); });
        }
        ds.set(d.s.map(function(s){ return {v: s.n, label: s.n}; }), g.state, !d.s.length);
        fillCities();
        if (first && (g.state || g.city)) emit();
      }).catch(function(){});
    }
    dc.onPick = function(v){ g.country = v; g.state = ""; g.city = ""; g.lat = g.lng = null; loadCountry(false); emit(); };
    ds.onPick = function(v){ g.state = v; g.city = ""; fillCities(); emit(); };
    dy.onPick = function(v){ g.city = v; fillCities(); emit(); };
    getJSON("/geo/countries.json").then(function(list){
      dc.set(list.map(function(c){ return {v: c.c, label: c.n, flag: c.c}; }), g.country, false);
      if (g.country) loadCountry(true);
    }).catch(function(){ el.insertAdjacentHTML("beforeend", "<p style='color:#DC2626;font-size:13px'>Could not load the country list.</p>"); });
    return {get: function(){ return g; }};
  };
})();
