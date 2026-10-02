/* XpertCreation printable visiting cards: 10 original templates, front and back (QR to the digital card).
   Card: 3.5 x 2 in at 300 dpi = 1050 x 600. Draws on any canvas 2D context. */
(function(root){
  "use strict";
  var BG = false;   /* true while drawing the artwork only (no text), for the online card header */
  var W = 1050, H = 600, SANS = "Poppins, 'Segoe UI', Arial, sans-serif", SERIF = "Georgia, 'Times New Roman', serif";
  function font(ctx, w, s, fam){ ctx.font = (w || "") + " " + s + "px " + (fam || SANS); }
  function fit(ctx, text, max, size, w, fam, min){
    text = String(text || ""); min = min || 14;
    for (var s = size; s > min; s -= 1){ font(ctx, w, s, fam); if (ctx.measureText(text).width <= max) return s; }
    font(ctx, w, min, fam); return min;
  }
  function txt(ctx, text, x, y, o){
    if (!text || BG) return; o = o || {};
    fit(ctx, text, o.max || 900, o.size || 28, o.w || "", o.fam, o.min);
    ctx.fillStyle = o.c || "#111"; ctx.textAlign = o.a || "left"; ctx.textBaseline = "alphabetic"; ctx.fillText(String(text), x, y);
  }
  function rr(ctx, x, y, w, h, r){ ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function initials(d){ var n = (d.business || d.name || "X").trim().split(/\s+/); return ((n[0] || "")[0] + ((n[1] || "")[0] || "")).toUpperCase(); }
  function badge(ctx, d, x, y, r, bg, fg){
    if (BG) return;
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fillStyle = bg; ctx.fill();
    if (d.logoImg){ ctx.clip(); var s = r * 2; ctx.drawImage(d.logoImg, x - r, y - r, s, s); }
    else { font(ctx, "bold", r * 0.9); ctx.fillStyle = fg; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(initials(d), x, y + 2); }
    ctx.restore();
  }
  /* the standard layout: business in the middle, person bottom-left, address bottom-right */
  function classic(ctx, d, c, cy, yb){
    cy = cy || 330;
    txt(ctx, d.business, W / 2, cy, {a: "center", size: 60, w: "bold", c: c.title, max: 900, fam: c.fam});
    txt(ctx, d.category, W / 2, cy + 46, {a: "center", size: 32, w: "italic", c: c.sub, max: 820, fam: c.fam});
    var y = yb || 455;
    txt(ctx, d.name, 60, y, {size: 32, w: "bold", c: c.text, max: 520});
    txt(ctx, d.title, 60, y + 36, {size: 24, c: c.muted, max: 520});
    txt(ctx, d.phone, 60, y + (d.title ? 72 : 40), {size: 28, c: c.text, max: 520});
    txt(ctx, d.email, 60, y + (d.title ? 106 : 76), {size: 24, c: c.text, max: 520});
    txt(ctx, d.address, W - 60, y, {a: "right", size: 26, c: c.text, max: 440});
    txt(ctx, d.city, W - 60, y + 36, {a: "right", size: 26, c: c.text, max: 440});
    txt(ctx, d.website, W - 60, y + 76, {a: "right", size: 24, w: "bold", c: c.title, max: 440});
  }
  function petals(ctx, cx, cy, r, n, len, wid, color, rot){
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot || 0); ctx.fillStyle = color;
    for (var i = 0; i < n; i++){ ctx.save(); ctx.rotate(i * Math.PI * 2 / n); ctx.beginPath(); ctx.moveTo(0, r);
      ctx.quadraticCurveTo(wid, r + len * 0.55, 0, r + len); ctx.quadraticCurveTo(-wid, r + len * 0.55, 0, r); ctx.fill(); ctx.restore(); }
    ctx.restore();
  }
  function mandala(ctx, cx, cy, s){
    petals(ctx, cx, cy, 150 * s, 24, 120 * s, 28 * s, "#138A72", 0);
    petals(ctx, cx, cy, 120 * s, 20, 110 * s, 30 * s, "#F5A623", Math.PI / 20);
    petals(ctx, cx, cy, 80 * s, 16, 95 * s, 30 * s, "#D7263D", 0);
    ctx.beginPath(); ctx.arc(cx, cy, 90 * s, 0, Math.PI * 2); ctx.fillStyle = "#FCE3BF"; ctx.fill();
    petals(ctx, cx, cy, 30 * s, 12, 55 * s, 16 * s, "#B0283B", Math.PI / 12);
    ctx.beginPath(); ctx.arc(cx, cy, 34 * s, 0, Math.PI * 2); ctx.fillStyle = "#F5A623"; ctx.fill();
    ctx.beginPath(); ctx.arc(cx, cy, 16 * s, 0, Math.PI * 2); ctx.fillStyle = "#138A72"; ctx.fill();
  }
  function star8(ctx, x, y, r){ ctx.beginPath(); for (var i = 0; i < 16; i++){ var a = i * Math.PI / 8, rr2 = i % 2 ? r * 0.62 : r; ctx[i ? "lineTo" : "moveTo"](x + Math.cos(a) * rr2, y + Math.sin(a) * rr2); } ctx.closePath(); }
  var T = [
    {id: "mandala", name: "Mandala", back: "#B0283B", draw: function(ctx, d){
      ctx.fillStyle = "#FCE3BF"; ctx.fillRect(0, 0, W, H);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, 250); ctx.clip();
      mandala(ctx, W / 2, -20, 1.05); mandala(ctx, 120, -40, 0.62); mandala(ctx, W - 120, -40, 0.62); ctx.restore();
      classic(ctx, d, {title: "#B0283B", sub: "#B0283B", text: "#1B1B1B", muted: "#5B4636"});
    }},
    {id: "corporate", name: "Corporate blue", back: "#1B4DFF", draw: function(ctx, d){
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "#1B4DFF"; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(330, 0); ctx.lineTo(250, H); ctx.lineTo(0, H); ctx.fill();
      ctx.fillStyle = "#0B2A8A"; ctx.beginPath(); ctx.moveTo(330, 0); ctx.lineTo(352, 0); ctx.lineTo(272, H); ctx.lineTo(250, H); ctx.fill();
      badge(ctx, d, 145, 300, 92, "#fff", "#1B4DFF");
      txt(ctx, d.business, 400, 150, {size: 54, w: "bold", c: "#0B1B4D", max: 600});
      txt(ctx, d.category, 400, 196, {size: 28, c: "#1B4DFF", max: 600});
      ctx.fillStyle = "#1B4DFF"; ctx.fillRect(400, 222, 80, 5);
      txt(ctx, d.name, 400, 300, {size: 34, w: "bold", c: "#111", max: 600}); txt(ctx, d.title, 400, 338, {size: 24, c: "#555", max: 600});
      var y = 400; [d.phone, d.email, [d.address, d.city].filter(Boolean).join(", "), d.website].forEach(function(v){ if (v){ txt(ctx, v, 400, y, {size: 25, c: "#222", max: 600}); y += 40; } });
    }},
    {id: "minimal", name: "Minimal white", back: "#111111", draw: function(ctx, d){
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H); ctx.strokeStyle = "#111"; ctx.lineWidth = 3; ctx.strokeRect(36, 36, W - 72, H - 72);
      txt(ctx, (d.business || "").toUpperCase(), W / 2, 190, {a: "center", size: 50, w: "600", c: "#111", max: 880});
      txt(ctx, d.category, W / 2, 236, {a: "center", size: 26, c: "#666", max: 800});
      ctx.fillStyle = "#111"; ctx.fillRect(W / 2 - 40, 266, 80, 3);
      txt(ctx, d.name, W / 2, 340, {a: "center", size: 34, w: "bold", c: "#111", max: 800}); txt(ctx, d.title, W / 2, 378, {a: "center", size: 24, c: "#666", max: 800});
      txt(ctx, [d.phone, d.email].filter(Boolean).join("   \u00b7   "), W / 2, 450, {a: "center", size: 25, c: "#222", max: 900});
      txt(ctx, [d.address, d.city].filter(Boolean).join(", "), W / 2, 492, {a: "center", size: 24, c: "#444", max: 900});
      txt(ctx, d.website, W / 2, 530, {a: "center", size: 22, w: "bold", c: "#111", max: 900});
    }},
    {id: "gold", name: "Black and gold", back: "#111111", draw: function(ctx, d){
      ctx.fillStyle = "#0E0E0E"; ctx.fillRect(0, 0, W, H);
      var g = ctx.createLinearGradient(0, 0, W, H); g.addColorStop(0, "#F7E7A1"); g.addColorStop(.5, "#D4AF37"); g.addColorStop(1, "#A8862B");
      ctx.strokeStyle = g; ctx.lineWidth = 4; ctx.strokeRect(30, 30, W - 60, H - 60); ctx.lineWidth = 1.5; ctx.strokeRect(44, 44, W - 88, H - 88);
      classic(ctx, d, {title: "#E8C766", sub: "#CDB46A", text: "#F2EBD6", muted: "#BFB28A", fam: SERIF}, 220, 395);
    }},
    {id: "islamic", name: "Green geometric", back: "#0F5132", draw: function(ctx, d){
      ctx.fillStyle = "#0F5132"; ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = "rgba(255,255,255,.08)"; ctx.lineWidth = 2;
      for (var x = 0; x <= W + 60; x += 90) for (var y = 0; y <= H + 60; y += 90){ star8(ctx, x, y, 34); ctx.stroke(); }
      ctx.fillStyle = "#FBF6E9"; rr(ctx, 70, 130, W - 140, 400, 26); ctx.fill();
      ctx.strokeStyle = "#C9A227"; ctx.lineWidth = 3; rr(ctx, 82, 142, W - 164, 376, 20); ctx.stroke();
      txt(ctx, d.business, W / 2, 90, {a: "center", size: 50, w: "bold", c: "#F4D35E", max: 900, fam: SERIF});
      txt(ctx, d.category, W / 2, 210, {a: "center", size: 30, w: "italic", c: "#0F5132", max: 800, fam: SERIF});
      txt(ctx, d.name, W / 2, 290, {a: "center", size: 36, w: "bold", c: "#13301F", max: 800}); txt(ctx, d.title, W / 2, 328, {a: "center", size: 24, c: "#4B5E52", max: 800});
      txt(ctx, [d.phone, d.email].filter(Boolean).join("   \u00b7   "), W / 2, 400, {a: "center", size: 25, c: "#13301F", max: 860});
      txt(ctx, [d.address, d.city].filter(Boolean).join(", "), W / 2, 442, {a: "center", size: 24, c: "#13301F", max: 860});
      txt(ctx, d.website, W / 2, 482, {a: "center", size: 23, w: "bold", c: "#0F5132", max: 860});
    }},
    {id: "gradient", name: "Modern gradient", back: "#5B2BD9", draw: function(ctx, d){
      var g = ctx.createLinearGradient(0, 0, W, H); g.addColorStop(0, "#1B4DFF"); g.addColorStop(1, "#8E2DE2"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "rgba(255,255,255,.10)"; ctx.beginPath(); ctx.arc(W - 80, 60, 230, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.arc(80, H + 40, 180, 0, Math.PI * 2); ctx.fill();
      badge(ctx, d, 120, 120, 62, "#fff", "#5B2BD9");
      txt(ctx, d.business, 210, 115, {size: 46, w: "bold", c: "#fff", max: 760}); txt(ctx, d.category, 210, 155, {size: 26, c: "#E3DBFF", max: 760});
      txt(ctx, d.name, 60, 330, {size: 44, w: "bold", c: "#fff", max: 900}); txt(ctx, d.title, 60, 372, {size: 26, c: "#E3DBFF", max: 900});
      var y = 450; [d.phone, d.email].forEach(function(v){ if (v){ txt(ctx, v, 60, y, {size: 26, c: "#fff", max: 480}); y += 40; } });
      y = 450; [[d.address, d.city].filter(Boolean).join(", "), d.website].forEach(function(v){ if (v){ txt(ctx, v, W - 60, y, {a: "right", size: 25, c: "#fff", max: 440}); y += 40; } });
    }},
    {id: "medical", name: "Clinic / medical", back: "#0E7C86", draw: function(ctx, d){
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H); ctx.fillStyle = "#0E7C86"; ctx.fillRect(0, 0, W, 22); ctx.fillRect(0, H - 22, W, 22);
      ctx.fillStyle = "#E6F6F7"; ctx.beginPath(); ctx.arc(W - 150, 170, 105, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#0E7C86"; ctx.fillRect(W - 172, 110, 44, 120); ctx.fillRect(W - 210, 148, 120, 44);
      txt(ctx, d.business, 60, 140, {size: 52, w: "bold", c: "#0B3B40", max: 700}); txt(ctx, d.category, 60, 186, {size: 28, c: "#0E7C86", max: 700});
      txt(ctx, d.name, 60, 300, {size: 36, w: "bold", c: "#111", max: 700}); txt(ctx, d.title, 60, 338, {size: 24, c: "#555", max: 700});
      var y = 410; [d.phone, d.email, [d.address, d.city].filter(Boolean).join(", "), d.website].forEach(function(v){ if (v){ txt(ctx, v, 60, y, {size: 25, c: "#222", max: 930}); y += 38; } });
    }},
    {id: "shop", name: "Shop / store", back: "#1E7B34", draw: function(ctx, d){
      ctx.fillStyle = "#FFFBEA"; ctx.fillRect(0, 0, W, H);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, 170); ctx.clip(); ctx.fillStyle = "#1E7B34"; ctx.fillRect(0, 0, W, 170);
      ctx.fillStyle = "#28A745"; for (var x = -200; x < W + 200; x += 70){ ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + 35, 0); ctx.lineTo(x - 135, 170); ctx.lineTo(x - 170, 170); ctx.fill(); } ctx.restore();
      ctx.fillStyle = "#F4C430"; for (var i = 0; i < 15; i++){ ctx.beginPath(); ctx.arc(35 + i * 70, 170, 35, 0, Math.PI); ctx.fill(); }
      txt(ctx, d.business, W / 2, 110, {a: "center", size: 60, w: "bold", c: "#fff", max: 900});
      txt(ctx, d.category, W / 2, 275, {a: "center", size: 32, w: "italic", c: "#1E7B34", max: 860});
      classic(ctx, Object.assign({}, d, {business: "", category: ""}), {title: "#1E7B34", sub: "#1E7B34", text: "#1B1B1B", muted: "#555"});
    }},
    {id: "tech", name: "Tech dark blue", back: "#0B1220", draw: function(ctx, d){
      ctx.fillStyle = "#0B1220"; ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = "rgba(30,160,255,.35)"; ctx.lineWidth = 2;
      [[700, 40, 900, 40, 950, 90], [760, 120, 980, 120], [650, 560, 860, 560, 900, 520], [40, 560, 200, 560]].forEach(function(p){ ctx.beginPath(); ctx.moveTo(p[0], p[1]); for (var i = 2; i < p.length; i += 2) ctx.lineTo(p[i], p[i + 1]); ctx.stroke(); ctx.fillStyle = "#1EA0FF"; ctx.beginPath(); ctx.arc(p[p.length - 2], p[p.length - 1], 6, 0, Math.PI * 2); ctx.fill(); });
      ctx.fillStyle = "rgba(30,160,255,.5)"; [[960, 200, 14], [990, 230, 10], [930, 240, 18], [985, 270, 12]].forEach(function(q){ ctx.fillRect(q[0], q[1], q[2], q[2]); });
      txt(ctx, d.business, 60, 150, {size: 58, w: "bold", c: "#1EA0FF", max: 820}); txt(ctx, d.category, 60, 196, {size: 28, c: "#9FB3C8", max: 820});
      txt(ctx, d.name, 60, 310, {size: 38, w: "bold", c: "#fff", max: 820}); txt(ctx, d.title, 60, 350, {size: 25, c: "#9FB3C8", max: 820});
      var y = 420; [d.phone, d.email, [d.address, d.city].filter(Boolean).join(", "), d.website].forEach(function(v){ if (v){ txt(ctx, v, 60, y, {size: 25, c: "#E5EDF5", max: 900}); y += 38; } });
    }},
    {id: "maroon", name: "Elegant maroon", back: "#6B1D2A", draw: function(ctx, d){
      ctx.fillStyle = "#6B1D2A"; ctx.fillRect(0, 0, W, H); ctx.fillStyle = "#FBF3E4"; rr(ctx, 40, 40, W - 80, H - 80, 22); ctx.fill();
      ctx.strokeStyle = "#B08D57"; ctx.lineWidth = 2; rr(ctx, 56, 56, W - 112, H - 112, 16); ctx.stroke();
      [[56, 56], [W - 56, 56], [56, H - 56], [W - 56, H - 56]].forEach(function(p){ ctx.fillStyle = "#6B1D2A"; star8(ctx, p[0], p[1], 20); ctx.fill(); });
      classic(ctx, d, {title: "#6B1D2A", sub: "#8A5A3C", text: "#2A1A12", muted: "#6E5A4C", fam: SERIF}, 210, 385);
    }}
  ];
  function back(ctx, tpl, d, qr){
    ctx.fillStyle = tpl.back; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#fff"; rr(ctx, 60, 60, 480, 480, 28); ctx.fill();
    if (qr){ var n = qr.getModuleCount(), cell = Math.floor(400 / n), off = 60 + (480 - cell * n) / 2; ctx.fillStyle = "#111";
      for (var r = 0; r < n; r++) for (var c = 0; c < n; c++) if (qr.isDark(r, c)) ctx.fillRect(off + c * cell, off + r * cell, cell, cell); }
    var light = /^#(?:F|E|D)/i.test(tpl.back);
    var fg = light ? "#111" : "#fff", sub = light ? "#444" : "rgba(255,255,255,.85)";
    txt(ctx, d.business, 600, 230, {size: 46, w: "bold", c: fg, max: 400});
    txt(ctx, d.qrUrl ? "Scan to save my contact" : "Add your card link", 600, 290, {size: 26, c: sub, max: 400});
    txt(ctx, d.qrLabel || "", 600, 335, {size: 22, w: "bold", c: fg, max: 400});
    txt(ctx, d.website || "", 600, 470, {size: 24, c: sub, max: 400});
  }
  root.XCPrint = {W: W, H: H, TEMPLATES: T,
                  art: function(ctx, id){ var t = T.filter(function(x){ return x.id === id; })[0] || T[0]; BG = true; ctx.save(); try { t.draw(ctx, {}); } finally { ctx.restore(); BG = false; } }, front: function(ctx, id, d){ var t = T.filter(function(x){ return x.id === id; })[0] || T[0]; ctx.save(); t.draw(ctx, d); ctx.restore(); },
                  back: function(ctx, id, d, qr){ var t = T.filter(function(x){ return x.id === id; })[0] || T[0]; ctx.save(); back(ctx, t, d, qr); ctx.restore(); }};
})(typeof window !== "undefined" ? window : globalThis);
