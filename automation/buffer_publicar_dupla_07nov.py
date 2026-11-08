#!/usr/bin/env python3
"""Publish two separately approved Kit Controle Facil commercials, without duplicates."""
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

from buffer_publish import query_graphql, fetch_posts, gql_string, is_duplicate

REPO = "duarteleonardo692-eng/kit-controle-facil-midia"
SITE = "https://kit-controle-facil-site.pages.dev/"
ITEMS = [
    {
        "file": "assets/kit-controle-facil-despesas-sem-sustos-fullhd-20261107.mp4",
        "sha256": "7b729821695f1f90f5d27017e42d3f811920e491d0f5f04e6632e3dea76a05db",
        "marker": "#CFDespesasSemSustos07Nov26",
        "legacy_phrase": "despesas sem sustos",
        "caption": ("💚 Você sabe para onde vai o dinheiro do seu negócio?\n\n"
                    "Com o Kit Controle Fácil para Excel, organize suas despesas e acompanhe seus valores "
                    "com mais clareza. Menos surpresas. Mais controle. 📊\n\n"
                    "Conheça nosso site: " + SITE + "\n\n"
                    "🎬 Demonstração ilustrativa com dados fictícios e recursos de IA.\n\n"
                    "#KitControleFacil #GestaoFinanceira #PequenosNegocios #Empreendedorismo #Despesas "
                    "#CFDespesasSemSustos07Nov26")
    },
    {
        "file": "assets/kit-controle-facil-quanto-entrou-hoje-musica-20261107.mp4",
        "sha256": "064f2bbf7ccbfc8a7bcac6dd72eaa7e86b59aef777a18e4291d5afcc51050419",
        "marker": "#CFQuantoEntrouHoje07Nov26",
        "legacy_phrase": "quanto entrou hoje?",
        "caption": ("🧾 Quanto entrou hoje no caixa?\n\n"
                    "Cada venda conta! Registre as vendas e confira os valores do dia com "
                    "o Kit Controle Fácil para Excel. Mais organização para encerrar o expediente. 💚\n\n"
                    "Conheça nosso site: " + SITE + "\n\n"
                    "🎬 Vídeo demonstrativo com dados ilustrativos.\n\n"
                    "#KitControleFacil #GestaoDeVendas #ControleDeCaixa #PequenosNegocios "
                    "#CFQuantoEntrouHoje07Nov26")
    },
]
EXPECTED = {
    "instagram": "6ae904cfe29c69a1713f2ad8",
    "tiktok": "6ae904e9e29c69a1713f2ba9",
}

def normalize(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "").casefold())
                   if not unicodedata.combining(c)).strip()

def channels(token):
    orgs = (query_graphql("query { account { organizations { id name } } }", token)
            .get("account") or {}).get("organizations") or []
    found = {}
    facebook_candidates = []
    for org in orgs:
        org_id = org["id"]
        q = ("query { channels(input: { organizationId: " + gql_string(org_id) +
             " }) { id name displayName service } }")
        for c in query_graphql(q, token).get("channels") or []:
            service = str(c.get("service", "")).lower()
            if service in EXPECTED and c.get("id") == EXPECTED[service]:
                found[service] = {"id": c["id"], "org_id": org_id}
            if service == "facebook":
                label = normalize(" ".join([str(c.get("name") or ""), str(c.get("displayName") or "")]))
                if "kit controle facil" in label:
                    facebook_candidates.append({"id": c["id"], "org_id": org_id})
    if len(facebook_candidates) == 1:
        found["facebook"] = facebook_candidates[0]
    else:
        print(f"Facebook omitido: {len(facebook_candidates)} canais compatíveis (precisa ser exatamente um).")
    return found



def validate_video(item):
    import hashlib
    path = Path(item["file"])
    if not path.is_file():
        raise RuntimeError("Arquivo nao encontrado no checkout: " + item["file"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item["sha256"]:
        raise RuntimeError("Integridade SHA256 diferente para " + item["file"])
    if path.open("rb").read(12)[4:8] != b"ftyp":
        raise RuntimeError("MP4 invalido: " + item["file"])
    url = "https://raw.githubusercontent.com/" + REPO + "/main/" + item["file"]
    for attempt in range(12):
        try:
            req = urllib.request.Request(url,
                headers={"Range": "bytes=0-31", "User-Agent": "kit-controle-facil-publish-two/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                h = resp.read(16)
                if resp.status in (200,206) and len(h)>=8 and h[4:8] == b"ftyp":
                    return url
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(5)
    raise RuntimeError("MP4 publico indisponivel: " + item["file"])

def create_post(token, service, channel_id, item, url):
    metadata = ""
    if service == "facebook":
        metadata = "metadata: { facebook: { type: reel } }"
    elif service == "instagram":
        metadata = "metadata: { instagram: { type: reel, shouldShareToFeed: true, isAiGenerated: true } }"
    elif service == "tiktok":
        metadata = "metadata: { tiktok: { isAiGenerated: true } }"
    q = ("mutation { createPost(input: { text: " + gql_string(item["caption"]) +
         " channelId: " + gql_string(channel_id) +
         " schedulingType: automatic mode: shareNow " + metadata +
         " assets: [{ video: { url: " + gql_string(url) +
         " } }] }) { __typename ... on PostActionSuccess { post { id dueAt status } } " +
         "... on MutationError { message } } }")
    response = query_graphql(q, token).get("createPost") or {}
    if response.get("__typename") != "PostActionSuccess" or not (response.get("post") or {}).get("id"):
        raise RuntimeError("Buffer recusou " + service + ": " + str(response.get("message",response)))
    return response["post"]

def main():
    token = os.environ.get("BUFFER_API_KEY", "").strip()
    if not token:
        raise RuntimeError("BUFFER_API_KEY ausente. Nenhuma publicacao realizada.")
    found = channels(token)
    if set(found) != {"facebook","instagram","tiktok"}:
        raise RuntimeError("Nem todas as tres redes autorizadas estao disponiveis: " + repr(sorted(found)))
    for item in ITEMS:
        if item["marker"] not in item["caption"] or SITE not in item["caption"]:
            raise RuntimeError("Legenda sem identificador ou link oficial: " + item["file"])
    # Prefetch all histories and verify all MP4s before any writes to Buffer.
    histories = {}
    for service, ch in found.items():
        histories[service] = fetch_posts(token, ch["org_id"], ch["id"])
        print("CANAL: " + service + ", posts analisados: " + str(len(histories[service])))
    links = {item["file"]:validate_video(item) for item in ITEMS}
    errors = []
    for item in ITEMS:
        for service in ("facebook","instagram","tiktok"):
            matches = [p for p in histories[service] if is_duplicate(p,item)]
            if matches:
                print("JA_EXISTE: " + item["file"] + " / " + service +
                      " / id=" + str(matches[0].get("id")) + " / status=" + str(matches[0].get("status")))
                continue
            try:
                result = create_post(token,service,found[service]["id"],item,links[item["file"]])
                print("SOLICITADO: " + item["file"] + " / " + service +
                      " / postId=" + str(result.get("id")) + " / status=" + str(result.get("status")))
                histories[service].append({"id":result["id"],"text":item["caption"],
                    "assets":[{"source":links[item["file"]]}],"status":result.get("status")})
            except Exception as exc:
                print("ERRO: " + item["file"] + " / " + service + " / " + str(exc),file=sys.stderr)
                errors.append((item["file"],service))
    if errors:
        raise RuntimeError("Falhas parciais: " + repr(errors))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("BLOQUEADO: " + str(exc),file=sys.stderr)
        sys.exit(1)
