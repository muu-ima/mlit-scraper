# src/search_conditions.py
from __future__ import annotations

from playwright.sync_api import Page


def safe_select_value(page: Page, selector: str, value: str) -> None:
    loc = page.locator(selector)
    loc.wait_for(state="visible", timeout=20_000)
    loc.select_option(value=value)


def safe_select_label(page: Page, selector: str, label: str) -> None:
    loc = page.locator(selector)
    loc.wait_for(state="visible", timeout=20_000)
    loc.select_option(label=label)


def apply_search_conditions(page: Page) -> None:
    """
    安定版用：
    ・検索条件セット
    ・js_Search('0') を直接実行
    ・結果テーブル出現まで待機
    """

    # ページ初期ロード待ち
    page.wait_for_load_state("domcontentloaded")

    # =========================
    # 条件セット
    # =========================

    # 本店
    safe_select_value(page, "#choice", "1")

    # 東京都
    safe_select_value(page, "#kenCode", "13")

    # 業種（と）
    safe_select_value(page, "#gyosyu", "5")

    # 一般建設業
    safe_select_label(page, "#gyosyuType", "一般建設業")

    # 10件表示
    safe_select_value(page, 'select[name="dispCount"]', "10")

    # =========================
    # 検索実行（ここが安定ポイント）
    # =========================

    # UIクリックではなくJS直接実行
    page.evaluate("js_Search('0')")

    # 結果一覧テーブルが出るまで待つ
    page.wait_for_selector("table.re_disp", timeout=30_000)
