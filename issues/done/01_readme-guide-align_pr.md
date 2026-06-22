## 変更内容

- **Tech Stack テーブルに `Reason` 列を追加**し、行を区分ごとに分割（Python / GAS / systemd / ハードウェア / Discord それぞれの選定理由を明記）
- **Design Decisions セクションを新設**（Tech Stack の直後）: 標準ライブラリのみ採用・GAS 選択・systemd user services・ファイルベース状態管理の意図を箇条書きで記載
- **Scope セクションを新設**（Design Decisions の直後）: Focus（打刻・通知・給与計算、小規模事業所）と Out of Scope（Web UI / クラウド DB / 承認ワークフロー）を明記

## 静的確認結果

- **Markdown 構文目視確認**: 見出し階層（h2 のみ追加）・テーブル（3 列、区切り行あり）・コードブロック（既存のまま変更なし）すべて正常
- pytest: README のみ変更のため対象外
- py_compile: .py ファイル変更なし

## 検証手順

README のみの変更のため、ハードウェア・サービス動作確認は不要。

- GitHub 上で README.md のプレビューを確認し、Tech Stack テーブル・Design Decisions・Scope の表示が崩れていないことを確認する
