"""Shared helpers for every scholar-deep-research script.

Provides:
  - USER_AGENT             polite-pool identifier for HTTP calls
  - EXIT_*                 stable, differentiated exit codes for agents/orchestrators
  - ok() / err()           unified stdout envelope
  - UpstreamError          typed exception for HTTP/API failures
  - make_paper / make_payload / emit   search-script normalization helpers

Envelope contract:
  success → {"ok": true, "data": <any>, ...}
  failure → {"ok": false, "error": {"code": str, "message": str,
                                    "retryable": bool, ...}}

Every script must print exactly one envelope to stdout and exit with one of
the EXIT_* codes. Diagnostics go to stderr. No prose on stdout, ever.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Canonical version string. Bump in lockstep with the `version` field in
# SKILL.md frontmatter so USER_AGENT, telemetry, and skill metadata agree.
VERSION = "0.3.0"

USER_AGENT = (
    f"scholar-deep-research/{VERSION} "
    "(+https://github.com/Agents365-ai/scholar-deep-research; "
    "polite-pool)"
)

# ---------- exit codes ----------
# Stable across versions. Documented in SKILL.md.
EXIT_OK = 0          # success
EXIT_RUNTIME = 1     # runtime / API logic error (e.g. malformed upstream response)
EXIT_UPSTREAM = 2    # upstream / network error (retryable)
EXIT_VALIDATION = 3  # bad input: missing flag, bad value, whitelist violation
EXIT_STATE = 4       # state file missing, corrupt, or schema mismatch


# ---------- envelope helpers ----------

def ok(data: Any = None, *, meta: dict[str, Any] | None = None,
       **extra: Any) -> None:
    """Print a success envelope to stdout.

    Does not exit. Caller returns normally (implicit exit 0).
    """
    payload: dict[str, Any] = {"ok": True}
    if data is not None:
        payload["data"] = data
    if meta is not None:
        payload["meta"] = meta
    payload.update(extra)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def err(code: str, message: str, *, retryable: bool = False,
        exit_code: int = EXIT_RUNTIME, **ctx: Any) -> None:
    """Print an error envelope to stdout and exit with `exit_code`.

    `code` is a stable snake_case routing key (e.g. "state_not_found",
    "upstream_error"). `message` is the human-readable sentence. `retryable`
    signals whether calling the exact same command again may succeed. Any
    additional kwargs become extra fields on the error object (e.g. `field`,
    `source`, `allowed`).
    """
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    error.update(ctx)
    json.dump({"ok": False, "error": error}, sys.stdout,
              ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.exit(exit_code)


class UpstreamError(Exception):
    """HTTP/API failure raised from inside a search function.

    The search script's main() catches this and calls err() so the agent sees
    a structured failure envelope rather than a silent empty result.
    """

    def __init__(self, source: str, message: str, *,
                 retryable: bool = True,
                 exit_code: int = EXIT_UPSTREAM,
                 status: int | None = None) -> None:
        super().__init__(message)
        self.source = source
        self.message = message
        self.retryable = retryable
        self.exit_code = exit_code
        self.status = status

# Fields that every normalized paper should have (None if unknown).
PAPER_FIELDS = (
    "doi", "title", "authors", "year", "venue", "abstract",
    "citations", "url", "pdf_url",
    "openalex_id", "arxiv_id", "pmid",
)


def make_paper(**kwargs: Any) -> dict[str, Any]:
    """Build a paper dict with all standard fields, missing → None."""
    p: dict[str, Any] = {f: None for f in PAPER_FIELDS}
    p.update({k: v for k, v in kwargs.items() if v is not None})
    # type discipline
    if p.get("authors") and not isinstance(p["authors"], list):
        p["authors"] = [p["authors"]]
    if p.get("year"):
        try:
            p["year"] = int(p["year"])
        except (TypeError, ValueError):
            p["year"] = None
    if p.get("citations") is not None:
        try:
            p["citations"] = int(p["citations"])
        except (TypeError, ValueError):
            p["citations"] = 0
    return p


def make_payload(source: str, query: str, round_: int,
                 papers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source": source,
        "query": query,
        "round": round_,
        "papers": papers,
    }


def emit(payload: dict[str, Any], output: str | None,
         state: str | None) -> None:
    """Write search payload to --output JSON and/or hand to research_state ingest.

    Always prints exactly one envelope to stdout:
      - with --state: pass-through of `research_state.py ingest`'s envelope
      - with --output only: {"ok": true, "data": {"output": path, "count": N, ...}}
      - with neither: {"ok": true, "data": <payload>}
    """
    tmp: Path | None = None
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        tmp = out_path

    if state:
        # If we don't already have a file, write a temp path for subprocess ingest.
        if tmp is None:
            tmp = Path(".search_payload.tmp.json")
            tmp.write_text(json.dumps(payload, ensure_ascii=False))
        here = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, str(here / "research_state.py"),
             "--state", state, "ingest", "--input", str(tmp)],
            capture_output=True, text=True,
        )
        # research_state.py ingest emits its own ok/err envelope — pass it through.
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)
        if tmp == Path(".search_payload.tmp.json"):
            try:
                tmp.unlink()
            except OSError:
                pass
        return

    if output:
        ok({
            "output": str(output),
            "source": payload.get("source"),
            "query": payload.get("query"),
            "round": payload.get("round"),
            "count": len(payload.get("papers", [])),
        })
        return

    # Neither --output nor --state: dump the whole payload, enveloped.
    ok(payload)


def reconstruct_inverted_abstract(idx: dict[str, list[int]] | None) -> str | None:
    """OpenAlex returns abstracts as inverted indexes; reconstruct flat text."""
    if not idx:
        return None
    positions: list[tuple[int, str]] = []
    for word, locs in idx.items():
        for loc in locs:
            positions.append((loc, word))
    positions.sort()
    return " ".join(w for _, w in positions) or None


# ---------- schema introspection ----------

SCHEMA_VERSION = 1

# Stable exit-code vocabulary, shared by every script. The schema response
# includes this so agents can route on code without reading SKILL.md.
EXIT_CODE_VOCAB: dict[str, str] = {
    "0": "success",
    "1": "runtime error (e.g. malformed upstream response, missing dependency)",
    "2": "upstream / network error (retryable)",
    "3": "validation error (bad input)",
    "4": "state error (missing, corrupt, or schema mismatch)",
}


def _action_type_name(action: argparse.Action) -> str:
    """Map an argparse action to a JSON-schema-ish type name."""
    if isinstance(action, (argparse._StoreTrueAction,
                           argparse._StoreFalseAction)):
        return "boolean"
    t = action.type
    if t is int:
        return "integer"
    if t is float:
        return "number"
    if t is None or t is str:
        return "string"
    return getattr(t, "__name__", str(t))


def _parser_to_schema(parser: argparse.ArgumentParser,
                      command: str) -> dict[str, Any]:
    """Walk an argparse parser into a JSON-serializable schema.

    Subparsers recurse into `subcommands`. Positional arguments are emitted
    alongside flags — every agent-visible parameter the command accepts.
    """
    params: dict[str, Any] = {}
    subcommands: dict[str, Any] = {}

    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if isinstance(action, argparse._SubParsersAction):
            for subname, subparser in action.choices.items():
                subcommands[subname] = _parser_to_schema(
                    subparser, f"{command} {subname}")
            continue

        dest = action.dest
        entry: dict[str, Any] = {
            "type": _action_type_name(action),
            "required": bool(action.required),
        }
        if action.option_strings:
            entry["flag"] = action.option_strings[0]
        else:
            entry["positional"] = True
        if action.help:
            entry["help"] = action.help
        if action.choices is not None:
            entry["choices"] = list(action.choices)
        if (action.default is not None
                and action.default is not argparse.SUPPRESS):
            try:
                json.dumps(action.default)  # ensure serializable
                entry["default"] = action.default
            except (TypeError, ValueError):
                entry["default"] = str(action.default)
        if action.nargs in ("*", "+") or isinstance(action,
                                                    argparse._AppendAction):
            entry["multiple"] = True
        params[dest] = entry

    out: dict[str, Any] = {
        "command": command,
        "description": parser.description or "",
        "params": params,
    }
    if subcommands:
        out["subcommands"] = subcommands
    return out


def maybe_emit_schema(parser: argparse.ArgumentParser, command: str,
                      argv: list[str] | None = None) -> None:
    """If the caller passed --schema, emit the parser schema and exit 0.

    Call this at the top of every script's main() *before* parser.parse_args().
    The intercept is pre-parse so --schema works even when required flags are
    missing — an agent discovering a command should be able to ask for its
    schema without already knowing what the flags are.
    """
    argv = argv if argv is not None else sys.argv[1:]
    if "--schema" not in argv:
        return
    schema = _parser_to_schema(parser, command)
    schema["exit_codes"] = EXIT_CODE_VOCAB
    schema["envelope_version"] = SCHEMA_VERSION
    ok(schema)
    sys.exit(0)


# ---------- idempotency cache ----------
#
# The cache is a directory of JSON files, one per idempotency key. A cache
# entry stores `{response, signature, cached_at}`. When an agent retries a
# command with the same `--idempotency-key`, the cached response is returned
# unchanged so repeated calls do not re-spend API budget or re-mutate state.
#
# Cache directory precedence: $SCHOLAR_CACHE_DIR > .scholar_cache/ in cwd.
# There is no TTL — the agent (or a human) flushes stale keys manually. This
# is deliberate: an idempotency key names a *specific run*, not a time window,
# so silent expiry would violate the contract.

CACHE_ENTRY_VERSION = 1


def cache_dir() -> Path:
    """Return the cache directory path, creating it on first use."""
    d = Path(os.environ.get("SCHOLAR_CACHE_DIR", ".scholar_cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_path_for(key: str) -> Path:
    """Map an idempotency key to its cache file path.

    Keys are sanitized to safe filenames: the raw key is hashed and the
    resulting hex prefix is used as the filename. This means arbitrary
    user-supplied key strings (including `/`, whitespace, unicode) are safe.
    """
    safe = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return cache_dir() / f"{safe}.json"


def command_signature(args: argparse.Namespace,
                      *, exclude: tuple[str, ...] = ()) -> str:
    """Hash an argparse.Namespace into a short signature.

    Used to detect idempotency-key collisions: the same key MUST see the
    same (semantically meaningful) arguments. `exclude` names fields that
    do not affect output (e.g. `email` for polite-pool identification).
    The `idempotency_key` field is always excluded.
    """
    ignored = set(exclude) | {"idempotency_key", "dry_run", "schema"}
    fields = {k: v for k, v in vars(args).items()
              if k not in ignored and not k.startswith("_")}
    blob = json.dumps(fields, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def read_cache(key: str) -> dict[str, Any] | None:
    """Read a cache entry by key, or None if missing/corrupt."""
    path = cache_path_for(key)
    if not path.exists():
        return None
    try:
        entry = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(entry, dict) or "response" not in entry:
        return None
    return entry


def write_cache(key: str, response: dict[str, Any], *,
                signature: str | None = None) -> None:
    """Persist a cache entry for an idempotency key."""
    path = cache_path_for(key)
    entry = {
        "version": CACHE_ENTRY_VERSION,
        "key": key,
        "signature": signature,
        "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "response": response,
    }
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2))
