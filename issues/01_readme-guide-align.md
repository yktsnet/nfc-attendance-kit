## README を readme-guide に準拠させる
id: 01
skill: pr-workflow
branch-slug: readme-guide-align
github_issue: 1
status: open
type: cleanup
対象: README.md
内容: Tech Stack に選定理由を追加、Design Decisions・Scope セクションを追加し、docs-agents の readme-guide 構成に揃える
確認: README.md の Markdown 構文が壊れていないこと（見出し階層・テーブル・コードブロックの閉じ）を目視確認
---
## 変更内容

### Tech Stack テーブル
既存の Tech Stack テーブルに `Reason` 列を追加する。

| 区分 | 内容 | Reason |
|-----|------|--------|
| 言語 | Python 3.11+（標準ライブラリのみ） | pip 依存ゼロで Raspberry Pi へのデプロイを簡素化 |
| 言語 | JavaScript（GAS） | Google スプレッドシートとのネイティブ連携 |
| インフラ | Linux systemd user services | root 権限不要、`loginctl enable-linger` で常駐 |
| ハードウェア | Sony RC-S300/P, Raspberry Pi 2 | 既存資産の活用。PC/SC 標準で NFC リーダーを抽象化 |
| 通知 | Discord Webhook | Bot 不要、URL 1 つで導入完了 |

### Design Decisions セクション
Tech Stack の直後に追加。以下の判断を簡潔に記載する。

- **標準ライブラリのみ**: pip install を排除し、clone → 即実行を実現。Raspberry Pi OS の Python で追加パッケージなしに動く。
- **GAS（Google Apps Script）**: 給与集計先として Google スプレッドシートを選択。専用サーバ・DB を持たず、閲覧・共有・印刷を Google 側に委譲。
- **systemd user services**: root 不要で 1 台〜複数台構成に対応。timer で日次バッチを宣言的に管理。
- **ファイルベースの状態管理（`state/`）**: DB を持たず JSON ログで打刻を永続化。バックアップは `cp` で完結。

### Scope セクション
Design Decisions の直後に追加。

**Focus:**
- NFC カードによる打刻の検知・記録・通知・給与計算
- 小規模事業所（従業員数十名以下）での運用

**Out of Scope:**
- Web UI / モバイルアプリによる打刻
- クラウド DB（PostgreSQL 等）への移行
- 勤怠の承認ワークフロー・シフト管理
