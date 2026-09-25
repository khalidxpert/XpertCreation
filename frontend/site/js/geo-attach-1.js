/* Swaps plain "City" boxes for the country / state / city pickers (lists with flags), keeping the
   original box hidden and filled in, so each page's own code works unchanged. Settings come from the
   data-geo attribute of this script tag. */
(function(){
  "use strict";
  var me = document.querySelector('script[src*="geo-attach-1.js"]');
  var specs = [];
  try { specs = JSON.parse(me.getAttribute("data-geo") || "[]"); } catch (e) {}
  if (!specs.length) return;
  // Standard offsets for single-time-zone countries (daylight saving is left to the person).
  var TZ = {PK: 5, IN: 5.5, BD: 6, NP: 5.75, LK: 5.5, AF: 4.5, IR: 3.5, AE: 4, OM: 4, SA: 3, QA: 3, KW: 3, BH: 3, IQ: 3, TR: 3, JO: 3,
            EG: 2, MY: 8, SG: 8, CN: 8, HK: 8, PH: 8, TH: 7, VN: 7, JP: 9, KR: 9, GB: 0, IE: 0, PT: 0, DE: 1, FR: 1, IT: 1,
            ES: 1, NL: 1, BE: 1, CH: 1, AT: 1, SE: 1, NO: 1, PL: 1, NG: 1, KE: 3, ZA: 2, NZ: 12, MV: 5, UZ: 5, KZ: 5};
  var credited = false;
  function credit(host){
    if (credited) return;
    credited = true;
    host.insertAdjacentHTML("beforeend", "<p style='font-size:11.5px;color:var(--ink-soft,#5A657C);margin:4px 0 0'>Place lists: "
      + "<a href='https://github.com/dr5hn/countries-states-cities-database' target='_blank' rel='noopener'>countries-states-cities-database</a> (ODbL).</p>");
  }
  function whenReady(fn){
    if (window.GeoPicker) return fn();
    var s = document.createElement("script");
    s.src = "/js/geo-1.js";
    s.onload = fn;
    document.head.appendChild(s);
  }
  function attachInput(spec, input){
    if (input.getAttribute("data-geo-done")) return;
    input.setAttribute("data-geo-done", "1");
    input.style.display = "none";
    var box = document.createElement("div");
    box.className = "geoatt";
    box.style.gridColumn = "1 / -1";
    box.style.width = "100%";
    input.parentNode.insertBefore(box, input.nextSibling);
    GeoPicker(box, {country: spec.country || "", city: input.value || "", onChange: function(g){
      input.value = g.city || "";
      input.dispatchEvent(new Event("input", {bubbles: true}));
      input.dispatchEvent(new Event("change", {bubbles: true}));
      if (spec.go && (g.city || !g.state)){ var b = document.getElementById(spec.go); if (b) b.click(); }
    }});
    credit(box);
  }
  function attachZodiac(){
    var cSel = document.getElementById("skyc"), oSel = document.getElementById("skyo");
    if (!cSel || cSel.getAttribute("data-geo-done")) return;
    cSel.setAttribute("data-geo-done", "1");
    var row = cSel.closest(".skyrow") || cSel.parentNode;
    var box = document.createElement("div");
    box.className = "geoatt";
    box.style.margin = "0 0 10px";
    box.innerHTML = "<div style='font-size:13px;font-weight:700;margin-bottom:5px'>Place of birth (any city in the world)</div><div></div>";
    row.parentNode.insertBefore(box, row);
    GeoPicker(box.lastChild, {onChange: function(g){
      if (g.lat == null || g.lng == null) return;
      cSel.value = "x";
      cSel.dispatchEvent(new Event("change", {bubbles: true}));
      document.getElementById("skylat").value = g.lat;
      document.getElementById("skylng").value = g.lng;
      var off = g.country in TZ ? TZ[g.country] : Math.round(g.lng / 15 * 2) / 2;
      if (oSel && oSel.querySelector("option[value='" + off + "']")) oSel.value = String(off);
    }});
    credit(box);
  }
  function scan(){
    specs.forEach(function(s){
      if (s.zodiac) return attachZodiac();
      var el = document.getElementById(s.input);
      if (el) attachInput(s, el);
    });
  }
  whenReady(function(){
    scan();
    new MutationObserver(scan).observe(document.body, {childList: true, subtree: true});   // forms drawn later
  });
})();
