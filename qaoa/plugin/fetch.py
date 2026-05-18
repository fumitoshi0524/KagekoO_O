"""Fetch plugin artifacts (Claude Code marketplace source types)."""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Failed to materialize a plugin directory."""


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    try:
        subprocess.run(
            cmd,
            check=True,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise FetchError(f"Command not found: {cmd[0]}") from e
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        raise FetchError(f"Command failed: {' '.join(cmd)}: {err}") from e


def _safe_plugin_name(name: str) -> str:
    out = []
    for c in name:
        if c.isalnum() or c in "._-":
            out.append(c)
        else:
            out.append("_")
    s = "".join(out).strip("._")
    return s[:80] if s else "plugin"


def stable_cache_subdir(plugin_name: str, source_fingerprint: str) -> str:
    h = hashlib.sha256(source_fingerprint.encode("utf-8")).hexdigest()[:12]
    return f"{_safe_plugin_name(plugin_name)}-{h}"


def _ensure_empty_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _copy_tree(src: Path, dest: Path) -> None:
    if not src.is_dir():
        raise FetchError(f"Not a directory: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _github_repo_url(repo: str) -> str:
    r = repo.strip()
    if r.startswith("git@") or r.startswith("https://") or r.startswith("http://"):
        return r
    if "/" in r and " " not in r:
        return f"https://github.com/{r}.git"
    raise FetchError(f"Invalid github repo: {repo!r}")


def _git_clone(
    url: str,
    dest: Path,
    *,
    ref: str | None = None,
    sha: str | None = None,
    sparse_path: str | None = None,
) -> None:
    _ensure_empty_dir(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if sparse_path:
        _run(["git", "clone", "--filter=blob:none", "--sparse", url, str(dest)])
        _run(["git", "-C", str(dest), "sparse-checkout", "set", sparse_path])
        if ref:
            _run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin", ref])
            _run(["git", "-C", str(dest), "checkout", ref])
        elif sha:
            _run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin", sha])
            _run(["git", "-C", str(dest), "checkout", sha])
        else:
            _run(["git", "-C", str(dest), "sparse-checkout", "reapply"])
    else:
        depth_args: list[str] = ["--depth", "1"]
        if ref:
            _run(["git", "clone", *depth_args, "--branch", ref, url, str(dest)])
        else:
            _run(["git", "clone", *depth_args, url, str(dest)])
        if sha:
            _run(["git", "-C", str(dest), "fetch", "origin", sha])
            _run(["git", "-C", str(dest), "checkout", sha])


def _copy_subpath(repo: Path, subpath: str, dest: Path) -> None:
    inner = (repo / subpath).resolve()
    if not str(inner).startswith(str(repo.resolve())):
        raise FetchError("git-subdir path escapes repository")
    if not inner.is_dir():
        raise FetchError(f"git-subdir not found: {subpath}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(inner, dest)


def fetch_plugin_source(
    *,
    source: Any,
    dest: Path,
    marketplace_root: Path,
    plugin_root_prefix: str = "",
) -> None:
    """Materialize plugin files into ``dest`` (directory).

    ``source`` follows Claude Code marketplace.json (string path or object).
    """
    mroot = marketplace_root.resolve()
    base = mroot
    if plugin_root_prefix:
        base = (mroot / plugin_root_prefix).resolve()
        if not str(base).startswith(str(mroot)):
            raise FetchError("metadata.pluginRoot escapes marketplace root")

    if isinstance(source, str):
        s = source.strip()
        if s.startswith("./") or s.startswith(".\\"):
            rel = Path(s[2:])
        elif s.startswith("/") or (len(s) > 1 and s[1] == ":"):
            src_path = Path(s).expanduser().resolve()
            if not src_path.is_dir():
                raise FetchError(f"Local plugin path not found: {src_path}")
            _copy_tree(src_path, dest)
            return
        else:
            rel = Path(s)
        src_path = (base / rel).resolve()
        if not str(src_path).startswith(str(mroot)):
            raise FetchError("Relative plugin source escapes marketplace root")
        if not src_path.is_dir():
            raise FetchError(f"Plugin directory not found: {src_path}")
        _copy_tree(src_path, dest)
        return

    if not isinstance(source, dict):
        raise FetchError(f"Unsupported plugin source type: {type(source).__name__}")

    st = source.get("source")
    if st == "github":
        repo = source.get("repo")
        if not isinstance(repo, str) or not repo:
            raise FetchError("github source missing repo")
        url = _github_repo_url(repo)
        ref = source.get("ref") if isinstance(source.get("ref"), str) else None
        sha = source.get("sha") if isinstance(source.get("sha"), str) else None
        with tempfile.TemporaryDirectory() as tmp:
            clone_root = Path(tmp) / "repo"
            _git_clone(url, clone_root, ref=ref, sha=sha)
            _copy_tree(clone_root, dest)
        return

    if st == "url":
        url = source.get("url")
        if not isinstance(url, str) or not url:
            raise FetchError("url source missing url")
        ref = source.get("ref") if isinstance(source.get("ref"), str) else None
        sha = source.get("sha") if isinstance(source.get("sha"), str) else None
        with tempfile.TemporaryDirectory() as tmp:
            clone_root = Path(tmp) / "repo"
            _git_clone(url, clone_root, ref=ref, sha=sha)
            _copy_tree(clone_root, dest)
        return

    if st == "git-subdir":
        url_raw = source.get("url")
        sub = source.get("path")
        if not isinstance(url_raw, str) or not isinstance(sub, str):
            raise FetchError("git-subdir requires url and path")
        if "://" in url_raw or url_raw.startswith("git@"):
            url = url_raw
        elif "/" in url_raw and url_raw.count("/") == 1:
            url = _github_repo_url(url_raw)
        else:
            url = url_raw
        if not url.endswith(".git") and "github.com" in url and not url.endswith("/"):
            url = url + ".git"
        ref = source.get("ref") if isinstance(source.get("ref"), str) else None
        sha = source.get("sha") if isinstance(source.get("sha"), str) else None
        with tempfile.TemporaryDirectory() as tmp:
            clone_root = Path(tmp) / "repo"
            try:
                _git_clone(url, clone_root, ref=ref, sha=sha, sparse_path=sub)
            except FetchError:
                if clone_root.exists():
                    shutil.rmtree(clone_root, ignore_errors=True)
                _git_clone(url, clone_root, ref=ref, sha=sha, sparse_path=None)
            _copy_subpath(clone_root, sub, dest)
        return

    if st == "npm":
        package = source.get("package")
        if not isinstance(package, str) or not package:
            raise FetchError("npm source missing package")
        version = source.get("version") if isinstance(source.get("version"), str) else None
        registry = source.get("registry") if isinstance(source.get("registry"), str) else None
        spec = f"{package}@{version}" if version else package
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            cmd = ["npm", "pack", spec, "--pack-destination", str(tdir)]
            if registry:
                cmd.extend(["--registry", registry])
            _run(cmd)
            tgzs = list(tdir.glob("*.tgz"))
            if not tgzs:
                raise FetchError("npm pack produced no .tgz")
            extract = tdir / "extract"
            extract.mkdir()
            with tarfile.open(tgzs[0], "r:gz") as tf:
                tf.extractall(extract)
            # npm pack yields package/ inside tarball
            roots = [p for p in extract.iterdir() if p.is_dir()]
            if len(roots) != 1:
                raise FetchError("npm package layout unexpected")
            _copy_tree(roots[0], dest)
        return

    if st == "pip":
        package = source.get("package")
        if not isinstance(package, str) or not package:
            raise FetchError("pip source missing package")
        version = source.get("version") if isinstance(source.get("version"), str) else None
        index = source.get("index") if isinstance(source.get("index"), str) else None
        spec = f"{package}=={version}" if version else package
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            cmd = [sys.executable, "-m", "pip", "download", spec, "-d", str(tdir), "--no-deps"]
            if index:
                cmd.extend(["-i", index])
            _run(cmd)
            wheels = list(tdir.glob("*.whl"))
            zips = list(tdir.glob("*.zip"))
            if not wheels and not zips:
                raise FetchError("pip download produced no wheel/zip")
            archive = wheels[0] if wheels else zips[0]
            extract = tdir / "extract"
            extract.mkdir()
            if archive.suffix == ".whl":
                with zipfile.ZipFile(archive, "r") as zf:
                    zf.extractall(extract)
            else:
                with zipfile.ZipFile(archive, "r") as zf:
                    zf.extractall(extract)
            # find deepest directory that looks like a plugin
            candidates: list[Path] = []
            for p in extract.rglob(".claude-plugin"):
                if p.is_dir():
                    candidates.append(p.parent)
            if not candidates:
                for p in extract.rglob("SKILL.md"):
                    candidates.append(p.parent)
            if not candidates:
                roots = [p for p in extract.iterdir() if p.is_dir()]
                if len(roots) == 1:
                    candidates.append(roots[0])
            if not candidates:
                raise FetchError("pip package: could not locate plugin root")
            candidates.sort(key=lambda x: len(x.parts))
            _copy_tree(candidates[0], dest)
        return

    raise FetchError(f"Unknown source discriminator: {st!r}")
