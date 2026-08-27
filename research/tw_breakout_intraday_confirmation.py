#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三階段：測試『突破必須由開盤後買盤確認，而不是只靠跳空』。

凍結假說（看結果前固定）：
- 沿用 09:35、20日新高、prev_close>MA20>MA60、RVOL>1.5。
- 產業前3、同產業至少2檔上漲、突破前高延伸<=2%。
- 開盤跳空不超過 +1.5%，避免直接追過度跳空。
- 09:35 價格至少比開盤再漲 +0.5%，要求開盤後仍有主動買盤。
- 固定持有 5 日；成本 0.685%。
- IS 2024-03-01~2025-03-31；OOS 2025-04-01~2026-04-01。
- IS 至少30筆、平均>0、PF>1.2 才准進 OOS；否則直接淘汰。
- OOS 通過後還要移除最大貢獻股票，且正報酬月份占比>=50%。
"""
from __future__ import annotations

import math
from pathlib import Path
import pandas as pd
import tw_breakout_oos_research as base

OUT = Path("research_output/tw_breakout_intraday_confirmation")


def pf(s: pd.Series) -> float:
    pos=float(s[s>0].sum()); neg=float(-s[s<0].sum())
    return pos/neg if neg>0 else (float("inf") if pos>0 else math.nan)


def metrics(df: pd.DataFrame) -> dict:
    s=df["net"].dropna()
    return {"trades":len(s),"win_rate":float((s>0).mean()) if len(s) else math.nan,
            "avg_net":float(s.mean()) if len(s) else math.nan,
            "median_net":float(s.median()) if len(s) else math.nan,"pf":pf(s) if len(s) else math.nan}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parts=[]; bars_map={}
    for sid,ind in base.UNIVERSE:
        try: b=base.download(sid)
        except Exception as e:
            print("SKIP",sid,e); continue
        bars_map[sid]=b; parts.append(base.features(b,ind))
    f=pd.concat(parts,ignore_index=True).dropna(subset=["ret935","rvol935","ma20","ma60","high20","open"])
    sec=(f.groupby(["date","industry"]).agg(sector_ret=("ret935","mean"),breadth=("ret935",lambda s:int((s>0).sum()))).reset_index())
    sec["sector_rank"]=sec.groupby("date")["sector_ret"].rank(ascending=False,method="first")
    f=f.merge(sec,on=["date","industry"],how="left")
    f["gap"]=f["open"]/f["prev_close"]-1
    f["open_to_935"]=f["p935"]/f["open"]-1
    mask=(f["trend"] & f["break20"] & (f["rvol935"]>1.5) & (f["sector_rank"]<=3) &
          (f["breadth"]>=2) & (f["ext20"]<=.02) & (f["gap"]<=.015) & (f["open_to_935"]>=.005))
    trades=[]
    for _,r in f[mask].iterrows():
        period="IS" if base.IS_START.normalize()<=r["date"]<=base.IS_END.normalize() else ("OOS" if base.OOS_START.normalize()<=r["date"]<=base.OOS_END.normalize() else None)
        if not period: continue
        sid=str(r["stock_id"]); gross=base.fixed_return(bars_map[sid],r["date"],float(r["p935"]),5)
        if gross is None: continue
        trades.append({"period":period,"date":r["date"].date().isoformat(),"stock_id":sid,"industry":r["industry"],"gap":r["gap"],"open_to_935":r["open_to_935"],"gross":gross,"net":gross-base.COST})
    t=pd.DataFrame(trades); t.to_csv(OUT/"trades.csv",index=False,encoding="utf-8-sig")
    im=metrics(t[t.period=="IS"]); om=metrics(t[t.period=="OOS"])
    is_pass=im["trades"]>=30 and im["avg_net"]>0 and im["pf"]>1.2
    confirmed=False; dm={}; month_share=math.nan; top=""
    if is_pass:
        o=t[t.period=="OOS"].copy(); contrib=o.groupby("stock_id")["net"].sum().sort_values(ascending=False)
        top=str(contrib.index[0]) if len(contrib) else ""; dm=metrics(o[o.stock_id!=top]) if top else om
        if len(o):
            o["month"]=pd.to_datetime(o["date"]).dt.to_period("M"); mm=o.groupby("month")["net"].mean(); month_share=float((mm>0).mean())
        confirmed=(om["trades"]>=30 and om["avg_net"]>0 and om["pf"]>1.2 and dm.get("avg_net",-1)>0 and dm.get("pf",0)>1.2 and month_share>=.5)
    lines=["# 開盤後買盤確認的第一次突破", "", "固定規則：20日新高 + 多頭排列 + RVOL>1.5 + 產業共振 + 延伸<=2% + 跳空<=1.5% + 開盤至09:35再漲>=0.5%，持有5日。", "", f"IS：{im}", f"IS_PASS={is_pass}"]
    if is_pass: lines += [f"OOS：{om}",f"移除最大貢獻股票 {top}：{dm}",f"OOS正報酬月份占比={month_share:.1%}",f"CONFIRMED={confirmed}"]
    else: lines += ["未通過 IS，依預先規則不使用 OOS 結果做策略宣稱。", "CONFIRMED=False"]
    report="\n".join(lines); (OUT/"report.md").write_text(report,encoding="utf-8"); print(report)

if __name__=="__main__": main()
