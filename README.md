# ios-safari-screens

iPhone シミュレーターの Safari で**公開ページ**を開き、1画面目を撮影する GitHub Actions です。
Mac を持っていなくても、実機に近い iOS Safari の表示を確認できます。

- 公開リポジトリのため、標準の macOS ランナーは無料です（[GitHub Docs](https://docs.github.com/en/billing/concepts/product-billing/github-actions)）。
- **手動起動のみ**。秘密値は使いません。ログインが必要なページは撮れません（撮らないでください）。

## 使い方

```bash
gh workflow run screens.yml -R yannsunn/ios-safari-screens \
  -f label=koyomi-20260924 \
  -f urls="https://koyomiboshi.com/fortune/ https://koyomiboshi.com/fortune/birthstone.html"
gh run watch -R yannsunn/ios-safari-screens
gh run download -R yannsunn/ios-safari-screens -n koyomi-20260924 -D ./shots
```

`fixtures/` の確認用ページは `http://localhost:8000/...` で撮れます（例: `http://localhost:8000/fortune/daily.html`
＝本番の CSS とメニューを読み、ログイン中の下部タブを再現するページ）。

`out/index.tsv` に番号と URL の対応、`out/environment.txt` に Xcode と端末・iOS の版が入ります。
画像は14日で自動削除されます。
