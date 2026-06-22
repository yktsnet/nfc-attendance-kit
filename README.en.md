[🇯🇵 日本語](README.md) | [🇬🇧 English](README.en.md)

# NFC Attendance & Payroll System

[![CI](https://github.com/yktsnet/nfc-attendance-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/yktsnet/nfc-attendance-kit/actions/workflows/ci.yml)

A clock-in and payroll system combining the Sony RC-S300 (PaSoRi) with a Raspberry Pi.
**Just tap an NFC card** to record attendance — Discord notifications and automatic Google Sheets aggregation are included.

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/nfc-attendance-kit.svg" width="400">
    <img src="./src/nfc-attendance-kit.svg" alt="NFC Attendance Architecture" style="max-width: 100%;" width="800">
  </picture>
</p>

## Architecture

| Component | Role |
|-----------|------|
| **Edge (Pi 2)** | Controls Sony RC-S300 via PC/SC and reads NFC UIDs |
| **Logic** | Python handles 5-minute debounce, 15-hour timeout, and midnight rollover |
| **Backend (GAS)** | Syncs to Google Sheets via HTTPS API |
| **Notifications** | Real-time feedback via Discord Webhook |

## Design Principles

- **Simplicity** — Employees only need to tap their card
- **Reuse existing hardware** — Works on Raspberry Pi 2 or older PCs. No pip dependencies (standard library only)
- **Error prevention** — Debounce, timeout, and midnight rollover are all handled by the system

## Requirements

### Hardware

- Sony RC-S300/P (PaSoRi) or any PC/SC-compatible NFC reader
- Raspberry Pi 2 / any Linux PC (Ubuntu 22.04+, Debian 11+, Raspberry Pi OS)

### Software

```bash
sudo apt update
sudo apt install -y pcscd libccid opensc
python3 --version  # 3.11 or later
```

No pip dependencies. All Python code runs on the standard library only.

## Setup

### 1. Clone

```bash
git clone https://github.com/yktsnet/nfc-attendance-kit.git ~/nfc
cd ~/nfc
```

### 2. PCSC Service

```bash
sudo systemctl enable --now pcscd

# Verify the reader is recognized
opensc-tool --list-readers
# → 0: Sony RC-S300 ...
```

### 3. Secrets

```bash
cp config/attendance/discord.env.example config/attendance/discord.env
cp config/attendance/gas.env.example     config/attendance/gas.env

nano config/attendance/discord.env
nano config/attendance/gas.env
```

### 4. NFC Card Registration

Copy the UID map template and map card UIDs to employee IDs.

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

A card's UID can be checked with:

```bash
opensc-tool --reader 0 --wait --card-driver default --send-apdu FF:CA:00:00:00
# The hex byte string in the "Received" line is the UID
```

### 5. Employee Config

```bash
cp config/employees/emp.env.example config/employees/emp01.env
nano config/employees/emp01.env
```

```ini
NAME=Taro Yamada
HOURLY_YEN=1500
ROUND_UNIT_MINUTES=5
```

The filename (`emp01.env`) must match the value in `uid_map.json`.

### 6. systemd Deploy

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

Verify:

```bash
systemctl --user status attendance-reader
journalctl --user -u attendance-reader -f
```

### 7. Google Apps Script Deploy

1. Create a new Google Spreadsheet and note the **Spreadsheet ID** from the URL
2. Open **Extensions → Apps Script**
3. Paste `Code.js` and `payroll_views.js` from `gas/nfc_reader/`
4. Replace `SPREADSHEET_ID` in `Code.js` with the ID from step 1
5. Set employee IDs and names in `PAYROLL_VIEW_EMP_LABELS` in `payroll_views.js`
6. **Deploy → New deployment → Web app**
   - Execute as: **Me**
   - Who has access: **Anyone** (requests are validated with `ATT_GAS_TOKEN`)
7. Set the deployment URL as `ATT_GAS_URL` in `config/attendance/gas.env`

## Services

| Service | Role | Run on |
|---------|------|--------|
| `attendance-reader` | Reads NFC UIDs and writes event logs | Machine with NFC reader |
| `attendance-discord` | Tails event log and posts to Discord | Notification display PC |
| `attendance-payroll.timer` | Daily payroll calculation and GAS sync | Machine with access to shared filesystem |

In a single-machine setup, all three services can run on the same device.

## Adding an Employee

1. Monitor logs with `sudo journalctl -fu attendance-reader.service` and tap the new card
2. Note the `uid` value in the JSON line containing `"emp":"unknown"`
3. Add the UID and new employee ID to `config/attendance/uid_map.json`
4. Create `config/employees/<emp_id>.env` with name, hourly wage, and rounding unit
5. `sudo systemctl restart attendance-reader.service` (uid_map is loaded at startup, so a restart is required)

Hourly wage changes only require editing `emp.env` — no restart needed, as the value is read fresh at each payroll calculation.

## Anomaly Flags

Records output by `attendance_payroll.py` may include the following flags:

| Flag | Meaning |
|------|---------|
| `missing_out` | Session ended without OUT (timeout, error, etc.) |
| `orphan_out` | OUT detected without a matching IN |
| `double_in` | IN detected again without a preceding OUT |
| `cross_day` | IN and OUT span two calendar days |
| `timeout_15h` | Session auto-closed after exceeding 15 hours |
| `day_rollover` | Auto-closed at midnight rollover |
| `missing_hourly_yen` | Hourly wage not found for the employee |

## Development & Testing

```bash
pip install pytest
pytest
```

Tests cover the 3 modules in `lib/` (state machine, payroll calculation, store) and run on the standard library only. CI automatically runs tests on Python 3.11 and 3.12 for every push and pull request.

## Tech Stack

| Category | Details | Reason |
|----------|---------|--------|
| Language | Python 3.11+ (standard library only) | Zero pip dependencies simplifies deployment to Raspberry Pi |
| Language | JavaScript (GAS) | Native integration with Google Sheets |
| Infrastructure | Linux systemd user services | No root required; persistent with `loginctl enable-linger` |
| Hardware | Sony RC-S300/P, Raspberry Pi 2 | Reuse of existing assets; PC/SC standard abstracts NFC readers |
| Notifications | Discord Webhook | No bot required; one URL is all it takes |

## Design Decisions

- **Standard library only**: Eliminates pip install, enabling clone-and-run. Works on Raspberry Pi OS Python with no additional packages.
- **GAS (Google Apps Script)**: Google Sheets chosen as the payroll aggregation target. No dedicated server or DB needed; viewing, sharing, and printing delegated to Google.
- **systemd user services**: No root required; scales from single to multi-machine. Daily batch managed declaratively with timers.
- **File-based state management (`state/`)**: No DB; attendance persisted as JSON logs. Backups done with `cp`.

## Scope

**Focus:**
- Detecting, recording, notifying, and calculating payroll from NFC card taps
- Operation in small businesses (dozens of employees or fewer)

**Out of Scope:**
- Web UI / mobile app clock-in
- Migration to cloud DB (PostgreSQL, etc.)
- Attendance approval workflows and shift management
