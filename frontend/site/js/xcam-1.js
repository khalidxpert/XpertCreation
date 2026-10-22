/* XpertCam (xcam-1.js) - camera with filters for photos and short clips.
   Colour filters (WebGL), face filters that follow your face (on-device face tracking, nothing is uploaded),
   and event frames the team can add on the server (/js/xcam-filters.json) without an app update.
   In XpertChat: a camera button next to the message box sends the photo or clip; clips play inside the chat.
   On /cam: take, save and share. */
(function(){
  "use strict";
  if (window.XCAM) return;
  var D = document, B = D.body || D.documentElement;
  var PAGE = /^\/cam/.test(location.pathname) ? "cam" : /^\/group\//.test(location.pathname) ? "group" : /^\/chat/.test(location.pathname) ? "chat" : "other";
  var FACE_LOCAL = "/vendor/facemesh/", FACE_CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/";
  var MAX_CLIP = 20;   // seconds
  function $(id){ return D.getElementById(id); }
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function ck(n){ var m = D.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; }

  /* ------------------------------------------------------------ styles */
  var st = D.createElement("style");
  st.textContent = ""
   + ".xmov{position:fixed;inset:0;z-index:2147482990;background:#000;color:#fff;display:flex;flex-direction:column;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;user-select:none;-webkit-user-select:none}"
   + ".xmstage{flex:1;position:relative;overflow:hidden;display:flex;align-items:center;justify-content:center;min-height:0}"
   + ".xmstage canvas,.xmstage video.pv,.xmstage img.pv{max-width:100%;max-height:100%;object-fit:contain}.xmstage canvas.live{width:auto;height:auto}"
   + ".xmtop{position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;padding:calc(10px + env(safe-area-inset-top)) 12px 10px;z-index:3;background:linear-gradient(rgba(0,0,0,.45),transparent)}"
   + ".xmi{width:44px;height:44px;border-radius:50%;border:0;background:rgba(0,0,0,.35);color:#fff;font-size:20px;display:flex;align-items:center;justify-content:center;cursor:pointer}"
   + ".xmbot{padding:8px 0 calc(14px + env(safe-area-inset-bottom));background:#000;z-index:3}"
   + ".xmrow{display:flex;gap:10px;overflow-x:auto;padding:6px 14px;scrollbar-width:none;-webkit-overflow-scrolling:touch}.xmrow::-webkit-scrollbar{display:none}"
   + ".xmf{flex:0 0 auto;display:flex;flex-direction:column;align-items:center;gap:4px;border:0;background:transparent;color:#fff;font:inherit;font-size:.72rem;cursor:pointer;opacity:.85}"
   + ".xmf b{width:54px;height:54px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:26px;background:#222 center/cover;border:2px solid transparent}.xmf.on{opacity:1}.xmf.on b{border-color:#ffd54f}"
   + ".xmtabs{display:flex;justify-content:center;gap:6px;margin:2px 0 6px}.xmtab{border:0;border-radius:16px;padding:5px 12px;background:transparent;color:#bbb;font:inherit;font-size:.82rem;cursor:pointer}.xmtab.on{background:#fff;color:#000;font-weight:700}"
   + ".xmctl{display:flex;align-items:center;justify-content:space-around;padding:8px 18px 0}"
   + ".xmshut{width:76px;height:76px;border-radius:50%;border:5px solid #fff;background:rgba(255,255,255,.25);cursor:pointer;position:relative;touch-action:none}.xmshut.vid{background:#e53935}.xmshut.rec{background:#e53935;transform:scale(1.12)}"
   + ".xmshut svg{position:absolute;inset:-9px;width:94px;height:94px;transform:rotate(-90deg)}"
   + ".xmmode{display:flex;gap:4px;justify-content:center;margin-top:8px}.xmmode button{border:0;background:transparent;color:#aaa;font:inherit;font-weight:700;letter-spacing:.04em;cursor:pointer;padding:4px 10px}.xmmode button.on{color:#ffd54f}"
   + ".xmmsg{position:absolute;left:50%;top:72px;transform:translateX(-50%);background:rgba(0,0,0,.6);padding:6px 12px;border-radius:14px;font-size:.88rem;z-index:4;text-align:center;max-width:90%}"
   + ".xmacts{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;padding:12px 12px calc(16px + env(safe-area-inset-bottom))}.xmb{border:0;border-radius:22px;padding:11px 18px;font:inherit;font-weight:700;cursor:pointer;background:#fff;color:#000}.xmb.g{background:#0f9d58;color:#fff}.xmb.o{background:transparent;color:#fff;border:1px solid #fff}"
   + ".xmtime{position:absolute;top:calc(64px + env(safe-area-inset-top));left:50%;transform:translateX(-50%);background:#e53935;padding:3px 10px;border-radius:12px;font-weight:700;font-size:.85rem;z-index:4;display:none}"
   + ".xcclip{display:block;max-width:260px;width:100%;border-radius:12px;background:#000;margin:2px 0}"
   + ".xccam{background:transparent!important;box-shadow:none!important;border:0;cursor:pointer;color:inherit;padding:6px;display:inline-flex;align-items:center;justify-content:center;font-size:20px}";
  D.head.appendChild(st);

  /* ------------------------------------------------------------ colour filters (WebGL) */
  // each: [name, emoji, colour matrix rows r,g,b (3x3) + offset, vignette, grain, saturation boost]
  var I3 = [1,0,0, 0,1,0, 0,0,1];
  var COLOURS = [
    ["Normal", "⭕", I3, [0,0,0], 0, 0],
    ["Warm", "🌅", [1.08,0.04,0, 0.02,1.0,0, 0,0,0.86], [0.03,0.01,-0.02], 0.15, 0],
    ["Cool", "❄️", [0.9,0,0, 0,1.0,0.03, 0,0.05,1.12], [-0.01,0,0.03], 0.1, 0],
    ["B&W", "🎱", [0.299,0.587,0.114, 0.299,0.587,0.114, 0.299,0.587,0.114], [0,0,0], 0.2, 0.04],
    ["Vintage", "📷", [0.62,0.5,0.17, 0.33,0.66,0.15, 0.25,0.4,0.32], [0.06,0.03,0], 0.45, 0.07],
    ["Bright", "☀️", [1.12,0,0, 0,1.12,0, 0,0,1.12], [0.05,0.05,0.05], 0, 0],
    ["Drama", "🎭", [1.35,-0.1,-0.05, -0.05,1.3,-0.05, -0.05,-0.1,1.35], [-0.12,-0.1,-0.1], 0.55, 0.02],
    ["Rose", "🌸", [1.06,0.04,0.04, 0,0.94,0.04, 0.03,0.02,1.0], [0.05,0.0,0.04], 0.12, 0],
    ["Vivid", "🌈", [1.4,-0.2,-0.2, -0.2,1.4,-0.2, -0.2,-0.2,1.4], [0,0,0], 0.1, 0],
    ["Noir", "🌑", [0.4,0.8,0.2, 0.4,0.8,0.2, 0.4,0.8,0.2], [-0.2,-0.2,-0.2], 0.7, 0.08]
  ];
  function GL(canvas){
    var g = canvas.getContext("webgl", {preserveDrawingBuffer: true, premultipliedAlpha: false}) || canvas.getContext("experimental-webgl", {preserveDrawingBuffer: true});
    if (!g) return null;
    var vs = "attribute vec2 p;varying vec2 uv;uniform float mir;void main(){uv=vec2(mir>0.5?1.0-(p.x*0.5+0.5):(p.x*0.5+0.5),0.5-p.y*0.5);gl_Position=vec4(p,0.0,1.0);}";
    var fs = "precision mediump float;varying vec2 uv;uniform sampler2D t;uniform mat3 m;uniform vec3 o;uniform float vig,grain,time;"
      + "float rnd(vec2 c){return fract(sin(dot(c,vec2(12.9898,78.233))+time)*43758.5453);}"
      + "void main(){vec4 c=texture2D(t,uv);vec3 r=m*c.rgb+o;float d=distance(uv,vec2(0.5));r*=1.0-vig*smoothstep(0.35,0.85,d);r+=grain*(rnd(uv*1000.0)-0.5);gl_FragColor=vec4(clamp(r,0.0,1.0),1.0);}";
    function sh(type, src){ var s = g.createShader(type); g.shaderSource(s, src); g.compileShader(s); return s; }
    var pr = g.createProgram(); g.attachShader(pr, sh(g.VERTEX_SHADER, vs)); g.attachShader(pr, sh(g.FRAGMENT_SHADER, fs)); g.linkProgram(pr);
    if (!g.getProgramParameter(pr, g.LINK_STATUS)) return null;
    g.useProgram(pr);
    var bf = g.createBuffer(); g.bindBuffer(g.ARRAY_BUFFER, bf); g.bufferData(g.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), g.STATIC_DRAW);
    var lp = g.getAttribLocation(pr, "p"); g.enableVertexAttribArray(lp); g.vertexAttribPointer(lp, 2, g.FLOAT, false, 0, 0);
    var tx = g.createTexture(); g.bindTexture(g.TEXTURE_2D, tx);
    [g.TEXTURE_WRAP_S, g.TEXTURE_WRAP_T].forEach(function(k){ g.texParameteri(g.TEXTURE_2D, k, g.CLAMP_TO_EDGE); });
    g.texParameteri(g.TEXTURE_2D, g.TEXTURE_MIN_FILTER, g.LINEAR); g.texParameteri(g.TEXTURE_2D, g.TEXTURE_MAG_FILTER, g.LINEAR);
    var U = {}; ["m", "o", "vig", "grain", "time", "mir"].forEach(function(k){ U[k] = g.getUniformLocation(pr, k); });
    return {
      draw: function(src, f, mirror){
        if (canvas.width !== g.drawingBufferWidth || canvas.height !== g.drawingBufferHeight) {}
        g.viewport(0, 0, canvas.width, canvas.height);
        try { g.texImage2D(g.TEXTURE_2D, 0, g.RGB, g.RGB, g.UNSIGNED_BYTE, src); } catch (e) { return false; }
        var M = f[2]; // GLSL mat3 is column-major
        g.uniformMatrix3fv(U.m, false, new Float32Array([M[0], M[3], M[6], M[1], M[4], M[7], M[2], M[5], M[8]]));
        g.uniform3fv(U.o, new Float32Array(f[3])); g.uniform1f(U.vig, f[4]); g.uniform1f(U.grain, f[5]); g.uniform1f(U.time, (Date.now() % 10000) / 1000); g.uniform1f(U.mir, mirror ? 1 : 0);
        g.drawArrays(g.TRIANGLE_STRIP, 0, 4);
        return true;
      }
    };
  }

  /* ------------------------------------------------------------ face tracking (loaded only when a face filter is picked) */
  var FM = null, FMload = null;
  function faceMesh(){
    if (FM) return Promise.resolve(FM);
    if (FMload) return FMload;
    FMload = new Promise(function(ok, no){
      var base = FACE_LOCAL, s = D.createElement("script"); s.src = base + "face_mesh.js";
      s.onload = function(){
        try {
          var f = new window.FaceMesh({locateFile: function(p){ return base + p; }});
          f.setOptions({maxNumFaces: 2, refineLandmarks: false, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5});
          f.onResults(function(r){ if (f._cb) f._cb(r.multiFaceLandmarks || []); });
          f.initialize().then(function(){ FM = f; ok(f); }, function(e){ FMload = null; no(e); });
        } catch (e) { FMload = null; no(e); }
      };
      s.onerror = function(){
        if (base === FACE_LOCAL){ base = FACE_CDN; var s2 = D.createElement("script"); s2.src = base + "face_mesh.js"; s2.crossOrigin = "anonymous"; s2.onload = s.onload; s2.onerror = s.onerror; D.head.appendChild(s2); return; }
        FMload = null; no(new Error("Face filters could not load. Check your connection."));
      };
      D.head.appendChild(s);
    });
    return FMload;
  }

  /* ------------------------------------------------------------ face filters: drawn on top of the picture */
  function P(lm, i, W, H, mir){ var p = lm[i]; return {x: (mir ? 1 - p.x : p.x) * W, y: p.y * H}; }
  function face(lm, W, H, mir){
    var g = function(i){ return P(lm, i, W, H, mir); };
    var le = mid(g(33), g(133)), re = mid(g(362), g(263));
    if (mir){ var t = le; le = re; re = t; }
    var L = g(234), R = g(454), top = g(10), chin = g(152);
    var w = dist(L, R), h = dist(top, chin), ang = Math.atan2(re.y - le.y, re.x - le.x);
    return {g: g, le: le, re: re, top: top, chin: chin, nose: g(1), mouth: mid(g(13), g(14)), lipTop: g(0), w: w, h: h, ang: ang, eyes: mid(le, re), eyeD: dist(le, re),
            lc: g(mir ? 425 : 205), rc: g(mir ? 205 : 425)};
  }
  function mid(a, b){ return {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}; }
  function dist(a, b){ return Math.hypot(a.x - b.x, a.y - b.y); }
  function up(f, k){ return {x: f.top.x + Math.sin(f.ang) * f.h * k, y: f.top.y - Math.cos(f.ang) * f.h * k}; }
  function emoji(c, ch, at, size, ang){
    c.save(); c.translate(at.x, at.y); c.rotate(ang || 0); c.font = Math.round(size) + "px 'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',sans-serif";
    c.textAlign = "center"; c.textBaseline = "middle"; c.fillText(ch, 0, 0); c.restore();
  }
  var FACES = [
    ["None", "🚫", null],
    ["Shades", "😎", function(c, f){
      c.save(); c.translate(f.eyes.x, f.eyes.y); c.rotate(f.ang); var d = f.eyeD, r = d * 0.42;
      c.fillStyle = "rgba(10,10,15,.92)"; c.strokeStyle = "#111"; c.lineWidth = d * 0.07;
      [-d / 2, d / 2].forEach(function(x){ c.beginPath(); c.ellipse(x, d * 0.02, r, r * 0.78, 0, 0, Math.PI * 2); c.fill(); c.stroke();
        c.fillStyle = "rgba(255,255,255,.25)"; c.beginPath(); c.ellipse(x - r * 0.35, -r * 0.25, r * 0.25, r * 0.12, -0.5, 0, Math.PI * 2); c.fill(); c.fillStyle = "rgba(10,10,15,.92)"; });
      c.beginPath(); c.moveTo(-d / 2 + r * 0.9, -r * 0.2); c.quadraticCurveTo(0, -r * 0.55, d / 2 - r * 0.9, -r * 0.2); c.stroke();
      c.beginPath(); c.moveTo(-d / 2 - r, -r * 0.2); c.lineTo(-d * 1.05, -r * 0.35); c.moveTo(d / 2 + r, -r * 0.2); c.lineTo(d * 1.05, -r * 0.35); c.stroke(); c.restore();
    }],
    ["Crown", "👑", function(c, f){ emoji(c, "👑", up(f, 0.28), f.w * 0.75, f.ang); }],
    ["Flowers", "🌸", function(c, f){
      var fl = ["🌸", "🌼", "🌺", "🌷", "🌼", "🌸", "🌺"];
      for (var i = 0; i < fl.length; i++){
        var a = -Math.PI * 0.85 + i * (Math.PI * 0.7 / (fl.length - 1)) + f.ang, cx = f.top.x + Math.sin(f.ang) * f.h * 0.05, cy = f.top.y - Math.cos(f.ang) * f.h * 0.05;
        emoji(c, fl[i], {x: cx + Math.cos(a) * f.w * 0.52, y: cy + Math.sin(a) * f.w * 0.3 + f.h * 0.08}, f.w * 0.2, f.ang);
      }
    }],
    ["Cat", "🐱", function(c, f){
      c.save(); c.translate(f.top.x, f.top.y); c.rotate(f.ang); var w = f.w, h = f.h;
      [-1, 1].forEach(function(s){
        c.fillStyle = "#3b2f2f"; c.beginPath(); c.moveTo(s * w * 0.18, -h * 0.02); c.lineTo(s * w * 0.42, -h * 0.42); c.lineTo(s * w * 0.48, h * 0.05); c.closePath(); c.fill();
        c.fillStyle = "#f6a5c0"; c.beginPath(); c.moveTo(s * w * 0.25, -h * 0.02); c.lineTo(s * w * 0.41, -h * 0.3); c.lineTo(s * w * 0.43, 0); c.closePath(); c.fill();
      }); c.restore();
      c.save(); c.translate(f.nose.x, f.nose.y); c.rotate(f.ang); var n = f.eyeD * 0.22;
      c.fillStyle = "#f06292"; c.beginPath(); c.moveTo(-n, -n * 0.5); c.lineTo(n, -n * 0.5); c.lineTo(0, n * 0.6); c.closePath(); c.fill();
      c.strokeStyle = "rgba(30,30,30,.8)"; c.lineWidth = Math.max(2, f.eyeD * 0.025);
      [-1, 1].forEach(function(s){ for (var k = -1; k <= 1; k++){ c.beginPath(); c.moveTo(s * n * 1.6, n * 0.4); c.lineTo(s * f.eyeD * 1.05, n * 0.4 + k * n * 1.1); c.stroke(); } }); c.restore();
    }],
    ["Moustache", "🥸", function(c, f){
      var at = mid(f.nose, f.lipTop); c.save(); c.translate(at.x, at.y + f.h * 0.01); c.rotate(f.ang); var w = f.eyeD * 0.75;
      c.fillStyle = "#2b1d14"; c.beginPath(); c.moveTo(0, -w * 0.08);
      c.bezierCurveTo(w * 0.3, -w * 0.32, w * 0.7, -w * 0.12, w * 0.95, -w * 0.32); c.bezierCurveTo(w * 0.85, w * 0.05, w * 0.4, w * 0.2, 0, w * 0.06);
      c.bezierCurveTo(-w * 0.4, w * 0.2, -w * 0.85, w * 0.05, -w * 0.95, -w * 0.32); c.bezierCurveTo(-w * 0.7, -w * 0.12, -w * 0.3, -w * 0.32, 0, -w * 0.08); c.fill(); c.restore();
    }],
    ["Hearts", "💖", function(c, f, t){
      for (var i = 0; i < 6; i++){
        var a = t / 900 + i * Math.PI / 3, at = {x: f.eyes.x + Math.cos(a) * f.w * 0.75, y: f.top.y - f.h * 0.05 + Math.sin(a) * f.h * 0.22};
        emoji(c, i % 2 ? "💖" : "❤️", at, f.w * (0.14 + 0.03 * Math.sin(t / 300 + i)), 0);
      }
    }],
    ["Star eyes", "🤩", function(c, f){ emoji(c, "⭐", f.le, f.eyeD * 0.62, f.ang); emoji(c, "⭐", f.re, f.eyeD * 0.62, f.ang); }],
    ["Pakistan", "🇵🇰", function(c, f){
      [f.lc, f.rc].forEach(function(p){ c.save(); c.translate(p.x, p.y); c.rotate(f.ang); var w = f.eyeD * 0.5, h = w * 0.66;
        c.fillStyle = "#fff"; c.fillRect(-w / 2, -h / 2, w * 0.25, h); c.fillStyle = "#01411C"; c.fillRect(-w / 2 + w * 0.25, -h / 2, w * 0.75, h);
        c.fillStyle = "#fff"; c.beginPath(); c.arc(w * 0.14, 0, h * 0.3, 0, Math.PI * 2); c.fill(); c.fillStyle = "#01411C"; c.beginPath(); c.arc(w * 0.2, -h * 0.05, h * 0.26, 0, Math.PI * 2); c.fill();
        c.fillStyle = "#fff"; c.beginPath(); c.arc(w * 0.3, -h * 0.17, h * 0.07, 0, Math.PI * 2); c.fill(); c.restore(); });
    }]
  ];
  // event frames: built in + more from the server (/js/xcam-filters.json)
  var FRAMES = [
    {id: "none", name: "No frame", emoji: "▫️"},
    {id: "eid", name: "Eid Mubarak", emoji: "🌙", text: "Eid Mubarak", sub: "عید مبارک", color: "#0b6e4f", deco: "🌙✨🕌✨"},
    {id: "pk", name: "14 August", emoji: "🇵🇰", text: "Happy Independence Day", sub: "جشنِ آزادی مبارک", color: "#01411C", deco: "🇵🇰⭐🇵🇰"},
    {id: "bday", name: "Birthday", emoji: "🎂", text: "Happy Birthday", sub: "سالگرہ مبارک", color: "#ad1457", deco: "🎈🎉🎂🎉🎈"},
    {id: "jumma", name: "Jumma Mubarak", emoji: "🕌", text: "Jumma Mubarak", sub: "جمعہ مبارک", color: "#1b5e20", deco: "🕌🌿🕌"},
    {id: "xc", name: "XpertCreation", emoji: "✨", text: "xpertcreation.com", sub: "", color: "#1B4DFF", deco: "✨"}
  ];
  var extraLoaded = false;
  function loadExtra(cb){
    if (extraLoaded) return cb();
    fetch("/js/xcam-filters.json?d=" + new Date().toISOString().slice(0, 10), {credentials: "same-origin"}).then(function(r){ return r.ok ? r.json() : {}; }).catch(function(){ return {}; }).then(function(d){
      extraLoaded = true; var today = new Date().toISOString().slice(0, 10);
      (d.frames || []).forEach(function(f){ if (f && f.id && f.name && (!f.from || f.from <= today) && (!f.to || f.to >= today)){ FRAMES = FRAMES.filter(function(x){ return x.id !== f.id; }); FRAMES.splice(f.first ? 1 : FRAMES.length, 0, f); } });
      (d.face || []).forEach(function(f){ if (f && f.emoji && f.name && (!f.from || f.from <= today) && (!f.to || f.to >= today)) FACES.push([f.name, f.emoji, anchorFn(f)]); });
      cb();
    });
  }
  function anchorFn(cfg){
    return function(c, f){
      var at = cfg.anchor === "eyes" ? f.eyes : cfg.anchor === "nose" ? f.nose : cfg.anchor === "mouth" ? f.mouth : cfg.anchor === "chin" ? f.chin : cfg.anchor === "cheeks" ? null : up(f, +cfg.dy || 0.28);
      var size = f.w * (+cfg.scale || 0.6);
      if (at) emoji(c, cfg.emoji, at, size, f.ang); else { emoji(c, cfg.emoji, f.lc, size, f.ang); emoji(c, cfg.emoji, f.rc, size, f.ang); }
    };
  }
  function drawFrame(c, fr, W, H){
    if (!fr || fr.id === "none") return;
    var bh = Math.round(H * 0.16), col = fr.color || "#1B4DFF";
    var gr = c.createLinearGradient(0, H - bh * 1.6, 0, H); gr.addColorStop(0, "rgba(0,0,0,0)"); gr.addColorStop(0.45, hexA(col, 0.75)); gr.addColorStop(1, hexA(col, 0.95));
    c.fillStyle = gr; c.fillRect(0, H - bh * 1.6, W, bh * 1.6);
    c.strokeStyle = hexA("#ffffff", 0.85); c.lineWidth = Math.max(3, W * 0.008); c.strokeRect(W * 0.025, W * 0.025, W - W * 0.05, H - W * 0.05);
    c.fillStyle = "#fff"; c.textAlign = "center"; c.textBaseline = "middle";
    var fs = Math.round(Math.min(W * 0.085, bh * 0.42)), txt = fr.text || fr.name;
    c.font = "800 " + fs + "px system-ui,-apple-system,'Segoe UI',Roboto,sans-serif";
    while (fs > 10 && c.measureText(txt).width > W * 0.88){ fs -= 2; c.font = "800 " + fs + "px system-ui,-apple-system,'Segoe UI',Roboto,sans-serif"; }
    c.shadowColor = "rgba(0,0,0,.35)"; c.shadowBlur = fs * 0.2; c.fillText(txt, W / 2, H - bh * (fr.sub ? 0.82 : 0.55)); c.shadowBlur = 0;
    if (fr.sub){ c.font = Math.round(fs * 0.62) + "px 'Noto Nastaliq Urdu','Jameel Noori Nastaleeq',serif"; c.fillText(fr.sub, W / 2, H - bh * 0.32); }
    if (fr.deco) emoji(c, fr.deco, {x: W / 2, y: H * 0.14}, Math.round(W * 0.075), 0);
  }
  function hexA(h, a){ var m = /^#?([0-9a-f]{6})$/i.exec(h || ""); if (!m) return "rgba(27,77,255," + a + ")"; var n = parseInt(m[1], 16); return "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")"; }

  /* ------------------------------------------------------------ the camera */
  var ICON_FLIP = '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M20 5h-3.2L15 3H9L7.2 5H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm-8 13a5 5 0 0 1-4.6-3H9l-2.5-2.5L4 15h1.3A7 7 0 0 0 12 20zm0-10a5 5 0 0 1 4.6 3H15l2.5 2.5L20 13h-1.3A7 7 0 0 0 12 8z"/></svg>';
  function Cam(opts){
    this.o = opts || {}; this.colour = 0; this.faceF = 0; this.frame = 0; this.front = true; this.mode = this.o.mode || "photo"; this.lms = []; this.stopped = false;
  }
  Cam.prototype.say = function(t, ms){ var m = this.ov.querySelector(".xmmsg"); if (!m){ m = D.createElement("div"); m.className = "xmmsg"; this.ov.querySelector(".xmstage").appendChild(m); } m.textContent = t; clearTimeout(this.sT); this.sT = setTimeout(function(){ m.remove(); }, ms || 3500); };
  Cam.prototype.ui = function(){
    var self = this, ov = D.createElement("div"); ov.className = "xmov"; ov.setAttribute("role", "dialog"); ov.setAttribute("aria-label", "Camera with filters");
    ov.innerHTML = '<div class="xmstage"><canvas class="live"></canvas><div class="xmtop"><button class="xmi" data-a="close" aria-label="Close">✕</button><span></span>'
      + '<div style="display:flex;gap:8px"><label class="xmi" aria-label="Pick from gallery" title="Pick a photo">🖼<input type="file" accept="image/*" hidden data-a="gal"></label><button class="xmi" data-a="flip" aria-label="Switch camera">' + ICON_FLIP + '</button></div></div>'
      + '<div class="xmtime">0:00</div></div>'
      + '<div class="xmbot"><div class="xmtabs"><button class="xmtab on" data-t="colour">Colours</button><button class="xmtab" data-t="face">Face</button><button class="xmtab" data-t="frame">Frames</button></div>'
      + '<div class="xmrow"></div>'
      + '<div class="xmctl"><span style="width:44px"></span><button class="xmshut" aria-label="Take photo"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="46" fill="none" stroke="#ffd54f" stroke-width="6" stroke-dasharray="289" stroke-dashoffset="289"/></svg></button><span style="width:44px"></span></div>'
      + (this.o.noVideo ? "" : '<div class="xmmode"><button data-m="photo">PHOTO</button><button data-m="video">VIDEO</button></div>') + '</div>';
    B.appendChild(ov); this.ov = ov; this.cv = ov.querySelector("canvas"); B.style.overflow = "hidden";
    this.tab = "colour"; this.row(); this.setMode(this.mode);
    ov.addEventListener("click", function(e){
      var b = e.target.closest("button"); if (!b) return;
      if (b.dataset.a === "close") return self.close();
      if (b.dataset.a === "flip"){ self.front = !self.front; return self.startCam(); }
      if (b.dataset.t){ [].forEach.call(ov.querySelectorAll(".xmtab"), function(x){ x.classList.toggle("on", x === b); }); self.tab = b.dataset.t; return self.row(); }
      if (b.dataset.m) return self.setMode(b.dataset.m);
      if (b.dataset.f != null){ self.pick(+b.dataset.f); [].forEach.call(ov.querySelectorAll(".xmf"), function(x){ x.classList.toggle("on", x === b); }); }
    });
    ov.querySelector("[data-a=gal]").addEventListener("change", function(e){ var f = e.target.files[0]; e.target.value = ""; if (f) self.useImage(f); });
    var sh = ov.querySelector(".xmshut"), downT = 0, holdT = null;
    sh.addEventListener("pointerdown", function(e){ e.preventDefault(); downT = Date.now(); if (self.mode === "photo" && !self.o.noVideo && self.video) holdT = setTimeout(function(){ self.record(); }, 450); });
    sh.addEventListener("pointerup", function(){
      clearTimeout(holdT);
      if (self.rec){ self.stopRec(); return; }
      if (self.mode === "video"){ return self.record(); }
      if (Date.now() - downT < 450) self.snap();
    });
  };
  Cam.prototype.setMode = function(m){
    this.mode = m; var sh = this.ov.querySelector(".xmshut"); sh.classList.toggle("vid", m === "video"); sh.setAttribute("aria-label", m === "video" ? "Record a clip" : "Take photo (hold to record)");
    [].forEach.call(this.ov.querySelectorAll(".xmmode button"), function(x){ x.classList.toggle("on", x.dataset.m === m); });
    if (this.rec && m === "photo") this.stopRec();
  };
  Cam.prototype.row = function(){
    var list = this.tab === "colour" ? COLOURS.map(function(c){ return [c[0], c[1]]; }) : this.tab === "face" ? FACES.map(function(f){ return [f[0], f[1]]; }) : FRAMES.map(function(f){ return [f.name, f.emoji]; });
    var on = this.tab === "colour" ? this.colour : this.tab === "face" ? this.faceF : this.frame;
    this.ov.querySelector(".xmrow").innerHTML = list.map(function(x, i){ return '<button class="xmf' + (i === on ? " on" : "") + '" data-f="' + i + '"><b>' + esc(x[1]) + "</b>" + esc(x[0]) + "</button>"; }).join("");
  };
  Cam.prototype.pick = function(i){
    var self = this;
    if (this.tab === "colour") this.colour = i;
    else if (this.tab === "frame") this.frame = i;
    else {
      this.faceF = i;
      if (i && !FM){ this.say("Loading face filters…", 9000); faceMesh().then(function(){ self.say("Look at the camera 🙂", 2000); if (self.img) self.detectImage(); }).catch(function(e){ self.say(e.message || "Face filters are not available on this phone.", 5000); }); }
      else if (i && this.img) this.detectImage();
    }
    if (this.img) this.render();
  };
  Cam.prototype.open = function(){
    var self = this; this.ui();
    this.gl = GL(this.glc = D.createElement("canvas"));
    if (!this.gl) this.say("Colour filters are not available on this phone, but you can still use face filters and frames.", 5000);
    this.c2 = this.cv.getContext("2d");
    loadExtra(function(){ if (self.tab === "frame") self.row(); });
    if (this.o.image) return this.useImage(this.o.image);
    this.startCam();
  };
  Cam.prototype.startCam = function(){
    var self = this;
    this.stopTracks(); this.img = null;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){ this.say("This browser can't open the camera. Use the 🖼 button to pick a photo.", 6000); return; }
    navigator.mediaDevices.getUserMedia({video: {facingMode: this.front ? "user" : "environment", width: {ideal: 1280}, height: {ideal: 720}}, audio: false}).then(function(s){
      self.stream = s; var v = self.video || (self.video = D.createElement("video")); v.muted = true; v.playsInline = true; v.setAttribute("playsinline", ""); v.srcObject = s;
      return v.play().then(function(){ self.loop(); });
    }).catch(function(e){
      self.say(e && e.name === "NotAllowedError" ? "Please allow the camera for xpertcreation.com, or pick a photo with 🖼." : "The camera could not open. Pick a photo with 🖼 instead.", 7000);
    });
  };
  Cam.prototype.size = function(sw, sh){
    var max = 1280, k = Math.min(1, max / Math.max(sw, sh)), W = Math.round(sw * k), H = Math.round(sh * k);
    if (this.cv.width !== W || this.cv.height !== H){ this.cv.width = W; this.cv.height = H; this.glc.width = W; this.glc.height = H; }
    return [W, H];
  };
  // what you see is what you get: the live picture is cut to the shape of the screen, so frames and text are never cut off
  Cam.prototype.crop = function(v, vw, vh){
    var st = this.ov.querySelector(".xmstage"), A = (st.clientWidth || vw) / (st.clientHeight || vh), a = vw / vh, sx = 0, sy = 0, cw = vw, ch = vh;
    if (a > A){ cw = Math.round(vh * A); sx = Math.round((vw - cw) / 2); } else { ch = Math.round(vw / A); sy = Math.round((vh - ch) / 2); }
    var k = Math.min(1, 1280 / Math.max(cw, ch)), W = Math.max(2, Math.round(cw * k)), H = Math.max(2, Math.round(ch * k));
    var cc = this.cc || (this.cc = D.createElement("canvas"));
    if (cc.width !== W || cc.height !== H){ cc.width = W; cc.height = H; }
    cc.getContext("2d").drawImage(v, sx, sy, cw, ch, 0, 0, W, H);
    return cc;
  };
  Cam.prototype.paint = function(src, sw, sh, mirror, t){
    var wh = this.size(sw, sh), W = wh[0], H = wh[1], c = this.c2;
    var done = this.gl && this.gl.draw(src, COLOURS[this.colour], mirror);
    if (done) c.drawImage(this.glc, 0, 0, W, H);
    else { c.save(); if (mirror){ c.translate(W, 0); c.scale(-1, 1); } c.drawImage(src, 0, 0, W, H); c.restore(); }
    var ff = FACES[this.faceF][2];
    if (ff && this.lms.length) this.lms.forEach(function(lm){ try { ff(c, face(lm, W, H, mirror), t || Date.now()); } catch (e) {} });
    drawFrame(c, FRAMES[this.frame], W, H);
  };
  Cam.prototype.loop = function(){
    var self = this, v = this.video, busy = false, last = 0;
    if (FM) FM._cb = function(l){ self.lms = l; busy = false; };
    var step = function(t){
      if (self.stopped || self.img || !self.stream) return;
      if (v.videoWidth){
        var cr = self.crop(v, v.videoWidth, v.videoHeight);
        self.paint(cr, cr.width, cr.height, self.front, t);
        if (self.faceF && FM && !busy && t - last > 60){ busy = true; last = t; FM._cb = function(l){ self.lms = l; busy = false; }; FM.send({image: cr}).catch(function(){ busy = false; }); }
        if (!self.faceF) self.lms = [];
      }
      self.raf = requestAnimationFrame(step);
    };
    cancelAnimationFrame(this.raf); this.raf = requestAnimationFrame(step);
  };
  Cam.prototype.useImage = function(file){
    var self = this, im = new Image();
    this.stopTracks(); cancelAnimationFrame(this.raf);
    im.onload = function(){ self.img = im; self.lms = []; self.render(); if (self.faceF) self.detectImage(); var m = self.ov.querySelector(".xmmode"); if (m) m.style.display = "none"; self.ov.querySelector(".xmshut").setAttribute("aria-label", "Use this photo"); };
    im.onerror = function(){ self.say("That photo could not be opened."); };
    im.src = URL.createObjectURL(file);
  };
  Cam.prototype.detectImage = function(){
    var self = this; if (!FM || !this.img) return;
    FM._cb = function(l){ self.lms = l; self.render(); if (!l.length) self.say("No face found in this photo."); };
    FM.send({image: this.img}).catch(function(){});
  };
  Cam.prototype.render = function(){ if (this.img) this.paint(this.img, this.img.naturalWidth, this.img.naturalHeight, false); };
  Cam.prototype.snap = function(){
    var self = this; if (this.img) this.render();
    try { navigator.vibrate && navigator.vibrate(30); } catch (e) {}
    this.cv.toBlob(function(b){ if (b) self.review(b, "photo"); }, "image/jpeg", 0.9);
  };
  Cam.prototype.record = function(){
    var self = this; if (this.rec || !this.video || !window.MediaRecorder || !this.cv.captureStream) { if (!window.MediaRecorder) this.say("This browser can't record clips."); return; }
    var types = ["video/mp4;codecs=avc1,mp4a", "video/mp4", "video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
    var type = types.filter(function(t){ return MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t); })[0] || "";
    var go = function(audio){
      var out = self.cv.captureStream(30); if (audio) audio.getAudioTracks().forEach(function(t){ out.addTrack(t); });
      var r; try { r = new MediaRecorder(out, type ? {mimeType: type, videoBitsPerSecond: 2000000} : {videoBitsPerSecond: 2000000}); } catch (e) { self.say("Recording is not available here."); return; }
      var parts = []; r.ondataavailable = function(e){ if (e.data && e.data.size) parts.push(e.data); };
      r.onstop = function(){ if (audio) audio.getTracks().forEach(function(t){ t.stop(); }); var bl = new Blob(parts, {type: (r.mimeType || type || "video/webm").split(";")[0]}); self.rec = null; self.recUi(false); if (bl.size > 2000) self.review(bl, "video"); };
      r.start(250); self.rec = r; self.t0 = Date.now(); self.recUi(true);
      self.recT = setInterval(function(){ var s = (Date.now() - self.t0) / 1000; self.ov.querySelector(".xmtime").textContent = "0:" + ("0" + Math.floor(s)).slice(-2);
        self.ov.querySelector(".xmshut circle").setAttribute("stroke-dashoffset", String(289 * (1 - Math.min(1, s / MAX_CLIP)))); if (s >= MAX_CLIP) self.stopRec(); }, 200);
    };
    navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true}}).then(go, function(){ go(null); });
  };
  Cam.prototype.recUi = function(on){ var sh = this.ov.querySelector(".xmshut"); sh.classList.toggle("rec", on); this.ov.querySelector(".xmtime").style.display = on ? "block" : "none"; if (!on){ clearInterval(this.recT); sh.querySelector("circle").setAttribute("stroke-dashoffset", "289"); } };
  Cam.prototype.stopRec = function(){ if (this.rec && this.rec.state !== "inactive") this.rec.stop(); };
  Cam.prototype.review = function(blob, kind){
    var self = this, url = URL.createObjectURL(blob), ext = kind === "photo" ? "jpg" : (/mp4/.test(blob.type) ? "mp4" : "webm");
    var name = "XpertCam-" + new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14) + "." + ext;
    var file = new File([blob], name, {type: blob.type || (kind === "photo" ? "image/jpeg" : "video/webm")});
    var rv = D.createElement("div"); rv.className = "xmov"; rv.style.zIndex = 2147482995;
    rv.innerHTML = '<div class="xmstage">' + (kind === "photo" ? '<img class="pv" alt="Your photo" src="' + url + '">' : '<video class="pv" src="' + url + '" controls autoplay loop playsinline></video>') + '</div>'
      + '<div class="xmacts">' + (this.o.onSend ? '<button class="xmb g" data-r="send">➤ ' + esc(this.o.sendLabel || "Send") + '</button>' : "")
      + '<button class="xmb" data-r="save">⬇ Save</button>' + (navigator.canShare && navigator.canShare({files: [file]}) ? '<button class="xmb" data-r="share">📤 Share</button>' : "")
      + '<button class="xmb o" data-r="again">↺ Retake</button></div>';
    B.appendChild(rv);
    if (kind === "video" && blob.size > 7.5 * 1048576) this.say("This clip is over 8 MB, so it can't be sent in chat. You can still save or share it.", 6000);
    rv.addEventListener("click", function(e){
      var b = e.target.closest("[data-r]"); if (!b) return;
      var r = b.dataset.r;
      if (r === "again"){ rv.remove(); URL.revokeObjectURL(url); return; }
      if (r === "save"){ var a = D.createElement("a"); a.href = url; a.download = name; B.appendChild(a); a.click(); a.remove(); b.textContent = "✔ Saved"; return; }
      if (r === "share"){ navigator.share({files: [file], title: "XpertCam", text: "Made with XpertCam on xpertcreation.com"}).catch(function(){}); return; }
      if (r === "send"){
        if (kind === "video" && blob.size > 7.5 * 1048576) return;
        b.disabled = true; b.textContent = "Sending…";
        Promise.resolve(self.o.onSend(file, kind)).then(function(){ rv.remove(); self.close(); }).catch(function(er){ b.disabled = false; b.textContent = "➤ Send"; self.say((er && er.message) || "Could not send it."); });
      }
    });
  };
  Cam.prototype.stopTracks = function(){ if (this.stream){ this.stream.getTracks().forEach(function(t){ t.stop(); }); this.stream = null; } };
  Cam.prototype.close = function(){ this.stopped = true; this.stopRec(); cancelAnimationFrame(this.raf); this.stopTracks(); if (this.ov) this.ov.remove(); B.style.overflow = ""; if (this.o.onClose) this.o.onClose(); };

  function open(opts){ var c = new Cam(opts); c.open(); return c; }

  /* ------------------------------------------------------------ XpertChat: camera button + clips in chat */
  function postChat(file){
    var cur = window.XC3 && XC3.cur && XC3.cur(); if (!cur) return Promise.reject(new Error("Open a chat first."));
    var fd = new FormData(); fd.append(/^image\//.test(file.type) ? "photo" : "file", file);
    return fetch("/api/notify/threads/" + cur.id + "/", {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": ck("xc_csrf")}, body: fd})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){ if (!r.ok) throw new Error(d.detail || (r.status === 413 ? "That is too big to send (8 MB at most)." : "Could not send it.")); if (d.message && XC3.add) XC3.add([d.message]); }); });
  }
  function camButton(where, send){
    var b = D.createElement("button"); b.type = "button"; b.className = "xccam"; b.setAttribute("aria-label", "Camera with filters"); b.title = "Camera with filters"; b.textContent = "📸";
    b.addEventListener("click", function(e){ e.preventDefault(); e.stopPropagation(); open({onSend: send}); });
    where.parentNode.insertBefore(b, where); return b;
  }
  function mount(){
    setInterval(function(){
      if (PAGE === "chat"){ var ci = $("cinput"); if (ci && !ci.parentNode.querySelector(".xccam")) camButton(ci, postChat); }
      if (PAGE === "group"){ var gq = $("gq"); if (gq && !gq.parentNode.querySelector(".xccam")) camButton(gq, function(f){ if (!window.XCG) throw new Error("Open the group first."); XCG.send("", f); }); }
    }, 1200);
  }
  // clips: show a player instead of a file link
  var CLIP = /\.(webm|mp4|mov)\b/i;
  function clips(){
    [].forEach.call(D.querySelectorAll(".sys3"), function(el){ if (!el.dataset.xk && /^\u23F1\s*\uD83D\uDCDE/.test(el.textContent)){ el.dataset.xk = "1"; el.textContent = el.textContent.replace(/^\u23F1\s*/, ""); } });
    [].forEach.call(D.querySelectorAll("a.cfile, a.gf"), function(a){
      if (a.dataset.xclip) return; a.dataset.xclip = "1";
      if (!CLIP.test(a.textContent)) return;
      var m = (a.getAttribute("href") || "").match(/\/api\/notify\/(groups\/)?files\/(\d+)\//); if (!m) return;
      var v = D.createElement("video"); v.className = "xcclip"; v.controls = true; v.playsInline = true; v.setAttribute("playsinline", ""); v.preload = "metadata";
      v.src = "/api/cam/clip/" + (m[1] ? "g" : "t") + "/" + m[2] + "/";
      a.parentNode.insertBefore(v, a); a.style.fontSize = "12px"; a.innerHTML = "⬇ Save clip";
    });
  }
  function menuLink(){
    new MutationObserver(function(){
      var m = D.querySelector(".xcmenu"); if (!m || m.querySelector("[data-xmcam]")) return;
      var a = D.createElement("a"); a.href = "/cam"; a.setAttribute("data-xmcam", "1"); a.textContent = "📸 XpertCam (filters)";
      var cls = m.querySelector("a"); if (cls) a.className = cls.className; m.appendChild(a);
    }).observe(B, {childList: true});
  }

  window.XCAM = {open: open, edit: function(file, opts){ opts = opts || {}; opts.image = file; return open(opts); }, COLOURS: COLOURS, FACES: FACES, FRAMES: FRAMES, _face: face};
  if (PAGE === "cam"){
    var start = function(){ open({onClose: function(){ var h = D.createElement("div"); h.className = "xmov"; h.style.alignItems = "center"; h.style.justifyContent = "center"; h.style.textAlign = "center";
      h.innerHTML = '<div style="padding:24px"><h1 style="margin:0 0 8px">📸 XpertCam</h1><p style="opacity:.8">Photos and clips with filters. Save them or share them anywhere.<br><span dir="rtl" lang="ur" style="font-family:\'Noto Nastaliq Urdu\',serif">فلٹر والی تصویریں اور ویڈیو</span></p><p><button class="xmb g" id="xmagain">Open the camera</button> <a class="xmb o" href="/chat" style="text-decoration:none;display:inline-block">XpertChat</a></p></div>';
      B.appendChild(h); h.querySelector("#xmagain").onclick = function(){ h.remove(); start(); }; }}); };
    start();
  } else if (PAGE === "chat" || PAGE === "group"){
    mount(); menuLink();
    new MutationObserver(clips).observe(B, {childList: true, subtree: true}); clips();
  }
})();
