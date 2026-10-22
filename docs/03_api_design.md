# 03. API設計

## 1. 共通仕様

| 項目 | 仕様 |
|---|---|
| ベースパス | `/api` |
| 形式 | JSON(UTF-8)。CSVインポートだけはリクエスト本文が `text/csv` |
| 文字列の扱い | 前後の空白を除いてから長さを検証する(`str_strip_whitespace`) |
| 未定義の項目 | 400 で拒否する(`extra="forbid"`)。理由:項目名のタイプミスを黙って無視しないため |
| 日付 | `"YYYY-MM-DD"`。月は `"YYYY-MM"` |
| 金額 | 整数(StrictInt)。BR-01 |
| 率 | 小数第1位の文字列(例:`"12.5"`)。BR-06 |
| 認証 | なし |
| 自動ドキュメント | `/docs`(Swagger UI)、`/openapi.json`。本書の内容と一致させる |

### HTTPステータスコードの使い分け

| コード | 用途 |
|---|---|
| 200 | 取得・更新・状態変更・CSVインポートの結果(一部の行がエラーでも200) |
| 201 | 作成 |
| 204 | 削除(本文なし) |
| 400 | 入力の検証エラー(VALIDATION_ERROR、INVALID_JSON、CSVの形式エラー) |
| 404 | 対象リソースがない、または未定義のパス |
| 405 | メソッドが許可されていない |
| 409 | 状態の競合(使用中のカテゴリ、状態遷移違反など) |
| 413 | CSVのサイズ・行数の上限超過 |
| 415 | CSVインポートの Content-Type が不正 |
| 500 | 予期しないエラー、保存の失敗 |

- **なぜ検証エラーを 422 ではなく 400 にするか**:FastAPI標準の422形式を使わないことを明確にするため。
  また「不正入力は4xx」(NFR-002)の中で、入力不備は 400、業務状態の競合は 409 と、意味で分けられる。

## 2. 統一エラー形式(ERR-01)

すべてのエラーレスポンスは次の形式で返す。

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [
      { "field": "amount", "code": "OUT_OF_RANGE", "params": { "min": 1, "max": 9999999 } }
    ]
  }
}
```

| 項目 | 型 | 説明 |
|---|---|---|
| error.code | str | エラーコード(08_error_handling.md の一覧)。**フロントはこの値を翻訳キーに使う** |
| error.message | str | 開発者向けの英語メッセージ。画面には表示しない |
| error.details | array | 項目ごとの詳細。該当がなければ空配列 |
| details[].field | str / null | 項目のパス(`.` 区切り。例:`categories.0.amount`)。`body` / `query` / `path` は付けない |
| details[].code | str | 項目エラーコード(ERR-02) |
| details[].params | object | 文言の埋め込みに使う値(min, max など)。なければ `{}` |

### 例外ハンドラの仕様(ERR-03)

| 捕捉する例外 | 変換後のステータス | error.code |
|---|---|---|
| `RequestValidationError`(Pydantic検証) | 400 | `VALIDATION_ERROR`。JSON構文エラーの場合は `INVALID_JSON` |
| `AppError`(業務例外。code / status / details を持つ) | AppError の値 | AppError の値 |
| `StarletteHTTPException` 404 | 404 | `NOT_FOUND` |
| `StarletteHTTPException` 405 | 405 | `METHOD_NOT_ALLOWED` |
| その他の `StarletteHTTPException` | そのまま | `HTTP_ERROR` |
| `Exception`(想定外) | 500 | `INTERNAL_ERROR`(スタックトレースはログのみに出し、レスポンスに含めない) |

Pydantic のエラー種別(`type`)は、次の対応表で項目エラーコードに変換する。

| Pydantic の type | details[].code | params |
|---|---|---|
| missing | FIELD_REQUIRED | |
| int_type, int_parsing, string_type, bool_type, date_type, dict_type, list_type, model_type | INVALID_TYPE | |
| greater_than_equal, less_than_equal, greater_than, less_than | OUT_OF_RANGE | min / max |
| string_too_short | TOO_SHORT | min |
| string_too_long | TOO_LONG | max |
| date_parsing, date_from_datetime_parsing | INVALID_DATE | |
| literal_error, enum | INVALID_CHOICE | choices |
| extra_forbidden | UNKNOWN_FIELD | |
| json_invalid | (error.code を INVALID_JSON にする) | |
| 独自検証(PydanticCustomError) | 独自に指定したコード(例:INVALID_MONTH、DATE_OUT_OF_RANGE) | 指定値 |
| 上記以外 | INVALID_VALUE | |

- OUT_OF_RANGE の params は、モデルに定義した最小値・最大値の両方を返す。
  - 理由:フロントで「1〜9,999,999の範囲で入力してください」と1つの文言で表示できるため。

## 3. エンドポイント一覧

| API-ID | メソッド | パス | 概要 | 正常 | 主な異常 |
|---|---|---|---|---|---|
| API-01 | GET | /api/status | 今日の日付・データ復旧の状態 | 200 | |
| API-02 | GET | /api/categories | カテゴリ一覧 | 200 | |
| API-03 | POST | /api/categories | ユーザーカテゴリの追加 | 201 | 400, 409 |
| API-04 | DELETE | /api/categories/{id} | カテゴリの削除 | 204 | 404, 409 |
| API-05 | GET | /api/expenses?month= | 月別の支出一覧 | 200 | 400 |
| API-06 | POST | /api/expenses | 支出の登録 | 201 | 400 |
| API-07 | GET | /api/expenses/{id} | 支出1件の取得 | 200 | 404 |
| API-08 | PUT | /api/expenses/{id} | 支出の更新(全項目を置き換え) | 200 | 400, 404 |
| API-09 | DELETE | /api/expenses/{id} | 支出の削除 | 204 | 404 |
| API-10 | GET | /api/subscriptions | サブスク一覧 | 200 | |
| API-11 | POST | /api/subscriptions | サブスクの登録 | 201 | 400 |
| API-12 | GET | /api/subscriptions/{id} | サブスク1件の取得 | 200 | 404 |
| API-13 | PUT | /api/subscriptions/{id} | サブスクの更新 | 200 | 400, 404 |
| API-14 | DELETE | /api/subscriptions/{id} | サブスクの削除 | 204 | 404 |
| API-15 | POST | /api/subscriptions/{id}/pause | 停止 | 200 | 404, 409 |
| API-16 | POST | /api/subscriptions/{id}/resume | 再開 | 200 | 404, 409 |
| API-17 | POST | /api/subscriptions/{id}/renew | 更新済みにする | 200 | 404, 409 |
| API-18 | GET | /api/subscriptions/upcoming | 更新予定(7日以内と超過分) | 200 | |
| API-19 | GET | /api/budgets | 予算設定の取得 | 200 | |
| API-20 | PUT | /api/budgets | 予算設定の更新(全体を置き換え) | 200 | 400 |
| API-21 | GET | /api/summary?month= | 月次集計・予算判定・アラート | 200 | 400 |
| API-22 | GET | /api/charts/category-breakdown?month= | 円グラフ用データ | 200 | 400 |
| API-23 | GET | /api/charts/monthly-trend?month= | 棒グラフ用データ(6か月) | 200 | 400 |
| API-24 | POST | /api/imports/expenses | CSVインポート | 200 | 400, 413, 415 |

- `month` を省略したときは当月(BR-02)とする。
- `/api/subscriptions/upcoming` は `/api/subscriptions/{id}` より先にルートを登録する。
  - 理由:後に登録すると `upcoming` がIDとして解釈されるため。
- 画面の配信:`GET /` は `static/index.html` を返し、`/static/*` は StaticFiles で配信する。どちらもAPIの対象外。

---

## 4. スキーマ定義

> 各スキーマ名は Pydantic モデル名と一致させる(07_module_design.md の MOD-10)。
> 制約の表記:`int[1..9999999]` は下限・上限を含む範囲、`str[0..100]` は文字数の範囲。

### 4.1 共通

```jsonc
// ErrorResponse
{ "error": { "code": "str", "message": "str",
             "details": [ { "field": "str|null", "code": "str", "params": {} } ] } }
```

### 4.2 API-01 GET /api/status → `StatusOut`

```json
{
  "today": "2026-10-23",
  "timezone": "Asia/Tokyo",
  "current_month": "2026-10",
  "data_recovered": false,
  "backup_file": null
}
```

| 項目 | 型 | 説明 |
|---|---|---|
| today | date | Clock.today()(BR-02) |
| current_month | str | today が属する月 |
| data_recovered | bool | 起動後に破損ファイルを退避したら true(ERR-30) |
| backup_file | str / null | 退避先のファイル名(パスを含まない) |

### 4.3 カテゴリ

```jsonc
// CategoryOut
{ "id": "cat-000001", "key": "category.food", "name": null, "is_fixed": true, "in_use": true }
{ "id": "cat-000009", "key": null, "name": "Pets", "is_fixed": false, "in_use": false }
```

| 項目 | 型 | 説明 |
|---|---|---|
| key | str / null | 固定カテゴリの翻訳キー(AD-03) |
| name | str / null | ユーザーカテゴリの名前 |
| in_use | bool | 支出から参照されているか。画面で削除ボタンを無効にするのに使う |

- **API-02** GET `/api/categories` → `{"items": [CategoryOut, ...]}`(`CategoryListOut`)。
  並び順は固定カテゴリ(id順)→ ユーザーカテゴリ(id順)。
- **API-03** POST `/api/categories`

  | 項目 | 型 | 必須 | 制約 |
  |---|---|---|---|
  | name | str[1..30] | ○ | DATA-05 の重複チェックに該当したら 409 CATEGORY_NAME_DUPLICATED |

  正常時は 201 で `CategoryOut` を返す。
- **API-04** DELETE `/api/categories/{id}`
  - 正常時は 204。
  - 異常時:404 CATEGORY_NOT_FOUND / 409 CATEGORY_FIXED / 409 CATEGORY_IN_USE(`details[0].params.count` に使用件数を入れる)

### 4.4 支出

```jsonc
// ExpenseIn(POST / PUT の本文)
{ "date": "2026-10-23", "amount": 1200, "category_id": "cat-000001", "memo": "Lunch" }
// ExpenseOut
{ "id": "exp-000001", "date": "2026-10-23", "amount": 1200, "category_id": "cat-000001", "memo": "Lunch" }
// ExpenseListOut(API-05)
{ "month": "2026-10", "total": 1200, "count": 1, "items": [ ExpenseOut ] }
```

| 項目 | 型 | 必須 | 制約 | 項目エラーコード |
|---|---|---|---|---|
| date | date | ○ | 2000-01-01〜2099-12-31 | INVALID_DATE / DATE_OUT_OF_RANGE |
| amount | StrictInt[1..9999999] | ○ | BR-01 | INVALID_TYPE / OUT_OF_RANGE |
| category_id | str | ○ | 存在するカテゴリであること | UNKNOWN_CATEGORY |
| memo | str[0..100] | | 省略時は "" | TOO_LONG |

- UNKNOWN_CATEGORY はカテゴリの存在をサービス層で確認して判定する。
  返すときは 400 VALIDATION_ERROR の details として返す(Pydanticのエラーと同じ形式)。
  - 理由:フロントから見れば入力ミスであり、項目エラーとして同じ場所に表示できるため。
- API-05 の並び順は date の降順 → id の降順(同じ日付なら新しく登録したものが上)。
- 他のIDを参照する項目は、文字列として受け取ってからサービス層で存在を確認する。

### 4.5 サブスク

```jsonc
// SubscriptionIn(POST / PUT の本文)
{ "name": "Video streaming", "amount": 1490, "cycle": "monthly", "next_renewal_date": "2026-10-31" }
// SubscriptionOut
{ "id": "sub-000001", "name": "Video streaming", "amount": 1490, "cycle": "monthly",
  "next_renewal_date": "2026-10-31", "anchor_day": 31, "anchor_month": null,
  "status": "active", "monthly_equivalent": 1490 }
```

| 項目 | 型 | 必須 | 制約 |
|---|---|---|---|
| name | str[1..50] | ○ | |
| amount | StrictInt[1..9999999] | ○ | |
| cycle | "monthly" / "yearly" | ○ | INVALID_CHOICE |
| next_renewal_date | date | ○ | 2000-01-01〜2099-12-31 |

- `monthly_equivalent` は BR-04-1 で計算した値。フロントで計算させないため、APIで返す。
- anchor の扱いは BR-03 の表に従う。
- **API-10** の応答は `{"items": [SubscriptionOut]}`(`SubscriptionListOut`)。
  並び順は status(active が先)→ next_renewal_date の昇順 → id の昇順。
- **API-15〜17** は本文なしで呼び、変更後の `SubscriptionOut` を返す。409 の条件は DATA-04 と BR-03 を参照。
- **API-18** GET `/api/subscriptions/upcoming` → `UpcomingListOut`

```json
{
  "today": "2026-10-23",
  "window_days": 7,
  "items": [
    { "id": "sub-000003", "name": "Cloud storage", "amount": 1300, "cycle": "yearly",
      "next_renewal_date": "2026-10-20", "days_until": -3, "is_overdue": true },
    { "id": "sub-000001", "name": "Video streaming", "amount": 1490, "cycle": "monthly",
      "next_renewal_date": "2026-10-30", "days_until": 7, "is_overdue": false }
  ]
}
```

- 抽出条件と並び順は BR-04-2 に従う(next_renewal_date の昇順)。

### 4.6 予算

```jsonc
// BudgetsIn(API-20 本文)/ BudgetsOut(API-19, API-20 の応答)
{
  "overall": 150000,
  "categories": [ { "category_id": "cat-000001", "amount": 40000 } ]
}
```

| 項目 | 型 | 必須 | 制約 |
|---|---|---|---|
| overall | StrictInt[0..99999999] / null | ○ | 0 と null は「未設定」。保存時は null |
| categories | array | ○ | 同じ category_id を重複させない(DUPLICATED_CATEGORY) |
| categories[].category_id | str | ○ | 存在するカテゴリ(UNKNOWN_CATEGORY) |
| categories[].amount | StrictInt[0..99999999] / null | ○ | 0 と null は未設定 → 保存しない |

- PUT は**全体の置き換え**とする。送られなかったカテゴリの予算は削除される。
  - 理由:予算設定画面は全カテゴリを1つのフォームで送るため、差分更新より単純で、状態の食い違いが起きない。
- BudgetsOut の categories には、予算が設定されているものだけを category_id の昇順で入れる。

### 4.7 API-21 GET /api/summary?month=YYYY-MM → `MonthlySummaryOut`

```json
{
  "month": "2026-10",
  "previous_month": "2026-09",
  "next_month": "2026-11",
  "total": 112500,
  "previous_total": 100000,
  "change_amount": 12500,
  "change_rate": "12.5",
  "overall_budget": { "budget": 120000, "spent": 112500, "usage_percent": 93, "status": "caution" },
  "categories": [
    { "category_id": "cat-000001", "key": "category.food", "name": null,
      "total": 42000, "previous_total": 38000, "change_amount": 4000, "change_rate": "10.5",
      "budget": 40000, "usage_percent": 105, "status": "over" }
  ],
  "subscriptions": { "monthly_total": 3114, "active_count": 3 },
  "alerts": [
    { "scope": "category", "category_id": "cat-000001", "key": "category.food", "name": null,
      "status": "over", "usage_percent": 105, "budget": 40000, "spent": 42000 },
    { "scope": "overall", "category_id": null, "key": null, "name": null,
      "status": "caution", "usage_percent": 93, "budget": 120000, "spent": 112500 }
  ]
}
```

- `previous_month` / `next_month` は画面の月移動に使う(BR-02。2000-01 の前月・2099-12 の翌月は null)。
- `status` は `none` / `ok` / `caution` / `over` のいずれか(BR-05)。
- `change_rate` は前月が0円のとき null(BR-06)。
- categories の対象と並び順は BR-07-1、alerts の並び順は BR-05 に従う。

### 4.8 API-22 GET /api/charts/category-breakdown?month= → `CategoryBreakdownOut`

```json
{
  "month": "2026-10",
  "total": 112500,
  "items": [
    { "kind": "category", "category_id": "cat-000001", "key": "category.food", "name": null,
      "amount": 42000, "ratio_percent": "37.3" },
    { "kind": "other", "category_id": null, "key": "category.others", "name": null,
      "amount": 3000, "ratio_percent": "2.7" }
  ]
}
```

- `kind="other"` は BR-07-2 の集約行で、最大1件・必ず末尾に置く。0件のときは `items: []`。

### 4.9 API-23 GET /api/charts/monthly-trend?month= → `MonthlyTrendOut`

```json
{
  "end_month": "2026-10",
  "items": [
    { "month": "2026-05", "total": 98000 },
    { "month": "2026-06", "total": 0 },
    { "month": "2026-07", "total": 105000 },
    { "month": "2026-08", "total": 101000 },
    { "month": "2026-09", "total": 100000 },
    { "month": "2026-10", "total": 112500 }
  ]
}
```

- items は必ず6件で、古い順に並ぶ(BR-07-3)。

### 4.10 API-24 POST /api/imports/expenses → `ImportReportOut`

| 項目 | 仕様 |
|---|---|
| リクエスト | 本文に CSVファイルのバイト列をそのまま入れる。`Content-Type: text/csv`(`; charset=...` は無視する) |
| Content-Type が異なる | 415 CSV_UNSUPPORTED_MEDIA_TYPE |
| ファイル名 | 受け取らない(不要なため) |

- **なぜ multipart/form-data にしないか**:FastAPI でファイルを受け取るには `python-multipart` の追加が必要になるため。
  本文に直接入れる方式なら依存を増やさずに済む。文字コードを判定するにはどうせ生のバイト列が必要なので、受け取り方として自然でもある。
  ブラウザからは `fetch(url, {method: "POST", headers: {"Content-Type": "text/csv"}, body: file})` で送れる。

```json
{
  "encoding": "shift_jis",
  "total_rows": 10,
  "imported_count": 7,
  "error_count": 2,
  "duplicate_count": 1,
  "errors": [
    { "line": 4, "field": "amount", "code": "INVALID_AMOUNT", "value": "12a0" },
    { "line": 9, "field": null, "code": "DUPLICATE_IN_FILE", "value": null }
  ]
}
```

- 検証規則とエラーコードは 06_csv_import_design.md(CSV-04、CSV-07)に定める。
- `total_rows = imported_count + error_count + duplicate_count` が常に成り立つ。
