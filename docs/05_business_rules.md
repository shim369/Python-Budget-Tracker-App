# 05. 業務ルール設計(最重要)

本書の規則は、すべて `app/domain/` の**純粋関数**として実装する(I/Oなし、「今日」は引数で受け取る)。
フロントエンドでは計算しない(NFR-007)。関数名は実装時の予定名。

| ID | ルール | 実装モジュール |
|---|---|---|
| BR-01 | 金額の扱い | `app/domain/money.py` |
| BR-02 | 月の境界・タイムゾーン・「今日」 | `app/domain/period.py`, `app/clock.py` |
| BR-03 | サブスク次回更新日の計算 | `app/domain/renewal.py` |
| BR-04 | サブスクの月額換算・更新予定の抽出 | `app/domain/renewal.py`, `app/domain/money.py` |
| BR-05 | 予算判定 | `app/domain/budget_rule.py` |
| BR-06 | 前月比 | `app/domain/summary.py` |
| BR-07 | 集計(カテゴリ別・グラフ用データ) | `app/domain/summary.py` |

---

## BR-01 金額の扱い

### BR-01-1 型と範囲

| 対象 | 型 | 下限 | 上限 | 備考 |
|---|---|---|---|---|
| 支出金額 | int | 1 | 9,999,999 | 0円・負数は不可(返金は対象外) |
| サブスク金額 | int | 1 | 9,999,999 | 周期あたりの金額(年次なら年額) |
| 予算(全体・カテゴリ) | int または null | 0 | 99,999,999 | 0 と null はどちらも「未設定」。保存時に null へ正規化する |
| 集計値 | int(Pythonのint) | - | 上限なし | 最大でも 5,000件×9,999,999 ≒ 5×10^10 で、JSの安全な整数(2^53)に収まる |

- **なぜ整数か**:JPYは小数点以下がないため。最小単位(1円)の整数で持てば、浮動小数点の誤差が起こらない。
- APIの入力は **StrictInt**(Pydantic)で受ける。`1200.0`・`"1200"`・`true` はすべて 400(INVALID_TYPE)。
  - 理由:型をあいまいに受け入れると、フロントの不具合を見逃すため。

### BR-01-2 丸めルール

金額の除算が発生するのは次の1か所だけ。率(%)の計算は BR-05・BR-06 で定義する。

| 計算 | 規則 | 例 |
|---|---|---|
| 年次サブスクの月額換算 | `amount // 12`(切り捨て) | 12,000 → 1,000 / 1,490 → 124 / 11 → 0 |

- **なぜ切り捨てか**:Pythonの整数除算と一致し、実装が単純になるため。また、端数で合計が実際の支払額を上回ることがない。

### BR-01-3 CSVの金額文字列(CSV-04 から利用)

```
parse_csv_amount(text) -> int | エラーコード
  s = text の前後の空白を除去
  s が空                      → AMOUNT_REQUIRED
  s が ^[0-9]{1,3}(,[0-9]{3})*$ または ^[0-9]+$ に一致しない → INVALID_AMOUNT
  n = int(s からカンマを除去)
  n < 1 または n > 9,999,999  → AMOUNT_OUT_OF_RANGE
  return n
```

- 小数点・符号・通貨記号("¥"、"円")は受け付けない(INVALID_AMOUNT)。
  - 理由:"1.5" を 1 や 2 に解釈するような推測をしないため。

---

## BR-02 月の境界・タイムゾーン・「今日」

| 項目 | 規則 |
|---|---|
| タイムゾーン | Asia/Tokyo 固定(`zoneinfo.ZoneInfo("Asia/Tokyo")`) |
| 今日 | `Clock.today()` = 現在時刻をJSTに変換したときの日付。サービス層は Clock を DI で受け取る |
| 支出の日付 | 暦日(`date`、時刻なし)。範囲は 2000-01-01〜2099-12-31 |
| 月の表現 | `"YYYY-MM"`(例:`"2026-10"`)。範囲は 2000-01〜2099-12 |
| 月への帰属 | 支出は `(date.year, date.month)` が一致する月に属する |
| 月の範囲 | 1日 〜 末日(`calendar.monthrange` で求める。2月はうるう年を考慮) |
| 当月 | `Clock.today()` が属する月 |
| 前月 | 1月の前月は前年12月(`2026-01` → `2025-12`) |

### 「月末23:59」と「翌月0:00」の扱い

支出は日付だけを持つため、時刻の影響を受けるのは「今日」と「当月」の判定だけである。

| 現在時刻(JST) | Clock.today() | 当月 | 支出フォームの日付の初期値 |
|---|---|---|---|
| 2026-10-31 23:59:59 | 2026-10-31 | 2026-10 | 2026-10-31 |
| 2026-11-01 00:00:00 | 2026-11-01 | 2026-11 | 2026-11-01 |
| 2026-10-31 15:00:00 UTC | 2026-11-01 | 2026-11 | 2026-11-01 |

- 3行目のように、サーバのOSタイムゾーンがUTCでも、日付はJSTで判定する。
- フロントは日付の初期値をブラウザの時計から作らず、`GET /api/status` の `today` を使う。
  - 理由:日付の判定をサーバ側の1か所に集約するため。

```
parse_month("YYYY-MM") -> (year, month) | INVALID_MONTH   # 正規表現 ^\d{4}-\d{2}$ と範囲で検証する
month_of(d: date) -> "YYYY-MM"
month_range(ym) -> (first_day, last_day)
previous_month(ym) -> ym'                                # 範囲外(1999-12)になる場合は None
next_month(ym) -> ym'                                    # 範囲外(2100-01)になる場合は None
last_n_months(ym, n) -> [ym_(n-1)前, ..., ym]            # 古い順
```

---

## BR-03 サブスク次回更新日の計算

### 保持する項目

| 項目 | 意味 |
|---|---|
| `next_renewal_date` | 次回の更新日 |
| `anchor_day` | 本来の更新日(1〜31)。例:「毎月31日」 |
| `anchor_month` | 年次の更新月(1〜12)。月次では null |

- **なぜ anchor を持つか**:結果の日付だけを持つと、1/31 → 2/28 → 3/28 のように日付がずれていくため。
  anchor を持てば、正しく 3/31 に戻せる。

### anchor の設定タイミング

| 操作 | anchor_day / anchor_month |
|---|---|
| 登録 | `next_renewal_date` の日・月から設定する |
| 編集で `next_renewal_date` を変えた | 新しい日付の日・月から設定し直す |
| 編集で `next_renewal_date` を変えていない | 維持する(ただし周期を年次に変えたら `anchor_month = next_renewal_date.month`、月次に変えたら null) |
| 更新済み・再開 | 維持する |

### 計算式

```
last_day(y, m) = calendar.monthrange(y, m)[1]

advance(current: date, cycle, anchor_day, anchor_month) -> date
  if cycle == "monthly":
      (y, m) = current の翌月          # 12月 → 翌年1月
  else:  # "yearly"
      (y, m) = (current.year + 1, anchor_month)
  return date(y, m, min(anchor_day, last_day(y, m)))
```

### 具体例(境界値)

| No | 周期 | anchor | current | advance の結果 | 観点 |
|---|---|---|---|---|---|
| 1 | 月次 | 15 | 2026-10-15 | 2026-11-15 | 通常 |
| 2 | 月次 | 31 | 2026-12-31 | 2027-01-31 | 年またぎ |
| 3 | 月次 | 31 | 2027-01-31 | 2027-02-28 | 31日 → 平年2月 |
| 4 | 月次 | 31 | 2027-02-28 | 2027-03-31 | anchor で31日に戻る |
| 5 | 月次 | 31 | 2028-01-31 | 2028-02-29 | 31日 → うるう年2月 |
| 6 | 月次 | 31 | 2026-03-31 | 2026-04-30 | 31日 → 30日の月 |
| 7 | 月次 | 30 | 2027-01-30 | 2027-02-28 | 30日 → 2月 |
| 8 | 月次 | 29 | 2028-01-29 | 2028-02-29 | 29日 → うるう年2月 |
| 9 | 年次 | 2/29 | 2028-02-29 | 2029-02-28 | うるう日 → 平年 |
| 10 | 年次 | 2/29 | 2031-02-28 | 2032-02-29 | anchor でうるう日に戻る |
| 11 | 年次 | 10/23 | 2026-10-23 | 2027-10-23 | 通常 |

- 年次サブスクの anchor は (anchor_month, anchor_day) の組。No.9・10 は anchor_month=2, anchor_day=29。

### 「更新済み」操作(API-17)

```
renew(sub, today):
  if sub.status != "active":                 → 409 SUBSCRIPTION_INACTIVE
  if sub.next_renewal_date > today + 7日:    → 409 SUBSCRIPTION_RENEW_TOO_EARLY
  sub.next_renewal_date = advance(sub.next_renewal_date, ...)   # 1回の操作で1周期だけ進める
```

- 計算結果が 2099-12-31 を超える場合は 409 SUBSCRIPTION_DATE_LIMIT とし、保存しない(再開時の繰り越しも同じ。工程2で追加)。
- **なぜ7日の制限を設けるか**:誤操作で1周期先へ進めてしまうことを防ぐため。7日は通知の範囲(BR-04)と同じにしている。
- **なぜ1周期ずつか**:複数周期を過ぎていても、1回の支払いを1回の操作で確認できるようにするため。

### 再開操作(API-16)

```
resume(sub, today):
  if sub.status != "paused": → 409 SUBSCRIPTION_STATE_CONFLICT
  sub.status = "active"
  while sub.next_renewal_date < today:       # 停止中に過ぎた周期は課金されていないため飛ばす
      sub.next_renewal_date = advance(...)
```

| 例 | 次回更新日 | today | 再開後 |
|---|---|---|---|
| a | 2026-08-31(月次, anchor 31) | 2026-10-23 | 2026-10-31 |
| b | 2026-10-23 | 2026-10-23 | 2026-10-23(当日は過去扱いにしない) |
| c | 2026-12-01 | 2026-10-23 | 2026-12-01(変更なし) |

---

## BR-04 サブスクの月額換算・更新予定の抽出

### BR-04-1 月額換算

| 周期 | 月額換算 |
|---|---|
| monthly | amount |
| yearly | amount // 12(BR-01-2) |

- 月次集計のサブスク合計は、**有効(active)なサブスクの月額換算の合計**とする。
- 停止中のサブスクは含めない。
- サブスクは変更履歴を持たないため、過去の月を表示しても「現在の登録内容」で計算する。これは既知の制約で、拡張案 X-03 で扱う。
- サブスクは支出として自動計上せず、予算判定にも含めない(AD-07)。

### BR-04-2 更新予定(通知)の抽出

```
upcoming(subs, today, window=7):
  対象 = status == "active" かつ next_renewal_date <= today + window
  各要素に days_until = (next_renewal_date - today).days を付ける   # 負なら超過
  is_overdue = days_until < 0
  並び順:next_renewal_date の昇順 → id の昇順
```

| next_renewal_date(today=2026-10-23) | days_until | 表示 |
|---|---|---|
| 2026-10-20 | -3 | 対象(超過) |
| 2026-10-23 | 0 | 対象(今日) |
| 2026-10-30 | 7 | 対象(境界:含む) |
| 2026-10-31 | 8 | 対象外 |

---

## BR-05 予算判定

### 判定規則

使用率 r = spent / budget として次のように判定する。浮動小数点を避けるため、整数のまま比較する。

| status | 条件(整数比較) | 意味 |
|---|---|---|
| `none` | budget が null または 0 | 未設定。判定しない |
| `ok` | spent × 100 < budget × 80 | 80%未満 |
| `caution` | budget × 80 ≤ spent × 100 かつ spent ≤ budget | 80%以上100%以下(**ちょうど100%は caution**) |
| `over` | spent > budget | 100%超 |

- **ちょうど100%を over にしない理由**:基本設計の「100%**超**で警告」に従うため。予算をちょうど使い切った状態は超過ではない。

### 表示用の使用率

```
usage_percent = (spent * 100) // budget     # 切り捨ての整数。budget 未設定なら null
```

- status は必ず上の整数比較で決め、usage_percent からは**決めない**。
- そのため 100.01% は表示が「100%」でも status は `over` になる。
  - 理由:表示用の丸めが判定に影響しないようにするため。画面では status に応じて色と文言を変えるので、利用者が誤解しない。

### 境界値の例(budget = 10,000)

| spent | 比率 | usage_percent | status |
|---|---|---|---|
| 0 | 0% | 0 | ok |
| 7,900 | 79% | 79 | ok |
| 7,999 | 79.99% | 79 | ok |
| 8,000 | 80% | 80 | caution |
| 9,900 | 99% | 99 | caution |
| 10,000 | 100% | 100 | caution |
| 10,001 | 100.01% | 100 | over |
| 10,100 | 101% | 101 | over |

### 判定の単位

| 対象 | spent |
|---|---|
| 全体予算 | 対象月の全支出の合計 |
| カテゴリ予算 | 対象月の、そのカテゴリの支出合計 |

アラート(ダッシュボードの警告一覧)には status が `caution` または `over` の判定を並べる。
順序は `over` を先にし、同じ status の中では全体 → カテゴリ(カテゴリは使用率の降順)とする。

---

## BR-06 前月比

```
change_amount = current - previous                     # 整数。負もあり得る
change_rate:
  previous == 0 → null                                 # 0除算を避ける。画面では「—」と表示する
  それ以外      → Decimal(current - previous) * 100 / Decimal(previous)
                  を小数第1位で四捨五入(ROUND_HALF_UP)し、文字列で返す
```

| previous | current | change_amount | change_rate |
|---|---|---|---|
| 10,000 | 11,250 | 1,250 | "12.5" |
| 10,000 | 10,000 | 0 | "0.0" |
| 10,000 | 0 | -10,000 | "-100.0" |
| 0 | 5,000 | 5,000 | null |
| 0 | 0 | 0 | null |
| 3 | 4 | 1 | "33.3" |
| 3 | 5 | 2 | "66.7" |
| 8 | 9 | 1 | "12.5"(12.5 ちょうどで丸めない) |
| 16 | 17 | 1 | "6.3"(6.25 → 四捨五入) |
| 16 | 15 | -1 | "-6.3"(-6.25 → 絶対値を四捨五入) |

- **なぜ文字列か**:Pydantic v2 は Decimal を JSON で文字列として出力する。数値で返すと JS 側で浮動小数点になり、表示が "12.499999" のように崩れるおそれがある。
- **前月0円で null を返す理由**:「∞%」や「100%」と表示すると誤解を招くため。差額だけを示す。

---

## BR-07 集計(カテゴリ別・グラフ用データ)

### BR-07-1 カテゴリ別集計(サマリー用)

```
summarize(expenses, categories, budgets, ym):
  cur  = ym の支出をカテゴリ別に合計
  prev = 前月の支出をカテゴリ別に合計
  対象カテゴリ = cur > 0 または prev > 0 または カテゴリ予算が設定されている
  各カテゴリに total, previous_total, change_amount, change_rate(BR-06),
            budget, usage_percent, status(BR-05) を付ける
  並び順:total の降順 → category_id の昇順
```

### BR-07-2 円グラフ用データ(category-breakdown)

```
breakdown(expenses, ym, max_slices=8):
  items = ym の、合計 > 0 のカテゴリを (amount 降順, category_id 昇順) で並べる
  if len(items) > max_slices:
      items = 上位7件 + {kind: "other", label_key: "category.others", amount: 残りの合計}
  ratio_percent = 各 amount / 月合計 × 100 を小数第1位で四捨五入(ROUND_HALF_UP)した文字列
```

- 0件のとき `items = []`、`total = 0`。フロントは「データなし」を表示する(SCR-01)。
- 各 ratio_percent は個別に丸めるため、合計が 100.0 にならない場合がある。これは仕様とする。
  - 理由:最大剰余法などで合計を合わせると、規則が複雑になり検証もしにくいため。

| 件数 | 結果 |
|---|---|
| 0 | items 0件 |
| 1 | 1件、ratio "100.0" |
| 8 | 8件(集約なし:境界) |
| 9 | 上位7件 + その他(2件分) |

### BR-07-3 棒グラフ用データ(monthly-trend)

```
trend(expenses, end_ym, n=6):
  months = last_n_months(end_ym, 6)        # 古い順
  items = [{month, total}] (支出がない月も total=0 で含める)
```

- 6か月すべてが0円の場合も items は6件返す。「データなし」を表示するかどうかはフロントが判断する(SCR-01)。

---

## 将来の拡張案(本工程では実装しない)

- X-01:支出のマイナス(返金)の登録
- X-02:月ごとに異なる予算
- X-03:サブスクの価格改定履歴と支払実績の保持
