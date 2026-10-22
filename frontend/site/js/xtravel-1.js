/* XpertCreation Hotels & Tours: /hotels, /hotels?h=slug, /tours, /tours?t=slug, /my-trips, /travel-manage
   Guests book free and pay at the hotel / to the tour operator. Only KYC-verified companies list; the team approves listings. */
(function(){
  "use strict";
  var D = document, B = D.body, P = location.pathname.replace(/\/+$/, ""), Q = new URLSearchParams(location.search);
  var app = D.getElementById("xtr");
  var AM = {wifi: ["📶", "Wi-Fi"], parking: ["🅿️", "Parking"], breakfast: ["🍳", "Breakfast"], ac: ["❄️", "AC"], heating: ["🔥", "Heating"],
    hot_water: ["🚿", "Hot water"], tv: ["📺", "TV"], restaurant: ["🍽️", "Restaurant"], room_service: ["🛎️", "Room service"], family: ["👪", "Family friendly"],
    prayer_room: ["🕌", "Prayer room"], generator: ["⚡", "Backup power"], pool: ["🏊", "Pool"], gym: ["🏋️", "Gym"], airport_pickup: ["✈️", "Airport pickup"],
    laundry: ["🧺", "Laundry"], mountain_view: ["🏔️", "Mountain view"], lake_view: ["🌊", "Lake view"], pets: ["🐾", "Pets allowed"], wheelchair: ["♿", "Wheelchair access"]};
  var INC = {hotel: ["🏨", "Hotel stay"], transport: ["🚐", "Transport"], meals: ["🍛", "All meals"], breakfast: ["🍳", "Breakfast"], guide: ["🧭", "Tour guide"],
    tickets: ["🎟️", "Entry tickets"], jeep: ["🚙", "Jeep rides"], flights: ["✈️", "Flights"], visa: ["🛂", "Visa help"], insurance: ["🛡️", "Insurance"],
    photos: ["📸", "Photography"], bonfire: ["🔥", "Bonfire night"]};
  var ST = {pending: ["#B45309", "#FEF3C7"], confirmed: ["#15803D", "#DCFCE7"], checked_in: ["#1D4ED8", "#DBEAFE"], done: ["#334155", "#E2E8F0"], declined: ["#B91C1C", "#FEE2E2"], cancelled: ["#64748B", "#F1F5F9"], no_show: ["#B91C1C", "#FEE2E2"]};

  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }
  function api(url, body, method){
    var o = {method: method || (body ? "POST" : "GET"), credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}};
    if (body instanceof FormData) o.body = body; else if (body){ o.body = JSON.stringify(body); o.headers["Content-Type"] = "application/json"; }
    return fetch("/api/travel/" + url, o).then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ d._s = r.status; d._ok = r.ok; return d; }); })
      .catch(function(){ return {_ok: false, _s: 0, detail: "No internet. Try again."}; });
  }
  function rs(n){ return "Rs " + Number(n || 0).toLocaleString("en-PK"); }
  function iso(d){ return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
  function addDays(s, n){ var d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return iso(d); }
  function nice(s){ if (!s) return ""; var d = new Date(s + "T00:00:00"); return d.toLocaleDateString("en-GB", {weekday: "short", day: "numeric", month: "short"}); }
  function toast(t){ var e = D.createElement("div"); e.className = "tr-toast"; e.textContent = t; B.appendChild(e); setTimeout(function(){ e.remove(); }, 2800); }
  function stars(n){ n = +n || 0; return n ? '<span class="tr-st">' + "★".repeat(n) + "</span>" : ""; }
  function rating(x){ return x.reviews ? '<span class="tr-rate">⭐ ' + x.rating + " <small>(" + x.reviews + ")</small></span>" : '<span class="tr-new">New</span>'; }
  function badge(s, label){ var c = ST[s] || ["#334155", "#E2E8F0"]; return '<span class="tr-badge" style="color:' + c[0] + ";background:" + c[1] + '">' + esc(label || s) + "</span>"; }
  function wa(n, text){ n = String(n || "").replace(/[^\d]/g, ""); if (n.charAt(0) === "0") n = "92" + n.slice(1); return "https://wa.me/" + n + (text ? "?text=" + encodeURIComponent(text) : ""); }
  function sheet(html){ var ov = D.createElement("div"); ov.className = "tr-sh"; ov.innerHTML = '<div class="tr-box"><div class="tr-grab"></div>' + html + "</div>"; ov.addEventListener("click", function(e){ if (e.target === ov || e.target.closest("[data-x]")) ov.remove(); }); B.appendChild(ov); return ov; }
  function signin(){ location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search); }
  var TODAY = iso(new Date());

  var css = D.createElement("style");
  css.textContent = [
    ".tr{max-width:980px;width:100%;flex:1;margin:0 auto;padding:12px 15px 60px;color:#0D1424;box-sizing:border-box}",
    ".tr ol{padding-left:22px;margin:8px 0}.tr p{margin:6px 0}.tr-h1{font-family:var(--display,inherit);font-weight:800}",
    ".tr-tabs{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;margin:4px 0 14px}.tr-tabs::-webkit-scrollbar{display:none}",
    ".tr-tabs a{flex:0 0 auto;padding:9px 14px;border-radius:99px;border:1.5px solid #E4E8F2;background:#fff;color:#0D1424;font-weight:800;font-size:14px;text-decoration:none}",
    ".tr-tabs a.on{background:#0D1424;color:#fff;border-color:#0D1424}",
    ".tr-hero{background:linear-gradient(135deg,#0B3B5C,#0E7490 55%,#14B8A6);color:#fff;border-radius:22px;padding:20px 18px;margin-bottom:14px}",
    ".tr-hero h1{margin:0 0 4px;font-size:25px;letter-spacing:-.02em}.tr-hero p{margin:0 0 12px;opacity:.9;font-size:14px}",
    "@font-face{font-family:'Noto Nastaliq Urdu';font-style:normal;font-weight:700;font-display:swap;src:url(/fonts/noto-nastaliq-urdu-700.woff2) format('woff2')}",
    ".tr-hero .ur{font-family:'Noto Nastaliq Urdu',serif;font-weight:700;direction:rtl;font-size:15px;line-height:2.1;opacity:.92;margin-bottom:8px}",
    ".tr-search{display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;gap:8px}",
    "@media(max-width:720px){.tr-search{grid-template-columns:1fr 1fr}.tr-search .w{grid-column:1/-1}.tr-search button{grid-column:1/-1}}",
    ".tr-search label{display:flex;flex-direction:column;font-size:11px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;opacity:.95;gap:4px}",
    ".tr-search input,.tr-search select{border:0;border-radius:12px;padding:12px;font:inherit;font-size:15px;color:#0D1424;background:#fff;width:100%;box-sizing:border-box}",
    ".tr-btn{border:0;border-radius:13px;padding:12px 16px;font:inherit;font-weight:800;font-size:14.5px;cursor:pointer;background:#0D1424;color:#fff;text-decoration:none;display:inline-block;text-align:center}",
    ".tr-btn.g{background:#16A34A}.tr-btn.o{background:#fff;color:#0D1424;border:1.5px solid #E4E8F2}.tr-btn.b{background:#0E7490}.tr-btn.r{background:#fff;color:#B91C1C;border:1.5px solid #FCA5A5}.tr-btn.wa{background:#25D366}",
    ".tr-btn:disabled{opacity:.5}.tr-btn.s{padding:8px 11px;font-size:13px;border-radius:10px}",
    ".tr-chips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}.tr-chips button{border:1.5px solid #E4E8F2;background:#fff;border-radius:99px;padding:7px 12px;font:inherit;font-size:13px;font-weight:700;cursor:pointer}",
    ".tr-chips button.on{background:#0E7490;color:#fff;border-color:#0E7490}",
    ".tr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}",
    ".tr-card{background:#fff;border:1px solid #E4E8F2;border-radius:18px;overflow:hidden;text-decoration:none;color:inherit;display:flex;flex-direction:column}",
    ".tr-card .ph{aspect-ratio:3/2;background:#E2E8F0 center/cover no-repeat;position:relative}.tr-card .ph span{position:absolute;left:10px;top:10px}",
    ".tr-card .bd{padding:11px 13px 13px;display:flex;flex-direction:column;gap:3px}.tr-card b{font-size:15.5px}.tr-card small{color:#5A657C;font-size:12.5px}",
    ".tr-card .pr{display:flex;align-items:baseline;justify-content:space-between;margin-top:6px}.tr-card .pr strong{font-size:17px}.tr-card .pr em{font-style:normal;font-size:12px;color:#5A657C}",
    ".tr-st{color:#F59E0B;font-size:12px;letter-spacing:1px}.tr-rate{font-size:13px;font-weight:800}.tr-rate small{color:#5A657C;font-weight:600}.tr-new{font-size:11.5px;font-weight:800;color:#0E7490;background:#CCFBF1;border-radius:7px;padding:2px 7px}",
    ".tr-badge{font-size:11.5px;font-weight:800;border-radius:8px;padding:3px 8px;display:inline-block}",
    ".tr-feat{background:#F59E0B;color:#fff;font-size:11px;font-weight:900;border-radius:7px;padding:3px 7px}",
    ".tr-empty{text-align:center;color:#5A657C;padding:36px 10px}.tr-empty div{font-size:46px}",
    ".tr-gal{display:flex;gap:6px;overflow-x:auto;scroll-snap-type:x mandatory;border-radius:18px;margin-bottom:12px;scrollbar-width:none}.tr-gal::-webkit-scrollbar{display:none}",
    ".tr-gal img{flex:0 0 88%;max-width:620px;aspect-ratio:3/2;object-fit:cover;border-radius:16px;scroll-snap-align:start;background:#E2E8F0}",
    ".tr-gal.one img{flex-basis:100%}",
    ".tr-h1{font-size:24px;margin:2px 0;letter-spacing:-.02em}.tr-sub{color:#5A657C;font-size:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}",
    ".tr-sec{background:#fff;border:1px solid #E4E8F2;border-radius:18px;padding:14px 15px;margin-top:12px}.tr-sec h3{margin:0 0 8px;font-size:16px}",
    ".tr-am{display:flex;flex-wrap:wrap;gap:6px}.tr-am span{background:#F1F5F9;border-radius:10px;padding:6px 9px;font-size:13px;font-weight:600}",
    ".tr-room{display:flex;gap:12px;padding:12px 0;border-top:1px solid #EEF1F6}.tr-room:first-child{border-top:0}",
    ".tr-room .rp{width:96px;height:72px;border-radius:12px;background:#E2E8F0 center/cover;flex:0 0 auto}.tr-room .rb{flex:1;min-width:0}.tr-room .rb b{display:block}",
    ".tr-room .rr{text-align:right;display:flex;flex-direction:column;gap:6px;align-items:flex-end}.tr-room .rr strong{font-size:16px}",
    "@media(max-width:560px){.tr-dates{grid-template-columns:1fr 1fr!important}.tr-dates label:nth-child(3){grid-column:1/-1}.tr-room{flex-wrap:wrap}.tr-room .rb{flex-basis:calc(100% - 110px)}.tr-room .rr{flex-direction:row;flex-wrap:wrap;width:100%;align-items:center;justify-content:flex-end;text-align:left}.tr-room .rr strong{margin-right:auto}}",
    ".tr-dates{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}.tr-dates label{font-size:11px;font-weight:800;color:#5A657C;text-transform:uppercase;display:flex;flex-direction:column;gap:4px}",
    ".tr-dates input,.tr-dates select{min-width:0;width:100%;box-sizing:border-box;border:1.5px solid #E4E8F2;border-radius:12px;padding:10px;font:inherit;font-size:14.5px;background:#F6F7FB}",
    ".tr-sh{position:fixed;inset:0;z-index:2147483100;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}",
    ".tr-box{background:#fff;width:100%;max-width:560px;max-height:92vh;overflow:auto;border-radius:22px 22px 0 0;padding:10px 18px calc(18px + env(safe-area-inset-bottom));color:#0D1424}",
    "@media(min-width:700px){.tr-sh{align-items:center}.tr-box{border-radius:22px}}",
    ".tr-grab{width:44px;height:5px;border-radius:9px;background:#D6DCE8;margin:2px auto 12px}",
    ".tr-box h3{margin:0 0 8px}.tr-box label.l{display:block;font-size:11.5px;font-weight:800;color:#5A657C;text-transform:uppercase;letter-spacing:.03em;margin:11px 0 5px}",
    ".tr-box input,.tr-box select,.tr-box textarea{width:100%;box-sizing:border-box;padding:11px 12px;border:1.5px solid #E4E8F2;border-radius:12px;font:inherit;font-size:15px;background:#F6F7FB;color:#0D1424}",
    ".tr-box textarea{min-height:80px}.tr-row2{display:grid;grid-template-columns:1fr 1fr;gap:8px}.tr-row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}",
    ".tr-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.tr-hint{font-size:12.5px;color:#5A657C;line-height:1.5}",
    ".tr-sum{background:#F0FDFA;border:1px solid #99F6E4;border-radius:14px;padding:11px 13px;font-size:14px;margin-top:10px}",
    ".tr-ok{text-align:center}.tr-ok .big{font-size:48px}.tr-ok .code{font-family:ui-monospace,monospace;font-size:22px;font-weight:900;letter-spacing:.1em;background:#F1F5F9;border-radius:10px;padding:6px 12px;display:inline-block}",
    ".tr-bk{background:#fff;border:1px solid #E4E8F2;border-radius:16px;padding:12px 14px;margin-bottom:10px}.tr-bk .top{display:flex;gap:8px;align-items:center;justify-content:space-between}",
    ".tr-bk .meta{font-size:13.5px;color:#334155;margin-top:4px;line-height:1.6}.tr-bk .meta b{color:#0D1424}",
    ".tr-it{border-left:3px solid #14B8A6;padding:2px 0 10px 12px;margin-left:6px}.tr-it b{display:block}.tr-it p{margin:3px 0 0;font-size:14px;color:#334155;white-space:pre-line}",
    ".tr-deps{display:flex;gap:6px;flex-wrap:wrap}.tr-deps button{border:1.5px solid #E4E8F2;background:#fff;border-radius:12px;padding:8px 10px;font:inherit;font-size:13px;cursor:pointer;text-align:left}",
    ".tr-deps button.on{border-color:#0E7490;background:#F0FDFA}.tr-deps button small{display:block;color:#5A657C;font-size:11.5px}.tr-deps button:disabled{opacity:.45}",
    ".tr-cal{overflow-x:auto}.tr-cal table{border-collapse:collapse;font-size:12px}.tr-cal th,.tr-cal td{border:1px solid #E4E8F2;padding:4px;text-align:center;min-width:30px}",
    ".tr-cal th:first-child,.tr-cal td:first-child{position:sticky;left:0;background:#fff;text-align:left;min-width:110px;font-weight:700}",
    ".tr-cal td.f{background:#DCFCE7;color:#166534}.tr-cal td.p{background:#FEF3C7}.tr-cal td.x{background:#FEE2E2;color:#991B1B}.tr-cal td.t{outline:2px solid #0E7490}",
    ".tr-checks{display:flex;flex-wrap:wrap;gap:6px}.tr-checks label{display:flex;gap:5px;align-items:center;border:1.5px solid #E4E8F2;border-radius:10px;padding:6px 9px;font-size:13px;cursor:pointer;background:#fff}",
    ".tr-checks input{width:auto}.tr-pics{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.tr-pics div{position:relative;width:92px;height:62px;border-radius:10px;background:#E2E8F0 center/cover}",
    ".tr-pics button{position:absolute;border:0;border-radius:7px;font-size:11px;font-weight:800;padding:2px 6px;cursor:pointer}.tr-pics .rm{right:3px;top:3px;background:#fff;color:#B91C1C}.tr-pics .cv{left:3px;bottom:3px;background:rgba(0,0,0,.6);color:#fff}",
    ".tr-toast{position:fixed;left:50%;bottom:110px;transform:translateX(-50%);background:#0D1424;color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;z-index:2147483600;max-width:90%}",
    ".tr-note{background:#FFFBEB;border:1px solid #FDE68A;border-radius:14px;padding:10px 12px;font-size:13.5px;margin:10px 0}",
    ".tr-mini{display:flex;gap:10px;align-items:center;padding:10px 0;border-top:1px solid #EEF1F6}.tr-mini:first-child{border-top:0}.tr-mini .ph{width:64px;height:46px;border-radius:9px;background:#E2E8F0 center/cover;flex:0 0 auto}.tr-mini .t{flex:1;min-width:0}"
  ].join("\n");
  D.head.appendChild(css);

  function tabs(on, extra){
    return '<div class="tr-tabs"><a href="/hotels"' + (on === "h" ? ' class="on"' : "") + '>🏨 Hotels</a><a href="/tours"' + (on === "t" ? ' class="on"' : "") + '>🧳 Tours</a><a href="/my-trips"' + (on === "m" ? ' class="on"' : "") + '>📅 My trips</a><a href="/travel-manage"' + (on === "o" ? ' class="on"' : "") + ">💼 List & sell</a>" + (extra || "") + "</div>";
  }

  /* ================================================================ hotels list */
  function hotelList(){
    var st = {q: Q.get("q") || "", a: Q.get("in") || "", b: Q.get("out") || "", g: Q.get("guests") || "2", kind: "", sort: ""};
    app.innerHTML = '<div class="tr">' + tabs("h") + '<div class="tr-hero"><h1>Find a hotel or guest house</h1><div class="ur">ہوٹل اور گیسٹ ہاؤس بک کریں — ادائیگی ہوٹل پر</div><p>Book free and pay at the hotel. Every place is run by a KYC-verified company.</p>'
      + '<form class="tr-search" data-f><label class="w">Where<input name="q" placeholder="City or area, e.g. Murree, Hunza, Lahore" value="' + esc(st.q) + '"></label>'
      + '<label>Check-in<input name="in" type="date" min="' + TODAY + '" value="' + esc(st.a) + '"></label><label>Check-out<input name="out" type="date" min="' + addDays(TODAY, 1) + '" value="' + esc(st.b) + '"></label>'
      + '<label>Guests<select name="guests">' + [1, 2, 3, 4, 5, 6, 8, 10, 15, 20].map(function(n){ return "<option" + (String(n) === st.g ? " selected" : "") + ">" + n + "</option>"; }).join("") + '</select></label><button class="tr-btn g">Search</button></form></div>'
      + '<div class="tr-chips" data-cities></div><div class="tr-chips" data-kinds></div><div data-res><p class="tr-hint">Loading…</p></div></div>';
    var f = app.querySelector("[data-f]");
    f.in.addEventListener("change", function(){ if (f.in.value && (!f.out.value || f.out.value <= f.in.value)) f.out.value = addDays(f.in.value, 1); f.out.min = f.in.value ? addDays(f.in.value, 1) : addDays(TODAY, 1); });
    f.addEventListener("submit", function(e){ e.preventDefault(); st.q = f.q.value.trim(); st.a = f.in.value; st.b = f.out.value; st.g = f.guests.value; load(); try { history.replaceState(null, "", "/hotels?" + new URLSearchParams({q: st.q, in: st.a, out: st.b, guests: st.g})); } catch (x) {} });
    var kinds = [["", "All"], ["hotel", "Hotels"], ["guesthouse", "Guest houses"], ["resort", "Resorts"], ["apartment", "Apartments"], ["hostel", "Hostels"], ["camp", "Camps / huts"]];
    app.querySelector("[data-kinds]").innerHTML = kinds.map(function(k){ return '<button data-k="' + k[0] + '"' + (k[0] === st.kind ? ' class="on"' : "") + ">" + k[1] + "</button>"; }).join("") + '<button data-sort="price">↓ Lowest price</button>';
    app.querySelector("[data-kinds]").addEventListener("click", function(e){ var b = e.target.closest("button"); if (!b) return; if (b.hasAttribute("data-sort")){ st.sort = st.sort ? "" : "price"; b.classList.toggle("on"); } else { st.kind = b.getAttribute("data-k"); [].forEach.call(this.querySelectorAll("[data-k]"), function(x){ x.classList.toggle("on", x === b); }); } load(); });
    function load(){
      var box = app.querySelector("[data-res]"); box.innerHTML = '<p class="tr-hint">Searching…</p>';
      api("hotels/?" + new URLSearchParams({q: st.q, in: st.a, out: st.b, guests: st.g, kind: st.kind, sort: st.sort})).then(function(d){
        app.querySelector("[data-cities]").innerHTML = (d.cities || []).map(function(c){ return '<button data-c="' + esc(c.city) + '"' + (st.q.toLowerCase() === c.city.toLowerCase() ? ' class="on"' : "") + ">📍 " + esc(c.city) + " <small>" + c.n + "</small></button>"; }).join("");
        var L = d.hotels || [], dates = st.a && st.b ? "&in=" + st.a + "&out=" + st.b + "&guests=" + st.g : "";
        box.innerHTML = L.length ? '<div class="tr-grid">' + L.map(function(h){
          return '<a class="tr-card" href="' + h.url + dates + '"><div class="ph" style="background-image:url(\'' + esc(h.photo) + '\')">' + (h.featured ? '<span class="tr-feat">FEATURED</span>' : "") + "</div><div class=\"bd\"><b>" + esc(h.name) + "</b>"
            + "<small>" + esc(h.kind_label) + (h.stars ? " · " + stars(h.stars) : "") + " · 📍 " + esc(h.area ? h.area + ", " : "") + esc(h.city) + "</small>"
            + '<div class="pr"><span>' + rating(h) + (h.available === false ? ' <span class="tr-badge" style="color:#B91C1C;background:#FEE2E2">Full on your dates</span>' : h.available ? ' <span class="tr-badge" style="color:#15803D;background:#DCFCE7">Available</span>' : "") + "</span><span><em>from</em> <strong>" + rs(h.from) + "</strong><em>/night</em></span></div></div></a>";
        }).join("") + "</div>" : '<div class="tr-empty"><div>🏨</div><p>No places found' + (st.q ? " in “" + esc(st.q) + "”" : "") + ' yet.</p><p class="tr-hint">Hotels are joining every day. Own a hotel or guest house? <a href="/travel-manage">List it free</a>.</p></div>';
      });
    }
    app.querySelector("[data-cities]").addEventListener("click", function(e){ var b = e.target.closest("[data-c]"); if (!b) return; f.q.value = st.q = b.getAttribute("data-c"); load(); });
    load();
  }

  /* ================================================================ one hotel */
  function hotelPage(slug){
    var a = Q.get("in") || "", b = Q.get("out") || "", g = Q.get("guests") || "2";
    app.innerHTML = '<div class="tr">' + tabs("h") + '<p class="tr-hint">Loading…</p></div>';
    function load(){
      api("hotels/" + encodeURIComponent(slug) + "/?" + new URLSearchParams({in: a, out: b})).then(function(h){
        if (!h._ok){ app.innerHTML = '<div class="tr">' + tabs("h") + '<div class="tr-empty"><div>🔎</div><p>' + esc(h.detail || "Not found") + '</p><a class="tr-btn" href="/hotels">See all hotels</a></div></div>'; return; }
        document.title = h.name + " — " + h.city + " — XpertCreation";
        var gal = h.photos.length ? '<div class="tr-gal' + (h.photos.length === 1 ? " one" : "") + '">' + h.photos.map(function(p){ return '<img src="' + esc(p) + '" alt="' + esc(h.name) + '" loading="lazy">'; }).join("") + "</div>" : "";
        var rooms = h.rooms.filter(function(r){ return r.active; });
        app.innerHTML = '<div class="tr">' + tabs("h") + (h.preview ? '<div class="tr-note">👁️ Preview — this place is not live yet (waiting for review).</div>' : "") + gal
          + '<h1 class="tr-h1">' + esc(h.name) + " " + stars(h.stars) + '</h1><div class="tr-sub"><span>' + esc(h.kind_label) + "</span><span>📍 " + esc(h.area ? h.area + ", " : "") + esc(h.city) + "</span>" + rating(h)
          + '<span class="tr-badge" style="color:#15803D;background:#DCFCE7">✔ ' + esc(h.company.name) + " (verified)</span></div>"
          + '<div class="tr-sec"><h3>📅 Your dates</h3><div class="tr-dates"><label>Check-in<input data-a type="date" min="' + TODAY + '" value="' + esc(a) + '"></label><label>Check-out<input data-b type="date" min="' + addDays(TODAY, 1) + '" value="' + esc(b) + '"></label>'
          + '<label>Guests<select data-g>' + [1, 2, 3, 4, 5, 6, 8, 10, 15, 20].map(function(n){ return "<option" + (String(n) === g ? " selected" : "") + ">" + n + "</option>"; }).join("") + "</select></label></div>"
          + '<p class="tr-hint" style="margin:8px 0 0">Check-in from ' + esc(h.check_in) + " · check-out by " + esc(h.check_out) + " · <b>Pay at the hotel</b> — booking is free.</p></div>"
          + '<div class="tr-sec"><h3>🛏️ Rooms</h3>' + (rooms.length ? rooms.map(function(r){
              var full = a && b && r.free === 0;
              return '<div class="tr-room"><div class="rp" style="background-image:url(\'' + esc(r.photos[0] || h.photos[0] || "") + '\')"></div><div class="rb"><b>' + esc(r.name) + "</b><small class=\"tr-hint\">👤 up to " + r.adults + " adults" + (r.beds ? " · " + esc(r.beds) : "") + "</small>"
                + (r.about ? '<div class="tr-hint">' + esc(r.about) + "</div>" : "") + (r.amenities.length ? '<div class="tr-hint">' + r.amenities.slice(0, 6).map(function(x){ return (AM[x] || ["", x])[0] + " " + (AM[x] || ["", x])[1]; }).join(" · ") + "</div>" : "") + "</div>"
                + '<div class="rr"><strong>' + rs(r.price) + '</strong><small class="tr-hint">per night</small>' + (a && b ? (full ? badge("declined", "Full") : '<small class="tr-hint">' + r.free + " left · " + rs(r.total) + " for " + r.nights + " night" + (r.nights === 1 ? "" : "s") + "</small>") : "")
                + '<button class="tr-btn g s" data-book="' + r.id + '"' + (full ? " disabled" : "") + ">Book</button></div></div>";
            }).join("") : '<p class="tr-hint">No rooms listed yet.</p>') + "</div>"
          + (h.amenities.length ? '<div class="tr-sec"><h3>What this place offers</h3><div class="tr-am">' + h.amenities.map(function(x){ return "<span>" + (AM[x] || ["", x]).join(" ") + "</span>"; }).join("") + "</div></div>" : "")
          + (h.about ? '<div class="tr-sec"><h3>About</h3><p style="white-space:pre-line;margin:0;font-size:14.5px;line-height:1.6">' + esc(h.about) + "</p></div>" : "")
          + '<div class="tr-sec"><h3>📍 Location</h3><p style="margin:0">' + esc(h.address || h.city) + "</p>" + (h.map_url ? '<p><a class="tr-btn o s" target="_blank" rel="noopener" href="' + esc(h.map_url) + '">Open in Maps</a></p>' : "") + "</div>"
          + (h.policies ? '<div class="tr-sec"><h3>House rules</h3><p style="white-space:pre-line;margin:0;font-size:14px">' + esc(h.policies) + "</p></div>" : "")
          + '<div class="tr-sec"><h3>⭐ Reviews from guests who stayed</h3>' + (h.review_list.length ? h.review_list.map(function(r){ return '<div class="tr-mini"><div class="t"><b>' + "★".repeat(r.stars) + "</b> <small class=\"tr-hint\">" + esc(r.name) + " · " + esc(r.when) + "</small><div>" + esc(r.text) + "</div></div></div>"; }).join("") : '<p class="tr-hint">No reviews yet. Only guests who completed a stay can review.</p>') + "</div></div>";
        var fa = app.querySelector("[data-a]"), fb = app.querySelector("[data-b]");
        function re(){ a = fa.value; b = fb.value; g = app.querySelector("[data-g]").value; if (a && (!b || b <= a)){ b = addDays(a, 1); fb.value = b; } if (a && b) { try { history.replaceState(null, "", "/hotels?" + new URLSearchParams({h: slug, in: a, out: b, guests: g})); } catch (x) {} load(); } }
        fa.onchange = re; fb.onchange = re; app.querySelector("[data-g]").onchange = function(){ g = this.value; };
        app.querySelectorAll("[data-book]").forEach(function(btn){ btn.onclick = function(){ var r = rooms.filter(function(x){ return String(x.id) === btn.getAttribute("data-book"); })[0]; bookRoom(h, r); }; });
      });
    }
    function bookRoom(h, r){
      if (!a || !b){ toast("Pick your check-in and check-out dates first."); app.querySelector("[data-a]").focus(); return; }
      var n = Math.round((new Date(b) - new Date(a)) / 864e5), need = Math.max(1, Math.ceil((+g) / (r.adults + 1)));
      var ov = sheet("<h3>Book " + esc(r.name) + '</h3><div class="tr-hint">' + esc(h.name) + " · " + nice(a) + " → " + nice(b) + " · " + n + " night" + (n === 1 ? "" : "s") + "</div>"
        + '<div class="tr-row2"><div><label class="l">Rooms</label><select name="rooms">' + Array.from({length: Math.max(1, Math.min(r.free || r.count, 20))}, function(_, i){ return "<option" + (i + 1 === need ? " selected" : "") + ">" + (i + 1) + "</option>"; }).join("") + '</select></div><div><label class="l">Guests</label><input name="guests" type="number" min="1" max="60" value="' + esc(g) + '"></div></div>'
        + '<label class="l">Your name</label><input name="name" maxlength="80" autocomplete="name"><label class="l">Phone (the hotel will call or WhatsApp you)</label><input name="phone" type="tel" maxlength="30" autocomplete="tel" placeholder="03xx xxxxxxx">'
        + '<label class="l">Message to the hotel (optional)</label><textarea name="note" maxlength="300" placeholder="e.g. arriving late, need an extra bed"></textarea>'
        + '<div class="tr-sum" data-sum></div><p class="tr-hint">Free booking — you pay ' + esc(h.company.name) + " at the hotel. The hotel confirms your booking; you get a notification.</p>"
        + '<div class="tr-acts"><button class="tr-btn o" data-x>Cancel</button><button class="tr-btn g" data-go style="flex:1">Send booking request</button></div>');
      var sum = function(){ var q = +ov.querySelector("[name=rooms]").value; ov.querySelector("[data-sum]").innerHTML = "<b>" + rs(r.price * q * n) + "</b> total · " + q + " room" + (q === 1 ? "" : "s") + " × " + n + " night" + (n === 1 ? "" : "s") + " × " + rs(r.price); };
      sum(); ov.querySelector("[name=rooms]").onchange = sum;
      ov.querySelector("[data-go]").onclick = function(){
        var bt = this, v = function(k){ return ov.querySelector("[name=" + k + "]").value; }; bt.disabled = true;
        api("book/", {room: r.id, in: a, out: b, rooms: v("rooms"), guests: v("guests"), name: v("name"), phone: v("phone"), note: v("note")}).then(function(d){
          if (d._s === 401 || d._s === 403) return signin();
          if (!d._ok){ toast(d.detail || "Could not book."); bt.disabled = false; return; }
          ov.remove(); done(d);
        });
      };
    }
    load();
  }

  function done(bk){
    var c = bk.contact || {};
    sheet('<div class="tr-ok"><div class="big">🎉</div><h3>Booking request sent!</h3><p>Your code</p><div class="code">' + esc(bk.code) + '</div>'
      + '<p class="tr-hint">' + esc(bk.place) + " · " + nice(bk.start) + (bk.end ? " → " + nice(bk.end) : "") + " · " + rs(bk.total) + "<br>The owner will confirm soon — you get a notification. Pay at arrival.</p>"
      + '<div class="tr-acts" style="justify-content:center">' + (c.whatsapp ? '<a class="tr-btn wa" target="_blank" rel="noopener" href="' + wa(c.whatsapp, "Assalam o alaikum, I booked on XpertCreation. Code " + bk.code) + '">WhatsApp the owner</a>' : "") + (c.phone ? '<a class="tr-btn o" href="tel:' + esc(c.phone) + '">📞 Call</a>' : "") + '<a class="tr-btn" href="/my-trips">My trips</a></div></div>');
  }

  /* ================================================================ tours */
  function tourList(){
    var q = Q.get("q") || "", sort = "";
    app.innerHTML = '<div class="tr">' + tabs("t") + '<div class="tr-hero" style="background:linear-gradient(135deg,#7C2D12,#C2410C 55%,#F59E0B)"><h1>Tour packages</h1><div class="ur">ٹور پیکجز — ہنزہ، اسکردو، سوات، عمرہ اور مزید</div><p>Trips designed by verified tour companies. Book free, pay the tour company.</p>'
      + '<form class="tr-search" data-f style="grid-template-columns:1fr auto"><label class="w">Where to?<input name="q" placeholder="e.g. Hunza, Skardu, Swat, Umrah, Dubai" value="' + esc(q) + '"></label><button class="tr-btn g">Search</button></form></div>'
      + '<div class="tr-chips" data-d></div><div data-res><p class="tr-hint">Loading…</p></div></div>';
    var f = app.querySelector("[data-f]");
    f.addEventListener("submit", function(e){ e.preventDefault(); q = f.q.value.trim(); load(); });
    function load(){
      api("tours/?" + new URLSearchParams({q: q, sort: sort})).then(function(d){
        app.querySelector("[data-d]").innerHTML = (d.destinations || []).map(function(x){ return '<button data-q="' + esc(x.destination) + '"' + (q.toLowerCase() === x.destination.toLowerCase() ? ' class="on"' : "") + ">🏔️ " + esc(x.destination) + "</button>"; }).join("") + '<button data-sort="1"' + (sort ? ' class="on"' : "") + ">↓ Lowest price</button>";
        var L = d.tours || [];
        app.querySelector("[data-res]").innerHTML = L.length ? '<div class="tr-grid">' + L.map(function(t){
          return '<a class="tr-card" href="' + t.url + '"><div class="ph" style="background-image:url(\'' + esc(t.photo) + '\')">' + (t.featured ? '<span class="tr-feat">FEATURED</span>' : "") + '</div><div class="bd"><b>' + esc(t.title) + "</b><small>📍 " + esc(t.destination) + (t.start_city ? " · from " + esc(t.start_city) : "") + " · " + t.days + " days / " + t.nights + " nights</small>"
            + '<small>' + (t.includes || []).slice(0, 4).map(function(x){ return (INC[x] || ["", x])[0]; }).join(" ") + " " + (t.next ? "· next: " + nice(t.next) : t.on_request ? "· any date on request" : "") + "</small>"
            + '<div class="pr"><span>' + rating(t) + "</span><span><strong>" + rs(t.price) + "</strong><em>/person</em></span></div></div></a>";
        }).join("") + "</div>" : '<div class="tr-empty"><div>🧳</div><p>No tours found' + (q ? " for “" + esc(q) + "”" : "") + ' yet.</p><p class="tr-hint">Run a tour company? <a href="/travel-manage">Design and sell your package</a>.</p></div>';
      });
    }
    app.querySelector("[data-d]").addEventListener("click", function(e){ var b = e.target.closest("button"); if (!b) return; if (b.hasAttribute("data-sort")) sort = sort ? "" : "price"; else { q = b.getAttribute("data-q"); f.q.value = q; } load(); });
    load();
  }

  function tourPage(slug){
    app.innerHTML = '<div class="tr">' + tabs("t") + '<p class="tr-hint">Loading…</p></div>';
    api("tours/" + encodeURIComponent(slug) + "/").then(function(t){
      if (!t._ok){ app.innerHTML = '<div class="tr">' + tabs("t") + '<div class="tr-empty"><div>🔎</div><p>' + esc(t.detail || "Not found") + '</p><a class="tr-btn" href="/tours">See all tours</a></div></div>'; return; }
      document.title = t.title + " — XpertCreation tours";
      var pick = null;
      app.innerHTML = '<div class="tr">' + tabs("t") + (t.preview ? '<div class="tr-note">👁️ Preview — this tour is not live yet (waiting for review).</div>' : "")
        + (t.photos.length ? '<div class="tr-gal' + (t.photos.length === 1 ? " one" : "") + '">' + t.photos.map(function(p){ return '<img src="' + esc(p) + '" alt="' + esc(t.title) + '" loading="lazy">'; }).join("") + "</div>" : "")
        + '<h1 class="tr-h1">' + esc(t.title) + '</h1><div class="tr-sub"><span>📍 ' + esc(t.destination) + "</span>" + (t.start_city ? "<span>from " + esc(t.start_city) + "</span>" : "") + "<span>🗓️ " + t.days + " days / " + t.nights + " nights</span>" + rating(t)
        + '<span class="tr-badge" style="color:#15803D;background:#DCFCE7">✔ ' + esc(t.company.name) + " (verified)</span></div>"
        + '<div class="tr-sec"><h3>' + rs(t.price) + ' <small class="tr-hint">per person' + (t.child_price ? " · child " + rs(t.child_price) : "") + "</small></h3>"
        + (t.departures.length ? '<label class="tr-hint">Pick a departure</label><div class="tr-deps">' + t.departures.map(function(d){ return '<button data-d="' + d.d + '"' + (d.left === 0 ? " disabled" : "") + ">" + nice(d.d) + "<small>" + (d.left === 0 ? "Full" : d.left + " seats left") + "</small></button>"; }).join("") + "</div>"
          : '<div class="tr-dates" style="grid-template-columns:1fr"><label>Travel date (on request)<input data-dd type="date" min="' + addDays(TODAY, 1) + '"></label></div>')
        + '<div class="tr-acts"><button class="tr-btn g" data-book style="flex:1">Book this tour</button>' + (t.whatsapp ? '<a class="tr-btn wa" target="_blank" rel="noopener" href="' + wa(t.whatsapp, "Assalam o alaikum, I saw your tour \"" + t.title + "\" on XpertCreation.") + '">Ask on WhatsApp</a>' : "") + "</div>"
        + '<p class="tr-hint">Free booking — you pay ' + esc(t.company.name) + " directly. Up to " + t.max_group + " people per booking.</p></div>"
        + ((t.includes.length || t.excludes.length) ? '<div class="tr-sec"><h3>What’s included</h3><div class="tr-am">' + t.includes.map(function(x){ return "<span>✅ " + (INC[x] || ["", x]).join(" ") + "</span>"; }).join("") + "</div>"
          + (t.excludes.length ? '<p class="tr-hint" style="margin:10px 0 0"><b>Not included:</b> ' + t.excludes.map(esc).join(" · ") + "</p>" : "") + "</div>" : "")
        + (t.itinerary.length ? '<div class="tr-sec"><h3>🗺️ Day by day</h3>' + t.itinerary.map(function(d, i){ return '<div class="tr-it"><b>Day ' + (i + 1) + ": " + esc(d.t) + "</b>" + (d.x ? "<p>" + esc(d.x) + "</p>" : "") + "</div>"; }).join("") + "</div>" : "")
        + (t.about ? '<div class="tr-sec"><h3>About this trip</h3><p style="white-space:pre-line;margin:0;font-size:14.5px;line-height:1.6">' + esc(t.about) + "</p></div>" : "")
        + '<div class="tr-sec"><h3>⭐ Reviews from travellers</h3>' + (t.review_list.length ? t.review_list.map(function(r){ return '<div class="tr-mini"><div class="t"><b>' + "★".repeat(r.stars) + "</b> <small class=\"tr-hint\">" + esc(r.name) + " · " + esc(r.when) + "</small><div>" + esc(r.text) + "</div></div></div>"; }).join("") : '<p class="tr-hint">No reviews yet. Only travellers who completed the tour can review.</p>') + "</div></div>";
      app.querySelectorAll("[data-d]").forEach(function(b){ b.onclick = function(){ pick = b.getAttribute("data-d"); app.querySelectorAll("[data-d]").forEach(function(x){ x.classList.toggle("on", x === b); }); }; });
      app.querySelector("[data-book]").onclick = function(){
        var d = pick || (app.querySelector("[data-dd]") && app.querySelector("[data-dd]").value);
        if (!d){ toast("Pick a date first."); return; }
        var ov = sheet("<h3>Book: " + esc(t.title) + '</h3><div class="tr-hint">' + nice(d) + " · " + t.days + " days</div>"
          + '<div class="tr-row2"><div><label class="l">Adults</label><input name="adults" type="number" min="1" max="' + t.max_group + '" value="2"></div><div><label class="l">Children</label><input name="children" type="number" min="0" max="' + t.max_group + '" value="0"></div></div>'
          + '<label class="l">Your name</label><input name="name" maxlength="80" autocomplete="name"><label class="l">Phone (the company will call or WhatsApp you)</label><input name="phone" type="tel" maxlength="30" autocomplete="tel" placeholder="03xx xxxxxxx">'
          + '<label class="l">Message (optional)</label><textarea name="note" maxlength="300" placeholder="e.g. pickup point, food needs"></textarea><div class="tr-sum" data-sum></div>'
          + '<div class="tr-acts"><button class="tr-btn o" data-x>Cancel</button><button class="tr-btn g" data-go style="flex:1">Send booking request</button></div>');
        var sum = function(){ var A = +ov.querySelector("[name=adults]").value || 0, C = +ov.querySelector("[name=children]").value || 0; ov.querySelector("[data-sum]").innerHTML = "<b>" + rs(A * t.price + C * (t.child_price || t.price)) + "</b> total · " + A + " adult" + (A === 1 ? "" : "s") + (C ? " + " + C + (C === 1 ? " child" : " children") : ""); };
        sum(); ov.querySelectorAll("[name=adults],[name=children]").forEach(function(i){ i.oninput = sum; });
        ov.querySelector("[data-go]").onclick = function(){
          var bt = this, v = function(k){ return ov.querySelector("[name=" + k + "]").value; }; bt.disabled = true;
          api("tours/" + encodeURIComponent(slug) + "/book/", {date: d, adults: v("adults"), children: v("children"), name: v("name"), phone: v("phone"), note: v("note")}).then(function(x){
            if (x._s === 401 || x._s === 403) return signin();
            if (!x._ok){ toast(x.detail || "Could not book."); bt.disabled = false; return; }
            ov.remove(); done(x);
          });
        };
      };
    });
  }

  /* ================================================================ my trips */
  function myTrips(){
    app.innerHTML = '<div class="tr">' + tabs("m") + '<h1 class="tr-h1">My trips</h1><div data-l><p class="tr-hint">Loading…</p></div></div>';
    api("my/").then(function(d){
      if (d._s === 401 || d._s === 403){ app.querySelector("[data-l]").innerHTML = '<p>Please <a href="/login?next=/my-trips">sign in</a> to see your bookings.</p>'; return; }
      var L = d.bookings || [];
      app.querySelector("[data-l]").innerHTML = L.length ? L.map(function(b){
        var c = b.contact || {};
        return '<div class="tr-bk" id="b' + b.id + '"><div class="top"><b>' + (b.kind === "room" ? "🏨 " : "🧳 ") + '<a href="' + b.place_url + '">' + esc(b.place) + "</a></b>" + badge(b.status, b.status_label) + "</div>"
          + '<div class="meta">' + (b.kind === "room" ? esc(b.room) + " × " + b.qty + " · <b>" + nice(b.start) + " → " + nice(b.end) + "</b> (" + b.nights + " night" + (b.nights === 1 ? "" : "s") + ")" : "<b>" + nice(b.start) + "</b> · " + b.guests + " people")
          + " · <b>" + rs(b.total) + "</b> (pay there)<br>Code <b>" + esc(b.code) + "</b> · " + esc(b.company) + (b.owner_note ? '<br>💬 Owner: ' + esc(b.owner_note) : "") + "</div>"
          + '<div class="tr-acts">' + (c.whatsapp ? '<a class="tr-btn wa s" target="_blank" rel="noopener" href="' + wa(c.whatsapp, "Assalam o alaikum, about my booking " + b.code) + '">WhatsApp</a>' : "") + (c.phone ? '<a class="tr-btn o s" href="tel:' + esc(c.phone) + '">📞 Call</a>' : "")
          + ((b.status === "pending" || b.status === "confirmed") && b.start >= TODAY ? '<button class="tr-btn r s" data-cancel="' + b.id + '">Cancel booking</button>' : "")
          + (b.status === "done" && !b.reviewed ? '<button class="tr-btn b s" data-rev="' + b.id + '">⭐ Review</button>' : "") + "</div></div>";
      }).join("") : '<div class="tr-empty"><div>📅</div><p>No trips yet.</p><a class="tr-btn g" href="/hotels">Find a hotel</a> <a class="tr-btn o" href="/tours">Browse tours</a></div>';
      app.querySelectorAll("[data-cancel]").forEach(function(b){ b.onclick = function(){
        var ov = sheet('<h3>Cancel this booking?</h3><p class="tr-hint">The owner gets a notification.</p><div class="tr-acts"><button class="tr-btn o" data-x>Keep it</button><button class="tr-btn r" data-y>Cancel booking</button></div>');
        ov.querySelector("[data-y]").onclick = function(){ api("my/" + b.getAttribute("data-cancel") + "/cancel/", {}).then(function(x){ ov.remove(); toast(x._ok ? "Cancelled" : (x.detail || "Could not cancel.")); myTrips(); }); };
      }; });
      app.querySelectorAll("[data-rev]").forEach(function(b){ b.onclick = function(){
        var n = 5, ov = sheet('<h3>How was it?</h3><div class="tr-chips" data-s>' + [1, 2, 3, 4, 5].map(function(i){ return '<button data-n="' + i + '"' + (i === 5 ? ' class="on"' : "") + ">" + "★".repeat(i) + "</button>"; }).join("") + '</div><textarea name="t" maxlength="600" placeholder="Tell other travellers (optional)"></textarea><div class="tr-acts"><button class="tr-btn o" data-x>Later</button><button class="tr-btn g" data-y>Post review</button></div>');
        ov.querySelector("[data-s]").onclick = function(e){ var x = e.target.closest("[data-n]"); if (!x) return; n = +x.getAttribute("data-n"); this.querySelectorAll("button").forEach(function(y){ y.classList.toggle("on", y === x); }); };
        ov.querySelector("[data-y]").onclick = function(){ api("my/" + b.getAttribute("data-rev") + "/review/", {stars: n, text: ov.querySelector("[name=t]").value}).then(function(x){ ov.remove(); toast(x._ok ? "Thanks for your review!" : (x.detail || "Could not post.")); myTrips(); }); };
      }; });
      var h = location.hash && D.getElementById(location.hash.slice(1)); if (h) h.scrollIntoView({block: "center"});
    });
  }

  /* ================================================================ owners */
  var M = null, mtab = "b";
  function manage(){
    app.innerHTML = '<div class="tr">' + tabs("o") + '<p class="tr-hint">Loading…</p></div>';
    api("manage/").then(function(d){
      if (d._s === 401 || d._s === 403){ app.innerHTML = '<div class="tr">' + tabs("o") + '<p>Please <a href="/login?next=/travel-manage">sign in</a> first.</p></div>'; return; }
      M = d; drawManage();
    });
  }
  function reload(t){ if (t) mtab = t; api("manage/").then(function(d){ M = d; drawManage(); }); }
  function drawManage(){
    var d = M, hasCo = d.companies.length > 0;
    var h = '<div class="tr">' + tabs("o") + '<h1 class="tr-h1">For hotels & tour companies</h1><p class="tr-hint">List rooms and design tour packages. Guests book free and pay you directly — no commission.</p>';
    if (!hasCo && !d.properties.length && !d.tours.length && !d.is_mod){
      app.innerHTML = h + '<div class="tr-sec"><h3>✔ First, verify your company</h3><p>Only KYC-verified companies can list hotels and tours, so guests can trust every listing.</p><ol style="line-height:1.8"><li>Open your <a href="/company/manage">company page</a> and fill it in.</li><li>Verify your website and send the KYC documents.</li><li>When the team approves it, come back here and add your hotel or tour.</li></ol><a class="tr-btn g" href="/company/manage">Go to my company page</a></div></div>';
      return;
    }
    h += '<div class="tr-chips"><button data-mt="b"' + (mtab === "b" ? ' class="on"' : "") + ">📥 Bookings" + (d.waiting ? " (" + d.waiting + " new)" : "") + '</button><button data-mt="p"' + (mtab === "p" ? ' class="on"' : "") + ">🏨 My places (" + d.properties.length + ')</button><button data-mt="t"' + (mtab === "t" ? ' class="on"' : "") + ">🧳 My tours (" + d.tours.length + ")</button>" + (d.is_mod ? '<button data-mt="r"' + (mtab === "r" ? ' class="on"' : "") + ">🛡️ Team review</button>" : "") + "</div><div data-mb></div></div>";
    app.innerHTML = h;
    app.querySelector(".tr-chips").onclick = function(e){ var b = e.target.closest("[data-mt]"); if (!b) return; mtab = b.getAttribute("data-mt"); drawManage(); };
    var box = app.querySelector("[data-mb]");
    if (mtab === "b") ownerBookings(box); else if (mtab === "p") ownerPlaces(box); else if (mtab === "t") ownerTours(box); else teamReview(box);
  }
  function ownerBookings(box){
    var f = "upcoming";
    function draw(){
      var L = M.bookings.filter(function(b){ return f === "all" ? true : f === "upcoming" ? ["pending", "confirmed", "checked_in"].indexOf(b.status) >= 0 : b.status === f; });
      box.innerHTML = '<div class="tr-chips" data-f>' + [["upcoming", "Upcoming"], ["pending", "Waiting"], ["done", "Completed"], ["all", "All"]].map(function(x){ return '<button data-v="' + x[0] + '"' + (x[0] === f ? ' class="on"' : "") + ">" + x[1] + "</button>"; }).join("") + "</div>"
        + (L.length ? L.map(function(b){
          var acts = {pending: [["confirm", "✅ Confirm", "g"], ["decline", "Decline", "r"]], confirmed: [["checkin", "Check in", "b"], ["noshow", "Did not come", "o"], ["cancel", "Cancel", "r"]], checked_in: [["checkout", "Check out", "g"]]}[b.status] || [];
          return '<div class="tr-bk" id="b' + b.id + '"><div class="top"><b>' + esc(b.name) + " · " + esc(b.code) + "</b>" + badge(b.status, b.status_label) + "</div>"
            + '<div class="meta">' + (b.kind === "room" ? "🏨 " + esc(b.place) + " — " + esc(b.room) + " × " + b.qty + "<br><b>" + nice(b.start) + " → " + nice(b.end) + "</b> · " + b.nights + " night" + (b.nights === 1 ? "" : "s") + " · " + b.guests + " guests" : "🧳 " + esc(b.place) + "<br><b>" + nice(b.start) + "</b> · " + b.qty + " adults" + (b.children ? " + " + b.children + (b.children === 1 ? " child" : " children") : ""))
            + " · <b>" + rs(b.total) + "</b>" + (b.note ? "<br>💬 " + esc(b.note) : "") + "</div>"
            + '<div class="tr-acts"><a class="tr-btn wa s" target="_blank" rel="noopener" href="' + wa(b.phone, "Assalam o alaikum " + b.name + ", about your booking " + b.code + " on XpertCreation") + '">WhatsApp</a><a class="tr-btn o s" href="tel:' + esc(b.phone) + '">📞 ' + esc(b.phone) + "</a>"
            + acts.map(function(a){ return '<button class="tr-btn ' + a[2] + ' s" data-act="' + a[0] + '" data-id="' + b.id + '">' + a[1] + "</button>"; }).join("") + '<button class="tr-btn o s" data-inv="' + b.id + '">🧾 Invoice</button></div></div>';
        }).join("") : '<div class="tr-empty"><div>📥</div><p>No bookings here yet.</p></div>');
      box.querySelector("[data-f]").onclick = function(e){ var b = e.target.closest("[data-v]"); if (!b) return; f = b.getAttribute("data-v"); draw(); };
      box.querySelectorAll("[data-act]").forEach(function(b){ b.onclick = function(){
        var act = b.getAttribute("data-act"), go = function(note){ b.disabled = true; api("manage/bookings/" + b.getAttribute("data-id") + "/", {action: act, note: note || ""}).then(function(x){ if (!x._ok){ toast(x.detail || "Could not."); b.disabled = false; return; } toast("Done ✔"); reload("b"); }); };
        if (act === "confirm" || act === "decline" || act === "cancel"){
          var ov = sheet("<h3>" + (act === "confirm" ? "Confirm booking" : act === "decline" ? "Decline booking" : "Cancel booking") + '</h3><label class="l">Message to the guest (optional)</label><textarea name="n" maxlength="300" placeholder="' + (act === "confirm" ? "e.g. Your room is ready. Call us when you reach Murree." : "e.g. Sorry, we are full on those dates.") + '"></textarea><div class="tr-acts"><button class="tr-btn o" data-x>Back</button><button class="tr-btn ' + (act === "confirm" ? "g" : "r") + '" data-y>' + (act === "confirm" ? "Confirm" : act === "decline" ? "Decline" : "Cancel booking") + "</button></div>");
          ov.querySelector("[data-y]").onclick = function(){ var n = ov.querySelector("[name=n]").value; ov.remove(); go(n); };
        } else go();
      }; });
      box.querySelectorAll("[data-inv]").forEach(function(b){ b.onclick = function(){ invoice(M.bookings.filter(function(x){ return String(x.id) === b.getAttribute("data-inv"); })[0]); }; });
      var hh = location.hash && D.getElementById(location.hash.slice(1)); if (hh) hh.scrollIntoView({block: "center"});
    }
    draw();
  }
  function invoice(b){
    var w = window.open("", "_blank"); if (!w){ toast("Allow pop-ups to print the invoice."); return; }
    var lines = b.kind === "room" ? "<tr><td>" + esc(b.room) + " × " + b.qty + " room(s) × " + b.nights + " night(s)</td><td>" + rs(b.price) + "</td><td>" + rs(b.total) + "</td></tr>"
      : "<tr><td>" + esc(b.place) + " — " + b.qty + " adult(s)</td><td>" + rs(b.price) + "</td><td>" + rs(b.price * b.qty) + "</td></tr>" + (b.children ? "<tr><td>" + b.children + " child(ren)</td><td>" + rs(b.child_price || b.price) + "</td><td>" + rs((b.child_price || b.price) * b.children) + "</td></tr>" : "");
    w.document.write("<!doctype html><meta charset=utf-8><title>Invoice " + esc(b.code) + "</title><style>body{font-family:system-ui,sans-serif;max-width:700px;margin:30px auto;padding:0 20px;color:#0D1424}h1{margin:0}table{width:100%;border-collapse:collapse;margin:18px 0}td,th{border-bottom:1px solid #ddd;padding:9px;text-align:left}td:last-child,th:last-child{text-align:right}.tot{font-size:20px;font-weight:900;text-align:right}small{color:#5A657C}@media print{button{display:none}}</style>"
      + "<h1>" + esc(b.company) + "</h1><small>Booked through XpertCreation · xpertcreation.com</small><hr><p><b>Invoice / booking " + esc(b.code) + "</b><br>Guest: " + esc(b.name) + " · " + esc(b.phone || "") + "<br>" + esc(b.place) + "<br>"
      + (b.kind === "room" ? "Check-in " + esc(b.start) + " · Check-out " + esc(b.end) : "Tour date " + esc(b.start)) + "<br>Status: " + esc(b.status_label) + "</p><table><tr><th>Item</th><th>Rate</th><th>Amount</th></tr>" + lines + "</table><p class='tot'>Total: " + rs(b.total) + "</p><p><small>Paid directly to " + esc(b.company) + ". Printed " + new Date().toLocaleString() + "</small></p><button onclick='print()'>Print / Save as PDF</button>");
    w.document.close();
  }
  function photosBlock(list, raw, url){
    return '<div class="tr-pics">' + list.map(function(p, i){ return '<div style="background-image:url(\'' + esc(p) + '\')"><button class="rm" data-rmp="' + esc(raw[i]) + '" data-u="' + url + '">✕</button>' + (i ? '<button class="cv" data-cv="' + esc(raw[i]) + '" data-u="' + url + '">Cover</button>' : '<button class="cv">Cover</button>') + "</div>"; }).join("")
      + '</div><label class="tr-btn o s" style="margin-top:6px">＋ Add photos<input type="file" accept="image/*" multiple hidden data-up="' + url + '"></label>';
  }
  function wirePhotos(root, after){
    root.querySelectorAll("[data-up]").forEach(function(inp){ inp.onchange = function(){
      var fs = [].slice.call(inp.files), url = inp.getAttribute("data-up"), i = 0; if (!fs.length) return; toast("Uploading " + fs.length + " photo(s)…");
      (function next(){ if (i >= fs.length){ after(); return; } var fd = new FormData(); fd.append("photo", fs[i++]); api(url, fd).then(function(x){ if (!x._ok) toast(x.detail || "Could not upload."); next(); }); })();
    }; });
    root.querySelectorAll("[data-rmp]").forEach(function(b){ b.onclick = function(){ api(b.getAttribute("data-u"), {photo: b.getAttribute("data-rmp")}, "DELETE").then(after); }; });
    root.querySelectorAll("[data-cv]").forEach(function(b){ b.onclick = function(){ api(b.getAttribute("data-u"), {cover: b.getAttribute("data-cv")}).then(after); }; });
  }
  function checks(all, labels, on, name){ return '<div class="tr-checks">' + all.map(function(k){ return '<label><input type="checkbox" name="' + name + '" value="' + k + '"' + (on.indexOf(k) >= 0 ? " checked" : "") + ">" + (labels[k] || ["", k]).join(" ") + "</label>"; }).join("") + "</div>"; }
  function picked(root, name){ return [].slice.call(root.querySelectorAll("[name=" + name + "]:checked")).map(function(x){ return x.value; }); }
  function coSelect(){ return '<label class="l">Company</label><select name="company">' + M.companies.map(function(c){ return '<option value="' + c.id + '">' + esc(c.name) + " ✔</option>"; }).join("") + "</select>"; }

  function ownerPlaces(box){
    box.innerHTML = (M.companies.length ? '<button class="tr-btn g" data-new>＋ Add a hotel or guest house</button>' : '<div class="tr-note">Verify a company to add places.</div>')
      + (M.properties.length ? M.properties.map(function(p){
        return '<div class="tr-sec"><div class="tr-mini" style="border:0;padding:0"><div class="ph" style="background-image:url(\'' + esc(p.photo) + '\')"></div><div class="t"><b>' + esc(p.name) + "</b><div class=\"tr-hint\">" + esc(p.city) + " · " + p.rooms.length + " room type(s) · " + badge(p.status === "approved" ? "confirmed" : p.status === "rejected" ? "declined" : "pending", p.status_label) + "</div>"
          + (p.review_note ? '<div class="tr-hint">Team note: ' + esc(p.review_note) + "</div>" : "") + "</div></div>"
          + '<div class="tr-acts"><button class="tr-btn s" data-edit="' + p.id + '">✏️ Edit & rooms</button><button class="tr-btn b s" data-cal="' + p.id + '">📅 Calendar</button><a class="tr-btn o s" href="' + p.url + '">👁 View</a></div></div>';
      }).join("") : '<div class="tr-empty"><div>🏨</div><p>No places yet.</p></div>');
    var nb = box.querySelector("[data-new]"); if (nb) nb.onclick = function(){ editPlace(null); };
    box.querySelectorAll("[data-edit]").forEach(function(b){ b.onclick = function(){ editPlace(M.properties.filter(function(p){ return String(p.id) === b.getAttribute("data-edit"); })[0]); }; });
    box.querySelectorAll("[data-cal]").forEach(function(b){ b.onclick = function(){ cal(+b.getAttribute("data-cal")); }; });
  }
  function editPlace(p){
    var isNew = !p; p = p || {name: "", kind: "hotel", stars: 0, city: "", area: "", address: "", map_url: "", about: "", amenities: [], phone: "", whatsapp: "", check_in: "14:00", check_out: "12:00", policies: "", rooms: [], photos: [], raw_photos: []};
    var ov = sheet("<h3>" + (isNew ? "Add a place" : "Edit " + esc(p.name)) + "</h3>" + (isNew ? coSelect() : "")
      + '<label class="l">Name</label><input name="name" maxlength="120" value="' + esc(p.name) + '" placeholder="e.g. Pine View Hotel">'
      + '<div class="tr-row3"><div><label class="l">Type</label><select name="kind">' + M.kinds.map(function(k){ return '<option value="' + k[0] + '"' + (k[0] === p.kind ? " selected" : "") + ">" + k[1] + "</option>"; }).join("") + '</select></div><div><label class="l">Stars</label><select name="stars">' + [0, 1, 2, 3, 4, 5].map(function(n){ return "<option value='" + n + "'" + (n === p.stars ? " selected" : "") + ">" + (n ? n + " ★" : "Not rated") + "</option>"; }).join("") + '</select></div><div><label class="l">City</label><input name="city" maxlength="60" value="' + esc(p.city) + '" placeholder="Murree"></div></div>'
      + '<div class="tr-row2"><div><label class="l">Area</label><input name="area" maxlength="80" value="' + esc(p.area) + '" placeholder="Mall Road"></div><div><label class="l">Google Maps link</label><input name="map_url" maxlength="300" value="' + esc(p.map_url) + '" placeholder="https://maps.app.goo.gl/…"></div></div>'
      + '<label class="l">Address</label><input name="address" maxlength="240" value="' + esc(p.address) + '">'
      + '<div class="tr-row2"><div><label class="l">Phone</label><input name="phone" maxlength="30" value="' + esc(p.phone) + '"></div><div><label class="l">WhatsApp</label><input name="whatsapp" maxlength="30" value="' + esc(p.whatsapp) + '"></div></div>'
      + '<div class="tr-row2"><div><label class="l">Check-in from</label><input name="check_in" type="time" value="' + esc(p.check_in) + '"></div><div><label class="l">Check-out by</label><input name="check_out" type="time" value="' + esc(p.check_out) + '"></div></div>'
      + '<label class="l">About the place</label><textarea name="about" maxlength="4000">' + esc(p.about) + '</textarea><label class="l">What it offers</label>' + checks(M.amenities, AM, p.amenities, "am")
      + '<label class="l">House rules (optional)</label><textarea name="policies" maxlength="2000" placeholder="e.g. Couples need a nikah nama · No smoking in rooms · Free cancellation 2 days before">' + esc(p.policies) + "</textarea>"
      + (isNew ? "" : '<label class="l">Photos (first one is the cover)</label>' + photosBlock(p.photos, p.raw_photos, "manage/places/" + p.id + "/photo/")
        + '<label class="l">Rooms</label>' + (p.rooms.length ? p.rooms.map(function(r){ return '<div class="tr-mini"><div class="ph" style="background-image:url(\'' + esc(r.photos[0] || "") + '\')"></div><div class="t"><b>' + esc(r.name) + (r.active ? "" : " (hidden)") + '</b><div class="tr-hint">' + rs(r.price) + "/night · " + r.count + " room(s) · up to " + r.adults + ' adults</div></div><button class="tr-btn o s" data-room="' + r.id + '">Edit</button></div>'; }).join("") : '<p class="tr-hint">Add at least one room type so guests can book.</p>')
        + '<button class="tr-btn b s" data-room="new">＋ Add room type</button>'
        + '<label class="tr-checks" style="margin-top:12px"><label><input type="checkbox" name="hidden"' + (p.status === "hidden" ? " checked" : "") + "> Hide this place for now</label></label>")
      + '<div class="tr-acts"><button class="tr-btn o" data-x>Close</button><button class="tr-btn g" data-save style="flex:1">' + (isNew ? "Save and continue" : "Save") + "</button></div>"
      + (isNew ? '<p class="tr-hint">After saving, add photos and rooms. The team reviews new places (usually within a day).</p>' : "") + (p.status === "rejected" ? '<p class="tr-hint">Saving sends it to the team again.</p>' : ""));
    var v = function(k){ var e = ov.querySelector("[name=" + k + "]"); return e ? e.value : ""; };
    ov.querySelector("[data-save]").onclick = function(){
      var bt = this, body = {name: v("name"), kind: v("kind"), stars: v("stars"), city: v("city"), area: v("area"), map_url: v("map_url"), address: v("address"), phone: v("phone"), whatsapp: v("whatsapp"),
        check_in: v("check_in"), check_out: v("check_out"), about: v("about"), policies: v("policies"), amenities: picked(ov, "am"), resubmit: p.status === "rejected"};
      if (isNew) body.company = v("company"); else body.hidden = !!(ov.querySelector("[name=hidden]") || {}).checked;
      bt.disabled = true;
      api("manage/places/" + (isNew ? "" : p.id + "/"), body).then(function(x){ if (!x._ok){ toast(x.detail || "Could not save."); bt.disabled = false; return; } ov.remove(); toast("Saved ✔"); M.properties = M.properties.filter(function(q){ return q.id !== x.id; }).concat([x]); mtab = "p"; drawManage(); if (isNew) editPlace(x); });
    };
    if (!isNew){
      wirePhotos(ov, function(){ api("manage/").then(function(d){ M = d; ov.remove(); editPlace(d.properties.filter(function(q){ return q.id === p.id; })[0]); }); });
      ov.querySelectorAll("[data-room]").forEach(function(b){ b.onclick = function(){ var id = b.getAttribute("data-room"); ov.remove(); editRoom(p, id === "new" ? null : p.rooms.filter(function(r){ return String(r.id) === id; })[0]); }; });
    }
  }
  function editRoom(p, r){
    var isNew = !r; r = r || {name: "", adults: 2, beds: "", price: "", count: 1, about: "", amenities: [], photos: [], active: true};
    var ov = sheet("<h3>" + (isNew ? "Add a room type" : "Edit " + esc(r.name)) + '</h3><label class="l">Room name</label><input name="name" maxlength="80" value="' + esc(r.name) + '" placeholder="e.g. Deluxe Double, Family Suite">'
      + '<div class="tr-row3"><div><label class="l">Price / night (Rs)</label><input name="price" type="number" min="100" value="' + esc(r.price) + '"></div><div><label class="l">How many rooms</label><input name="count" type="number" min="1" max="500" value="' + esc(r.count) + '"></div><div><label class="l">Adults per room</label><input name="adults" type="number" min="1" max="20" value="' + esc(r.adults) + '"></div></div>'
      + '<label class="l">Beds</label><input name="beds" maxlength="80" value="' + esc(r.beds) + '" placeholder="1 king bed, or 2 single beds"><label class="l">Short description</label><input name="about" maxlength="300" value="' + esc(r.about) + '">'
      + '<label class="l">In the room</label>' + checks(["wifi", "ac", "heating", "hot_water", "tv", "breakfast", "room_service", "mountain_view", "lake_view", "wheelchair"], AM, r.amenities, "am")
      + (isNew ? "" : '<label class="l">Room photos</label>' + photosBlock(r.photos, r.raw_photos || [], "manage/places/" + p.id + "/rooms/" + r.id + "/photo/")
        + '<div class="tr-checks" style="margin-top:10px"><label><input type="checkbox" name="active"' + (r.active ? " checked" : "") + "> Guests can book this room</label></div>")
      + '<div class="tr-acts">' + (isNew ? "" : '<button class="tr-btn r" data-del>Delete</button>') + '<button class="tr-btn o" data-x>Close</button><button class="tr-btn g" data-save style="flex:1">Save room</button></div>');
    var v = function(k){ return ov.querySelector("[name=" + k + "]").value; };
    var back = function(){ api("manage/").then(function(d){ M = d; ov.remove(); var pp = d.properties.filter(function(q){ return q.id === p.id; })[0]; editPlace(pp); }); };
    ov.querySelector("[data-save]").onclick = function(){
      var bt = this; bt.disabled = true;
      api("manage/places/" + p.id + "/rooms/" + (isNew ? "" : r.id + "/"), {name: v("name"), price: v("price"), count: v("count"), adults: v("adults"), beds: v("beds"), about: v("about"), amenities: picked(ov, "am"), active: isNew ? true : ov.querySelector("[name=active]").checked})
        .then(function(x){ if (!x._ok){ toast(x.detail || "Could not save."); bt.disabled = false; return; } toast("Room saved ✔"); back(); });
    };
    var del = ov.querySelector("[data-del]"); if (del) del.onclick = function(){ api("manage/places/" + p.id + "/rooms/" + r.id + "/", {}, "DELETE").then(function(x){ toast(x.hidden ? "It has bookings, so it was hidden instead." : "Deleted"); back(); }); };
    if (!isNew) wirePhotos(ov, function(){ api("manage/").then(function(d){ M = d; ov.remove(); var pp = d.properties.filter(function(q){ return q.id === p.id; })[0]; editRoom(pp, pp.rooms.filter(function(q){ return q.id === r.id; })[0]); }); });
  }
  function cal(pid, month){
    var p = M.properties.filter(function(q){ return q.id === pid; })[0];
    api("manage/places/" + pid + "/calendar/?month=" + (month || "")).then(function(c){
      var days = c.rows.length ? c.rows[0].days : [];
      var [y, m] = c.month.split("-").map(Number), prev = iso(new Date(y, m - 2, 1)).slice(0, 7), next = iso(new Date(y, m, 1)).slice(0, 7);
      var ov = sheet('<h3>📅 ' + esc(p.name) + '</h3><div class="tr-acts" style="margin:0 0 8px;align-items:center"><button class="tr-btn o s" data-m="' + prev + '">←</button><b style="flex:1;text-align:center">' + esc(c.label) + '</b><button class="tr-btn o s" data-m="' + next + '">→</button></div>'
        + '<div class="tr-cal"><table><tr><th>Room</th>' + days.map(function(d){ var dt = new Date(d.d + "T00:00:00"); return "<th" + (d.d === TODAY ? ' style="color:#0E7490"' : "") + ">" + dt.getDate() + "<br><small>" + "SMTWTFS".charAt(dt.getDay()) + "</small></th>"; }).join("") + "</tr>"
        + c.rows.map(function(r){ return "<tr><td>" + esc(r.name) + " <small>(" + r.count + ")</small></td>" + r.days.map(function(d){ var cls = d.free === 0 ? "x" : d.booked || d.blocked ? "p" : "f"; return '<td class="' + cls + (d.d === TODAY ? " t" : "") + '" title="' + esc(d.who.map(function(w){ return w.n + " " + w.c; }).join(", ")) + (d.blocked ? " closed:" + d.blocked : "") + '">' + d.free + "</td>"; }).join("") + "</tr>"; }).join("") + "</table></div>"
        + '<p class="tr-hint">Numbers = rooms free that night. Green free · yellow partly booked · red full.</p>'
        + '<h3 style="margin-top:14px">Close rooms (phone booking, walk-in, repairs)</h3><div class="tr-row2"><div><label class="l">Room</label><select name="room">' + c.rows.map(function(r){ return '<option value="' + r.room + '">' + esc(r.name) + "</option>"; }).join("") + '</select></div><div><label class="l">How many</label><input name="count" type="number" min="1" value="1"></div></div>'
        + '<div class="tr-row2"><div><label class="l">From night of</label><input name="start" type="date" value="' + TODAY + '"></div><div><label class="l">Until (check-out day)</label><input name="end" type="date" value="' + addDays(TODAY, 1) + '"></div></div><label class="l">Note</label><input name="note" maxlength="120" placeholder="e.g. Walk-in guest Mr Ali">'
        + '<div class="tr-acts"><button class="tr-btn o" data-x>Close</button><button class="tr-btn b" data-blk style="flex:1">Close these rooms</button></div>'
        + (c.rows.some(function(r){ return r.blocks.length; }) ? '<h3 style="margin-top:12px">Closed this month</h3>' + c.rows.map(function(r){ return r.blocks.map(function(b){ return '<div class="tr-mini"><div class="t"><b>' + esc(r.name) + " × " + b.count + '</b><div class="tr-hint">' + nice(b.start) + " → " + nice(b.end) + (b.note ? " · " + esc(b.note) : "") + '</div></div><button class="tr-btn r s" data-unb="' + b.id + '">Open again</button></div>'; }).join(""); }).join("") : ""));
      ov.querySelectorAll("[data-m]").forEach(function(b){ b.onclick = function(){ ov.remove(); cal(pid, b.getAttribute("data-m")); }; });
      var v = function(k){ return ov.querySelector("[name=" + k + "]").value; };
      ov.querySelector("[data-blk]").onclick = function(){ api("manage/places/" + pid + "/block/", {room: v("room"), count: v("count"), start: v("start"), end: v("end"), note: v("note")}).then(function(x){ if (!x._ok){ toast(x.detail || "Could not."); return; } toast("Closed ✔"); ov.remove(); cal(pid, c.month); }); };
      ov.querySelectorAll("[data-unb]").forEach(function(b){ b.onclick = function(){ api("manage/places/" + pid + "/block/", {id: b.getAttribute("data-unb")}, "DELETE").then(function(){ ov.remove(); cal(pid, c.month); }); }; });
    });
  }

  function ownerTours(box){
    box.innerHTML = (M.companies.length ? '<button class="tr-btn g" data-new>＋ Design a tour package</button>' : '<div class="tr-note">Verify a company to sell tours.</div>')
      + (M.tours.length ? M.tours.map(function(t){
        return '<div class="tr-sec"><div class="tr-mini" style="border:0;padding:0"><div class="ph" style="background-image:url(\'' + esc(t.photo) + '\')"></div><div class="t"><b>' + esc(t.title) + '</b><div class="tr-hint">' + esc(t.destination) + " · " + t.days + "D/" + t.nights + "N · " + rs(t.price) + " · " + badge(t.status === "approved" ? "confirmed" : t.status === "rejected" ? "declined" : "pending", t.status) + "</div>" + (t.review_note ? '<div class="tr-hint">Team note: ' + esc(t.review_note) + "</div>" : "") + "</div></div>"
          + '<div class="tr-acts"><button class="tr-btn s" data-edit="' + t.id + '">✏️ Edit</button><a class="tr-btn o s" href="' + t.url + '">👁 View</a></div></div>';
      }).join("") : '<div class="tr-empty"><div>🧳</div><p>No tours yet.</p></div>');
    var nb = box.querySelector("[data-new]"); if (nb) nb.onclick = function(){ editTour(null); };
    box.querySelectorAll("[data-edit]").forEach(function(b){ b.onclick = function(){ editTour(M.tours.filter(function(t){ return String(t.id) === b.getAttribute("data-edit"); })[0]); }; });
  }
  function editTour(t){
    var isNew = !t; t = t || {title: "", destination: "", start_city: "", days: 3, nights: 2, price: "", child_price: 0, includes: ["hotel", "transport", "breakfast"], excludes: [], itinerary: [], departures: [], max_group: 20, about: "", phone: "", whatsapp: "", photos: [], raw_photos: []};
    var it = (t.itinerary || []).slice(), deps = (t.departures || []).map(function(d){ return {d: d.d, seats: d.seats}; });
    var ov = sheet("<h3>" + (isNew ? "Design a tour package" : "Edit " + esc(t.title)) + "</h3>" + (isNew ? coSelect() : "")
      + '<label class="l">Title</label><input name="title" maxlength="140" value="' + esc(t.title) + '" placeholder="e.g. 5 Days Hunza & Naltar Valley">'
      + '<div class="tr-row2"><div><label class="l">Destination</label><input name="destination" maxlength="80" value="' + esc(t.destination) + '" placeholder="Hunza"></div><div><label class="l">Starts from</label><input name="start_city" maxlength="60" value="' + esc(t.start_city) + '" placeholder="Islamabad"></div></div>'
      + '<div class="tr-row3"><div><label class="l">Days</label><input name="days" type="number" min="1" max="60" value="' + t.days + '"></div><div><label class="l">Nights</label><input name="nights" type="number" min="0" max="60" value="' + t.nights + '"></div><div><label class="l">Max per booking</label><input name="max_group" type="number" min="1" max="500" value="' + t.max_group + '"></div></div>'
      + '<div class="tr-row2"><div><label class="l">Price per person (Rs)</label><input name="price" type="number" min="100" value="' + esc(t.price) + '"></div><div><label class="l">Child price (0 = same)</label><input name="child_price" type="number" min="0" value="' + esc(t.child_price) + '"></div></div>'
      + '<div class="tr-row2"><div><label class="l">Phone</label><input name="phone" maxlength="30" value="' + esc(t.phone) + '"></div><div><label class="l">WhatsApp</label><input name="whatsapp" maxlength="30" value="' + esc(t.whatsapp) + '"></div></div>'
      + '<label class="l">Included</label>' + checks(M.includes, INC, t.includes, "inc") + '<label class="l">Not included (one per line)</label><textarea name="excludes" maxlength="1200" placeholder="Lunch on travel days&#10;Personal expenses">' + esc((t.excludes || []).join("\n")) + "</textarea>"
      + '<label class="l">Day by day</label><div data-it></div><button class="tr-btn o s" data-addday>＋ Add day</button>'
      + '<label class="l">Departure dates</label><div data-deps></div><div class="tr-row2"><input name="nd" type="date" min="' + addDays(TODAY, 1) + '"><button class="tr-btn o s" data-adddep>＋ Add date</button></div><p class="tr-hint">No dates = travellers ask for any date (private tours).</p>'
      + '<label class="l">About this trip</label><textarea name="about" maxlength="5000">' + esc(t.about) + "</textarea>"
      + (isNew ? "" : '<label class="l">Photos (first one is the cover)</label>' + photosBlock(t.photos, t.raw_photos, "manage/tours/" + t.id + "/photo/") + '<div class="tr-checks" style="margin-top:10px"><label><input type="checkbox" name="hidden"' + (t.status === "hidden" ? " checked" : "") + "> Hide this tour for now</label></div>")
      + '<div class="tr-acts"><button class="tr-btn o" data-x>Close</button><button class="tr-btn g" data-save style="flex:1">' + (isNew ? "Save and continue" : "Save") + "</button></div>" + (isNew ? '<p class="tr-hint">After saving, add photos. The team reviews new tours (usually within a day).</p>' : ""));
    function drawIt(){
      ov.querySelector("[data-it]").innerHTML = it.map(function(d, i){ return '<div class="tr-sec" style="margin-top:6px;padding:10px"><div class="tr-row2" style="grid-template-columns:auto 1fr auto;align-items:center"><b>Day ' + (i + 1) + '</b><input data-it-t="' + i + '" maxlength="100" value="' + esc(d.t) + '" placeholder="e.g. Islamabad to Chilas"><button class="tr-btn r s" data-it-rm="' + i + '">✕</button></div><textarea data-it-x="' + i + '" maxlength="1000" style="margin-top:6px;min-height:56px" placeholder="What happens this day">' + esc(d.x) + "</textarea></div>"; }).join("");
      ov.querySelectorAll("[data-it-t]").forEach(function(e){ e.oninput = function(){ it[+e.getAttribute("data-it-t")].t = e.value; }; });
      ov.querySelectorAll("[data-it-x]").forEach(function(e){ e.oninput = function(){ it[+e.getAttribute("data-it-x")].x = e.value; }; });
      ov.querySelectorAll("[data-it-rm]").forEach(function(e){ e.onclick = function(){ it.splice(+e.getAttribute("data-it-rm"), 1); drawIt(); }; });
    }
    function drawDeps(){
      deps.sort(function(a, b){ return a.d < b.d ? -1 : 1; });
      ov.querySelector("[data-deps]").innerHTML = '<div class="tr-deps">' + deps.map(function(d, i){ return '<button type="button">' + nice(d.d) + '<small><input data-seat="' + i + '" type="number" min="1" value="' + d.seats + '" style="width:60px;padding:3px;font-size:12px"> seats · <span data-dep-rm="' + i + '" style="color:#B91C1C;cursor:pointer">remove</span></small></button>'; }).join("") + "</div>";
      ov.querySelectorAll("[data-seat]").forEach(function(e){ e.oninput = function(){ deps[+e.getAttribute("data-seat")].seats = +e.value || 1; }; });
      ov.querySelectorAll("[data-dep-rm]").forEach(function(e){ e.onclick = function(){ deps.splice(+e.getAttribute("data-dep-rm"), 1); drawDeps(); }; });
    }
    drawIt(); drawDeps();
    ov.querySelector("[data-addday]").onclick = function(){ it.push({t: "", x: ""}); drawIt(); };
    ov.querySelector("[data-adddep]").onclick = function(){ var d = ov.querySelector("[name=nd]").value; if (!d) return; if (!deps.some(function(x){ return x.d === d; })) deps.push({d: d, seats: +ov.querySelector("[name=max_group]").value || 20}); drawDeps(); };
    var v = function(k){ var e = ov.querySelector("[name=" + k + "]"); return e ? e.value : ""; };
    ov.querySelector("[data-save]").onclick = function(){
      var bt = this, body = {title: v("title"), destination: v("destination"), start_city: v("start_city"), days: v("days"), nights: v("nights"), max_group: v("max_group"), price: v("price"), child_price: v("child_price"),
        phone: v("phone"), whatsapp: v("whatsapp"), includes: picked(ov, "inc"), excludes: v("excludes").split("\n").map(function(x){ return x.trim(); }).filter(Boolean), itinerary: it.filter(function(d){ return d.t.trim(); }), departures: deps, about: v("about"), resubmit: t.status === "rejected"};
      if (isNew) body.company = v("company"); else body.hidden = !!(ov.querySelector("[name=hidden]") || {}).checked;
      bt.disabled = true;
      api("manage/tours/" + (isNew ? "" : t.id + "/"), body).then(function(x){ if (!x._ok){ toast(x.detail || "Could not save."); bt.disabled = false; return; } ov.remove(); toast("Saved ✔"); M.tours = M.tours.filter(function(q){ return q.id !== x.id; }).concat([x]); mtab = "t"; drawManage(); if (isNew) editTour(x); });
    };
    if (!isNew) wirePhotos(ov, function(){ api("manage/").then(function(d){ M = d; ov.remove(); editTour(d.tours.filter(function(q){ return q.id === t.id; })[0]); }); });
  }

  function teamReview(box){
    box.innerHTML = '<p class="tr-hint">Loading…</p>';
    api("review/").then(function(d){
      var L = (d.properties || []).map(function(p){ return ["property", p.id, p.name, p.city + " · " + p.company.name, p.url, p.photo]; }).concat((d.tours || []).map(function(t){ return ["tour", t.id, t.title, t.destination + " · " + t.company.name + " · " + rs(t.price), t.url, t.photo]; }));
      box.innerHTML = L.length ? L.map(function(x){ return '<div class="tr-sec"><div class="tr-mini" style="border:0;padding:0"><div class="ph" style="background-image:url(\'' + esc(x[5]) + '\')"></div><div class="t"><b>' + (x[0] === "tour" ? "🧳 " : "🏨 ") + esc(x[2]) + '</b><div class="tr-hint">' + esc(x[3]) + '</div></div></div><div class="tr-acts"><a class="tr-btn o s" target="_blank" href="' + x[4] + '">Open</a><button class="tr-btn g s" data-ok="' + x[0] + ":" + x[1] + '">Approve</button><button class="tr-btn r s" data-no="' + x[0] + ":" + x[1] + '">Reject</button></div></div>'; }).join("") : '<div class="tr-empty"><div>✅</div><p>Nothing waiting.</p></div>';
      box.querySelectorAll("[data-ok],[data-no]").forEach(function(b){ b.onclick = function(){
        var ok = b.hasAttribute("data-ok"), k = (b.getAttribute("data-ok") || b.getAttribute("data-no")).split(":"), note = ok ? "" : (prompt("Why? (the owner sees this)") || "");
        api("review/", {kind: k[0], id: k[1], approve: ok, note: note}).then(function(x){ toast(x._ok ? (ok ? "Approved" : "Rejected") : (x.detail || "Could not.")); teamReview(box); });
      }; });
    });
  }

  /* ================================================================ route */
  if (P === "/tours") (Q.get("t") ? tourPage(Q.get("t")) : tourList());
  else if (P === "/my-trips") myTrips();
  else if (P === "/travel-manage") manage();
  else (Q.get("h") ? hotelPage(Q.get("h")) : hotelList());
  window.XTR = {reload: function(){ location.reload(); }};
})();
