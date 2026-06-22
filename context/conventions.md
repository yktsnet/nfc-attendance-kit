# Conventions

命名・コード規約・スタイル（どう書くか）。

## Python

- エントリポイントは `core/` 配下。各ファイルが独立した実行単位（reader / discord / payroll）。
- 共通ロジックは `lib/` 配下にモジュール分割。`attendance_rules.py`（勤務ルール判定）、`payroll_calc.py`（給与計算）、`attendance_store.py`（打刻永続化）など。
- 時刻は `lib/time_jst.py` 経由で JST を扱う。
- 設定読み込みは `lib/env_loader.py`。`config/` 配下の `.env` を読む。
- テストは `tests/` 配下の `test_*.py`。外部依存なし（NFC リーダー・Discord・GAS 不要）。

## Google Apps Script (gas/)

- `gas/nfc_reader/Code.js` がメイン。`payroll_views.js` が給与表示。
- Python 側の `lib/gas_sync.py` から HTTP で連携。

## 設定ファイル

- `config/attendance/` — Discord 通知・GAS 連携・UID マッピング
- `config/employees/` — 社員ごとの `.env`（時給・勤務形態等）
- テンプレートは `.example` 付きで tracking。実値は ignore。

## コミット

- conventional commits（`feat` / `fix` / `docs` / `style` / `chore`）。
