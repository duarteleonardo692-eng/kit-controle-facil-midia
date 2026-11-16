#!/usr/bin/env python3
"""Publish the approved narrated commercial once per existing brand channel."""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from buffer_publicar_dupla_07nov import channels, validate_video, create_post
from buffer_publish import is_duplicate
from buffer_audit import fetch_detailed_posts

ITEM = {
    'file': 'assets/kit-controle-facil-negocio-em-pausa-revisado-20261116.mp4',
    'sha256': '1d33571f9ec786cdf5679026975e9aec6754e1b7fe09a92072b9c43ccc8ac142',
    'marker': '#CFNegocioEmPausa16Nov26',
    'legacy_phrase': 'Seu negócio não para. E os seus números?',
    'caption': (
        'Seu negócio não para. E os seus números?\n\n'
        'Com o Kit Controle Fácil Excel, organize vendas, despesas e estoque '
        'e acompanhe seu negócio com mais clareza.\n\n'
        'Conheça o kit: https://kit-controle-facil-site.pages.dev/\n'
        'Comprar: https://chk.eduzz.com/8017JVYK07\n\n'
        'Vídeo e locução produzidos com IA. Imagem real da planilha.\n\n'
        '#KitControleFacil #PlanilhaExcel #PequenosNegocios #GestaoFinanceira '
        '#CFNegocioEmPausa16Nov26'
    ),
}
REPORT = Path('reports/negocio-em-pausa-20261116-buffer.json')
SERVICES = ('facebook', 'instagram', 'tiktok')

def save(report):
    report['checked_at'] = datetime.now(timezone.utc).isoformat()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def summarize(service, post):
    return {k: post.get(k) for k in ('id', 'status', 'dueAt', 'sentAt', 'externalLink')}

def main():
    token = os.environ.get('BUFFER_API_KEY', '').strip()
    if not token:
        raise RuntimeError('BUFFER_API_KEY unavailable; no posts submitted')
    found = channels(token)
    if set(found) != set(SERVICES):
        raise RuntimeError('Expected exactly the existing three brand channels')
    url = validate_video(ITEM)
    histories = {svc: fetch_detailed_posts(token, found[svc]['org_id'], found[svc]['id']) for svc in SERVICES}
    report = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {
        'content': 'Kit Controle Facil - O negocio em pausa - revisao com locucao',
        'sha256': ITEM['sha256'], 'media_url': url,
        'caption': ITEM['caption'], 'networks': {},
        'prior_metricool_attempt': 'All three destinations failed with account limit before this Buffer submission',
    }
    # Save the attempt before transmission; an uncertain request is never retried automatically.
    for svc in SERVICES:
        matches = [p for p in histories[svc] if is_duplicate(p, ITEM)]
        if len(matches) > 1:
            raise RuntimeError('Multiple matching posts for '+svc+'; no automatic resend')
        if matches:
            report['networks'][svc] = summarize(svc, matches[0])
            save(report)
            print(svc, json.dumps(report['networks'][svc]), flush=True)
            continue
        if svc in report['networks']:
            report['networks'][svc]['reconciliation_required'] = True
            save(report)
            print(svc, 'Previous attempt needs reconciliation; not resent', flush=True)
            continue
        report['networks'][svc] = {'status': 'request_started'}
        save(report)
        try:
            post = create_post(token, svc, found[svc]['id'], ITEM, url)
            report['networks'][svc] = summarize(svc, post)
        except Exception as exc:
            report['networks'][svc] = {'status': 'submission_error', 'detail': str(exc), 'reconciliation_required': True}
        save(report)
        print(svc, json.dumps(report['networks'][svc]), flush=True)
    # Read-only confirmation. Never create a replacement for an existing failed post.
    for attempt in range(24):
        pending = False
        for svc in SERVICES:
            row = report['networks'][svc]
            if not row.get('id'):
                continue
            posts = fetch_detailed_posts(token, found[svc]['org_id'], found[svc]['id'])
            match = next((p for p in posts if str(p.get('id')) == str(row['id'])), None)
            if match:
                report['networks'][svc] = summarize(svc, match)
                print(svc, json.dumps(report['networks'][svc]), flush=True)
            else:
                row['reconciliation_required'] = True
            if report['networks'][svc].get('status') not in ('sent', 'error', 'submission_error'):
                pending = True
        save(report)
        if not pending:
            break
        time.sleep(15)
    if not all(report['networks'][svc].get('status') == 'sent' for svc in SERVICES):
        raise RuntimeError('Not every destination is confirmed sent; see persisted report')

if __name__ == '__main__':
    main()

