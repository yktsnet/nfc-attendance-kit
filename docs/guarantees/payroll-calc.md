# payroll-calc

## 時間と金額

| 保証 | 対応テスト |
|---|---|
| `build_daily_payroll_records` は IN と OUT の間の分数を `min_raw` に入れる | `test_in_out_60min`, `test_in_out_90min` |
| `build_daily_payroll_records` は `min_raw` を `ROUND_UNIT_MINUTES` 単位で切り捨てた値を `min` に入れる | `test_rounding_truncates_down` |
| `build_daily_payroll_records` は `ROUND_UNIT_MINUTES` が0なら5分単位で丸める | `test_round_unit_zero_defaults_to_5` |
| `build_daily_payroll_records` は `ROUND_UNIT_MINUTES` が負なら5分単位で丸める | `test_negative_round_unit_defaults_to_5` |
| `build_daily_payroll_records` は `min` に `HOURLY_YEN` を掛けた時給換算の額を `yen` に入れる | `test_in_out_60min`, `test_in_out_90min` |
| `build_daily_payroll_records` は日をまたいだ勤務の分数を IN 側の日付のレコードに入れる | `test_cross_day_flag` |

## 異常のフラグ

| 保証 | 対応テスト |
|---|---|
| `build_daily_payroll_records` は対応する IN の無い OUT の日付に `orphan_out` を立てる | `test_orphan_out` |
| `build_daily_payroll_records` は対応する IN の無い OUT の日付の `yen` を0にする | `test_orphan_out` |
| `build_daily_payroll_records` は従業員の設定ファイルが無ければ `missing_hourly_yen` を立てる | `test_missing_hourly_yen_flag` |
| `build_daily_payroll_records` は従業員の設定ファイルが無ければ `yen` を0にする | `test_missing_hourly_yen_flag` |
| `build_daily_payroll_records` は `HOURLY_YEN` が0以下なら `missing_hourly_yen` を立てる | `test_zero_hourly_yen_sets_missing_hourly_yen` |
| `build_daily_payroll_records` は `HOURLY_YEN` が0以下なら `yen` を0にする | `test_zero_hourly_yen_sets_missing_hourly_yen` |
| `build_daily_payroll_records` は OUT の無いままイベントが終わった IN の日付に `missing_out` を立てる | `test_missing_out_from_end_of_events` |
| `build_daily_payroll_records` は IN の後に ERROR が来たとき、IN の日付に `missing_out` を立てる | `test_missing_out_from_error_event` |
| `build_daily_payroll_records` は ERROR イベントの日付に `error:<code>` を立てる | `test_error_flag_recorded` |
| `build_daily_payroll_records` は `code` が空の ERROR イベントの日付に `error:error` を立てる | `test_error_without_code_records_error_error` |
| `build_daily_payroll_records` は閉じていない IN の後の IN の日付に `double_in` を立てる | `test_double_in_sets_double_in_flag_on_second_day`, `test_double_in_same_day` |
| `build_daily_payroll_records` は2回目の IN が来たとき、前の IN の日付に `missing_out` を立てる | `test_double_in_sets_missing_out_on_first_day`, `test_double_in_same_day` |
| `build_daily_payroll_records` は IN と OUT の日付が違うとき、IN 側の日付に `cross_day` を立てる | `test_cross_day_flag` |

## 対象のイベントと集計

| 保証 | 対応テスト |
|---|---|
| `build_daily_payroll_records` はイベントが無ければ空のリストを返す | `test_zero_min_no_record` |
| `build_daily_payroll_records` は日付と従業員の組ごとに1レコードを返す | `test_multiple_days` |
| `build_daily_payroll_records` は `emp` が `"unknown"` のイベントからレコードを作らない | `test_unknown_emp_excluded_from_records` |
| `build_daily_payroll_records` は `ts` を解釈できないイベントをレコードの計算に使わない | `test_unparseable_ts_excluded` |
| `summary["events"]` は `ts` を解釈できないものも含む入力イベントの総数である | `test_summary_counts`, `test_unparseable_ts_excluded` |
| `summary["events_unknown_emp"]` は `emp` が `"unknown"` のイベントの数である | `test_summary_counts`, `test_unknown_emp_excluded_from_records` |
| `summary["days_emps"]` は返したレコードの数である | `test_multiple_days` |
| `summary["flags_days"]` はフラグの付いたレコードの数である | `test_summary_flags_days_counts_flagged_records` |
| レコードの `id` は同じ日付と従業員の組なら同じ値になる | `test_same_date_emp_gives_same_id` |
| レコードの `id` は日付が違えば違う値になる | `test_different_date_gives_different_id` |
