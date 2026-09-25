"""ログインが要る画面を撮る（Apple 公式の safaridriver でシミュレーターの Safari を操作する）。

- 資格情報は GitHub Secrets（KOYOMI_TEST_EMAIL / KOYOMI_TEST_PASSWORD）から環境変数で受け取り、表示しない
- 撮る前に画面上のメールアドレスを伏せる（公開リポジトリの成果物に残さないため）
- スクリーンショットは Safari の枠ごと写すため xcrun simctl で撮る
"""
import os
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

udid = os.environ["UDID"]
# DRIVER_ONLY=1 のときはログインせず、公開ページで safaridriver の接続だけを確かめる（Secrets 不要）
driver_only = os.environ.get("DRIVER_ONLY") == "1"
email = "" if driver_only else os.environ["TEST_EMAIL"]
password = "" if driver_only else os.environ["TEST_PASSWORD"]
login_url = os.environ["LOGIN_URL"]
urls = os.environ["URLS"].split()

MASK_JS = """
const target = arguments[0];
const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
let n; while ((n = walker.nextNode())) {
  if (n.nodeValue.includes(target)) n.nodeValue = n.nodeValue.split(target).join("（試験用アカウント）");
}
for (const el of document.querySelectorAll("input")) {
  if (el.value && el.value.includes(target)) el.value = "（試験用アカウント）";
}
"""

opts = webdriver.SafariOptions()
opts.set_capability("platformName", "iOS")
opts.set_capability("safari:useSimulator", True)
opts.set_capability("safari:deviceUDID", udid)

def new_driver():
    # シミュレーターの Safari への接続は1回目に時間切れになることがある（actions/runner-images#1453）。
    # 開きっぱなしの Safari を閉じてから、3回まで試す
    last = None
    for attempt in range(1, 4):
        subprocess.run(["xcrun", "simctl", "terminate", udid, "com.apple.mobilesafari"], check=False)
        time.sleep(5)
        try:
            return webdriver.Safari(options=opts)
        except Exception as err:
            last = err
            print(f"safaridriver 接続失敗（{attempt}回目）: {type(err).__name__}", file=sys.stderr)
            time.sleep(15)
    raise last


driver = new_driver()
print("driver ok", flush=True)
wait = WebDriverWait(driver, 60)
failed = 0
try:
    if driver_only and os.environ.get("PROBE_LOGIN_URL"):
        # 入力の確かめ（送信しない）: 打った文字がそのまま入るか（自動大文字化・自動修正の有無）
        driver.get(os.environ["PROBE_LOGIN_URL"])
        probe = "e2e-probe-Check@example.com"
        field = wait.until(ec.presence_of_element_located((By.ID, "email")))
        field.send_keys(probe)
        got = field.get_attribute("value")
        print("probe typed == value:", got == probe, "| len", len(got))
        pw = driver.find_element(By.ID, "password")
        pw.send_keys("Abc123xyz")
        print("probe password len:", len(pw.get_attribute("value") or ""))
        print("probe submit enabled:", driver.find_element(By.ID, "submit").is_enabled())
        subprocess.run(["xcrun", "simctl", "io", udid, "screenshot", "out/probe-login.png"], check=True)
    if not driver_only:
        driver.get(login_url)
        wait.until(ec.presence_of_element_located((By.ID, "email"))).send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        typed_ok = driver.find_element(By.ID, "email").get_attribute("value") == email
        print("email typed as-is:", typed_ok, flush=True)
        wait.until(ec.element_to_be_clickable((By.ID, "submit"))).click()
        try:
            wait.until(lambda d: "/login.html" not in d.current_url)
        except Exception:
            # 失敗の手がかりを残す（メールは伏せてから撮る。パスワード欄は伏せ字表示）
            err = driver.execute_script("return (document.getElementById('error')||{}).textContent || ''")
            print("login failed; error text:", err.strip()[:200], flush=True)
            driver.execute_script(MASK_JS, email)
            subprocess.run(["xcrun", "simctl", "io", udid, "screenshot", "out/login-failed.png"], check=False)
            raise
        print("login ok", flush=True)
    with open("out/index.tsv", "a", encoding="utf-8") as idx:
        for i, url in enumerate(urls, 1):
            name = f"login-{i:02d}"
            try:
                driver.get(url)
                time.sleep(8)
                if email:
                    driver.execute_script(MASK_JS, email)
                subprocess.run(["xcrun", "simctl", "io", udid, "screenshot", f"out/{name}.png"], check=True)
                idx.write(f"{name}\t{url}\t{driver.current_url}\n")
                print("shot", name, url)
            except Exception as err:  # 1件の失敗で残りを止めない
                failed += 1
                idx.write(f"{name}\t{url}\tFAILED\n")
                print("failed", url, type(err).__name__, file=sys.stderr)
finally:
    driver.quit()
sys.exit(1 if failed else 0)
