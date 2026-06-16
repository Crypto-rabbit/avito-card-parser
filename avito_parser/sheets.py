from __future__ import annotations

from pathlib import Path

from .report import REPORT_HEADERS, report_rows_for_sheets
from .parser import AvitoCard


def append_to_google_sheet(
    cards: list[AvitoCard],
    credentials_path: str,
    spreadsheet_id: str,
    worksheet_range: str = "A1",
) -> None:
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Google Sheets export requires google-api-python-client and google-auth. "
            "Install dependencies from requirements.txt."
        ) from exc

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_file(str(Path(credentials_path)), scopes=scopes)
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()

    sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range=worksheet_range,
        valueInputOption="RAW",
        body={"values": [REPORT_HEADERS]},
    ).execute()

    if cards:
        sheet.values().append(
            spreadsheetId=spreadsheet_id,
            range=worksheet_range,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": report_rows_for_sheets(cards)},
        ).execute()

