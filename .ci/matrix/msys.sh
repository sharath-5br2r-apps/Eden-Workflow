#!/bin/sh -e

# Currently uses MINGW64. Could try clang64 or ucrt64,
# but not viable right now.

arch() {
	cat <<-EOF
		"runs-on": "$1", "arch": "$2", "msystem": "$3"
	EOF
}

AMD64="$(arch windows-latest amd64 UCRT64)"
ARM64="$(arch windows-11-arm arm64 CLANGARM64)"

PGO='"program": "clang", "target": "pgo"'
CLANG='"program": "clang", "target": "standard"'
GCC='"program": "gcc", "target": "standard"'

target() {
	arch="$1"
	compiler="$2"

	echo "{${arch}, ${compiler}}"
}

amd_gcc="$(target "$AMD64" "$GCC")"
arm_clang="$(target "$ARM64" "$CLANG")"
arm_pgo="$(target "$ARM64" "$PGO")"
MATRIX="[${amd_gcc}, ${arm_clang}, ${arm_pgo}]"

echo "MSYS Matrix: $MATRIX"
echo "matrix=${MATRIX}" >>"$GITHUB_OUTPUT"
