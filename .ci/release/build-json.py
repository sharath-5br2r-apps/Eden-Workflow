#!/usr/bin/env python3
"""Generate release metadata using the write_build_info-style asset schema."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def apk_metadata(path, arch):
    data = {"min_sdk": "", "version_code": "", "densities": [], "native_libraries": []}
    tool = shutil.which("aapt2") or shutil.which("aapt")
    if not tool:
        return data
    try:
        output = subprocess.run([tool, "dump", "badging", str(path)], capture_output=True,
                                text=True, check=False).stdout
    except OSError:
        return data
    match = re.search(r"(?:sdkVersion|minSdkVersion):'([^']+)'", output)
    if match:
        data["min_sdk"] = match.group(1)
    match = re.search(r"versionCode='([^']+)'", output)
    if match:
        data["version_code"] = match.group(1)
    match = re.search(r"densities: '([^']+)'", output)
    if match:
        data["densities"] = match.group(1).split()
    match = re.search(r"native-code: '([^']+)'", output)
    if match:
        data["native_libraries"] = match.group(1).split()
    return data


def metadata(name):
    lower = name.lower()
    if "android" in lower or lower.endswith((".apk", ".apks", ".xapk", ".apkm")):
        os_name, ext = "Android", Path(name).suffix
        arch = "x86_64" if "chromeos" in lower or "x86_64" in lower else "arm64-v8a"
    elif any(x in lower for x in ("windows", ".zip", ".exe")):
        os_name, ext = "Windows", Path(name).suffix
        arch = "arm64" if "arm64" in lower or "aarch64" in lower else "amd64"
    elif any(x in lower for x in ("macos", ".dmg")):
        os_name, ext, arch = "macOS", Path(name).suffix, "universal"
    else:
        os_name, ext = "Linux", Path(name).suffix
        arch = "aarch64" if "aarch64" in lower or "arm64" in lower else "amd64"
    if "pgo" in lower:
        variant, sub = "standard", "clang-pgo"
    else:
        variant = next((v for v in ("chromeos", "legacy", "optimized", "optimised") if v in lower), "standard")
        sub = "msvc" if "msvc" in lower else "clang" if "clang" in lower else "gcc" if "gcc" in lower else ""
    return os_name, ext, arch, variant, sub


def android_package(name):
    lower = name.lower()
    if "legacy" in lower:
        return "dev.legacy.eden_emulator"
    if "optimized" in lower or "optimised" in lower or "genshin" in lower:
        return "com.miHoYo.Yuanshen"
    return "dev.eden.eden_emulator"


def main():
    changelog = Path("changelog.md").read_text() if Path("changelog.md").exists() else ""
    result = {}
    for path in sorted(Path("artifacts").iterdir()):
        if not path.is_file() or path.name == "build.json":
            continue
        os_name, ext, arch, variant, sub = metadata(path.name)
        key = "eden" + (f"-{variant}" if variant != "standard" else "") + (f"-{sub}" if sub else "")
        asset = {"name": path.name, "arch": arch, "ext": ext, "os": os_name,
                 "appliedPatches": [], "skippedPatches": [], "failedPatches": []}
        if ext.lower() in (".apk", ".apks", ".xapk", ".apkm"):
            asset.update(apk_metadata(path, arch))
            asset["package_name"] = android_package(path.name)
            if asset["native_libraries"] == []:
                asset.pop("native_libraries")
            for field in ("min_sdk", "version_code", "densities"):
                if not asset[field]:
                    asset.pop(field)
        entry = result.setdefault(key, {"name": key, "version": os.environ.get("GITHUB_TAG", "latest"),
            "cli": "", "patches": "eden-emulator", "changelog": changelog,
            "changelog_urls": [], "changelogs": [],
            "package_name": android_package(path.name) if os_name == "Android" else "",
            "display_name": "Eden", "patches_source": "", "engine_brand": "",
            "patch_brand": "", "variant": variant, "sub_variant": sub, "assets": []})
        entry["assets"] = [a for a in entry["assets"] if a["name"] != path.name]
        entry["assets"].append(asset)
    Path("build.json").write_text(json.dumps(result, indent=2) + "\n")
    Path("artifacts/build.json").write_text(Path("build.json").read_text())


if __name__ == "__main__":
    main()
