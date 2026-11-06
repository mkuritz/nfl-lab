/* Display-only: RB avg attempts × opp yards allowed per attempt. Does not change projections. */
(function () {
  "use strict";
  if (window.SLRBExpected) return;
  var CACHE = null,
    P = null;
  function E(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function load() {
    if (CACHE) return Promise.resolve(CACHE);
    if (P) return P;
    P = fetch("data/rb_expected_rush.json?v=" + Math.floor(Date.now() / 6e5))
      .then(function (r) {
        if (!r.ok) throw 0;
        return r.json();
      })
      .then(function (d) {
        CACHE = d;
        return d;
      })
      .catch(function () {
        P = null;
        return null;
      });
    return P;
  }
  function row(id) {
    return CACHE && CACHE.players ? CACHE.players[String(id)] : null;
  }
  function cardHtml(r) {
    if (!r) return "";
    var site = r.home ? "vs" : "@";
    var kick = r.kickoff
      ? new Date(r.kickoff).toLocaleString("en-US", {
          timeZone: "America/New_York",
          weekday: "short",
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
        }) + " ET"
      : "";
    var comps =
      '<div class="sl-rbex-math"><span class="sl-rbex-n">' +
      E(r.avg_att) +
      '</span> <span class="sl-rbex-l">avg att</span> <span class="sl-rbex-op">×</span> <span class="sl-rbex-n">' +
      E(r.opp_ypc) +
      '</span> <span class="sl-rbex-l">yds allowed/att</span> <span class="sl-rbex-op">=</span> <span class="sl-rbex-n sl-rbex-exp">' +
      E(r.expected) +
      '</span> <span class="sl-rbex-l">expected yds</span></div>';
    var side = "";
    if (r.sl_proj != null || r.line != null) {
      side = '<div class="sl-rbex-side">';
      if (r.sl_proj != null)
        side +=
          '<div><span class="sl-rbex-l">Sports Labs proj</span><b>' +
          E(Math.round(r.sl_proj * 10) / 10) +
          "</b></div>";
      if (r.line != null) {
        var tag = r.line_src == "model" ? "model line" : "book line";
        side +=
          '<div><span class="sl-rbex-l">' +
          E(tag) +
          "</span><b>" +
          E(r.line) +
          "</b></div>";
      }
      side += "</div>";
    }
    var under =
      '<div class="sl-rbex-mut">' +
      E(r.label) +
      " · " +
      E(r.att_window) +
      " · " +
      E(r.opp) +
      " allows " +
      E(r.opp_ypc) +
      " yds/att" +
      (r.opp_ry != null && r.opp_ra != null
        ? " (" + E(r.opp_ry) + " yds / " + E(r.opp_ra) + " att)"
        : "") +
      (kick ? " · " + E(site + " " + r.opp + " · " + kick) : "") +
      ". Not a replacement for the Sports Labs projection.</div>";
    return (
      '<div class="sl-rbex card" data-sl-rbex="' +
      E(r.id) +
      '"><div class="sl-rbex-h">Expected rush yards</div>' +
      comps +
      side +
      under +
      "</div>"
    );
  }
  function lineHtml(r) {
    if (!r) return "";
    return (
      '<div class="sl-rbex-line mut sm">' +
      E(r.avg_att) +
      " att × " +
      E(r.opp_ypc) +
      " yds allowed/att = <b>" +
      E(r.expected) +
      "</b> expected yds <span class=\"mut\">(attempts × opponent rate)</span></div>"
    );
  }
  var css = document.createElement("style");
  css.textContent =
    ".sl-rbex{background:#121a2a;border:1px solid #232b3b;border-radius:12px;padding:10px 12px;margin-top:10px}" +
    ".sl-rbex-h{font-size:12px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;color:#8b97b0;margin-bottom:6px}" +
    ".sl-rbex-math{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 6px;font-size:14px;color:#e6e9ef}" +
    ".sl-rbex-n{font-weight:800;font-size:18px;color:#53e3a6}.sl-rbex-exp{color:#a78bfa}" +
    ".sl-rbex-l{font-size:11px;color:#8b97b0;font-weight:600}.sl-rbex-op{color:#8b97b0;font-weight:700}" +
    ".sl-rbex-side{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px}.sl-rbex-side div{background:#182033;border-radius:8px;padding:6px 8px;min-width:96px}" +
    ".sl-rbex-side b{display:block;font-size:16px;color:#e6e9ef}.sl-rbex-mut{margin-top:6px;font-size:11.5px;color:#8b97b0;line-height:1.4}" +
    ".sl-rbex-line{margin-top:4px}.sh .sl-rbex{margin:10px 16px}";
  document.head.appendChild(css);

  function mount(el, id) {
    if (!el) return;
    load().then(function () {
      var r = row(id);
      if (!r) {
        el.innerHTML = "";
        return;
      }
      el.innerHTML = cardHtml(r);
    });
  }
  window.SLRBExpected = { load: load, row: row, cardHtml: cardHtml, lineHtml: lineHtml, mount: mount };
})();
