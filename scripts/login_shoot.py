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
print("driver ok")
wait = WebDriverWait(driver, 60)
failed = 0
try:
    if not driver_only:
        driver.get(login_url)
        wait.until(ec.presence_of_element_located((By.ID, "email"))).send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        wait.until(ec.element_to_be_clickable((By.ID, "submit"))).click()
        wait.until(lambda d: "/login.html" not in d.current_url)
        print("login ok")
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
