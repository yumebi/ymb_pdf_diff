#!/bin/bash
# macOS上で実行する。事前に python scripts/build.py で dist/YMB PDF DIFF.app を生成しておくこと。
# 追加ツール不要(hdiutilはmacOS標準搭載)。
set -e

APP_NAME="YMB PDF DIFF"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
APP_PATH="$DIST_DIR/$APP_NAME.app"
DMG_PATH="$DIST_DIR/${APP_NAME// /_}.dmg"

if [ ! -d "$APP_PATH" ]; then
    echo "見つからない: $APP_PATH (先に python scripts/build.py を実行すること)" >&2
    exit 1
fi

rm -f "$DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
echo "作成完了: $DMG_PATH"
