#!/usr/bin/env python3
"""Auditoria somente de leitura dos dois videos aprovados de 07/11 no Buffer."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from buffer_publish import fetch_posts, is_duplicate
from buffer_publicar_dupla_07nov import ITEMS, channels

def main():
    report = {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "action": "read_only_audit_no_publication",
        "videos": {},
    }
    for item in ITEMS:
        report["videos"][item["marker"]] = {
            "video": item["file"].rsplit("/", 1)[-1],
            "networks": {},
        }
    token = os.environ.get("BUFFER_API_KEY", "").strip()
    if not token:
        report["error"] = "BUFFER_API_KEY ausente ou nao acessivel no workflow"
    else:
        try:
            found = channels(token)
            for service in ("facebook", "instagram", "tiktok"):
                if service not in found:
                    for item in ITEMS:
                        report["videos"][item["marker"]]["networks"][service] = {
                            "status": "channel_not_found"
                        }
                    continue
                try:
                    ch = found[service]
                    history = fetch_posts(token, ch["org_id"], ch["id"])
                    for item in ITEMS:
                        matches = [p for p in history if is_duplicate(p, item)]
                        statuses = sorted({str(p.get("status") or "unknown") for p in matches})
                        report["videos"][item["marker"]]["networks"][service] = {
                            "status": "found" if matches else "not_found",
                            "post_count": len(matches),
                            "post_statuses": statuses,
                        }
                except Exception as exc:
                    for item in ITEMS:
                        report["videos"][item["marker"]]["networks"][service] = {
                            "status": "lookup_failed",
                            "error_type": type(exc).__name__,
                        }
        except Exception as exc:
            report["error"] = "Falha ao identificar os canais Buffer: " + type(exc).__name__
    path = Path("reports/dupla-07nov-buffer.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
