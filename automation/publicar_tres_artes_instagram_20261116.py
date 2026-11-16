#!/usr/bin/env python3
"""Publica SOMENTE as 3 artes recriadas do Kit Controle Facil no Instagram via Buffer.
Uma imediatamente e as demais +10 e +20 minutos. Nunca reenvia em estado incerto.
"""
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from buffer_publicar_dupla_07nov import channels
from buffer_audit import fetch_detailed_posts
from buffer_publish import gql_string, is_duplicate, query_graphql

REPO = "duarteleonardo692-eng/kit-controle-facil-midia"
SITE = "https://kit-controle-facil-site.pages.dev/"
LOJA = "https://kit-controle-facil-site.pages.dev/loja/"
REPORT = Path("reports/instagram-tres-artes-recriadas-20261116.json")
INSTAGRAM_ID = "6ae904cfe29c69a1713f2ad8"
ITEMS = [
    {
        "slug": "01_organize_negocio_vendas",
        "file": "assets/kit-instagram-recriado-01_organize_negocio_vendas.jpg",
        "sha256": "47a11b233899fd2a05c8a39589093de8ad3e0c87cbd43c0de0a72a201be4350b",
        "marker": "#CFRecriadoVendasIG16Nov26",
        "caption": (
            "📊 Organize seu negócio e venda mais!\n\n"
            "Acompanhe vendas, entradas e saídas com o Kit Controle Fácil Excel. "
            "Tenha uma visão mais clara do seu negócio, com planilha e gráficos em um só lugar. 💚\n\n"
            "🌐 Conheça no site: " + SITE + "\n"
            "🛍️ Veja nossa loja: " + LOJA + "\n"
            "📲 Links também no perfil!\n\n"
            "#KitControleFacil #PequenosNegocios #ControleDeVendas #PlanilhaExcel #CFRecriadoVendasIG16Nov26"
        ),
    },
    {
        "slug": "02_veja_na_pratica",
        "file": "assets/kit-instagram-recriado-02_veja_na_pratica.jpg",
        "sha256": "ee355370355e34e46b138cd16aaf54730c6f115697b105b3fc086ea6f0199065",
        "marker": "#CFRecriadoDemonstracaoIG16Nov26",
        "caption": (
            "💻 Quer ver o Kit Controle Fácil na prática?\n\n"
            "Conheça as demonstrações do Excel para acompanhar vendas, estoque, despesas e relatórios. "
            "Explore como as informações ficam organizadas para facilitar sua rotina. ✨\n\n"
            "🌐 Veja a demonstração: " + SITE + "\n"
            "🛍️ Conheça a loja: " + LOJA + "\n"
            "📲 Acesse o link da bio!\n\n"
            "#KitControleFacil #GestaoSimples #PlanilhaExcel #Empreendedorismo #CFRecriadoDemonstracaoIG16Nov26"
        ),
    },
    {
        "slug": "03_negocios_atendidos",
        "file": "assets/kit-instagram-recriado-03_negocios_atendidos.jpg",
        "sha256": "d8126c55892eb567e83f6007ef12b76614de9164f524db9d2d8b384a4efb627d",
        "marker": "#CFRecriadoNegociosIG16Nov26",
        "caption": (
            "☕💈🌸 Seu negócio merece mais organização!\n\n"
            "Cafeterias, barbearias, floriculturas e outros pequenos negócios podem organizar "
            "suas vendas, estoque e despesas com o Kit Controle Fácil Excel. "
            "Conheça os recursos e veja como podem ajudar na rotina. 💚\n\n"
            "🌐 Explore o produto: " + SITE + "\n"
            "🛍️ Visite nossa loja: " + LOJA + "\n"
            "📲 Links no perfil!\n\n"
            "#KitControleFacil #PequenosNegocios #Cafeteria #Barbearia #GestaoFinanceira #CFRecriadoNegociosIG16Nov26"
        ),
    },
]

def checkpoint(state):
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(REPORT)], check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode:
        subprocess.run(["git", "commit", "-m", "Registrar entrega das 3 artes recriadas no Instagram"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push", "origin", "HEAD:main"], check=True, stdout=subprocess.DEVNULL)

def preflight():
    """Todos os tres JPGs originais (1080x1350) sao obrigatorios; NUNCA usar fotos genericas."""
    urls = {}
    for item in ITEMS:
        path = Path(item["file"])
        if not path.is_file():
            raise RuntimeError("IMAGEM NOVA AUSENTE; nenhum post criado: " + str(path))
        raw = path.read_bytes()
        if raw[:3] != b"\xff\xd8\xff" or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise RuntimeError("IMAGEM INCORRETA OU ALTERADA; nenhum post criado: " + str(path))
        url = "https://raw.githubusercontent.com/" + REPO + "/main/" + str(path)
        confirmed = False
        for _ in range(10):
            try:
                req = urllib.request.Request(url, headers={"Range": "bytes=0-15", "User-Agent": "KitControleFacilIG/1.0"})
                with urllib.request.urlopen(req, timeout=25) as resp:
                    confirmed = resp.status in (200, 206) and resp.read(3) == b"\xff\xd8\xff"
                if confirmed:
                    break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(6)
        if not confirmed:
            raise RuntimeError("Imagem ainda nao acessivel pelo Buffer: " + url)
        urls[item["slug"]] = url
    return urls

def summary(p):
    return {k: p.get(k) for k in ("id", "status", "dueAt", "sentAt", "externalLink")}

def create(token, channel_id, item, url, due_at):
    mode = "mode: shareNow" if due_at is None else "mode: customScheduled dueAt: " + gql_string(due_at)
    query = (
        "mutation { createPost(input: { text: " + gql_string(item["caption"]) +
        " channelId: " + gql_string(channel_id) + " schedulingType: automatic " + mode +
        " metadata: { instagram: { type: post, shouldShareToFeed: true, isAiGenerated: true } }" +
        " assets: [{ image: { url: " + gql_string(url) + " } }]" +
        " }) { __typename ... on PostActionSuccess { post { id dueAt status } }" +
        " ... on MutationError { message } } }"
    )
    result = (query_graphql(query, token).get("createPost") or {})
    if result.get("__typename") != "PostActionSuccess" or not (result.get("post") or {}).get("id"):
        raise RuntimeError("Buffer recusou: " + str(result.get("message") or result))
    return result["post"]

def main():
    token = os.environ.get("BUFFER_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Sem BUFFER_API_KEY; nenhum post enviado")
    urls = preflight()  # Garantir todas as artes ANTES de qualquer publicacao
    found = channels(token)
    insta = found.get("instagram")
    if not insta or insta["id"] != INSTAGRAM_ID:
        raise RuntimeError("Conta Instagram diferente da autorizada; nao publicado")
    history = fetch_detailed_posts(token, insta["org_id"], insta["id"])
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {
        "campaign": "Três artes recriadas Instagram 16nov",
        "network": "instagram",
        "posts": {},
    }
    for item in ITEMS:
        if item["marker"] not in item["caption"]:
            raise RuntimeError("Legenda invalida")
        matches = [p for p in history if is_duplicate(p, item)]
        if len(matches) > 1:
            raise RuntimeError("Duplicatas no Buffer: " + item["slug"])
        recorded = report["posts"].get(item["slug"])
        if recorded and recorded.get("status") in ("request_started", "submission_error"):
            raise RuntimeError("Tentativa de resultado incerto; conferir manualmente: " + item["slug"])
        if matches or (recorded and recorded.get("id")):
            existing = matches[0] if matches else recorded
            report["posts"][item["slug"]] = summary(existing)
            checkpoint(report)
            print("JA EXISTE; nao reenviado:", item["slug"], flush=True)
            continue
        # Agendar as proximas em intervalos de 10 minutos contados do primeiro envio.
        if "first_request_at" not in report:
            report["first_request_at"] = datetime.now(timezone.utc).isoformat()
        start = datetime.fromisoformat(report["first_request_at"])
        index = ITEMS.index(item)
        due = None if index == 0 else (start + timedelta(minutes=10*index)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if due is not None and datetime.fromisoformat(due.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            # Evita datas passadas se a execucao demorar; agendar pelo menos dez minutos a frente.
            due = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        report["posts"][item["slug"]] = {"status": "request_started", "requested_due_at": due, "media_url": urls[item["slug"]], "marker": item["marker"]}
        checkpoint(report)
        try:
            created = create(token, insta["id"], item, urls[item["slug"]], due)
            report["posts"][item["slug"]] = {**summary(created), "requested_due_at": due, "media_url": urls[item["slug"]]}
        except Exception as exc:
            report["posts"][item["slug"]] = {"status": "submission_error", "detail": str(exc)[:500], "reconciliation_required": True}
            checkpoint(report)
            raise
        checkpoint(report)
        history.append({"id": created["id"], "text": item["caption"], "assets": [{"source": urls[item["slug"]]}], "status": created.get("status")})
        print("BUFFER_ACEITO instagram", item["slug"], json.dumps(report["posts"][item["slug"]]), flush=True)
    print("FIM: verificar status de cada post em " + str(REPORT), flush=True)

if __name__ == "__main__":
    main()
