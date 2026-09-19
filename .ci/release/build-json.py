#!/usr/bin/env python3
import json, os, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

def apk_data(path):
    out = {"minSdk": None, "versionCode": None, "densities": [], "nativeLibraries": []}
    tool = shutil.which("aapt2") or shutil.which("aapt")
    if not tool: return out
    text = subprocess.run([tool, "dump", "badging", str(path)], capture_output=True, text=True).stdout
    patterns = {"minSdk": r"(?:sdkVersion|minSdkVersion):'([^']+)'", "versionCode": r"versionCode='([^']+)'",
                "densities": r"densities: '([^']+)'", "nativeLibraries": r"native-code: '([^']+)'"}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match: out[key] = match.group(1).split() if key.endswith("s") else match.group(1)
    return out

def info(name):
    lower = name.lower(); ext = Path(name).suffix
    apk = ext.lower() in (".apk", ".apks", ".xapk", ".apkm")
    if apk:
        os_name, arch = "Android", "x86_64" if "chromeos" in lower or "x86_64" in lower else "arm64-v8a"
        variant = "legacy" if "legacy" in lower else "optimized" if any(x in lower for x in ("optimized", "optimised", "genshin")) else "chromeos" if "chromeos" in lower else None
        sub = None
    elif "windows" in lower or ext.lower() in (".zip", ".exe"):
        os_name, arch = "Windows", "aarch64" if any(x in lower for x in ("arm64", "aarch64")) else "amd64"
        variant, sub = None, "msvc" if "msvc" in lower else "clang-pgo" if "pgo" in lower else "gcc"
    elif "macos" in lower or ext.lower() in (".dmg", ".pkg"):
        os_name, arch, variant, sub = "macOS", "universal", None, None
    else:
        os_name, arch, variant, sub = "Linux", "aarch64" if "aarch64" in lower or "arm64" in lower else "amd64", None, "clang-pgo" if "pgo" in lower else "gcc"
    return os_name, ext, arch, variant, sub, apk

def main():
    version = os.environ.get("GITHUB_TAG") or os.environ.get("ARTIFACT_REF", "latest")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    channel = "beta" if os.environ.get("IS_PRERELEASE", "false").lower() == "true" else "stable"
    files = {}
    artifacts = Path("artifacts")
    artifacts.mkdir(parents=True, exist_ok=True)
    for path in sorted(artifacts.iterdir()):
        if not path.is_file() or path.name == "build.json": continue
        os_name, ext, arch, variant, sub, apk = info(path.name); data = apk_data(path) if apk else {}
        files[path.name] = {k: v for k, v in {"name": "eden", "version": version, "appKey": "eden", "appName": "Eden", "arch": arch,
            "fileType": "APK" if apk else ext.lstrip(".").upper(), "brandKey": None, "brandName": None,
            "variant": variant, "subVariant": sub, "packageName": ("dev.legacy.eden_emulator" if "legacy" in path.name.lower() else "com.miHoYo.Yuanshen" if any(x in path.name.lower() for x in ("optimized", "optimised", "genshin")) else "dev.eden.eden_emulator") if apk else None,
            "patchSources": [], "changelogs": [], "appliedPatches": [], "densities": data.get("densities", []), "nativeLibraries": data.get("nativeLibraries", []),
            "minSdk": data.get("minSdk"), "versionCode": data.get("versionCode"), "originBuild": version, "publishedAt": now}.items() if v is not None and v != []}
    manifest = {"schema": 1, "kind": "build", "meta": {"build": version, "channel": channel, "publishedAt": now}, "files": files}
    Path("build.json").write_text(json.dumps(manifest, separators=(",", ":")) + "\n")
    (artifacts / "build.json").write_text(Path("build.json").read_text())

if __name__ == "__main__": main()
