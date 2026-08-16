"""Googleカレンダーへの終日予定登録と重複防止。"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from src.fetch_reservations import Reservation

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
SOURCE_MARKER = "wakayama-facility-reservation"


@dataclass(frozen=True)
class CalendarSyncResult:
    created: int
    skipped: int
    planned: int


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"GitHub Secret {name} が未設定です")
    return value


def _get_calendar_service():
    token_data = json.loads(_require_env("GOOGLE_TOKEN_JSON"))
    credentials = Credentials.from_authorized_user_info(token_data, [CALENDAR_SCOPE])
    if not credentials.valid:
        if not credentials.refresh_token:
            raise RuntimeError("Google OAuthの更新トークンがありません")
        credentials.refresh(Request())
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def _event_key(reservation: "Reservation") -> str:
    """受付番号をそのままカレンダーに保存せず、ハッシュ化して重複判定に用いる。"""
    return hashlib.sha256(reservation.dedupe_key.encode("utf-8")).hexdigest()


def sync_reservations(
    reservations: list["Reservation"], *, dry_run: bool
) -> CalendarSyncResult:
    """未登録の予約だけを、体育館名をタイトルとする終日予定で登録する。"""
    if dry_run:
        return CalendarSyncResult(created=0, skipped=0, planned=len(reservations))

    calendar_id = _require_env("GOOGLE_CALENDAR_ID")
    service = _get_calendar_service()
    created = 0
    skipped = 0

    for reservation in reservations:
        event_key = _event_key(reservation)
        date_value = reservation.reservation_date.isoformat()
        next_date_value = (reservation.reservation_date + timedelta(days=1)).isoformat()

        existing = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=f"{date_value}T00:00:00Z",
                timeMax=f"{next_date_value}T00:00:00Z",
                singleEvents=True,
                privateExtendedProperty=f"reservation_sync_key={event_key}",
            )
            .execute()
        )
        if existing.get("items"):
            skipped += 1
            continue

        event = {
            "summary": reservation.facility_name,
            "description": "和歌山市公共施設予約システムから登録",
            "start": {"date": date_value},
            "end": {"date": next_date_value},
            "extendedProperties": {
                "private": {
                    "reservation_sync_key": event_key,
                    "source": SOURCE_MARKER,
                }
            },
        }
        service.events().insert(calendarId=calendar_id, body=event).execute()
        created += 1

    return CalendarSyncResult(created=created, skipped=skipped, planned=0)
