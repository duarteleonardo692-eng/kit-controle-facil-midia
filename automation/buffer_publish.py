#!/usr/bin/env python3
"""Agenda vídeos aprovados do GitHub no Buffer; nunca publica sem consultar duplicações."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.buffer.com"
REPO = "duarteleonardo692-eng/kit-controle-facil-midia"
EXPECTED_CHANNELS = {
    "instagram": "6ae904cfe29c69a1713f2ad8",
    "tiktok": "6ae904e9e29c69a1713f2ba9",
}
STATUSES = "sent, scheduled, sending, draft, needs_approval, error"


def query_graphql(document, token):
    body = json.dumps({"query": document}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API, data=body,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json", "User-Agent": "kit-controle-facil-automation/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Buffer API retornou HTTP " + str(exc.code)) from None
    if data.get("errors"):
        raise RuntimeError("Buffer GraphQL falhou: " + json.dumps(data["errors"], ensure_ascii=False)[:800])
    return data.get("data") or {}


def gql_string(value):
    return json.dumps(str(value), ensure_ascii=False)


def locate_channels(token):
    account = query_graphql("query { account { organizations { id name } } }", token)
    organizations = (account.get("account") or {}).get("organizations") or []
    matches = {}
    for organization in organizations:
        org_id = organization["id"]
        document = (
            "query { channels(input: { organizationId: " + gql_string(org_id) +
            " }) { id name displayName service } }"
        )
        for channel in query_graphql(document, token).get("channels") or []:
            service = str(channel.get("service", "")).lower()
            if service in EXPECTED_CHANNELS and channel.get("id") == EXPECTED_CHANNELS[service]:
                matches[service] = {"id": channel["id"], "org_id": org_id}
    if set(matches) != set(EXPECTED_CHANNELS):
        raise RuntimeError(
            "Canais Buffer não correspondem aos canais aprovados. "
            "Nenhuma publicação será criada. Encontrados: " + str(sorted(matches))
        )
    return matches


def fetch_posts(token, org_id, channel_id):
    posts, cursor = [], None
    for _ in range(100):
        after = ", after: " + gql_string(cursor) if cursor else ""
        document = (
            "query { posts(first: 50" + after + ", input: { organizationId: " +
            gql_string(org_id) + ", filter: { status: [" + STATUSES +
            "], channelIds: [" + gql_string(channel_id) +
            "] } }) { pageInfo { hasNextPage endCursor } edges { node { id text status assets { source } } } } }"
        )
        result = query_graphql(document, token).get("posts") or {}
        posts.extend(edge["node"] for edge in (result.get("edges") or []) if edge.get("node"))
        page = result.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return posts
        next_cursor = page.get("endCursor")
        if not next_cursor or next_cursor == cursor:
            raise RuntimeError("Paginação incompleta: bloqueado para evitar duplicações.")
        cursor = next_cursor
    raise RuntimeError("Histórico muito grande/incompleto: bloqueado para evitar duplicações.")


def is_duplicate(post, item):
    text = str(post.get("text") or "").casefold()
    marker = item["marker"].casefold()
    phrase = str(item.get("legacy_phrase") or "").casefold()
    if marker in text or (phrase and phrase in text):
        return True
    filename = item["file"].rsplit("/", 1)[-1].casefold()
    for asset in post.get("assets") or []:
        source = urllib.parse.unquote(str(asset.get("source") or "")).casefold()
        if filename in source:
            return True
    return False


def validate_video(item):
    filename = item["file"]
    if (not filename.startswith("assets/") or ".." in filename
            or not filename.endswith(".mp4") or Path(filename).is_absolute()):
        raise RuntimeError("Caminho de mídia não autorizado: " + filename)
    if not Path(filename).is_file():
        raise RuntimeError("Vídeo inexistente no checkout: " + filename)
    with open(filename, "rb") as handle:
        header = handle.read(16)
    if len(header) < 12 or header[4:8] != b"ftyp":
        raise RuntimeError("Arquivo não é um MP4 reconhecível: " + filename)
    url = "https://raw.githubusercontent.com/" + REPO + "/main/" + filename
    request = urllib.request.Request(
        url, headers={"User-Agent": "kit-controle-facil-automation/1.0", "Range": "bytes=0-31"}
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            remote_head = response.read(16)
            if response.status not in (200, 206) or remote_head[4:8] != b"ftyp":
                raise RuntimeError("URL pública não entregou MP4 válido: " + filename)
    except urllib.error.URLError as exc:
        raise RuntimeError("URL pública do MP4 não está acessível: " + filename) from exc
    return url


def create_buffer_post(token, channel_id, service, item, url):
    metadata = (
        "metadata: { instagram: { type: reel, shouldShareToFeed: true } }"
        if service == "instagram" else ""
    )
    document = (
        "mutation { createPost(input: { text: " + gql_string(item["caption"]) +
        " channelId: " + gql_string(channel_id) +
        " schedulingType: automatic mode: addToQueue " + metadata +
        " assets: [{ video: { url: " + gql_string(url) +
        " } }] }) { __typename ... on PostActionSuccess { post { id dueAt } } "
        "... on MutationError { message } } }"
    )
    response = query_graphql(document, token).get("createPost") or {}
    if response.get("__typename") != "PostActionSuccess" or not (response.get("post") or {}).get("id"):
        raise RuntimeError("Buffer recusou criar post: " + str(response.get("message") or response))
    return response["post"]


def main():
    token = os.environ.get("BUFFER_API_KEY", "").strip()
    if not token:
        print("NÃO ATIVADO: configure o secret BUFFER_API_KEY neste repositório.")
        return 0
    dry_run = os.environ.get("DRY_RUN", "true").lower() != "false"
    manifest = json.loads(Path("automation/posts.json").read_text(encoding="utf-8"))
    items = [p for p in manifest["posts"] if p.get("approved") is True and p.get("enabled") is True]
    if not items:
        print("Nenhum vídeo aprovado e habilitado.")
        return 0
    for item in items:
        if item["marker"] not in item["caption"]:
            raise RuntimeError("Legenda sem identificador anti-duplicação: " + item["slug"])
        if not set(item["channels"]).issubset(EXPECTED_CHANNELS):
            raise RuntimeError("Canal não autorizado: " + item["slug"])

    channels = locate_channels(token)
    # Pré-checagem: qualquer falha de leitura impede TODAS as alterações.
    history = {}
    for service, info in channels.items():
        history[service] = fetch_posts(token, info["org_id"], info["id"])
        print(service + ": " + str(len(history[service])) + " registros analisados.")
    urls = {item["slug"]: validate_video(item) for item in items}
    created_per_channel = set()
    for item in items:
        for service in item["channels"]:
            if any(is_duplicate(post, item) for post in history[service]):
                print("JÁ EXISTE, ignorado: " + item["slug"] + " / " + service)
                continue
            if service in created_per_channel:
                print("Limite de 1 vídeo novo por canal por execução: " + service)
                continue
            if dry_run:
                print("SIMULAÇÃO: " + item["slug"] + " / " + service + " (não criou post)")
                continue
            post = create_buffer_post(token, channels[service]["id"], service, item, urls[item["slug"]])
            print("ADICIONADO À FILA: " + item["slug"] + " / " + service +
                  " | Buffer id " + post["id"] + " | horário " + str(post.get("dueAt")))
            created_per_channel.add(service)
            history[service].append({"text": item["caption"], "assets": [{"source": urls[item["slug"]]}]})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        print("BLOQUEADO: " + str(exc), file=sys.stderr)
        sys.exit(1)
