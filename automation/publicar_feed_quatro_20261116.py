#!/usr/bin/env python3
"""Publicar 3 posts educativos e 1 convite de afiliados, somente Instagram/Facebook.
Usa o Buffer API secret existente no GitHub Actions. Reconciliacao impede duplicatas.
"""
import hashlib, json, os, subprocess, sys, time
import urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from buffer_publicar_dupla_07nov import channels
from buffer_publish import query_graphql, gql_string, fetch_posts, is_duplicate

REPO="duarteleonardo692-eng/kit-controle-facil-midia"
SITE="https://kit-controle-facil-site.pages.dev/"
LOJA="https://kit-controle-facil-site.pages.dev/loja/"
AFILIADO="https://orbita.eduzz.com/affiliate/invite/3142098"
REPORT=Path("reports/feed-quatro-20261116-buffer.json")
SERVICES=("facebook","instagram")
ITEMS=[
  {
    "slug":"01_vendas","topic":"Vendas e caixa","marker":"#CFVendasFeed16Nov26",
    "file":"assets/kit-post-01_vendas-20261116.jpg",
    "caption":"📊 Você sabe quanto vendeu hoje, sem depender da memória?\n\nRegistre as vendas e acompanhe o caixa com mais clareza usando a planilha Kit Controle Fácil Excel. Conheça as demonstrações e veja como ela pode ajudar na rotina do seu negócio.\n\n🌐 Site: "+SITE+"\n🛍️ Conheça nossa loja: "+LOJA+"\nNo Instagram, acesse o link do perfil.\n\n#KitControleFacil #Vendas #ControleDeCaixa #PequenosNegocios #CFVendasFeed16Nov26",
  },
  {
    "slug":"02_estoque","topic":"Organizacao de estoque","marker":"#CFEstoqueFeed16Nov26",
    "file":"assets/kit-post-02_estoque-20261116.jpg",
    "caption":"📦 Produto acabando e você só percebe na hora da venda?\n\nAcompanhar quantidades e movimentações faz diferença. O Kit Controle Fácil Excel ajuda a organizar o estoque e identificar o que precisa de atenção para repor.\n\n🌐 Explore o site: "+SITE+"\n🛍️ Veja nossa loja: "+LOJA+"\nNo Instagram, os links estão no perfil.\n\n#KitControleFacil #Estoque #GestaoSimples #Empreendedorismo #CFEstoqueFeed16Nov26",
  },
  {
    "slug":"03_despesas","topic":"Despesas e fluxo do negocio","marker":"#CFDespesasFeed16Nov26",
    "file":"assets/kit-post-03_despesas-20261116.jpg",
    "caption":"💸 Vender é importante. Mas você sabe para onde vai o dinheiro?\n\nOrganize despesas, acompanhe entradas e saídas e entenda melhor os números do negócio com o Kit Controle Fácil Excel. Veja as prévias e escolha com informação.\n\n🌐 Conheça o site: "+SITE+"\n🛍️ Visite nossa loja: "+LOJA+"\nNo Instagram, acesse o link do perfil.\n\n#KitControleFacil #Despesas #OrganizacaoFinanceira #PequenosNegocios #CFDespesasFeed16Nov26",
  },
  {
    "slug":"04_afiliados","topic":"Convite para afiliados","marker":"#CFAfiliadosFeed16Nov26",
    "file":"assets/kit-post-04_afiliados-20261116.jpg",
    "caption":"🤝 Quer divulgar uma solução digital voltada a pequenos negócios?\n\nConheça a oportunidade de ser afiliado do Kit Controle Fácil Excel. Acesse o convite oficial para verificar cadastro, regras e condições de comissão antes de participar.\n\n🔗 Convite de afiliados: "+AFILIADO+"\n🌐 Conheça o produto: "+SITE+"\n🛍️ Visite nossa loja: "+LOJA+"\nNo Instagram, procure o convite no nosso site ou no link do perfil.\n\n#KitControleFacil #Afiliados #MarketingDeAfiliados #RendaExtra #CFAfiliadosFeed16Nov26",
  },
]
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*256),b""):h.update(part)
    return h.hexdigest()
def checkpoint(data):
    data["updated_at"]=datetime.now(timezone.utc).isoformat()
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    subprocess.run(["git","add",str(REPORT)],check=True)
    if subprocess.run(["git","diff","--cached","--quiet"]).returncode:
        subprocess.run(["git","commit","-m","Registrar resultado da campanha de 4 posts no Buffer"],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(["git","pull","--rebase","origin","main"],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(["git","push","origin","HEAD:main"],check=True,stdout=subprocess.DEVNULL)
def public_link(item):
    path=Path(item["file"])
    assert path.is_file() and path.stat().st_size>15000 and path.read_bytes()[:3]==b"\xff\xd8\xff"
    url="https://raw.githubusercontent.com/"+REPO+"/main/"+item["file"]
    for _ in range(14):
        try:
            req=urllib.request.Request(url,headers={"Range":"bytes=0-7","User-Agent":"KitControleFacilSocial/1.0"})
            with urllib.request.urlopen(req,timeout=25) as r:
                if r.status in (200,206) and r.read(3)==b"\xff\xd8\xff":return url
        except (urllib.error.URLError,TimeoutError,OSError):pass
        time.sleep(6)
    raise RuntimeError("Arte indisponivel publicamente no GitHub: "+path.name)
def create_post(token, channel_id, item, url, due_at):
    schedule=(" mode: shareNow " if due_at is None else
              " mode: customScheduled dueAt: "+gql_string(due_at)+" ")
    q=("mutation { createPost(input: { text: "+gql_string(item["caption"])+
       " channelId: "+gql_string(channel_id)+
       " schedulingType: automatic "+schedule+
       " assets: [{ image: { url: "+gql_string(url)+" } }]"+
       " }) { __typename ... on PostActionSuccess { post { id dueAt status } }"+
       " ... on MutationError { message } } }")
    r=query_graphql(q,token).get("createPost") or {}
    if r.get("__typename")!="PostActionSuccess" or not (r.get("post") or {}).get("id"):
        raise RuntimeError("Buffer recusou post: "+str(r.get("message") or r))
    return r["post"]
def main():
    token=os.getenv("BUFFER_API_KEY","").strip()
    if not token:raise RuntimeError("BUFFER_API_KEY ausente; nada publicado")
    found=channels(token)
    if any(x not in found for x in SERVICES):raise RuntimeError("Facebook e Instagram do Kit nao confirmados no Buffer")
    for it in ITEMS:
        assert it["marker"] in it["caption"] and SITE in it["caption"] and LOJA in it["caption"]
    urls={it["slug"]:public_link(it) for it in ITEMS}
    history={s:fetch_posts(token,found[s]["org_id"],found[s]["id"]) for s in SERVICES}
    if REPORT.exists():report=json.loads(REPORT.read_text(encoding="utf-8"))
    else:report={"campaign":"Kit 4 posts 2026-11-16","channels":list(SERVICES),"posts":{}}
    base=datetime.now(timezone.utc)+timedelta(minutes=12)
    failed=False
    for i,it in enumerate(ITEMS):
        post=report["posts"].setdefault(it["slug"],{
            "topic":it["topic"],"marker":it["marker"],"file":it["file"],
            "sha256":sha(it["file"]),"media_url":urls[it["slug"]],
            "caption":it["caption"],"destinations":{}
        })
        if post["sha256"]!=sha(it["file"]):raise RuntimeError("Arte alterada apos o registro: "+it["slug"])
        for service in SERVICES:
            matches=[p for p in history[service] if is_duplicate(p,it)]
            if len(matches)>1:
                failed=True;print("DUPLICATA NO BUFFER",it["slug"],service,flush=True);continue
            if matches:
                post["destinations"][service]={"id":matches[0].get("id"),"status":matches[0].get("status"),"origin":"existing"}
                checkpoint(report);print("JA_EXISTE",it["slug"],service,flush=True);continue
            if service in post["destinations"]:
                print("NAO_REENVIAR_ESTADO_INCERTO",it["slug"],service,flush=True);failed=True;continue
            due=None if i==0 else (base+timedelta(minutes=(i-1)*10)).isoformat(timespec="milliseconds").replace("+00:00","Z")
            post["destinations"][service]={"status":"request_started","requested_due_at":due}
            checkpoint(report)
            try:
                res=create_post(token,found[service]["id"],it,urls[it["slug"]],due)
                post["destinations"][service]={"id":res["id"],"status":res.get("status"),"due_at":res.get("dueAt"),"requested_due_at":due,"origin":"created"}
                history[service].append({"id":res["id"],"text":it["caption"],"status":res.get("status"),"assets":[{"source":urls[it["slug"]]}]})
                print("ACEITO_BUFFER",it["slug"],service,res,flush=True)
            except Exception as e:
                failed=True
                post["destinations"][service]={"status":"submission_error","detail":str(e)[:550],"reconciliation_required":True}
                print("ERRO",it["slug"],service,str(e)[:250],flush=True)
            checkpoint(report)
    print("RELATORIO",REPORT,flush=True)
    if failed:sys.exit("Uma ou mais publicacoes exigem verificacao; sem repostagem automatica.")
if __name__=="__main__":main()
