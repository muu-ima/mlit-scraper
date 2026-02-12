from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple, Set

from playwright.sync_api import sync_playwright, Page

from search_conditions import apply_search_conditions

URL = "https://etsuran2.mlit.go.jp/TAKKEN/kensetuKensaku.do"

OUT_PATH = Path("data/results.csv")

MAX_PAGES = 10       # ← 今は10ページで止める
PER_PAGE = 10        # 1ページ10件固定


# =========================
# 再開用：既取得キー
# =========================
def load_seen_keys(path: Path) -> Set[Tuple[str, str]]:
    if not path.exists():
        return set()

    seen: Set[Tuple[str, str]] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        rows = list(r)

    if len(rows) <= 1:
        return set()

    for row in rows[1:]:
        if len(row) < 4:
            continue
        name = row[1].strip()
        phone = row[3].strip()
        seen.add((name, phone))

    return seen


# =========================
# CSV追記
# =========================
def append_rows(path: Path, rows: List[List[str]]) -> None:
    file_exists = path.exists()

    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)

        if not file_exists:
            w.writerow(["カナ", "会社名", "所在地", "電話番号", "資本金", "区分"])

        for r in rows:
            w.writerow(r)


# =========================
# 1ページ分取得
# =========================
def scrape_one_page(page: Page, seen: Set[Tuple[str, str]]) -> List[List[str]]:
    rows = page.locator("table tbody tr")
    count = rows.count()

    result: List[List[str]] = []

    for i in range(count):
        tr = rows.nth(i)
        tds = tr.locator("td")

        kana = tds.nth(0).inner_text().strip()
        name = tds.nth(1).inner_text().strip()
        addr = tds.nth(3).inner_text().strip()
        phone = tds.nth(4).inner_text().strip()
        cap = tds.nth(5).inner_text().strip()
        kubun = tds.nth(6).inner_text().strip()

        key = (name, phone)
        if key in seen:
            continue

        seen.add(key)

        result.append([
            kana,
            name,
            addr,
            phone,
            cap,
            kubun
        ])

    return result


# =========================
# 全体スクレイプ
# =========================
def scrape_all(page: Page) -> None:
    seen = load_seen_keys(OUT_PATH)

    if seen:
        skip_pages = len(seen) // PER_PAGE
        print(f"⏩ resume: already have {len(seen)} rows -> skipping {skip_pages} pages...")

        for _ in range(skip_pages):
            page.locator("text=次へ").click()
            page.wait_for_load_state("networkidle")

    total_new = 0

    for page_index in range(MAX_PAGES):

        new_rows = scrape_one_page(page, seen)
        new_in_page = len(new_rows)

        if new_in_page != PER_PAGE:
            raise RuntimeError(
                f"このページで {PER_PAGE} 件揃わなかった (new_in_page={new_in_page}) -> 停止"
            )

        append_rows(OUT_PATH, new_rows)

        total_new += new_in_page

        print(f"[page +{page_index+1}] new={new_in_page} total_new={total_new}")

        # 最終ページなら終了
        if page_index == MAX_PAGES - 1:
            break

        # 次ページへ
        page.locator("text=次へ").click()
        page.wait_for_load_state("networkidle")


# =========================
# 実行
# =========================
def run(headless: bool = False) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox"]
        )

        page = browser.new_page()
        page.goto(URL)

        # 検索条件セット
        apply_search_conditions(page)

        print("検索成功")

        scrape_all(page)

        browser.close()


if __name__ == "__main__":
    run(headless=False)
