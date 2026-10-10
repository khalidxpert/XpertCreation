/* XpertCreation Help search: type a question ("job kaisay post karoon", "how to sell my skill") and get the steps at once.
   Works in English and Roman Urdu. Renders into any element with id="xchelp". */
(function(){
  if (window.XCHELP) return; window.XCHELP = 1;
  var A = [
    // ---------- account
    {t: "Create an account", k: "register sign up signup new account banana join khata", s: ["Open xpertcreation.com/register.", "Enter your name, email and a password. Pick Individual (or Company for a business).", "We email you a 6-digit code. Type it in to confirm your email.", "Done. One account works for every part of XpertCreation."], l: "/register", b: "Create account"},
    {t: "Forgot my password", k: "forgot password reset bhool gaya bhool gayi login nahi ho raha sign in problem", s: ["Open the sign-in page.", "Tap Forgot password and enter your email.", "Type the 6-digit code from the email and choose a new password."], l: "/login", b: "Open sign in"},
    {t: "Forgot my username", k: "forgot username user name bhool", s: ["Open the sign-in page and tap Forgot username.", "Enter your email. We email your username to you."], l: "/login", b: "Open sign in"},
    {t: "Change my name, username or photo", k: "change name username profile picture photo avatar dp tasveer naam badalna", s: ["Tap your picture at the top, then Account.", "Choose a picture (square, up to 2 MB) or build an avatar.", "Change the display name or username and tap Save. A username can change once a day."], l: "/account", b: "Open my account"},
    {t: "Add my phone / WhatsApp number", k: "phone number whatsapp mobile number add karna contact", s: ["Open Account.", "Find Phone / WhatsApp number and type it (03001234567 or +923001234567).", "Tap Save number. It is not shown on your public profile."], l: "/account", b: "Open my account"},
    {t: "Delete my account", k: "delete account remove account khatam band karna", s: ["Open Account and scroll down to Delete my account.", "Read what gets deleted, then confirm. This cannot be undone."], l: "/account/delete", b: "Delete account"},
    {t: "Turn on notifications on my phone", k: "notification push alert android phone bell turn on", s: ["Open the home page on your phone (or the Play Store app).", "Tap Turn on notifications on the card, then Allow.", "You will get offers, connection requests and orders even when the app is closed."], l: "/", b: "Open home"},
    {t: "Pin my favourite pages (up to 3)", k: "pin favourite shortcut quick link bookmark top", s: ["Open the tool or section you use most (Money, Freelance, a tool...).", "Tap the 📌 pin button at the top.", "It shows first in the menu and as a big card on the home page. With 3 pins, choose one to replace."], l: "/tools", b: "Open tools"},
    {t: "Change language or settings", k: "language urdu english settings preferences zaban", s: ["Open Preferences from your account menu.", "Pick your language and other settings, then save."], l: "/me/preferences", b: "Open preferences"},
    // ---------- profile, connect
    {t: "Make my professional profile", k: "profile cv headline skills experience education xpertconnect banana", s: ["Open My profile.", "Add a headline, where you live, a few lines about you, skills, jobs and education.", "Choose who can see it: Everyone and Google, signed-in members, or only me. Tap Save."], l: "/me/profile", b: "Open my profile"},
    {t: "Get the blue tick", k: "blue tick verified verify badge tasdeeq kyc cnic", s: ["Create your XpertConnect profile first.", "Open Get verified and upload your CNIC (front and back) and an address proof, plus your WhatsApp number.", "Tap Send for review. The team checks it and you get a notification."], l: "/get-verified", b: "Get verified"},
    {t: "Connect with someone", k: "connect friend request add friend dost follow message", s: ["Open Connect and search by name, skill or city.", "Open their profile and tap Connect. They get a notification.", "Once they accept, a Message button appears and you can chat."], l: "/people", b: "Open Connect"},
    {t: "Find friends from my phone contacts", k: "contacts phone book friends find people you know suggestion facebook", s: ["Open Connect, then Find people you know.", "Tap Pick from my phone contacts (Android) or type emails and numbers.", "You see which of them are on XpertCreation. The list is not kept."], l: "/people", b: "Find people"},
    {t: "Post on XpertConnect", k: "post status share feed update wall likhna", s: ["Open XpertConnect.", "Write in the box at the top, add a picture if you like, and choose who can see it.", "Tap Post."], l: "/feed", b: "Open XpertConnect"},
    {t: "Create a group or channel", k: "group channel community banana announcement", s: ["Open Groups.", "Create a Group (everyone talks) or an Announcement channel (only admins post).", "Share the link to invite people."], l: "/groups", b: "Open groups"},
    {t: "Invite friends and earn (referral link)", k: "referral invite link earn rewards affiliate dawat", s: ["Open Rewards.", "Choose a username first if asked.", "Copy your invite link or share it on WhatsApp. People who join with it count for you."], l: "/rewards", b: "Open rewards"},
    {t: "Spin the wheel and withdraw rewards", k: "spin wheel rewards prize withdraw easypaisa jazzcash inaam", s: ["Open Rewards and tap Spin.", "Prizes go to your rewards balance.", "Before the first withdrawal, finish the steps shown (post on your wall, follow our channels), then tap Request withdrawal."], l: "/rewards", b: "Open rewards"},
    // ---------- jobs
    {t: "Post a job", k: "job post naukri nokri vacancy hire hiring staff employee job dalna lagani", s: ["You need a verified business account: create your company page and get it verified under My company.", "Open Jobs and tap + Post a job.", "Fill in the title, type, location, salary (optional), skills and description, then tap Post job. Posting is free."], l: "/jobs/new", b: "Post a job", tip: "Jobs that ask applicants for money are removed."},
    {t: "Apply for a job", k: "apply job naukri apply karna cv send", s: ["Open Jobs and search by title, company or city.", "Open the job and check your profile with Check it first.", "Add a short note (optional) and tap Apply. See replies under My applications."], l: "/jobs", b: "Find jobs"},
    {t: "Create and verify my company page", k: "company page business verify kyc ntn registration certificate karobar", s: ["Open My company and tap Create page.", "Step 1: verify your website (upload our small file to your site and tap Check now).", "Step 2: KYC — upload the registration certificate or NTN, then Send for review."], l: "/company/manage", b: "My company"},
    // ---------- freelance
    {t: "Sell my skill (create a service / gig)", k: "gig service sell skill freelance seller kaam bechna freelancing banana", s: ["Get your ID verified first (Get verified). Selling needs it.", "Open Freelance, then Selling, and tap + New service.", "Add a title, category, description, price and delivery days; add Basic / Standard / Premium packages if you like.", "Add up to 3 pictures (1200 × 800 works best) and publish."], l: "/market#sell", b: "Start selling"},
    {t: "Hire someone / buy a service", k: "hire freelancer buy service order designer website banwana logo", s: ["Open Freelance and explore services, or search.", "Pick a package and tap Order. You pay XpertCreation, not the seller.", "The seller is paid only when you accept the work."], l: "/market#gigs", b: "Explore services"},
    {t: "Ask for a custom offer", k: "custom offer quote price request special milestone", s: ["Open the service and tap Ask for a custom offer, or post a request under Offers.", "The seller sends an offer (valid 7 days); big jobs can be split into milestones.", "Accept the offer to order it."], l: "/market#offers", b: "Open offers"},
    {t: "Post a project for freelancers to bid", k: "project bid post requirement kaam dena", s: ["Open Freelance and tap + Post a project.", "Describe the work, budget and deadline.", "Freelancers send bids; pick one to start."], l: "/market#newproject", b: "Post a project"},
    {t: "Deliver, accept or cancel an order", k: "order deliver accept cancel late deadline revision file upload", s: ["Open Freelance, then My orders, and open the order.", "Seller: upload files and tap Deliver. Buyer: Accept, or ask for a revision.", "To cancel, send a cancel request; the other side agrees or declines (auto-agreed after 3 days). Late orders can be cancelled by the buyer 48 hours after the due time."], l: "/market#orders", b: "My orders"},
    {t: "Withdraw my freelance earnings", k: "withdraw earnings payout easypaisa jazzcash bank paisay nikalna", s: ["Open Freelance, then Earnings.", "Choose EasyPaisa, JazzCash or bank and the amount.", "The team pays it by hand and you get a notification."], l: "/market#wallet", b: "Earnings"},
    {t: "Make my CV", k: "cv resume biodata pdf banana", s: ["Open Freelance, then My CV.", "Fill in your details and pick a template.", "Print or save as PDF. Tick Show my CV to show it on your seller page."], l: "/market#cv", b: "My CV"},
    // ---------- property
    {t: "Post a property (house, plot, shop)", k: "property house plot shop rent sale makan ghar zameen kiraya dalna", s: ["Open Freelance & Property, then Property.", "Tap + Post property and fill in sale or rent, city, price, size and pictures.", "Buyers contact you directly. Dealers and agents need KYC."], l: "/market#editprop-new", b: "Post a property"},
    {t: "Find a house or plot", k: "find property buy rent house plot makan kiraye", s: ["Open Property.", "Filter by city, sale or rent and price.", "Open a listing and contact the owner directly."], l: "/market#property", b: "Open property"},
    // ---------- store
    {t: "Open my shop on the Store", k: "shop store merchant sell products dukaan kholna online business", s: ["Complete your profile and get your ID verified (KYC).", "Open the Store and tap Sell on XpertCreation, then Open your shop.", "The team approves your shop; then tap + Add a product."], l: "/store#seller", b: "Open my shop"},
    {t: "Add a product to my shop", k: "add product item listing picture price stock", s: ["Open the Store, then Seller center.", "Tap + Add a product: title, price, stock, pictures and category.", "Set a reorder level to get a low-stock alert."], l: "/store#editp-new", b: "Add a product"},
    {t: "Buy from the Store", k: "buy order cart checkout cash on delivery cod khareedna", s: ["Find the product and tap Add to cart or Buy now.", "Open the cart, fill in your name, phone and address.", "Choose Cash on delivery (or online) and tap Place order. Track it under My orders."], l: "/store", b: "Open the Store"},
    {t: "Ask for a wholesale (B2B) price", k: "wholesale b2b bulk quote quantity", s: ["Open the product and tap Request a wholesale quote.", "Enter the quantity, your phone and a message.", "The shop replies under Quotes."], l: "/store#b2b", b: "Wholesale"},
    // ---------- promote / pay
    {t: "Boost my profile, post, job or service", k: "boost promote ad advertise paid featured sponsored", s: ["Open Promote.", "Pick what to boost and the plan.", "Pay and it goes live. See views and clicks under your orders."], l: "/promote", b: "Open Promote"},
    // ---------- tools
    {t: "Keep track of money (Money)", k: "money hisaab kitab expense income budget udhaar loan cash account", s: ["Open Money.", "Add your accounts (cash, bank, wallet).", "Use + Received and − Paid for each entry; add people you owe or who owe you under To pay / To receive."], l: "/money", b: "Open Money"},
    {t: "Make a digital business card", k: "visiting card business card qr digital card", s: ["Open My business cards and tap + New card.", "Choose your card address (it goes inside the QR code, so it cannot change).", "Add your details, icons and template, then share or download the QR."], l: "/cards", b: "My cards"},
    {t: "Use the step counter", k: "steps walk run step counter health map", s: ["Open Step counter.", "Choose Walk, Run or Ride and tap Start. Keep the page open while you walk.", "Tap Finish and save. Set a daily goal in Settings."], l: "/steps", b: "Step counter"},
    {t: "Find all the tools", k: "tools calculator converter prayer times qibla age zakat", s: ["Open Tools.", "Search or browse the groups (Money, Convert, Dates, Maths, Health, Daily...).", "Pin the ones you use most."], l: "/tools", b: "Open tools"},
    {t: "Book a ride (women only)", k: "ride rides taxi car rickshaw bike uber ladies women gari", s: ["Open Rides.", "Set pickup and drop-off on the map and choose car, rickshaw or bike.", "Tap ask for a ride. A nearby woman driver accepts; pay cash at the end."], l: "/rides", b: "Open Rides"},
    {t: "Drive with Rides (women)", k: "driver drive earn rides licence", s: ["Get your ID verified first.", "Open Rides, then Drive, and upload your licence, vehicle papers and a photo with the vehicle.", "After the team approves you, go online to get rides."], l: "/rides#drive", b: "Become a driver"},
    {t: "Make my family tree (Roots of Love)", k: "family tree shajra khandan rishtay roots love relatives", s: ["Open Roots of Love and tap Start my family tree.", "Tap any person to add their father, mother, husband/wife or children.", "Share the family code or an invite link on WhatsApp so relatives join."], l: "/roots", b: "Open Roots of Love"},
    // ---------- community
    {t: "Find a blood donor", k: "blood donor khoon group hospital emergency", s: ["Open Blood Bank and choose the blood group and city.", "Search donors or post a request.", "When a donor accepts, you can chat."], l: "/blood", b: "Blood Bank"},
    {t: "Give or ask for things (Donate)", k: "donate give clothes books cheezain dena", s: ["Open Donate.", "Tap Give something, add photos and details, and post it.", "People ask for it; accept one and chat."], l: "/donate", b: "Open Donate"},
    {t: "Register my pet and QR tag", k: "pet dog cat qr tag vaccine lost", s: ["Open My pets and tap Add a pet.", "Add health records and plan vaccines from the schedule.", "Print the QR tag for the collar. If lost, tap Mark as lost."], l: "/pets", b: "My pets"},
    {t: "Learn a course and get a certificate", k: "course academy learn certificate excel word python quiz seekhna", s: ["Open XpertAcademy and pick a course.", "Go through the lessons and pass the quiz.", "Leave a short review and your certificate opens."], l: "/academy/", b: "Open Academy"},
    {t: "Check a certificate", k: "verify certificate check real fake", s: ["Open the verify page.", "Type the certificate number or open its link."], l: "/verify", b: "Check a certificate"},
    // ---------- help
    {t: "Talk to the team (support ticket)", k: "support help ticket complaint problem contact team shikayat madad", s: ["Open Support and tap Open a ticket.", "Write a short subject and what is going on.", "The team replies on the ticket; you get a notification."], l: "/support", b: "Open Support"},
    {t: "The site looks old after an update", k: "old update not updating refresh cache purana", s: ["Close the app or tab and open it again (on a phone, pull down to refresh).", "If it still looks old, clear the site's data in your browser settings."], l: "/whats-new", b: "What's new"}
  ];
  var SYN = {naukri: "job", nokri: "job", naukari: "job", vacancy: "job", jobs: "job", gig: "service", gigs: "service", kaam: "work", dukaan: "shop", dukan: "shop", makan: "house", ghar: "house", zameen: "plot", kiraya: "rent", kiraye: "rent",
    paisay: "money", paise: "money", pesay: "money", raqam: "money", shajra: "family", khandan: "family", rishtay: "family", gari: "car", gaari: "car", taxi: "ride", tasdeeq: "verify", number: "phone", mobile: "phone", tasveer: "photo", picture: "photo", dp: "photo",
    khata: "account", login: "sign", signin: "sign", madad: "help", shikayat: "complaint", bechna: "sell", bechni: "sell", khareedna: "buy", kharidna: "buy", banana: "make", banani: "make", banwana: "hire", dalna: "post", dalni: "post", lagana: "post", likhna: "post",
    seekhna: "learn", khoon: "blood", inaam: "prize", nikalna: "withdraw", nikalun: "withdraw", nikalni: "withdraw", nikalo: "withdraw", kholna: "open", kholni: "open", kholo: "open", dost: "friend", rabta: "contact"};
  var STOP = "how to do i a an the my me can is are of in on for and or kaisay kaise kese kesay kaisy kese kia kya kyse karoon karun karoo karna karein krna kro karo hai hain mein main mujhe mujay hum apna apni apne ka ki ke ko se sey par pe ye yeh wo please plz".split(" ");
  function norm(s){ return String(s || "").toLowerCase().replace(/[^a-z0-9؀-ۿ ]+/g, " ").split(/\s+/).filter(function(w){ return w && STOP.indexOf(w) < 0; }).map(function(w){ return SYN[w] || w.replace(/(ing|es|s)$/, function(x){ return w.length > 4 ? "" : x; }); }); }
  A.forEach(function(a){ a.T = norm(a.t); a.K = norm(a.k); a.S = norm(a.s.join(" ")); });
  function hit(list, w){ for (var i = 0; i < list.length; i++){ var x = list[i]; if (x === w || (w.length >= 3 && x.indexOf(w) === 0) || (x.length >= 4 && w.indexOf(x) === 0)) return 1; } return 0; }
  function search(q){
    var ws = norm(q); if (!ws.length) return [];
    return A.map(function(a){ var sc = 0, got = 0; ws.forEach(function(w){ var s = hit(a.T, w) * 3 + hit(a.K, w) * 2 + hit(a.S, w); if (s) got++; sc += s; }); return {a: a, sc: sc + (got === ws.length ? 4 : 0)}; })
      .filter(function(x){ return x.sc > 0; }).sort(function(x, y){ return y.sc - x.sc; }).slice(0, 6).map(function(x){ return x.a; });
  }
  function esc(s){ return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  var CSS = ".xh{margin:0 0 16px;font-family:inherit}.xh *{box-sizing:border-box}"
    + ".xh-box{background:linear-gradient(135deg,#1B4DFF,#7C3AED);border-radius:20px;padding:18px 16px;color:#fff}"
    + ".xh-box h2{margin:0 0 4px;font-size:20px;font-weight:800;color:#fff}.xh-box p{margin:0 0 12px;font-size:13.5px;opacity:.9}"
    + ".xh-in{display:flex;align-items:center;gap:8px;background:#fff;border-radius:14px;padding:4px 6px 4px 12px}"
    + ".xh-in input{flex:1;border:0;outline:0;font:inherit;font-size:16px;padding:10px 0;color:#0D1424;background:none;min-width:0}"
    + ".xh-in span{font-size:18px}.xh-chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}"
    + ".xh-chips button{border:0;background:rgba(255,255,255,.18);color:#fff;border-radius:99px;padding:6px 11px;font:inherit;font-size:12.5px;font-weight:700;cursor:pointer}"
    + ".xh-res{margin-top:10px}.xh-a{background:#fff;border:1px solid #E4E8F2;border-radius:16px;margin-bottom:8px;overflow:hidden}"
    + ".xh-a>button{display:flex;width:100%;align-items:center;gap:10px;text-align:left;border:0;background:none;padding:13px 14px;font:inherit;font-size:15px;font-weight:800;color:#0D1424;cursor:pointer}"
    + ".xh-a>button i{margin-left:auto;font-style:normal;color:#94A3B8;transition:transform .2s}.xh-a.on>button i{transform:rotate(90deg)}"
    + ".xh-a .bd{display:none;padding:0 14px 14px}.xh-a.on .bd{display:block}"
    + ".xh-a ol{margin:0 0 10px;padding-left:22px;font-size:14.5px;line-height:1.55;color:#1E293B}.xh-a li{margin-bottom:5px}"
    + ".xh-a .tip{font-size:13px;color:#92400E;background:#FEF3C7;border-radius:10px;padding:8px 10px;margin-bottom:10px}"
    + ".xh-go{display:inline-flex;align-items:center;gap:6px;background:#1B4DFF;color:#fff!important;text-decoration:none;font-weight:800;font-size:14px;padding:10px 14px;border-radius:12px}"
    + ".xh-none{background:#fff;border:1px solid #E4E8F2;border-radius:16px;padding:14px;font-size:14px;color:#334155}"
    + ".xh-none a{font-weight:800;color:#1B4DFF}";
  function render(el){
    if (el._xh) return; el._xh = 1;
    var st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    var chips = ["Post a job", "Sell my skill", "Get the blue tick", "Open my shop", "Forgot password", "Family tree"];
    el.innerHTML = '<div class="xh"><div class="xh-box"><h2>🔎 How can we help?</h2><p>Type your question in English or Roman Urdu, e.g. "job kaisay post karoon".</p>'
      + '<div class="xh-in"><span>🔎</span><input type="search" id="xhq" placeholder="Search help…" autocomplete="off" enterkeyhint="search"></div>'
      + '<div class="xh-chips">' + chips.map(function(c){ return '<button type="button" data-q="' + esc(c) + '">' + esc(c) + '</button>'; }).join("") + '</div></div><div class="xh-res" id="xhr"></div></div>';
    var q = el.querySelector("#xhq"), r = el.querySelector("#xhr"), t = null;
    function show(){
      var v = q.value.trim(), res = search(v);
      if (!v){ r.innerHTML = el.hasAttribute("data-all") ? '<div class="xh-none"><b style="display:block;margin-bottom:8px">All help topics</b>' + A.map(function(a){ return '<a href="#" data-t="' + esc(a.t) + '" style="display:block;padding:6px 0;font-weight:600;color:#1B4DFF;text-decoration:none;border-top:1px solid #F1F5F9">' + esc(a.t) + '</a>'; }).join("") + '</div>' : ""; return; }
      if (!res.length){ r.innerHTML = '<div class="xh-none">No ready answer for that yet. <a href="/assistant">Ask the AI assistant</a>, or <a href="/support">open a support ticket</a> and the team will help.</div>'; return; }
      r.innerHTML = res.map(function(a, i){
        return '<div class="xh-a' + (i === 0 ? " on" : "") + '"><button type="button">' + esc(a.t) + '<i>›</i></button><div class="bd"><ol>' + a.s.map(function(x){ return "<li>" + esc(x) + "</li>"; }).join("") + '</ol>'
          + (a.tip ? '<div class="tip">' + esc(a.tip) + '</div>' : '') + '<a class="xh-go" href="' + esc(a.l) + '">' + esc(a.b) + ' →</a></div></div>'; }).join("")
        + '<div class="xh-none" style="margin-top:4px;font-size:13px">Not what you need? <a href="/assistant">Ask the AI assistant</a> or <a href="/support">open a support ticket</a>.</div>';
    }
    q.oninput = function(){ clearTimeout(t); t = setTimeout(show, 120); };
    r.onclick = function(e){
      var tt = e.target.closest("[data-t]"); if (tt){ e.preventDefault(); q.value = tt.getAttribute("data-t"); show(); window.scrollTo({top: el.getBoundingClientRect().top + window.pageYOffset - 70, behavior: "smooth"}); return; }
      var b = e.target.closest(".xh-a>button"); if (b) b.parentNode.classList.toggle("on"); };
    el.querySelector(".xh-chips").onclick = function(e){ var b = e.target.closest("[data-q]"); if (!b) return; q.value = b.getAttribute("data-q"); show(); q.focus(); };
    var p = (location.search.match(/[?&]q=([^&]+)/) || [])[1];
    if (p){ q.value = decodeURIComponent(p.replace(/\+/g, " ")); }
    show();
  }
  window.XCHELP_SEARCH = search;
  function start(){ var el = document.getElementById("xchelp"); if (el) render(el); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
