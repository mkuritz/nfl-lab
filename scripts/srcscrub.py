"""Public-text source-name scrubber (standing rule: no data-source names on public pages).
Rewrites display strings in public JSON; leaves URLs, ids, sportsbook/price-venue names, TV broadcasters and
third-party news text (journalist attributions) and required data credits (MoneyPuck.com: their terms require credit) alone. Usage: python3 srcscrub.py <file-or-dir> [...]  or  import scrub_obj."""
import json, os, re, sys
SKIP_KEYS = {"url", "src_url", "link", "href", "book", "best_book", "ref_book", "books_list", "bc", "broadcast", "t", "title_news", "headline", "description", "story", "news_text", "img", "logo", "id", "aid", "espn_id"}
R = [
    (r"(?:^|(?<=\.\s))(?:Per|According to)\s+[A-Z][\w'. -]{1,40}?\s+of\s+ESPN(?:\.com|\s+\d+\s+[A-Za-z]+)?,\s*", ""),
    (r",?(\"?)\s*(?:per|according to)\s+(?:[A-Z][\w'. -]{1,40}?\s+of\s+)?ESPN(?:\.com|\s+\d+\s+[A-Za-z]+)?(?:'s\s+[A-Z][\w'.-]+(?:\s+[A-Z]\w*)?)?(?=[.)\"'\s]|$)", r"\1"),
    (r",(\"?)\s*[A-Z][\w'. -]{1,40}?\s+of\s+ESPN(?:\.com|\s+\d+\s+[A-Za-z]+)?\s+re(?:ports?)?(?=[.)\"'\s]|$)", r"\1"),
    (r",(\"?)\s*(?:a\s+(?:team\s+|league\s+)?source|sources|his\s+agent)\s+told\s+ESPN(?:\.com)?(?:'s\s+[A-Z][\w'.-]+(?:\s+[A-Z]\w*)?)?(?=[.)\"'\s]|$)", r"\1"),
    (r"\b(?:A\s+(?:team\s+|league\s+)?source|Sources)\s+told\s+ESPN(?:\.com)?\s+that\s+", ""),
    (r"\btells\s+ESPN(?:\.com)?\s+about\b", "discusses"),
    (r"\s+of\s+ESPN(?:\.com|\s+\d+\s+[A-Za-z]+)?\b", ""),
    (r"\bESPN\.com\b", ""),
    (r"\s*\((?:via )?ESPN(?:'s)? (?:public|free)?\s*(?:odds )?feed\)", ""),
    (r"\s*via ESPN(?:'s)?(?: public| free)?(?: odds)?(?: feed| scoreboard| pickcenter)?", ""),
    (r"\s*\(ESPN\)", ""),
    (r"Kickoff forecast \(Open-Meteo\)", "Kickoff forecast"),
    (r"\s*\(Open-Meteo[^)]*\)", ""),
    (r"Open-Meteo forecast", "Forecast"),
    (r"Open-Meteo", "forecast"),
    (r"ESPN (FPI|BPI)", r"power index"),
    (r"(?:from )?ESPN(?:'s)? (injury report|injury reports|injuries|game logs?|match logs?|match data|box scores?|boxscores?|depth charts?|standings|schedule|rosters?|leaders|coach-season records|coach records?|scoreboard|summary|final scores)", lambda m: ("from " if m.group(0).lower().startswith("from") else "") + m.group(1)),
    (r"ESPN NFL standings", "NFL standings"),
    (r"\s*from ESPN\.?$", "."),
    (r"ESPN fantasy public player list", "public fantasy ownership"),
    (r"(?:The )?Odds API \(([^,)]+),\s*(as of [^)]*)\)", r"\1 (\2)"),
    (r"(?:The )?Odds API \(([^)]*)\)(?: via Bet Lab market snapshots)?", r"\1"),
    (r"(?:The )?Odds API (prices|books|lines|props?|prop pulls)", r"market \1"),
    (r"(?:The )?Odds API,?\s*", "market data, "),
    (r"MLB (?:Stats API|statsapi)", "official MLB data"),
    (r"NHL (?:API|stats feed)", "official NHL data"),
    (r"\(nflverse[^)]*\)", "(weekly player stats)"),
    (r"nflverse\s*", ""),
    (r"Graded from official final scores|Graded from ESPN final scores", "Graded from official final scores"),
    (r"ESPN report", "injury report"),
    (r"ESPN pickcenter\s*", ""),
    (r"\bESPN(?!\s?BET|\s?Bet|\+|2|U\b| Deportes|\.com)\s*", ""),
]
R = [(re.compile(a), b) for a, b in R]
def s_(v):
    if "ESPN" not in v and "nflverse" not in v and "Odds API" not in v and "Open-Meteo" not in v and "statsapi" not in v and "Stats API" not in v and "NHL API" not in v and "NHL stats feed" not in v: return v
    if v.startswith("http"): return v
    for a, b in R: v = a.sub(b, v)
    v = re.sub(r"(?:^|(?<=\.\s))([a-z])", lambda m: m.group(1).upper(), v)
    return re.sub(r"\s{2,}", " ", v).replace(" .", ".").replace("..", ".").replace(",.", ".").replace('".', '."').replace("market data, )", "market data)").strip()

# ---- sportsbook / exchange names -> fixed public letters (standing rule, Oct 19 2026). Real names stay only in private engine files.
# Case-sensitive proper names only: lowercase API keys (e.g. "draftkings") are lookup ids the pages map to letters themselves.
BOOK_L = [("DraftKings Sportsbook", "Book A"), ("DraftKings", "Book A"), ("FanDuel Sportsbook", "Book B"), ("FanDuel", "Book B"), ("BetMGM", "Book C"),
          ("Caesars Sportsbook", "Book D"), ("William Hill", "Book D"), ("Caesars", "Book D"), ("Fanatics Sportsbook", "Book E"), ("Fanatics", "Book E"), ("BetRivers", "Book F"),
          ("theScore Bet", "Book P"), ("theScore / ESPN Bet", "Book G"), ("ESPN BET", "Book G"), ("ESPN Bet", "Book G"), ("ESPNBet", "Book G"), ("bet365", "Book H"), ("Hard Rock Bet", "Book I"), ("Hard Rock", "Book I"),
          ("PointsBet", "Book J"), ("Fliff", "Book K"), ("Bovada", "Book L"), ("BetOnline.ag", "Book M"), ("BetOnline", "Book M"), ("PrizePicks", "Book N"), ("Underdog Fantasy", "Book O"), ("Underdog", "Book O"),
          ("Unibet", "Book Q"), ("WynnBET", "Book R"), ("Borgata", "Book S"), ("BetPARX", "Book V"), ("betPARX", "Book V"), ("Bally Bet", "Book W"), ("MyBookie", "Book Z"), ("LowVig", "Book X"), ("Circa Sports", "Book Y"), ("Circa", "Book Y"),
          ("Kalshi", "Exchange A"), ("Polymarket", "Exchange B"), ("Novig", "Exchange C"), ("ProphetX", "Exchange D"), ("Sporttrade", "Exchange E"), ("Betfair", "Exchange F"), ("BetOpenly", "Exchange H"),
          ("Pinnacle", "sharp book")]
_BRE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(a) for a, _ in BOOK_L) + r")(?:'s)?(?![A-Za-z])")
_BMAP = dict(BOOK_L)
_ABR = re.compile(r"\b(DK|FD|MGM|CZR)(?= [+-]?\d)|^(DK|FD|MGM|CZR|PIN)$")
_AMAP = {"DK": "Book A", "FD": "Book B", "MGM": "Book C", "CZR": "Book D", "PIN": "sharp book"}
BOOK_SKIP_KEYS = {"url", "src_url", "link", "href", "img", "logo", "id", "aid", "espn_id", "ticker", "event_ticker", "slug"}
def books_s(v):
    if not v or v.startswith(("http://", "https://")): return v
    v = _BRE.sub(lambda m: _BMAP[m.group(1)], v)
    return _ABR.sub(lambda m: _AMAP[m.group(1) or m.group(2)], v)
def books_obj(d, k=None):
    if isinstance(d, dict): return {(books_s(kk) if kk in _BMAP else kk): (vv if kk in BOOK_SKIP_KEYS else books_obj(vv, kk)) for kk, vv in d.items()}
    if isinstance(d, list): return [books_obj(x, k) for x in d]
    if isinstance(d, str): return books_s(d)
    return d
def _is_log(p):
    b = os.path.basename(p).lower()
    return b.endswith(".jsonl") or any(t in b for t in ("log", "ledger", "grades", "history", "tracker", "clv"))
def scrub_obj(d, k=None):
    if isinstance(d, dict): return {kk: (vv if kk in SKIP_KEYS else scrub_obj(vv, kk)) for kk, vv in d.items()}
    if isinstance(d, list): return [scrub_obj(x, k) for x in d]
    if isinstance(d, str): return s_(d)
    return d
def scrub_file(p):
    try:
        if p.endswith(".jsonl"):
            raw = [l for l in open(p) if l.strip()]; O = [json.loads(l) for l in raw]; N = [scrub_obj(x) for x in O]
            if N != O: open(p, "w").write("\n".join(r.rstrip("\n") if o == n else json.dumps(n, separators=(",", ":")) for r, o, n in zip(raw, O, N)) + "\n")
        else:
            O = json.load(open(p)); N = scrub_obj(O)
            if not _is_log(p): N = books_obj(N)   # logged picks/history are never rewritten
            if N != O: open(p, "w").write(json.dumps(N, separators=(",", ":"), ensure_ascii=False))
    except Exception as e: print("srcscrub skip", p, e)
def scrub_dir(a):
    for root, _, fs in os.walk(a):
        for f in fs:
            if f.endswith((".json", ".jsonl")): scrub_file(os.path.join(root, f))
if __name__ == "__main__":
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            for root, _, fs in os.walk(a):
                for f in fs:
                    if f.endswith((".json", ".jsonl")): scrub_file(os.path.join(root, f))
        else: scrub_file(a)
