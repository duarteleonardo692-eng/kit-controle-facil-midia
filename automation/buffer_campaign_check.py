#!/usr/bin/env python3
"""Auditoria somente leitura dos posts desta campanha por IDs persistidos."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from buffer_publish import EXPECTED_CHANNELS, gql_string, locate_channels, query_graphql


def all_posts(token, org_id, channel_id):
    posts, cursor = [], None
    for _ in range(100):
        after=", after: "+gql_string(cursor) if cursor else ""
        q=("query { posts(first: 50"+after+", input: { organizationId: "+
           gql_string(org_id)+", filter: { status: [sent, scheduled, sending, draft, needs_approval, error], channelIds: ["+
           gql_string(channel_id)+"] } }) { pageInfo { hasNextPage endCursor } "+
           "edges { node { id status dueAt sentAt externalLink schedulingType } } } }")
        data=query_graphql(q,token).get("posts") or {}
        posts.extend(x["node"] for x in data.get("edges") or [] if x.get("node"))
        page=data.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return {str(p["id"]): p for p in posts}
        nxt=page.get("endCursor")
        if not nxt or nxt==cursor:
            raise RuntimeError("Histórico Buffer incompleto.")
        cursor=nxt
    raise RuntimeError("Histórico grande demais para auditoria.")


def parse_date(value):
    if not value: return None
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None: raise RuntimeError("Data sem fuso")
    return dt.astimezone(timezone.utc)


def main():
    token=os.environ.get("BUFFER_API_KEY","")
    if not token: raise RuntimeError("Secret BUFFER_API_KEY ausente.")
    state=json.loads(Path("automation/campanha-03nov-state.json").read_text(encoding="utf8"))
    ledger=state.get("records",{})
    channels=locate_channels(token)
    history={name:all_posts(token,info["org_id"],info["id"]) for name,info in channels.items()}
    errors=[]
    waiting=sent=0
    now=datetime.now(timezone.utc)
    for key, saved in ledger.items():
        slug,network=key.rsplit(":",1)
        if network not in EXPECTED_CHANNELS:
            raise RuntimeError("Canal inesperado no ledger.")
        post=history[network].get(saved["id"])
        if not post:
            errors.append(key+": desapareceu do histórico Buffer.")
            continue
        status=str(post.get("status") or "").lower()
        due=parse_date(post.get("dueAt") or saved.get("dueAt"))
        if post.get("schedulingType") and post["schedulingType"]!="automatic":
            errors.append(key+": exige intervenção manual (notificação).")
        elif status=="sent":
            sent+=1
            print("PUBLICADO:",key,"|",post.get("externalLink") or "sem URL pública")
        elif status=="error" or (due and now>due+timedelta(hours=2)):
            errors.append(key+": "+status+" fora do prazo.")
        else:
            waiting+=1
            print("AGUARDANDO:",key,"|",status,"|",due.isoformat() if due else "")
    print("RESUMO: publicados",sent,"agendados/pendentes",waiting,"erros",len(errors))
    if errors:
        for message in errors: print("FALHA:",message)
        raise RuntimeError("Publicações pendentes com falha; conferir Buffer.")
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf8") as f:
            f.write("\n### Campanha de 10 minutos\n\nPublicados: "+
                    str(sent)+"; pendentes: "+str(waiting)+
                    "; falhas: 0. Nenhum post foi reenviado.\n")
    return 0


if __name__=="__main__":
    try: sys.exit(main())
    except (RuntimeError,ValueError,KeyError,OSError) as exc:
        print("AUDITORIA CAMPANHA FALHOU:",str(exc),file=sys.stderr)
        sys.exit(1)
