# 予約まとめ（GitHub Actions版）

和歌山市公共施設案内・予約システムから、自分の予約日と施設名を取得し、将来的にGoogleカレンダーへ登録するための基盤です。

## 現在の状態

最初の段階では、予約サイトへログインして予約情報を取得する処理をテストモードで動かします。Googleカレンダーへの書き込みは、取得結果の確認後に有効化します。

## GitHub Secrets

認証情報はコードへ書かず、GitHubリポジトリの **Settings → Secrets and variables → Actions** に登録します。予定するSecret名は次のとおりです。

| Secret名 | 内容 |
|---|---|
| `RESERVATION_USER_ID` | 予約サイトの利用者番号 |
| `RESERVATION_PASSWORD` | 予約サイトのパスワード |
| `GOOGLE_TOKEN_JSON` | Google Calendar API OAuthトークン。設定時まで未使用 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API用。設定時まで未使用 |
| `LINE_CHANNEL_SECRET` | LINE Webhook署名検証用。設定時まで未使用 |
| `LINE_ALLOWED_USER_ID` | 指示を許可する自分のLINEユーザーID |
| `GITHUB_DISPATCH_TOKEN` | LINE中継からActionsを起動する限定権限トークン |

利用者番号、パスワード、OAuthトークン、LINEトークンは、Issue、ログ、ソースコードへ絶対に記載しないでください。

## 実行

GitHubの **Actions** タブから「予約情報の更新」を選び、`Run workflow` を押して実行します。現在は取得処理の準備段階です。

## 注意

予約サイトの利用規約上、自動取得が許可されるかを確認してから本番利用してください。サイトの画面変更により、ログイン処理や抽出処理の修正が必要になる場合があります。
