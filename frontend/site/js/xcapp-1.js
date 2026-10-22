/* XpertCreation on phones: (1) "Related" buttons under each section, (2) an app look on phones -
   a bottom tab bar, the long footer folded away, content edge to edge. Loaded on every page by topnav-1.js. */
(function(){
  "use strict";
  if (window.XCAPP) return;
  window.XCAPP = 1;
  var D = document, path = location.pathname.replace(/\/+$/, "") || "/", T = (location.search.match(/[?&]t=([a-z0-9-]+)/) || [])[1] || "";

  /* ------------------------------------------------------------------ related */
  var L = {
    quran: ["Quran", "/quran", "📖"], islamic: ["Islamic", "/islamic", "🕌"], prayer: ["Prayer times", "/tools?t=prayer", "🕌"],
    qibla: ["Qibla", "/tools?t=qibla", "🧭"], zakat: ["Zakat", "/tools?t=zakat", "🤲"], faraid: ["Faraid", "/tools/faraid-calculator/", "⚖️"],
    hijri: ["Hijri date", "/tools?t=hijri", "🌙"], tasbeeh: ["Tasbeeh", "/tools?t=tasbeeh", "📿"], rishta: ["Halal Rishta", "/rishta", "💍"],
    legal: ["Legal documents", "/legal-documents/", "📜"], property: ["Property", "/market#property", "🏠"], roots: ["Family tree", "/roots", "🌳"],
    brief: ["My Briefcase", "/briefcase", "💼"], scan: ["XpertScan", "/scan", "📄"], money: ["Money", "/money", "💰"],
    tax: ["Tax (FBR)", "/tools?t=fbrtax", "🇵🇰"], bills: ["Bills", "/bills", "🧾"], emi: ["Loan / EMI", "/tools?t=emi", "🏦"],
    salary: ["Salary", "/tools?t=salary", "💼"], gold: ["Gold price", "/tools?t=gold", "🪙"], rates: ["Currency rates", "/rates", "💱"],
    invoice: ["Invoice", "/tools?t=invoice", "🧾"], bijli: ["Electricity bill", "/tools?t=bijli", "⚡"], jobs: ["Jobs", "/jobs", "💼"],
    cv: ["My CV", "/market#cv", "📄"], freelance: ["Freelance", "/market", "🧑‍💻"], promote: ["Promote", "/promote", "📣"],
    pros: ["XpertPros", "/pros", "🛠️"], store: ["Store", "/store", "🛍️"], bizstk: ["Business stickers", "/business-stickers", "🏢"],
    brand: ["Brand kit", "/brand", "🎨"], coreg: ["Company register", "/company-register", "🏢"], biz: ["Staff & stock", "/business", "📦"],
    food: ["Food delivery", "/food", "🍔"], orders: ["My orders", "/orders", "📦"], recipes: ["Recipes", "/recipes", "🍲"],
    board: ["Gov jobs", "/board", "🏛️"], academy: ["Academy", "/academy/", "🎓"], typing: ["Typing tutor", "/typing", "⌨️"],
    feed: ["XpertConnect", "/feed", "🤝"], mcq: ["MCQs", "/mcq", "✅"], vocab: ["Vocabulary", "/vocabulary", "🔤"],
    library: ["Library", "/library", "📚"], gpa: ["GPA", "/tools?t=gpa", "🎓"], translate: ["Translate", "/translate", "🌐"],
    exam: ["Exam planner", "/tools?t=examplan", "📅"], flash: ["Flashcards", "/tools?t=flashcards", "🗂️"], urdukb: ["Urdu keyboard", "/tools?t=urdukb", "ا"],
    voice: ["Voice typing", "/tools?t=voicetype", "🎙️"], norway: ["Learn Norwegian", "/norwegian", "🇳🇴"], meetups: ["Meetups", "/meetups", "👥"],
    verify: ["Get verified", "/get-verified", "✅"], birthdays: ["Birthdays", "/birthdays", "🎂"], steps: ["Step counter", "/steps", "🚶"],
    travel: ["Travel", "/travel", "✈️"], bus: ["Bus terminals", "/bus", "🚌"], weather: ["Weather", "/weather", "🌤️"],
    rides: ["Rides", "/rides", "🚗"], air: ["Airports", "/air", "🛫"], news: ["News", "/news", "📰"], sports: ["Sports", "/sports", "🏏"],
    shows: ["Shows", "/shows", "🎬"], predict: ["Predict", "/predict", "🎯"], games: ["Games", "/games", "🎮"], rewards: ["Rewards", "/rewards", "🎁"],
    kids: ["Kids", "/kids", "🧸"], poetry: ["Poetry", "/poetry", "📜"], afsanay: ["Afsanay", "/afsanay", "📖"], clips: ["Clips", "/clips", "🎬"],
    pets: ["My pets", "/pets", "🐾"], vets: ["Vets", "/vets", "🩺"], lost: ["Lost & found", "/lost", "🔎"], adopt: ["Adopt a pet", "/adopt", "🐶"],
    blood: ["Blood bank", "/blood", "🩸"], donate: ["Donate", "/donate", "🤲"], bmi: ["BMI", "/tools?t=bmi", "⚖️"], water: ["Water to drink", "/tools?t=water", "💧"],
    idealwt: ["Ideal weight", "/tools?t=idealwt", "🏃"], wheels: ["Cars & bikes", "/wheels", "🚘"], groups: ["Groups", "/groups", "👥"],
    rooms: ["Chat rooms", "/chat-rooms", "💬"], people: ["Find people", "/people", "🔍"], cards: ["Digital card", "/cards", "🎯"],
    events: ["Events", "/events", "📅"], qr: ["QR code", "/tools?t=qr", "▦"], amb: ["Ambassadors", "/ambassadors", "🌟"], cam: ["XpertCam", "/cam", "📸"],
    meet: ["XpertMeet", "/call?new=1", "🎥"], vt: ["Urdu voice typing", "/urdu-voice-typing", "🎙️"], live: ["Go Live", "/live", "🔴"], chat: ["XpertChat", "/chat", "💬"], tools: ["All tools", "/tools", "🧰"]
  };
  var MAP = [
    ["/islamic", "quran prayer qibla zakat faraid hijri tasbeeh rishta"], ["/quran", "islamic prayer qibla tasbeeh hijri"],
    ["/tools/faraid-calculator", "legal property zakat islamic roots brief"], ["/legal-documents", "faraid property brief scan money pros"],
    ["/market", "legal jobs cv promote pros store bizstk"], ["/money", "tax zakat bills emi salary gold rates invoice brief"],
    ["/bills", "money bijli tax rates"], ["/rates", "money gold rates travel"], ["/store", "bizstk promote brand coreg biz invoice food orders"],
    ["/orders", "store food money"], ["/food", "store recipes rides orders"], ["/recipes", "food store kids"],
    ["/jobs", "freelance cv board academy typing feed brief"], ["/board", "jobs mcq academy brief"],
    ["/academy", "mcq vocab typing library gpa translate jobs"], ["/courses", "mcq vocab typing library gpa jobs"],
    ["/mcq", "academy vocab board exam"], ["/vocabulary", "translate academy mcq flash"], ["/translate", "vt vocab urdukb norway"], ["/urdu-voice-typing", "translate urdukb poetry vocab chat"],
    ["/norwegian", "translate vocab academy"], ["/rishta", "islamic roots meetups verify brief"], ["/roots", "faraid birthdays rishta islamic"],
    ["/rides", "steps travel bus weather food"], ["/travel", "air bus weather rides rates brief"], ["/air", "travel weather rates brief"],
    ["/bus", "travel rides weather"], ["/weather", "prayer travel news"], ["/news", "sports weather shows rates"],
    ["/sports", "predict news games"], ["/predict", "sports games rewards"], ["/shows", "kids poetry afsanay library clips"],
    ["/kids", "shows games typing quran library"], ["/poetry", "vt afsanay library shows"], ["/afsanay", "poetry library shows"],
    ["/library", "academy afsanay poetry"], ["/games", "predict sports kids"], ["/pets", "vets lost adopt"], ["/pet", "vets lost adopt"],
    ["/vets", "pets lost adopt"], ["/lost", "pets vets adopt"], ["/adopt", "pets vets lost"], ["/blood", "donate steps weather"],
    ["/donate", "blood zakat islamic"], ["/steps", "bmi water idealwt rides"], ["/pros", "store freelance rides verify"],
    ["/wheels", "rides property legal emi"], ["/feed", "live groups meetups rooms promote people"], ["/live", "feed groups meetups meet"], ["/people", "feed cards verify cv"],
    ["/in", "feed cards verify cv"], ["/meetups", "groups events rooms"], ["/events", "meetups groups birthdays"],
    ["/birthdays", "events roots"], ["/cards", "brand people qr bizstk"], ["/card", "brand people qr bizstk"], ["/brand", "bizstk cards store"],
    ["/company", "bizstk brand store promote jobs"], ["/company-register", "store bizstk brand verify"], ["/promote", "rewards store amb"],
    ["/rewards", "promote predict amb"], ["/ambassadors", "rewards promote verify"], ["/briefcase", "scan legal jobs verify"],
    ["/business-stickers", "store brand cards chat"], ["/business", "store invoice bizstk money"], ["/typing", "academy jobs kids"],
    ["/clips", "cam live shows feed"], ["/get-verified", "brief scan feed"], ["/safety", "verify brief"]
  ];
  var TOOLMAP = {zakat: "islamic faraid money", fbrtax: "money salary bills", salary: "tax money jobs", prayer: "islamic qibla quran", qibla: "islamic prayer quran",
    bmi: "steps water idealwt", emi: "money wheels property", gold: "money rates zakat", invoice: "store money biz", bijli: "bills money", gpa: "academy mcq exam",
    hijri: "islamic prayer quran", tasbeeh: "islamic quran prayer", qr: "cards brand store", voicetype: "vt translate urdukb", urdukb: "vt translate vocab"};
  var GAMES = /^\/(2048|chess|carrom|carrom-online|connect4|ludo|minesweeper|pool|simon|snake|sudoku|tictactoe|wordgame|arrows)$/;
  var SKIP = /^\/(chat|group|groups|nearby|offline|call|cam|scan|irc|login|signup|register|account\/delete|delete-account|tools)(\/|$)/;

  function relatedKeys(){
    if (path === "/tools" && T && TOOLMAP[T]) return TOOLMAP[T];
    if (GAMES.test(path)) return "games kids predict";
    if (SKIP.test(path) || path === "/") return "";
    var best = "", len = 0;
    MAP.forEach(function(m){ if ((path === m[0] || path.indexOf(m[0] + "/") === 0) && m[0].length > len){ best = m[1]; len = m[0].length; } });
    return best;
  }
  function same(u){ var p = u.split("#")[0], b = p.split("?")[0].replace(/\/+$/, "") || "/", t = (p.match(/[?&]t=([a-z0-9-]+)/) || [])[1] || ""; return b === path && t === T; }
  function addRelated(){
    var keys = relatedKeys(); if (!keys || D.querySelector(".xcrel")) return;
    var items = keys.split(" ").map(function(k){ return L[k]; }).filter(function(x){ return x && !same(x[1]); });
    if (!items.length) return;
    var box = D.createElement("nav"); box.className = "xcrel"; box.setAttribute("aria-label", "Related");
    box.innerHTML = '<div class="xcrel-h"><b>Related</b><span>متعلقہ</span></div><div class="xcrel-g">'
      + items.map(function(x){ return '<a href="' + x[1] + '"><i>' + x[2] + "</i><span>" + x[0] + "</span></a>"; }).join("") + "</div>";
    var foot = D.querySelector(".xcfoot");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(box, foot); else D.body.appendChild(box);
  }

  /* ------------------------------------------------------------------ app look on phones */
  var TABS = [["Home", "/", "M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"], ["Connect", "/feed", "M16 11a4 4 0 1 0-8 0M3 20c1.5-3.5 5-5 9-5s7.5 1.5 9 5M12 3v4"],
    ["Chat", "/chat", "M4 5h16v11H8l-4 4z"], ["Tools", "/tools", "M14 7l3-3 3 3-3 3M4 20l9-9M5 5h4v4H5zM15 15h4v4h-4z"], ["Menu", "#menu", "M4 7h16M4 12h16M4 17h16"]];
  var NOBAR = /^\/(chat|group|groups|nearby|offline|call|cam|scan|irc|2048|chess|carrom|carrom-online|connect4|ludo|minesweeper|pool|simon|snake|sudoku|tictactoe|wordgame|arrows|login|signup)(\/|$)/;
  function phone(){ return Math.min(window.innerWidth, screen.width || 9999) <= 760; }
  function hasOwnBar(){
    var h = window.innerHeight, w = window.innerWidth, all = D.body.getElementsByTagName("*");
    for (var i = 0; i < all.length && i < 4000; i++){
      var el = all[i]; if (el.closest(".xctab")) continue;
      var cs = getComputedStyle(el); if (cs.position !== "fixed" || cs.display === "none" || cs.visibility === "hidden") continue;
      var r = el.getBoundingClientRect();
      if (r.bottom >= h - 4 && r.height > 30 && r.height < 140 && r.width > w * 0.6) return true;
    }
    return false;
  }
  function on(u){ var b = u.replace(/\/+$/, "") || "/"; if (b === "/") return path === "/"; if (b === "/feed") return path === "/feed" || path.indexOf("/post/") === 0 || path === "/people" || path.indexOf("/in/") === 0; return path === b || path.indexOf(b + "/") === 0; }
  function addAppLook(){
    if (!phone()) return;
    D.documentElement.classList.add("xc-m");
    var foot = D.querySelector(".xcfoot");
    if (foot && !foot.querySelector(".xcf-more")){
      var btn = D.createElement("button"); btn.type = "button"; btn.className = "xcf-more"; btn.innerHTML = "About XpertCreation, help and policies <span>▾</span>";
      btn.onclick = function(){ foot.classList.toggle("xcf-open"); };
      foot.insertBefore(btn, foot.firstChild);
    }
    if (NOBAR.test(path) || hasOwnBar() || D.querySelector(".xctab")) return;
    var bar = D.createElement("nav"); bar.className = "xctab"; bar.setAttribute("aria-label", "Main");
    bar.innerHTML = TABS.map(function(t){ return '<a href="' + t[1] + '"' + (t[1] !== "#menu" && on(t[1]) ? ' class="on"' : "") + (t[1] === "#menu" ? ' data-xcmenu="1"' : "") + '><svg viewBox="0 0 24 24"><path d="' + t[2] + '"/></svg><span>' + t[0] + "</span></a>"; }).join("");
    D.body.appendChild(bar); D.documentElement.classList.add("xc-tabbed");
    bar.querySelector("[data-xcmenu]").addEventListener("click", function(e){
      e.preventDefault();
      var m = D.querySelector(".tmenu"); if (m && getComputedStyle(m).display !== "none"){ m.click(); window.scrollTo({top: 0, behavior: "smooth"}); return; }
      location.href = "/tools";
    });
  }

  var css = D.createElement("style");
  css.textContent = [
    ".xcrel{max-width:1060px;margin:26px auto 6px;padding:0 16px;box-sizing:border-box;font-family:inherit}",
    ".xcrel-h{display:flex;align-items:baseline;gap:10px;margin-bottom:10px}.xcrel-h b{font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#5A657C}",
    ".xcrel-h span{font-family:'Noto Nastaliq Urdu','Jameel Noori Nastaleeq',serif;font-size:13px;color:#8A93A6}",
    ".xcrel-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:8px}",
    ".xcrel-g a{display:flex;align-items:center;gap:9px;padding:11px 12px;background:#fff;border:1px solid #E4E8F2;border-radius:14px;text-decoration:none;color:#0D1424;font-size:13.5px;font-weight:700;line-height:1.2;min-height:46px;box-sizing:border-box}",
    ".xcrel-g a:hover{border-color:#1B4DFF;color:#1B4DFF}.xcrel-g a i{font-style:normal;font-size:20px;flex:0 0 auto}",
    "@media(max-width:760px){.xcrel-g{display:flex;overflow-x:auto;scrollbar-width:none;padding-bottom:4px;margin:0 -16px;padding-left:16px;padding-right:16px}.xcrel-g::-webkit-scrollbar{display:none}.xcrel-g a{flex:0 0 auto}}",
    ".xctab{position:fixed;left:0;right:0;bottom:0;z-index:8990;display:flex;background:rgba(255,255,255,.97);backdrop-filter:blur(12px);border-top:1px solid #E4E8F2;padding:4px 4px calc(4px + env(safe-area-inset-bottom));font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}",
    ".xctab a{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 0 4px;text-decoration:none;color:#5A657C;font-size:11px;font-weight:700;border-radius:12px;-webkit-tap-highlight-color:transparent}",
    ".xctab a svg{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}",
    ".xctab a.on{color:#1B4DFF}.xctab a.on svg{stroke-width:2.3}.xctab a:active{background:#F1F4FA}",
    "html.xc-tabbed body{padding-bottom:calc(68px + env(safe-area-inset-bottom)) !important}",
    "html.xc-tabbed .xcb{bottom:calc(80px + env(safe-area-inset-bottom)) !important}",
    "html.xc-m .xcfoot{margin-top:18px;padding:14px 16px 18px}",
    "html.xc-m .xcfoot .xf-grid{display:none}html.xc-m .xcfoot.xcf-open .xf-grid{display:grid}",
    ".xcf-more{display:none}html.xc-m .xcf-more{display:flex;justify-content:space-between;width:100%;border:1px solid #E4E8F2;background:#fff;border-radius:12px;padding:11px 14px;font:inherit;font-size:13.5px;font-weight:700;color:#0D1424;margin-bottom:12px;cursor:pointer}",
    "html.xc-m .xcfoot.xcf-open .xcf-more span{transform:rotate(180deg)}",
    "html.xc-m{-webkit-text-size-adjust:100%}html.xc-m body{overscroll-behavior-y:contain}",
    "@media (display-mode: standalone){html.xc-m header.top,html.xc-m header.topbar{padding-top:env(safe-area-inset-top)}}"
  ].join("\n");
  (D.head || D.documentElement).appendChild(css);

  function go(){ try { addRelated(); } catch (e) {} setTimeout(function(){ try { addAppLook(); } catch (e) {} }, 400); }
  if (D.readyState === "loading") D.addEventListener("DOMContentLoaded", go); else go();
})();
