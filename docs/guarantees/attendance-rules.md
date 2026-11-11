# attendance-rules

## 再タップの抑止

| 保証 | 対応テスト |
|---|---|
| `apply_rules` は同じ UID の直前のタップから5分未満のタップに空リストを返す | `test_tap_within_5min_ignored` |
| `apply_rules` は同じ UID の直前のタップから5分ちょうどのタップを処理する | `test_tap_at_exactly_5min_processed` |
| `apply_rules` は同じ UID の直前のタップから5分を超えたタップを処理する | `test_tap_after_5min_processed` |
| `apply_rules` の5分の抑止は UID ごとに独立し、別の UID のタップを妨げない | `test_debounce_is_per_uid` |

## IN・OUT の判定

| 保証 | 対応テスト |
|---|---|
| `apply_rules` は UID の初めてのタップに、渡した従業員 ID を `emp` に持つ IN イベントを返す | `test_first_tap_is_in` |
| `apply_rules` は IN 済みの UID の次のタップに OUT イベントを返す | `test_second_tap_is_out` |
| `apply_rules` は OUT 後の同じ日のタップに空リストを返す | `test_out_then_same_day_tap_ignored` |
| `apply_rules` は OUT 後の翌日のタップに IN イベントを返す | `test_out_then_next_day_tap_is_in` |
| `apply_rules` は `emp` が `"unknown"` のタップに、その UID に記録済みの従業員 ID を `emp` として使う | `test_unknown_emp_tap_uses_last_known_emp` |
| `apply_rules` は `emp` が `"unknown"` のタップで、状態に記録済みの従業員 ID を上書きしない | `test_unknown_emp_tap_does_not_overwrite_stored_emp` |

## 打刻漏れのエラー

| 保証 | 対応テスト |
|---|---|
| `apply_rules` は前日に IN したままの UID の翌日のタップに、`code="day_rollover"` の ERROR イベントと IN イベントを返す | `test_in_yesterday_tap_today_emits_error_then_in` |
| `apply_rules` が day_rollover で返すイベントは ERROR が IN より先に並ぶ | `test_day_rollover_order_error_before_in` |
| `apply_rules` は IN から15時間を超えたタップで `code="timeout_15h"` の ERROR イベントを返す | `test_in_then_16h_later_same_day_emits_timeout` |
| `apply_rules` は IN から14時間のタップで ERROR イベントを返さない | `test_in_then_14h_later_no_timeout` |
| `sweep_errors` は日をまたいで入場中の UID に `code="day_rollover"` の ERROR イベントを返す | `test_sweep_errors_day_rollover` |
| `sweep_errors` は IN から15時間を超えて入場中の UID に `code="timeout_15h"` の ERROR イベントを返す | `test_sweep_errors_timeout` |
| `sweep_errors` が day_rollover を返した UID の次のタップは IN になる | `test_sweep_errors_after_rollover_uid_is_outside` |
| `sweep_errors` は入場中でない UID にエラーを返さない | `test_not_inside_no_error` |
| `sweep_errors` は空の状態に空リストを返す | `test_empty_state_no_error` |
| `sweep_errors` は複数の UID のうち入場中の UID だけにエラーを返す | `test_multiple_uids_only_inside_flagged` |

## イベントの形と状態の復元

| 保証 | 対応テスト |
|---|---|
| `apply_rules` が返すイベントは `id`・`ts`・`uid`・`emp`・`act` を持つ | `test_event_has_required_fields` |
| ERROR イベントは `code` を持つ | `test_error_event_has_code` |
| ERROR 以外のイベントは `code` を持たない | `test_non_error_event_has_no_code` |
| `State.from_current_month` は今月 IN だけの UID を、従業員 ID ごと入場中として復元する | `test_restores_inside_state_and_emp` |
| `State.from_current_month` は今日 OUT 済みの UID を、同じ日の再タップを無視する状態として復元する | `test_restores_done_day_after_out` |
| `State.from_current_month` はイベントが無ければ空の状態を返す | `test_no_events_restores_empty_state` |
| `State.from_current_month` は先月のイベントを読まない | `test_reads_only_current_month` |
