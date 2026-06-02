#!/usr/bin/env python3
"""
SDEV - Server Deployment Environment

A lightweight Linux CLI for FiveM/RedM FXServer management.

v0.5:
- universal `sdev adoptserver`
- automatic cache detection
- prompts after artifact install/update: Clear cache? [Y/n]
- standalone `sdev clear-cache`
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


APP = "sdev"
FULL_NAME = "SDEV - Server Deployment Environment"
VERSION = "0.5.0"

CONFIG_FILE = "sdev.json"
LOCK_FILE = "sdev.lock.json"

JG_API_V2 = "https://artifacts.jgscripts.com/jsonv2"
JG_CHECK_API = "https://artifacts.jgscripts.com/check?artifact={artifact}"

DEFAULT_CONFIG = {
    "name": "fxserver",
    "profile": "auto",
    "artifact_source": "jgscripts",
    "artifact_url": "",
    "artifact_extract_dir": "artifacts",
    "artifact_clean_paths": ["artifacts"],
    "artifact_expected_dir": "",
    "server_dir": ".",
    "resources_dir": "resources",
    "server_cfg": "server.cfg",
    "cache_dir": "cache",
    "clear_cache_after_artifact_update": "ask",
    "run_command": "./run.sh +exec {server_cfg}"
}


class SdevError(Exception):
    pass


def project_root() -> Path:
    return Path.cwd()


def config_path() -> Path:
    return project_root() / CONFIG_FILE


def lock_path() -> Path:
    return project_root() / LOCK_FILE


def rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(project_root().resolve()))
    except ValueError:
        return str(path)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_config() -> dict[str, Any]:
    cfg = load_json(config_path(), None)
    if cfg is None:
        raise SdevError(f"No {CONFIG_FILE} found. Run: {APP} adoptserver")
    merged = DEFAULT_CONFIG.copy()
    merged.update(cfg)

    # Backward compatibility with older configs.
    if "artifacts_dir" in cfg and "artifact_extract_dir" not in cfg:
        merged["artifact_extract_dir"] = cfg["artifacts_dir"]
        merged["artifact_clean_paths"] = [cfg["artifacts_dir"]]

    if "cache_dir" not in cfg:
        merged["cache_dir"] = "cache"

    if "clear_cache_after_artifact_update" not in cfg:
        merged["clear_cache_after_artifact_update"] = "ask"

    return merged


def load_lock() -> dict[str, Any]:
    return load_json(lock_path(), {"resources": {}, "artifact": {}})


def save_lock(lock: dict[str, Any]) -> None:
    save_json(lock_path(), lock)


def ensure_tools(*tools: str) -> None:
    missing = [t for t in tools if shutil.which(t) is None]
    if missing:
        raise SdevError("Missing required tools: " + ", ".join(missing))


def sh(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("+ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def http_get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": f"SDEV/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if getattr(response, "status", 200) >= 400:
                raise SdevError(f"HTTP {response.status} while requesting {url}")
            data = response.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.URLError as e:
        raise SdevError(f"Could not reach {url}: {e}") from e
    except json.JSONDecodeError as e:
        raise SdevError(f"Invalid JSON from {url}: {e}") from e


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": f"SDEV/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            if getattr(response, "status", 200) >= 400:
                raise SdevError(f"Download failed with HTTP {response.status}: {url}")
            with dest.open("wb") as f:
                shutil.copyfileobj(response, f)
    except urllib.error.URLError as e:
        raise SdevError(f"Download failed: {e}") from e


def is_inside_project(path: Path) -> bool:
    root = project_root().resolve()
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def is_dangerous_clean_path(path: Path) -> bool:
    root = project_root().resolve()
    resolved = path.resolve()

    if str(path).strip() in ["", ".", "./", "/", "~"]:
        return True

    if resolved == root:
        return True

    if str(resolved) == "/":
        return True

    try:
        resolved.relative_to(root)
    except ValueError:
        return True

    return False


def clean_paths(paths: list[str]) -> None:
    for raw in paths:
        target = Path(raw)
        if is_dangerous_clean_path(target):
            raise SdevError(f"Refusing to clean dangerous path: {raw}")

        if target.exists():
            print(f"Cleaning {target}")
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        else:
            print(f"Clean path does not exist, skipping: {target}")


def safe_extract_tar(tar: tarfile.TarFile, dest: Path) -> None:
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if not str(target).startswith(str(dest_resolved)):
            raise SdevError(f"Unsafe tar path blocked: {member.name}")
    tar.extractall(dest)


def extract_archive(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()

    if name.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as z:
            z.extractall(dest)
        return

    if any(name.endswith(ext) for ext in [".tar.xz", ".tar.gz", ".tgz", ".tar"]):
        with tarfile.open(archive, "r:*") as t:
            safe_extract_tar(t, dest)
        return

    raise SdevError(f"Unsupported archive type: {archive.name}")


def postprocess_artifact_dir(cfg: dict[str, Any]) -> None:
    """
    FiveM Linux artifacts usually extract to ./alpine.
    If the existing server uses a different folder name, SDEV can rename the extracted folder.
    Example: alpine -> alpina
    """
    expected = str(cfg.get("artifact_expected_dir", "")).strip()
    extract_dir = Path(cfg.get("artifact_extract_dir", "artifacts"))

    if not expected or expected == "alpine":
        return

    extracted_alpine = extract_dir / "alpine"
    expected_path = extract_dir / expected

    if extracted_alpine.exists() and not expected_path.exists():
        print(f"Renaming extracted artifact folder: {extracted_alpine} -> {expected_path}")
        extracted_alpine.rename(expected_path)


def resolve_cache_dir(cfg: dict[str, Any]) -> Path:
    raw = str(cfg.get("cache_dir", "cache")).strip() or "cache"
    path = Path(raw)

    # Protect against accidentally using absolute /cache on the host.
    # SDEV operates inside the server folder; cache paths must be relative or inside current workspace.
    if path.is_absolute() and not is_inside_project(path):
        raise SdevError(
            f"Refusing cache path outside current server folder: {path}. "
            "Use a relative path like 'cache'."
        )

    return path


def clear_cache_dir(cfg: dict[str, Any], create_after: bool = True) -> bool:
    cache_dir = resolve_cache_dir(cfg)

    if is_dangerous_clean_path(cache_dir):
        raise SdevError(f"Refusing to clear dangerous cache path: {cache_dir}")

    if not cache_dir.exists():
        print(f"Cache folder not found, skipping: {cache_dir}")
        if create_after:
            cache_dir.mkdir(parents=True, exist_ok=True)
        return False

    if not cache_dir.is_dir():
        raise SdevError(f"Cache path exists but is not a folder: {cache_dir}")

    print(f"Clearing cache folder: {cache_dir}")

    for child in cache_dir.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()

    if create_after:
        cache_dir.mkdir(parents=True, exist_ok=True)

    print("Cache cleared.")
    return True


def ask_yes_no(question: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"

    while True:
        answer = input(f"{question} {suffix} ").strip().lower()

        if not answer:
            return default_yes

        if answer in ["y", "yes", "j", "ja"]:
            return True

        if answer in ["n", "no", "nein"]:
            return False

        print("Please answer with y or n.")


def maybe_clear_cache_after_artifact_update(cfg: dict[str, Any], force_yes: bool = False, force_no: bool = False) -> None:
    mode = str(cfg.get("clear_cache_after_artifact_update", "ask")).strip().lower()
    cache_dir = resolve_cache_dir(cfg)

    if force_no or mode in ["false", "no", "never", "disabled", "off"]:
        print("Cache clear skipped.")
        return

    if force_yes or mode in ["true", "yes", "always", "on"]:
        clear_cache_dir(cfg)
        return

    if mode != "ask":
        print(f"Unknown clear_cache_after_artifact_update mode '{mode}', using ask.")

    if ask_yes_no(f"Clear cache folder '{cache_dir}' now?", default_yes=True):
        clear_cache_dir(cfg)
    else:
        print("Cache clear skipped.")


def looks_like_git_url(source: str) -> bool:
    return (
        source.endswith(".git")
        or source.startswith("git@")
        or re.match(r"^https?://(www\.)?github\.com/[^/]+/[^/]+/?$", source) is not None
    )


def normalize_github_url(source: str) -> str:
    source = source.rstrip("/")
    if source.startswith("https://github.com/") and not source.endswith(".git"):
        return source + ".git"
    return source


def resource_name_from_source(source: str) -> str:
    parsed = urlparse(source)
    candidate = Path(parsed.path.rstrip("/")).name
    if candidate.endswith(".git"):
        candidate = candidate[:-4]
    if candidate in ["", "archive", "download"]:
        candidate = "resource"
    candidate = re.sub(r"[^a-zA-Z0-9_.-]+", "-", candidate).strip("-._")
    return candidate or "resource"


def has_fxserver_binary(path: Path) -> bool:
    if not path.is_dir():
        return False

    possible = [
        path / "opt/cfx-server/FXServer",
        path / "FXServer",
        path / "run.sh"
    ]

    return any(p.exists() for p in possible)


def score_artifact_candidate(path: Path) -> int:
    score = 0
    name = path.name.lower()

    if name == "alpine":
        score += 100
    if name == "alpina":
        score += 95
    if name in ["artifacts", "artifact", "fxserver", "server"]:
        score += 30

    if (path / "opt/cfx-server/FXServer").exists():
        score += 100
    if (path / "opt/cfx-server/citizen").exists():
        score += 40
    if (path / "opt/cfx-server/ld-musl-x86_64.so.1").exists():
        score += 40
    if (path / "run.sh").exists():
        score += 20

    depth = len(path.relative_to(project_root()).parts) if path != project_root() else 0
    score -= depth * 3
    return score


def scan_artifact_folder(max_depth: int = 4) -> Path | None:
    root = project_root()

    preferred = [
        root / "alpine",
        root / "alpina",
        root / "artifacts/alpine",
        root / "artifacts/alpina",
        root / "server/alpine",
        root / "server/artifacts/alpine",
        root / "fxserver/alpine",
    ]

    for p in preferred:
        if has_fxserver_binary(p):
            return p

    candidates: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_dir():
            continue

        try:
            depth = len(p.relative_to(root).parts)
        except ValueError:
            continue

        if depth > max_depth:
            continue

        if has_fxserver_binary(p):
            candidates.append(p)

    if not candidates:
        return None

    candidates.sort(key=score_artifact_candidate, reverse=True)
    return candidates[0]


def score_server_cfg_candidate(path: Path) -> int:
    score = 0
    text_path = str(path).replace("\\", "/").lower()

    if text_path == "server.cfg":
        score += 100
    if text_path.endswith("/server.cfg"):
        score += 50
    if text_path.startswith("server-data/"):
        score += 40
    if text_path.startswith("txdata/"):
        score += 20

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")[:6000].lower()
        if "endpoint_add_tcp" in content:
            score += 30
        if "sv_licensekey" in content:
            score += 20
        if "ensure " in content or "start " in content:
            score += 20
    except Exception:
        pass

    depth = len(path.relative_to(project_root()).parts)
    score -= depth * 2
    return score


def scan_server_cfg(max_depth: int = 5) -> Path | None:
    root = project_root()

    preferred = [
        root / "server.cfg",
        root / "server-data/server.cfg",
        root / "server/server.cfg",
        root / "txData/default/server.cfg",
    ]

    for p in preferred:
        if p.exists() and p.is_file():
            return p

    candidates: list[Path] = []
    for p in root.rglob("server.cfg"):
        if not p.is_file():
            continue
        try:
            depth = len(p.relative_to(root).parts)
        except ValueError:
            continue
        if depth <= max_depth:
            candidates.append(p)

    if not candidates:
        return None

    candidates.sort(key=score_server_cfg_candidate, reverse=True)
    return candidates[0]


def resource_folder_has_resources(path: Path) -> bool:
    if not path.is_dir():
        return False

    try:
        children = [c for c in path.iterdir() if c.is_dir()]
    except Exception:
        return False

    if not children:
        return False

    hits = 0
    for child in children[:200]:
        if (child / "fxmanifest.lua").exists() or (child / "__resource.lua").exists():
            hits += 1

    if hits > 0:
        return True

    return path.name.lower() == "resources" and len(children) > 0


def score_resources_candidate(path: Path) -> int:
    score = 0
    text_path = str(path).replace("\\", "/").lower()

    if text_path == "resources":
        score += 100
    if text_path.endswith("/resources"):
        score += 60
    if text_path.startswith("server-data/"):
        score += 35
    if text_path.startswith("server/"):
        score += 20
    if text_path.startswith("txdata/"):
        score += 10

    try:
        children = [c for c in path.iterdir() if c.is_dir()]
        score += min(len(children), 30)
        for child in children[:200]:
            if (child / "fxmanifest.lua").exists() or (child / "__resource.lua").exists():
                score += 5
    except Exception:
        pass

    depth = len(path.relative_to(project_root()).parts)
    score -= depth * 2
    return score


def scan_resources_dir(max_depth: int = 5) -> Path | None:
    root = project_root()

    preferred = [
        root / "resources",
        root / "server-data/resources",
        root / "server/resources",
        root / "txData/default/resources",
    ]

    for p in preferred:
        if resource_folder_has_resources(p):
            return p

    candidates: list[Path] = []
    for p in root.rglob("resources"):
        if not p.is_dir():
            continue
        try:
            depth = len(p.relative_to(root).parts)
        except ValueError:
            continue
        if depth <= max_depth and resource_folder_has_resources(p):
            candidates.append(p)

    if not candidates:
        return None

    candidates.sort(key=score_resources_candidate, reverse=True)
    return candidates[0]


def scan_cache_dir(max_depth: int = 4) -> Path:
    root = project_root()

    preferred = [
        root / "cache",
        root / "server-data/cache",
        root / "server/cache",
        root / "txData/default/cache",
    ]

    for p in preferred:
        if p.exists() and p.is_dir():
            return p

    candidates: list[Path] = []
    for p in root.rglob("cache"):
        if not p.is_dir():
            continue
        try:
            depth = len(p.relative_to(root).parts)
        except ValueError:
            continue
        if depth <= max_depth:
            candidates.append(p)

    if candidates:
        candidates.sort(key=lambda p: (p.name.lower() == "cache", -len(p.relative_to(root).parts)), reverse=True)
        return candidates[0]

    # Default to ./cache even if it does not exist yet.
    return root / "cache"


def build_run_command_for_artifact(artifact_folder: Path | None, server_cfg: str) -> str:
    if artifact_folder is None:
        return DEFAULT_CONFIG["run_command"]

    artifact_rel = rel(artifact_folder).replace("\\", "/")

    if (artifact_folder / "opt/cfx-server/FXServer").exists():
        return (
            f"./{artifact_rel}/opt/cfx-server/ld-musl-x86_64.so.1 "
            f"--library-path ./{artifact_rel}/usr/lib/v8/:./{artifact_rel}/lib/:./{artifact_rel}/usr/lib/ "
            f"./{artifact_rel}/opt/cfx-server/FXServer "
            f"+set citizen_dir ./{artifact_rel}/opt/cfx-server/citizen/ "
            f"+exec {{server_cfg}}"
        )

    if (artifact_folder / "run.sh").exists():
        return f"./{artifact_rel}/run.sh +exec {{server_cfg}}"

    return "./run.sh +exec {server_cfg}"


def make_auto_config(
    artifact_folder: Path | None,
    resources_dir: Path | None,
    server_cfg: Path | None,
    cache_dir: Path | None
) -> dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()

    artifact_expected_dir = ""
    artifact_extract_dir = "artifacts"
    artifact_clean_paths = ["artifacts"]

    if artifact_folder:
        artifact_expected_dir = artifact_folder.name
        artifact_extract_dir = rel(artifact_folder.parent)
        if artifact_extract_dir == "":
            artifact_extract_dir = "."
        artifact_clean_paths = [rel(artifact_folder)]

    resources_rel = rel(resources_dir) if resources_dir else "resources"
    server_cfg_rel = rel(server_cfg) if server_cfg else "server.cfg"
    cache_rel = rel(cache_dir) if cache_dir else "cache"

    cfg.update({
        "name": project_root().name or "fxserver",
        "profile": "auto",
        "artifact_source": "jgscripts",
        "artifact_url": "",
        "artifact_extract_dir": artifact_extract_dir,
        "artifact_clean_paths": artifact_clean_paths,
        "artifact_expected_dir": artifact_expected_dir,
        "server_dir": ".",
        "resources_dir": resources_rel,
        "server_cfg": server_cfg_rel,
        "cache_dir": cache_rel,
        "clear_cache_after_artifact_update": "ask",
        "run_command": build_run_command_for_artifact(artifact_folder, server_cfg_rel)
    })

    return cfg


def import_local_resources(lock: dict[str, Any], resources_dir: Path | None) -> int:
    if not resources_dir or not resources_dir.exists():
        return 0

    lock.setdefault("resources", {})
    count = 0

    for child in sorted(resources_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            if child.name not in lock["resources"]:
                lock["resources"][child.name] = {
                    "type": "local",
                    "source": "",
                    "managed": False
                }
                count += 1

    return count


def adoptserver(args: argparse.Namespace) -> None:
    cfg_file = config_path()

    if cfg_file.exists() and not args.force:
        raise SdevError(f"{CONFIG_FILE} already exists. Use --force to overwrite.")

    artifact_folder = Path(args.artifact_folder) if args.artifact_folder else scan_artifact_folder()
    resources_dir = Path(args.resources_dir) if args.resources_dir else scan_resources_dir()
    server_cfg = Path(args.server_cfg) if args.server_cfg else scan_server_cfg()
    cache_dir = Path(args.cache_dir) if args.cache_dir else scan_cache_dir()

    cfg = make_auto_config(artifact_folder, resources_dir, server_cfg, cache_dir)
    save_json(cfg_file, cfg)

    lock = load_lock()
    lock.setdefault("resources", {})
    lock.setdefault("artifact", {})

    imported = import_local_resources(lock, resources_dir)
    save_lock(lock)

    print("SDEV adopted the current server folder.")
    print("")
    print("Detected layout:")
    print(f"  Artifact folder: {rel(artifact_folder) if artifact_folder else 'NOT FOUND'}")
    print(f"  Resources dir:   {rel(resources_dir) if resources_dir else 'NOT FOUND'}")
    print(f"  Server cfg:      {rel(server_cfg) if server_cfg else 'NOT FOUND'}")
    print(f"  Cache dir:       {rel(cache_dir) if cache_dir else 'cache'}")
    print("")
    print("Generated config:")
    print(f"  Artifact extract:  {cfg['artifact_extract_dir']}")
    print(f"  Artifact clean:    {', '.join(cfg['artifact_clean_paths'])}")
    print(f"  Artifact expected: {cfg['artifact_expected_dir'] or '-'}")
    print(f"  Resources dir:     {cfg['resources_dir']}")
    print(f"  Server cfg:        {cfg['server_cfg']}")
    print(f"  Cache dir:         {cfg['cache_dir']}")
    print(f"  Cache after update:{cfg['clear_cache_after_artifact_update']}")
    print("")
    print(f"Imported local resources as unmanaged: {imported}")

    if not artifact_folder:
        print("")
        print("Warning: No FXServer artifact folder was detected.")
        print("You can rerun with: sdev adoptserver --artifact-folder alpine --force")

    if not resources_dir:
        print("")
        print("Warning: No resources folder was detected.")
        print("You can rerun with: sdev adoptserver --resources-dir resources --force")

    if not server_cfg:
        print("")
        print("Warning: No server.cfg was detected.")
        print("You can rerun with: sdev adoptserver --server-cfg server.cfg --force")


def init(args: argparse.Namespace) -> None:
    cfg_file = config_path()
    if cfg_file.exists() and not args.force:
        raise SdevError(f"{CONFIG_FILE} already exists. Use --force to overwrite.")

    cfg = DEFAULT_CONFIG.copy()
    if args.artifact_url:
        cfg["artifact_url"] = args.artifact_url
        cfg["artifact_source"] = "manual"

    save_json(cfg_file, cfg)
    if not lock_path().exists() or args.force:
        save_lock({"resources": {}, "artifact": {}})

    Path(cfg["resources_dir"]).mkdir(parents=True, exist_ok=True)
    server_cfg_path = Path(cfg["server_cfg"])
    if not server_cfg_path.exists():
        server_cfg_path.write_text(
            "# FXServer config generated by SDEV\n"
            "endpoint_add_tcp \"0.0.0.0:30120\"\n"
            "endpoint_add_udp \"0.0.0.0:30120\"\n"
            "sv_hostname \"FXServer via SDEV\"\n"
            "# sv_licenseKey \"YOUR_KEY\"\n",
            encoding="utf-8"
        )

    print(f"Initialized new {FULL_NAME} workspace.")


def get_recommended_artifact() -> dict[str, Any]:
    data = http_get_json(JG_API_V2)
    recommended = str(data.get("recommendedArtifact", "")).strip()
    linux_link = str(data.get("linuxDownloadLink", "")).strip()

    if not recommended or not linux_link:
        raise SdevError("JG Scripts API did not return recommendedArtifact and linuxDownloadLink.")

    return {
        "artifact": recommended,
        "linux_url": linux_link,
        "windows_url": data.get("windowsDownloadLink", ""),
        "broken_artifacts": data.get("brokenArtifacts", []),
        "source_api": JG_API_V2
    }


def check_artifact_status(artifact: str) -> dict[str, Any]:
    artifact = str(artifact).strip()
    if not artifact:
        raise SdevError("Artifact number is required.")
    return http_get_json(JG_CHECK_API.format(artifact=artifact))


def resolve_artifact_url(args: argparse.Namespace, cfg: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if getattr(args, "url", None):
        return args.url, {"source": "manual-url"}

    use_recommended = (
        getattr(args, "recommended", False)
        or cfg.get("artifact_source") == "jgscripts"
        or not cfg.get("artifact_url")
    )

    if use_recommended:
        rec = get_recommended_artifact()
        return rec["linux_url"], {
            "source": "jgscripts",
            "recommendedArtifact": rec["artifact"],
            "source_api": rec["source_api"]
        }

    return cfg["artifact_url"], {"source": "configured-url"}


def install_artifact(args: argparse.Namespace) -> None:
    cfg = load_config()
    lock = load_lock()

    url, meta = resolve_artifact_url(args, cfg)

    extract_dir = Path(cfg.get("artifact_extract_dir", "artifacts"))
    extract_dir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        clean_paths([str(p) for p in cfg.get("artifact_clean_paths", [])])
        extract_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        archive_name = Path(urlparse(url).path).name or "artifact.tar.xz"
        archive = tmp / archive_name
        download(url, archive)
        extract_archive(archive, extract_dir)

    postprocess_artifact_dir(cfg)

    lock["artifact"] = {
        "url": url,
        "extract_dir": str(extract_dir),
        "clean_paths": cfg.get("artifact_clean_paths", []),
        "expected_dir": cfg.get("artifact_expected_dir", ""),
        **meta
    }
    save_lock(lock)

    if meta.get("recommendedArtifact"):
        print(f"Installed recommended Linux artifact {meta['recommendedArtifact']}.")
    else:
        print("Installed artifact.")

    maybe_clear_cache_after_artifact_update(
        cfg,
        force_yes=getattr(args, "clear_cache", False),
        force_no=getattr(args, "no_cache", False)
    )


def update_artifact(args: argparse.Namespace) -> None:
    cfg = load_config()
    lock = load_lock()

    if args.recommended or lock.get("artifact", {}).get("source") == "jgscripts" or cfg.get("artifact_source") == "jgscripts":
        args.url = None
        args.recommended = True
    else:
        locked_url = lock.get("artifact", {}).get("url")
        if not locked_url:
            raise SdevError("No artifact in lockfile. Use install-artifact first.")
        args.url = locked_url

    args.clean = True
    install_artifact(args)


def artifact_info(args: argparse.Namespace) -> None:
    rec = get_recommended_artifact()
    print(f"Recommended artifact: {rec['artifact']}")
    print(f"Linux download:        {rec['linux_url']}")
    print(f"Windows download:      {rec['windows_url']}")
    print(f"Known issue entries:   {len(rec['broken_artifacts'])}")

    if args.show_broken:
        print("\nArtifacts with reported issues:")
        for item in rec["broken_artifacts"]:
            print(f"- {item.get('artifact')}: {item.get('reason')}")


def check_artifact(args: argparse.Namespace) -> None:
    result = check_artifact_status(args.artifact)
    status = result.get("status", "UNKNOWN")
    print(f"Artifact {args.artifact}: {status}")
    if "reason" in result:
        print(f"Reason: {result['reason']}")


def clear_cache_command(args: argparse.Namespace) -> None:
    cfg = load_config()
    if args.yes or ask_yes_no(f"Clear cache folder '{resolve_cache_dir(cfg)}' now?", default_yes=True):
        clear_cache_dir(cfg)
    else:
        print("Cache clear skipped.")


def set_cache_mode(args: argparse.Namespace) -> None:
    cfg = load_config()
    cfg["clear_cache_after_artifact_update"] = args.mode
    save_json(config_path(), cfg)
    print(f"Set clear_cache_after_artifact_update to: {args.mode}")


def add_resource(args: argparse.Namespace) -> None:
    ensure_tools("git")
    cfg = load_config()
    lock = load_lock()
    source = args.source
    name = args.name or resource_name_from_source(source)
    dest = Path(cfg["resources_dir"]) / name

    if dest.exists() and not args.force:
        raise SdevError(f"Resource already exists: {dest}. Use --force to replace it.")

    if dest.exists():
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)

    if looks_like_git_url(source):
        git_url = normalize_github_url(source)
        sh(["git", "clone", "--depth", "1", git_url, str(dest)])
        lock["resources"][name] = {"type": "git", "source": git_url, "managed": True}
    else:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            filename = Path(urlparse(source).path).name or f"{name}.download"
            downloaded = tmp / filename
            download(source, downloaded)

            if filename.lower().endswith((".zip", ".tar.xz", ".tar.gz", ".tgz", ".tar")):
                extract_archive(downloaded, dest)
                lock["resources"][name] = {"type": "archive", "source": source, "managed": True}
            else:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(downloaded), str(dest / filename))
                lock["resources"][name] = {"type": "file", "source": source, "managed": True}

    save_lock(lock)
    print(f"Resource added: {name}")


def remove_resource(args: argparse.Namespace) -> None:
    cfg = load_config()
    lock = load_lock()
    name = args.name
    dest = Path(cfg["resources_dir"]) / name

    if dest.exists() and not args.lock_only:
        shutil.rmtree(dest)
        print(f"Deleted {dest}")
    elif args.lock_only:
        print(f"Keeping folder, removing only from lockfile: {name}")
    else:
        print(f"No folder found for {name}")

    lock.get("resources", {}).pop(name, None)
    save_lock(lock)
    print(f"Removed from lockfile: {name}")


def update_resources(args: argparse.Namespace) -> None:
    ensure_tools("git")
    cfg = load_config()
    lock = load_lock()
    resources = lock.get("resources", {})

    if not resources:
        print("No resources in lockfile.")
        return

    for name, meta in resources.items():
        dest = Path(cfg["resources_dir"]) / name
        rtype = meta.get("type")
        source = meta.get("source")
        managed = meta.get("managed", True)

        print(f"\n== Updating {name} ==")

        if not managed or rtype == "local":
            print("Skipped: local/unmanaged resource")
            continue

        if rtype == "git" and dest.exists():
            sh(["git", "pull", "--ff-only"], cwd=dest, check=False)
        elif source:
            class Obj:
                pass
            add_args = Obj()
            add_args.source = source
            add_args.name = name
            add_args.force = True
            add_resource(add_args)
        else:
            print(f"Skipped {name}: missing source")


def list_resources(args: argparse.Namespace) -> None:
    lock = load_lock()
    resources = lock.get("resources", {})
    if not resources:
        print("No resources installed.")
        return

    for name, meta in resources.items():
        managed = "managed" if meta.get("managed", True) else "local"
        print(f"{name:30} {meta.get('type', '?'):8} {managed:8} {meta.get('source', '')}")


def run_server(args: argparse.Namespace) -> None:
    cfg = load_config()
    server_cfg = Path(cfg["server_cfg"]).resolve()

    cmd = args.command or cfg.get("run_command", DEFAULT_CONFIG["run_command"])
    cmd = cmd.replace("{server_cfg}", str(server_cfg))

    print(f"Running from {project_root()}: {cmd}")
    os.execvp("bash", ["bash", "-lc", cmd])


def show_status(args: argparse.Namespace) -> None:
    cfg = load_config()
    lock = load_lock()
    artifact = lock.get("artifact", {})

    print(f"{FULL_NAME} v{VERSION}")
    print(f"Project:             {cfg.get('name')}")
    print(f"Profile:             {cfg.get('profile')}")
    print(f"Artifact source:     {artifact.get('source') or cfg.get('artifact_source') or '-'}")
    print(f"Artifact version:    {artifact.get('recommendedArtifact') or '-'}")
    print(f"Artifact URL:        {artifact.get('url') or cfg.get('artifact_url') or '-'}")
    print(f"Artifact extract:    {cfg.get('artifact_extract_dir')}")
    print(f"Artifact clean:      {', '.join(cfg.get('artifact_clean_paths', [])) or '-'}")
    print(f"Artifact expected:   {cfg.get('artifact_expected_dir') or '-'}")
    print(f"Resources dir:       {cfg.get('resources_dir')}")
    print(f"Server cfg:          {cfg.get('server_cfg')}")
    print(f"Cache dir:           {cfg.get('cache_dir')}")
    print(f"Cache after update:  {cfg.get('clear_cache_after_artifact_update')}")
    print(f"Resources in lock:   {len(lock.get('resources', {}))}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=APP, description=FULL_NAME)
    p.add_argument("--version", action="version", version=f"{APP} {VERSION}")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("adoptserver", help="scan current folder and adopt existing FXServer installation")
    s.add_argument("--artifact-folder", default="", help="manual artifact folder override, e.g. alpine or alpina")
    s.add_argument("--resources-dir", default="", help="manual resources folder override")
    s.add_argument("--server-cfg", default="", help="manual server.cfg path override")
    s.add_argument("--cache-dir", default="", help="manual cache folder override, default: detected cache or ./cache")
    s.add_argument("--force", action="store_true", help="overwrite existing sdev.json")
    s.set_defaults(func=adoptserver)

    s = sub.add_parser("init", help="initialize fresh empty SDEV workspace")
    s.add_argument("--artifact-url", default="", help="manual Linux artifact URL")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=init)

    s = sub.add_parser("artifact-info", help="show JG Scripts recommended artifact")
    s.add_argument("--show-broken", action="store_true", help="print known broken artifacts")
    s.set_defaults(func=artifact_info)

    s = sub.add_parser("check-artifact", help="check whether an artifact has reported issues")
    s.add_argument("artifact", help="artifact number, e.g. 30439")
    s.set_defaults(func=check_artifact)

    s = sub.add_parser("install-artifact", help="install FXServer Linux artifact")
    s.add_argument("url", nargs="?", help="manual artifact archive URL; omitted = JG recommended Linux artifact")
    s.add_argument("--recommended", action="store_true", help="force JG Scripts recommended Linux artifact")
    s.add_argument("--clean", action="store_true", help="delete configured artifact_clean_paths before install")
    s.add_argument("--clear-cache", action="store_true", help="clear cache without asking after artifact install")
    s.add_argument("--no-cache", action="store_true", help="do not ask and do not clear cache after artifact install")
    s.set_defaults(func=install_artifact)

    s = sub.add_parser("update-artifact", help="update/reinstall artifact")
    s.add_argument("--recommended", action="store_true", help="force newest JG Scripts recommendation")
    s.add_argument("--clear-cache", action="store_true", help="clear cache without asking after artifact update")
    s.add_argument("--no-cache", action="store_true", help="do not ask and do not clear cache after artifact update")
    s.set_defaults(func=update_artifact)

    s = sub.add_parser("clear-cache", help="clear configured server cache folder")
    s.add_argument("-y", "--yes", action="store_true", help="clear without confirmation")
    s.set_defaults(func=clear_cache_command)

    s = sub.add_parser("cache-mode", help="set cache behavior after artifact updates")
    s.add_argument("mode", choices=["ask", "always", "never"], help="ask = prompt [Y/n], always = clear automatically, never = skip")
    s.set_defaults(func=set_cache_mode)

    s = sub.add_parser("add", help="add resource from Git/GitHub/URL")
    s.add_argument("source")
    s.add_argument("--name")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=add_resource)

    s = sub.add_parser("remove", help="remove resource")
    s.add_argument("name")
    s.add_argument("--lock-only", action="store_true", help="keep folder, remove only from lockfile")
    s.set_defaults(func=remove_resource)

    s = sub.add_parser("update", help="update all managed resources")
    s.set_defaults(func=update_resources)

    s = sub.add_parser("list", help="list resources")
    s.set_defaults(func=list_resources)

    s = sub.add_parser("status", help="show workspace status")
    s.set_defaults(func=show_status)

    s = sub.add_parser("run", help="run FXServer")
    s.add_argument("--command", help="override command")
    s.set_defaults(func=run_server)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode or 1
    except SdevError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
