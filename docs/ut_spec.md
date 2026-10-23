# 単体テスト仕様書(UT)

| 項目 | 内容 |
|---|---|
| 対象 | `app/`(domain / schemas / errors / repositories / clock / services)、`static/js/`(純粋関数モジュール) |
| ツール | pytest + pytest-cov(Python)、`node --test`(JavaScript) |
| 実行 | `uv run pytest tests/unit --cov=app`、`node --test "tests/js/*.test.mjs"` |
| 合格基準 | 全ケース成功。`app/` の行カバレッジ 80% 以上 |
| 対象外 | HTTP経由の動作(工程4の IT)、Chart.js の実描画と Alpine コンポーネント(工程4の手動確認 MT) |

## 1. テスト方針

| 観点 | 方針 |
|---|---|
| 同値クラス | 正常・異常のクラスごとに代表値を1つ以上入れる |
| 境界値 | 設計書の「境界」を必ず含め、境界の内側と外側を対で確認する(例:79% / 80%、7日 / 8日) |
| 異常系 | 型違い、範囲外、形式違い、存在しない参照、壊れたファイル、I/O失敗 |
| 純粋関数 | domain 層は引数と戻り値だけで検証する。「今日」は引数で固定する |
| I/Oを伴うもの | JsonStore と services は pytest の `tmp_path` に作った一時ファイルで検証する。日付は FixedClock で固定する |
| テストID | `UT-<領域>-<連番>`。parametrize のケースIDとテスト関数名に含め、仕様書と対応づける |

### 領域

| 略号 | 対象 | テストファイル | 設計ID |
|---|---|---|---|
| MNY | domain/money.py | tests/unit/test_money.py | BR-01, BR-04-1 |
| PER | domain/period.py | tests/unit/test_period.py | BR-02 |
| RNW | domain/renewal.py | tests/unit/test_renewal.py | BR-03, BR-04-2 |
| BGT | domain/budget_rule.py | tests/unit/test_budget_rule.py | BR-05 |
| SUM | domain/summary.py | tests/unit/test_summary.py | BR-05(アラート), BR-06, BR-07 |
| CAT | domain/categories.py | tests/unit/test_categories.py | DATA-05 |
| CSV | domain/csv_rules.py | tests/unit/test_csv_rules.py | CSV-01〜05 |
| SCH | schemas(Pydantic のバリデーション) | tests/unit/test_schemas.py | 03 4章, MOD-10 |
| ERR | errors.py(エラーの変換) | tests/unit/test_errors.py | ERR-01〜03 |
| STO | repositories(JsonStore, DataFile) | tests/unit/test_json_store.py | DATA-01〜03, ERR-30, ERR-31 |
| CLK | clock.py | tests/unit/test_clock.py | BR-02 |
| SVC | services(一時ストア + FixedClock) | tests/unit/test_services.py | API層を除くユースケース |
| I18N | 翻訳辞書(キーの一致) | tests/unit/test_i18n_keys.py | REQ-023 |
| JFMT | js/i18n/format.js | tests/js/format.test.mjs | REQ-021 |
| JI18N | js/i18n/i18n.js | tests/js/i18n.test.mjs | REQ-020 |
| JCLI | js/api/client.js | tests/js/client.test.mjs | ERR-20 |
| JCHT | js/charts/chart-config.js | tests/js/chart-config.test.mjs | CH-01, CH-02 |
| JRTE | js/router.js | tests/js/router.test.mjs | SCR-00 |
| JSHR | js/pages/shared.js | tests/js/shared.test.mjs | ERR-20, 02 4章 |

---

## 2. テストケース(Python)

### UT-MNY 金額(BR-01, BR-04-1)

| ID | 観点 | 入力 | 期待結果 |
|---|---|---|---|
| UT-MNY-01 | 月額換算:月次 | 1490, monthly | 1490 |
| UT-MNY-02 | 月額換算:年次で割り切れる | 12000, yearly | 1000 |
| UT-MNY-03 | 月額換算:年次で端数を切り捨て | 1490, yearly | 124 |
| UT-MNY-04 | 月額換算:年次で12未満 | 11, yearly | 0 |
| UT-MNY-05 | 月額換算:上限 | 9999999, yearly | 833333 |
| UT-MNY-06 | CSV金額:正常(桁区切りなし・あり・空白付き) | "1200" / "1,200" / " 3,980 " / "9,999,999" | 1200 / 1200 / 3980 / 9999999 |
| UT-MNY-07 | CSV金額:空 | "" / "  " | AMOUNT_REQUIRED |
| UT-MNY-08 | CSV金額:形式違い | "1.5", "-100", "¥1200", "1200円", "1,20", "12,0000", "abc", "１２００"(全角) | INVALID_AMOUNT |
| UT-MNY-09 | CSV金額:範囲の境界 | "0" / "1" / "9999999" / "10000000" | OUT_OF_RANGE / 1 / 9999999 / OUT_OF_RANGE |

### UT-PER 月の境界(BR-02)

| ID | 観点 | 入力 | 期待結果 |
|---|---|---|---|
| UT-PER-01 | 月の解析:正常と範囲の境界 | "2026-10", "2000-01", "2099-12" | (年, 月) |
| UT-PER-02 | 月の解析:異常 | "2026-1", "2026-13", "2026-00", "1999-12", "2100-01", "2026/10", "abcd-ef", "" | None |
| UT-PER-03 | 日付 → 月 | 2026-10-31 / 2026-11-01 | "2026-10" / "2026-11" |
| UT-PER-04 | 月の範囲(末日) | 2027-02 / 2028-02 / 2026-04 / 2026-12 | 末日が 28 / 29 / 30 / 31 |
| UT-PER-05 | 前月(年またぎ・下限) | "2026-01" / "2026-10" / "2000-01" | "2025-12" / "2026-09" / None |
| UT-PER-06 | 翌月(年またぎ・上限) | "2026-12" / "2099-12" | "2027-01" / None |
| UT-PER-07 | 直近n か月(年をまたぐ・古い順) | "2026-03", 6 | 2025-10 〜 2026-03 の6件 |
| UT-PER-08 | 日付範囲の境界 | 1999-12-31 / 2000-01-01 / 2099-12-31 / 2100-01-01 | F / T / T / F |
| UT-PER-09 | 不正な月を渡したときの例外 | month_range("2026-13") など | ValueError |

### UT-RNW 次回更新日(BR-03, BR-04-2)

| ID | 観点 | 入力 | 期待結果 |
|---|---|---|---|
| UT-RNW-01〜11 | advance の具体例(BR-03 の表 No.1〜11) | 05_business_rules.md の表のとおり | 表のとおり |
| UT-RNW-12 | anchor の設定(月次・年次) | 2026-10-31 monthly / 2028-02-29 yearly | (31, None) / (29, 2) |
| UT-RNW-13 | 編集:日付を変えた | 新しい日付 2026-11-15 | anchor を新しい日付から設定し直す |
| UT-RNW-14 | 編集:日付が同じ(月次のまま) | anchor 31、日付 2027-02-28 は同じ | anchor_day=31 を維持 |
| UT-RNW-15 | 編集:月次 → 年次(日付は同じ) | | anchor_month = 日付の月 |
| UT-RNW-16 | 編集:年次 → 月次(日付は同じ) | | anchor_month = None |
| UT-RNW-17 | 編集:年次のまま(日付は同じ) | anchor (29, 2) | 維持 |
| UT-RNW-18 | 年次なのに anchor_month がない | | ValueError |
| UT-RNW-19 | 再開時の繰り越し(BR-03 の例 a/b/c) | | 2026-10-31 / 2026-10-23 / 2026-12-01 |
| UT-RNW-20 | 再開時に複数周期を繰り越す(月末 anchor) | 2026-01-31, today 2026-04-15 | 2026-04-30 |
| UT-RNW-21 | 更新できるか(境界) | today+7 / today+8 / today / 過去 | T / F / T / T |
| UT-RNW-22 | 更新予定:抽出の境界(BR-04-2 の表) | -3, 0, 7, 8 日 | 8日だけ対象外。days_until と is_overdue が正しい |
| UT-RNW-23 | 更新予定:停止中は対象外 | paused で 0日 | 対象外 |
| UT-RNW-24 | 更新予定:並び順 | 日付の降順・同日で別ID | 日付の昇順 → id の昇順 |

### UT-BGT 予算判定(BR-05)

| ID | 観点 | spent / budget | 期待 status / usage |
|---|---|---|---|
| UT-BGT-01 | 0円 | 0 / 10000 | ok / 0 |
| UT-BGT-02 | 79% | 7900 / 10000 | ok / 79 |
| UT-BGT-03 | 79.99%(80%の直前) | 7999 / 10000 | ok / 79 |
| UT-BGT-04 | 80%(注意の境界) | 8000 / 10000 | caution / 80 |
| UT-BGT-05 | 99% | 9900 / 10000 | caution / 99 |
| UT-BGT-06 | ちょうど100% | 10000 / 10000 | **caution** / 100 |
| UT-BGT-07 | 100.01%(超過の直後) | 10001 / 10000 | **over** / 100 |
| UT-BGT-08 | 101% | 10100 / 10000 | over / 101 |
| UT-BGT-09 | 予算が未設定(None・0) | 5000 / None, 5000 / 0 | none / None |
| UT-BGT-10 | 整数比較で判定していること(端数の出る予算) | 2 / 3(66.7%)、8 / 10、12 / 15(80%ちょうど) | ok / caution / caution |

### UT-SUM 集計・前月比・グラフ(BR-05〜07)

| ID | 観点 | 期待結果 |
|---|---|---|
| UT-SUM-01〜10 | 前月比(BR-06 の表 10ケース。前月0円 → None、四捨五入、負の値) | 表のとおり |
| UT-SUM-11 | 構成比の丸め | 42000/112500 → "37.3"、1/3 → "33.3"、2/3 → "66.7" |
| UT-SUM-12 | 月の境界での集計(9/30・10/1・10/31・11/1) | 10月分には 10/1 と 10/31 だけが入る |
| UT-SUM-13 | 月合計で月が None のとき | 0 |
| UT-SUM-14 | カテゴリ別:対象の範囲(今月だけ・前月だけ・予算だけ) | 3つとも行が出る。支出も予算もないカテゴリは出ない |
| UT-SUM-15 | カテゴリ別:並び順(合計の降順 → id の昇順) | 同額は id 順 |
| UT-SUM-16 | アラートの並び順 | over → caution。同じ status では全体 → カテゴリ(使用率の降順) |
| UT-SUM-17 | アラートの対象外 | ok / none は含めない |
| UT-SUM-18 | 円グラフ:0件 | (0, []) |
| UT-SUM-19 | 円グラフ:1件 | ratio "100.0" |
| UT-SUM-20 | 円グラフ:8件(集約の境界) | 8件、other なし |
| UT-SUM-21 | 円グラフ:9件 | 上位7件 + other(残り2件の合計)= 8件 |
| UT-SUM-22 | 円グラフ:同額の順序 | id の昇順 |
| UT-SUM-23 | 棒グラフ:支出のない月も0で6件(年またぎ) | "2026-02" までの6件、古い順 |

### UT-CAT カテゴリ(DATA-05)

| ID | 観点 | 期待結果 |
|---|---|---|
| UT-CAT-01 | 翻訳キーの導出 | "food" → "category.food"、None → None |
| UT-CAT-02 | 固定カテゴリ8件の id と code | DATA-05 の表と一致 |
| UT-CAT-03 | 名前の重複:固定カテゴリの別名(日英、大文字小文字、前後空白) | "食費", "FOOD", " Food " は使用済み |
| UT-CAT-04 | 名前の重複:既存のユーザーカテゴリ | "pets" と "Pets" は重複 |
| UT-CAT-05 | 重複しない名前 | "Hobby" は未使用 |
| UT-CAT-06 | CSV照合表 | "食費" / "daily goods" / "pets" → それぞれのカテゴリID |

### UT-CSV CSV検証(CSV-01〜05)

| ID | 観点 | 期待結果 |
|---|---|---|
| UT-CSV-01 | 文字コード:UTF-8 | encoding "utf-8" |
| UT-CSV-02 | 文字コード:BOM付き UTF-8 | "utf-8-sig"、BOM が除かれる |
| UT-CSV-03 | 文字コード:Shift_JIS(機種依存文字 ① を含む) | "shift_jis" で正しく読める |
| UT-CSV-04 | 文字コード:ASCII のみ | "utf-8" |
| UT-CSV-05 | 文字コード:どちらでも読めない(UTF-16、BOM の後が不正)。BUG-001 の再テストとして UTF-16(BOM付き / LE / BE / CJK)・UTF-32・NUL を含むバイト列を追加 | None |
| UT-CSV-06 | ヘッダー:列の順番は自由、大文字小文字・空白を無視 | 列名 → 位置の対応 |
| UT-CSV-07 | ヘッダー:memo は省略できる | 3列で成功 |
| UT-CSV-08 | ヘッダー:必須列の不足・未定義の列・同じ列名の重複 | MISSING_COLUMN / UNKNOWN_COLUMN / DUPLICATE_COLUMN |
| UT-CSV-09 | 日付:受け付ける形式 | 2026-10-01、2026/10/1、2026/1/05 |
| UT-CSV-10 | 日付:異常 | "" → DATE_REQUIRED、2026-02-30 / 2026-10/01 / 20261001 / 26-10-01 → INVALID_DATE、1999-12-31 / 2100-01-01 → DATE_OUT_OF_RANGE |
| UT-CSV-11 | 行:正常(日本語カテゴリ・memo 100文字) | ValidRow |
| UT-CSV-12 | 行:列数の不一致 | COLUMN_COUNT_MISMATCH |
| UT-CSV-13 | 行:検証順(日付と金額が両方とも不正) | 先に判定する日付のエラーだけを返す |
| UT-CSV-14 | 行:カテゴリが空・存在しない | CATEGORY_REQUIRED / UNKNOWN_CATEGORY |
| UT-CSV-15 | 行:memo 101文字 | MEMO_TOO_LONG |
| UT-CSV-16 | 行:エラー値を50文字で切り詰める | value の長さが50 |
| UT-CSV-17 | 重複キーの正規化 | "2026/10/1","1,200","食費" と "2026-10-01","1200","food" のキーが一致する |
| UT-CSV-18 | 空行の判定 | [] / ["", " "] は空行。["", "1"] は空行ではない |

### UT-SCH Pydantic のバリデーション(03 4章)

| ID | 観点 | 入力 | 期待される details[].code |
|---|---|---|---|
| UT-SCH-01 | 支出:正常(文字列の空白を除去、memo は省略可) | | 成功、memo="" |
| UT-SCH-02 | 金額の型 | 1200.0 / "1200" / true / null | INVALID_TYPE |
| UT-SCH-03 | 金額の範囲 | 0 / 10000000 | OUT_OF_RANGE(params に min=1, max=9999999) |
| UT-SCH-04 | 金額の境界(正常) | 1 / 9999999 | 成功 |
| UT-SCH-05 | 日付の形式 | "2026-02-30" / "2026/10/01" / "2026-10-01T00:00:00" | INVALID_DATE |
| UT-SCH-06 | 日付の型 | 1700000000 | INVALID_TYPE |
| UT-SCH-07 | 日付の範囲 | "1999-12-31" / "2100-01-01" | DATE_OUT_OF_RANGE |
| UT-SCH-08 | memo の長さ | 100文字 / 101文字 | 成功 / TOO_LONG |
| UT-SCH-09 | 未定義の項目・必須項目の欠落 | | UNKNOWN_FIELD / FIELD_REQUIRED |
| UT-SCH-10 | サブスク:周期が選択肢にない | "weekly" | INVALID_CHOICE(choices) |
| UT-SCH-11 | サブスク・カテゴリ:名前が空白だけ・長すぎる | "  " / 51文字 / 31文字 | TOO_SHORT / TOO_LONG |
| UT-SCH-12 | 予算:null と範囲 | null / 0 / 99999999 / -1 / 100000000 | 成功 ×3 / OUT_OF_RANGE ×2 |
| UT-SCH-13 | 月クエリ | "2026-13" | INVALID_MONTH |
| UT-SCH-14 | 率は JSON で文字列になる | Decimal("12.5") | "12.5" |

### UT-ERR エラーの変換(ERR-01〜03)

| ID | 観点 | 期待結果 |
|---|---|---|
| UT-ERR-01 | 項目パスの組み立て | ("body","categories",0,"amount") → "categories.0.amount"、("body",) → None |
| UT-ERR-02 | 標準エラー種別の変換表 | missing → FIELD_REQUIRED、greater_than_equal → OUT_OF_RANGE{min} など |
| UT-ERR-03 | 独自コード(PydanticCustomError)はそのまま | OUT_OF_RANGE と ctx がそのまま入る |
| UT-ERR-04 | 未知の種別 | INVALID_VALUE |
| UT-ERR-05 | 統一エラー形式 | {"error": {"code","message","details"}} |
| UT-ERR-06 | 業務例外の補助関数 | not_found → 404、conflict → 409(params あり / なし)、field_error → 400 VALIDATION_ERROR |

### UT-STO 保存(DATA-01〜03, ERR-30, ERR-31)

| ID | 観点 | 期待結果 |
|---|---|---|
| UT-STO-01 | ファイルがない(初回) | 初期データ(固定カテゴリ8件)で作成。復旧フラグは立たない |
| UT-STO-02 | JSONとして読めない | `.corrupt-<時刻>` に退避して初期化。recovery に退避ファイル名 |
| UT-STO-03 | 整合性違反(存在しないカテゴリへの参照) | 破損として退避 |
| UT-STO-04 | 整合性違反(固定カテゴリの欠落・ID重複・採番の遅れ・年次の anchor_month 欠落) | 破損として扱う(DataFile の検証で ValidationError) |
| UT-STO-05 | 退避ファイル名が重複する | `-1` を付ける |
| UT-STO-06 | 起動時に残っている .tmp を削除 | .tmp がなくなる |
| UT-STO-07 | トランザクションで変更を保存 | 再読み込みで反映されている |
| UT-STO-08 | ブロック内で例外 / discard() | 保存されない |
| UT-STO-09 | 書き込み失敗(os.replace が OSError) | STORAGE_WRITE_FAILED(500)。元のファイルは変わらず、.tmp も残らない |
| UT-STO-10 | 採番 | exp-000001 → exp-000002。種類ごとに独立 |
| UT-STO-11 | 退避(改名)に失敗 | OSError を送出する(起動を中止) |
| UT-STO-12 | サンプルデータ | data/sample.json が DataFile の検証に通る |

### UT-CLK 時計(BR-02)

| ID | 観点 | 入力(UTC) | 期待結果(JST の日付) |
|---|---|---|---|
| UT-CLK-01 | 月末 23:59:59 JST | 2026-10-31T14:59:59Z | 2026-10-31 |
| UT-CLK-02 | 翌月 0:00:00 JST | 2026-10-31T15:00:00Z | 2026-11-01 |
| UT-CLK-03 | タイムゾーンなしの日時 | naive datetime | ValueError |
| UT-CLK-04 | 固定の時計 | FixedClock(2026-10-23) | today と now が固定値 |

### UT-SVC サービス(一時ストア + FixedClock 2026-10-23)

| ID | 観点 | 期待結果 |
|---|---|---|
| UT-SVC-01 | カテゴリ削除:予算も一緒に消える | budgets.categories から削除される |
| UT-SVC-02 | カテゴリ削除:固定・使用中・存在しない | CATEGORY_FIXED / CATEGORY_IN_USE(params.count)/ CATEGORY_NOT_FOUND |
| UT-SVC-03 | 支出:存在しないカテゴリ | 400 VALIDATION_ERROR(category_id: UNKNOWN_CATEGORY)。保存されない |
| UT-SVC-04 | 支出一覧:月の指定なしは当月。並び順(日付の降順 → id の降順) | |
| UT-SVC-05 | サブスク編集:日付が同じなら anchor_day を維持 | 31 のまま |
| UT-SVC-06 | 更新済み:7日より先・停止中 | RENEW_TOO_EARLY / INACTIVE |
| UT-SVC-07 | 更新済み・再開で 2099-12-31 を超える | SUBSCRIPTION_DATE_LIMIT。保存されない |
| UT-SVC-08 | 状態遷移の違反(停止中を停止・有効を再開) | SUBSCRIPTION_STATE_CONFLICT |
| UT-SVC-09 | 予算:0 を null に正規化。同じカテゴリの重複・存在しないカテゴリ | 正規化される / DUPLICATED_CATEGORY / UNKNOWN_CATEGORY |
| UT-SVC-10 | CSV:全行が不正 | imported 0。ファイルの中身が変わらない |
| UT-SVC-11 | CSV:ヘッダーだけ・空白だけ・0バイト | CSV_EMPTY |
| UT-SVC-12 | CSV:5,000行(境界)/ 5,001行 | 成功 / CSV_TOO_MANY_ROWS(413) |
| UT-SVC-13 | CSV:解析できない(巨大な値) | CSV_PARSE_ERROR |
| UT-SVC-13b | CSV:ヘッダー不正・UTF-16 | CSV_HEADER_INVALID / CSV_ENCODING_UNSUPPORTED(BUG-001 を検出) |
| UT-SVC-14 | 集計:前月が 2000-01 より前 | previous_month None、previous_total 0 |

### UT-I18N 翻訳辞書(REQ-023)

| ID | 観点 | 期待結果 |
|---|---|---|
| UT-I18N-01 | en.json と ja.json のキーが一致する | 過不足なし |
| UT-I18N-02 | 値が空文字でない | すべて1文字以上 |
| UT-I18N-03 | バックエンドの全エラーコードに翻訳がある | `errors.<CODE>` がそろっている |
| UT-I18N-04 | CSV行エラーコードに翻訳がある | `csv.row.<CODE>` がそろっている |
| UT-I18N-05 | 固定カテゴリの翻訳がCSV照合の別名と一致する | en/ja の表示名が DATA-05 の別名に含まれる |
| UT-I18N-06 | 埋め込み変数({name} など)が en と ja で同じ | 片方だけにある変数がない |

---

## 3. テストケース(JavaScript)

| ID | 対象 | 観点 | 期待結果 |
|---|---|---|---|
| UT-JFMT-01 | formatMoney | en / ja / 負数 / 0 / null | ¥1,200 / 1,200円 / -¥1,200・-1,200円 / ¥0 / — |
| UT-JFMT-02 | formatSignedMoney | 正 / 0 / 負 | +¥1,200 / ¥0 / -¥1,200 |
| UT-JFMT-03 | formatDate | en / ja / 1桁の月日 / 不正な文字列 | Oct 23, 2026 / 2026年10月23日 / 2026年1月5日 / そのまま返す |
| UT-JFMT-04 | formatDate のタイムゾーン | TZ によらず同じ日 | 1日ずれない |
| UT-JFMT-05 | formatMonth | en / ja | Oct 2026 / 2026年10月 |
| UT-JFMT-06 | formatRate | "12.5" / "-6.3" / "0.0" / null | +12.5% / -6.3% / 0.0% / — |
| UT-JFMT-07 | formatPercent・formatNumber | 93 / null / 9999999(ja) | 93% / — / 9,999,999 |
| UT-JI18N-01 | resolveKey | 階層キー / 存在しない / 途中が文字列 | 値 / undefined / undefined |
| UT-JI18N-02 | interpolate | 埋め込み / 未指定の変数 / 0 | 置換 / そのまま残す / "0" |
| UT-JI18N-03 | translate のフォールバック | ja にない → en → キー文字列 | 順に解決 |
| UT-JI18N-04 | readStoredLang | ja / 不正値 / null / 例外 / storage なし | ja / en / en / en / en |
| UT-JI18N-05 | saveLang | 保存 / 例外を握りつぶす | 保存される / 例外が出ない |
| UT-JI18N-06 | loadDictionary | 成功 / !ok | JSON / 例外 |
| UT-JI18N-07 | collectKeys・hasKey | 入れ子の辞書 | ドット区切りの全キー / en へのフォールバック込みで判定 |
| UT-JCLI-01 | toApiError | 統一形式 / details なし / 形式違い / null | code / [] / UNKNOWN / UNKNOWN |
| UT-JCLI-02 | request 成功 | 200 JSON / 204 | 解析済み JSON / null |
| UT-JCLI-03 | request 失敗 | 統一エラー / JSONでない本文 | ApiError(code) / UNKNOWN |
| UT-JCLI-04 | 通信失敗 | fetch が例外 | ApiError(status 0, NETWORK_ERROR) |
| UT-JCLI-05 | 成功なのにJSONでない | | UNKNOWN |
| UT-JCLI-06 | 送信ヘッダー | post / postCsv / 本文なしの post | application/json / text/csv / 本文なし |
| UT-JCHT-01 | isAllZero | 全部0 / 1件だけ0以外 / 空 / undefined | T / F / T / T |
| UT-JCHT-02 | 円グラフ設定:ラベル | key あり → 翻訳、name → そのまま、other → category.others | |
| UT-JCHT-03 | 円グラフ設定:色 | other は灰色、9色目以降は先頭に戻る | |
| UT-JCHT-04 | 円グラフ設定:ツールチップ | "Food: ¥42,000 (37.3%)" | |
| UT-JCHT-05 | 棒グラフ設定 | 月ラベル・系列名・Y軸目盛り・ツールチップが整形関数を通る | |
| UT-JRTE-01 | parseHash | 定義済み / 末尾スラッシュ / 未定義 / 空 / undefined | 画面ID / 画面ID / dashboard ×3 |
| UT-JRTE-02 | startRouter | 不正なハッシュを置き換え、変更を通知する | replaceState と onChange が呼ばれる |
| UT-JSHR-01 | fieldErrorsFrom | VALIDATION_ERROR / 他のコード / 同じ項目に2件 | 項目ごとに最初の1件 / {} |
| UT-JSHR-02 | errorView・errorKey | params の取り出し / 辞書にないコード | errors.UNKNOWN |
| UT-JSHR-03 | fieldMessage | 数値は言語別に桁区切り、日付は言語別、未知コードは INVALID_VALUE | |
| UT-JSHR-04 | toNumberOrNull | "" / null / "12" / 12 / "abc" | null / null / 12 / 12 / "abc" |
| UT-JSHR-05 | categoryLabel | key あり / name / null | 翻訳 / name / "" |

## 4. 結果

最終的な結果は [test_report.md](./test_report.md)(工程4で作成)にまとめる。以下は工程3の時点の結果。

### 4.1 実行結果(2026-10-23)

| 区分 | コマンド | 件数 | 結果 |
|---|---|---|---|
| Python | `uv run pytest tests/unit --cov=app` | 251 | 全件成功 |
| JavaScript | `node --test "tests/js/*.test.mjs"` | 32 | 全件成功 |

- Python は parametrize の各ケースを1件として数える。
- 実行環境:Python 3.15.1、pytest 9.1.1、Node.js 24.7.0、macOS。

### 4.2 カバレッジ

| 対象 | 行カバレッジ | 分岐を含むカバレッジ | 備考 |
|---|---|---|---|
| `app/` 全体 | **91.4%**(1,510行中130行が未実行) | 91% | 目標80%以上を達成 |
| `app/domain/`(業務ルール) | 100% | 99% | |
| `app/schemas/`、`app/repositories/`、`app/clock.py` | 100% | 100% | |
| `app/services/` | 60〜98% | | 未実行の行は主に API 経由の正常系。工程4の IT で通す |
| `app/routers/`、`app/main.py`、`app/errors.py` の例外ハンドラ | 48〜87% | | HTTP 層は工程4の IT が対象 |
| `static/js/`(純粋関数のモジュール) | 99.7% | 96.8% | `node --test --experimental-test-coverage` で計測 |

### 4.3 検出した不具合

| ID | 内容 | 発見したテスト |
|---|---|---|
| BUG-001 | UTF-16 の CSV が CSV_ENCODING_UNSUPPORTED にならず、CSV_HEADER_INVALID になる | UT-SVC-13b |

詳細は [bug_reports.md](./bug_reports.md) を参照。修正後に UT-CSV-05 へ6ケースを追加し、再テストですべて成功した。
