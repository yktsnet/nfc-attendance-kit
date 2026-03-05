# NFC Attendance & Payroll System

An NFC-based attendance and payroll calculation script set designed to run on legacy hardware like Raspberry Pi 2 and repurposed PCs.

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/nfc-attendance-kit.svg" width="400">
    <img src="./src/nfc-attendance-kit.svg" alt="NFC Attendance Architecture" style="max-width: 100%;" width="800">
  </picture>
</p>

<details>
<summary>🇯🇵 日本語による説明を表示する</summary>

## システム概要
Raspberry Pi 2や旧型PCなどの既存ハードウェアを利用した勤怠管理および給与計算システムです。

## 設計方針
利用者の操作をICカードのタッチのみに限定して設計されています。
- **シンプルな操作**: 従業員は物理カードをNFCリーダーにタッチして打刻を記録します。
- **既存ハードウェアの活用**: Raspberry Pi 2や旧型PCを動作環境として想定し、軽量に動作します。
- **エラー防止処理**: 5分以内の連続打刻の無視、15時間経過後の自動タイムアウト、日またぎの判定などをシステム側で処理します。

## システム構成
1. **エッジ (Pi 2)**: Sony RC-S300をPCSC経由で制御し、NFCのUIDを読み取ります。
2. **ロジック**: Pythonで打刻状態を管理し、異常検知（`missing_out`等）や労働時間の丸め処理を行います。
3. **バックエンド (GAS)**: HTTPS APIを介してGoogleスプレッドシートへデータを同期します。
4. **通知・表示**: DiscordのWebhookを利用し、旧型PC等の画面上に打刻結果のフィードバックを表示します。

## 主な機能
- **低リソース動作**: 旧型SBCやPCで動作するよう設計されています。
- **リトライ処理**: ネットワーク通信のエラーに対するAPIリトライロジックを実装しています。
- **ルール設定**: 従業員ごとの`.env`ファイルを用いて、時給および丸め単位（分）を設定します。

</details>

## System Architecture

```
[NFC Card] → [Sony RC-S300] → [Pi 2 / Linux PC]
                                      │
                         attendance_reader.py   (PCSC, state machine)
                                      │
                         attendance_discord.py  (tail events → Discord)
                         attendance_payroll.py  (daily cron → GAS)
                                      │
                              [Google Sheets]  ←  GAS Web App
```

1. **Edge (Pi 2)**: NFC UID capture using Sony RC-S300 via PCSC / opensc-tool.
2. **Logic**: State management (5-min debounce, 15-hour timeouts), anomaly flagging, and time rounding implemented in Python.
3. **Backend (GAS)**: Synchronization to Google Sheets via HTTPS API.
4. **Notification**: Real-time feedback via Discord webhook for check-in/out verification on a repurposed PC display.

## Design Concept

- **Simple Operation**: Users record attendance solely by tapping physical cards.
- **Hardware Utilization**: Designed to operate on low-resource hardware. No pip dependencies — stdlib only.
- **Input Validation**: Automatically handles debouncing, timeouts, and cross-day logic to prevent invalid data entries.

## Requirements

### Hardware
- Sony RC-S300/P (PaSoRi) or compatible PCSC NFC reader
- Raspberry Pi 2 / any Linux PC (Ubuntu 22.04+, Debian 11+, Raspberry Pi OS)

### Software
```bash
# System packages (apt)
sudo apt update
sudo apt install -y pcscd libccid opensc

# Python 3.11+ with zoneinfo (standard library)
python3 --version
```

> **Note**: This project has **no pip dependencies**. All Python code uses the standard library only.

## Getting Started

### 1. Clone

```bash
git clone https://github.com/yktsnet/nfc-attendance-kit.git ~/nfc
cd ~/nfc
```

### 2. System service for PCSC

```bash
sudo systemctl enable --now pcscd
```

Verify the NFC reader is detected:

```bash
opensc-tool --list-readers
# Expected: 0: Sony RC-S300 ...
```

### 3. Configure secrets

```bash
# Attendance config
cp config/attendance/discord.env.example config/attendance/discord.env
cp config/attendance/gas.env.example     config/attendance/gas.env

# Edit each file and fill in real values
nano config/attendance/discord.env
nano config/attendance/gas.env
```

### 4. Register NFC cards

Copy the UID map template and map each card UID to an employee ID:

```bash
cp config/attendance/uid_map.json.example config/attendance/uid_map.json
nano config/attendance/uid_map.json
```

Find your card's UID by tapping it and running:

```bash
opensc-tool --reader 0 --wait --card-driver default --send-apdu FF:CA:00:00:00
# Look for the "Received" hex bytes in the output
```

Format:
```json
{
  "0123456789ABCD": "emp01",
  "FEDCBA98765432": "emp02"
}
```

### 5. Configure employees

```bash
cp config/employees/emp.env.example config/employees/emp01.env
nano config/employees/emp01.env
```

```ini
NAME=Taro_Yamada
HOURLY_YEN=1500
ROUND_UNIT_MINUTES=5
```

The filename (e.g. `emp01.env`) must match the value in `uid_map.json`.

### 6. Deploy systemd services (user-level)

All three services run as the current user under `~/.config/systemd/user/`.

```bash
mkdir -p ~/.config/systemd/user
cp config/systemd/usr/*.service ~/.config/systemd/user/
cp config/systemd/usr/*.timer  ~/.config/systemd/user/

systemctl --user daemon-reload

# NFC reader (always running on the edge device)
systemctl --user enable --now attendance-reader

# Discord notifier (always running on the notification PC)
systemctl --user enable --now attendance-discord

# Payroll sync (daily timer)
systemctl --user enable --now attendance-payroll.timer

# Keep user services running after logout
loginctl enable-linger $USER
```

Check status:
```bash
systemctl --user status attendance-reader
journalctl --user -u attendance-reader -f
```

### 7. Deploy Google Apps Script

1. Create a new Google Spreadsheet and note the **Spreadsheet ID** from the URL.
2. Open **Extensions → Apps Script**.
3. Create two files: `Code.js` and `payroll_views.js` (contents in `gas/nfc_reader/`).
4. In `Code.js`, set `SPREADSHEET_ID` to your spreadsheet's ID.
5. In `payroll_views.js`, update `PAYROLL_VIEW_EMP_LABELS` with your employee IDs and names.
6. Click **Deploy → New deployment → Web App**.
   - Execute as: **Me**
   - Who has access: **Anyone** (requests are validated by `ATT_GAS_TOKEN`)
7. Copy the deployment URL into `config/attendance/gas.env` as `ATT_GAS_URL`.

## Service Layout

| Service | Role | Runs on |
|---------|------|---------|
| `attendance-reader` | Reads NFC card UIDs, writes event log | Edge device (Pi / PC with reader) |
| `attendance-discord` | Tails event log, posts to Discord | Notification display PC |
| `attendance-payroll.timer` | Daily payroll build + GAS sync | Any device on the same filesystem |

All services share the same `~/nfc/` directory. On a single-machine setup, all three can run on one device.

## Key Features

- **No pip dependencies**: stdlib only (`json`, `urllib`, `subprocess`, `zoneinfo`, …)
- **Anomaly Detection**: Flags `missing_out`, `day_rollover`, `timeout_15h`, `double_in`, `orphan_out`
- **API Retry Logic**: Configurable retries + sleep for GAS sync and Discord posting
- **Time Rounding**: Per-employee configurable rounding unit (default 5 min)
- **Month Rollover**: Payroll job covers previous month on the 1st–2nd of each month

## Tech Stack

- **Language**: Python 3.11+, JavaScript (GAS)
- **Infrastructure**: Linux (systemd user services), Google Apps Script
- **Hardware**: Sony RC-S300/P, Raspberry Pi 2, Repurposed Laptop
