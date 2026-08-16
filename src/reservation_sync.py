"""和歌山市公共施設予約サイトから予約日・施設名を抽出する処理。"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from src.calendar_sync import sync_reservations

BASE_URL = "https://www.task-asp.net/cu/eg/ykr302015.task"
LOGIN_USER_SELECTOR = "#LoginInputUC_UserIdTextBox"
LOGIN_PASSWORD_SELECTOR = "#LoginInputUC_PasswordTextBox"
LOGIN_BUTTON_SELECTOR = "#LoginInputUC_LoginImgButton"
RESERVATION_LIST_SELECTOR = "#YkrHeaderButton2"

# 例: 令 8. 8.23(日) 19:00～21:00
USE_DATE_PATTERN = re.compile(
    r"令\s*(?P<year>\d{1,2})\.\s*(?P<month>\d{1,2})\.\s*(?P<day>\d{1,2})"
    r"\s*\([^)]*\)\s*(?P<start>\d{1,2}:\d{2})\s*[～~]\s*(?P<end>\d{1,2}:\d{2})"
)


@dataclass(frozen=True)
class Reservation:
    """Googleカレンダーに登録する1件の予約。"""

    reservation_date: date
    facility_name: str
    receipt_number: str

    @property
    def dedupe_key(self) -> str:
        """同じ予約を二重に登録しないための安定キー。"""
        return f"{self.reservation_date.isoformat()}::{self.facility_name}::{self.receipt_number}"


def require_secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"GitHub Secret {name} が未設定です")
    return value


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def parse_reservation_cell(value: str) -> tuple[date, str] | None:
    """利用日時／施設セルから日付と施設名を返す。"""
    text = normalize_text(value)
    matched = USE_DATE_PATTERN.search(text)
    if not matched:
        return None

    # 令和元年は2019年なので、西暦 = 2018 + 令和年。
    reservation_date = date(
        2018 + int(matched.group("year")),
        int(matched.group("month")),
        int(matched.group("day")),
    )
    facility_name = normalize_text(text[matched.end() :])
    if not facility_name:
        return None
    return reservation_date, facility_name


def extract_reservations_from_html(html: str) -> list[Reservation]:
    """予約一覧表の全行から、本予約だけを抽出する。

    予約件数には依存しない。表中の各行について、利用日時の令和表記を持つ行を
    予約行とみなし、第1列が「本予約」のものだけを対象にする。
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[Reservation] = []

    for row in soup.select("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        status = normalize_text(cells[0].get_text(" ", strip=True))
        if status != "本予約":
            continue

        parsed = parse_reservation_cell(cells[1].get_text(" ", strip=True))
        if parsed is None:
            continue

        reservation_date, facility_name = parsed
        receipt_number = normalize_text(cells[2].get_text(" ", strip=True))
        items.append(
            Reservation(
                reservation_date=reservation_date,
                facility_name=facility_name,
                receipt_number=receipt_number,
            )
        )

    return items


def login_and_open_reservation_list(page: Page, user_id: str, password: str) -> None:
    """ログイン後、「予約の確認」画面を開く。予約変更操作は行わない。"""
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.locator("#LoginButton").click()
    page.locator(LOGIN_USER_SELECTOR).fill(user_id)
    page.locator(LOGIN_PASSWORD_SELECTOR).fill(password)
    page.locator(LOGIN_BUTTON_SELECTOR).click()
    page.wait_for_load_state("domcontentloaded")

    # 予約の確認ページは、ログイン後のヘッダーメニューから閲覧する。
    page.locator(RESERVATION_LIST_SELECTOR).click()
    page.wait_for_load_state("domcontentloaded")
    page.locator("table").first.wait_for(timeout=15_000)


def main() -> int:
    user_id = require_secret("RESERVATION_USER_ID")
    password = require_secret("RESERVATION_PASSWORD")
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(locale="ja-JP")
            try:
                login_and_open_reservation_list(page, user_id, password)
                reservations = extract_reservations_from_html(page.content())
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        print(f"予約サイトの応答待ちでタイムアウトしました: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"予約情報の取得に失敗しました: {exc}", file=sys.stderr)
        return 1

    print(f"本予約の取得件数: {len(reservations)}")
    for item in reservations:
        print(f"{item.reservation_date.isoformat()} | {item.facility_name}")

    try:
        result = sync_reservations(reservations, dry_run=dry_run)
    except Exception as exc:
        print(f"Googleカレンダー連携に失敗しました: {exc}", file=sys.stderr)
        return 1

    print(
        "Googleカレンダー処理結果: "
        f"新規 {result.created} 件、登録済み {result.skipped} 件、テスト対象 {result.planned} 件"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
