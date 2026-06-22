[🇯🇵 日本語](setup.md) | [🇬🇧 English](setup.en.md)

# Setup Guide

Detailed steps from connecting the NFC reader through systemd persistence and GAS deployment. For environment prerequisites, see Requirements in the [README](../README.en.md).

## 1. Clone

```bash
git clone https://github.com/yktsnet/nfc-attendance-kit.git ~/nfc
cd ~/nfc
```

## 2. PCSC Service

```bash
sudo systemctl enable --now pcscd

# Verify the reader is recognized
opensc-tool --list-readers
# → 0: Sony RC-S300 ...
```

## 3. Secrets

```bash
cp config/attendance/discord.env.example config/attendance/discord.env
cp config/attendance/gas.env.example     config/attendance/gas.env

nano config/attendance/discord.env
nano config/attendance/gas.env
```

## 4. NFC Card Registration

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

## 5. Employee Config

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

## 6. systemd Deploy

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

For each service's role and target machine, see [Services in the README](../README.en.md#services).

## 7. Google Apps Script Deploy

1. Create a new Google Spreadsheet and note the **Spreadsheet ID** from the URL
2. Open **Extensions → Apps Script**
3. Paste `Code.js` and `payroll_views.js` from `gas/nfc_reader/`
4. Replace `SPREADSHEET_ID` in `Code.js` with the ID from step 1
5. Set employee IDs and names in `PAYROLL_VIEW_EMP_LABELS` in `payroll_views.js`
6. **Deploy → New deployment → Web app**
   - Execute as: **Me**
   - Who has access: **Anyone** (requests are validated with `ATT_GAS_TOKEN`)
7. Set the deployment URL as `ATT_GAS_URL` in `config/attendance/gas.env`
