/* XpertAcademy extras (academy-x-1.js)
   - Quick check after every lesson (written questions, or built from the lesson's word = meaning lists)
   - Excel sheets you can edit, with formulas that really calculate, and a .xlsx download
   - Excel practice tasks that check your formula
   - Questions & answers under every lesson
   index.html calls XCLX.lesson(course, index, lesson, lang) after it draws a lesson. */
(function(){
  "use strict";
  var CHECKS = null, CHK_LOADING = null, LANG = "en", CUR = null;

  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function L(en, ur){ return LANG === "ur" && ur ? ur : en; }
  function both(en, ur){ return LANG === "ur" ? ur : en + ' <span class="xur" lang="ur" dir="rtl">' + ur + '</span>'; }
  function csrf(){ var m = document.cookie.match(/(?:^|; )xc_csrf=([^;]+)/) || document.cookie.match(/(?:^|; )csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ""; }
  function api(path, body){
    var o = { credentials: "same-origin", headers: { "Accept": "application/json" } };
    if (body !== undefined){ o.method = "POST"; o.headers["Content-Type"] = "application/json"; o.headers["X-CSRFToken"] = csrf(); o.body = JSON.stringify(body); }
    return fetch(path, o).then(function(r){
      return r.text().then(function(t){ var d = {}; try { d = t ? JSON.parse(t) : {}; } catch (e) {} if (!r.ok){ var er = new Error(d.detail || ("Error " + r.status)); er.status = r.status; throw er; } return d; });
    });
  }
  function shuffle(a){ for (var i = a.length - 1; i > 0; i--){ var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

  /* ------------------------------------------------------------ styles */
  var css = ""
   + ".xlx{margin:22px 0 6px;border:1px solid var(--line,#e3e8f0);border-radius:14px;padding:14px 16px;background:var(--card,#fff)}"
   + ".xlx h3{margin:0 0 10px;font-size:1.05rem;display:flex;gap:8px;align-items:center;flex-wrap:wrap}"
   + ".xur{font-family:'Noto Nastaliq Urdu',serif;font-weight:400;opacity:.75;font-size:.92em}"
   + ".xq{margin:12px 0 4px}.xq p{margin:0 0 8px;font-weight:600}"
   + ".xo{display:block;width:100%;text-align:left;margin:6px 0;padding:10px 12px;border-radius:10px;border:1px solid var(--line,#d8dee9);background:transparent;color:inherit;font:inherit;cursor:pointer}"
   + ".xo:hover{border-color:var(--accent,#1B4DFF)}.xo.ok{background:#e7f7ec;border-color:#1f9d55;color:#0f5132}.xo.no{background:#fdecec;border-color:#d64545;color:#842029}"
   + ".xo:disabled{cursor:default}.xwhy{font-size:.92rem;margin:6px 0 0;padding:8px 10px;border-radius:8px;background:rgba(27,77,255,.06)}"
   + ".xscore{margin-top:12px;font-weight:700}.xbtn{padding:9px 14px;border-radius:10px;border:0;background:var(--accent,#1B4DFF);color:#fff;font:inherit;font-weight:600;cursor:pointer}"
   + ".xbtn.ghost{background:transparent;color:var(--accent,#1B4DFF);border:1px solid currentColor}.xbtn:disabled{opacity:.5;cursor:default}"
   + ".xsbar{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.xsbar .xbtn{padding:6px 12px;font-size:.9rem}"
   + ".xgrid{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line,#d8dee9);border-radius:10px;margin:6px 0}"
   + ".xgrid table{border-collapse:collapse;font-size:.92rem;min-width:100%}.xgrid th{background:rgba(127,127,127,.12);font-weight:600;padding:4px 6px;min-width:30px}"
   + ".xgrid td{border:1px solid rgba(127,127,127,.25);padding:0;min-width:92px}.xgrid input{width:100%;box-sizing:border-box;border:0;padding:7px 6px;font:inherit;background:transparent;color:inherit;outline:none}"
   + ".xgrid input:focus{box-shadow:inset 0 0 0 2px #217346;background:rgba(33,115,70,.06)}.xgrid input.num{text-align:right}.xgrid input.err{color:#d64545}.xgrid td.goal{background:rgba(255,193,7,.18)}"
   + ".xfx{font-family:ui-monospace,Consolas,monospace;font-size:.88rem;padding:6px 8px;border-radius:8px;background:rgba(127,127,127,.1);min-height:1.4em;word-break:break-all}"
   + ".xmsg{margin:8px 0 0;font-weight:600}.xmsg.ok{color:#1f9d55}.xmsg.no{color:#d64545}"
   + ".xqa textarea{width:100%;box-sizing:border-box;min-height:70px;border-radius:10px;border:1px solid var(--line,#d8dee9);padding:9px;font:inherit;background:transparent;color:inherit;resize:vertical}"
   + ".xqi{border-top:1px solid var(--line,#e3e8f0);padding:12px 0}.xqi:first-of-type{border-top:0}.xqh{font-size:.85rem;opacity:.75;margin-bottom:4px}.xqh a{color:inherit;font-weight:600}"
   + ".xqb{white-space:pre-wrap;word-break:break-word}.xans{margin:8px 0 0 14px;padding-left:12px;border-left:3px solid var(--line,#e3e8f0)}.xans .xqi{padding:8px 0}"
   + ".xtag{font-size:.72rem;padding:1px 7px;border-radius:20px;background:#1B4DFF;color:#fff;margin-left:4px}.xtag.h{background:#1f9d55}"
   + ".xlink{background:none;border:0;color:var(--accent,#1B4DFF);cursor:pointer;font:inherit;font-size:.88rem;padding:4px 8px 4px 0}"
   + ".xtask{border-left:4px solid #217346;padding-left:12px}.xmuted{opacity:.7;font-size:.9rem}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  /* ------------------------------------------------------------ formula engine (a small Excel) */
  function colNum(s){ var n = 0; for (var i = 0; i < s.length; i++) n = n * 26 + (s.charCodeAt(i) - 64); return n - 1; }
  function colLet(n){ var s = ""; while (n >= 0){ s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26) - 1; } return s; }
  function ERR(c){ return { err: c }; }
  function isErr(v){ return v && typeof v === "object" && v.err; }

  function dateSerial(d, m, y){ var t = Date.UTC(y, m - 1, d); return Math.round((t - Date.UTC(1899, 11, 30)) / 86400000); }
  function literal(raw){            // what a typed (non-formula) cell holds
    var s = String(raw == null ? "" : raw);
    if (s === "") return null;
    if (s.charAt(0) === "'") return s.slice(1);
    var t = s.trim().replace(/,/g, "");
    if (/^-?\d+(\.\d+)?$/.test(t)) return parseFloat(t);
    if (/^-?\d+(\.\d+)?%$/.test(t)) return parseFloat(t) / 100;
    var m = s.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (m) return { date: dateSerial(+m[1], +m[2], +m[3]) };
    if (/^true$/i.test(t)) return true;
    if (/^false$/i.test(t)) return false;
    return s;
  }
  function tokenize(f){
    var out = [], i = 0, m;
    var re = /^(\s+)|^("(?:[^"]|"")*")|^(\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)(?![A-Za-z0-9(])|^(\d+(?:\.\d+)?%?)|^([A-Za-z][A-Za-z0-9.]*)(?=\s*\()|^(TRUE|FALSE)\b|^(<>|<=|>=|[-+*\/^&=<>(),:;])/i;
    while (i < f.length){
      m = re.exec(f.slice(i));
      if (!m) throw ERR("#NAME?");
      if (m[2]) out.push({ t: "s", v: m[2].slice(1, -1).replace(/""/g, '"') });
      else if (m[3]) out.push({ t: "r", v: m[3].toUpperCase() });
      else if (m[4]) out.push({ t: "n", v: /%$/.test(m[4]) ? parseFloat(m[4]) / 100 : parseFloat(m[4]) });
      else if (m[5]) out.push({ t: "f", v: m[5].toUpperCase() });
      else if (m[6]) out.push({ t: "b", v: m[6].toUpperCase() === "TRUE" });
      else if (m[7]) out.push({ t: "o", v: m[7] === ";" ? "," : m[7] });
      i += m[0].length;
    }
    return out;
  }
  function Sheet(raw){ this.raw = raw; this.cache = {}; this.busy = {}; }
  Sheet.prototype.rawAt = function(r, c){ return (this.raw[r] && this.raw[r][c] != null) ? String(this.raw[r][c]) : ""; };
  Sheet.prototype.val = function(r, c){
    var k = r + "," + c;
    if (k in this.cache) return this.cache[k];
    if (this.busy[k]) return ERR("#CIRCULAR");
    var s = this.rawAt(r, c), v;
    if (s.charAt(0) === "=" && s.length > 1){
      this.busy[k] = true;
      try { v = this.evalFormula(s.slice(1)); } catch (e){ v = isErr(e) ? e : ERR("#ERROR"); }
      this.busy[k] = false;
    } else v = literal(s);
    if (v && v.date !== undefined) v = v.date;
    this.cache[k] = v; return v;
  };
  Sheet.prototype.isDate = function(r, c){ var l = literal(this.rawAt(r, c)); return !!(l && l.date !== undefined); };
  function parseRef(a){ var m = a.match(/^\$?([A-Z]{1,3})\$?(\d+)$/); return { c: colNum(m[1]), r: parseInt(m[2], 10) - 1 }; }
  Sheet.prototype.evalFormula = function(f){
    var tk = tokenize(f), p = 0, self = this;
    function peek(){ return tk[p]; }
    function eat(v){ var t = tk[p]; if (!t || t.v !== v) throw ERR("#ERROR"); p++; }
    function range(a){
      var parts = a.split(":"), s = parseRef(parts[0]), e = parseRef(parts[1] || parts[0]);
      return { range: true, r1: Math.min(s.r, e.r), r2: Math.max(s.r, e.r), c1: Math.min(s.c, e.c), c2: Math.max(s.c, e.c) };
    }
    function cmpE(){ var a = catE(); while (peek() && /^(=|<>|<|>|<=|>=)$/.test(peek().v) && peek().t === "o"){ var o = tk[p++].v, b = catE(); a = compare(o, val1(a), val1(b)); } return a; }
    function catE(){ var a = addE(); while (peek() && peek().v === "&"){ p++; var b = addE(); a = txt(val1(a)) + txt(val1(b)); } return a; }
    function addE(){ var a = mulE(); while (peek() && (peek().v === "+" || peek().v === "-") && peek().t === "o"){ var o = tk[p++].v, b = mulE(); a = arith(o, val1(a), val1(b)); } return a; }
    function mulE(){ var a = powE(); while (peek() && (peek().v === "*" || peek().v === "/")){ var o = tk[p++].v, b = powE(); a = arith(o, val1(a), val1(b)); } return a; }
    function powE(){ var a = unE(); while (peek() && peek().v === "^"){ p++; var b = unE(); a = arith("^", val1(a), val1(b)); } return a; }
    function unE(){ if (peek() && peek().v === "-"){ p++; return arith("*", -1, val1(unE())); } if (peek() && peek().v === "+"){ p++; return unE(); } return prim(); }
    function prim(){
      var t = tk[p++];
      if (!t) throw ERR("#ERROR");
      if (t.t === "n" || t.t === "s" || t.t === "b") return t.v;
      if (t.t === "r") return t.v.indexOf(":") > 0 ? range(t.v) : (function(){ var x = parseRef(t.v); return self.val(x.r, x.c); })();
      if (t.v === "("){ var v = cmpE(); eat(")"); return v; }
      if (t.t === "f"){
        eat("("); var args = [];
        function arg(){ var keep = p; try { return cmpE(); } catch (e){ if (!isErr(e) || e.err === "#ERROR" && !skip()) throw e; return e; } }
        function skip(){ var depth = 0; while (p < tk.length){ var v = tk[p].v; if (v === "(") depth++; else if (v === ")"){ if (!depth) return true; depth--; } else if (v === "," && !depth) return true; p++; } return false; }
        if (peek() && peek().v !== ")"){ args.push(arg()); while (peek() && peek().v === ","){ p++; args.push(arg()); } }
        eat(")");
        return call(t.v, args);
      }
      throw ERR("#ERROR");
    }
    function val1(v){ if (v && v.range){ if (v.r1 === v.r2 && v.c1 === v.c2) return self.val(v.r1, v.c1); return ERR("#VALUE!"); } return v; }
    var res = cmpE();
    if (p < tk.length) throw ERR("#ERROR");
    res = val1(res);
    return res == null ? 0 : res;
  };
  function num(v){
    if (isErr(v)) throw v;
    if (v == null || v === "") return 0;
    if (typeof v === "number") return v;
    if (typeof v === "boolean") return v ? 1 : 0;
    var t = String(v).trim().replace(/,/g, "");
    if (/^-?\d+(\.\d+)?$/.test(t)) return parseFloat(t);
    throw ERR("#VALUE!");
  }
  function txt(v){ if (isErr(v)) throw v; if (v == null) return ""; if (typeof v === "boolean") return v ? "TRUE" : "FALSE"; if (typeof v === "number") return String(+v.toFixed(10)); return String(v); }
  function arith(o, a, b){
    a = num(a); b = num(b);
    if (o === "+") return a + b; if (o === "-") return a - b; if (o === "*") return a * b;
    if (o === "/"){ if (b === 0) throw ERR("#DIV/0!"); return a / b; }
    return Math.pow(a, b);
  }
  function compare(o, a, b){
    if (isErr(a)) throw a; if (isErr(b)) throw b;
    if (a == null) a = typeof b === "string" ? "" : 0; if (b == null) b = typeof a === "string" ? "" : 0;
    var x = a, y = b;
    if (typeof a === "string" || typeof b === "string"){ x = String(a).toLowerCase(); y = String(b).toLowerCase(); }
    switch (o){ case "=": return x === y; case "<>": return x !== y; case "<": return x < y; case ">": return x > y; case "<=": return x <= y; default: return x >= y; }
  }
  var SH = null;   // the sheet being worked out (used by call)
  function cells(v){ var out = []; if (v && v.range){ for (var r = v.r1; r <= v.r2; r++) for (var c = v.c1; c <= v.c2; c++) out.push(SH.val(r, c)); } else out.push(v); return out; }
  function nums(args){ var out = []; args.forEach(function(a){ var isR = a && a.range; cells(a).forEach(function(v){ if (isErr(v)) throw v; if (typeof v === "number") out.push(v); else if (!isR && v != null && v !== ""){ out.push(num(v)); } }); }); return out; }
  function crit(c){
    if (isErr(c)) throw c;
    var s = String(c == null ? "" : c), m = s.match(/^(<>|<=|>=|=|<|>)?(.*)$/), op = m[1] || "=", rhs = m[2];
    var n = /^-?\d+(\.\d+)?$/.test(rhs.trim()) ? parseFloat(rhs) : null;
    return function(v){
      if (n !== null && typeof v === "number") return compare(op, v, n);
      if (n !== null && op !== "=" && op !== "<>") return false;
      return compare(op, v == null ? "" : v, rhs);
    };
  }
  function call(name, a){
    switch (name){
      case "SUM": return nums(a).reduce(function(s, x){ return s + x; }, 0);
      case "AVERAGE": var n = nums(a); if (!n.length) throw ERR("#DIV/0!"); return n.reduce(function(s, x){ return s + x; }, 0) / n.length;
      case "MIN": n = nums(a); return n.length ? Math.min.apply(null, n) : 0;
      case "MAX": n = nums(a); return n.length ? Math.max.apply(null, n) : 0;
      case "COUNT": var k = 0; a.forEach(function(x){ cells(x).forEach(function(v){ if (typeof v === "number") k++; }); }); return k;
      case "COUNTA": k = 0; a.forEach(function(x){ cells(x).forEach(function(v){ if (v != null && v !== "") k++; }); }); return k;
      case "COUNTBLANK": k = 0; cells(a[0]).forEach(function(v){ if (v == null || v === "") k++; }); return k;
      case "IF": var t = a[0] && a[0].range ? cells(a[0])[0] : a[0]; if (isErr(t)) throw t; return truthy(t) ? (a.length > 1 ? one(a[1]) : true) : (a.length > 2 ? one(a[2]) : false);
      case "IFS": for (var i = 0; i + 1 < a.length; i += 2) if (truthy(one(a[i]))) return one(a[i + 1]); throw ERR("#N/A");
      case "IFERROR": try { var v = one(a[0]); if (isErr(v)) return one(a[1]); return v; } catch (e){ return one(a[1]); }
      case "AND": return a.every(function(x){ return cells(x).every(truthy); });
      case "OR": return a.some(function(x){ return cells(x).some(truthy); });
      case "NOT": return !truthy(one(a[0]));
      case "ROUND": var f = Math.pow(10, num(one(a[1] || 0))); return Math.round(num(one(a[0])) * f) / f;
      case "ABS": return Math.abs(num(one(a[0])));
      case "TRIM": return txt(one(a[0])).replace(/\s+/g, " ").trim();
      case "UPPER": return txt(one(a[0])).toUpperCase();
      case "LOWER": return txt(one(a[0])).toLowerCase();
      case "LEN": return txt(one(a[0])).length;
      case "CONCAT": case "CONCATENATE": return a.map(function(x){ return cells(x).map(txt).join(""); }).join("");
      case "TODAY": var d = new Date(); return dateSerial(d.getDate(), d.getMonth() + 1, d.getFullYear());
      case "COUNTIF": var ok = crit(one(a[1])); return cells(a[0]).filter(ok).length;
      case "SUMIF": case "AVERAGEIF":
        ok = crit(one(a[1])); var rg = cells(a[0]), sm = a[2] ? cells(a[2]) : rg, tot = 0, cnt = 0;
        rg.forEach(function(v, j){ if (ok(v) && typeof sm[j] === "number"){ tot += sm[j]; cnt++; } });
        if (name === "SUMIF") return tot; if (!cnt) throw ERR("#DIV/0!"); return tot / cnt;
      case "VLOOKUP":
        var key = one(a[0]), tb = a[1], col = num(one(a[2])), exact = a.length < 4 || !truthy(one(a[3]));
        if (!tb || !tb.range) throw ERR("#VALUE!");
        if (col < 1 || tb.c1 + col - 1 > tb.c2) throw ERR("#REF!");
        var best = -1;
        for (var r = tb.r1; r <= tb.r2; r++){
          var v2 = SH.val(r, tb.c1);
          if (exact){ if (compare("=", v2, key)){ best = r; break; } }
          else if (v2 != null && compare("<=", v2, key)) best = r;
        }
        if (best < 0) throw ERR("#N/A");
        return SH.val(best, tb.c1 + col - 1);
      case "XLOOKUP":
        var lk = cells(a[1]), rt = cells(a[2]), kk = one(a[0]);
        for (i = 0; i < lk.length; i++) if (compare("=", lk[i], kk)) return rt[i];
        if (a.length > 3) return one(a[3]);
        throw ERR("#N/A");
    }
    throw ERR("#NAME?");
  }
  function one(v){ if (v && v.range) return v.r1 === v.r2 && v.c1 === v.c2 ? SH.val(v.r1, v.c1) : ERR("#VALUE!"); return v; }
  function truthy(v){ if (isErr(v)) throw v; if (typeof v === "string"){ if (/^true$/i.test(v)) return true; if (/^false$/i.test(v)) return false; throw ERR("#VALUE!"); } return !!v; }
  // wrap the sheet so call() can reach it
  var _val = Sheet.prototype.evalFormula;
  Sheet.prototype.evalFormula = function(f){ var keep = SH; SH = this; try { return _val.call(this, f); } finally { SH = keep; } };

  function show(v, isDate, rawS){
    if (isErr(v)) return v.err;
    if (v == null) return "";
    if (typeof v === "boolean") return v ? "TRUE" : "FALSE";
    if (typeof v === "number"){
      if (isDate && v > 0 && v < 2958466){ var d = new Date(Date.UTC(1899, 11, 30) + v * 86400000); return ("0" + d.getUTCDate()).slice(-2) + "/" + ("0" + (d.getUTCMonth() + 1)).slice(-2) + "/" + d.getUTCFullYear(); }
      if (/%\s*$/.test(rawS || "")) return +(v * 100).toFixed(2) + "%";
      return String(+v.toFixed(4));
    }
    return String(v);
  }
  // move a formula's relative references by dr rows / dc columns (what Excel does when you copy)
  function shift(f, dr, dc){
    return f.replace(/("(?:[^"]|"")*")|(\$?)([A-Z]{1,3})(\$?)(\d+)(?![A-Za-z0-9(])/gi, function(all, str, d1, col, d2, row){
      if (str) return str;
      var c = d1 ? col.toUpperCase() : colLet(colNum(col.toUpperCase()) + dc), r = d2 ? row : String(parseInt(row, 10) + dr);
      if (parseInt(r, 10) < 1 || colNum(c.replace(/\$/g, "")) < 0) return "#REF!";
      return d1 + c + d2 + r;
    });
  }

  /* ------------------------------------------------------------ editable grid */
  function Grid(box, rows, opts){
    opts = opts || {};
    var raw = rows.map(function(r){ return r.slice(); });
    var W = 0; raw.forEach(function(r){ W = Math.max(W, r.length); });
    var addC = opts.extraCols == null ? 2 : opts.extraCols, addR = opts.extraRows == null ? 2 : opts.extraRows;
    W += addC; var H = raw.length + addR;
    for (var r = 0; r < H; r++){ raw[r] = raw[r] || []; for (var c = 0; c < W; c++) if (raw[r][c] == null) raw[r][c] = ""; }
    var h = '<div class="xfx" aria-live="polite">' + esc(L("Tap a cell. Type a value or a formula starting with =", "کسی خانے پر ٹیپ کریں۔ قیمت یا = سے شروع ہونے والا فارمولا لکھیں")) + '</div><div class="xgrid"><table><tr><th></th>';
    for (c = 0; c < W; c++) h += "<th>" + colLet(c) + "</th>";
    h += "</tr>";
    for (r = 0; r < H; r++){
      h += "<tr><th>" + (r + 1) + "</th>";
      for (c = 0; c < W; c++) h += '<td' + (opts.goal === colLet(c) + (r + 1) ? ' class="goal"' : '') + '><input data-r="' + r + '" data-c="' + c + '" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="' + colLet(c) + (r + 1) + '"></td>';
      h += "</tr>";
    }
    box.innerHTML = h + "</table></div>";
    var fx = box.querySelector(".xfx"), ins = box.querySelectorAll("input"), self = this, focused = null;
    this.raw = raw;
    function paint(){
      var s = new Sheet(raw);
      for (var i = 0; i < ins.length; i++){
        var el = ins[i], rr = +el.dataset.r, cc = +el.dataset.c;
        if (el === focused) continue;
        var v = s.val(rr, cc); el.value = show(v, s.isDate(rr, cc), raw[rr][cc].charAt(0) === "=" ? "" : raw[rr][cc]);
        el.className = (typeof v === "number" ? "num" : "") + (isErr(v) ? " err" : "");
      }
      self.sheet = s;
      if (opts.onChange) opts.onChange(s);
    }
    box.addEventListener("focusin", function(e){
      var el = e.target; if (el.tagName !== "INPUT") return;
      focused = el; el.value = raw[+el.dataset.r][+el.dataset.c];
      fx.textContent = colLet(+el.dataset.c) + (+el.dataset.r + 1) + ":  " + (el.value || "");
    });
    box.addEventListener("input", function(e){ var el = e.target; if (el.tagName === "INPUT") fx.textContent = colLet(+el.dataset.c) + (+el.dataset.r + 1) + ":  " + el.value; });
    box.addEventListener("focusout", function(e){
      var el = e.target; if (el.tagName !== "INPUT") return;
      raw[+el.dataset.r][+el.dataset.c] = el.value; focused = null; paint();
    });
    box.addEventListener("keydown", function(e){
      var el = e.target; if (el.tagName !== "INPUT") return;
      var rr = +el.dataset.r, cc = +el.dataset.c, to = null;
      if (e.key === "Enter"){ to = [rr + (e.shiftKey ? -1 : 1), cc]; }
      else if (e.key === "Escape"){ el.value = raw[rr][cc]; el.blur(); return; }
      else if (e.key === "Tab"){ to = [rr, cc + (e.shiftKey ? -1 : 1)]; }
      if (to){
        var nx = box.querySelector('input[data-r="' + to[0] + '"][data-c="' + to[1] + '"]');
        if (nx){ e.preventDefault(); el.blur(); nx.focus(); nx.select(); }
        else if (e.key === "Enter"){ e.preventDefault(); el.blur(); }
      }
    });
    paint();
    this.paint = paint;
  }

  /* ------------------------------------------------------------ .xlsx download (SheetJS, loaded only when asked) */
  var XL = null;
  function loadXL(){
    if (window.XLSX) return Promise.resolve(window.XLSX);
    if (XL) return XL;
    XL = new Promise(function(ok, no){
      var s = document.createElement("script"); s.src = "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js";
      s.onload = function(){ ok(window.XLSX); }; s.onerror = function(){ XL = null; no(new Error("Could not load the Excel maker. Check your connection.")); };
      document.head.appendChild(s);
    });
    return XL;
  }
  function download(rows, name){
    return loadXL().then(function(X){
      var ws = {}, W = 0, H = rows.length;
      rows.forEach(function(r, ri){
        W = Math.max(W, r.length);
        r.forEach(function(v, ci){
          var s = String(v == null ? "" : v), addr = colLet(ci) + (ri + 1);
          if (s === "") return;
          if (s.charAt(0) === "=" && s.length > 1){ ws[addr] = { t: "n", f: s.slice(1) }; return; }
          var l = literal(s);
          if (typeof l === "number") ws[addr] = /%$/.test(s.trim()) ? { t: "n", v: l, z: "0%" } : { t: "n", v: l };
          else if (l && l.date !== undefined) ws[addr] = { t: "n", v: l.date, z: "dd/mm/yyyy" };
          else if (typeof l === "boolean") ws[addr] = { t: "b", v: l };
          else ws[addr] = { t: "s", v: String(l) };
        });
      });
      ws["!ref"] = "A1:" + colLet(Math.max(0, W - 1)) + Math.max(1, H);
      ws["!cols"] = []; for (var c = 0; c < W; c++) ws["!cols"].push({ wch: 14 });
      var wb = X.utils.book_new(); X.utils.book_append_sheet(wb, ws, "Practice");
      X.writeFile(wb, name.replace(/[^\w-]+/g, "_").slice(0, 60) + ".xlsx");
    });
  }
  function trimRows(raw){
    var rows = raw.map(function(r){ var x = r.slice(); while (x.length && String(x[x.length - 1]) === "") x.pop(); return x; });
    while (rows.length && !rows[rows.length - 1].length) rows.pop();
    return rows;
  }

  /* lesson sheets: read the table index.html drew, add Try it + Download */
  function readSheet(el){
    var rows = [], trs = el.querySelectorAll("tr");
    for (var i = 1; i < trs.length; i++){
      var tds = trs[i].querySelectorAll("td"), row = [];
      for (var j = 1; j < tds.length; j++) row.push(tds[j].textContent);
      rows.push(row);
    }
    return rows;
  }
  function enhanceSheets(root, c, i){
    var list = root.querySelectorAll(".sheet");
    Array.prototype.forEach.call(list, function(el, n){
      if (el.dataset.xlx) return; el.dataset.xlx = "1";
      var rows = readSheet(el), cap = (el.querySelector(".cap") || {}).textContent || (c.name || c.id) + " " + (i + 1);
      var bar = document.createElement("div"); bar.className = "xsbar";
      bar.innerHTML = '<button class="xbtn" data-a="try">✏️ ' + esc(L("Try it here", "یہیں آزمائیں")) + '</button>'
        + '<button class="xbtn ghost" data-a="dl">⬇ ' + esc(L("Download .xlsx", "ایکسل فائل ڈاؤن لوڈ")) + '</button>';
      el.parentNode.insertBefore(bar, el.nextSibling);
      var g = null, holder = null;
      bar.addEventListener("click", function(e){
        var b = e.target.closest("button"); if (!b) return;
        if (b.dataset.a === "try"){
          if (!g){
            holder = document.createElement("div"); bar.parentNode.insertBefore(holder, bar.nextSibling);
            g = new Grid(holder, rows); el.style.display = "none";
            b.textContent = "↺ " + L("Back to the example", "مثال پر واپس");
          } else { holder.remove(); g = null; el.style.display = ""; b.innerHTML = "✏️ " + esc(L("Try it here", "یہیں آزمائیں")); }
        } else {
          b.disabled = true;
          download(g ? trimRows(g.raw) : rows, "XpertAcademy_" + c.id + "_lesson" + (i + 1) + "_" + (n + 1)).catch(function(er){ alertBox(bar, er.message); }).then(function(){ b.disabled = false; });
        }
      });
    });
  }
  function alertBox(after, msg){ var p = document.createElement("p"); p.className = "xmsg no"; p.textContent = msg; after.parentNode.insertBefore(p, after.nextSibling); setTimeout(function(){ p.remove(); }, 6000); }

  /* ------------------------------------------------------------ Excel practice tasks */
  var SALES = [["Date","City","Salesperson","Amount"],["01/08","Lahore","Ayesha","12500"],["01/08","Karachi","Bilal","8900"],["02/08","Lahore","Hina","9100"],["02/08","Islamabad","Bilal","7400"],["03/08","Lahore","Ayesha","15200"]];
  var TASKS = {
    3: { rows: [["Item","Price"],["Rice bag","2500"],["Cooking oil","890"],["Sugar","640"],["Total",""]], cell: "B5", expect: 4030, nolit: ["2500","890","640"],
         ask: ["In B5, write a formula that adds the three prices.", "B5 میں ایسا فارمولا لکھیں جو تینوں قیمتیں جمع کرے۔"], hint: "Start with = and click or type the cells: B2, B3, B4.", ans: "=B2+B3+B4  or  =SUM(B2:B4)" },
    4: { rows: [["Item","Price"],["Rice bag","2500"],["Cooking oil","890"],["Sugar","640"],["Tea","1150"],["Average",""]], cell: "B6", expect: 1295, need: /AVERAGE/i,
         ask: ["In B6, use a function to get the average price.", "B6 میں فنکشن سے اوسط قیمت نکالیں۔"], hint: "A range uses a colon: B2:B5.", ans: "=AVERAGE(B2:B5)" },
    5: { rows: [["Category","Budget","Actual","Difference"],["Rent","35000","35000",""],["Groceries","25000","28400",""],["Utilities","8000","9200",""],["Transport","6000","5100",""]], cell: "D3", expect: 3400, nolit: ["28400","25000"],
         ask: ["In D3, work out how much Groceries went over budget (Actual minus Budget).", "D3 میں گروسری کا فرق نکالیں (اصل خرچ منفی بجٹ)۔"], hint: "Actual is in C3, Budget is in B3.", ans: "=C3-B3" },
    6: { rows: [["Item","Price","Tax","","17%"],["Rice bag","2500","","",""],["Cooking oil","890","","",""],["Sugar","640","","",""]], cell: "C2", expect: 425, copy: { to: "C3", expect: 151.3 },
         ask: ["In C2, write the tax for Rice bag using the rate in E1, so the same formula still works when copied down to C3.", "C2 میں E1 والی شرح سے ٹیکس نکالیں، اس طرح کہ نیچے کاپی کرنے پر بھی درست رہے۔"], hint: "Pin the rate with dollar signs: $E$1.", ans: "=B2*$E$1" },
    8: { rows: [["Student","Marks","Result"],["Ayesha","78",""],["Bilal","35",""],["Hina","91",""]], cell: "C2", expect: "Pass", copy: { to: "C3", expect: "Fail" },
         ask: ["In C2, show Pass if the marks are 40 or more, otherwise Fail.", "C2 میں 40 یا زیادہ نمبر پر Pass ورنہ Fail دکھائیں۔"], hint: "=IF(test, value if true, value if false). Text needs double quotes.", ans: "=IF(B2>=40,\"Pass\",\"Fail\")" },
    10: { rows: SALES.concat([["","","",""],["Lahore total","","",""]]), cell: "B8", expect: 36800, need: /SUMIF/i,
         ask: ["In B8, add up all the Lahore sales with SUMIF.", "B8 میں SUMIF سے لاہور کی تمام سیلز جمع کریں۔"], hint: "SUMIF(where to look, what to match, what to add).", ans: "=SUMIF(B2:B6,\"Lahore\",D2:D6)" },
    11: { rows: [["Code","Product","Price","","Find","Price"],["P01","Rice bag","2500","","P03",""],["P02","Cooking oil","890","","",""],["P03","Sugar","640","","",""],["P04","Tea","1150","","",""]], cell: "F2", expect: 640, need: /LOOKUP/i,
         ask: ["In F2, look up the price of the code in E2.", "F2 میں E2 والے کوڈ کی قیمت تلاش کریں۔"], hint: "=VLOOKUP(what, table, column number, FALSE)", ans: "=VLOOKUP(E2,A2:C5,3,FALSE)  or  =XLOOKUP(E2,A2:A5,C2:C5)" },
    13: { rows: [["Roll","Name","Urdu","English","Maths","Science","Total"],["1","Ayesha","78","82","91","88",""],["2","Bilal","45","38","52","41",""]], cell: "G2", expect: 339, copy: { to: "G3", expect: 176 }, need: /SUM/i,
         ask: ["In G2, add Ayesha's four marks, so it also works when copied down for Bilal.", "G2 میں عائشہ کے چاروں نمبر جمع کریں، اس طرح کہ بلال کے لیے کاپی کرنے پر بھی کام کرے۔"], hint: "=SUM(C2:F2)", ans: "=SUM(C2:F2)" }
  };
  function addrRC(a){ var x = parseRef(a); return x; }
  function taskBlock(c, i){
    var T = TASKS[i]; if (!T || c.id !== "excel") return null;
    var d = document.createElement("section"); d.className = "xlx xtask";
    d.innerHTML = '<h3>🎯 ' + both("Practice task", "مشق") + '</h3><p>' + esc(L(T.ask[0], T.ask[1])) + '</p><div class="xg"></div>'
      + '<div class="xsbar"><button class="xbtn" data-a="check">' + esc(L("Check my answer", "جواب چیک کریں")) + '</button>'
      + '<button class="xbtn ghost" data-a="hint">' + esc(L("Hint", "اشارہ")) + '</button>'
      + '<button class="xbtn ghost" data-a="show">' + esc(L("Show answer", "جواب دکھائیں")) + '</button>'
      + '<button class="xbtn ghost" data-a="dl">⬇ ' + esc(L("Download this sheet", "یہ شیٹ ڈاؤن لوڈ کریں")) + '</button></div><p class="xmsg"></p>';
    var g = new Grid(d.querySelector(".xg"), T.rows, { goal: T.cell, extraRows: 1, extraCols: 1 }), msg = d.querySelector(".xmsg");
    function say(ok, t){ msg.className = "xmsg " + (ok ? "ok" : "no"); msg.textContent = t; }
    d.addEventListener("click", function(e){
      var b = e.target.closest("button"); if (!b) return;
      if (b.dataset.a === "hint"){ msg.className = "xmsg"; msg.textContent = "💡 " + T.hint; return; }
      if (b.dataset.a === "show"){ msg.className = "xmsg"; msg.textContent = T.cell + ":  " + T.ans; return; }
      if (b.dataset.a === "dl"){ download(trimRows(g.raw), "XpertAcademy_excel_task_" + (i + 1)).catch(function(er){ say(false, er.message); }); return; }
      if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
      var p = addrRC(T.cell), f = String(g.raw[p.r][p.c] || "").trim();
      if (!f) return say(false, L("Type your answer in the yellow cell " + T.cell + " first.", "پہلے پیلے خانے " + T.cell + " میں جواب لکھیں۔"));
      if (f.charAt(0) !== "=") return say(false, L("A formula must start with =", "فارمولا = سے شروع ہوتا ہے"));
      if (T.nolit && T.nolit.some(function(n){ return new RegExp("(^|[^\\d])" + n + "([^\\d]|$)").test(f); })) return say(false, L("Right idea, but point at the cells instead of typing the numbers - then it stays correct when a price changes.", "خیال درست ہے، مگر نمبر لکھنے کی بجائے خانوں کا حوالہ دیں تاکہ قیمت بدلنے پر بھی جواب درست رہے۔"));
      if (T.need && !T.need.test(f)) return say(false, L("Use the function from this lesson (" + T.need.source.replace(/\\/g, "") + ").", "اس سبق والا فنکشن استعمال کریں (" + T.need.source + ")۔"));
      var s = new Sheet(g.raw), v = s.val(p.r, p.c);
      if (isErr(v)) return say(false, L("Excel would show " + v.err + ". Check your brackets, commas and quotes.", "ایکسل " + v.err + " دکھائے گا۔ بریکٹ، کوما اور کوٹس چیک کریں۔"));
      if (!same(v, T.expect)) return say(false, L("Not yet - that gives " + show(v) + ". Try again.", "ابھی نہیں - اس سے " + show(v) + " آتا ہے۔ دوبارہ کوشش کریں۔"));
      if (T.copy){
        var q = addrRC(T.copy.to), raw2 = g.raw.map(function(r){ return r.slice(); });
        raw2[q.r][q.c] = "=" + shift(f.slice(1), q.r - p.r, q.c - p.c);
        var v2 = new Sheet(raw2).val(q.r, q.c);
        if (!same(v2, T.copy.expect)) return say(false, L("Correct in " + T.cell + ", but copied to " + T.copy.to + " it becomes " + raw2[q.r][q.c] + " and gives " + show(v2) + ". " + (i === 6 ? "Pin E1 with dollar signs." : ""), T.cell + " میں درست، مگر " + T.copy.to + " میں کاپی کرنے پر غلط نتیجہ آتا ہے۔"));
        g.raw[q.r][q.c] = raw2[q.r][q.c]; g.paint();
      }
      say(true, "✔ " + L("Correct! Well done.", "شاباش! بالکل درست۔") + (T.copy ? " " + L("It copies down correctly too.", "نیچے کاپی بھی درست ہوتا ہے۔") : ""));
    });
    return d;
  }
  function same(v, e){ if (typeof e === "number") return typeof v === "number" && Math.abs(v - e) < 1e-6; return String(v).toLowerCase() === String(e).toLowerCase(); }

  /* ------------------------------------------------------------ quick check */
  function loadChecks(){
    if (CHECKS) return Promise.resolve(CHECKS);
    if (!CHK_LOADING) CHK_LOADING = fetch("/academy/checks.json?v=2", { credentials: "same-origin" }).then(function(r){ return r.ok ? r.json() : {}; }).catch(function(){ return {}; }).then(function(d){ CHECKS = d || {}; return CHECKS; });
    return CHK_LOADING;
  }
  function pairsOf(l){
    var out = [];
    (l.b || []).forEach(function(b){ if (b.k === "bullets") (b.v || []).forEach(function(x){ var at = x.indexOf(" = "); if (at > 0){ var a = x.slice(0, at).trim(), m = x.slice(at + 3).trim(); if (a && m && a.length < 60 && m.length < 90) out.push([a, m]); } }); });
    return out;
  }
  function autoQs(c, i, l){
    var p = pairsOf(l); if (p.length < 4) return [];
    var pool = p.slice();
    if (pool.length < 6) (c.lessons || []).forEach(function(o, j){ if (j !== i && o && o.b) pool = pool.concat(pairsOf(o)); });
    var picks = shuffle(p.slice()).slice(0, 3), qs = [];
    picks.forEach(function(pr, n){
      var rev = n === 1, right = rev ? pr[0] : pr[1];
      var wrong = shuffle(pool.filter(function(x){ return (rev ? x[0] : x[1]) !== right; }).map(function(x){ return rev ? x[0] : x[1]; }));
      var opts = [right], seen = {}; seen[right] = 1;
      for (var k = 0; k < wrong.length && opts.length < 4; k++) if (!seen[wrong[k]]){ seen[wrong[k]] = 1; opts.push(wrong[k]); }
      if (opts.length < 3) return;
      shuffle(opts);
      qs.push([rev ? L("Which one means “" + pr[1] + "”?", "“" + pr[1] + "” کس کا مطلب ہے؟") : L("What does “" + pr[0] + "” mean?", "“" + pr[0] + "” کا مطلب کیا ہے؟"), opts, opts.indexOf(right), pr[0] + " = " + pr[1]]);
    });
    return qs;
  }
  function checkBlock(c, i, l, art){
    var d = document.createElement("section"); d.className = "xlx"; d.id = "xcheck";
    loadChecks().then(function(all){
      var qs = (all[c.id] && all[c.id][String(i)]) || autoQs(c, i, l);
      if (!qs || !qs.length){ d.remove(); return; }
      var h = '<h3>✅ ' + both("Quick check", "فوری جانچ") + ' <span class="xmuted">' + esc(L(qs.length + " questions - answer straight away", qs.length + " سوال - فوراً جواب")) + '</span></h3>';
      qs.forEach(function(q, n){
        h += '<div class="xq" data-n="' + n + '"><p>' + (n + 1) + ". " + esc(q[0]) + "</p>";
        q[1].forEach(function(o, k){ h += '<button class="xo" data-k="' + k + '">' + esc(o) + "</button>"; });
        h += "</div>";
      });
      d.innerHTML = h + '<div class="xscore" hidden></div>';
      var got = 0, done = 0;
      d.addEventListener("click", function(e){
        var b = e.target.closest(".xo"); if (!b || b.disabled) return;
        var box = b.closest(".xq"), q = qs[+box.dataset.n], k = +b.dataset.k, os = box.querySelectorAll(".xo");
        Array.prototype.forEach.call(os, function(x){ x.disabled = true; });
        os[q[2]].classList.add("ok"); if (k !== q[2]) b.classList.add("no"); else got++;
        var w = document.createElement("div"); w.className = "xwhy"; w.textContent = (k === q[2] ? "✔ " + L("Right. ", "درست۔ ") : "✖ " + L("Not quite. ", "درست نہیں۔ ")) + (q[3] || ""); box.appendChild(w);
        if (++done === qs.length){
          var sc = d.querySelector(".xscore"); sc.hidden = false;
          var all2 = got === qs.length, tog = art && art.querySelector('[data-act="toggle"]');
          sc.innerHTML = esc(L("You got " + got + " of " + qs.length + ".", qs.length + " میں سے " + got + " درست۔")) + " " + (all2 ? "🎉 " : "")
            + (all2 && tog && !tog.classList.contains("done") ? ' <button class="xbtn" data-mark="1">' + esc(L("Mark lesson done", "سبق مکمل کریں")) + "</button>" : "")
            + (!all2 ? ' <button class="xbtn ghost" data-again="1">' + esc(L("Try again", "دوبارہ")) + "</button>" : "");
        }
      });
      d.addEventListener("click", function(e){
        if (e.target.dataset.mark){ var tog = art.querySelector('[data-act="toggle"]'); if (tog) tog.click(); }
        if (e.target.dataset.again){ var nd = checkBlock(c, i, l, art); d.parentNode.replaceChild(nd, d); }
      });
    });
    return d;
  }

  /* ------------------------------------------------------------ lesson Q&A */
  function ago(iso){
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return L("just now", "ابھی"); if (s < 3600) return Math.floor(s / 60) + L(" min ago", " منٹ پہلے");
    if (s < 86400) return Math.floor(s / 3600) + L(" h ago", " گھنٹے پہلے"); return Math.floor(s / 86400) + L(" days ago", " دن پہلے");
  }
  function qaBlock(c, i){
    var d = document.createElement("section"); d.className = "xlx xqa"; d.id = "qa";
    var lesson = String(i), state = { me: false, staff: false, qs: [] };
    d.innerHTML = '<h3>💬 ' + both("Questions about this lesson", "اس سبق کے بارے میں سوالات") + '</h3><div class="xqform"></div><div class="xqlist"><p class="xmuted">' + esc(L("Loading…", "لوڈ ہو رہا ہے…")) + "</p></div>";
    function person(p){ var n = esc(p.name); return (p.slug ? '<a href="/in/' + encodeURIComponent(p.slug) + '">' + n + "</a>" : "<b>" + n + "</b>") + (p.staff ? '<span class="xtag">' + esc(L("Team", "ٹیم")) + "</span>" : ""); }
    function item(p, q){
      var acts = "";
      if (q && (state.staff || q.mine) && !p.mine) acts += '<button class="xlink" data-help="' + p.id + '">' + (p.helpful ? "↩ " + esc(L("Not helpful", "مددگار نہیں")) : "✔ " + esc(L("Helpful", "مددگار"))) + "</button>";
      if (p.mine || state.staff) acts += '<button class="xlink" data-del="' + p.id + '">' + esc(L("Delete", "حذف")) + "</button>";
      return '<div class="xqi"><div class="xqh">' + person(p) + " · " + esc(ago(p.at)) + (p.helpful ? '<span class="xtag h">✔ ' + esc(L("Helpful", "مددگار")) + "</span>" : "") + '</div><div class="xqb">' + esc(p.body) + "</div>" + acts + "</div>";
    }
    function draw(){
      var f = d.querySelector(".xqform");
      f.innerHTML = state.me
        ? '<textarea maxlength="1000" placeholder="' + esc(L("Stuck? Ask your question here. Tutors and other learners can answer.", "کہیں اٹک گئے؟ یہاں سوال پوچھیں۔ ٹیوٹر اور دوسرے طلبہ جواب دے سکتے ہیں۔")) + '"></textarea><div class="xsbar"><button class="xbtn" data-ask="1">' + esc(L("Ask", "پوچھیں")) + '</button><span class="xmsg"></span></div>'
        : '<p class="xmuted"><a href="/login?next=' + encodeURIComponent(location.pathname + location.search) + '">' + esc(L("Sign in", "سائن ان کریں")) + "</a> " + esc(L("to ask a question or answer one.", "سوال پوچھنے یا جواب دینے کے لیے۔")) + "</p>";
      var h = "";
      if (!state.qs.length) h = '<p class="xmuted">' + esc(L("No questions yet. Be the first to ask.", "ابھی کوئی سوال نہیں۔ پہلا سوال آپ پوچھیں۔")) + "</p>";
      state.qs.forEach(function(q){
        h += '<div class="xqi" data-q="' + q.id + '">' + item(q).replace(/^<div class="xqi">|<\/div>$/g, "")
          + '<div class="xans">' + q.answers.map(function(a){ return item(a, q); }).join("") + "</div>"
          + (state.me ? '<button class="xlink" data-reply="' + q.id + '">↳ ' + esc(L("Answer", "جواب دیں")) + " (" + q.answers.length + ")</button>" : (q.answers.length ? '<span class="xmuted">' + q.answers.length + " " + esc(L("answers", "جوابات")) + "</span>" : "")) + "</div>";
      });
      d.querySelector(".xqlist").innerHTML = h;
    }
    function load(){
      api("/api/learnx/qa/?course=" + encodeURIComponent(c.id) + "&lesson=" + lesson).then(function(r){ state = { me: r.me, staff: r.staff, qs: r.questions || [] }; draw(); if (location.hash === "#qa") d.scrollIntoView(); })
        .catch(function(){ d.querySelector(".xqlist").innerHTML = '<p class="xmuted">' + esc(L("Questions could not load. Try again later.", "سوالات لوڈ نہیں ہو سکے۔")) + "</p>"; });
    }
    function post(body, parent, msgEl, btn){
      btn.disabled = true;
      api("/api/learnx/qa/", { course: c.id, lesson: lesson, body: body, parent: parent || null }).then(load).catch(function(er){ btn.disabled = false; if (msgEl){ msgEl.className = "xmsg no"; msgEl.textContent = er.message; } });
    }
    d.addEventListener("click", function(e){
      var t = e.target;
      if (t.dataset.ask){ var ta = d.querySelector(".xqform textarea"); post(ta.value.trim(), null, d.querySelector(".xqform .xmsg"), t); }
      else if (t.dataset.reply){
        var box = t.parentNode; if (box.querySelector(".xrep")) return;
        var r = document.createElement("div"); r.className = "xrep";
        r.innerHTML = '<textarea maxlength="1000" placeholder="' + esc(L("Write your answer…", "اپنا جواب لکھیں…")) + '"></textarea><div class="xsbar"><button class="xbtn">' + esc(L("Post answer", "جواب بھیجیں")) + '</button><span class="xmsg"></span></div>';
        box.appendChild(r); r.querySelector("textarea").focus();
        r.querySelector("button").addEventListener("click", function(){ post(r.querySelector("textarea").value.trim(), t.dataset.reply, r.querySelector(".xmsg"), this); });
      } else if (t.dataset.del){
        if (!window.confirm(L("Delete this post?", "یہ پوسٹ حذف کریں؟"))) return;
        api("/api/learnx/qa/" + t.dataset.del + "/delete/", {}).then(load).catch(function(){});
      } else if (t.dataset.help){ api("/api/learnx/qa/" + t.dataset.help + "/helpful/", {}).then(load).catch(function(){}); }
    });
    load();
    return d;
  }

  /* ------------------------------------------------------------ entry point */
  window.XCLX = {
    lesson: function(c, i, l, lang){
      LANG = lang || "en"; CUR = c.id + ":" + i;
      var app = document.getElementById("app"), art = app && app.querySelector("article.lesson");
      if (!art) return;
      enhanceSheets(art, c, i);
      var nav = art.querySelector(".navrow"), at = nav || null;
      var tb = taskBlock(c, i); if (tb) art.insertBefore(tb, at);
      art.insertBefore(checkBlock(c, i, l, art), at);
      art.insertBefore(qaBlock(c, i), nav ? nav.nextSibling : null);
    },
    _engine: { Sheet: Sheet, shift: shift, show: show, autoQs: autoQs, TASKS: TASKS }
  };
})();
