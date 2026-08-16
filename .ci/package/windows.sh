#!/bin/sh -e

# SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
# SPDX-License-Identifier: GPL-3.0-or-later

ROOTDIR="$PWD"
BUILDDIR="${BUILDDIR:-$ROOTDIR/build}"
ARTIFACTS_DIR="$ROOTDIR/artifacts"

# shellcheck disable=SC1091
. "$ROOTDIR/.ci/build/project.sh"

BINDIR="$BUILDDIR/bin"
PKGDIR="$BUILDDIR/pkg"
TMP_DIR=$(mktemp -d)
EXE="${PROJECT_REPO}.exe"

WINDEPLOYQT="${WINDEPLOYQT:-windeployqt6}"

# check if common script folder is on Workflow
if [ ! -d "$ROOTDIR/.ci/build" ]; then
	echo "error: could not find $ROOTDIR/.ci/build"
	exit 1
fi

# shellcheck disable=SC1091
. "$ROOTDIR/.ci/build/platform.sh"

rm -f "$BINDIR/"*.pdb || true

mkdir -p "$ARTIFACTS_DIR"
[ -n "$PKGDIR" ] && rm -rf "$PKGDIR"
mkdir -p "$PKGDIR"

cp "$BINDIR/"*.exe "$PKGDIR"
cd "$PKGDIR"

if [ "$PLATFORM" = "msys" ] && [ "$STATIC" != "ON" ]; then
	echo "-- On MSYS, bundling MinGW DLLs..."

	MSYS_TOOLCHAIN="${MSYS_TOOLCHAIN:-$MSYSTEM}"
	export PATH="/${MSYS_TOOLCHAIN}/bin:$PATH"

	# grab deps of a dll or exe and place them in the current dir
	deps() {
		objdump -p "$1" | awk '/DLL Name:/ {print $3}' | while read -r dll; do
			[ -z "$dll" ] && continue

			dllpath=$(command -v "$dll" 2>/dev/null || true)

			[ -z "$dllpath" ] && continue

			case "$dllpath" in
				*System32* | *SysWOW64*) continue ;;
			esac

			if [ ! -f "$dll" ]; then
				echo "$dllpath"
				cp "$dllpath" "$dll"
				deps "$dllpath"
			fi
		done
	}

	deps "$EXE"
fi

# qt
if [ "$STATIC" != "ON" ]; then
	${WINDEPLOYQT} --no-compiler-runtime --no-opengl-sw --no-system-dxc-compiler --no-system-d3d-compiler "$EXE"
fi

if [ "$PLATFORM" = "msys" ] && [ "$STATIC" != "ON" ]; then
	# grab deps for Qt plugins
	find ./*/ -name "*.dll" | while read -r dll; do deps "$dll"; done
fi

SHORT_SHA=$(echo "${FORGEJO_REF:-${GITHUB_SHA:-head}}" | cut -c1-10)

case "$TARGET" in
	arm64|aarch64) ARCH_NAME="arm64-v8a" ;;
	amd64|x86_64) ARCH_NAME="x86_64" ;;
	*)
		case "$ARCH" in
			*arm64*|*aarch64*) ARCH_NAME="arm64-v8a" ;;
			*) ARCH_NAME="x86_64" ;;
		esac
		;;
esac

if [ "$PLATFORM" = "msvc" ] || [ "$MSYSTEM" = "msvc" ] || [ "$TARGET" = "msvc" ]; then
	COMPILER_NAME="msvc"
elif [ -n "$COMPILER" ]; then
	COMPILER_NAME="$COMPILER"
elif case "$ARCH" in *clang*) true ;; *) false ;; esac; then
	COMPILER_NAME="clang"
else
	COMPILER_NAME="gcc"
fi

if [ "$PGO_TARGET" = "pgo" ] || case "$ARCH" in *pgo*) true ;; *) false ;; esac; then
	TARGET_NAME="pgo"
elif [ "$TARGET" = "rog-ally" ] || case "$ARCH" in *rog-ally*) true ;; *) false ;; esac; then
	TARGET_NAME="rog-ally"
else
	TARGET_NAME="standard"
fi

VARIANT="${TARGET_NAME}-${COMPILER_NAME}"
ZIP_NAME="eden-windows-${VARIANT}-v${SHORT_SHA}-${ARCH_NAME}.zip"

cp -r ./* "$TMP_DIR"/
cp -r "$ROOTDIR"/LICENSE* "$ROOTDIR"/README* "$TMP_DIR"/

7z a -tzip "$ARTIFACTS_DIR/$ZIP_NAME" "$TMP_DIR"/*

rm -rf "$TMP_DIR"
