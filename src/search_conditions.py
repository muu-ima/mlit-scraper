from playwright.sync_api import Page


def apply_search_conditions(page: Page) -> None:

    # 本店
    page.locator("#honshaKbn").select_option(label="本店")

    # 東京都
    page.locator("#kenCode").select_option(label="東京都")

    # 業種「と」
    page.locator("#gyosyu").select_option("5")

    # 一般建設業
    page.locator("#gyosyuType").select_option(label="一般建設業")

    # 10件表示
    page.locator('select[name="dispCount"]').select_option("10")
