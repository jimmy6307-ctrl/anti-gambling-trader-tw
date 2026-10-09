#!/usr/bin/env python3
"""Quarantined TPEx official daily-vs-monthly OHLC crosscheck; NOT minute/tick validation."""
import argparse, csv, hashlib, json, re, time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import requests

URL="https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"
STOCKS=("3105","5347","6488","8069","8299")
FIELDS=("open","high","low","close")

def number(v):
    s=re.sub(r"<[^>]*>","",str(v)).strip().replace(",","")
    if s in ("","-","--","---","N/A","—"): raise ValueError("missing number")
    n=Decimal(s)
    if not n.is_finite(): raise ValueError("nonfinite")
    return n

def parse_monthly(raw, day, sid):
    obj=json.loads(raw.decode("utf-8-sig"))
    if not isinstance(obj,dict) or not isinstance(obj.get("aaData"),list):
        raise ValueError("aaData list missing")
    if obj.get("stkNo") and str(obj["stkNo"])!=sid: raise ValueError("wrong stock")
    d=date.fromisoformat(day)
    target=(d.year-1911,d.month,d.day)
    matches=[]
    for row in obj["aaData"]:
        if not isinstance(row,list) or len(row)<7: raise ValueError("monthly row schema drift")
        try: parts=tuple(int(x) for x in str(row[0]).strip().split("/"))
        except ValueError as exc: raise ValueError("bad date") from exc
        if len(parts)!=3: raise ValueError("bad date")
        if parts==target:
            x=dict(zip(FIELDS,(number(row[i]) for i in (3,4,5,6))))
            if not (0<x["low"]<=min(x["open"],x["close"])<=max(x["open"],x["close"])<=x["high"]):
                raise ValueError("invalid OHLC")
            matches.append(x)
    if len(matches)!=1: raise ValueError(f"exact dated row count {len(matches)}")
    return matches[0]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--daily-csv",type=Path,default=Path("research_output/tw_tpex_historical_daily_gate/daily_snapshot.csv"))
    p.add_argument("--out",type=Path,default=Path("research_output/tw_tpex_individual_anchor_gate"))
    p.add_argument("--date",default="2026-10-07")
    p.add_argument("--stocks",nargs="+",default=list(STOCKS))
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rawdir=a.out/"raw";rawdir.mkdir(exist_ok=True)
    manifest={"status":"BLOCKED","strategy_gate":"BLOCKED","holdout_quarantined":True,
              "date":a.date,"stocks":a.stocks,"source":URL,"anchors":[],"errors":[]}
    try:
        with a.daily_csv.open(encoding="utf-8-sig",newline="") as f:
            daily={(r["date"],r["stock_id"]):r for r in csv.DictReader(f)}
    except Exception as e:
        daily={};manifest["errors"].append(f"daily source missing: {e}")
    d=date.fromisoformat(a.date);month=f"{d.year-1911}/{d.month:02d}"
    for sid in a.stocks:
        try:
            if (a.date,sid) not in daily: raise ValueError("not in official daily snapshot")
            fetched=datetime.now(timezone.utc).isoformat()
            r=requests.get(URL,params={"l":"zh-tw","d":month,"stkno":sid},
                           timeout=30,headers={"User-Agent":"TPEx-official-QA/1.0"})
            r.raise_for_status();raw=r.content
            (rawdir/f"{a.date}_{sid}.json").write_bytes(raw)
            got=parse_monthly(raw,a.date,sid)
            expected={k:number(daily[(a.date,sid)][k]) for k in FIELDS}
            mismatch={k:[str(expected[k]),str(got[k])] for k in FIELDS if expected[k]!=got[k]}
            if mismatch: raise ValueError(f"OHLC mismatch {mismatch}")
            manifest["anchors"].append({"stock_id":sid,"date":a.date,"retrieved_utc":fetched,
                "raw_sha256":hashlib.sha256(raw).hexdigest(),"url":r.url,
                "ohlc":{k:str(got[k]) for k in FIELDS},"status":"PASS_OFFICIAL_DAILY_ONLY"})
            print(f"PASS {sid} {a.date} daily-vs-monthly OHLC",flush=True)
        except Exception as e:
            err=f"{sid}: {type(e).__name__}: {str(e)[:200]}"
            manifest["errors"].append(err);print("BLOCKED "+err,flush=True)
        time.sleep(0.3)
    if len(a.stocks)>=5 and len(manifest["anchors"])==len(a.stocks) and not manifest["errors"]:
        manifest["status"]="PASS_FIVE_OFFICIAL_DAILY_ANCHORS_ONLY"
    (a.out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (a.out/"report.md").write_text(
        "# TPEx individual-stock daily official anchor gate\n\n"
        +f"Status: **{manifest['status']}**. {len(manifest['anchors'])}/{len(a.stocks)} matches.\n\n"
        +"Two official TPEx daily-price reports, NOT independent intraday/tick data. "
        +"No validated closing auction, fills, corporate actions, PIT universe, or clean OOS.\n\n"
        +"\n".join(manifest["errors"])+"\n",encoding="utf-8")
    return 0 if manifest["status"].startswith("PASS") else 2

if __name__=="__main__": raise SystemExit(main())
