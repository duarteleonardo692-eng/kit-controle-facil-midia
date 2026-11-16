#!/usr/bin/env python3
"""Publish only the three latest photo commercials, once per authorized channel."""
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from buffer_publicar_dupla_07nov import channels, validate_video, create_post
from buffer_publish import is_duplicate
from buffer_audit import fetch_detailed_posts

SERVICES=('facebook','instagram','tiktok')
REPORT=Path('reports/tres-fotos-20261116-buffer.json')
MANIFEST=Path('automation/tres-fotos-20261116.json')

def save(report,checkpoint=False):
    report['checked_at']=datetime.now(timezone.utc).isoformat()
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if checkpoint:
        subprocess.run(['git','add',str(REPORT)],check=True)
        subprocess.run(['git','commit','-m','Registrar tentativa e estado dos tres comerciais com fotos'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['git','pull','--rebase','origin','main'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['git','push','origin','HEAD:main'],check=True,stdout=subprocess.DEVNULL)

def summary(post):
    return {k:post.get(k) for k in ('id','status','dueAt','sentAt','externalLink')}

def main():
    token=os.environ.get('BUFFER_API_KEY','').strip()
    if not token: raise RuntimeError('BUFFER_API_KEY absent; nothing submitted')
    items=json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert len(items)==3 and {x['slug'] for x in items}=={'01_padaria','02_oficina','03_florista'}
    found=channels(token)
    if set(found)!=set(SERVICES):raise RuntimeError('Expected exactly the three authorized brand channels')
    history={s:fetch_detailed_posts(token,found[s]['org_id'],found[s]['id']) for s in SERVICES}
    urls={x['slug']:validate_video(x) for x in items}
    for x in items:
        assert x['marker'] in x['caption'] and 'https://kit-controle-facil-site.pages.dev/' in x['caption']
    report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'campaign':'Only latest three photo commercials','mode':'shareNow','videos':{}}
    for x in items:
        row=report['videos'].setdefault(x['slug'],{'title':x['title'],'sha256':x['sha256'],'media_url':urls[x['slug']],'caption':x['caption'],'networks':{}})
        assert row['sha256']==x['sha256']
        for s in SERVICES:
            matches=[p for p in history[s] if is_duplicate(p,x)]
            if len(matches)>1:raise RuntimeError('Multiple matching posts: '+x['slug']+' '+s)
            if matches:
                row['networks'][s]=summary(matches[0]);save(report)
                print('EXISTS',x['slug'],s,json.dumps(row['networks'][s]),flush=True);continue
            if s in row['networks']:
                row['networks'][s]['reconciliation_required']=True;save(report)
                print('NOT_RESENT',x['slug'],s,flush=True);continue
            row['networks'][s]={'status':'request_started'}
            # Durable claim before sending. An uncertain request is never blindly retried.
            save(report,checkpoint=True)
            try:
                result=create_post(token,s,found[s]['id'],x,urls[x['slug']])
                row['networks'][s]=summary(result)
                history[s].append({'id':result['id'],'text':x['caption'],'status':result.get('status'),'assets':[{'source':urls[x['slug']]}]})
            except Exception as exc:
                row['networks'][s]={'status':'submission_error','detail':str(exc),'reconciliation_required':True}
            save(report,checkpoint=True)
            print('RESULT',x['slug'],s,json.dumps(row['networks'][s]),flush=True)
    for attempt in range(32):
        history={s:fetch_detailed_posts(token,found[s]['org_id'],found[s]['id']) for s in SERVICES}
        pending=False
        for x in items:
            for s in SERVICES:
                row=report['videos'][x['slug']]['networks'][s]
                post=next((p for p in history[s] if str(p.get('id'))==str(row.get('id'))),None) if row.get('id') else None
                if post:report['videos'][x['slug']]['networks'][s]=summary(post)
                row=report['videos'][x['slug']]['networks'][s]
                print('CONFIRM',x['slug'],s,json.dumps(row),flush=True)
                if row.get('status') not in ('sent','error','submission_error','request_started'):pending=True
        save(report)
        if not pending:break
        time.sleep(15)
    save(report,checkpoint=True)
    assert all(report['videos'][x['slug']]['networks'][s].get('status')=='sent' for x in items for s in SERVICES),'Some destinations were not confirmed sent; inspect report without reposting'

if __name__=='__main__':main()

