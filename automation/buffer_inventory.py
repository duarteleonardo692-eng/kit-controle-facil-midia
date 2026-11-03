#!/usr/bin/env python3
"""Inventário somente leitura para decidir quais vídeos já estão no Buffer."""
import os
from buffer_publish import locate_channels, fetch_posts
def main():
    token=os.environ.get("BUFFER_API_KEY","")
    if not token:
        raise RuntimeError("BUFFER_API_KEY ausente")
    chans=locate_channels(token)
    for service, info in chans.items():
        print("=== CANAL:",service,"===")
        posts=fetch_posts(token, info["org_id"], info["id"])
        print("TOTAL:",len(posts))
        for p in posts:
            text=" ".join((p.get("text") or "").split())[:200]
            assets=[(x or {}).get("source","") for x in p.get("assets") or []]
            print("POST",p.get("id"),"STATUS",p.get("status"),"TEXT",text,"ASSETS",str(assets)[:400])
if __name__=="__main__":
    main()
