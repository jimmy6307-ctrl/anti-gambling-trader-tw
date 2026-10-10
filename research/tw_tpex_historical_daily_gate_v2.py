#!/usr/bin/env python3
"""Official TPEx historical daily data-quality probe; NO strategy backtest.
All results are quarantined. No point-in-time common-stock universe or minute bars.
"""
import argparse, csv, hashlib, html, io, json, math, re, time
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import requests

URL="https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php"
DATES=("2024-08-05","2025-10-01","2026-03-31","2026-10-07")
FIELDS=("date","stock_id","name","open","high","low","close","volume_shares","turnover_twd","trades","source")
NEEDED=("代號","名稱","收盤","開盤","最高","最低","成交股數","成交金額","成交筆數")
def clean(s):
    return re.sub(r"[\s\u3000\ufeff]+","",html.unescape(str(s))).replace("(元)","").replace("（元）","")
def number(s):
    x=clean(s).replace(",","")
    if x in ("","-","--","---","----","—","N/A"): raise ValueError("missing number")
    v=float(x)
    if not math.isfinite(v): raise ValueError("nonfinite number")
    return v
class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None;self.depth=0
    def handle_starttag(self,tag,attrs):
        if tag=="table":
            self.depth+=1
            if self.depth==1:self.table=[]
        elif self.depth==1 and tag=="tr":self.row=[]
        elif self.depth==1 and tag in ("td","th") and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if self.depth==1 and tag in ("td","th") and self.cell is not None:
            self.row.append("".join(self.cell));self.cell=None
        elif self.depth==1 and tag=="tr" and self.row is not None:
            self.table.append(self.row);self.row=None
        elif tag=="table" and self.depth:
            if self.depth==1:self.tables.append(self.table);self.table=None
            self.depth-=1
def parse(raw, expected):
    s=None
    for enc in ("utf-8-sig","big5","cp950"):
        try:s=raw.decode(enc);break
        except UnicodeDecodeError:pass
    if s is None:raise ValueError("unknown encoding")
    d=date.fromisoformat(expected);roc=d.year-1911
    patterns=[rf"(?<!\d){yr}\s*[年/.-]\s*0?{d.month}\s*[月/.-]\s*0?{d.day}\s*日?" for yr in (roc,d.year)]
    if not any(re.search(p,s) for p in patterns):raise ValueError("requested trading date missing from response")
    p=Tables();p.feed(s)
    tables=p.tables if "<table" in s.lower() else [list(csv.reader(io.StringIO(s)))]
    matched=[]
    for t in tables:
        for i,row in enumerate(t):
            labels=[clean(x) for x in row];ix={}
            for key in NEEDED:
                positions=[j for j,x in enumerate(labels) if x==key]
                if len(positions)==1:ix[key]=positions[0]
            if len(ix)==len(NEEDED):matched.append((t[i+1:],ix))
    if len(matched)!=1:raise ValueError(f"OHLC table missing or ambiguous: {len(matched)}")
    rows,ix=matched[0];seen=set();out=[];skipped={"other_code":0,"no_trade":0,"short_row":0}
    for row in rows:
        if len(row)<=max(ix.values()):skipped["short_row"]+=1;continue
        sid=clean(row[ix["代號"]])
        if not re.fullmatch(r"[1-9]\d{3}",sid):skipped["other_code"]+=1;continue
        if sid in seen:raise ValueError("duplicate code "+sid)
        seen.add(sid)
        try:
            op,hi,lo,cl=[number(row[ix[k]]) for k in ("開盤","最高","最低","收盤")]
            vol,val,n=[number(row[ix[k]]) for k in ("成交股數","成交金額","成交筆數")]
        except ValueError as e:
            if str(e)=="missing number":skipped["no_trade"]+=1;continue
            raise
        if not (0<lo<=min(op,cl)<=max(op,cl)<=hi and vol>0 and val>0 and n>0):
            raise ValueError("impossible OHLC/activity "+sid)
        if not all(float(v).is_integer() for v in (vol,val,n)):raise ValueError("noninteger activity "+sid)
        out.append(dict(date=expected,stock_id=sid,name=clean(row[ix["名稱"]]),open=op,high=hi,low=lo,
            close=cl,volume_shares=int(vol),turnover_twd=int(val),trades=int(n),source=URL))
    if not out:raise ValueError("zero valid securities")
    return sorted(out,key=lambda x:x["stock_id"]),skipped
def main():
    a=argparse.ArgumentParser();a.add_argument("--dates",nargs="+",default=list(DATES))
    a.add_argument("--out",type=Path,default=Path("research_output/tw_tpex_historical_daily_gate"))
    a.add_argument("--min-rows",type=int,default=500);args=a.parse_args()
    rawdir=args.out/"raw";rawdir.mkdir(parents=True,exist_ok=True)
    manifest={"source":URL,"requested_dates":args.dates,"status":"BLOCKED","strategy_gate":"BLOCKED",
        "holdout_quarantined":True,"dates":[],"errors":[]}
    allrows=[];session=requests.Session()
    for target in args.dates:
        try:
            d=date.fromisoformat(target);roc=f"{d.year-1911}/{d.month:02d}/{d.day:02d}"
            failures=[]
            for fmt in ("csv","htm"):
                try:
                    stamp=datetime.now(timezone.utc).isoformat()
                    resp=session.get(URL,params={"d":roc,"l":"zh-tw","o":fmt,"se":"EW"},
                        timeout=45,headers={"User-Agent":"TPEx-official-daily-QA/1.0"})
                    resp.raise_for_status()
                    raw=resp.content;(rawdir/f"{target}_{fmt}.bin").write_bytes(raw)
                    parsed,skips=parse(raw,target)
                    if len(parsed)<args.min_rows:raise ValueError(f"only {len(parsed)} rows")
                    allrows+=parsed
                    manifest["dates"].append(dict(date=target,format=fmt,retrieved_utc=stamp,
                        url=resp.url,raw_sha256=hashlib.sha256(raw).hexdigest(),rows=len(parsed),
                        skipped=skips,status="PASS_OFFICIAL_DAILY_ONLY"))
                    print(f"PASS {target} {len(parsed)} official daily rows",flush=True)
                    break
                except Exception as e:failures.append(f"{fmt}: {type(e).__name__}: {str(e)[:160]}")
            else:raise RuntimeError("; ".join(failures))
        except Exception as e:
            manifest["errors"].append(f"{target}: {type(e).__name__}: {str(e)[:350]}")
            print("BLOCKED "+manifest["errors"][-1],flush=True)
        time.sleep(.5)
    with (args.out/"daily_snapshot.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(allrows)
    if len(manifest["dates"])==len(args.dates) and not manifest["errors"]:
        manifest["status"]="PASS_TPEX_DAILY_ONLY"
    (args.out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (args.out/"report.md").write_text("# TPEx historical official daily quality gate\n\n"
        +f"Status: {manifest['status']}; {len(manifest['dates'])}/{len(args.dates)} dates; {len(allrows)} rows.\n"
        +"Only official daily data. No independent minute/tick, corporate actions, point-in-time universe, fills or clean OOS. No strategy certification.\n"
        +"\n".join(manifest["errors"])+"\n",encoding="utf-8")
    return 0 if manifest["status"].startswith("PASS") else 2
if __name__=="__main__":raise SystemExit(main())
