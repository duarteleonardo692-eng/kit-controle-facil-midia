#!/usr/bin/env python3
"""Publicar a versao FINAL distinta de Quanto Entrou Hoje, uma vez por canal."""
import os
import sys
from buffer_publicar_dupla_07nov import channels, validate_video, create_post
from buffer_publish import fetch_posts, is_duplicate

ITEM = {
    "file": "assets/kit-controle-facil-quanto-entrou-hoje-final-20261109.mp4",
    "sha256": "39c95069c4740ccc1b4473cb63aff11253dca2183598ea2750768bab22a61b32",
    "marker": "#CFQuantoEntrouFinal09Nov26",
    "legacy_phrase": "",
    "caption": (
        "💚 Quanto entrou hoje no seu negócio?\n\n"
        "Vender é importante. Saber quanto entrou e manter as contas organizadas também! 📊\n"
        "Com o Kit Controle Fácil para Excel, você registra as vendas e acompanha os valores do caixa com mais clareza.\n\n"
        "🌐 Conheça o Kit Controle Fácil: https://kit-controle-facil-site.pages.dev/\n\n"
        "🎬 Demonstração ilustrativa do produto.\n\n"
        "#KitControleFacil #ControleDeCaixa #PlanilhaExcel #GestaoFinanceira #PequenosNegocios "
        "#CFQuantoEntrouFinal09Nov26"
    ),
}

def main():
    token = os.environ.get("BUFFER_API_KEY", "").strip()
    if not token:
        raise RuntimeError("BUFFER_API_KEY ausente - nenhuma publicacao realizada")
    found = channels(token)
    expected = {"facebook", "instagram", "tiktok"}
    if set(found) != expected:
        raise RuntimeError("Canais incompletos; bloqueio preventivo: " + repr(sorted(found)))
    # Ler todo o historico primeiro para prevenir duplicacoes, inclusive em tentativas repetidas.
    histories = {}
    for service in ("facebook", "instagram", "tiktok"):
        ch = found[service]
        histories[service] = fetch_posts(token, ch["org_id"], ch["id"])
        print("VERIFICADO: " + service + " - " + str(len(histories[service])) + " posts no historico", flush=True)
    url = validate_video(ITEM)
    errors = []
    for service in ("facebook", "instagram", "tiktok"):
        matches = [p for p in histories[service] if is_duplicate(p, ITEM)]
        if matches:
            print("JA_EXISTE: " + service + " id=" + str(matches[0].get("id")) + " status=" + str(matches[0].get("status")), flush=True)
            continue
        try:
            post = create_post(token, service, found[service]["id"], ITEM, url)
            print("SOLICITADO: " + service + " id=" + str(post.get("id")) + " status=" + str(post.get("status")), flush=True)
        except Exception as exc:
            errors.append(service)
            print("ERRO: " + service + " - " + str(exc), file=sys.stderr, flush=True)
    if errors:
        raise RuntimeError("Falhas parciais nas redes: " + ", ".join(errors))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("BLOQUEADO: " + str(exc), file=sys.stderr)
        sys.exit(1)
