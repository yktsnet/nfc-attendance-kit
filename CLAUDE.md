# CLAUDE.md

@context/conventions.md

## コマンド

- テスト: `pytest`（pytest.ini で pythonpath=. 設定済み）
- 構文チェック: `python -m py_compile lib/payroll_calc.py`（変更ファイルごと）

## アーキテクチャの要点

- NFC リーダー（RC-S300 / PC/SC）でカードの UID を読み取り、`config/attendance/uid_map.json` で社員に紐付ける。
- `core/` が 3 つのエントリポイント: `attendance_reader.py`（打刻）、`attendance_discord.py`（Discord 通知）、`attendance_payroll.py`（給与計算・GAS 同期）。
- `lib/` が共通ロジック: ルール判定・打刻保存・給与計算・GAS 連携・JST 時刻。
- 設定は `config/` 配下の `.env` ファイルと JSON。秘密値は `.gitignore` で除外済み。
- ランタイム状態（打刻ログ・キャッシュ）は `state/` に保存（ignore 対象）。
- `gas/` は Google Apps Script（スプレッドシート連携）。Python とは独立。

## 検証手段

- `pytest`
- 変更した `.py` に `python -m py_compile`
- `core/` の実行・NFC ハードウェア動作は user が確認
