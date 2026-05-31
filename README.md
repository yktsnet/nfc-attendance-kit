# NFC Attendance & Payroll System

[![CI](https://github.com/yktsnet/nfc-attendance-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/yktsnet/nfc-attendance-kit/actions/workflows/ci.yml)

Sony RC-S300（PaSoRi）と Raspberry Pi を組み合わせた打刻・給与計算システム。
**NFC カードをタッチするだけ**で打刻が完了し、Discord 通知と Google スプレッドシートへの自動集計まで行う。

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/nfc-attendance-kit.svg" width="400">
    <img src="./src/nfc-attendance-kit.svg" alt="NFC Attendance Architecture" style="max-width: 100%;" width="800">
  </picture>
</p>

## Architecture

| コンポーネント | 役割 |
|--------------|------|
| **Edge (Pi 2)** | Sony RC-S300 を PCSC 経由で制御し NFC UID を取得 |
| **ロジック** | 5 分デバウンス・15 時間タイムアウト・日またぎ判定を Python で処理 |
| **バックエンド (GAS)** | HTTPS API 経由で Google スプレッドシートへ同期 |
| **通知** | Discord Webhook でリアルタイムフィードバック |

## Design Principles

- **操作の単純化** — 従業員が覚えることはカードをタッチするだけ
- **既存ハードウェア活用** — Raspberry Pi 2 や旧型 PC で動作。pip 依存なし（標準ライブラリのみ）
- **エラー防止** — デバウンス・タイムアウト・日またぎ判定をすべてシステム側で処理

## Requirements

### ハードウェア

- Sony RC-S300/P（PaSoRi）または PCSC 互換 NFC リーダー
- Raspberry Pi 2 / 任意の Linux PC（Ubuntu 22.04+、Debian 11+、Raspberry Pi OS）

### ソフトウェア

```bash
sudo apt update
sudo apt install -y pcscd libccid opensc
python3 --version  # 3.11 以上
```

pip 依存はない。Python コードはすべて標準ライブラリのみで動作する。

## Setup

### 1. Clone

```bash
git clone https://github.com/yktsnet/nfc-attendance-kit.git ~/nfc
cd ~/nfc
```

### 2. PCSC サービスの起動

```bash
sudo systemctl enable --now pcscd

# リーダーが認識されているか確認
opensc-tool --list-readers
# → 0: Sony RC-S300 ...
```

### 3. シークレット設定

```bash
cp config/attendance/discord.env.example config/attendance/discord.env
cp config/attendance/gas.env.example     config/attendance/gas.env

nano config/attendance/discord.env
nano config/attendance/gas.env
```

### 4. NFC カード登録

UID マップのテンプレートをコピーし、カード UID と社員 ID を対応付ける。

```bash
cp config/attendance/uid_map.json.example config/attendance/uid_map.json
nano config/attendance/uid_map.json
```

```json
{
  "0123456789ABCD": "emp01",
  "FEDCBA98765432": "emp02"
}
```

カードの UID は次のコマンドで確認できる。

```bash
opensc-tool --reader 0 --wait --card-driver default --send-apdu FF:CA:00:00:00
# "Received" 行の16進バイト列が UID
```

### 5. 社員設定

```bash
cp config/employees/emp.env.example config/employees/emp01.env
nano config/employees/emp01.env
```

```ini
NAME=山田太郎
HOURLY_YEN=1500
ROUND_UNIT_MINUTES=5
```

ファイル名（`emp01.env`）は `uid_map.json` の値と一致させる。

### 6. systemd サービスのデプロイ

```bash
mkdir -p ~/.config/systemd/user
cp config/systemd/usr/*.service ~/.config/systemd/user/
cp config/systemd/usr/*.timer   ~/.config/systemd/user/

systemctl --user daemon-reload

systemctl --user enable --now attendance-reader
systemctl --user enable --now attendance-discord
systemctl --user enable --now attendance-payroll.timer

loginctl enable-linger $USER
```

動作確認：

```bash
systemctl --user status attendance-reader
journalctl --user -u attendance-reader -f
```

### 7. Google Apps Script のデプロイ

1. Google スプレッドシートを新規作成し、URL から **スプレッドシート ID** を控える
2. **拡張機能 → Apps Script** を開く
3. `gas/nfc_reader/` 内の `Code.js` と `payroll_views.js` を貼り付ける
4. `Code.js` の `SPREADSHEET_ID` を手順 1 の ID に書き換える
5. `payroll_views.js` の `PAYROLL_VIEW_EMP_LABELS` に社員 ID と氏名を設定する
6. **デプロイ → 新しいデプロイ → ウェブアプリ** で公開
   - 実行ユーザー: **自分**
   - アクセスできるユーザー: **全員**（リクエストは `ATT_GAS_TOKEN` で検証）
7. デプロイ URL を `config/attendance/gas.env` の `ATT_GAS_URL` に設定する

## Services

| サービス | 役割 | 起動対象 |
|---------|------|---------|
| `attendance-reader` | NFC UID 読み取り・イベントログ書き込み | リーダー接続機 |
| `attendance-discord` | イベントログを tail して Discord 投稿 | 通知表示 PC |
| `attendance-payroll.timer` | 日次給与計算・GAS 同期 | 共有ファイルシステムにアクセスできる機器 |

1 台構成の場合は 3 サービスすべてを同一機で動かせる。

## Adding an Employee

1. `sudo journalctl -fu attendance-reader.service` でログを監視しながら新カードをタッチ
2. `"emp":"unknown"` の JSON に含まれる `uid` の値を確認
3. `config/attendance/uid_map.json` に UID と新しい社員 ID を追記
4. `config/employees/<emp_id>.env` を作成して氏名・時給・丸め単位を設定
5. `sudo systemctl restart attendance-reader.service`（uid_map は起動時に読み込まれるため再起動必須）

時給変更は `emp.env` を編集するだけでよい。給与計算時に都度読み込まれるためサービス再起動は不要。

## Anomaly Flags

`attendance_payroll.py` が出力する給与レコードには、以下のフラグが付与される場合がある。

| フラグ | 意味 |
|-------|------|
| `missing_out` | IN のまま終了（タイムアウト・エラー等） |
| `orphan_out` | 対応する IN なしに OUT を検出 |
| `double_in` | OUT なしに再度 IN を検出 |
| `cross_day` | IN と OUT が日付をまたいでいる |
| `timeout_15h` | 15 時間超の打刻を自動クローズ |
| `day_rollover` | 日付変更時の自動クローズ |
| `missing_hourly_yen` | 社員の時給設定が見つからない |

## Development & Testing

```bash
pip install pytest
pytest
```

テストは `lib/` の 3 モジュール（状態機械・給与計算・ストア）を対象とし、標準ライブラリのみで動作する。CI は push / PR 時に Python 3.11・3.12 でテストを自動実行する。

## Tech Stack

| 区分 | 内容 |
|-----|------|
| 言語 | Python 3.11+（標準ライブラリのみ）、JavaScript（GAS） |
| インフラ | Linux systemd user services、Google Apps Script |
| ハードウェア | Sony RC-S300/P、Raspberry Pi 2、旧型 PC |
| 通知 | Discord Webhook |
