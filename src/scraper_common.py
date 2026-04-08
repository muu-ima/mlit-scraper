from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List, Tuple

from playwright.sync_api import Page

URL = "https://etsuran2.mlit.go.jp/TAKKEN/kensetuKensaku.do"
PER_PAGE = 50  # 1ページの表示件数


def ensure_csv_header(path: Path, header: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def append_csv_row(path: Path, row: List[str]) -> None:
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def load_last_row_number(path: Path) -> int | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    for row in reversed(rows[1:]):
        if not row:
            continue
        try:
            return int((row[-1] or "").strip())
        except ValueError:
            continue

    return None


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_detail_info(page: Page) -> Tuple[str, str, str, str, str]:
    def pick(label: str) -> str:
        el = page.locator(f'th:has-text("{label}") + td').first
        return norm(el.inner_text()) if el.count() else ""

    kana = norm(page.locator("p.phonetic").first.inner_text())
    name_cell = page.locator("td:has(p.phonetic)").first
    company = norm(name_cell.inner_text().replace(kana, ""))

    address = pick("主たる営業所の所在地")
    phone = pick("電話番号")
    capital = pick("資本金額")

    return company, kana, address, phone, capital


def return_to_results(page: Page) -> None:
    try:
        page.go_back(wait_until="domcontentloaded", timeout=10_000)
    except Exception:
        page.evaluate("history.back()")

    page.wait_for_selector("table.re_disp", timeout=30_000)


def go_next(page: Page) -> bool:
    btn = page.locator('img[src*="result_move_r"][onclick*="js_Search"]').first
    if btn.count() == 0:
        return False

    before = ""
    try:
        before = page.locator("table.re_disp tr").nth(1).inner_text().strip()
    except Exception:
        pass

    onclick = btn.get_attribute("onclick") or ""
    if onclick:
        page.evaluate(onclick)
    else:
        btn.click()

    page.wait_for_selector("table.re_disp", timeout=30_000)

    if before:
        page.wait_for_function(
            """(beforeText) => {
                const tr = document.querySelector('table.re_disp tr:nth-child(2)');
                if (!tr) return false;
                const now = (tr.textContent || '').trim();
                return now !== beforeText;
            }""",
            arg=before,
            timeout=30_000,
        )

    return True
