"""予約サイトから予約日と施設名を取得する初期実装。



本番のDOMセレクタは、ログイン後の予約一覧画面を確認してから確定する。

"""



from __future__ import annotations



import os

import sys

from dataclasses import dataclass

from datetime import date



from bs4 import BeautifulSoup

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright



BASE_URL = "https://www.task-asp.net/cu/eg/ykr302015.task"





@dataclass(frozen=True)

class Reservation:
  
    reservation_date: date
  
    facility_name: str
  




def require_secret(name: str) -> str:
  
    value = os.environ.get(name)
  
    if not value:
      
        raise RuntimeError(f"GitHub Secret {name} が未設定です")
      
    return value
  




def login(page: Page, user_id: str, password: str) -> None:
  
    """ログイン処理の仮実装。"""
  
    page.goto(BASE_URL, wait_until="domcontentloaded")
  
    page.locator("#LoginButton").click()
  
    page.wait_for_load_state("domcontentloaded")
  


    # TODO: ログイン画面確認後に、実際のセレクタへ置き換える。

    # page.locator("#user-id").fill(user_id)

    # page.locator("#password").fill(password)

    # page.locator("button[type='submit']").click()

    raise NotImplementedError("ログイン後画面の確認が必要です")
  




def extract_reservations(page: Page) -> list[Reservation]:
  
    """予約一覧から日付と施設名を抽出する仮実装。"""
  
    soup = BeautifulSoup(page.content(), "html.parser")
  
    # TODO: 予約一覧HTMLに合わせて抽出処理を実装する。

    _ = soup
  
    return []
  




def main() -> int:
  
    user_id = require_secret("RESERVATION_USER_ID")
  
    password = require_secret("RESERVATION_PASSWORD")
  


    try:
      
        with sync_playwright() as playwright:
          
            browser = playwright.chromium.launch(headless=True)
          
            page = browser.new_page(locale="ja-JP")
          
            try:
              
                login(page, user_id, password)
              
                reservations = extract_reservations(page)
              
            finally:
              
                browser.close()
              
    except PlaywrightTimeoutError as exc:
      
        print(f"予約サイトの応答待ちでタイムアウトしました: {exc}", file=sys.stderr)
      
        return 1
      
    except NotImplementedError as exc:
      
        print(f"テスト準備中: {exc}", file=sys.stderr)
      
        return 2
      


    print(f"取得件数: {len(reservations)}")
  
    for item in reservations:
      
        print(f"{item.reservation_date.isoformat()} | {item.facility_name}")
      
    return 0
  




if __name__ == "__main__":
  
    raise SystemExit(main())
  











































