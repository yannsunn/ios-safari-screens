#!/usr/bin/env bash
# 使い方は README.md。入力は環境変数 URLS / DEVICE / LABEL で受け取る（式展開をシェルに直接埋めない）
set -euo pipefail

mkdir -p out
read -r -a urls <<< "$URLS"
if (( ${#urls[@]} == 0 || ${#urls[@]} > 20 )); then
  echo "URL は1〜20件で指定してください（${#urls[@]}件）" >&2
  exit 1
fi
for url in "${urls[@]}"; do
  [[ "$url" =~ ^https://[A-Za-z0-9.-]+(/[^[:space:]]*)?$ || "$url" =~ ^http://localhost:8000/[^[:space:]]*$ ]] ||
    { echo "https の URL（または http://localhost:8000/ の確認用ページ）ではありません: $url" >&2; exit 1; }
done

# fixtures/ の確認用ページを http://localhost:8000/ で配る（シミュレーターは Mac とネットワークを共有する）
python3 -m http.server 8000 --directory fixtures >/dev/null 2>&1 &

xcodebuild -version | tee out/environment.txt
udid=$(xcrun simctl list devices available -j | python3 -c '
import json, os, sys
want = os.environ.get("DEVICE", "")
devs = [d | {"runtime": r} for r, ds in json.load(sys.stdin)["devices"].items()
        if "iOS" in r for d in ds if d["name"].startswith("iPhone")]
devs.sort(key=lambda d: d["runtime"], reverse=True)
pick = next((d for d in devs if want and want in d["name"]), devs[0])
print(pick["udid"])
print("device: %s / %s" % (pick["name"], pick["runtime"]), file=sys.stderr)
' 2>>out/environment.txt)
cat out/environment.txt

lang="${LANG_CODE:-ja}"
[[ "$lang" =~ ^[a-z]{2}$ ]] || { echo "lang は2文字の言語コードで指定してください: $lang" >&2; exit 1; }
region=$([[ "$lang" == "ja" ]] && echo "ja_JP" || echo "${lang}_US")

# 言語は起動中に書き換えても Safari に効かないため、1回起動して設定→再起動する
xcrun simctl boot "$udid"
xcrun simctl bootstatus "$udid" -b
xcrun simctl spawn "$udid" defaults write -g AppleLanguages -array "$lang"
xcrun simctl spawn "$udid" defaults write -g AppleLocale -string "$region"
xcrun simctl shutdown "$udid"
xcrun simctl boot "$udid"
xcrun simctl bootstatus "$udid" -b
echo "lang: $lang / $region" >> out/environment.txt
xcrun simctl status_bar "$udid" override --time "9:41" --batteryState charged --batteryLevel 100 || true

# 起動完了の直後はまだ Safari を開けないことがあるので少し待つ
sleep 20

# Safari 初回起動の案内（吹き出し）が1枚目を隠すため、撮影前に1回開いて消化させる（空撮り）
for attempt in 1 2 3; do
  xcrun simctl openurl "$udid" "${urls[0]}" && break
  sleep 15
done
sleep 20

i=0
failed=0
for url in "${urls[@]}"; do
  i=$((i + 1))
  name=$(printf '%02d' "$i")
  # 起動直後は openurl が時間切れになることがある（2026-09-24 実測）。3回まで再試行し、
  # それでも開けない URL は記録して次へ進む
  opened=0
  for attempt in 1 2 3; do
    if xcrun simctl openurl "$udid" "$url"; then opened=1; break; fi
    echo "openurl 失敗（${attempt}回目）: $url" >&2
    sleep 15
  done
  if (( opened == 0 )); then
    printf '%s\t%s\tFAILED\n' "$name" "$url" >> out/index.tsv
    failed=$((failed + 1))
    continue
  fi
  # 読み込み・フォント・画像の表示を待つ（Safari の初回起動分を含めて長めに取る）
  sleep 10
  xcrun simctl io "$udid" screenshot "out/${name}.png"
  printf '%s\t%s\n' "$name" "$url" >> out/index.tsv
  echo "shot $name $url"
done

# 1件でも開けなかった URL があれば、撮れた画像は保存したうえで失敗として終える
if (( failed > 0 )); then
  echo "開けなかった URL: ${failed}件（out/index.tsv 参照）" >&2
  exit 1
fi
