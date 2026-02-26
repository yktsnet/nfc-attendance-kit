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

## 導入手順
- エッジデバイスへのPythonスクリプトの配置と `systemd` へのサービス登録
- GAS（Google Apps Script）のウェブアプリケーションとしてのデプロイ
- `.env`ファイルによる従業員設定とWebhook URLの設定
</details>

## System Architecture
1. **Edge (Pi 2)**: NFC UID capture using Sony RC-S300 via PCSC.
2. **Logic**: State management (5-min debounce, 15-hour timeouts), anomaly flagging, and time rounding implemented in Python.
3. **Backend (GAS)**: Synchronization to Google Sheets via HTTPS API.
4. **Notification**: Real-time feedback via Discord webhook for check-in/out verification on a repurposed PC display.

## Design Concept
The system uses physical card taps to record attendance, minimizing UI interaction:
- **Simple Operation**: Users record attendance solely by tapping physical cards.
- **Hardware Utilization**: Designed to operate on low-resource hardware.
- **Input Validation**: Automatically handles debouncing, timeouts, and cross-day logic to prevent invalid data entries.

## Key Features
- **Low Resource Requirements**: Runs on legacy SBCs and laptops.
- **Anomaly Detection**: Flags missing check-outs, cross-day shifts, and duplicate scans.
- **API Retry Logic**: Built-in error handling for backend synchronization.
- **Configuration**: Employee-specific hourly rates and rounding intervals are managed via isolated `.env` files.

## Getting Started
Deployment requires the following steps:
- Registering Python scripts as `systemd` services on the edge device.
- Deploying Google Apps Script as a Web App.
- Configuring employee settings and webhooks via `.env` files.

## Tech Stack
- **Language**: Python 3.12, JavaScript (GAS)
- **Infrastructure**: Linux (Systemd), Google Apps Script
- **Hardware**: Sony RC-S300/P, Raspberry Pi 2, Repurposed Laptop
