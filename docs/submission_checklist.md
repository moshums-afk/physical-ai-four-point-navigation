# 公開・提出前の確認

このフォルダはGitHubに載せるファイル一式です。ファイルの作成とGitHubへの公開、OmniCampusへの提出は別の工程です。

- [x] READMEの動画欄へ、本人から受領したYouTubeのURLを入れる。
- [x] OmniCampusアカウント名をID88589で確定し、指定名の提出PDFを用意する。
- [x] GitHub・YouTubeのURLをREADMEとPDFに反映する。
- [ ] 提出用PDFの本文と表示を本人が最終確認する。
- [x] GitHubのリポジトリをpublicで作成する（画面のPublic表示を確認）。
- [ ] 役割分担を明記した更新版の説明資料とREADME等をGitHubへ反映する（更新前の110ファイルは公開済み・原本との一致を確認）。
- [x] YouTubeが限定公開、再生時間が1分42秒であることを画面で確認する。
- [x] YouTubeタイトルが `PAI最終課題_ID88589` であることを動画ページで確認する。
- [ ] ログインしていない状態でもREADME・コード・PDF・動画を開けることを確認する。
- [ ] 最新の運営案内を確認し、OmniCampusにPDFとGitHub・YouTubeのURLを提出する。
- [ ] 提出日時と受付確認を手元へ保存する。

PDFは目的・工夫・結果の説明、GitHubはコードと再現手順、YouTubeは動作の提示を担当します。アカウント名はID88589で確定し、GitHub・YouTubeのURLを登録済みです。OmniCampusへ渡すPDF名は `説明資料_PAI最終課題_ID88589.pdf` です。GitHub内では同じ内容を `docs/report.pdf` に置いています。

## 公開対象

このリポジトリの中身を登録してください。上位の作業フォルダには講義資料・復旧記録等があるため、上位フォルダ全体を登録しないでください。

`evidence/` は説明用の保存記録として登録します。新しい実験の `results/`、キャッシュ、動画ファイルは `.gitignore` の対象です。YouTubeへアップロードするMP4は手元の動画フォルダで管理します。

## Gitコマンドで登録する場合

GitHubで空のpublicリポジトリを作成し、表示された実在のURLを使います。README等の初期ファイルはGitHub側で追加せず、空のリポジトリにすると手順が簡単です。

このフォルダを端末で開き、次を実行します。

```bash
git init
git add .
git status --short
git diff --cached --stat
```

登録対象を確認してからコミットします。Gitの名前・メールは公開コミットへ記録されるため、個人情報を出さない設定にしてください。GitHubのメール非公開設定と自分のnoreplyアドレスについては [GitHub公式案内](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address) を参照してください。氏名やメールは本プロジェクトのファイルには記載しません。

```bash
git commit -m "Prepare four-point navigation submission"
git branch -M main
```

続いて、GitHubの新規リポジトリ画面に表示される `git remote add origin ...` と `git push -u origin main` を、そのリポジトリのURLで実行します。認証用トークンをファイルやURLへ書き込まないでください。

ブラウザのファイルアップロードでも登録できます。ZIPだけを置くのではなく、展開したREADME・フォルダ・隠し設定ファイルを含む中身を登録すると、採点者がコードを直接読めます。
