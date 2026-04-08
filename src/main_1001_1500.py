from __future__ import annotations

from math import ceil
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from scraper_common import (
    PER_PAGE,
    URL,
    append_csv_row,
    ensure_csv_header,
    extract_detail_info,
    go_next,
    load_last_row_number,
    return_to_results,
)
from search_conditions import apply_search_conditions

# ✅ 区間取得（1始まり）
START_ROW = 1001
END_ROW = 1500  # ここで止める（含む）
BATCH_SIZE = 100  # 1回の実行で取得する件数

# ✅ 出力は分けるのが安全（混ざらない）
OUT_PATH = Path("data/results_1001_1500.csv")

# 余裕込みでページ制限（保険）
MAX_PAGES = ceil(END_ROW / PER_PAGE) + 5


def scrape_range(page: Page) -> None:
    ensure_csv_header(OUT_PATH, ["カナ", "会社名", "所在地", "電話番号", "資本金", "取得行番号"])

    if END_ROW < START_ROW:
        raise ValueError("END_ROW must be >= START_ROW")

    start_row = START_ROW
    last_row_no = load_last_row_number(OUT_PATH)
    if last_row_no is not None:
        if last_row_no >= END_ROW:
            print(f"✅ already done through row {last_row_no}")
            return
        if last_row_no >= START_ROW:
            start_row = last_row_no + 1
            print(f"⏩ resume from row {start_row} (last saved: {last_row_no})")

    start_index = start_row - 1
    end_index = END_ROW - 1

    skip_pages = start_index // PER_PAGE
    skip_rows_in_first_page = start_index % PER_PAGE

    if skip_pages > 0:
        print(f"⏩ skipping pages: {skip_pages} (to reach row {start_row})")
        for _ in range(skip_pages):
            if not go_next(page):
                print("⚠️ reached end while skipping pages")
                return

    current_page_base = skip_pages * PER_PAGE
    page_count = 0
    total_saved = 0
    first_page = True
    batch_end_row = min(END_ROW, start_row + BATCH_SIZE - 1)
    batch_end_index = batch_end_row - 1

    print(f"🎯 current batch: {start_row}-{batch_end_row}")

    while True:
        page_count += 1
        if page_count > MAX_PAGES:
            raise RuntimeError("MAX_PAGES超え（保険停止）")

        trs = page.locator("table.re_disp tr")
        n = trs.count()

        start_i = 1 + (skip_rows_in_first_page if first_page else 0)
        first_page = False

        for i in range(start_i, n):
            global_index = current_page_base + (i - 1)
            global_row_no = global_index + 1

            if global_index > end_index:
                print(f"✅ done. saved={total_saved} (stopped at row {global_row_no})")
                return

            if global_index > batch_end_index:
                print(f"✅ batch done. saved={total_saved} (stopped at row {global_row_no})")
                return

            if global_index < start_index:
                continue

            tr = trs.nth(i)
            link = tr.locator("a").first
            if link.count() == 0:
                continue

            link.click()
            page.wait_for_load_state("domcontentloaded")

            company, kana, address, phone, capital = extract_detail_info(page)
            append_csv_row(
                OUT_PATH,
                [kana, company, address, phone, capital, str(global_row_no)],
            )
            total_saved += 1
            print(f"  💾 saved row={global_row_no} batch={total_saved}/{BATCH_SIZE} company={company}")

            return_to_results(page)

        print(f"[page] base_row={current_page_base + 1} saved={total_saved}")

        if not go_next(page):
            print("⚠️ reached end before END_ROW")
            return

        current_page_base += PER_PAGE


def run(headless: bool = False) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded")

        # 検索条件セットと検索実行
        apply_search_conditions(page)

        scrape_range(page)
        browser.close()


if __name__ == "__main__":
    run(headless=False)
