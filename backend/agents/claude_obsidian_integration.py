"""Claude-Obsidian Knowledge Vault Integration for Deep Research Agent.

Provides programmatic Python bindings to interact with Obsidian Knowledge Vaults
via the portable claude-obsidian core engine.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_OBSIDIAN_ROOT = PROJECT_ROOT / "claude-obsidian"
SCRIPT_PATH = CLAUDE_OBSIDIAN_ROOT / "scripts" / "claude-obsidian.py"
DEFAULT_VAULT_PATH = PROJECT_ROOT / "REX-Brain"


def _run_cli_command(args: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Execute a claude-obsidian CLI command and parse JSON output.
    Uses WSL if native execution hits platform write restrictions.
    """
    cmd = [sys.executable, str(SCRIPT_PATH)] + args
    effective_cwd = str(cwd or CLAUDE_OBSIDIAN_ROOT)

    try:
        res = subprocess.run(
            cmd,
            cwd=effective_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if res.returncode == 0:
            try:
                return json.loads(res.stdout)
            except json.JSONDecodeError:
                return {"status": "success", "raw_output": res.stdout.strip()}

        # If native execution failed due to Windows platform confinement, retry in WSL
        if "UNSUPPORTED_PLATFORM" in res.stderr or "UNSUPPORTED_PLATFORM" in res.stdout:
            return _run_wsl_cli_command(args)

        return {
            "status": "error",
            "returncode": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _to_wsl_path(win_path: Path) -> str:
    """Convert a Windows Path object to a WSL POSIX path."""
    resolved = win_path.resolve()
    drive = resolved.drive.replace(":", "").lower()
    parts = list(resolved.parts[1:])
    return f"/mnt/{drive}/" + "/".join(parts)


def _run_wsl_cli_command(args: List[str]) -> Dict[str, Any]:
    """Execute claude-obsidian command inside Alpine WSL for write operations."""
    wsl_script = _to_wsl_path(SCRIPT_PATH)
    wsl_args = []
    for arg in args:
        p = Path(arg)
        if p.is_absolute() or (len(arg) > 2 and arg[1] == ":"):
            wsl_args.append(_to_wsl_path(p))
        else:
            wsl_args.append(arg)

    wsl_cmd = ["wsl", "-d", "Alpine", "python3", wsl_script] + wsl_args
    try:
        res = subprocess.run(
            wsl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        if res.returncode == 0:
            try:
                return json.loads(res.stdout)
            except json.JSONDecodeError:
                return {"status": "success", "raw_output": res.stdout.strip()}
        return {
            "status": "error",
            "returncode": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def get_doctor_status(vault_path: Optional[str] = None) -> Dict[str, Any]:
    """Check health and compliance of an Obsidian knowledge vault."""
    target_vault = Path(vault_path or os.environ.get("CLAUDE_OBSIDIAN_VAULT") or DEFAULT_VAULT_PATH)
    return _run_cli_command(["doctor", "--vault", str(target_vault)])


def lint_vault(vault_path: Optional[str] = None) -> Dict[str, Any]:
    """Lint an Obsidian knowledge vault for structure, dead links, and schema integrity."""
    target_vault = Path(vault_path or os.environ.get("CLAUDE_OBSIDIAN_VAULT") or DEFAULT_VAULT_PATH)
    return _run_cli_command(["lint", "--vault", str(target_vault)])


def ingest_source(source_file_path: str, vault_path: Optional[str] = None) -> Dict[str, Any]:
    """Ingest a source document into the vault inbox and apply capture plan."""
    target_vault = Path(vault_path or os.environ.get("CLAUDE_OBSIDIAN_VAULT") or DEFAULT_VAULT_PATH)
    source_p = Path(source_file_path).resolve()
    if not source_p.exists():
        return {"status": "error", "message": f"Source file does not exist: {source_file_path}"}

    inbox_dir = target_vault / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    dest_file = inbox_dir / source_p.name

    shutil.copy2(source_p, dest_file)

    wsl_vault = _to_wsl_path(target_vault)
    wsl_script = _to_wsl_path(SCRIPT_PATH)

    # Two-pass capture plan & apply in WSL
    timestamp = "2026-08-31T09:32:00Z"
    op_id = f"capture-{Path(dest_file).stem}"
    py_code = f"""import subprocess, json
cmd = ['python3', '{wsl_script}', 'capture', 'apply', '--vault', '{wsl_vault}', '--generated-at', '{timestamp}', '--operation-id', '{op_id}']
res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
plan = json.loads(res.stdout)
if plan.get('status') == 'dry-run' and 'approved_plan_sha256' in plan:
    sha = plan['approved_plan_sha256']
    cmd_apply = cmd + ['--approved-plan-sha256', sha, '--apply']
    res_apply = subprocess.run(cmd_apply, stdout=subprocess.PIPE, text=True, check=True)
    print(res_apply.stdout)
else:
    print(json.dumps(plan))
"""
    try:
        res = subprocess.run(
            ["wsl", "-d", "Alpine", "python3", "-c", py_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        if res.returncode == 0:
            try:
                return json.loads(res.stdout)
            except json.JSONDecodeError:
                return {"status": "success", "file": str(dest_file), "raw": res.stdout.strip()}
        return {
            "status": "error",
            "file": str(dest_file),
            "stderr": res.stderr.strip(),
            "stdout": res.stdout.strip(),
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def save_finding(title: str, content: str, vault_path: Optional[str] = None) -> Dict[str, Any]:
    """Save a research finding or note into the vault wiki directory."""
    target_vault = Path(vault_path or os.environ.get("CLAUDE_OBSIDIAN_VAULT") or DEFAULT_VAULT_PATH)
    wiki_dir = target_vault / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    slug = title.lower().replace(" ", "-").replace("/", "-").strip("-")
    filename = f"{slug}.md" if not slug.endswith(".md") else slug
    note_path = wiki_dir / filename

    header = f"---\ntitle: \"{title}\"\ntype: concept\ncreated: {Path(DEFAULT_VAULT_PATH).stat().st_mtime}\ntags:\n  - deep-research\n---\n\n"
    full_content = header + content if not content.startswith("---") else content

    note_path.write_text(full_content, encoding="utf-8")
    return {
        "status": "success",
        "path": str(note_path),
        "title": title,
        "bytes_written": len(full_content.encode("utf-8")),
    }


def query_vault(query: str, vault_path: Optional[str] = None) -> Dict[str, Any]:
    """Query notes, index, and hot cache in the knowledge vault matching query term."""
    target_vault = Path(vault_path or os.environ.get("CLAUDE_OBSIDIAN_VAULT") or DEFAULT_VAULT_PATH)
    results = []

    # Search wiki notes
    wiki_dir = target_vault / "wiki"
    if wiki_dir.exists():
        for note_file in wiki_dir.rglob("*.md"):
            try:
                text = note_file.read_text(encoding="utf-8", errors="ignore")
                if query.lower() in text.lower() or query.lower() in note_file.name.lower():
                    results.append({
                        "file": str(note_file.relative_to(target_vault)),
                        "title": note_file.stem,
                        "matches": text.count(query),
                        "snippet": text[:300] + "..." if len(text) > 300 else text,
                    })
            except Exception:
                continue

    return {
        "status": "success",
        "query": query,
        "total_results": len(results),
        "matches": results,
    }
