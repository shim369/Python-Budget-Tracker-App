# Python-Budget-Tracker-App

[English](README.md) | **日本語**

FastAPI で作った、ローカルで動く軽量な**家計・サブスク管理アプリ**です。
支出を記録して月ごとの使い道を把握し、サブスクの更新日を見逃さず、予算を超える前に警告を受け取れます。
画面は英語が既定で、ボタン1つで日本語に切り替えられます。

<p align="center">
  <img src="docs/images/dashboard-ja.png" alt="ダッシュボード:月の支出合計、予算アラート、更新予定、グラフ" width="720">
</p>

このリポジトリは、**詳細設計 → 実装 → 単体テスト → 結合テスト**の工程を練習するためのポートフォリオです。
工程ごとにドキュメントを作り、要件から設計・コード・テストまでを追えるようにしています([トレーサビリティ表](docs/09_traceability.md))。

## 機能

| | 機能 | 内容 |
|---|---|---|
| 💴 | 支出 | 登録・編集・削除・月別の一覧(日付、金額、カテゴリ、メモ) |
| 🏷️ | カテゴリ | 固定の8カテゴリ + ユーザー追加。使用中のカテゴリは削除できない |
| 🔁 | サブスク | 月次 / 年次、有効 / 停止。「更新済み」で次回更新日を月末の規則に従って進める(1/31 → 2/28 → 3/31、うるう日も考慮) |
| 🔔 | 更新日の通知 | 7日以内に更新を迎えるもの(と更新日を過ぎたもの)をダッシュボードに表示 |
| 📊 | 月次集計 | カテゴリ別の合計、前月比、サブスク合計(月額換算)、円グラフと直近6か月の棒グラフ |
| 🚦 | 予算 | 全体とカテゴリ別。**80%で注意**、**100%を超えたら超過**(ちょうど100%は注意のまま) |
| 📥 | CSVインポート | UTF-8 / UTF-8(BOM付き)/ Shift_JIS。不正な行と重複行はスキップし、行番号つきで報告 |
| 🌐 | English / 日本語 | 文言、日付(`Oct 23, 2026` / `2026年10月23日`)、金額(`¥1,200` / `1,200円`)、グラフのラベル。選んだ言語を記憶する |
| 🛡️ | 壊れにくい保存 | JSON ファイル1つに、ロックと原子的な書き込みで保存。ファイルが壊れていても退避して起動できる |

## 技術スタック

| 区分 | 技術 |
|---|---|
| バックエンド | Python 3.12、FastAPI、Pydantic v2、uvicorn |
| フロントエンド | HTML5、CSS、JavaScript(ES Modules、ビルド工程なし) |
| UI ライブラリ(同梱、CDN 不使用) | Alpine.js 3.17.4、Chart.js 4.5.1、Pico CSS 2.1.1 |
| API | REST + JSON。エラーは統一形式 `{"error": {"code", "message", "details"}}` |
| データ保存 | JSON ファイル(`data/budget.json`) |
| テスト | pytest、pytest-cov、FastAPI TestClient、Node.js 標準のテストランナー(`node --test`) |
| ツール | uv |

金額はすべて整数(円)で扱います。前月比などの率は `Decimal` で計算して文字列(`"12.5"`)で返すため、浮動小数点の誤差が画面に出ることはありません。

## 起動方法

必要なもの:[uv](https://docs.astral.sh/uv/)(Python 3.12 は必要に応じて uv が入れます)。Node.js は JavaScript のテストを実行する場合だけ必要です。

```bash
uv sync

# 任意:サンプルデータで始める(2026年10月前後の支出・サブスク・予算)
cp data/sample.json data/budget.json

uv run uvicorn app.main:app --reload
```

<http://127.0.0.1:8000/> を開きます。API のドキュメントは <http://127.0.0.1:8000/docs> です。

- **単一プロセスで起動してください。** ファイルのロックはプロセス内でしか効かないため、`--workers` は使いません([DATA-01](docs/04_data_design.md))。
- 「今日」はサーバーのタイムゾーンに関係なく、**Asia/Tokyo** の日付で判定します。
- 別のデータファイルを使う場合は `BUDGET_DATA_FILE=/path/to/file.json` を指定します。
- `data/*.json`(`data/sample.json` を除く)と `data/*.csv` は Git の管理対象外です。

### データファイルが壊れた場合

壊れたファイルを `data/budget.json.corrupt-YYYYMMDDHHMMSS` に退避し、空のデータで起動して、画面にバナーを表示します。
元のファイルはそのまま残ります。手で修正してからアプリを止め、`data/budget.json` に戻してください。

## CSV の形式

```csv
date,amount,category,memo
2026-10-01,1200,food,Lunch
2026/10/02,"3,980",日用品,Detergent
```

- 必須の列は `date`、`amount`、`category`。`memo` は任意です。列の順番は自由です。
- `category` には、カテゴリ名(日本語・英語)か、`food` などのコードを指定します。
- 上限は 1MB・5,000行。日付・金額・カテゴリ・メモがすべて同じ行は重複として扱います。

詳細:[docs/06_csv_import_design.md](docs/06_csv_import_design.md)

## テストの実行

```bash
uv run pytest                                  # 単体 + 結合(304件)
uv run pytest --cov=app --cov-report=term      # カバレッジつき
uv run pytest tests/unit                       # 単体テストのみ
node --test "tests/js/*.test.mjs"              # JavaScript の単体テスト(32件)
```

## テスト結果

| | 結果 |
|---|---|
| pytest(単体 251 + 結合 53) | ✅ 304件成功 |
| node --test | ✅ 32件成功 |
| `app/` の行カバレッジ | **99.9%**(単体テストのみで 91.4%、業務ルールは 100%) |
| 性能(支出 5,000件) | 最も遅い API で 23.5ms(要件は 500ms 以内) |
| 検出・修正した不具合 | 3件([バグ票](docs/bug_reports.md)) |

詳細:[docs/test_report.md](docs/test_report.md)

## ディレクトリ構成

```
app/
├── main.py            # アプリの生成、ルーター、静的ファイル、例外ハンドラ
├── clock.py           # 差し替え可能な「今日」(テストで固定する)
├── errors.py          # エラーコード、AppError、統一エラー形式
├── domain/            # 業務ルールの純粋関数(金額、月、更新日、予算、集計、CSV)
├── schemas/           # Pydantic の入出力モデル(API 設計と1対1)
├── services/          # ユースケース(1操作 = 1トランザクション)
├── repositories/      # JSON ストア:ロック、原子的な書き込み、破損からの復旧
└── routers/           # REST エンドポイント(/api/...)
static/
├── index.html         # 単一ページ(ハッシュルーティング)
├── js/                # main、router、API クライアント、i18n、表示整形、グラフ、各画面
├── i18n/              # en.json、ja.json
├── css/custom.css     # Pico CSS への最小限の上書き
└── vendor/            # Alpine.js、Chart.js、Pico CSS と VERSIONS.md
data/sample.json       # サンプルデータ
docs/                  # 設計書・テスト文書
tests/
├── unit/              # pytest の単体テスト
├── integration/       # TestClient による API レベルの結合テスト
└── js/                # node --test の単体テスト
```

## ドキュメント

設計書とテスト文書は [`docs/`](docs) にあります。

| 工程 | ドキュメント |
|---|---|
| 基本設計・要件 | [00 基本設計](docs/00_basic_design.md)、[01 要件一覧](docs/01_requirements.md) |
| 詳細設計 | [02 画面](docs/02_screen_design.md)、[03 API](docs/03_api_design.md)、[04 データ](docs/04_data_design.md)、[05 業務ルール](docs/05_business_rules.md)、[06 CSVインポート](docs/06_csv_import_design.md)、[07 モジュール](docs/07_module_design.md)、[08 エラー処理](docs/08_error_handling.md) |
| トレーサビリティ | [09 要件 → 設計 → コード → テスト](docs/09_traceability.md) |
| テスト | [単体テスト仕様書](docs/ut_spec.md)、[結合テスト仕様書](docs/it_spec.md)、[手動確認手順書](docs/it_manual.md)、[テスト結果報告書](docs/test_report.md)、[バグ票](docs/bug_reports.md) |

コードのコメントと docstring には設計 ID(例:`[BR-03]`)を書いているので、コードから対応する設計書の規則をたどれます。

## 使用ライブラリとライセンス

| ライブラリ | バージョン | ライセンス |
|---|---|---|
| [Alpine.js](https://alpinejs.dev/) | 3.17.4 | MIT |
| [Chart.js](https://www.chartjs.org/) | 4.5.1 | MIT |
| [Pico CSS](https://picocss.com/) | 2.1.1 | MIT |
| [FastAPI](https://fastapi.tiangolo.com/)、[Pydantic](https://docs.pydantic.dev/)、[uvicorn](https://www.uvicorn.org/) | `uv.lock` を参照 | MIT / BSD-3-Clause |

フロントエンドのライブラリは、オフラインで動くように `static/vendor/` に同梱しています。取得元・ハッシュ値・ライセンス全文は [static/vendor/VERSIONS.md](static/vendor/VERSIONS.md) にあります。

## 将来の拡張案

現在の範囲には含めていないものです。設計書に記載した案をまとめています。

- 返金(マイナスの支出)— X-01
- 月ごとに異なる予算 — X-02
- サブスクの価格改定履歴と支払実績 — X-03
- CSV インポート時に未知のカテゴリを自動作成 — X-04
- CSV インポートのプレビュー(dry-run)と CSV エクスポート — X-05、X-06
- 壊れたデータファイルから正常なレコードを救済するツール — X-07
- 日付・月・ファイルの入力欄をアプリの言語で表示 — X-08
- 金額欄が空のときのエラー文言の改善 — X-09
- 複数ユーザー・認証、データベース、複数プロセスでの運用
