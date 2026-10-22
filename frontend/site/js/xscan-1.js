/* XpertScan (xscan-1.js) - scan documents with the phone camera, on the phone itself.
   Finds the page edges (drag the 4 corners to fix), straightens it, cleans it (Magic colour, Grey, Black & white),
   many pages -> one PDF, ID card mode (front + back on one page), and text from the picture (OCR, English / Urdu).
   Nothing is uploaded unless you send it. Text recognition files are kept on our server (/vendor/tess/). */
(function(){
  "use strict";
  if (window.XSCAN) return;
  var D = document, B = D.body || D.documentElement;
  var TESS = "/vendor/tess/";
  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }

  var st = D.createElement("style");
  st.textContent = ""
   + ".xsov{position:fixed;inset:0;z-index:2147482980;background:#0e1116;color:#fff;display:flex;flex-direction:column;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;-webkit-user-select:none;user-select:none}"
   + ".xstop{display:flex;align-items:center;gap:10px;padding:calc(10px + env(safe-area-inset-top)) 12px 10px;background:#161b22}.xstop b{flex:1;font-size:17px}"
   + ".xsi{width:42px;height:42px;border-radius:50%;border:0;background:rgba(255,255,255,.08);color:#fff;font-size:19px;cursor:pointer;display:grid;place-items:center}"
   + ".xsmain{flex:1;overflow:auto;position:relative;min-height:0;display:flex;flex-direction:column}"
   + ".xsbot{padding:10px 12px calc(14px + env(safe-area-inset-bottom));background:#161b22;display:flex;gap:8px;flex-wrap:wrap;justify-content:center}"
   + ".xsb{border:0;border-radius:22px;padding:11px 18px;font:inherit;font-weight:700;cursor:pointer;background:#fff;color:#0e1116}.xsb.g{background:#0f9d58;color:#fff}.xsb.o{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.5)}.xsb:disabled{opacity:.5}"
   + ".xshome{margin:auto;padding:24px 18px;max-width:440px;text-align:center}.xshome h1{margin:8px 0 4px;font-size:26px}.xshome p{opacity:.75;margin:0 0 18px}"
   + ".xsbig{display:flex;align-items:center;gap:14px;width:100%;text-align:left;border:0;border-radius:16px;padding:16px;margin:10px 0;background:#1f2630;color:#fff;font:inherit;font-size:16px;font-weight:700;cursor:pointer}.xsbig i{font-size:28px;font-style:normal}.xsbig small{display:block;font-weight:400;opacity:.7;font-size:13px}"
   + ".xscrop{flex:1;position:relative;display:flex;align-items:center;justify-content:center;padding:18px;min-height:0;touch-action:none}"
   + ".xscrop canvas{max-width:100%;max-height:100%;display:block}"
   + ".xscrop svg{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none}"
   + ".xsh{position:absolute;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;border:3px solid #fff;background:rgba(15,157,88,.55);box-shadow:0 0 0 2px rgba(0,0,0,.35);touch-action:none;cursor:grab;z-index:2}"
   + ".xsprev{flex:1;display:flex;align-items:center;justify-content:center;padding:12px;min-height:0}.xsprev img{max-width:100%;max-height:100%;box-shadow:0 4px 20px rgba(0,0,0,.5);background:#fff}"
   + ".xschips{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;padding:8px}.xschip{border:1px solid rgba(255,255,255,.35);border-radius:18px;padding:7px 14px;background:transparent;color:#fff;font:inherit;font-size:14px;cursor:pointer}.xschip.on{background:#ffd54f;color:#000;border-color:#ffd54f;font-weight:700}"
   + ".xspages{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:12px;padding:14px}"
   + ".xspg{position:relative;background:#1f2630;border-radius:12px;padding:8px;text-align:center}.xspg img{width:100%;aspect-ratio:1/1.414;object-fit:contain;background:#fff;border-radius:6px}.xspg b{position:absolute;left:12px;top:12px;background:#0f9d58;border-radius:10px;padding:1px 8px;font-size:12px}"
   + ".xspg .a{display:flex;justify-content:space-between;margin-top:6px}.xspg .a button{border:0;background:rgba(255,255,255,.1);color:#fff;border-radius:8px;width:30px;height:28px;cursor:pointer}"
   + ".xsmsg{position:absolute;left:50%;top:14px;transform:translateX(-50%);background:rgba(0,0,0,.75);padding:7px 14px;border-radius:14px;font-size:14px;z-index:5;max-width:90%;text-align:center}"
   + ".xsocr{padding:14px;display:flex;flex-direction:column;gap:10px;flex:1}.xsocr textarea{flex:1;min-height:240px;width:100%;box-sizing:border-box;border-radius:12px;border:1px solid #333;background:#0b0e12;color:#fff;font:inherit;font-size:15px;padding:12px;-webkit-user-select:text;user-select:text}"
   + ".xsbar{height:6px;border-radius:3px;background:#222;overflow:hidden}.xsbar i{display:block;height:100%;width:0;background:#0f9d58;transition:width .3s}";
  D.head.appendChild(st);

  /* ------------------------------------------------------------ image helpers */
  function loadImg(file){
    return new Promise(function(ok, no){
      var im = new Image(); im.onload = function(){ ok(im); }; im.onerror = function(){ no(new Error("That picture could not be opened.")); };
      im.src = URL.createObjectURL(file);
    });
  }
  function toCanvas(src, max){
    var w = src.naturalWidth || src.width, h = src.naturalHeight || src.height, k = Math.min(1, max / Math.max(w, h));
    var c = D.createElement("canvas"); c.width = Math.round(w * k); c.height = Math.round(h * k);
    c.getContext("2d").drawImage(src, 0, 0, c.width, c.height); return c;
  }
  function rotate(c, dir){
    var o = D.createElement("canvas"); o.width = c.height; o.height = c.width; var x = o.getContext("2d");
    x.translate(o.width / 2, o.height / 2); x.rotate(dir * Math.PI / 2); x.drawImage(c, -c.width / 2, -c.height / 2); return o;
  }
  // the page: brightest large area -> its 4 extreme corners (works for paper on a darker table); you can always drag them
  function detect(c){
    var k = Math.min(1, 360 / Math.max(c.width, c.height)), w = Math.max(8, Math.round(c.width * k)), h = Math.max(8, Math.round(c.height * k));
    var s = D.createElement("canvas"); s.width = w; s.height = h; var x = s.getContext("2d"); x.drawImage(c, 0, 0, w, h);
    var d = x.getImageData(0, 0, w, h).data, g = new Uint8Array(w * h), hist = new Array(256).fill(0), i;
    for (i = 0; i < w * h; i++){ g[i] = (d[i * 4] * 77 + d[i * 4 + 1] * 150 + d[i * 4 + 2] * 29) >> 8; }
    // light blur
    var b = new Uint8Array(w * h);
    for (var y = 1; y < h - 1; y++) for (var xx = 1; xx < w - 1; xx++){ var p = y * w + xx; b[p] = (g[p] * 4 + g[p - 1] + g[p + 1] + g[p - w] + g[p + w] + g[p - w - 1] + g[p - w + 1] + g[p + w - 1] + g[p + w + 1]) / 12; }
    for (i = 0; i < w * h; i++) hist[b[i]]++;
    var tot = w * h, sum = 0; for (i = 0; i < 256; i++) sum += i * hist[i];
    var sB = 0, wB = 0, best = 0, th = 128;
    for (i = 0; i < 256; i++){ wB += hist[i]; if (!wB) continue; var wF = tot - wB; if (!wF) break; sB += i * hist[i]; var mB = sB / wB, mF = (sum - sB) / wF, v = wB * wF * (mB - mF) * (mB - mF); if (v > best){ best = v; th = i; } }
    var seen = new Uint8Array(w * h), bestArea = 0, bestPts = null, stack = new Int32Array(w * h);
    for (var start = 0; start < w * h; start++){
      if (seen[start] || b[start] <= th) continue;
      var sp = 0, area = 0, tl = [1e9, 0, 0], br = [-1e9, 0, 0], tr = [-1e9, 0, 0], bl = [1e9, 0, 0], touches = 0;
      stack[sp++] = start; seen[start] = 1;
      while (sp){
        var q = stack[--sp], qx = q % w, qy = (q / w) | 0; area++;
        if (qx === 0 || qy === 0 || qx === w - 1 || qy === h - 1) touches++;
        var a1 = qx + qy, a2 = qx - qy;
        if (a1 < tl[0]) tl = [a1, qx, qy]; if (a1 > br[0]) br = [a1, qx, qy]; if (a2 > tr[0]) tr = [a2, qx, qy]; if (a2 < bl[0]) bl = [a2, qx, qy];
        var nb = [q - 1, q + 1, q - w, q + w];
        for (var n = 0; n < 4; n++){ var r = nb[n]; if (r < 0 || r >= w * h || seen[r]) continue; if ((n === 0 && qx === 0) || (n === 1 && qx === w - 1)) continue; if (b[r] > th){ seen[r] = 1; stack[sp++] = r; } }
      }
      if (area > bestArea){ bestArea = area; bestPts = [tl, tr, br, bl]; }
    }
    var inset = function(){ var m = 0.06; return [[c.width * m, c.height * m], [c.width * (1 - m), c.height * m], [c.width * (1 - m), c.height * (1 - m)], [c.width * m, c.height * (1 - m)]]; };
    if (!bestPts || bestArea < tot * 0.12 || bestArea > tot * 0.97) return inset();
    var pts = bestPts.map(function(p){ return [p[1] / k, p[2] / k]; }), cx = (pts[0][0] + pts[1][0] + pts[2][0] + pts[3][0]) / 4, cy = (pts[0][1] + pts[1][1] + pts[2][1] + pts[3][1]) / 4;
    return pts.map(function(p){ return [p[0] + (cx - p[0]) * 0.012, p[1] + (cy - p[1]) * 0.012]; });   // a hair inside, so no table edge shows
  }
  // straighten: map the 4 corners onto a flat rectangle
  function solve(A, bv){ var n = bv.length; for (var i = 0; i < n; i++){ var mx = i; for (var r = i + 1; r < n; r++) if (Math.abs(A[r][i]) > Math.abs(A[mx][i])) mx = r; var t = A[i]; A[i] = A[mx]; A[mx] = t; var tb = bv[i]; bv[i] = bv[mx]; bv[mx] = tb;
      for (r = i + 1; r < n; r++){ var f = A[r][i] / A[i][i]; for (var cc = i; cc < n; cc++) A[r][cc] -= f * A[i][cc]; bv[r] -= f * bv[i]; } }
    var x = new Array(n); for (i = n - 1; i >= 0; i--){ var s = bv[i]; for (var j = i + 1; j < n; j++) s -= A[i][j] * x[j]; x[i] = s / A[i][i]; } return x; }
  function homography(from, to){
    var A = [], bv = [];
    for (var i = 0; i < 4; i++){ var x = from[i][0], y = from[i][1], u = to[i][0], v = to[i][1];
      A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); bv.push(u); A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); bv.push(v); }
    var h = solve(A, bv); h.push(1); return h;
  }
  function dist(a, b){ return Math.hypot(a[0] - b[0], a[1] - b[1]); }
  function warp(src, quad){
    var W = Math.max(dist(quad[0], quad[1]), dist(quad[3], quad[2])), H = Math.max(dist(quad[0], quad[3]), dist(quad[1], quad[2]));
    var k = Math.min(1, 2200 / Math.max(W, H)); W = Math.max(20, Math.round(W * k)); H = Math.max(20, Math.round(H * k));
    var h = homography([[0, 0], [W, 0], [W, H], [0, H]], quad);   // output pixel -> source pixel
    var sw = src.width, sh = src.height, sd = src.getContext("2d").getImageData(0, 0, sw, sh).data;
    var o = D.createElement("canvas"); o.width = W; o.height = H; var ox = o.getContext("2d"), od = ox.createImageData(W, H), dd = od.data;
    for (var y = 0; y < H; y++){
      for (var x = 0; x < W; x++){
        var z = h[6] * x + h[7] * y + 1, sx = (h[0] * x + h[1] * y + h[2]) / z, sy = (h[3] * x + h[4] * y + h[5]) / z;
        var x0 = Math.floor(sx), y0 = Math.floor(sy), fx = sx - x0, fy = sy - y0, di = (y * W + x) * 4;
        if (x0 < 0 || y0 < 0 || x0 >= sw - 1 || y0 >= sh - 1){ dd[di] = dd[di + 1] = dd[di + 2] = 255; dd[di + 3] = 255; continue; }
        var i00 = (y0 * sw + x0) * 4, i10 = i00 + 4, i01 = i00 + sw * 4, i11 = i01 + 4;
        for (var ch = 0; ch < 3; ch++){ dd[di + ch] = (sd[i00 + ch] * (1 - fx) + sd[i10 + ch] * fx) * (1 - fy) + (sd[i01 + ch] * (1 - fx) + sd[i11 + ch] * fx) * fy; }
        dd[di + 3] = 255;
      }
    }
    ox.putImageData(od, 0, 0); return o;
  }
  // looks
  var LOOKS = [["magic", "Magic colour"], ["orig", "Original"], ["grey", "Grey"], ["bw", "Black & white"]];
  function look(c, kind){
    var o = D.createElement("canvas"); o.width = c.width; o.height = c.height; var x = o.getContext("2d"); x.drawImage(c, 0, 0);
    if (kind === "orig") return o;
    var W = o.width, H = o.height, im = x.getImageData(0, 0, W, H), d = im.data, n = W * H, i;
    if (kind === "grey" || kind === "bw"){
      var g = new Uint8ClampedArray(n); for (i = 0; i < n; i++) g[i] = (d[i * 4] * 77 + d[i * 4 + 1] * 150 + d[i * 4 + 2] * 29) >> 8;
      if (kind === "grey"){ var lo = pct(g, 0.02), hi = pct(g, 0.97); for (i = 0; i < n; i++){ var v = (g[i] - lo) * 255 / Math.max(1, hi - lo); d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = v; } }
      else {
        var S = new Float64Array((W + 1) * (H + 1)), r = Math.max(8, Math.round(W / 24));
        for (var y = 0; y < H; y++){ var row = 0; for (var xx = 0; xx < W; xx++){ row += g[y * W + xx]; S[(y + 1) * (W + 1) + xx + 1] = S[y * (W + 1) + xx + 1] + row; } }
        for (y = 0; y < H; y++){ var y1 = Math.max(0, y - r), y2 = Math.min(H, y + r + 1);
          for (xx = 0; xx < W; xx++){ var x1 = Math.max(0, xx - r), x2 = Math.min(W, xx + r + 1), cnt = (x2 - x1) * (y2 - y1);
            var m = (S[y2 * (W + 1) + x2] - S[y1 * (W + 1) + x2] - S[y2 * (W + 1) + x1] + S[y1 * (W + 1) + x1]) / cnt, p = y * W + xx, vv = g[p] < m * 0.88 ? 0 : 255;
            d[p * 4] = d[p * 4 + 1] = d[p * 4 + 2] = vv; } }
      }
    } else {   // magic colour: stretch each colour, lift the paper to white, a little more colour
      var lo3 = [], hi3 = [];
      for (var ch = 0; ch < 3; ch++){ var a = new Uint8ClampedArray(n); for (i = 0; i < n; i++) a[i] = d[i * 4 + ch]; lo3[ch] = pct(a, 0.02); hi3[ch] = pct(a, 0.9); }
      for (i = 0; i < n; i++){
        var rr = (d[i * 4] - lo3[0]) * 255 / Math.max(1, hi3[0] - lo3[0]), gg = (d[i * 4 + 1] - lo3[1]) * 255 / Math.max(1, hi3[1] - lo3[1]), bb = (d[i * 4 + 2] - lo3[2]) * 255 / Math.max(1, hi3[2] - lo3[2]);
        var l = (rr + gg + bb) / 3; rr = l + (rr - l) * 1.25; gg = l + (gg - l) * 1.25; bb = l + (bb - l) * 1.25;
        if (l > 205){ var t = Math.min(1, (l - 205) / 35); rr += (255 - rr) * t; gg += (255 - gg) * t; bb += (255 - bb) * t; }
        d[i * 4] = rr; d[i * 4 + 1] = gg; d[i * 4 + 2] = bb;
      }
    }
    x.putImageData(im, 0, 0); return o;
  }
  function pct(a, q){ var h = new Uint32Array(256), i; for (i = 0; i < a.length; i++) h[a[i]]++; var lim = a.length * q, s = 0; for (i = 0; i < 256; i++){ s += h[i]; if (s >= lim) return i; } return 255; }

  /* ------------------------------------------------------------ PDF (written here, no library) */
  function dataBytes(url){ var b = atob(url.split(",")[1]), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  function makePdf(pages){   // pages: [{url (jpeg data url), w, h}]
    var parts = [], len = 0, offs = [];
    var enc = function(s){ var u = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 255; return u; };
    var put = function(x){ var u = typeof x === "string" ? enc(x) : x; parts.push(u); len += u.length; };
    var obj = function(n, body){ offs[n] = len; put(n + " 0 obj\n"); body(); put("\nendobj\n"); };
    put("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n");
    var n = pages.length, kids = [];
    for (var i = 0; i < n; i++) kids.push((3 + i * 3) + " 0 R");
    obj(1, function(){ put("<< /Type /Catalog /Pages 2 0 R >>"); });
    obj(2, function(){ put("<< /Type /Pages /Count " + n + " /Kids [" + kids.join(" ") + "] >>"); });
    pages.forEach(function(p, i){
      var pw = 595.28, ph = 841.89, k = Math.min(pw / p.w, ph / p.h), iw = p.w * k, ih = p.h * k, ox = (pw - iw) / 2, oy = (ph - ih) / 2;
      var pn = 3 + i * 3, cn = pn + 1, im = pn + 2, img = dataBytes(p.url), cs = "q " + iw.toFixed(2) + " 0 0 " + ih.toFixed(2) + " " + ox.toFixed(2) + " " + oy.toFixed(2) + " cm /Im" + i + " Do Q";
      obj(pn, function(){ put("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /XObject << /Im" + i + " " + im + " 0 R >> >> /Contents " + cn + " 0 R >>"); });
      obj(cn, function(){ put("<< /Length " + cs.length + " >>\nstream\n" + cs + "\nendstream"); });
      obj(im, function(){ put("<< /Type /XObject /Subtype /Image /Width " + p.w + " /Height " + p.h + " /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length " + img.length + " >>\nstream\n"); put(img); put("\nendstream"); });
    });
    var total = 3 + n * 3, xref = len;
    var x = "xref\n0 " + total + "\n0000000000 65535 f \n"; for (var j = 1; j < total; j++) x += ("000000000" + offs[j]).slice(-10) + " 00000 n \n";
    put(x + "trailer\n<< /Size " + total + " /Root 1 0 R >>\nstartxref\n" + xref + "\n%%EOF");
    return new Blob(parts, {type: "application/pdf"});
  }

  /* ------------------------------------------------------------ text from the picture (OCR) */
  var TS = null;
  function tesseract(){
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    if (TS) return TS;
    TS = new Promise(function(ok, no){ var s = D.createElement("script"); s.src = TESS + "tesseract.min.js"; s.onload = function(){ ok(window.Tesseract); }; s.onerror = function(){ TS = null; no(new Error("Text reading could not load. Check your connection.")); }; D.head.appendChild(s); });
    return TS;
  }
  function readText(urls, lang, onProgress){
    return tesseract().then(function(T){
      return T.createWorker(lang, 1, {workerPath: TESS + "worker.min.js", corePath: TESS, langPath: TESS + "lang", logger: function(m){ if (m && typeof m.progress === "number" && onProgress) onProgress(m.status, m.progress); }})
        .then(function(w){
          var out = [];
          return urls.reduce(function(p, u, i){ return p.then(function(){ return w.recognize(u).then(function(r){ out.push((urls.length > 1 ? "--- Page " + (i + 1) + " ---\n" : "") + (r.data.text || "").trim()); }); }); }, Promise.resolve())
            .then(function(){ w.terminate(); return out.join("\n\n"); });
        });
    });
  }

  /* ------------------------------------------------------------ the scanner */
  function Scanner(opts){ this.o = opts || {}; this.pages = []; this.mode = "doc"; this.idParts = []; }
  Scanner.prototype.frame = function(title, main, bottom){
    if (!this.ov){ this.ov = D.createElement("div"); this.ov.className = "xsov"; B.appendChild(this.ov); B.style.overflow = "hidden"; }
    this.ov.innerHTML = '<div class="xstop"><button class="xsi" data-x="back" aria-label="Back">←</button><b>' + esc(title) + '</b><button class="xsi" data-x="close" aria-label="Close">✕</button></div><div class="xsmain">' + main + '</div>' + (bottom ? '<div class="xsbot">' + bottom + "</div>" : "");
    var self = this;
    this.ov.querySelector("[data-x=close]").onclick = function(){ self.close(); };
    this.ov.querySelector("[data-x=back]").onclick = function(){ self.back ? self.back() : self.close(); };
    return this.ov;
  };
  Scanner.prototype.say = function(t, ms){ var m = D.createElement("div"); m.className = "xsmsg"; m.textContent = t; var main = this.ov.querySelector(".xsmain"); main.appendChild(m); setTimeout(function(){ m.remove(); }, ms || 3500); };
  Scanner.prototype.close = function(){ if (this.ov) this.ov.remove(); this.ov = null; B.style.overflow = ""; if (this.o.onClose) this.o.onClose(); };
  Scanner.prototype.pick = function(camera, multiple){
    var self = this, inp = D.createElement("input"); inp.type = "file"; inp.accept = "image/*"; if (camera) inp.setAttribute("capture", "environment"); if (multiple) inp.multiple = true; inp.style.display = "none"; B.appendChild(inp);
    inp.onchange = function(){ var fs = [].slice.call(inp.files || []); inp.remove(); if (fs.length) self.queue = fs.slice(1), self.crop(fs[0]); };
    inp.click();
  };
  Scanner.prototype.home = function(){
    var self = this; this.back = null;
    this.frame("XpertScan", '<div class="xshome"><div style="font-size:46px">📄</div><h1>XpertScan</h1><p>Scan papers into a clean PDF. Pages stay on your phone until you send them.<br><span dir="rtl" lang="ur" style="font-family:\'Noto Nastaliq Urdu\',serif">کاغذات اسکین کریں اور پی ڈی ایف بنائیں</span></p>'
      + '<button class="xsbig" data-h="cam"><i>📷</i><span>Scan with camera<small>Point at a page, ID card, receipt or board</small></span></button>'
      + '<button class="xsbig" data-h="gal"><i>🖼️</i><span>Pick photos<small>Choose one or many pictures you already took</small></span></button>'
      + '<button class="xsbig" data-h="id"><i>🪪</i><span>ID card<small>Front and back on one page (for KYC)</small></span></button>'
      + (this.pages.length ? '<button class="xsbig" data-h="pages"><i>📚</i><span>My pages (' + this.pages.length + ')<small>Continue with the pages you scanned</small></span></button>' : "") + "</div>");
    this.ov.querySelector(".xsmain").addEventListener("click", function(e){
      var b = e.target.closest("[data-h]"); if (!b) return; var k = b.dataset.h;
      if (k === "cam"){ self.mode = "doc"; self.pick(true); } else if (k === "gal"){ self.mode = "doc"; self.pick(false, true); }
      else if (k === "id"){ self.mode = "id"; self.idParts = []; self.say("Scan the FRONT of the card"); setTimeout(function(){ self.pick(true); }, 600); }
      else self.list();
    });
  };
  Scanner.prototype.crop = function(file){
    var self = this;
    loadImg(file).then(function(im){
      var src = toCanvas(im, 2600), quad = detect(src);
      self.back = function(){ self.pages.length ? self.list() : self.home(); };
      var ov = self.frame(self.mode === "id" ? (self.idParts.length ? "Card - back side" : "Card - front side") : "Adjust the corners", '<div class="xscrop"><canvas></canvas><svg><polygon fill="rgba(15,157,88,.18)" stroke="#0f9d58" stroke-width="3"></polygon></svg></div>',
        '<button class="xsb o" data-c="auto">🎯 Auto</button><button class="xsb o" data-c="full">⬜ Whole photo</button><button class="xsb o" data-c="rot">↻ Rotate</button><button class="xsb g" data-c="ok">✔ Next</button>');
      var box = ov.querySelector(".xscrop"), cv = box.querySelector("canvas"), poly = box.querySelector("polygon"), hs = [];
      var draw = function(){
        var pw = box.clientWidth - 36, ph = box.clientHeight - 36, k = Math.min(pw / src.width, ph / src.height);
        cv.width = Math.round(src.width * k); cv.height = Math.round(src.height * k); cv.getContext("2d").drawImage(src, 0, 0, cv.width, cv.height);
        place();
      };
      var geo = function(){ var r = cv.getBoundingClientRect(), b = box.getBoundingClientRect(); return {ox: r.left - b.left, oy: r.top - b.top, k: r.width / src.width}; };
      var place = function(){ var g = geo();
        quad.forEach(function(p, i){ var h = hs[i]; if (!h){ h = hs[i] = D.createElement("div"); h.className = "xsh"; box.appendChild(h); drag(h, i); } h.style.left = (g.ox + p[0] * g.k) + "px"; h.style.top = (g.oy + p[1] * g.k) + "px"; });
        poly.setAttribute("points", quad.map(function(p){ return (g.ox + p[0] * g.k) + "," + (g.oy + p[1] * g.k); }).join(" "));
      };
      var drag = function(h, i){
        h.addEventListener("pointerdown", function(e){ e.preventDefault(); h.setPointerCapture(e.pointerId);
          var mv = function(ev){ var g = geo(), b = box.getBoundingClientRect(); quad[i] = [Math.max(0, Math.min(src.width, (ev.clientX - b.left - g.ox) / g.k)), Math.max(0, Math.min(src.height, (ev.clientY - b.top - g.oy) / g.k))]; place(); };
          var up = function(){ h.removeEventListener("pointermove", mv); h.removeEventListener("pointerup", up); };
          h.addEventListener("pointermove", mv); h.addEventListener("pointerup", up); });
      };
      requestAnimationFrame(draw); window.addEventListener("resize", draw);
      ov.querySelector(".xsbot").addEventListener("click", function(e){
        var b = e.target.closest("[data-c]"); if (!b) return; var k = b.dataset.c;
        if (k === "auto"){ quad = detect(src); place(); }
        else if (k === "full"){ quad = [[0, 0], [src.width, 0], [src.width, src.height], [0, src.height]]; place(); }
        else if (k === "rot"){ src = rotate(src, 1); quad = detect(src); hs.forEach(function(h){ h.remove(); }); hs = []; draw(); }
        else { window.removeEventListener("resize", draw); b.disabled = true; b.textContent = "Working…"; setTimeout(function(){ self.enhance(warp(src, quad)); }, 30); }
      });
    }).catch(function(e){ self.say(e.message); });
  };
  Scanner.prototype.enhance = function(flat){
    var self = this, cur = this.mode === "id" ? "orig" : "magic", cache = {};
    var ov = this.frame("Choose a look", '<div class="xsprev"><img alt="Scanned page"></div><div class="xschips">' + LOOKS.map(function(l){ return '<button class="xschip' + (l[0] === cur ? " on" : "") + '" data-l="' + l[0] + '">' + l[1] + "</button>"; }).join("") + "</div>",
      '<button class="xsb o" data-e="again">↺ Retake</button><button class="xsb o" data-e="rot">↻ Rotate</button><button class="xsb g" data-e="ok">✔ ' + (this.mode === "id" ? (this.idParts.length ? "Finish card" : "Next: back side") : "Add page") + "</button>");
    var img = ov.querySelector(".xsprev img");
    var show = function(){ if (!cache[cur]) cache[cur] = look(flat, cur).toDataURL("image/jpeg", 0.82); img.src = cache[cur]; };
    show();
    ov.querySelector(".xschips").addEventListener("click", function(e){ var b = e.target.closest("[data-l]"); if (!b) return; cur = b.dataset.l; [].forEach.call(ov.querySelectorAll(".xschip"), function(x){ x.classList.toggle("on", x === b); }); setTimeout(show, 10); });
    ov.querySelector(".xsbot").addEventListener("click", function(e){
      var b = e.target.closest("[data-e]"); if (!b) return; var k = b.dataset.e;
      if (k === "again") return self.pick(true);
      if (k === "rot"){ flat = rotate(flat, 1); cache = {}; return show(); }
      var done = look(flat, cur);
      if (self.mode === "id"){
        self.idParts.push(done);
        if (self.idParts.length < 2){ self.say("Now scan the BACK of the card"); return setTimeout(function(){ self.pick(true); }, 700); }
        done = idPage(self.idParts); self.mode = "doc"; self.idParts = [];
      }
      self.pages.push(done);
      if (self.queue && self.queue.length){ var nx = self.queue.shift(); return self.crop(nx); }
      self.list();
    });
  };
  function idPage(parts){   // A4 at 150 dpi, both sides one under the other, at real card size (85.6 x 54 mm)
    var W = 1240, H = 1754, c = D.createElement("canvas"); c.width = W; c.height = H; var x = c.getContext("2d"); x.fillStyle = "#fff"; x.fillRect(0, 0, W, H);
    var cw = Math.round(85.6 / 25.4 * 150 * 1.6), ch = Math.round(54 / 25.4 * 150 * 1.6);
    parts.forEach(function(p, i){
      var k = Math.min(cw / p.width, ch / p.height), w = p.width * k, h = p.height * k, ox = (W - w) / 2, oy = 180 + i * (ch + 160) + (ch - h) / 2;
      x.drawImage(p, ox, oy, w, h); x.strokeStyle = "#ccc"; x.lineWidth = 2; x.strokeRect(ox, oy, w, h);
      x.fillStyle = "#555"; x.font = "28px sans-serif"; x.textAlign = "center"; x.fillText(i ? "Back" : "Front", W / 2, oy - 18);
    });
    return c;
  }
  Scanner.prototype.list = function(){
    var self = this; this.back = function(){ self.home(); };
    var urls = this.pages.map(function(p){ return p.toDataURL("image/jpeg", 0.6); });
    var ov = this.frame(this.pages.length + " page" + (this.pages.length === 1 ? "" : "s"), '<div class="xspages">' + urls.map(function(u, i){ return '<div class="xspg"><b>' + (i + 1) + '</b><img src="' + u + '" alt="Page ' + (i + 1) + '"><div class="a"><button data-p="left" data-i="' + i + '" aria-label="Move left">◀</button><button data-p="rot" data-i="' + i + '" aria-label="Rotate">↻</button><button data-p="del" data-i="' + i + '" aria-label="Delete">🗑</button><button data-p="right" data-i="' + i + '" aria-label="Move right">▶</button></div></div>'; }).join("") + "</div>",
      '<button class="xsb o" data-l="add">📷 Add page</button><button class="xsb o" data-l="text">🔤 Get text</button><button class="xsb g" data-l="pdf">📄 Make PDF</button>');
    ov.addEventListener("click", function(e){
      var b = e.target.closest("[data-p],[data-l]"); if (!b) return;
      if (b.dataset.p){ var i = +b.dataset.i, P = self.pages;
        if (b.dataset.p === "del"){ if (!window.confirm("Delete page " + (i + 1) + "?")) return; P.splice(i, 1); }
        if (b.dataset.p === "rot") P[i] = rotate(P[i], 1);
        if (b.dataset.p === "left" && i > 0){ var t = P[i - 1]; P[i - 1] = P[i]; P[i] = t; }
        if (b.dataset.p === "right" && i < P.length - 1){ var t2 = P[i + 1]; P[i + 1] = P[i]; P[i] = t2; }
        return P.length ? self.list() : self.home();
      }
      if (b.dataset.l === "add") return self.pick(true);
      if (b.dataset.l === "text") return self.ocr();
      if (b.dataset.l === "pdf") return self.pdf();
    });
  };
  Scanner.prototype.stamp = function(){ return new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12); };
  Scanner.prototype.pdf = function(){
    var self = this;
    var pages = this.pages.map(function(p){ var c = toCanvas(p, 1754); return {url: c.toDataURL("image/jpeg", 0.8), w: c.width, h: c.height}; });
    var blob = makePdf(pages), name = "XpertScan-" + this.stamp() + ".pdf", file = new File([blob], name, {type: "application/pdf"}), url = URL.createObjectURL(blob);
    this.back = function(){ self.list(); };
    var mb = (blob.size / 1048576).toFixed(1);
    var ov = this.frame("PDF ready", '<div class="xshome"><div style="font-size:54px">📄</div><h1>' + esc(name) + '</h1><p>' + pages.length + " page" + (pages.length === 1 ? "" : "s") + " · " + mb + ' MB</p>'
      + '<button class="xsbig" data-r="save"><i>⬇️</i><span>Save PDF<small>To your phone or computer</small></span></button>'
      + (navigator.canShare && navigator.canShare({files: [file]}) ? '<button class="xsbig" data-r="share"><i>📤</i><span>Share<small>WhatsApp, email and more</small></span></button>' : "")
      + (this.o.onSend ? '<button class="xsbig" data-r="send"><i>💬</i><span>Send in this chat' + (blob.size > 5 * 1048576 ? '<small>Over 5 MB - save it, or scan fewer pages</small>' : '<small>As a PDF document</small>') + "</span></button>" : "")
      + '<button class="xsbig" data-r="jpg"><i>🖼️</i><span>Save pages as pictures (JPG)</span></button>'
      + '<button class="xsbig" data-r="open"><i>👁️</i><span>Open the PDF</span></button></div>');
    ov.querySelector(".xsmain").addEventListener("click", function(e){
      var b = e.target.closest("[data-r]"); if (!b) return; var r = b.dataset.r;
      if (r === "save"){ dl(url, name); }
      if (r === "open"){ window.open(url, "_blank"); }
      if (r === "share") navigator.share({files: [file], title: name}).catch(function(){});
      if (r === "jpg") pages.forEach(function(p, i){ setTimeout(function(){ dl(p.url, name.replace(".pdf", "-" + (i + 1) + ".jpg")); }, i * 400); });
      if (r === "send" && blob.size <= 5 * 1048576){ b.disabled = true; Promise.resolve(self.o.onSend(file)).then(function(){ self.close(); }).catch(function(x){ b.disabled = false; self.say((x && x.message) || "Could not send it."); }); }
    });
  };
  function dl(url, name){ var a = D.createElement("a"); a.href = url; a.download = name; B.appendChild(a); a.click(); a.remove(); }
  Scanner.prototype.ocr = function(){
    var self = this; this.back = function(){ self.list(); };
    var ov = this.frame("Get text", '<div class="xsocr"><div class="xschips"><button class="xschip on" data-g="eng">English</button><button class="xschip" data-g="urd">اردو Urdu</button><button class="xschip" data-g="eng+urd">Both</button></div>'
      + '<div class="xsbar"><i></i></div><p class="xsst" style="margin:0;opacity:.8;font-size:14px">Reads the text in your ' + this.pages.length + ' page' + (this.pages.length === 1 ? "" : "s") + '. The first time it downloads the reader (a few MB).</p><textarea placeholder="The text appears here"></textarea></div>',
      '<button class="xsb g" data-o="go">🔤 Read text</button><button class="xsb o" data-o="copy">📋 Copy</button>' + (navigator.share ? '<button class="xsb o" data-o="share">📤 Share</button>' : "") + (this.o.onSendText ? '<button class="xsb o" data-o="send">💬 Send as message</button>' : ""));
    var lang = "eng", ta = ov.querySelector("textarea"), bar = ov.querySelector(".xsbar i"), stt = ov.querySelector(".xsst");
    ov.querySelector(".xschips").addEventListener("click", function(e){ var b = e.target.closest("[data-g]"); if (!b) return; lang = b.dataset.g; [].forEach.call(ov.querySelectorAll("[data-g]"), function(x){ x.classList.toggle("on", x === b); }); ta.dir = lang === "urd" ? "rtl" : "auto"; });
    ov.querySelector(".xsbot").addEventListener("click", function(e){
      var b = e.target.closest("[data-o]"); if (!b) return; var o = b.dataset.o;
      if (o === "go"){
        b.disabled = true; stt.textContent = "Starting…";
        var urls = self.pages.map(function(p){ return look(toCanvas(p, 2000), "grey").toDataURL("image/png"); });
        readText(urls, lang, function(s, p){ bar.style.width = Math.round(p * 100) + "%"; stt.textContent = s === "recognizing text" ? "Reading… " + Math.round(p * 100) + "%" : "Getting ready…"; })
          .then(function(t){ ta.value = t || "(No text found)"; stt.textContent = "Done. Check it - small or handwritten text may have mistakes."; bar.style.width = "100%"; b.disabled = false; })
          .catch(function(x){ stt.textContent = (x && x.message) || "Could not read the text."; b.disabled = false; });
      }
      if (o === "copy"){ (navigator.clipboard ? navigator.clipboard.writeText(ta.value) : Promise.reject()).then(function(){ self.say("Copied"); }).catch(function(){ ta.select(); }); }
      if (o === "share") navigator.share({text: ta.value}).catch(function(){});
      if (o === "send" && ta.value.trim()){ Promise.resolve(self.o.onSendText(ta.value.trim().slice(0, 1900))).then(function(){ self.close(); }); }
    });
  };

  function open(opts){ var s = new Scanner(opts); s.home(); return s; }
  window.XSCAN = {open: open, _detect: detect, _warp: warp, _look: look, _pdf: makePdf};
  if (/^\/scan/.test(location.pathname)){
    var go = function(){ open({onClose: function(){ var h = D.createElement("div"); h.className = "xsov"; h.innerHTML = '<div class="xshome"><div style="font-size:46px">📄</div><h1>XpertScan</h1><p>Scan papers into a clean PDF.</p><button class="xsb g" id="xsagain">Start scanning</button> <a class="xsb o" href="/" style="text-decoration:none;display:inline-block">Home</a></div>'; B.appendChild(h); h.querySelector("#xsagain").onclick = function(){ h.remove(); go(); }; }}); };
    go();
  }
})();
