# Guarantee Ledger

## Guarantees

### 1. `tests/test_payroll_calc.py` — lib/payroll_calc.py (build_daily_payroll_records)

- IN→OUT のペアから経過分数（`min_raw`）を計算し、`ROUND_UNIT_MINUTES` 単位で切り捨てた `min` と、`min * HOURLY_YEN // 60` の `yen` を算出する。
- 丸め単位は `config/employees/<emp>.env` の `ROUND_UNIT_MINUTES` に従い、切り捨てで丸める（例: 67分 → 65分）。
- `ROUND_UNIT_MINUTES` が0以下に設定されている場合は5分をデフォルトとして使う。
- イベントが1件も無い場合、レコードは1件も生成されない（空配列）。
- 従業員設定ファイルが存在しない、または `HOURLY_YEN` が未設定・0以下の場合、`missing_hourly_yen` フラグが立ち `yen` は0になる。
- OUTに対応するINが無い場合は `orphan_out` フラグが立ち、`yen` は0になる。
- INのままイベント列が終了した場合、または直後にERRORイベントが来た場合、そのINの日付に `missing_out` フラグが立つ。
- ERRORイベントが来ると、そのイベントの日付に `error:<code>` フラグが記録される（`code` が空なら `error:error`）。
- 同一従業員に対して未クローズのINがある状態で2回目のINが来ると、当日側に `double_in`、前回INの日付側に `missing_out` が記録される（同日内の連続INも同様）。
- IN側の日付とOUT側の日付が異なる場合、その日（IN側の日付）に `cross_day` フラグが立ち、稼働時間はIN側の日付に加算される。
- `emp` が `"unknown"` のイベントはレコード生成対象から除外され、`summary["events_unknown_emp"]` でカウントされる。
- `ts` がISO形式としてパースできないイベントは処理から除外される（`summary["events"]` の総数には含まれるが、レコード生成・他の集計には反映されない）。
- `summary` は `events`（入力イベント総数）・`events_unknown_emp`・`days_emps`（生成されたレコード数）・`flags_days`（フラグ付きレコード数）を含む。
- レコードの `id` は日付と従業員から決定論的に生成され、同じ日付・従業員の組なら同じ `id`、異なれば異なる `id` になる。

| 保証（要約） | 対応テスト |
|---|---|
| 稼働時間・給与額の算出 | `test_in_out_60min`, `test_in_out_90min` |
| 丸め単位での切り捨て | `test_rounding_truncates_down` |
| ROUND_UNIT=0 は5分扱い | `test_round_unit_zero_defaults_to_5` |
| イベント無しはレコード無し | `test_zero_min_no_record` |
| 時給未設定フラグ | `test_missing_hourly_yen_flag` |
| orphan_out フラグ | `test_orphan_out` |
| missing_out フラグ（末尾/ERROR起因） | `test_missing_out_from_end_of_events`, `test_missing_out_from_error_event` |
| error:<code> フラグ | `test_error_flag_recorded` |
| double_in / missing_out の付与先 | `test_double_in_sets_double_in_flag_on_second_day`, `test_double_in_sets_missing_out_on_first_day`, `test_double_in_same_day` |
| cross_day フラグと加算先日付 | `test_cross_day_flag` |
| unknown emp の除外 | `test_unknown_emp_excluded_from_records` |
| 不正な ts の除外 | `test_unparseable_ts_excluded` |
| summary の集計項目 | `test_multiple_days`, `test_summary_counts` |
| record_id の決定性 | `test_same_date_emp_gives_same_id`, `test_different_date_gives_different_id` |

### 2. `tests/test_attendance_rules.py` — lib/attendance_rules.py (State, apply_rules, sweep_errors)

- `apply_rules`: 同一UIDに対し、直前のタップから5分未満の再タップは無視され空リストを返す。5分ちょうど、または5分超の再タップは処理される。
- `apply_rules`: このデバウンスはUIDごとに独立しており、別UIDのタップは制限を受けない。
- `apply_rules`: 初めてのタップはINイベントとして返され、`emp` フィールドは渡した従業員IDになる。
- `apply_rules`: IN済みのUIDへの次のタップはOUTイベントを返す。
- `apply_rules`: OUT後、同日中の再タップは無視され空リストを返す。
- `apply_rules`: OUT後、翌日のタップはINイベントとして扱われる。
- `apply_rules`: `emp` が `"unknown"` のタップは、そのUIDに直前まで記録されていた従業員IDをイベントの `emp` として使い、状態側の従業員IDは上書きしない。
- `apply_rules`: 前日にINしたまま同じカードが翌日タップされると、ERRORイベント（`code="day_rollover"`）が先に、INイベントが後に返される。
- `apply_rules`: IN状態のまま15時間を超えて経過した状態でタップすると、そのタップで `code="timeout_15h"` のERRORイベントが発生する。14時間経過時点ではERRORは発生しない。
- `apply_rules` が返すイベントには常に `id`・`ts`・`uid`・`emp`・`act` フィールドが含まれる。ERRORイベントには追加で `code` フィールドが含まれるが、ERROR以外のイベントには `code` フィールドが含まれない。
- `sweep_errors`: 指定時刻の時点で「入場中」のUIDについて、day_rolloverまたはtimeout_15hのERRORイベントを検出して返す。
- `sweep_errors`: 入場中でないUID、および状態が空の場合はエラーを返さない。
- `sweep_errors`: 複数UIDが存在する場合、入場中のUIDのみがエラー対象になる。
- `sweep_errors` でday_rolloverエラーが発行された後、そのUIDは「外にいる」状態になり、次のタップはINとして扱われる。
- `State.from_current_month(repo_root)`: 現在月（`now_jst()` 基準）のイベントファイルから状態を復元する。IN のみのUIDは入場中（次タップはOUT、従業員IDも復元）、IN→OUT済みのUIDは同日中の再タップ無視、イベント無しは空状態（初回タップはIN）として復元され、先月のイベントは対象外。

| 保証（要約） | 対応テスト |
|---|---|
| 5分未満の再タップは無視 | `test_tap_within_5min_ignored` |
| 5分ちょうど/超は処理 | `test_tap_at_exactly_5min_processed`, `test_tap_after_5min_processed` |
| デバウンスはUID単位 | `test_debounce_is_per_uid` |
| 初回タップはIN | `test_first_tap_is_in` |
| 2回目タップはOUT | `test_second_tap_is_out` |
| OUT後同日は無視 | `test_out_then_same_day_tap_ignored` |
| OUT後翌日はIN | `test_out_then_next_day_tap_is_in` |
| unknown emp タップは直前の従業員IDを使用 | `test_unknown_emp_tap_uses_last_known_emp` |
| unknown emp タップは状態を上書きしない | `test_unknown_emp_tap_does_not_overwrite_stored_emp` |
| day_rollover でERROR→INの順に発行 | `test_in_yesterday_tap_today_emits_error_then_in`, `test_day_rollover_order_error_before_in` |
| sweep_errors のday_rollover検出 | `test_sweep_errors_day_rollover` |
| day_rollover後は外にいる扱い | `test_sweep_errors_after_rollover_uid_is_outside` |
| timeout_15h の検出/非検出 | `test_in_then_16h_later_same_day_emits_timeout`, `test_in_then_14h_later_no_timeout` |
| sweep_errors のtimeout_15h検出 | `test_sweep_errors_timeout` |
| 入場中でない/空状態はエラー無し | `test_not_inside_no_error`, `test_empty_state_no_error` |
| 複数UIDでは入場中のみ対象 | `test_multiple_uids_only_inside_flagged` |
| イベントの必須フィールド | `test_event_has_required_fields` |
| ERRORイベントのcodeフィールド有無 | `test_error_event_has_code`, `test_non_error_event_has_no_code` |
| 現在月からの状態復元 | `test_restores_inside_state_and_emp`, `test_restores_done_day_after_out`, `test_no_events_restores_empty_state`, `test_reads_only_current_month` |

### 3. `tests/test_attendance_store.py` — lib/attendance_store.py (append_jsonl, append_event, iter_events_month, iter_payroll_month, month_events_path, month_payroll_path)

- `append_jsonl`: 親ディレクトリが存在しない場合でも自動作成し、ファイルに1行追記する。追記した内容は同じファイルから読み戻せ、複数回の追記はすべて保持される。
- `append_event`: イベントの `ts` フィールドがdatetimeの場合、JSTのISO形式文字列に変換してから保存する（例: `"2026-01-10T09:00:00+09:00"`）。
- `month_events_path`・`month_payroll_path`: 呼び出しただけでは親ディレクトリを作成しない（副作用が無い）。`month_events_path` は `state/attendance/events/{YYYY-MM}.jsonl` を、`month_payroll_path` は `state/attendance/payroll/{YYYY-MM}.jsonl` を返す。
- `iter_events_month`・`iter_payroll_month`: 対応する月のファイルが存在しない場合は空を返す（例外を送出しない）。
- `iter_events_month`: `append_event` で保存したイベントを読み戻すことができ、`emp`・`act` 等のフィールドが保持される。
- `iter_events_month`: ファイル中の空行・JSONとして不正な行・dictでない行（配列等）はスキップされ、不正な行についてはwarningログが記録される。他の正常な行の読み込みには影響しない。
- `iter_payroll_month`: `append_jsonl` で書き込んだオブジェクトを読み戻すことができる。

| 保証（要約） | 対応テスト |
|---|---|
| 親ディレクトリ自動作成と追記 | `test_creates_file_and_parent_dirs` |
| 書き込み内容の読み戻し | `test_written_line_is_readable` |
| 複数回追記の保持 | `test_multiple_appends` |
| datetime の ts を ISO 文字列化して保存 | `test_datetime_ts_serialized_to_iso` |
| パス関数に副作用が無い | `test_month_events_path_no_mkdir`, `test_month_payroll_path_no_mkdir` |
| パス関数が返す場所 | `test_month_events_path_correct_location`, `test_month_payroll_path_correct_location` |
| 存在しない月は空を返す（events / payroll） | `test_iter_nonexistent_month_returns_empty`, `test_iter_nonexistent_payroll_month_returns_empty` |
| append_event → iter_events_month の往復 | `test_append_and_iter_events` |
| append_jsonl → iter_payroll_month の往復 | `test_append_and_iter_payroll` |
| 公開イテレータ経由での不正行スキップ | `test_malformed_and_blank_lines_skipped_via_public_iterator` |

## About

対象範囲は `lib/payroll_calc.py`・`lib/attendance_rules.py`・`lib/attendance_store.py` の、アンダースコアで始まらない公開関数・クラス・メソッドとその戻り値・送出例外・ログ出力である。アンダースコア始まりの関数（例: `lib/attendance_store.py` の `_iter_jsonl`）は内部実装として対象外とし、その振る舞いは公開関数（`iter_events_month`・`iter_payroll_month`）の保証としてのみ扱う。**ここに載っていない振る舞いは約束ではなく、予告なく変わりうる。** 本台帳の位置づけは design-decisions.md 相当のドキュメントと同格である。
