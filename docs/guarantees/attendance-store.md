# attendance-store

## 書き込み

| 保証 | 対応テスト |
|---|---|
| `append_jsonl` は親ディレクトリが無ければ作る | `test_creates_file_and_parent_dirs` |
| `append_jsonl` は書き込み先のファイルが無ければ作る | `test_creates_file_and_parent_dirs` |
| `append_jsonl` で書いた内容は同じファイルから読み戻せる | `test_written_line_is_readable` |
| `append_jsonl` の複数回の追記は追記順にすべて残る | `test_multiple_appends` |
| `append_event` は datetime の `ts` を JST の ISO 文字列（例: `2026-01-10T09:00:00+09:00`）にして保存する | `test_datetime_ts_serialized_to_iso` |

## ファイルの置き場

| 保証 | 対応テスト |
|---|---|
| `month_events_path` は親ディレクトリを作らない | `test_month_events_path_no_mkdir` |
| `month_payroll_path` は親ディレクトリを作らない | `test_month_payroll_path_no_mkdir` |
| `month_events_path` は `state/attendance/events/{YYYY-MM}.jsonl` を返す | `test_month_events_path_correct_location` |
| `month_payroll_path` は `state/attendance/payroll/{YYYY-MM}.jsonl` を返す | `test_month_payroll_path_correct_location` |

## 読み出し

| 保証 | 対応テスト |
|---|---|
| `iter_events_month` はファイルの無い月に空を返す | `test_iter_nonexistent_month_returns_empty` |
| `iter_payroll_month` はファイルの無い月に空を返す | `test_iter_nonexistent_payroll_month_returns_empty` |
| `iter_events_month` は `append_event` で保存したイベントを `emp`・`act` を保ったまま読み戻す | `test_append_and_iter_events` |
| `iter_payroll_month` は `append_jsonl` で書いたオブジェクトをそのまま読み戻す | `test_append_and_iter_payroll` |
| `iter_payroll_month` は `append_jsonl` で追記した行を追記順に返す | `test_appended_lines_read_back_in_order_via_public_iterator` |
| `iter_events_month` は空行を飛ばす | `test_malformed_and_blank_lines_skipped_via_public_iterator` |
| `iter_events_month` は JSON として不正な行を飛ばす | `test_malformed_and_blank_lines_skipped_via_public_iterator` |
| `iter_events_month` は dict でない行を飛ばす | `test_malformed_and_blank_lines_skipped_via_public_iterator` |
| `iter_events_month` は飛ばした行の前後の正しい行を順に返す | `test_malformed_and_blank_lines_skipped_via_public_iterator` |
| `iter_events_month` は JSON として不正な行に warning のログを出す | `test_malformed_and_blank_lines_skipped_via_public_iterator` |
