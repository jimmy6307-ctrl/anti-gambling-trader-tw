#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""凍結假說：強趨勢中的短線拉回，09:35 出現回穩才進。

規則在看本輪結果前固定：
- 前一日收盤 > MA60。
- 前20交易日報酬 > +5%（中期強勢）。
- 最近3交易日報酬介於 -6% ~ -1%（不是追高，等拉回）。
- 09:35 價格 >= 當日開盤（開盤後沒有繼續殺低）。
- 09:35 RVOL > 1.2。
- 固定持有5日；round-trip 成本 0.685%。
- IS 2024-03-01~2025-03-31；OOS 2025-04-01~2026-04-01。
- IS 至少40筆、平均>0、PF>1.2 才准進 OOS。
- OOS 也需至少40筆、平均>0、PF>1.2；移除最大貢獻股票後仍平均>0、PF>1.2；正報酬月份>=50%。
"""
from __future__ import annotations
import math
from pathlib import Path
import pandas as pd
import tw_breakout_oos_research as base

OUT=Path('research_output/tw_trend_pullback_recovery')

def pf(s):
    p=float(s[s>0].sum()); n=float(-s[s<0].sum())
    return p/n if n>0 else (float('inf') if p>0 else math.nan)

def metrics(d):
    s=d['net'].dropna()
    return {'trades':len(s),'win_rate':float((s>0).mean()) if len(s) else math.nan,'avg_net':float(s.mean()) if len(s) else math.nan,'median_net':float(s.median()) if len(s) else math.nan,'pf':pf(s) if len(s) else math.nan}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    allf=[]; bm={}
    for sid,ind in base.UNIVERSE:
        try: b=base.download(sid)
        except Exception as e: print('SKIP',sid,e); continue
        bm[sid]=b; x=base.features(b,ind)
        x['ret20_prev']=x['prev_close']/x['close'].shift(21)-1
        x['ret3_prev']=x['prev_close']/x['close'].shift(4)-1
        allf.append(x)
    f=pd.concat(allf,ignore_index=True).dropna(subset=['prev_close','ma60','ret20_prev','ret3_prev','rvol935','open','p935'])
    mask=(f['prev_close']>f['ma60'])&(f['ret20_prev']>.05)&f['ret3_prev'].between(-.06,-.01)&(f['p935']>=f['open'])&(f['rvol935']>1.2)
    rows=[]
    for _,r in f[mask].iterrows():
        period='IS' if base.IS_START.normalize()<=r['date']<=base.IS_END.normalize() else ('OOS' if base.OOS_START.normalize()<=r['date']<=base.OOS_END.normalize() else None)
        if not period: continue
        sid=str(r['stock_id']); gross=base.fixed_return(bm[sid],r['date'],float(r['p935']),5)
        if gross is None: continue
        rows.append({'period':period,'date':r['date'].date().isoformat(),'stock_id':sid,'industry':r['industry'],'ret20_prev':r['ret20_prev'],'ret3_prev':r['ret3_prev'],'rvol935':r['rvol935'],'gross':gross,'net':gross-base.COST})
    t=pd.DataFrame(rows); t.to_csv(OUT/'trades.csv',index=False,encoding='utf-8-sig')
    im=metrics(t[t.period=='IS']); ispass=im['trades']>=40 and im['avg_net']>0 and im['pf']>1.2
    om={}; dm={}; top=''; mshare=math.nan; confirmed=False
    if ispass:
        o=t[t.period=='OOS'].copy(); om=metrics(o)
        c=o.groupby('stock_id')['net'].sum().sort_values(ascending=False); top=str(c.index[0]) if len(c) else ''
        dm=metrics(o[o.stock_id!=top]) if top else om
        if len(o):
            o['month']=pd.to_datetime(o['date']).dt.to_period('M'); mm=o.groupby('month')['net'].mean(); mshare=float((mm>0).mean())
        confirmed=om.get('trades',0)>=40 and om.get('avg_net',-1)>0 and om.get('pf',0)>1.2 and dm.get('avg_net',-1)>0 and dm.get('pf',0)>1.2 and mshare>=.5
    lines=['# 強趨勢拉回後 09:35 回穩','',f'IS：{im}',f'IS_PASS={ispass}']
    if ispass: lines += [f'OOS：{om}',f'移除最大貢獻股票 {top}：{dm}',f'OOS正報酬月份占比={mshare:.1%}',f'CONFIRMED={confirmed}']
    else: lines += ['未通過 IS；不使用 OOS 結果做策略宣稱。','CONFIRMED=False']
    report='\n'.join(lines); (OUT/'report.md').write_text(report,encoding='utf-8'); print(report)
if __name__=='__main__': main()
