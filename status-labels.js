/* NFL Hub status labels (display only). Loads data/status_overlay.json and paints
   trending-out / Watch / confirmed-Out pills on player profiles, team injuries,
   and prop cards. Does not change pick logic, model weights, or probabilities.
   Official confirmed Out/Doubtful/IR overrides unconfirmed trending labels.
   Staleness: if the overlay or a player row is older than 6 hours (or past expires), hide labels. */
(function () {
  "use strict";
  if (window.SLStatus) return;
  var D = null, P = null, TTL_MS = 6 * 3600e3;
  var E = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  function parseTs(s) {
    if (!s) return null;
    var t = Date.parse(s);
    return isNaN(t) ? null : t;
  }
  function fresh(file, row) {
    var now = Date.now();
    if (!file) return false;
    var fu = parseTs(file.updated), fe = parseTs(file.expires);
    if (fe != null && now > fe) return false;
    if (fu != null && now - fu > TTL_MS) return false;
    if (row) {
      var re = parseTs(row.expires), ra = parseTs(row.as_of);
      if (re != null && now > re) return false;
      if (ra != null && now - ra > TTL_MS) return false;
    }
    return true;
  }
  function load() {
    if (P) return P;
    P = fetch("data/status_overlay.json?v=" + Math.floor(Date.now() / 18e4))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j || !fresh(j)) { D = null; return null; }
        D = j;
        return j;
      })
      .catch(function () { P = null; return null; });
    return P;
  }
  function lookup(aid, name) {
    if (!D || !fresh(D)) return null;
    var a = aid != null ? String(aid) : "";
    var o = null;
    if (a && D.by_aid && D.by_aid[a]) o = D.by_aid[a];
    else {
      var n = String(name || "").toLowerCase().replace(/\s+jr\.?$/, "").trim();
      if (n && D.by_name && D.by_name[n]) o = D.by_name[n];
      else if (n && D.by_name && D.by_name[n + " jr."]) o = D.by_name[n + " jr."];
    }
    if (!o || !fresh(D, o)) return null;
    return o;
  }
  function resolve(baseSt, aid, name) {
    var o = lookup(aid, name);
    var st = (baseSt || (o && o.status) || "").trim();
    if (!o) return { st: st, tags: [], watch: false, unconfirmed: false, o: null };
    if (o.confirmed && /^Out$/i.test(o.status || "")) {
      return { st: "Out", tags: [], watch: false, unconfirmed: false, o: o, confirmed: true };
    }
    if (/^(Out|Injured Reserve|Doubtful|Suspension)/i.test(st) && !o.unconfirmed) {
      return { st: st, tags: [], watch: false, unconfirmed: false, o: o };
    }
    return {
      st: o.status || st || "Questionable",
      tags: (o.tags || []).slice(),
      watch: !!o.watch,
      unconfirmed: !!o.unconfirmed,
      o: o,
      confirmed: !!o.confirmed
    };
  }
  function pillClass(st) {
    if (/Out|Reserve|Suspen/i.test(st || "")) return "o";
    if (/Doubt/i.test(st || "")) return "d";
    return "q";
  }
  function pills(st, tags, opts) {
    opts = opts || {};
    var cls = opts.cls || "ib";
    var h = "";
    if (st && st !== "Active") {
      h += ' <span class="' + cls + " " + pillClass(st) + '">' + E(st) + "</span>";
    }
    (tags || []).forEach(function (t) {
      var c = /watch/i.test(t) ? "w" : /trending|unconfirmed/i.test(t) ? "u" : "q";
      h += ' <span class="' + cls + " " + c + '">' + E(t) + "</span>";
    });
    return h;
  }
  function fromInj(inj, aid, name) {
    inj = inj || {};
    var base = inj.st || inj.status || "";
    var r = resolve(base, aid || inj.id, name || inj.n || inj.name);
    var tags = (r.tags || []).slice();
    if (r.confirmed) { r.st = r.st || "Out"; tags = []; }
    // Do not trust hand-stamped inj.tags when overlay is missing/stale
    return { st: r.st || base, tags: tags, watch: !!r.watch, unconfirmed: !!r.unconfirmed, o: r.o, confirmed: !!r.confirmed };
  }
  var css = document.createElement("style");
  css.id = "sl-status-css";
  css.textContent =
    ".ib.u,#nfpd .pill.u,.sl-st.u{background:#3a2a08;color:#fbbf24;border:1px solid #fbbf2455}" +
    ".ib.w,#nfpd .pill.w,.sl-st.w{background:#1e3a5f;color:#7dd3fc;border:1px solid #38bdf855}" +
    "#nfpd .pill.u,#nfpd .pill.w{margin-left:4px}" +
    ".pc .sl-st{display:inline-block;padding:1px 7px;border-radius:99px;font-size:10px;font-weight:800;margin-left:4px;vertical-align:1px}" +
    ".pc .sl-st.q{background:#3a3a12;color:#facc15}" +
    ".pc .sl-st.o{background:#4c1d24;color:#ff8a95}" +
    ".pc .sl-st.d{background:#4a3310;color:#fbbf24}";
  document.head.appendChild(css);

  window.SLStatus = {
    load: load,
    lookup: lookup,
    resolve: resolve,
    fromInj: fromInj,
    pills: pills,
    pillClass: pillClass,
    fresh: fresh,
    E: E
  };
  load();
})();
