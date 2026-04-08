# mlit-scraper

国土交通省の建設業者検索ページを Playwright で巡回し、結果を CSV に保存するスクレイピングプロジェクトです。

## 前提

- Python 3.12 系
- Playwright が使えること
- `.venv` を使う前提

## セットアップ

仮想環境をまだ作っていない場合:

```bash
python3 -m venv .venv
```

仮想環境を有効化:

```bash
source .venv/bin/activate
```

依存関係を入れる:

```bash
pip install playwright
python -m playwright install chromium
```

## ファイル構成

- `src/main.py`
  - 通常の全件取得用
  - 出力先: `data/results.csv`
- `src/main_1001.py`
  - 現在は `src/main.py` の互換エントリポイント
- `src/main_1001_1500.py`
  - 1001 件目から 1500 件目までの範囲取得用
  - 出力先: `data/results_1001_1500.csv`
- `src/main_1501_2000.py`
  - 1501 件目から 2000 件目までの範囲取得用
  - 出力先: `data/results_1501_2000_50perpage.csv`
  - 既存 CSV の最終 `取得行番号` から再開可能
- `src/search_conditions.py`
  - 検索条件の設定と検索実行
- `src/scraper_common.py`
  - 共通の CSV 処理、詳細抽出、ページ送り処理

## 実行コマンド

通常実行:

```bash
.venv/bin/python src/main.py
```

`main_1001.py` から通常実行:

```bash
.venv/bin/python src/main_1001.py
```

1001 件目から 1500 件目まで取得:

```bash
.venv/bin/python src/main_1001_1500.py
```

1501 件目から 2000 件目まで取得:

```bash
.venv/bin/python src/main_1501_2000.py
```

headless で通常実行:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, 'src'); import main; main.run(headless=True)"
```

headless で 1001-1500 を実行:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, 'src'); import main_1001_1500; main_1001_1500.run(headless=True)"
```

## 取得条件

現在の検索条件は `src/search_conditions.py` で固定しています。

- 本店
- 東京都
- 業種: と
- 許可区分: 一般建設業
- 1ページ 50 件表示

## 出力

- `data/results.csv`
  - カナ, 会社名, 所在地, 電話番号, 資本金
- `data/results_1001_1500.csv`
  - カナ, 会社名, 所在地, 電話番号, 資本金, 取得行番号
- `data/results_1501_2000_50perpage.csv`
  - カナ, 会社名, 所在地, 電話番号, 資本金, 取得行番号

CSV は UTF-8 with BOM (`utf-8-sig`) で保存しています。

## 補足

- `src/main.py` は既存の `data/results.csv` を見て、取得済みの会社名 + 電話番号をスキップします
- `src/main.py` も、1回の実行で最大 100 件だけ取得します
- `src/main_1001_1500.py` は `START_ROW` と `END_ROW` を変えることで取得範囲を調整できます
- `src/main_1001_1500.py` と `src/main_1501_2000.py` は、既存 CSV の最終 `取得行番号` を見て途中から再開できます
- `src/main_1001_1500.py` と `src/main_1501_2000.py` は、1回の実行で最大 100 件だけ取得します
- 各スクリプトは保存のたびに `saved row=...` を出すので、どこまで進んだか追いやすくしています
- デフォルトでは `run(headless=False)` なのでブラウザ画面が表示されます

## 動作確認

構文チェック:

```bash
.venv/bin/python -m py_compile src/main.py src/main_1001.py src/main_1001_1500.py src/main_1501_2000.py src/search_conditions.py src/scraper_common.py
```
