#!/bin/sh
set -eu

UV_VERSION="0.11.31"
SOURCE_URL="https://github.com/matteodante/therapist/archive/refs/heads/main.tar.gz"

case "$(uname -s)" in
    Darwin|Linux) ;;
    *)
        echo "Therapist installation supports macOS, Linux, and Windows." >&2
        exit 1
        ;;
esac

if ! { : </dev/tty; } 2>/dev/null; then
    echo "Therapist setup requires an interactive terminal." >&2
    exit 1
fi

for command in curl tar; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        exit 1
    fi
done

if command -v uv >/dev/null 2>&1; then
    UV="$(command -v uv)"
else
    echo "Installing uv ${UV_VERSION}..."
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh
    UV="$HOME/.local/bin/uv"
    if [ ! -x "$UV" ]; then
        echo "uv was installed but could not be found at $UV." >&2
        exit 1
    fi
fi

TEMP_DIRECTORY="$(mktemp -d 2>/dev/null || mktemp -d -t therapist-install)"
trap 'rm -rf "$TEMP_DIRECTORY"' EXIT HUP INT TERM

echo "Downloading Therapist from main..."
curl -LsSf "$SOURCE_URL" | tar -xz -C "$TEMP_DIRECTORY" --strip-components=1
if [ ! -f "$TEMP_DIRECTORY/pyproject.toml" ]; then
    echo "The downloaded Therapist source is incomplete." >&2
    exit 1
fi

echo "Installing Therapist..."
"$UV" tool install --python 3.12 "$TEMP_DIRECTORY"
"$UV" tool update-shell

TOOL_BIN="$("$UV" tool dir --bin)"
THERA="$TOOL_BIN/thera"
if [ ! -x "$THERA" ]; then
    echo "Therapist was installed but $THERA is unavailable." >&2
    exit 1
fi

"$THERA" setup </dev/tty
"$THERA" doctor

echo
echo "Therapist is ready. Start it with: thera chat"
echo "If thera is not found in a new command, restart your shell."
