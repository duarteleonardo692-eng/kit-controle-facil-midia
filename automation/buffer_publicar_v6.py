#!/usr/bin/env python3
"""Post only the already-approved Kit Controle Facil V6 commercial, idempotently."""
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

from buffer_publish import query_graphql, fetch_posts, gql_string, is_duplicate

REPO = "duarteleonardo692-eng/kit-controle-facil-midia"
FILE = "assets/kit-controle-facil-comercial-v6-final-sincronizado.mp4"
URL = f"https://raw.githubusercontent.com/{REPO}/main/{FILE}"
MARKER = "#CFComercialV6Nov2026"
CAPTION = ("☕ Seu negócio merece mais organização e menos preocupação!\n\n"
           "Com o Kit Controle Fácil, você acompanha vendas, estoque, despesas e resultados "
           "em planilhas práticas para pequenos negócios. 📊\n\n"
           "Mais clareza para tomar decisões e mais tempo para cuidar dos clientes. 💚\n\n"
           "Conheça o Kit Controle Fácil!\n\n"
           "🎬 Vídeo ilustrativo produzido com inteligência artificial; "
           "telas demonstrativas com dados fictícios.\n\n"
           "#KitControleFacil #PequenosNegocios #Empreendedorismo "
           "#GestaoFinanceira #ControleDeEstoque " + MARKER)
EXPECTED = {
    "instagram": "6ae904cfe29c69a1713f2ad8",
    "tiktok": "6ae904e9e29c69a1713f2ba9",
}
ITEM = {"marker": MARKER, "file": FILE, "legacy_phrase": ""}

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

def check_remote():
    for attempt in range(10):
        try:
            req = urllib.request.Request(URL, headers={"Range": "bytes=0-31", "User-Agent":"kit-controle-facil-v6/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                header = resp.read(16)
                if header[4:8] == b"ftyp" and resp.status in (200,206):
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(5)
    raise RuntimeError("MP4 público não está acessível; nenhuma publicação autorizada")

def post(token, service, channel_id):
    extra = ""
    if service == "facebook":
        extra = "metadata: { facebook: { type: reel } }"
    elif service == "instagram":
        extra = "metadata: { instagram: { type: reel, shouldShareToFeed: true, isAiGenerated: true } }"
    elif service == "tiktok":
        extra = "metadata: { tiktok: { isAiGenerated: true } }"
    doc = ("mutation { createPost(input: { text: " + gql_string(CAPTION) +
           " channelId: " + gql_string(channel_id) +
           " schedulingType: automatic mode: shareNow " + extra +
           " assets: [{ video: { url: " + gql_string(URL) +
           " } }] }) { __typename ... on PostActionSuccess { post { id dueAt status } } "
           "... on MutationError { message } } }")
    result = query_graphql(doc, token).get("createPost") or {}
    if result.get("__typename") != "PostActionSuccess" or not (result.get("post") or {}).get("id"):
        raise RuntimeError(f"Buffer recusou {service}: {result.get('message', result)}")
    return result["post"]

def main():
    token = os.environ.get("BUFFER_API_KEY", "").strip()
    if not token: raise RuntimeError("BUFFER_API_KEY ausente. Nada publicado.")
    if not Path(FILE).is_file(): raise RuntimeError("MP4 reconstruído não encontrado")
    check_remote()
    found = channels(token)
    if not found: raise RuntimeError("Nenhum canal compatível conectado no Buffer.")
    histories = {}
    for svc, ch in found.items():
        histories[svc] = fetch_posts(token, ch["org_id"], ch["id"])
        print(f"{svc}: {len(histories[svc])} posts conferidos (anti-duplicação)")
    errors = []
    for svc in ("facebook", "instagram", "tiktok"):
        if svc not in found:
            print(f"INACESSÍVEL: {svc} não foi identificado como canal autorizado do Buffer")
            continue
        if any(is_duplicate(p, ITEM) for p in histories[svc]):
            print(f"JÁ EXISTE: {svc}, envio ignorado")
            continue
        try:
            response = post(token, svc, found[svc]["id"])
            print(f"SOLICITADO: {svc}, postId={response['id']}, status={response.get('status')}")
        except Exception as exc:
            print(f"ERRO: {svc}: {exc}", file=sys.stderr)
            errors.append(svc)
    if errors:
        raise RuntimeError("Falhou em: " + ", ".join(errors))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as exc:
        print("BLOQUEADO: " + str(exc), file=sys.stderr)
        sys.exit(1)
