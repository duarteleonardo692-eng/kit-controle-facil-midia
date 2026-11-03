#!/usr/bin/env python3
"""Auditoria somente leitura de publicações do Buffer após agendamento.

Não cria, altera, remove ou republica posts.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from buffer_publish import EXPECTED_CHANNELS, STATUSES, gql_string, is_duplicate, locate_channels, query_graphql

BRAZIL = ZoneInfo("America/Sao_Paulo")
GRACE = timedelta(hours=2)


def fetch_detailed_posts(token, org_id, channel_id):
    posts, cursor = [], None
    for _ in range(100):
        after = ", after: " + gql_string(cursor) if cursor else ""
        query = (
            "query { posts(first: 50" + after + ", input: { organizationId: " +
            gql_string(org_id) + ", filter: { status: [" + STATUSES +
            "], channelIds: [" + gql_string(channel_id) +
            "] } }) { pageInfo { hasNextPage endCursor } edges { node { "
            "id text status dueAt sentAt externalLink assets { source } "
            "} } } }"
        )
        result = query_graphql(query, token).get("posts") or {}
        posts.extend(edge["node"] for edge in (result.get("edges") or []) if edge.get("node"))
        page = result.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return posts
        following = page.get("endCursor")
        if not following or following == cursor:
            raise RuntimeError("Consulta incompleta do histórico do Buffer.")
        cursor = following
    raise RuntimeError("Histórico muito grande: impossível conferir todos os posts.")


def due_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if not parsed.tzinfo:
        raise RuntimeError("Data de agendamento não possui fuso horário.")
    return parsed.astimezone(timezone.utc)


def audit_post(item, service, posts, now):
    matches = [post for post in posts if is_duplicate(post, item)]
    label = item["slug"] + " / " + service
    if not matches:
        return ("ERRO", label, "Nenhum registro do vídeo aprovado encontrado no Buffer.")
    if len(matches) != 1:
        return ("ERRO", label, "Encontrados " + str(len(matches)) + " registros possíveis do mesmo vídeo.")
    post = matches[0]
    status = str(post.get("status") or "").lower()
    due = due_datetime(post.get("dueAt"))
    local_due = due.astimezone(BRAZIL).strftime("%d/%m/%Y %H:%M") if due else "não informado"
    link = str(post.get("externalLink") or "").strip()
    if status == "sent":
        info = "Publicado conforme Buffer"
        if post.get("sentAt"):
            info += " em " + str(post["sentAt"])
        if link.startswith("https://"):
            info += " | URL: " + link
        else:
            info += " | sem URL externa fornecida pela API"
        return ("OK", label, info)
    if status == "error":
        return ("ERRO", label, "Falha de publicação registrada no Buffer (post " + str(post.get("id")) + ").")
    if status == "scheduled":
        if not due:
            return ("ERRO", label, "Agendado sem data informada pela API.")
        if now > due + GRACE:
            return ("ERRO", label, "Ainda agendado mais de 2h após o horário " + local_due + ".")
        return ("AGUARDANDO", label, "Agendado para " + local_due + " (Brasília).")
    if status in ("sending", "needs_approval", "draft"):
        if due and now > due + GRACE:
            return ("ERRO", label, "Post permanece em estado " + status + " após " + local_due + ".")
        return ("AGUARDANDO", label, "Estado atual: " + status + " | previsão " + local_due + ".")
    return ("ERRO", label, "Estado desconhecido do Buffer: " + repr(status))


def report_summary(rows):
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    lines = [
        "## Auditoria GitHub → Buffer",
        "",
        "Verificação somente leitura. **Nenhum vídeo foi reenviado.**",
        "",
        "| Resultado | Conteúdo / rede | Detalhes |",
        "|---|---|---|",
    ]
    for state, label, message in rows:
        safe = lambda value: str(value).replace("|", " / ").replace("\n", " ").replace("\r", " ")
        lines.append("| " + safe(state) + " | " + safe(label) + " | " + safe(message) + " |")
    with open(summary, "a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main():
    token = os.environ.get("BUFFER_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Secret BUFFER_API_KEY ausente no GitHub Actions.")
    items = [
        x for x in json.loads(Path("automation/posts.json").read_text(encoding="utf-8"))["posts"]
        if x.get("approved") is True and x.get("enabled") is True
    ]
    if not items:
        print("Não há vídeos aprovados habilitados para acompanhamento.")
        return 0
    channels = locate_channels(token)
    history = {
        service: fetch_detailed_posts(token, info["org_id"], info["id"])
        for service, info in channels.items()
    }
    now = datetime.now(timezone.utc)
    rows = []
    for item in items:
        for service in item["channels"]:
            if service not in EXPECTED_CHANNELS:
                raise RuntimeError("Canal não permitido: " + service)
            result = audit_post(item, service, history[service], now)
            rows.append(result)
            print(" / ".join(result))
    report_summary(rows)
    if any(state == "ERRO" for state, _, _ in rows):
        raise RuntimeError("Auditoria encontrou falha de publicação ou possível duplicação. Verifique a aba Sent / Queue no Buffer.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        print("AUDITORIA FALHOU: " + str(exc), file=sys.stderr)
        sys.exit(1)
