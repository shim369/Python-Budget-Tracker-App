# 結合テスト仕様書(IT)

| 項目 | 内容 |
|---|---|
| 対象 | API(router → service → repository → JSON ファイル)と画面 |
| 自動テスト | `tests/integration/`(pytest + FastAPI TestClient)。`uv run pytest tests/integration` |
| 手動確認 | [it_manual.md](./it_manual.md)(MT-xx)。画面の見え方・グラフ・言語切替・オフライン |
| テストデータ | テストコードの中で生成する(CSV の文字コード違い・巨大ファイルを含む)。理由:Shift_JIS や UTF-16 のファイルは、リポジトリでレビューしにくいため |
| 共通の前提 | データファイルは pytest の `tmp_path` に作る(実データは使わない)。特に記載がなければ「今日」= 2026-10-23(FixedClock) |
| 合格基準 | 全ケース成功。不正な入力はすべて 4xx かつ統一エラー形式(NFR-002) |

## 1. 観点と対応

| 観点(依頼事項) | テストID | 種別 |
|---|---|---|
| 支出登録 → 月次集計 → 予算警告 | IT-FLOW-01〜04 | 自動 |
| サブスク登録 → 更新日通知 → 更新後の次回日付の再計算 | IT-SUB-01〜06 | 自動 |
| CSVインポート(正常、一部不正、全行不正、空、巨大、文字コード違い、重複) | IT-CSV-01〜12 | 自動 |
| 月またぎ(月末 23:59 / 翌月 0:00 の登録、月をまたぐ集計) | IT-MON-01〜04 | 自動 |
| カテゴリ削除と使用中データの整合性 | IT-CAT-01〜04 | 自動 |
| データファイルの破損・欠損時の起動と復旧 | IT-REC-01〜05 | 自動 + MT-05 |
| 同時リクエスト時の JSON ファイル書き込み競合 | IT-CON-01〜03 | 自動 |
| 言語切替後のエラー表示・日付・金額・グラフのラベル | IT-I18N-01〜02 + MT-02 | 自動 + 手動 |
| グラフ表示(0件、1件、大量カテゴリ、極端な金額) | IT-CHT-01〜04 + MT-03 | 自動 + 手動 |
| オフライン動作(CDN参照が残っていないこと) | IT-OFF-01〜03 + MT-04 | 自動 + 手動 |
| (追加)統一エラー形式・API仕様との一致 | IT-ERR-01〜05 | 自動 |
| (追加)基本の CRUD | IT-CRUD-01〜03 | 自動 |
| (追加)性能(NFR-001) | IT-PERF-01 | 自動 |

## 2. テストケース(自動)

### IT-FLOW 支出 → 集計 → 予算警告(REQ-001, 012, 013, 016, 017)

| ID | 前提 | 手順 | 期待結果 |
|---|---|---|---|
| IT-FLOW-01 | 空のデータ。全体予算 10,000、食費予算 5,000 を PUT | 食費 3,900 を登録 → GET /api/summary | 食費 78%(ok)、全体 39%(ok)。alerts は空 |
| IT-FLOW-02 | 01 の続き | 食費 100 を追加(合計 4,000)→ summary | 食費 80% caution。alerts に食費が1件 |
| IT-FLOW-03 | 02 の続き | 食費 1,000 を追加(合計 5,000)→ summary | 食費 100% は **caution のまま** |
| IT-FLOW-04 | 03 の続き | 食費 1 を追加(合計 5,001)→ 他カテゴリに 4,000 を追加 → summary | 食費 over。全体 90% caution。alerts は [食費 over, 全体 caution] の順。前月比は前月0円なので null |

### IT-SUB サブスクの更新(REQ-008〜011)

| ID | 前提 | 手順 | 期待結果 |
|---|---|---|---|
| IT-SUB-01 | today=2026-10-23 | 月次・次回 2026-10-31 を登録 → upcoming | 8日後なので対象外 |
| IT-SUB-02 | 01 の続き | 次回更新日を 2026-10-30 に編集 → upcoming | 対象(days_until=7)。anchor_day=30 |
| IT-SUB-03 | today=2027-01-30。月次・次回 2027-01-31 | renew → GET | 次回 2027-02-28、anchor_day=31。月次集計の monthly_total に入る |
| IT-SUB-04 | 03 の続き、today=2027-02-25 | renew | 2027-03-31(anchor により31日に戻る) |
| IT-SUB-05 | 年次・次回 2028-02-29、today=2028-02-25 | renew | 2029-02-28。月額換算 = 年額 // 12 |
| IT-SUB-06 | 停止 → today を2か月進める → 再開 | pause → resume | 再開後の次回更新日は今日以降。停止中は upcoming と monthly_total に入らない |

### IT-CSV CSVインポート(REQ-018, 019, NFR-002)

| ID | 入力 | 期待結果 |
|---|---|---|
| IT-CSV-01 | 正常3行(UTF-8)、列の順番を入れ替え、日本語カテゴリ、桁区切りの金額 | 200、imported 3。GET /api/expenses で3件 |
| IT-CSV-02 | 一部不正(5行中2行が不正) | 200、imported 3、errors に行番号とコード |
| IT-CSV-03 | 全行不正 | 200、imported 0。データファイルが変わらない |
| IT-CSV-04 | 空ファイル(0バイト)/ ヘッダーだけ | 400 CSV_EMPTY |
| IT-CSV-05 | 1MB を超える | 413 CSV_TOO_LARGE。1件も取り込まない |
| IT-CSV-06 | 5,001行(1MB 以内) | 413 CSV_TOO_MANY_ROWS(params.max=5000) |
| IT-CSV-07 | 5,000行(境界) | 200、imported 5000 |
| IT-CSV-08 | Shift_JIS(cp932)/ UTF-8 BOM付き | 200、encoding が shift_jis / utf-8-sig。日本語のメモが文字化けしない |
| IT-CSV-09 | UTF-16(BUG-001 の再テスト) | 400 CSV_ENCODING_UNSUPPORTED |
| IT-CSV-10 | ファイル内の重複 | 1件目を取り込み、2件目は DUPLICATE_IN_FILE |
| IT-CSV-11 | 同じファイルを2回取り込む | 2回目はすべて DUPLICATE_EXISTING、imported 0 |
| IT-CSV-12 | Content-Type が text/csv でない / ヘッダー不正 | 415 / 400 CSV_HEADER_INVALID(details に列名) |

### IT-MON 月またぎ(REQ-001, 004, 012, BR-02)

| ID | 前提 | 手順 | 期待結果 |
|---|---|---|---|
| IT-MON-01 | Clock = 2026-10-31 23:59:59 JST | GET /api/status → その today で支出を登録 → summary(月指定なし) | today=2026-10-31、当月 2026-10。10月に計上される |
| IT-MON-02 | Clock = 2026-11-01 00:00:00 JST | 同上 | today=2026-11-01、当月 2026-11。11月に計上され、10月の合計は変わらない |
| IT-MON-03 | サーバーが UTC で 2026-10-31 15:00 | GET /api/status | today=2026-11-01(JST で判定) |
| IT-MON-04 | 12/31 と 1/1 の支出 | 2027-01 の summary | 前月 2026-12 との前月比。trend が年をまたいで6か月分 |

### IT-CAT カテゴリ削除と整合性(REQ-005〜007)

| ID | 手順 | 期待結果 |
|---|---|---|
| IT-CAT-01 | ユーザーカテゴリを作成 → 支出2件で使用 → 削除 | 409 CATEGORY_IN_USE(count=2)。カテゴリと支出は残る |
| IT-CAT-02 | 01 の支出を2件とも別のカテゴリに変更 → 削除 | 204。カテゴリ予算も消える。GET /api/categories に出ない |
| IT-CAT-03 | 削除したカテゴリIDで支出を登録・予算を設定 | 400 VALIDATION_ERROR(UNKNOWN_CATEGORY) |
| IT-CAT-04 | 固定カテゴリを削除 / 固定カテゴリの別名と同じ名前で作成 | 409 CATEGORY_FIXED / 409 CATEGORY_NAME_DUPLICATED |

### IT-REC データファイルの破損・欠損(NFR-003, ERR-30)

| ID | 前提 | 手順 | 期待結果 |
|---|---|---|---|
| IT-REC-01 | ファイルなし | 起動 → status | 初期データで起動。data_recovered=false |
| IT-REC-02 | JSON の構文エラー | 起動 → status → 支出を登録 | 起動できる。data_recovered=true、backup_file が存在し中身が元のまま。登録も成功する |
| IT-REC-03 | 整合性違反(存在しないカテゴリへの参照) | 起動 | 02 と同じく退避して起動 |
| IT-REC-04 | 書き込み途中の .tmp が残っている | 起動 | .tmp が削除され、本体は残る |
| IT-REC-05 | 起動後に外部からファイルが壊された | 次の API 呼び出し | 退避して初期化し、200 を返す。status に反映される |

### IT-CON 同時書き込み(NFR-005, DATA-01)

| ID | 手順 | 期待結果 |
|---|---|---|
| IT-CON-01 | 50件の POST /api/expenses を16スレッドで同時に送る | 全件 201。IDが重複しない。ファイルに50件あり、JSON として正しい |
| IT-CON-02 | 支出の登録・予算の更新・カテゴリの追加を混ぜて同時に送る | 更新が失われない(各操作の結果がすべて残る) |
| IT-CON-03 | JsonStore.transaction を HTTP を通さず 8スレッド × 100回 | 採番(sequences.expense)が 800 になる |

### IT-I18N 言語に依存しない API(REQ-022)

| ID | 手順 | 期待結果 |
|---|---|---|
| IT-I18N-01 | Accept-Language: ja / en で同じ不正リクエストを送る | 応答が完全に一致する(エラーコードだけで、表示文言を含まない) |
| IT-I18N-02 | API が返しうるエラーコードと、カテゴリの key | すべて en.json / ja.json に翻訳がある |

### IT-CHT グラフ用データ(REQ-015)

| ID | データ | 期待結果 |
|---|---|---|
| IT-CHT-01 | 0件 | breakdown の items は空、total 0。trend は6件すべて0 |
| IT-CHT-02 | 1件 | items 1件、ratio "100.0" |
| IT-CHT-03 | ユーザーカテゴリを追加して10カテゴリに支出 | items 8件(上位7 + other)。other の key は category.others |
| IT-CHT-04 | 1円と 9,999,999円 × 3件 | 合計が正しい整数。1円の比率 "0.0" |

### IT-OFF オフライン動作(NFR-004)

| ID | 手順 | 期待結果 |
|---|---|---|
| IT-OFF-01 | index.html・JS・CSS・辞書に外部URL(http / https / //)の参照がないか検査 | 外部リソースの参照が0件(コメントと SVG 名前空間は除く) |
| IT-OFF-02 | index.html が参照する `/static/...` と、JS の import 先をすべて GET | すべて 200 |
| IT-OFF-03 | `/` と `/static/*` のキャッシュ制御(BUG-003 で追加) | `Cache-Control: no-cache`。If-None-Match で 304。API には付かない |

### IT-ERR 統一エラー形式と API 仕様(NFR-002, ERR-01〜03)

| ID | 手順 | 期待結果 |
|---|---|---|
| IT-ERR-01 | 未定義のパス / 許可されていないメソッド | 404 NOT_FOUND / 405 METHOD_NOT_ALLOWED(統一形式) |
| IT-ERR-02 | 壊れた JSON / 本文なし / 不正な month | 400 INVALID_JSON / 400 VALIDATION_ERROR |
| IT-ERR-03 | 想定外の例外(サービスが例外を送出) | 500 INTERNAL_ERROR。スタックトレースを含まない |
| IT-ERR-04 | 異常系の代表リクエスト一式 | 422 が1件もない。すべて統一形式 |
| IT-ERR-05 | /openapi.json | API-01〜24 の24本。422 の記載なし。ErrorResponse が登録されている |

### IT-CRUD 基本操作(REQ-002, 003, 008, 009)

| ID | 手順 | 期待結果 |
|---|---|---|
| IT-CRUD-01 | 支出の登録 → 取得 → 更新 → 削除 → 取得 | 201 → 200 → 200 → 204 → 404 |
| IT-CRUD-02 | サブスクの登録 → 一覧 → 更新 → 停止 → 一覧の並び → 削除 | active が先に並ぶ。削除後は 404 |
| IT-CRUD-03 | 存在しないIDへの更新・削除・状態変更 | 404(EXPENSE / SUBSCRIPTION / CATEGORY_NOT_FOUND) |

### IT-PERF 性能(NFR-001)

| ID | 前提 | 手順 | 期待結果 |
|---|---|---|---|
| IT-PERF-01 | 支出 5,000件(CSV で投入) | summary / breakdown / trend / expenses / upcoming をそれぞれ計測 | 各 500ms 以内 |

## 3. 結果

[test_report.md](./test_report.md) を参照。
