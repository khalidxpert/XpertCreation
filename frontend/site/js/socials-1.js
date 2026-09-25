/* Social links: the list of networks, how their addresses are built, the edit form and the chips. */
(function(){
  "use strict";
  // key, label, address pattern ({} = username; null = shown as text, no link)
  var S = [
    ["facebook", "Facebook", "https://www.facebook.com/{}"], ["instagram", "Instagram", "https://www.instagram.com/{}"],
    ["x", "X (Twitter)", "https://x.com/{}"], ["threads", "Threads", "https://www.threads.net/@{}"],
    ["tiktok", "TikTok", "https://www.tiktok.com/@{}"], ["youtube", "YouTube", "https://www.youtube.com/@{}"],
    ["linkedin", "LinkedIn", "https://www.linkedin.com/in/{}"], ["github", "GitHub", "https://github.com/{}"],
    ["whatsapp", "WhatsApp", "https://wa.me/{}"], ["telegram", "Telegram", "https://t.me/{}"],
    ["snapchat", "Snapchat", "https://www.snapchat.com/add/{}"], ["pinterest", "Pinterest", "https://www.pinterest.com/{}"],
    ["reddit", "Reddit", "https://www.reddit.com/user/{}"], ["discord", "Discord", null],
    ["twitch", "Twitch", "https://www.twitch.tv/{}"], ["bluesky", "Bluesky", "https://bsky.app/profile/{}"],
    ["mastodon", "Mastodon", "mastodon"], ["medium", "Medium", "https://medium.com/@{}"],
    ["behance", "Behance", "https://www.behance.net/{}"], ["dribbble", "Dribbble", "https://dribbble.com/{}"],
    ["stackoverflow", "Stack Overflow", "https://stackoverflow.com/users/{}"], ["quora", "Quora", "https://www.quora.com/profile/{}"],
    ["tumblr", "Tumblr", "https://{}.tumblr.com"], ["vk", "VK", "https://vk.com/{}"],
    ["soundcloud", "SoundCloud", "https://soundcloud.com/{}"], ["spotify", "Spotify", "https://open.spotify.com/user/{}"],
    ["vimeo", "Vimeo", "https://vimeo.com/{}"], ["flickr", "Flickr", "https://www.flickr.com/people/{}"],
    ["upwork", "Upwork", "https://www.upwork.com/freelancers/{}"], ["fiverr", "Fiverr", "https://www.fiverr.com/{}"],
    ["kaggle", "Kaggle", "https://www.kaggle.com/{}"], ["leetcode", "LeetCode", "https://leetcode.com/u/{}"],
    ["devto", "DEV", "https://dev.to/{}"], ["xing", "XING", "https://www.xing.com/profile/{}"],
    ["weibo", "Weibo", "https://weibo.com/{}"], ["line", "LINE", null], ["wechat", "WeChat", null],
    ["kakaotalk", "KakaoTalk", null], ["signal", "Signal", null], ["skype", "Skype", null]
  ];
  var BY = {};
  S.forEach(function(s){ BY[s[0]] = s; });
  function esc(s){
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function handleOf(k, v){
    v = String(v || "").trim();
    if (k === "whatsapp") return v.replace(/[^\d]/g, "").replace(/^0(?=3)/, "92");
    var m = v.match(/^https?:\/\/[^\/]+\/(?:in\/|user\/|users\/|u\/|profile\/|people\/|freelancers\/|add\/)?@?([^\/?#]+)/i);
    if (m && k !== "mastodon" && k !== "tumblr") v = decodeURIComponent(m[1]);
    return v.replace(/^@/, "").slice(0, 100);
  }
  window.SOCIALS = S;
  window.socialUrl = function(k, h){
    var s = BY[k];
    if (!s || !h || !s[2]) return "";
    if (s[2] === "mastodon"){
      var p = String(h).replace(/^@/, "").split("@");
      return p.length === 2 ? "https://" + p[1] + "/@" + p[0] : "";
    }
    return s[2].replace("{}", encodeURIComponent(h).replace(/%40/g, "@"));
  };
  window.socialChips = function(o){
    return S.filter(function(s){ return o && o[s[0]]; }).map(function(s){
      var u = window.socialUrl(s[0], o[s[0]]);
      return u ? "<a class='chip' href='" + esc(u) + "' target='_blank' rel='noopener nofollow ugc'>" + esc(s[1]) + "</a>"
               : "<span class='chip' title='" + esc(s[1]) + "'>" + esc(s[1]) + ": " + esc(o[s[0]]) + "</span>";
    }).join("");
  };
  window.socialInputs = function(o){
    o = o || {};
    return "<p class='muted' style='margin-top:0'>Type just your username (or paste the link). Leave the rest empty.</p>"
      + "<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px'>"
      + S.map(function(s){
          return "<label style='margin:0'>" + esc(s[1]) + "<input id='so-" + s[0] + "' maxlength='100' value='" + esc(o[s[0]] || "")
            + "' placeholder='" + (s[0] === "whatsapp" ? "03001234567" : s[0] === "mastodon" ? "name@server" : "username") + "'></label>";
        }).join("") + "</div>";
  };
  window.socialValues = function(){
    var out = {};
    S.forEach(function(s){
      var el = document.getElementById("so-" + s[0]);
      var h = el ? handleOf(s[0], el.value) : "";
      if (h) out[s[0]] = h;
    });
    return out;
  };
})();
