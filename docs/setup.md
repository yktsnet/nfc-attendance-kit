[🇯🇵 日本語](setup.md) | [🇬🇧 English](setup.en.md)

# Setup Guide

NFC リーダーの接続から systemd 常駐・GAS デプロイまでの詳細手順。動作環境の前提は [README](../README.md) の Requirements を参照。

## 1. Clone

```bash
git clone https://github.com/yktsnet/nfc-attendance-kit.git ~/nfc
cd ~/nfc
```

## 2. PCSC Service

```bash
sudo systemctl enable --now pcscd

# リーダーが認識されているか確認
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

## 5. Employee Config

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

動作確認：

```bash
systemctl --user status attendance-reader
journalctl --user -u attendance-reader -f
```

各サービスの役割と起動対象は [README の Services](../README.md#services) を参照。

## 7. Google Apps Script Deploy

1. Google スプレッドシートを新規作成し、URL から **スプレッドシート ID** を控える
2. **拡張機能 → Apps Script** を開く
3. `gas/nfc_reader/` 内の `Code.js` と `payroll_views.js` を貼り付ける
4. `Code.js` の `SPREADSHEET_ID` を手順 1 の ID に書き換える
5. `payroll_views.js` の `PAYROLL_VIEW_EMP_LABELS` に社員 ID と氏名を設定する
6. **デプロイ → 新しいデプロイ → ウェブアプリ** で公開
   - 実行ユーザー: **自分**
   - アクセスできるユーザー: **全員**（リクエストは `ATT_GAS_TOKEN` で検証）
7. デプロイ URL を `config/attendance/gas.env` の `ATT_GAS_URL` に設定する
