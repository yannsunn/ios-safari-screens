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

## ログイン後の画面（コヨミボシのみ）

`login_urls` に `https://koyomiboshi.com/...` を渡すと、Secrets（`KOYOMI_TEST_EMAIL` / `KOYOMI_TEST_PASSWORD`）の
試験用アカウント（架空データ・無料・管理者なし）で Apple 公式の safaridriver からログインして撮ります（`login-NN.png`）。
画面上のメールアドレスは撮る前に伏せます。Secrets は手動起動（書き込み権限のある人だけ）でしか使われません。
