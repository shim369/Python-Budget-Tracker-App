# 06. CSVインポート設計

| ID | 内容 |
|---|---|
| CSV-01 | 想定フォーマット・列定義 |
| CSV-02 | 文字コードの判定 |
| CSV-03 | ファイル全体の検証(取り込み前) |
| CSV-04 | 行の検証 |
| CSV-05 | 重複行の判定 |
| CSV-06 | 不正行の扱いと保存方針 |
| CSV-07 | 結果レポート |

実装は `app/domain/csv_rules.py`(純粋関数)と `app/services/import_service.py`(処理の流れと保存)。

---

## CSV-01 想定フォーマット・列定義

```csv
date,amount,category,memo
2026-10-01,1200,food,Lunch
2026/10/02,"3,980",日用品,Detergent
2026/10/3,8800,Pets,
```

| 項目 | 仕様 |
|---|---|
| 区切り文字 | カンマ |
| 囲み文字 | ダブルクォート(RFC 4180。`""` はエスケープ。値の中のカンマも可) |
| 改行 | LF / CRLF の両方を受け付ける |
| 1行目 | ヘッダー行(必須) |
| 空行 | 無視する(行数に数えない) |

### 列定義

| 列名 | 必須列 | 値の必須 | 形式 | 例 |
|---|---|---|---|---|
| date | ○ | ○ | `YYYY-MM-DD` または `YYYY/MM/DD`。月・日はゼロ埋めなしも可 | 2026-10-01, 2026/10/3 |
| amount | ○ | ○ | 整数。3桁ごとのカンマ可(BR-01-3) | 1200, "3,980" |
| category | ○ | ○ | 固定カテゴリの別名、またはユーザーカテゴリ名(DATA-05) | food, 食費, Pets |
| memo | | | 0〜100文字 | Lunch |

- ヘッダーは列名の前後空白を除き、大文字小文字を区別せずに照合する。
- 列の順番は自由。例:`amount,date,memo,category` も可。
- 理由:表計算ソフトで列を並べ替えてもエラーにしないため。
- `memo` 列はなくてもよい。その場合は全行が空文字になる。
- 未定義の列があれば、ヘッダーエラーにする。
  - 理由:`amonut` のようなタイプミスに気づけるようにするため。

## CSV-02 文字コードの判定

```
decode(raw: bytes) -> (text, encoding) | CSV_ENCODING_UNSUPPORTED
  if raw が FF FE / FE FF で始まる、または NUL(00)を含む:  → CSV_ENCODING_UNSUPPORTED   # UTF-16/32(BUG-001で追加)
  if raw が EF BB BF で始まる:  return raw[3:].decode("utf-8"), "utf-8-sig"    # 失敗したらエラー
  try: return raw.decode("utf-8"), "utf-8"
  try: return raw.decode("cp932"), "shift_jis"
  → 400 CSV_ENCODING_UNSUPPORTED
```

| 入力 | 判定結果 |
|---|---|
| UTF-8(BOMなし) | utf-8 |
| UTF-8(BOM付き。Excelの「CSV UTF-8」) | utf-8-sig(BOMは取り除く) |
| Shift_JIS(Excelの「CSV」) | shift_jis(cp932として解釈) |
| ASCIIのみ | utf-8(どちらで読んでも同じ結果になる) |
| UTF-16 など | CSV_ENCODING_UNSUPPORTED |

- **UTF-8 を先に試す理由**:UTF-8 は規則が厳しいため、Shift_JIS の日本語がたまたま有効な UTF-8 として読める確率は実用上ほぼない。
  逆の順にすると、UTF-8 の文字列が Shift_JIS として誤って読めてしまう場合がある。
- **cp932 を使う理由**:Windows版 Excel の出力に含まれる機種依存文字(①、髙 など)も読めるため。
- 判定結果はレポートの `encoding` に入れる。文字化けが起きたとき、利用者が原因に気づけるようにするため。

## CSV-03 ファイル全体の検証(取り込み前)

上から順に確認し、1つでも該当したら**1行も取り込まずに**エラーを返す。

| 順 | 条件 | ステータス | エラーコード |
|---|---|---|---|
| 1 | Content-Type が text/csv 以外 | 415 | CSV_UNSUPPORTED_MEDIA_TYPE |
| 2 | 本文が 1,048,576 バイト(1MB)を超える | 413 | CSV_TOO_LARGE |
| 3 | 本文が0バイト | 400 | CSV_EMPTY |
| 4 | 文字コードを判定できない | 400 | CSV_ENCODING_UNSUPPORTED |
| 5 | 空白・空行しかない | 400 | CSV_EMPTY |
| 5a | CSVとして解析できない(1つの値が csv.field_size_limit=131,072文字を超えるなど) | 400 | CSV_PARSE_ERROR(params.line に行番号)※工程2で追加 |
| 6 | ヘッダーに必須列がない・未定義の列がある・同じ列名が重複している | 400 | CSV_HEADER_INVALID(details[].field に列名、details[].code に MISSING_COLUMN / UNKNOWN_COLUMN / DUPLICATE_COLUMN) |
| 7 | データ行(空行を除く)が0件 | 400 | CSV_EMPTY |
| 8 | データ行が 5,000 行を超える | 413 | CSV_TOO_MANY_ROWS(params.max=5000) |

- 条件2は、本文を読み込むときに上限+1バイトで打ち切って判定する。巨大な本文をすべてメモリに載せないため。
- 条件8は、全行を数えてから判定する。
  - 理由:途中まで取り込むと「どこまで入ったか」が分かりにくくなるため。上限内に分割して送ってもらう方針とする。

## CSV-04 行の検証

各データ行を、次の順に検証する。**最初に見つかったエラーだけを報告する**(1行につき1件)。

| 順 | 検証 | エラーコード | field |
|---|---|---|---|
| 1 | 列数がヘッダーと一致する | COLUMN_COUNT_MISMATCH | null |
| 2 | date が空でない | DATE_REQUIRED | date |
| 3 | date を形式どおりに解釈できる(存在しない日付 2026-02-30 も含む) | INVALID_DATE | date |
| 4 | date が 2000-01-01〜2099-12-31 | DATE_OUT_OF_RANGE | date |
| 5 | amount が空でない | AMOUNT_REQUIRED | amount |
| 6 | amount の形式(BR-01-3) | INVALID_AMOUNT | amount |
| 7 | amount が 1〜9,999,999 | AMOUNT_OUT_OF_RANGE | amount |
| 8 | category が空でない | CATEGORY_REQUIRED | category |
| 9 | category が既存のカテゴリに一致する | UNKNOWN_CATEGORY | category |
| 10 | memo が100文字以内 | MEMO_TOO_LONG | memo |
| 11 | ファイル内の重複(CSV-05) | DUPLICATE_IN_FILE | null |
| 12 | 既存データとの重複(CSV-05) | DUPLICATE_EXISTING | null |

- **なぜ最初のエラーだけか**:利用者は1つ直して再度取り込むことが多く、レポートを短く読みやすく保てるため。
  検証順も決まるので、テストの期待値を一意に書ける。
- 値は前後の空白を除いてから検証する。
- 未知のカテゴリを自動作成はしない。
  - 理由:誤字のカテゴリ(`fodo` など)が増え続けるのを防ぐため。拡張案 X-04 で扱う。

```
validate_row(cells: dict[str,str], resolver) -> ValidRow | RowError
  ...上の表の 1〜10 の順に判定する...
  return ValidRow(date, amount, category_id, memo)
```

- `resolver` は「名前 → category_id」の対応表。DATA-05 の別名とユーザーカテゴリ名を、小文字にして登録しておく。
- 関数に対応表を引数で渡すことで、`validate_row` をI/Oのない純粋関数にできる。

## CSV-05 重複行の判定

```
key(row) = (date, amount, category_id, memo)      # 検証・正規化した後の値で比較する
```

| 状況 | 扱い |
|---|---|
| ファイル内で同じ key が2回以上ある | 最初の正常な行を取り込み、2回目以降は DUPLICATE_IN_FILE |
| 既存の支出に同じ key がある | DUPLICATE_EXISTING |
| 同じ行が両方に該当する | DUPLICATE_EXISTING を優先する |

- 正規化してから比較するので、`2026/10/1` と `2026-10-01`、`1,200` と `1200`、`食費` と `food` は同じ値として扱う。
- 制約:同じ日に同じ店で同額・同メモの支出が実際に2件ある場合も、重複として扱われる。
  その場合は画面から手動で登録してもらう(画面の登録では重複チェックをしない)。
  - 理由:二重取り込みを防ぐ利点のほうが大きいため。

## CSV-06 不正行の扱いと保存方針

| 方針 | 内容 |
|---|---|
| 不正行・重複行 | スキップしてレポートに載せる(処理は中断しない) |
| ファイル全体のエラー | 中断し、1行も取り込まない(CSV-03) |
| 保存 | 正常な行を1回の書き込みでまとめて保存する(ロック内で採番 → 追加 → 原子的に書き込み) |
| 保存失敗 | 500 STORAGE_WRITE_FAILED。元のファイルは残っているので、1行も取り込まれていない状態になる |
| 全行が不正 | 200 を返し、imported_count=0。ファイルは更新しない |

- **全行が不正でも200にする理由**:リクエスト自体は正しく処理され、「0件取り込めた」という業務上の結果を返しているため。
  この結果をエラーとして扱うかどうかは画面側の表示で区別する(SCR-05)。

## CSV-07 結果レポート

形式は API-24(03_api_design.md 4.10)を参照。

| 項目 | 説明 |
|---|---|
| encoding | `utf-8` / `utf-8-sig` / `shift_jis` |
| total_rows | 空行を除いたデータ行の数 |
| imported_count | 取り込んだ件数 |
| error_count | 検証エラーの件数(CSV-04 の1〜10) |
| duplicate_count | 重複の件数(CSV-04 の11〜12) |
| errors[] | エラー行と重複行の一覧。line の昇順 |
| errors[].line | ファイル上の行番号(ヘッダーが1行目。引用符内の改行を含む行は、その行が終わる行の番号) |
| errors[].field | エラーになった列名、または null |
| errors[].code | 行エラーコード |
| errors[].value | 問題の値(50文字で切り詰める)、または null |

### 行エラーコードと表示例(翻訳は `csv.row.<CODE>`)

| コード | 英語の表示例 | 日本語の表示例 |
|---|---|---|
| COLUMN_COUNT_MISMATCH | Column count does not match the header | 列数がヘッダーと一致しません |
| DATE_REQUIRED | Date is required | 日付が空です |
| INVALID_DATE | Invalid date | 日付の形式が正しくありません |
| DATE_OUT_OF_RANGE | Date must be between 2000 and 2099 | 日付は2000年〜2099年の範囲で指定してください |
| AMOUNT_REQUIRED | Amount is required | 金額が空です |
| INVALID_AMOUNT | Amount must be a whole number | 金額は整数で指定してください |
| AMOUNT_OUT_OF_RANGE | Amount must be 1 to 9,999,999 | 金額は1〜9,999,999の範囲で指定してください |
| CATEGORY_REQUIRED | Category is required | カテゴリが空です |
| UNKNOWN_CATEGORY | Unknown category | 存在しないカテゴリです |
| MEMO_TOO_LONG | Memo is too long (max 100) | メモは100文字以内にしてください |
| DUPLICATE_IN_FILE | Duplicate row in the file | ファイル内で重複しています |
| DUPLICATE_EXISTING | Already registered | 登録済みのデータと重複しています |

---

## 将来の拡張案

- X-04:未知のカテゴリを自動作成するオプション
- X-05:取り込み前のプレビュー(dry-run)
- X-06:支出データのCSVエクスポート
