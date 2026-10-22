/* Urdu voice typing (XpertCreation): speak Urdu (or English, Punjabi, Arabic) and get the text.
   - says punctuation for you: "فل سٹاپ" -> ۔  "کوما" -> ،  "سوالیہ نشان" -> ؟  "نئی لائن" -> new line (English: "full stop", "comma", "question mark", "new line")
   - keeps listening after short pauses, shows the words while you speak, undo the last part
   - copy, WhatsApp, share, save as .txt, save as a Nastaliq picture (for status), notes kept on this phone
   XCVT.page(el) draws the full page; XCVT.sheet({onText}) is the small panel used inside XpertChat. */
(function(){
  "use strict";
  if (window.XCVT) return;
  var D = document, SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var LANGS = [["ur-PK", "اردو Urdu"], ["en-US", "English"], ["en-GB", "English (UK)"], ["pa-IN", "Punjabi (Gurmukhi)"], ["ar-SA", "العربية Arabic"], ["hi-IN", "Hindi"]];
  var PUNCT = {
    ur: [[/\s*(فل سٹاپ|فلسٹاپ|ختم شد)\s*/g, "۔ "], [/\s*(کوما|قومہ)\s*/g, "، "],
         [/\s*(سوالیہ نشان|سوال نشان)\s*/g, "؟ "], [/\s*(نئی لائن|اگلی لائن|نیا پیرا)\s*/g, "\n"],
         [/\s*(فجائیہ نشان)\s*/g, "! "]],
    en: [[/\s*\b(full stop|period)\b\s*/gi, ". "], [/\s*\bcomma\b\s*/gi, ", "], [/\s*\bquestion mark\b\s*/gi, "? "], [/\s*\b(new line|next line)\b\s*/gi, "\n"],
         [/\s*\b(new paragraph)\b\s*/gi, "\n\n"], [/\s*\bexclamation mark\b\s*/gi, "! "]]
  };
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  function store(k, v){ try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || "null"); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } }
  function rtl(lang){ return /^(ur|ar)/.test(lang); }
  function tidy(t, lang){
    var set = /^ur/.test(lang) ? PUNCT.ur : /^en/.test(lang) ? PUNCT.en : [];
    set.forEach(function(p){ t = t.replace(p[0], p[1]); });
    if (/^ur/.test(lang)) t = t.replace(/\?/g, "؟").replace(/,/g, "،").replace(/\s+([۔،؟!])/g, "$1");
    return t;
  }

  /* one listener that keeps going after pauses until you press stop */
  function Listener(lang, onFinal, onInterim, onState){
    this.lang = lang; this.on = false; var self = this;
    this.start = function(){
      if (!SR){ onState("nosupport"); return; }
      self.on = true; run();
    };
    this.stop = function(){ self.on = false; try { self.rec && self.rec.stop(); } catch (e) {} onState("off"); };
    function run(){
      var r = new SR(); self.rec = r; r.lang = self.lang; r.continuous = true; r.interimResults = true; r.maxAlternatives = 1;
      r.onstart = function(){ onState("on"); };
      r.onresult = function(e){
        var interim = "";
        for (var i = e.resultIndex; i < e.results.length; i++){
          var x = e.results[i][0].transcript;
          if (e.results[i].isFinal) onFinal(x); else interim += x;
        }
        onInterim(interim);
      };
      r.onerror = function(e){
        if (e.error === "not-allowed" || e.error === "service-not-allowed"){ self.on = false; onState("denied"); }
        else if (e.error === "network"){ self.on = false; onState("network"); }
      };
      r.onend = function(){ onInterim(""); if (self.on) setTimeout(function(){ if (self.on) try { run(); } catch (x) { self.on = false; onState("off"); } }, 250); else onState("off"); };
      try { r.start(); } catch (e) { self.on = false; onState("off"); }
    }
  }

  var css = D.createElement("style");
  css.textContent = [
    "@font-face{font-family:'XC Nastaliq';src:local('Noto Nastaliq Urdu'),local('Jameel Noori Nastaleeq'),url(/fonts/noto-nastaliq-urdu-700.woff2) format('woff2');font-display:swap}",
    ".vt{max-width:720px;margin:0 auto;padding:16px 15px 40px;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:#0D1424}",
    ".vt h1{font-size:26px;font-weight:900;margin:2px 0;letter-spacing:-.03em}.vt .ur{font-family:'XC Nastaliq',serif;direction:rtl;color:#5A657C;font-size:17px;line-height:2}",
    ".vt-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0}",
    ".vt-bar select,.vt-bar button{border:1.5px solid #E4E8F2;background:#fff;border-radius:12px;padding:9px 12px;font:inherit;font-size:14px;font-weight:700;color:#0D1424;cursor:pointer}",
    ".vt-bar button.on{background:#0D1424;color:#fff;border-color:#0D1424}",
    ".vt-box{position:relative;background:#fff;border:1.5px solid #E4E8F2;border-radius:20px;padding:6px}",
    ".vt-box textarea{width:100%;box-sizing:border-box;min-height:240px;border:0;outline:none;resize:vertical;padding:14px;font-size:22px;line-height:2.1;background:transparent;color:#0D1424}",
    ".vt-box textarea.nq{font-family:'XC Nastaliq','Noto Nastaliq Urdu',serif;line-height:2.4}",
    ".vt-int{min-height:26px;padding:0 14px 8px;color:#8A93A6;font-size:18px}",
    ".vt-mic{display:flex;flex-direction:column;align-items:center;gap:8px;margin:18px 0 8px}",
    ".vt-mic button{width:92px;height:92px;border-radius:50%;border:0;background:#16A34A;color:#fff;cursor:pointer;box-shadow:0 10px 26px rgba(22,163,74,.35);display:grid;place-items:center}",
    ".vt-mic button svg{width:40px;height:40px;fill:#fff}.vt-mic button.live{background:#DC2626;box-shadow:0 0 0 0 rgba(220,38,38,.5);animation:vtp 1.4s infinite}",
    "@keyframes vtp{0%{box-shadow:0 0 0 0 rgba(220,38,38,.45)}70%{box-shadow:0 0 0 22px rgba(220,38,38,0)}100%{box-shadow:0 0 0 0 rgba(220,38,38,0)}}",
    ".vt-st{font-size:14px;font-weight:700;color:#5A657C;text-align:center}",
    ".vt-acts{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin-top:12px}",
    ".vt-acts button,.vt-acts a{border:1.5px solid #E4E8F2;background:#fff;border-radius:13px;padding:11px;font:inherit;font-size:14px;font-weight:800;color:#0D1424;cursor:pointer;text-align:center;text-decoration:none}",
    ".vt-acts .g{background:#16A34A;border-color:#16A34A;color:#fff}",
    ".vt-help{background:#F6F7FB;border:1px solid #E4E8F2;border-radius:16px;padding:12px 14px;font-size:13.5px;margin-top:14px;line-height:1.7}",
    ".vt-help b.ur2{font-family:'XC Nastaliq',serif;font-weight:400;font-size:15px}",
    ".vt-kb{display:none;flex-wrap:wrap;gap:4px;direction:rtl;margin-top:8px}.vt-kb.on{display:flex}",
    ".vt-kb button{min-width:38px;height:42px;border:1px solid #E4E8F2;background:#fff;border-radius:9px;font-size:20px;cursor:pointer;font-family:'XC Nastaliq',serif}",
    ".vt-notes{margin-top:16px}.vt-note{display:flex;gap:8px;align-items:center;background:#fff;border:1px solid #E4E8F2;border-radius:12px;padding:8px 10px;margin-bottom:6px;font-size:14px}",
    ".vt-note span{flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.vt-note button{border:0;background:#F1F4FA;border-radius:9px;padding:6px 10px;font:inherit;font-weight:700;cursor:pointer}",
    ".vt-toast{position:fixed;left:50%;bottom:120px;transform:translateX(-50%);background:#0D1424;color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;z-index:2147483600}",
    ".vt-sh{position:fixed;inset:0;z-index:2147483200;background:rgba(13,20,36,.5);display:flex;align-items:flex-end;justify-content:center}",
    ".vt-sb{background:#fff;width:100%;max-width:560px;border-radius:22px 22px 0 0;padding:14px 16px calc(16px + env(safe-area-inset-bottom));font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:#0D1424}",
    ".vt-sb textarea{width:100%;box-sizing:border-box;min-height:110px;border:1.5px solid #E4E8F2;border-radius:14px;padding:10px;font-size:19px;line-height:1.9;background:#F6F7FB}"
  ].join("\n");
  D.head.appendChild(css);
  var MIC = '<svg viewBox="0 0 24 24"><path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V22h2v-3.1a7 7 0 0 0 6-6.9z"/></svg>';
  var STOP = '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
  var STATE = {on: "Listening… speak now", off: "Tap the mic and speak", denied: "Please allow the microphone for this site (lock icon in the address bar), then try again.",
               network: "Voice typing needs internet. Check your connection and try again.", nosupport: "This browser cannot do voice typing. Use Chrome (Android or computer), Edge, Safari on iPhone, or the Xpert app."};
  function toast(t){ var e = D.createElement("div"); e.className = "vt-toast"; e.textContent = t; D.body.appendChild(e); setTimeout(function(){ e.remove(); }, 2200); }
  function addText(ta, t, lang){
    t = tidy(t.trim(), lang); if (!t) return;
    var v = ta.value; if (/^\n/.test(t)) v = v.replace(/ +$/, "");
    var sep = !v || /[\s\n]$/.test(v) || /^[۔،؟.,?!\n]/.test(t) ? "" : " ";
    ta.value = v + sep + t; ta.scrollTop = ta.scrollHeight; ta.dispatchEvent(new Event("input", {bubbles: true}));
  }

  /* ------------------------------------------------------------ full page */
  function page(root){
    var lang = store("xcvt_lang") || "ur-PK", hist = [], L;
    root.className = "vt";
    root.innerHTML = '<h1>🎙️ Urdu voice typing</h1><div class="ur">بولیں اور اردو میں لکھیں — مفت</div>'
      + '<div class="vt-bar"><select data-v="lang">' + LANGS.map(function(l){ return '<option value="' + l[0] + '"' + (l[0] === lang ? " selected" : "") + ">" + l[1] + "</option>"; }).join("") + "</select>"
      + '<button type="button" data-v="font" class="on">Nastaliq</button><button type="button" data-v="size">A↑</button><button type="button" data-v="kb">ا Keyboard</button><button type="button" data-v="undo">↶ Undo</button></div>'
      + '<div class="vt-box"><textarea class="nq" data-v="ta" placeholder="Your words appear here — آپ کے الفاظ یہاں آئیں گے"></textarea><div class="vt-int" data-v="int"></div></div>'
      + '<div class="vt-kb" data-v="kbd"></div>'
      + '<div class="vt-mic"><button type="button" data-v="mic" aria-label="Start speaking">' + MIC + '</button><div class="vt-st" data-v="st">' + (SR ? STATE.off : STATE.nosupport) + "</div></div>"
      + '<div class="vt-acts"><button type="button" class="g" data-v="copy">📋 Copy</button><a data-v="wa" target="_blank" rel="noopener">WhatsApp</a>'
      + (navigator.share ? '<button type="button" data-v="share">📤 Share</button>' : "") + '<button type="button" data-v="chat">💬 XpertChat</button>'
      + '<button type="button" data-v="img">🖼️ As picture</button><button type="button" data-v="txt">⬇️ Save .txt</button><button type="button" data-v="save">⭐ Keep note</button><button type="button" data-v="clear">🗑️ Clear</button></div>'
      + '<div class="vt-help"><b>Say punctuation:</b> <b class="ur2">فل سٹاپ</b> → ۔ · <b class="ur2">کوما</b> → ، · <b class="ur2">سوالیہ نشان</b> → ؟ · <b class="ur2">نئی لائن</b> → new line. In English: "full stop", "comma", "question mark", "new line".'
      + "<br>Speak clearly, a little slowly, in a quiet place. Your voice is turned into text by your phone's or browser's speech service; we do not keep any recording. Your text stays on this phone unless you share it.</div>"
      + '<div class="vt-notes" data-v="notes"></div>';
    var $ = function(k){ return root.querySelector('[data-v="' + k + '"]'); }, ta = $("ta"), st = $("st"), mic = $("mic"), size = store("xcvt_size") || 22;
    function applyLang(){ ta.dir = rtl(lang) ? "rtl" : "ltr"; ta.style.textAlign = rtl(lang) ? "right" : "left"; $("int").dir = ta.dir; }
    ta.value = store("xcvt_draft") || ""; ta.style.fontSize = size + "px"; applyLang();
    var KB = "ا ب پ ت ٹ ث ج چ ح خ د ڈ ذ ر ڑ ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن ں و ہ ھ ء ی ے آ ئ ۂ ۔ ، ؟".split(" ");
    $("kbd").innerHTML = KB.map(function(k){ return '<button type="button" data-k="' + k + '">' + k + "</button>"; }).join("") + '<button type="button" data-k=" " style="min-width:120px">space</button><button type="button" data-k="BS">⌫</button>';
    function wa(){ $("wa").href = "https://wa.me/?text=" + encodeURIComponent(ta.value); }
    function save(){ store("xcvt_draft", ta.value); wa(); }
    ta.addEventListener("input", save); wa();
    function notes(){
      var n = store("xcvt_notes") || [];
      $("notes").innerHTML = n.length ? '<b style="font-size:12px;letter-spacing:.06em;color:#5A657C">KEPT ON THIS PHONE</b>' + n.map(function(x, i){ return '<div class="vt-note"><span dir="auto">' + esc(x.t) + '</span><button data-n="' + i + '">Open</button><button data-nd="' + i + '">✕</button></div>'; }).join("") : "";
    }
    notes();
    L = null;
    function listen(){
      if (L && L.on){ L.stop(); return; }
      L = new Listener(lang, function(t){ hist.push(ta.value); addText(ta, t, lang); save(); }, function(t){ $("int").textContent = t; }, function(s){
        st.textContent = STATE[s] || ""; mic.classList.toggle("live", s === "on"); mic.innerHTML = s === "on" ? STOP : MIC;
      });
      L.start();
    }
    root.addEventListener("click", function(e){
      var b = e.target.closest("[data-v],[data-k],[data-n],[data-nd]"); if (!b) return;
      var v = b.getAttribute("data-v");
      if (b.hasAttribute("data-k")){ var k = b.getAttribute("data-k"); hist.push(ta.value); ta.value = k === "BS" ? ta.value.slice(0, -1) : ta.value + k; save(); return; }
      if (b.hasAttribute("data-n")){ var n1 = store("xcvt_notes") || []; ta.value = n1[+b.getAttribute("data-n")].t; save(); window.scrollTo({top: 0, behavior: "smooth"}); return; }
      if (b.hasAttribute("data-nd")){ var n2 = store("xcvt_notes") || []; n2.splice(+b.getAttribute("data-nd"), 1); store("xcvt_notes", n2); notes(); return; }
      if (v === "mic") listen();
      if (v === "font"){ ta.classList.toggle("nq"); b.classList.toggle("on"); }
      if (v === "size"){ size = size >= 34 ? 18 : size + 4; ta.style.fontSize = size + "px"; store("xcvt_size", size); }
      if (v === "kb"){ $("kbd").classList.toggle("on"); b.classList.toggle("on"); }
      if (v === "undo"){ if (hist.length){ ta.value = hist.pop(); save(); } }
      if (v === "copy"){ (navigator.clipboard ? navigator.clipboard.writeText(ta.value) : Promise.reject()).then(function(){ toast("Copied ✓"); }).catch(function(){ ta.select(); D.execCommand && D.execCommand("copy"); toast("Copied"); }); }
      if (v === "share" && ta.value.trim()) navigator.share({text: ta.value}).catch(function(){});
      if (v === "chat"){ (navigator.clipboard ? navigator.clipboard.writeText(ta.value) : Promise.resolve()).then(function(){ toast("Copied — paste it in a chat"); setTimeout(function(){ location.href = "/chat"; }, 900); }); }
      if (v === "txt" && ta.value.trim()){ var bl = new Blob(["﻿" + ta.value], {type: "text/plain;charset=utf-8"}), u = URL.createObjectURL(bl), a = D.createElement("a"); a.href = u; a.download = "voice-typing-" + new Date().toISOString().slice(0, 10) + ".txt"; D.body.appendChild(a); a.click(); a.remove(); setTimeout(function(){ URL.revokeObjectURL(u); }, 3000); }
      if (v === "img" && ta.value.trim()) picture(ta.value, lang);
      if (v === "save" && ta.value.trim()){ var n3 = store("xcvt_notes") || []; n3.unshift({t: ta.value, at: Date.now()}); store("xcvt_notes", n3.slice(0, 30)); notes(); toast("Kept on this phone ⭐"); }
      if (v === "clear" && ta.value){ hist.push(ta.value); ta.value = ""; save(); toast("Cleared — tap Undo to bring it back"); }
    });
    $("lang").addEventListener("change", function(){ lang = this.value; store("xcvt_lang", lang); applyLang(); if (L && L.on){ L.stop(); setTimeout(listen, 300); } });
  }

  /* the text as a picture (Nastaliq for Urdu) - for WhatsApp status and Facebook */
  function picture(text, lang){
    var c = D.createElement("canvas"), W = 1080, H = 1350; c.width = W; c.height = H; var g = c.getContext("2d");
    var gr = g.createLinearGradient(0, 0, W, H); gr.addColorStop(0, "#0B1530"); gr.addColorStop(1, "#1B4DFF"); g.fillStyle = gr; g.fillRect(0, 0, W, H);
    var ur = rtl(lang), fam = ur ? "'XC Nastaliq','Noto Nastaliq Urdu',serif" : "system-ui,-apple-system,'Segoe UI',Roboto,sans-serif";
    g.fillStyle = "#fff"; g.textAlign = "center"; g.direction = ur ? "rtl" : "ltr";
    var size = 64, lines;
    function wrap(){
      g.font = (ur ? "400 " : "700 ") + size + "px " + fam; lines = [];
      text.split("\n").forEach(function(par){
        var words = par.split(/\s+/), line = "";
        words.forEach(function(w){ var t = line ? line + " " + w : w; if (g.measureText(t).width > W - 160 && line){ lines.push(line); line = w; } else line = t; });
        lines.push(line);
      });
    }
    do { wrap(); size -= 4; } while (lines.length * size * (ur ? 2.1 : 1.45) > H - 360 && size > 26);
    var lh = (size + 4) * (ur ? 2.1 : 1.45), y = (H - lines.length * lh) / 2 + lh / 2;
    lines.forEach(function(l){ g.fillText(l, W / 2, y); y += lh; });
    g.font = "800 30px system-ui,sans-serif"; g.globalAlpha = .75; g.direction = "ltr"; g.fillText("xpertcreation.com/urdu-voice-typing", W / 2, H - 70); g.globalAlpha = 1;
    c.toBlob(function(b){ var u = URL.createObjectURL(b), a = D.createElement("a"); a.href = u; a.download = "urdu-text.png"; D.body.appendChild(a); a.click(); a.remove(); setTimeout(function(){ URL.revokeObjectURL(u); }, 3000); }, "image/png");
  }

  /* ------------------------------------------------------------ small panel for XpertChat */
  function sheet(opts){
    opts = opts || {};
    var lang = store("xcvt_lang") || "ur-PK", L = null;
    var ov = D.createElement("div"); ov.className = "vt-sh";
    ov.innerHTML = '<div class="vt-sb"><div style="display:flex;gap:8px;align-items:center;margin-bottom:8px"><b style="flex:1;font-size:17px">🎙️ Voice typing</b><select data-s="lang" style="border:1.5px solid #E4E8F2;border-radius:10px;padding:7px;font:inherit">'
      + LANGS.map(function(l){ return '<option value="' + l[0] + '"' + (l[0] === lang ? " selected" : "") + ">" + l[1] + "</option>"; }).join("") + '</select></div>'
      + '<textarea data-s="ta" placeholder="Speak — your words appear here"></textarea><div class="vt-int" data-s="int" style="padding:4px 2px"></div>'
      + '<div class="vt-mic" style="margin:6px 0"><button type="button" data-s="mic" style="width:72px;height:72px">' + MIC + '</button><div class="vt-st" data-s="st">' + (SR ? STATE.off : STATE.nosupport) + "</div></div>"
      + '<div style="display:flex;gap:8px"><button type="button" data-s="x" style="flex:1;border:1.5px solid #E4E8F2;background:#fff;border-radius:13px;padding:12px;font:inherit;font-weight:800;cursor:pointer">Cancel</button><button type="button" data-s="ok" style="flex:2;border:0;background:#16A34A;color:#fff;border-radius:13px;padding:12px;font:inherit;font-weight:800;cursor:pointer">Put in message</button></div></div>';
    D.body.appendChild(ov);
    var q = function(k){ return ov.querySelector('[data-s="' + k + '"]'); }, ta = q("ta"), mic = q("mic");
    function dir(){ ta.dir = rtl(lang) ? "rtl" : "ltr"; ta.style.fontFamily = /^ur/.test(lang) ? "'XC Nastaliq','Noto Nastaliq Urdu',serif" : ""; ta.style.lineHeight = /^ur/.test(lang) ? "2.3" : ""; }
    dir();
    function close(){ if (L) L.stop(); ov.remove(); }
    function listen(){
      if (L && L.on){ L.stop(); return; }
      L = new Listener(lang, function(t){ addText(ta, t, lang); }, function(t){ q("int").textContent = t; }, function(s){ q("st").textContent = STATE[s] || ""; mic.classList.toggle("live", s === "on"); mic.innerHTML = s === "on" ? STOP : MIC; });
      L.start();
    }
    ov.addEventListener("click", function(e){
      if (e.target === ov) return close();
      var b = e.target.closest("[data-s]"); if (!b) return; var k = b.getAttribute("data-s");
      if (k === "mic") listen();
      if (k === "x") close();
      if (k === "ok"){ var t = ta.value.trim(); close(); if (t && opts.onText) opts.onText(t); }
    });
    q("lang").addEventListener("change", function(){ lang = this.value; store("xcvt_lang", lang); dir(); if (L && L.on){ L.stop(); setTimeout(listen, 300); } });
    if (SR) setTimeout(listen, 200);
  }

  window.XCVT = {page: page, sheet: sheet, _tidy: tidy, supported: !!SR};
  var root = D.getElementById("xcvt");
  if (root) page(root);
})();
