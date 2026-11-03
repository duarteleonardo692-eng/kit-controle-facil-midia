#!/usr/bin/env python3
"""Testes locais: não precisam de acesso ao Buffer nem criam posts."""
import unittest
from datetime import datetime, timedelta, timezone

from buffer_audit import audit_post

NOW = datetime(2026, 11, 3, 12, 30, tzinfo=timezone.utc)
ITEM = {
    "slug": "reels10-lanchonetes-cafeterias",
    "file": "assets/reels10-lanchonetes-cafeterias-aprovado.mp4",
    "marker": "#CFReels10",
    "legacy_phrase": "lanchonetes e cafeterias"
}


def make_post(status, when=None):
    return {
        "id": "buffer-post-demo",
        "text": "Vídeo aprovado #CFReels10",
        "status": status,
        "assets": [],
        "dueAt": when.isoformat() if when else None,
        "sentAt": None,
        "externalLink": None,
    }


class BufferAuditTests(unittest.TestCase):
    def test_future_post_is_waiting(self):
        state, _, _ = audit_post(ITEM, "instagram", [make_post("scheduled", NOW + timedelta(hours=3))], NOW)
        self.assertEqual(state, "AGUARDANDO")

    def test_sent_post_is_success(self):
        post = make_post("sent", NOW - timedelta(hours=2))
        post["externalLink"] = "https://example.org/video"
        state, _, _ = audit_post(ITEM, "tiktok", [post], NOW)
        self.assertEqual(state, "OK")

    def test_publishing_error_is_failure(self):
        state, _, _ = audit_post(ITEM, "instagram", [make_post("error")], NOW)
        self.assertEqual(state, "ERRO")

    def test_overdue_post_is_failure(self):
        state, _, _ = audit_post(ITEM, "instagram", [make_post("scheduled", NOW - timedelta(hours=4))], NOW)
        self.assertEqual(state, "ERRO")

    def test_missing_post_is_failure(self):
        state, _, _ = audit_post(ITEM, "tiktok", [], NOW)
        self.assertEqual(state, "ERRO")

    def test_duplicate_post_is_failure(self):
        state, _, _ = audit_post(ITEM, "instagram", [make_post("scheduled", NOW), make_post("scheduled", NOW)], NOW)
        self.assertEqual(state, "ERRO")


if __name__ == "__main__":
    unittest.main()
