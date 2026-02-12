from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List, Set, Tuple

from playwright.sync_api import Page, sync_playwright

from search_conditions import apply_search_conditions

URL = "https://etsuran2.mlit.go.jp/TAKKEN/kensetuKensaku.do"
OUT_PATH = Path("data/results.csv")

MAX_PAGES = 10  # 無限ループ保険（必要なら増やしてOK）
PER_PAGE = 10   # 1ページの表示件数（このサイトは基本10）


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


def ensure_csv_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and path.stat().st_size > 0:
        return

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["カナ", "会社名", "所在地", "電話番号", "資本金"])


def append_csv_row(path: Path, row: List[str]) -> None:
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(row)


# =========================
# 整形
# =========================
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


# =========================
# 詳細ページ抽出（PhaseA）
# =========================
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


# =========================
# ページング：次へ
# =========================
def go_next(page: Page) -> bool:
    # 「次へ」ボタン（画像）
    btn = page.locator('img[src*="result_move_r"][onclick*="js_Search"]').first
    if btn.count() == 0:
        return False

    # 更新検知用：1行目のテキスト
    before = ""
    try:
        before = page.locator("table.re_disp tr").nth(1).inner_text().strip()
    except Exception:
        pass

    # onclick をそのまま実行（js_Search('2') みたいなの）
    onclick = btn.get_attribute("onclick") or ""
    if onclick:
        page.evaluate(onclick)
    else:
        btn.click()

    page.wait_for_selector("table.re_disp", timeout=30_000)

    # テーブルが変わるまで待つ
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


# =========================
# 本体：再開（ページスキップ）しながら全巡回
# =========================
def scrape_all(page: Page) -> None:
    seen = load_seen_keys(OUT_PATH)
    ensure_csv_header(OUT_PATH)

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
                page.go_back()
                page.wait_for_selector("table.re_disp", timeout=30_000)
                continue

            append_csv_row(OUT_PATH, [kana, company, address, phone, capital])
            seen.add(key)

            total_new += 1
            new_in_page += 1

            # 一覧に戻る
            page.go_back()
            page.wait_for_selector("table.re_disp", timeout=30_000)

        print(f"[page +{page_count}] new={new_in_page} total_new={total_new}")

        if not go_next(page):
            break

    print("✅ done. added:", total_new)


def run(headless: bool = False) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded")

        # 検索条件セット（※この関数内で検索実行までやる版なら下2行は不要）
        apply_search_conditions(page)

        # もし apply_search_conditions が「条件セットのみ」なら検索実行
        page.evaluate("js_Search('0')")
        page.wait_for_selector("table.re_disp", timeout=30_000)

        scrape_all(page)

        browser.close()


if __name__ == "__main__":
    run(headless=False)
