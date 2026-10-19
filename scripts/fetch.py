"""Pull official/public ESPN site-API feeds (scoreboard, standings, news) into data/. Display only."""
import json, sys, urllib.request, datetime, os
UA={"User-Agent":"SportsLabs/1.0"}
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=25))
    except Exception as e: print("fail",u,e); return None
def slim_board(j):
    out=[]
    for e in (j or {}).get("events",[]):
        c=e["competitions"][0]; t={x["homeAway"]:x for x in c["competitors"]}
        if "home" not in t: continue
        def side(x): return {"abbr":x["team"].get("abbreviation"),"name":x["team"].get("displayName"),"logo":x["team"].get("logo"),
             "score":x.get("score"),"record":(x.get("records") or [{}])[0].get("summary"),"form":x.get("form")}
        o=(c.get("odds") or [{}])[0] or {}
        out.append({"id":e["id"],"date":e["date"],"name":e.get("shortName"),"status":c["status"]["type"].get("shortDetail"),
            "state":c["status"]["type"].get("state"),"venue":(c.get("venue") or {}).get("fullName"),
            "home":side(t["home"]),"away":side(t["away"]),"line":o.get("details"),"total":o.get("overUnder"),
            "odds_src":(o.get("provider") or {}).get("name"),"bc":[(b.get("names") or [None])[0] for b in c.get("broadcasts",[])][:2]})
    return out
def slim_news(j):
    return [{"t":a.get("headline"),"d":a.get("published"),"u":((a.get("links") or {}).get("web") or {}).get("href"),"desc":a.get("description")} for a in (j or {}).get("articles",[])][:25]
def slim_stand(j):
    rows=[]
    def walk(n,grp):
        for c in n.get("children",[]): walk(c,c.get("name") or grp)
        for e in (n.get("standings") or {}).get("entries",[]):
            st={s["name"]:s.get("displayValue") for s in e.get("stats",[])}
            rows.append({"grp":grp,"team":e["team"].get("abbreviation") or e["team"].get("shortDisplayName"),"name":e["team"].get("displayName"),"logo":(e["team"].get("logos") or [{}])[0].get("href"),"st":st})
    if j: walk(j,j.get("name"))
    return rows
def main(sport):
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if sport=="nfl":
        lgs={"nfl":"football/nfl"}
    else:
        lgs={"eng.1":"soccer/eng.1","esp.1":"soccer/esp.1","ita.1":"soccer/ita.1","ger.1":"soccer/ger.1","fra.1":"soccer/fra.1","usa.1":"soccer/usa.1","uefa.champions":"soccer/uefa.champions"}
    meta={"updated":now,"leagues":{}}
    for k,p in lgs.items():
        if sport=="nfl": b=get(f"https://site.api.espn.com/apis/site/v2/sports/{p}/scoreboard")
        else:
            b={"events":[]}
            for i in range(8):
                dd=(datetime.date.today()+datetime.timedelta(days=i)).strftime("%Y%m%d")
                x=get(f"https://site.api.espn.com/apis/site/v2/sports/{p}/scoreboard?dates={dd}") or {}
                b["events"]+=x.get("events",[]); b.setdefault("leagues",x.get("leagues")); b.setdefault("season",x.get("season"))
        n=get(f"https://site.api.espn.com/apis/site/v2/sports/{p}/news?limit=30")
        s=get(f"https://site.api.espn.com/apis/v2/sports/{p}/standings")
        d={"updated":now,"games":slim_board(b),"news":slim_news(n),"standings":slim_stand(s),
           "season":((b or {}).get("season") or {}).get("year"),"week":((b or {}).get("week") or {}).get("number"),
           "league":((b or {}).get("leagues") or [{}])[0].get("name")}
        if d["games"] or d["standings"]:
            json.dump(d,open(f"data/{k}.json","w"),separators=(",",":")); meta["leagues"][k]={"name":d["league"],"games":len(d["games"])}
    json.dump(meta,open("data/meta.json","w"))
if __name__=="__main__": main(sys.argv[1])
