# 09. トレーサビリティ表

要件(01)→ 設計(02〜08)→ 実装 → テストの対応表。
テストの列は、工程3(UT-xxx)と工程4(IT-xxx / MT-xxx)で記入して完成させる。

## 1. 要件 → 設計

| 要件ID | 要件(要約) | 画面 | API | 業務ルール / CSV | データ | モジュール | エラー |
|---|---|---|---|---|---|---|---|
| REQ-001 | 支出の登録 | SCR-02(02-4〜02-9) | API-06 | BR-01, BR-02 | DATA-02, 03 | ExpenseService, MOD-30 UC-1 | VALIDATION_ERROR, UNKNOWN_CATEGORY |
| REQ-002 | 支出の編集 | SCR-02(02-3, 02-9) | API-07, 08 | BR-01 | DATA-02 | ExpenseService | EXPENSE_NOT_FOUND |
| REQ-003 | 支出の削除 | SCR-02(02-10) | API-09 | - | DATA-02 | ExpenseService | EXPENSE_NOT_FOUND |
| REQ-004 | 月別の支出一覧 | SCR-02(02-1〜02-3) | API-05 | BR-02 | DATA-02 | ExpenseService, domain.period | INVALID_MONTH |
| REQ-005 | カテゴリ一覧 | SCR-04(04-2) | API-02 | - | DATA-05 | CategoryService, domain.categories | - |
| REQ-006 | カテゴリの追加 | SCR-04(04-4) | API-03 | - | DATA-03, 05 | CategoryService | CATEGORY_NAME_DUPLICATED |
| REQ-007 | カテゴリの削除(使用中は不可) | SCR-04(04-5) | API-04 | - | DATA-02(削除時の連動) | CategoryService | CATEGORY_IN_USE, CATEGORY_FIXED |
| REQ-008 | サブスクのCRUD | SCR-03(03-1, 03-4〜03-7) | API-10〜14 | BR-03(anchor の設定), BR-04-1 | DATA-02 | SubscriptionService | SUBSCRIPTION_NOT_FOUND |
| REQ-009 | サブスクの停止・再開 | SCR-03(03-3) | API-15, 16 | BR-03(再開) | DATA-04 | SubscriptionService, domain.renewal | SUBSCRIPTION_STATE_CONFLICT |
| REQ-010 | 次回更新日の再計算 | SCR-03(03-8) | API-17 | BR-03 | DATA-04 | domain.renewal, MOD-30 UC-2 | SUBSCRIPTION_INACTIVE, RENEW_TOO_EARLY |
| REQ-011 | 更新予定の表示 | SCR-01(01-7), SCR-03(03-2) | API-18 | BR-04-2 | - | domain.renewal | - |
| REQ-012 | 月次のカテゴリ別合計 | SCR-01(01-2, 01-10) | API-21 | BR-02, BR-07-1 | - | SummaryService, domain.summary | INVALID_MONTH |
| REQ-013 | 前月比 | SCR-01(01-3, 01-10) | API-21 | BR-06 | - | domain.summary | - |
| REQ-014 | サブスク合計(月額換算) | SCR-01(01-5), SCR-03(03-1) | API-21, 10 | BR-04-1, BR-01-2 | - | domain.money | - |
| REQ-015 | グラフ | SCR-01(01-8, 01-9)、6章 CH-01/02 | API-22, 23 | BR-07-2, BR-07-3 | - | domain.summary, charts/ | - |
| REQ-016 | 予算の設定 | SCR-04(04-1〜04-3) | API-19, 20 | BR-01-1 | DATA-02 | BudgetService | DUPLICATED_CATEGORY, UNKNOWN_CATEGORY |
| REQ-017 | 予算判定・警告 | SCR-01(01-4, 01-6, 01-10) | API-21 | BR-05 | - | domain.budget_rule, MOD-30 UC-1 | - |
| REQ-018 | CSVの一括取り込み | SCR-05 | API-24 | CSV-01〜03, 06 | DATA-03 | ImportService, domain.csv_rules, MOD-30 UC-3 | CSV_* |
| REQ-019 | 不正行のスキップと結果レポート | SCR-05(05-4, 05-5) | API-24 | CSV-04, 05, 07 | - | domain.csv_rules | 行エラーコード |
| REQ-020 | 言語切替と記憶 | SCR-00(00-3)、4章 | - | - | - | i18n/i18n.js, $store.i18n | - |
| REQ-021 | 日付・金額・グラフの言語別表示 | 4章、6章 | - | - | - | i18n/format.js, charts/chart-config.js | - |
| REQ-022 | エラーコードの翻訳表示 | 4章「エラー表示」 | 全API(ERR-01) | - | - | api/client.js, pages/shared.js | ERR-02, ERR-20 |
| REQ-023 | 翻訳キーの一致 | - | - | - | - | static/i18n/*.json | - |
| NFR-001 | 応答500ms以内 | - | API-21〜23 | BR-07 | DATA-01 | SummaryService | - |
| NFR-002 | 不正入力は4xx・統一形式 | 4章 | 全API | BR-01 | - | errors.py, schemas/ | ERR-01〜03 |
| NFR-003 | 破損時も起動できる | SCR-00(00-4) | API-01 | - | DATA-01, 06 | JsonStore.initialize | ERR-30 |
| NFR-004 | オフライン動作 | 全画面 | - | - | - | static/vendor/(AD-02) | NETWORK_ERROR |
| NFR-005 | 同時書き込みの整合性 | - | 書き込み系の全API | - | DATA-01, 03 | JsonStore.transaction | ERR-31 |
| NFR-006 | 金額は整数 | 02, 05(入力) | 全スキーマ | BR-01, BR-06 | DATA-02 | schemas/common.py(Amount) | INVALID_TYPE |
| NFR-007 | 業務ルールの配置 | 7章 | - | 05 全体 | - | domain/、MOD-02, MOD-40 | - |

## 2. 要件 → 実装 → テスト(工程2〜4で記入)

> 実装ファイルの列は工程2で記入済み。テストと結果の列は工程3・4で記入する。
> パスの省略:`a/` = `app/`、`s/` = `static/js/`。

| 要件ID | 実装ファイル | 単体テスト(UT) | 結合テスト(IT:自動) | 手動確認(MT) | 結果 |
|---|---|---|---|---|---|
| REQ-001 | a/routers/expenses.py, a/services/expense_service.py, a/schemas/expense.py, a/schemas/common.py, s/pages/expenses.js | | | | |
| REQ-002 | a/routers/expenses.py, a/services/expense_service.py, s/pages/expenses.js | | | | |
| REQ-003 | a/routers/expenses.py, a/services/expense_service.py, s/pages/expenses.js | | | | |
| REQ-004 | a/services/expense_service.py, a/domain/period.py, s/pages/expenses.js | | | | |
| REQ-005 | a/routers/categories.py, a/services/category_service.py, a/domain/categories.py, static/i18n/*.json | | | | |
| REQ-006 | a/services/category_service.py, a/domain/categories.py(is_name_taken), s/pages/budgets.js | | | | |
| REQ-007 | a/services/category_service.py(delete), s/pages/budgets.js | | | | |
| REQ-008 | a/routers/subscriptions.py, a/services/subscription_service.py, a/domain/renewal.py(anchors_for, anchors_after_edit), s/pages/subscriptions.js | | | | |
| REQ-009 | a/services/subscription_service.py(pause, resume), a/domain/renewal.py(roll_forward) | | | | |
| REQ-010 | a/services/subscription_service.py(renew), a/domain/renewal.py(advance, can_renew) | | | | |
| REQ-011 | a/services/subscription_service.py(upcoming), a/domain/renewal.py(select_upcoming), s/pages/dashboard.js | | | | |
| REQ-012 | a/services/summary_service.py, a/domain/summary.py(month_total, summarize_categories) | | | | |
| REQ-013 | a/domain/summary.py(change_rate), s/i18n/format.js(formatRate, formatSignedMoney) | | | | |
| REQ-014 | a/domain/money.py(monthly_equivalent), a/services/summary_service.py | | | | |
| REQ-015 | a/domain/summary.py(breakdown, trend), a/routers/summary.py, s/charts/chart-config.js, s/charts/chart-render.js | | | | |
| REQ-016 | a/routers/budgets.py, a/services/budget_service.py, a/schemas/budget.py, s/pages/budgets.js | | | | |
| REQ-017 | a/domain/budget_rule.py, a/domain/summary.py(build_alerts), s/pages/dashboard.js | | | | |
| REQ-018 | a/routers/imports.py, a/services/import_service.py, a/domain/csv_rules.py(decode, parse_header), s/pages/csv-import.js | | | | |
| REQ-019 | a/domain/csv_rules.py(validate_row, duplicate_key), a/services/import_service.py | | | | |
| REQ-020 | s/i18n/i18n.js, s/main.js($store.i18n), static/index.html | | | | |
| REQ-021 | s/i18n/format.js, s/charts/chart-config.js | | | | |
| REQ-022 | a/errors.py, s/api/client.js, s/pages/shared.js, s/main.js($errMsg, $fieldMsg) | | | | |
| REQ-023 | static/i18n/en.json, static/i18n/ja.json, s/i18n/i18n.js(collectKeys) | | | | |
| NFR-001 | a/services/summary_service.py, a/repositories/json_store.py | | | | |
| NFR-002 | a/errors.py, a/schemas/common.py, a/main.py(_remove_default_422_from_openapi) | | | | |
| NFR-003 | a/repositories/json_store.py(initialize, _move_aside), a/routers/status.py | | | | |
| NFR-004 | static/vendor/*, static/index.html | | | | |
| NFR-005 | a/repositories/json_store.py(transaction, _write) | | | | |
| NFR-006 | a/schemas/common.py(Amount), a/domain/money.py, a/domain/summary.py(Decimal) | | | | |
| NFR-007 | a/domain/*(純粋関数), s/pages/*(計算なし) | | | | |

## 3. 設計 → 要件の逆引き(設計の過不足チェック)

| 設計ID | 対応する要件 |
|---|---|
| BR-01 | REQ-001, 014, 016, NFR-006 |
| BR-02 | REQ-001, 004, 012 |
| BR-03 | REQ-008, 009, 010 |
| BR-04 | REQ-011, 014 |
| BR-05 | REQ-017 |
| BR-06 | REQ-013 |
| BR-07 | REQ-012, 015, NFR-001 |
| CSV-01〜07 | REQ-018, 019 |
| DATA-01 | NFR-001, 003, 005 |
| DATA-04 | REQ-009, 010 |
| DATA-05 | REQ-005, 006, 018(カテゴリの照合) |
| ERR-01〜03 | NFR-002, REQ-022 |
| ERR-20 | REQ-022, NFR-004 |
| ERR-30〜31 | NFR-003, 005 |
| API-01 | NFR-003, REQ-001(日付の初期値), BR-02 |

- 要件に対応しない設計がないことを確認済み。API-01 の `today` は REQ-001 の日付の初期値と BR-02(サーバー側で日付を判定)に対応している。
