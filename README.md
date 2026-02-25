# NFC Attendance & Payroll Kit

A production-ready, end-to-end IoT kit optimized for high-utility, low-budget deployments using legacy hardware like Raspberry Pi 2 and repurposed laptops.

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/nfc-attendance-kit.svg" width="400">
    <img src="./src/nfc-attendance-kit.svg" alt="NFC Attendance Kit Architecture" style="max-width: 100%;" width="800">
  </picture>
</p>

<details>
<summary>🇯🇵 日本語による説明を表示する</summary>

## システム概要
Raspberry Pi 2 や旧型ラップトップ等の既存資産を「現場の即戦力」として再定義し、低予算かつ高信頼な運用を実現する勤怠管理・自動給与計算キット。

## 設計思想（Human-Centric Optimization）
本システムは、単なる技術的効率の追求ではなく、**非IT人材に対する学習コストをゼロにする**ことを最優先に設計されています。
- **摩擦ゼロのUX**: ユーザー（従業員）に求められる操作は「物理カードのタッチ」のみ。ITリテラシーの有無にかかわらず、日常の動作だけで完結します。
- **既存資産の再価値化**: 最新スペックを要求せず、Pi 2や旧型PCをエッジおよびキオスクとして活用。リソース制約を逆手に取った軽量・堅牢なアーキテクチャを採用しています。
- **構造的ガードレール**: 5分以内の重複打刻防止や15時間タイムアウト、日またぎの自動判定など、人間の不注意によるエラーをシステム側で論理的に排除します。

## システムアーキテクチャ
1. **エッジ (Pi 2)**: Sony RC-S300をPCSC経由で制御。低リソース環境下で安定したNFC UIDキャプチャを実行。
2. **ロジック**: Pythonにて状態管理、打刻異常（`missing_out`等）の検知、給与の丸め処理を実装。
3. **バックエンド (GAS)**: HTTPS APIを介してGoogleスプレッドシートへデータを同期し、マスタ管理を容易に。
4. **ダッシュボード (旧型PC)**: 慣れ親しまれたチャットUI（Discord）をキオスク化。打刻の成否をリアルタイムに現場へ視覚・聴覚フィードバックします。

## 主な機能
- **資産の最大活用**: 旧型SBCやラップトップを現役復帰させる、リソース効率の高い設計。
- **堅牢なリトライ処理**: ネットワークの不安定性に備えたAPIリトライロジックを実装。
- **柔軟なルール設定**: 従業員個別の環境変数ファイルを用いた、時給および丸め単位（分）の動的適用。

## 導入手順
- エッジデバイスの環境構築および `systemd` へのサービス登録
- GAS（Google Apps Script）のウェブアプリケーションとしてのデプロイ
- 環境変数による従業員マスタおよびWebhookの設定
</details>

## System Architecture
1. **Edge (Pi 2)**: Reliable NFC capture using Sony RC-S300 on low-resource hardware.
2. **Logic**: State management (5-min debounce, 15-hour timeouts), anomaly flagging, and rounding in Python.
3. **Backend (GAS)**: Secure synchronization to Google Sheets for master data management.
4. **Dashboard (Old Laptop)**: Real-time feedback via a Discord-based kiosk display for immediate on-site verification.

## Core Philosophy: Zero-Learning Architecture
This system is engineered to eliminate cognitive barriers for non-IT users through technical optimization:

- **Frictionless Workflow**: The user's only required action is a physical tap—no digital literacy or training needed.
- **Hardware-Software Integration**: Seamlessly connects legacy NFC hardware with a serverless backend to hide complexity.
- **Human-Centric Design**: Prioritizes the "human node" by adapting the system to natural physical behaviors rather than forcing technical learning.

## Key Features
- **Resource Optimization**: Designed to run on legacy SBCs and laptops, minimizing deployment costs.
- **Anomaly Detection**: Automatically flags missing check-outs, cross-day shifts, and duplicate scans.
- **Robust Sync**: Built-in API error handling and retry loops for network unreliability.
- **Dynamic Rules**: Employee-specific hourly rates and rounding intervals managed via isolated `.env` files.

## Getting Started
To deploy this kit to your environment, the following configuration steps are required:
- Registering Python scripts as `systemd` services on the edge device.
- Deploying Google Apps Script as a Web App.
- Configuring employee credentials and webhooks via `.env` files.

## Tech Stack
- **Language**: Python 3.12, JavaScript (GAS)
- **Infrastructure**: Linux (Systemd), Google Apps Script
- **Hardware**: Sony RC-S300/P, Raspberry Pi 2, Repurposed Laptop
