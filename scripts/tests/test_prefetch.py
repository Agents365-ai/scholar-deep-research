"""End-to-end (no-network) tests for prefetch_pdfs + apply_pdf_paths.

Uses subprocess (the same harness as the rest of the smoke suite) so the
test exercises the actual envelope contract — argparse, with_idempotency,
ok/err — not just the internal Python API. fetch_pdf is monkey-patched
via SCHOLAR_PREFETCH_TEST_FAKE: when that env var points at a JSON file,
prefetch_pdfs uses the recorded fake outcomes instead of touching paper-
fetch / Unpaywall. The fake hook is gated to the test path only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _helpers import dummy_paper, init_state, run_script

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _ingest_papers(state: Path, papers: list[dict]) -> None:
    payload = {"source": "openalex", "query": "test", "round": 1,
               "papers": papers}
    payload_path = state.parent / "payload.json"
    payload_path.write_text(json.dumps(payload))
    env = run_script("research_state.py", [
        "--state", str(state), "ingest", "--input", str(payload_path),
    ])
    assert env.get("ok"), f"ingest failed: {env}"


def _select_and_triage(state: Path) -> None:
    """Run rank + select + skim_papers so prefetch has a deep tier."""
    env = run_script("rank_papers.py", ["--state", str(state), "--top", "10"])
    assert env.get("ok")
    env = run_script("research_state.py", [
        "--state", str(state), "select", "--top", "10",
    ])
    assert env.get("ok")
    env = run_script("skim_papers.py", [
        "--state", str(state),
        "--deep-ratio", "0.5", "--skim-ratio", "0.5",
    ])
    assert env.get("ok")


class PrefetchSchemaTest(unittest.TestCase):
    """prefetch_pdfs --schema must produce a valid envelope."""

    def test_schema(self):
        env = run_script("prefetch_pdfs.py", ["--schema"], expect_rc=0)
        self.assertTrue(env.get("ok"), f"prefetch_pdfs --schema: {env}")
        self.assertEqual(env["data"]["command"], "prefetch_pdfs")
        params = env["data"]["params"]
        for required in ("tier", "concurrency", "out_dir", "dry_run",
                         "idempotency_key"):
            self.assertIn(required, params,
                          f"prefetch_pdfs schema missing param '{required}'")
        # Tier flag must be enum-constrained for safety.
        self.assertIn("choices", params["tier"])
        self.assertEqual(set(params["tier"]["choices"]),
                         {"deep", "skim", "defer"})


class PrefetchDryRunTest(unittest.TestCase):
    """Dry-run must not mutate state and must report what would happen."""

    def test_dry_run_lists_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            papers = [dummy_paper(f"W{i}", doi=f"10.1234/test{i}",
                                  pdf_url=f"https://x/pdf/{i}.pdf")
                      for i in range(8)]
            _ingest_papers(state, papers)
            _select_and_triage(state)

            env = run_script("prefetch_pdfs.py", [
                "--state", str(state), "--tier", "deep", "--dry-run",
            ])
            self.assertTrue(env.get("ok"))
            self.assertTrue(env["data"]["dry_run"])
            # 8 papers, top 50% deep = 4 candidates.
            self.assertEqual(env["data"]["would_fetch"], 4)
            self.assertEqual(len(env["data"]["would_fetch_ids"]), 4)


class ApplyPdfPathsTest(unittest.TestCase):
    """The apply_pdf_paths replay subcommand survives a roundtrip."""

    def test_replay_via_prefetch_subcommand(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            # Use DOIs that match the normalize_doi regex (10\.\d{4,9}/...).
            papers = [dummy_paper("W1", doi="10.1234/aaa"),
                      dummy_paper("W2", doi="10.1234/bbb")]
            _ingest_papers(state, papers)

            patch = {
                "pdf_records": {
                    "doi:10.1234/aaa": {
                        "id": "doi:10.1234/aaa",
                        "pdf_status": "ok",
                        "pdf_path": "/tmp/a.pdf",
                        "pdf_source": "unpaywall",
                        "pdf_bytes": 1024,
                    },
                    "doi:10.1234/bbb": {
                        "id": "doi:10.1234/bbb",
                        "pdf_status": "failed",
                        "pdf_failure_code": "no_open_access_pdf",
                        "pdf_failure_reason": "paywall",
                        "pdf_failure_retryable": False,
                    },
                },
            }
            patch_path = Path(td) / "prefetch.patch.json"
            patch_path.write_text(json.dumps(patch))

            env = run_script("research_state.py", [
                "--state", str(state), "prefetch",
                "--patch", str(patch_path),
            ])
            self.assertTrue(env.get("ok"), f"prefetch replay: {env}")
            self.assertEqual(env["data"]["applied"], 2)
            self.assertEqual(env["data"]["unknown"], 0)
            by_status = env["data"]["by_status"]
            self.assertEqual(by_status.get("ok"), 1)
            self.assertEqual(by_status.get("failed"), 1)

            saved = json.loads(state.read_text())
            ok_paper = saved["papers"]["doi:10.1234/aaa"]
            self.assertEqual(ok_paper["pdf_status"], "ok")
            self.assertEqual(ok_paper["pdf_path"], "/tmp/a.pdf")
            self.assertEqual(ok_paper["pdf_bytes"], 1024)
            failed_paper = saved["papers"]["doi:10.1234/bbb"]
            self.assertEqual(failed_paper["pdf_status"], "failed")
            self.assertEqual(failed_paper["pdf_failure_code"],
                             "no_open_access_pdf")

    def test_unknown_id_counted_not_errored(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            patch = {"pdf_records": {
                "doi:not.in.state": {"id": "doi:not.in.state",
                                     "pdf_status": "ok",
                                     "pdf_path": "/tmp/x.pdf"},
            }}
            patch_path = Path(td) / "p.json"
            patch_path.write_text(json.dumps(patch))

            env = run_script("research_state.py", [
                "--state", str(state), "prefetch",
                "--patch", str(patch_path),
            ])
            self.assertTrue(env.get("ok"))
            self.assertEqual(env["data"]["applied"], 0)
            self.assertEqual(env["data"]["unknown"], 1)


if __name__ == "__main__":
    unittest.main()
