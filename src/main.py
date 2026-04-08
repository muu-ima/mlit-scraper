from __future__ import annotations

import csv
from pathlib import Path
from typing import Set, Tuple

from playwright.sync_api import Page, sync_playwright

from search_conditions import apply_search_conditions
from scraper_common import (
    PER_PAGE,
    URL,
    append_csv_row,
    ensure_csv_header,
    extract_detail_info,
    go_next,
    return_to_results,
)

OUT_PATH = Path("data/results.csv")

MAX_PAGES = 10  # 無限ループ保険（必要なら増やしてOK）
BATCH_SIZE = 100  # 1回の実行で取得する件数


# =========================
# 再開用：既に取得済みキーを読む
# =========================
def load_seen_keys(path: Path) -> Set[Tuple[str, str]]:
    if not path.exists():
        return set()

    seen: Set[Tuple[str, str]] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        rows = list(r)

    if not rows:
        return set()

    # 1行目ヘッダ想定：カナ,会社名,所在地,電話番号,資本金
    for row in rows[1:]:
        if len(row) < 4:
            continue

        # CSVの列順：0=カナ, 1=会社名, 3=電話番号
        company = (row[1] or "").strip()
        phone = (row[3] or "").strip()
        if company:
            seen.add((company, phone))

    return seen


# =========================
# 本体：再開（ページスキップ）しながら全巡回
# =========================
def scrape_all(page: Page) -> None:
    seen = load_seen_keys(OUT_PATH)
    ensure_csv_header(OUT_PATH, ["カナ", "会社名", "所在地", "電話番号", "資本金"])

    start_row = len(seen) + 1
    batch_end_row = start_row + BATCH_SIZE - 1
    print(f"🎯 current batch: {start_row}-{batch_end_row}")

    # 既存件数から「開始ページ」を計算してスキップ
    skip_pages = len(seen) // PER_PAGE
    if skip_pages > 0:
        print(f"⏩ resume: already have {len(seen)} rows -> skipping {skip_pages} pages...")
        for _ in range(skip_pages):
            if not go_next(page):
                print("⚠️ no more pages while skipping. (already reached end)")
                return

    page_count = 0
    total_new = 0

    while True:
        page_count += 1
        if page_count > MAX_PAGES:
            raise RuntimeError("MAX_PAGES超え。無限ループ防止停止")

        trs = page.locator("table.re_disp tr")
        n = trs.count()

        new_in_page = 0

        for i in range(1, n):
            tr = trs.nth(i)
            link = tr.locator("a").first
            if link.count() == 0:
                continue

            # 詳細へ
            link.click()
            page.wait_for_load_state("domcontentloaded")

            company, kana, address, phone, capital = extract_detail_info(page)
            key = (company.strip(), phone.strip())

            if key in seen:
                # 既読：保存せず戻る
                return_to_results(page)
                continue

            if total_new >= BATCH_SIZE:
                print(f"✅ batch done. added={total_new}")
                return

            append_csv_row(OUT_PATH, [kana, company, address, phone, capital])
            seen.add(key)

            total_new += 1
            new_in_page += 1
            print(f"  💾 saved row={len(seen)} batch={total_new}/{BATCH_SIZE} company={company}")

            # 一覧に戻る
            return_to_results(page)

        print(f"[page +{page_count}] new={new_in_page} total_new={total_new}")

        if not go_next(page):
            break

    print("✅ done. added:", total_new)


def run(headless: bool = False) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded")

        # 検索条件セットと検索実行
        apply_search_conditions(page)

        scrape_all(page)

        browser.close()


if __name__ == "__main__":
    run(headless=False)
