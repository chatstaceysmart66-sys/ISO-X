#!/usr/bin/env python3
"""Local, repository-backed discovery and package operations for ISO-X Store."""
from __future__ import annotations

import configparser
import gzip
import io
import itertools
import locale
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import yaml


PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]{0,127}$")
FLATPAK_ID_RE = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+$")
VERSION_RE = re.compile(r"^[A-Za-z0-9.+:~_-]+$")
FLATHUB_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"
APPSTREAM_ROOTS = (
    Path("/var/lib/app-info/xmls"),
    Path("/var/cache/swcatalog/xml"),
    Path("/usr/share/metainfo"),
    Path("/usr/share/appdata"),
    Path("/var/lib/apt/lists"),
)
ICON_ROOTS = (
    Path("/usr/share/app-info/icons"),
    Path("/var/cache/swcatalog/icons"),
    Path("/usr/share/icons"),
)
CATEGORY_LABELS = {
    "AudioVideo": "Media",
    "Audio": "Media",
    "Video": "Media",
    "Education": "Education",
    "Office": "Office",
    "Game": "Games",
    "Graphics": "Graphics",
    "Network": "Internet",
    "WebBrowser": "Internet",
    "Development": "Development",
    "Utility": "System",
    "System": "System",
    "Science": "Education",
    "Education": "Education",
}
SEARCH_CATEGORIES = {
    "Education": ("education", "reading", "dictionary"),
    "Office": ("office", "document", "spreadsheet", "pdf"),
    "Internet": ("browser", "internet", "mail", "chat"),
    "Graphics": ("graphics", "drawing", "image"),
    "Media": ("audio", "video", "media"),
    "Development": ("development", "editor", "terminal"),
    "System": ("system", "network", "disk"),
    "Games": ("game", "gaming"),
    "Windows": ("wine", "windows", "bottles"),
}


@dataclass(frozen=True)
class StoreApp:
    app_id: str
    source: str
    source_name: str
    name: str
    summary: str
    category: str
    package_id: str
    version: str = ""
    installed: bool = False
    update_available: bool = False
    icon: str = ""
    developer: str = ""
    license: str = ""
    size_bytes: int | None = None
    architecture: str = ""
    desktop_id: str = ""
    launchable: bool = False
    description: str = ""
    remote: str = ""
    branch: str = ""


@dataclass(frozen=True)
class OperationResult:
    success: bool
    message: str
    returncode: int | None = None


def _run(
    argv: Sequence[str],
    *,
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def _localized_text(parent: ET.Element | None, tag: str, language: str) -> str:
    if parent is None:
        return ""
    nodes = parent.findall(tag)
    if not nodes:
        return ""
    preferred = [language, language.split("_", 1)[0], "C"]
    for wanted in preferred:
        for node in nodes:
            if node.get("{http://www.w3.org/XML/1998/namespace}lang", "C") == wanted:
                return " ".join("".join(node.itertext()).split())
    return " ".join("".join(nodes[0].itertext()).split())


def _category(labels: Sequence[str]) -> str:
    for label in labels:
        if label in CATEGORY_LABELS:
            return CATEGORY_LABELS[label]
    return "Other"


def _safe_local_icon(value: str, roots: Sequence[Path] = ICON_ROOTS) -> str:
    if not value or value.startswith(("http:", "https:", "data:")):
        return ""
    candidate = Path(value)
    if candidate.is_absolute():
        return str(candidate) if candidate.is_file() else ""
    if "/" in value:
        for root in roots:
            resolved = root / candidate
            if resolved.is_file():
                return str(resolved)
        return ""
    for root in roots:
        resolved = root / candidate
        if resolved.is_file():
            return str(resolved)
    return value if re.fullmatch(r"[A-Za-z0-9._+-]{1,160}", value) else ""


def parse_appstream_file(
    path: Path,
    language: str | None = None,
    *,
    icon_roots: Sequence[Path] = ICON_ROOTS,
) -> list[dict[str, object]]:
    language = language or locale.getlocale()[0] or "C"
    if len(language) > 16:
        language = "C"
    if path.stat().st_size > 8 * 1024 * 1024:
        return []
    try:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rb") as stream:
            contents = stream.read(8 * 1024 * 1024 + 1)
        if len(contents) > 8 * 1024 * 1024:
            return []
        root = ET.fromstring(contents)
    except (ET.ParseError, OSError):
        return []
    components = [root] if root.tag.rsplit("}", 1)[-1] == "component" else list(root)
    records: list[dict[str, object]] = []
    for component in components:
        if component.tag.rsplit("}", 1)[-1] != "component":
            continue
        package_names = [
            (node.text or "").strip()
            for node in component.findall("./pkgname")
            if node.text and PACKAGE_RE.fullmatch(node.text.strip())
        ]
        if not package_names:
            continue
        names = _localized_text(component, "name", language)
        if not names:
            continue
        summary = _localized_text(component, "summary", language)
        description = _localized_text(component, "description", language)
        categories = [
            (node.text or "").strip()
            for node in component.findall("./categories/category")
            if node.text
        ]
        icon = ""
        for node in component.findall("./icon"):
            icon = _safe_local_icon((node.text or "").strip(), icon_roots)
            if icon:
                break
        developer_node = component.find("./developer_name")
        developer = " ".join("".join(developer_node.itertext()).split()) if developer_node is not None else ""
        license_node = component.find("./project_license")
        license_name = (license_node.text or "").strip() if license_node is not None else ""
        launchable = component.find("./launchable[@type='desktop-id']")
        desktop_id = (launchable.text or "").strip() if launchable is not None else ""
        if desktop_id and (Path(desktop_id).name != desktop_id or not desktop_id.endswith(".desktop")):
            desktop_id = ""
        size_node = component.find("./size[@type='download']")
        try:
            size = int(size_node.text) if size_node is not None and size_node.text else None
        except ValueError:
            size = None
        records.append({
            "appstream_id": component.findtext("./id", default="").strip(),
            "package_names": package_names,
            "name": names,
            "summary": summary,
            "description": description,
            "categories": categories,
            "icon": icon,
            "developer": developer,
            "license": license_name,
            "size_bytes": size if size is not None and size >= 0 else None,
            "desktop_id": desktop_id,
        })
    return records


def _dep11_text(value: object, language: str) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if not isinstance(value, dict):
        return ""
    for wanted in (language, language.split("_", 1)[0], "C"):
        text = value.get(wanted)
        if isinstance(text, str) and text.strip():
            return " ".join(text.split())
    return ""


def parse_dep11_file(
    path: Path,
    language: str | None = None,
    *,
    icon_roots: Sequence[Path] = ICON_ROOTS,
) -> list[dict[str, object]]:
    language = language or locale.getlocale()[0] or "C"
    if len(language) > 16:
        language = "C"
    max_bytes = 64 * 1024 * 1024
    try:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rb") as stream:
            contents = stream.read(max_bytes + 1)
        if len(contents) > max_bytes:
            return []
        documents = yaml.safe_load_all(io.BytesIO(contents))
        records = []
        for component in documents:
            if not isinstance(component, dict):
                continue
            package_value = component.get("Package", "")
            package_names = package_value if isinstance(package_value, list) else [package_value]
            package_names = [
                package.strip()
                for package in package_names
                if isinstance(package, str) and PACKAGE_RE.fullmatch(package.strip())
            ]
            name = _dep11_text(component.get("Name"), language)
            if not package_names or not name:
                continue
            categories = component.get("Categories", [])
            if not isinstance(categories, list):
                categories = []
            launchable = component.get("Launchable", {})
            desktop_id = launchable.get("desktop-id", "") if isinstance(launchable, dict) else ""
            if not isinstance(desktop_id, str) or Path(desktop_id).name != desktop_id or not desktop_id.endswith(".desktop"):
                desktop_id = ""
            icon_value = component.get("Icon", {})
            if isinstance(icon_value, dict):
                cached = icon_value.get("cached", {})
                icon_value = icon_value.get("stock", "")
                if not icon_value and isinstance(cached, dict):
                    icon_value = cached.get("stock", "")
                if not icon_value and isinstance(cached, list):
                    icon_value = next(
                        (entry.get("name", "") for entry in cached if isinstance(entry, dict)),
                        "",
                    )
            icon = _safe_local_icon(icon_value if isinstance(icon_value, str) else "", icon_roots)
            records.append({
                "appstream_id": str(component.get("ID", "")).strip(),
                "package_names": package_names,
                "name": name,
                "summary": _dep11_text(component.get("Summary"), language),
                "description": _dep11_text(component.get("Description"), language),
                "categories": [value.strip() for value in categories if isinstance(value, str)],
                "icon": icon,
                "developer": _dep11_text(component.get("DeveloperName"), language),
                "license": str(component.get("ProjectLicense", "")).strip(),
                "size_bytes": None,
                "desktop_id": desktop_id,
            })
        return records
    except (OSError, yaml.YAMLError, UnicodeDecodeError):
        return []


class StoreBackend:
    """Discover software from enabled local package sources and perform safe argv-only actions."""

    def __init__(
        self,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = _run,
        appstream_roots: Sequence[Path] = APPSTREAM_ROOTS,
        icon_roots: Sequence[Path] = ICON_ROOTS,
        desktop_roots: Sequence[Path] | None = None,
        architecture: str | None = None,
    ):
        self.runner = runner
        self.appstream_roots = tuple(appstream_roots)
        self.icon_roots = tuple(icon_roots)
        self.desktop_roots = tuple(desktop_roots) if desktop_roots is not None else (
            Path("/usr/share/applications"),
            Path.home() / ".local/share/applications",
        )
        self.architecture = architecture or self._architecture()
        self._appstream_cache: list[dict[str, object]] | None = None
        self._policy_cache: dict[str, tuple[str, bool]] = {}
        self._state_cache: dict[str, tuple[bool, str]] = {}
        self._metadata_cache: dict[tuple[str, str], tuple[int | None, str]] = {}

    def _architecture(self) -> str:
        try:
            result = self.runner(["dpkg", "--print-architecture"], timeout=5)
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    def _appstream_records(self) -> list[dict[str, object]]:
        if self._appstream_cache is not None:
            return self._appstream_cache
        records = []
        seen: set[tuple[str, str]] = set()
        for root in self.appstream_roots:
            if not root.is_dir():
                continue
            xml_files = itertools.chain(root.rglob("*.xml"), root.rglob("*.xml.gz"))
            dep11_files = (
                path for path in root.rglob("*_dep11_Components-*.yml*")
                if path.is_file()
            )
            for path in itertools.chain(xml_files, dep11_files):
                try:
                    if "_dep11_Components-" in path.name:
                        parsed = parse_dep11_file(path, icon_roots=self.icon_roots)
                    else:
                        parsed = parse_appstream_file(path, icon_roots=self.icon_roots)
                except OSError:
                    continue
                for record in parsed:
                    for package in record["package_names"]:
                        key = (str(record["appstream_id"]), package)
                        if key not in seen:
                            seen.add(key)
                            records.append({**record, "package_name": package})
        self._appstream_cache = records
        return records

    def invalidate_catalog_cache(self) -> None:
        self._appstream_cache = None
        self._policy_cache.clear()
        self._state_cache.clear()
        self._metadata_cache.clear()

    def _package_policy(self, package: str) -> tuple[str, bool]:
        if not PACKAGE_RE.fullmatch(package):
            return "", False
        if package in self._policy_cache:
            return self._policy_cache[package]
        try:
            result = self.runner(["apt-cache", "policy", package], timeout=10)
        except (OSError, subprocess.SubprocessError):
            return "", False
        if result.returncode:
            return "", False
        candidate = ""
        for line in result.stdout.splitlines():
            match = re.match(r"\s*Candidate:\s*(\S+)", line)
            if match:
                candidate = match.group(1)
                break
        value = (candidate if candidate != "(none)" else "", bool(candidate and candidate != "(none)"))
        self._policy_cache[package] = value
        return value

    def _package_state(self, package: str) -> tuple[bool, str]:
        if not PACKAGE_RE.fullmatch(package):
            return False, ""
        if package in self._state_cache:
            return self._state_cache[package]
        try:
            result = self.runner(
                ["dpkg-query", "-W", "-f=${Status}\t${Version}", "--", package],
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return False, ""
        if result.returncode:
            return False, ""
        fields = result.stdout.strip().split("\t", 1)
        value = (len(fields) == 2 and fields[0] == "install ok installed", fields[1] if len(fields) == 2 else "")
        self._state_cache[package] = value
        return value

    def _apt_metadata(self, package: str, candidate: str) -> tuple[int | None, str]:
        key = (package, candidate)
        if key in self._metadata_cache:
            return self._metadata_cache[key]
        try:
            result = self.runner(["apt-cache", "show", package], timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None, ""
        if result.returncode:
            return None, ""
        paragraphs = result.stdout.split("\n\n")
        selected = {}
        for paragraph in paragraphs:
            fields = {}
            for line in paragraph.splitlines():
                if line and not line[0].isspace() and ": " in line:
                    key, value = line.split(": ", 1)
                    fields[key] = value
            if fields.get("Version") == candidate:
                selected = fields
                break
        try:
            size = int(selected["Size"])
        except (KeyError, ValueError):
            size = None
        arch = selected.get("Architecture", "")
        if arch and self.architecture and arch not in (self.architecture, "all"):
            value = (None, arch)
        else:
            value = (size if size is not None and size >= 0 else None, arch)
        self._metadata_cache[key] = value
        return value

    def _apt_search(self, query: str) -> list[tuple[str, str]]:
        if not query.strip():
            return []
        try:
            result = self.runner(["apt-cache", "search", "--names-only", query.strip()], timeout=30)
        except (OSError, subprocess.SubprocessError):
            return []
        if result.returncode:
            return []
        matches = []
        for line in result.stdout.splitlines():
            package, separator, summary = line.partition(" - ")
            if separator and PACKAGE_RE.fullmatch(package.strip()):
                matches.append((package.strip(), summary.strip()))
        return matches[:120]

    def _installed_desktop_apps(self) -> list[StoreApp]:
        result: list[StoreApp] = []
        seen: set[str] = set()
        for root in self.desktop_roots:
            if not root.is_dir():
                continue
            for path in root.rglob("*.desktop"):
                try:
                    if path.stat().st_size > 256 * 1024:
                        continue
                    desktop = configparser.ConfigParser(interpolation=None, strict=False)
                    desktop.optionxform = str
                    if not desktop.read(path, encoding="utf-8") or "Desktop Entry" not in desktop:
                        continue
                    entry = desktop["Desktop Entry"]
                    if entry.get("Type") != "Application" or entry.getboolean("NoDisplay", fallback=False):
                        continue
                    desktop_id = path.name
                    if desktop_id in seen:
                        continue
                    name = entry.get("Name", "").strip()
                    if not name:
                        continue
                    exec_line = entry.get("Exec", "")
                    launchable = bool(exec_line) and not entry.getboolean("Terminal", fallback=False)
                    categories = entry.get("Categories", "").split(";")
                    category = _category(categories)
                    result.append(StoreApp(
                        app_id=f"desktop:{desktop_id}",
                        source="installed",
                        source_name="System",
                        name=name,
                        summary=entry.get("Comment", "").strip(),
                        category=category,
                        package_id=desktop_id,
                        installed=True,
                        icon=_safe_local_icon(entry.get("Icon", "")),
                        desktop_id=desktop_id,
                        launchable=launchable,
                    ))
                    seen.add(desktop_id)
                except (OSError, configparser.Error, ValueError):
                    continue
        return result

    def _apt_apps(self, query: str = "") -> list[StoreApp]:
        records = self._appstream_records()
        candidates: dict[str, dict[str, object]] = {}
        terms = query.casefold().split()
        for record in records:
            haystack = " ".join(str(record[key]) for key in ("name", "summary", "description", "categories")).casefold()
            if terms and not all(term in haystack for term in terms):
                continue
            package = str(record["package_name"])
            candidates.setdefault(package, record)
        fallback_summaries: dict[str, str] = {}
        if query.strip():
            for package, summary in self._apt_search(query):
                candidates.setdefault(package, {
                    "appstream_id": "",
                    "package_name": package,
                    "name": package,
                    "summary": summary,
                    "description": summary,
                    "categories": [],
                    "icon": "",
                    "developer": "",
                    "license": "",
                    "size_bytes": None,
                    "desktop_id": "",
                })
                fallback_summaries[package] = summary
        apps = []
        for package, record in list(candidates.items())[:80]:
            version, available = self._package_policy(package)
            if not available:
                continue
            installed, installed_version = self._package_state(package)
            size, architecture = self._apt_metadata(package, version)
            if architecture and self.architecture and architecture not in (self.architecture, "all"):
                continue
            category = _category(record["categories"])
            desktop_id = str(record["desktop_id"])
            launchable = bool(desktop_id and (Path("/usr/share/applications") / desktop_id).is_file())
            newer = False
            if installed and version and installed_version:
                try:
                    comparison = self.runner(
                        ["dpkg", "--compare-versions", installed_version, "lt", version],
                        timeout=5,
                    )
                    newer = comparison.returncode == 0
                except (OSError, subprocess.SubprocessError):
                    newer = False
            apps.append(StoreApp(
                app_id=f"apt:{package}",
                source="apt",
                source_name="Debian APT",
                name=str(record["name"]),
                summary=str(record["summary"]) or fallback_summaries.get(package, ""),
                category=category,
                package_id=package,
                version=version if newer or not installed else installed_version,
                installed=installed,
                update_available=newer,
                icon=str(record["icon"]),
                developer=str(record["developer"]),
                license=str(record["license"]),
                size_bytes=size if size is not None else record["size_bytes"],
                architecture=architecture or self.architecture,
                desktop_id=desktop_id,
                launchable=launchable,
                description=str(record["description"]),
            ))
        return apps

    def _flatpak_apps(self, query: str = "") -> list[StoreApp]:
        if not shutil.which("flatpak"):
            return []
        try:
            remotes = self.runner(["flatpak", "remotes", "--user", "--columns=name"], timeout=15)
        except (OSError, subprocess.SubprocessError):
            return []
        if remotes.returncode:
            return []
        installed_by_id: dict[str, tuple[str, str, str]] = {}
        try:
            installed = self.runner(
                ["flatpak", "list", "--user", "--app", "--columns=application,name,version,origin,arch"],
                timeout=20,
            )
            if installed.returncode == 0:
                for line in installed.stdout.splitlines():
                    fields = line.split("\t")
                    if len(fields) >= 5 and FLATPAK_ID_RE.fullmatch(fields[0]):
                        installed_by_id[fields[0]] = (fields[1], fields[2], fields[3])
        except (OSError, subprocess.SubprocessError):
            pass
        results = []
        terms = query.casefold().split()
        for remote in dict.fromkeys(line.strip() for line in remotes.stdout.splitlines() if line.strip()):
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", remote):
                continue
            try:
                listing = self.runner([
                    "flatpak", "remote-ls", "--app",
                    "--columns=application,name,description,version,branch,arch,origin",
                    remote,
                ], timeout=45)
            except (OSError, subprocess.SubprocessError):
                continue
            if listing.returncode:
                continue
            for line in listing.stdout.splitlines():
                fields = line.split("\t")
                if len(fields) < 6:
                    continue
                app_id, name, summary, version, branch, arch = fields[:6]
                origin = fields[6] if len(fields) > 6 else remote
                if not FLATPAK_ID_RE.fullmatch(app_id) or arch not in ("", self.architecture):
                    continue
                if terms and not all(term in f"{name} {summary} {app_id}".casefold() for term in terms):
                    continue
                installed = app_id in installed_by_id
                results.append(StoreApp(
                    app_id=f"flatpak:{remote}:{app_id}",
                    source="flatpak",
                    source_name=origin or remote,
                    name=name or app_id,
                    summary=summary,
                    category="Other",
                    package_id=app_id,
                    version=installed_by_id.get(app_id, ("", version, ""))[1] or version,
                    installed=installed,
                    architecture=arch,
                    launchable=installed,
                    remote=remote,
                    branch=branch,
                ))
        return results

    def search(self, query: str = "", category: str = "All", *, source: str = "All") -> list[StoreApp]:
        query = query.strip()[:160]
        apps: list[StoreApp] = []
        if source in ("All", "APT"):
            apps.extend(self._apt_apps(query))
        if source in ("All", "Flatpak"):
            apps.extend(self._flatpak_apps(query))
        if category == "Installed":
            apps = [app for app in apps if app.installed]
            apps.extend(self._installed_desktop_apps())
        elif category in SEARCH_CATEGORIES and not query:
            category_results = list(apps)
            category_terms = SEARCH_CATEGORIES[category]
            for term in category_terms:
                category_results.extend(self._apt_apps(term))
                if source in ("All", "Flatpak"):
                    category_results.extend(self._flatpak_apps(term))
            apps = category_results
        if category not in ("All", "Installed", "Games", "Windows"):
            apps = [app for app in apps if app.category == category]
        elif category == "Games":
            apps = [
                app for app in apps
                if app.category == "Games"
                or any(token in f"{app.package_id} {app.name}".casefold() for token in ("steam", "lutris", "heroic", "game"))
            ]
        elif category == "Windows":
            apps = [
                app for app in apps
                if any(token in f"{app.package_id} {app.name} {app.summary}".casefold() for token in ("wine", "bottles", "winetricks", "windows", "proton"))
            ]
        unique: dict[str, StoreApp] = {}
        for app in apps:
            unique.setdefault(app.app_id, app)
        return sorted(unique.values(), key=lambda app: (not app.installed, app.name.casefold()))[:200]

    def installed_apps(self) -> list[StoreApp]:
        apps = self._apt_apps() + self._flatpak_apps()
        apps = [app for app in apps if app.installed]
        apps.extend(self._installed_desktop_apps())
        return sorted({app.app_id: app for app in apps}.values(), key=lambda app: app.name.casefold())

    def updates(self) -> list[str]:
        updates: list[str] = []
        try:
            apt = self.runner(["apt-get", "-s", "upgrade"], timeout=30)
            if apt.returncode == 0:
                updates.extend(
                    line.split()[1].split(":", 1)[0]
                    for line in apt.stdout.splitlines()
                    if line.startswith("Inst ")
                )
        except (OSError, subprocess.SubprocessError):
            pass
        if shutil.which("flatpak"):
            try:
                result = self.runner(["flatpak", "remote-ls", "--user", "--updates", "--columns=application"], timeout=45)
                if result.returncode == 0:
                    updates.extend(f"flatpak:{line.strip()}" for line in result.stdout.splitlines() if FLATPAK_ID_RE.fullmatch(line.strip()))
            except (OSError, subprocess.SubprocessError):
                pass
        return list(dict.fromkeys(updates))

    def package_candidate(self, package: str) -> str:
        candidate, available = self._package_policy(package)
        return candidate if available else ""

    def is_installed(self, source: str, package: str) -> bool:
        if source == "apt":
            return self._package_state(package)[0]
        if source != "flatpak" or not FLATPAK_ID_RE.fullmatch(package) or not shutil.which("flatpak"):
            return False
        try:
            result = self.runner(
                ["flatpak", "list", "--user", "--app", "--columns=application"],
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0 and package in {line.strip() for line in result.stdout.splitlines()}

    def upgrade_apt(self) -> OperationResult:
        return self._privileged_apt(["upgrade", "--yes", "--no-remove"], timeout=1800)

    def upgrade_flatpak(self) -> OperationResult:
        if not shutil.which("flatpak"):
            return OperationResult(False, "Flatpak is unavailable; no Flatpak updates were applied.")
        try:
            result = self.runner(
                ["flatpak", "update", "--user", "--assumeyes", "--noninteractive"],
                timeout=1800,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return OperationResult(False, str(error))
        message = (result.stderr or result.stdout or "No Flatpak update details were returned.").strip()
        return OperationResult(result.returncode == 0, message[-4000:], result.returncode)

    def update_flatpak(self, app_id: str) -> OperationResult:
        if not FLATPAK_ID_RE.fullmatch(app_id) or not shutil.which("flatpak"):
            return OperationResult(False, "Invalid Flatpak application identity or Flatpak is unavailable.")
        try:
            result = self.runner(
                ["flatpak", "update", "--user", "--assumeyes", "--noninteractive", app_id],
                timeout=1800,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return OperationResult(False, str(error))
        message = (result.stderr or result.stdout or "No Flatpak update details were returned.").strip()
        return OperationResult(result.returncode == 0, message[-4000:], result.returncode)

    def _privileged_apt(self, arguments: Sequence[str], timeout: int = 900) -> OperationResult:
        if not shutil.which("pkexec"):
            return OperationResult(False, "pkexec (Polkit) is not installed.")
        try:
            result = self.runner(["pkexec", "/usr/bin/apt-get", *arguments], timeout=timeout)
        except (OSError, subprocess.SubprocessError) as error:
            return OperationResult(False, str(error))
        message = (result.stderr or result.stdout or "No package-manager details were returned.").strip()
        if result.returncode == 0:
            self.invalidate_catalog_cache()
        return OperationResult(result.returncode == 0, message[-4000:], result.returncode)

    def update_indexes(self) -> OperationResult:
        return self._privileged_apt(["update"], timeout=900)

    def install_apt(self, package: str, expected_version: str) -> OperationResult:
        if not PACKAGE_RE.fullmatch(package) or not VERSION_RE.fullmatch(expected_version):
            return OperationResult(False, "Invalid package identity or version.")
        candidate, available = self._package_policy(package)
        if not available or candidate != expected_version:
            return OperationResult(False, "The selected package version is no longer available; refresh and review it again.")
        return self._privileged_apt([
            "install", "--yes", "--no-install-recommends", "--", f"{package}={expected_version}",
        ])

    def remove_apt(self, package: str, expected_version: str) -> OperationResult:
        if not PACKAGE_RE.fullmatch(package) or not VERSION_RE.fullmatch(expected_version):
            return OperationResult(False, "Invalid package identity or version.")
        installed, version = self._package_state(package)
        if not installed or version != expected_version:
            return OperationResult(False, "The installed package changed; refresh and review it again.")
        return self._privileged_apt(["remove", "--yes", "--no-auto-remove", "--", package])

    def install_flatpak(self, remote: str, app_id: str, branch: str = "") -> OperationResult:
        if (
            not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", remote)
            or not FLATPAK_ID_RE.fullmatch(app_id)
            or (branch and not re.fullmatch(r"[A-Za-z0-9._+-]{1,64}", branch))
            or not shutil.which("flatpak")
        ):
            return OperationResult(False, "Invalid Flatpak source or application identity.")
        try:
            listing = self.runner([
                "flatpak", "remote-ls", "--app", "--columns=application,branch,arch", remote,
            ], timeout=45)
        except (OSError, subprocess.SubprocessError) as error:
            return OperationResult(False, str(error))
        if listing.returncode:
            return OperationResult(False, (listing.stderr or listing.stdout or "Unable to verify the selected Flatpak.").strip()[-4000:], listing.returncode)
        verified = False
        for line in listing.stdout.splitlines():
            fields = line.split("\t")
            if (
                len(fields) >= 3
                and fields[0] == app_id
                and (not branch or fields[1] == branch)
                and fields[2] in ("", self.architecture)
            ):
                verified = True
                break
        if not verified:
            return OperationResult(False, "The selected Flatpak is no longer available for this architecture.")
        argv = ["flatpak", "install", "--user", "--assumeyes", "--noninteractive"]
        if branch:
            argv.extend(["--branch", branch])
        argv.extend([remote, app_id])
        try:
            result = self.runner(argv, timeout=1800)
        except (OSError, subprocess.SubprocessError) as error:
            return OperationResult(False, str(error))
        message = (result.stderr or result.stdout or "No Flatpak details were returned.").strip()
        return OperationResult(result.returncode == 0, message[-4000:], result.returncode)

    def remove_flatpak(self, app_id: str) -> OperationResult:
        if not FLATPAK_ID_RE.fullmatch(app_id) or not shutil.which("flatpak"):
            return OperationResult(False, "Invalid Flatpak application identity or Flatpak is unavailable.")
        try:
            result = self.runner(["flatpak", "uninstall", "--user", "--assumeyes", "--noninteractive", app_id], timeout=900)
        except (OSError, subprocess.SubprocessError) as error:
            return OperationResult(False, str(error))
        message = (result.stderr or result.stdout or "No Flatpak details were returned.").strip()
        return OperationResult(result.returncode == 0, message[-4000:], result.returncode)

    def enable_flathub(self) -> OperationResult:
        if not shutil.which("flatpak"):
            return OperationResult(False, "Flatpak is not installed.")
        try:
            result = self.runner([
                "flatpak", "remote-add", "--user", "--if-not-exists",
                "flathub", FLATHUB_URL,
            ], timeout=120)
        except (OSError, subprocess.SubprocessError) as error:
            return OperationResult(False, str(error))
        message = (result.stderr or result.stdout or "Flathub configuration failed.").strip()
        return OperationResult(result.returncode == 0, message[-4000:], result.returncode)

    def launch(self, app: StoreApp) -> OperationResult:
        if not app.installed or not app.launchable:
            return OperationResult(False, "This installed item has no verified application launcher.")
        if app.source == "flatpak":
            if not FLATPAK_ID_RE.fullmatch(app.package_id) or not shutil.which("flatpak"):
                return OperationResult(False, "Flatpak is unavailable.")
            argv = ["flatpak", "run", app.package_id]
        elif app.source == "apt":
            if not app.desktop_id or Path(app.desktop_id).name != app.desktop_id:
                return OperationResult(False, "The installed desktop entry is not valid.")
            if not (Path("/usr/share/applications") / app.desktop_id).is_file():
                return OperationResult(False, "The desktop launcher is no longer installed.")
            if not shutil.which("gtk-launch"):
                return OperationResult(False, "gtk-launch is not installed.")
            argv = ["gtk-launch", app.desktop_id.removesuffix(".desktop")]
        else:
            if Path(app.desktop_id).name != app.desktop_id or not app.desktop_id.endswith(".desktop"):
                return OperationResult(False, "The desktop launcher is not valid.")
            argv = ["gtk-launch", app.desktop_id.removesuffix(".desktop")]
        try:
            subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as error:
            return OperationResult(False, str(error))
        return OperationResult(True, "Application launch requested.")
