# prcb-checks
![icon](../images/icon_small.png)

[English Documentation is here](README_en.md)

prcb-checks は、AWS CodeBuild が GitHub から AWS CodeConnections 経由で実行される際に GitHub Checks API を呼び出すためのヘルパーコマンドです。

## インストール方法

```
pip install prcb-checks
```

開発モードでインストールする場合は以下を使用します：

```
pip install -e ".[dev]"
```

## 前提条件

prcb-checks を使用するには以下が必要です：

1. 適切な権限を持つ GitHub App の作成：
   - Checks: 読み取り & 書き込み

2. GitHub リポジトリにアプリをインストール

3. GitHub App の秘密鍵を AWS Secrets Manager に保存

4. GitHub リポジトリと連携する AWS CodeBuild プロジェクト

## 必要な環境変数

prcb-checks には以下の環境変数が必要です：

| 変数名 | 説明 |
|----------|-------------|
| GITHUB_APP_ID | GitHub App の ID |
| GITHUB_APP_INSTALLATION_ID | GitHub App のインストール ID |
| SECRETS_MANAGER_SECRETID | GitHub App の秘密鍵を含む AWS Secrets Manager のシークレット ID |
| AWS_REGION | Secrets Manager の AWS リージョン |
| CODEBUILD_RESOLVED_SOURCE_VERSION | Git コミット SHA (CodeBuild によって自動設定) |
| CODEBUILD_INITIATOR | CodeBuild のトリガーソース (CodeBuild によって自動設定) |
| CODEBUILD_SRC_DIR | ソースディレクトリ (GitHub からトリガーされたビルド用) |
| CODEPIPELINE_FULL_REPOSITORY_NAME | 完全なリポジトリ名 (CodePipeline からトリガーされたビルド用) |

## 使用方法

基本的なコマンド構造：

```
prcb-checks <name> [status] [conclusion] [title] [summary] [text]
```

### コマンドライン引数

| 引数 | 必須 | 説明 |
|----------|----------|-------------|
| name | はい | チェックの名前。例: "code-coverage" |
| status | いいえ | チェック実行の現在の状態。オプション: queued, in_progress, completed, waiting, requested, pending。デフォルト: queued |
| conclusion | いいえ | チェックの最終結論 (status が completed の場合は必須)。オプション: action_required, cancelled, failure, neutral, success, skipped, timed_out |
| title | いいえ | チェック実行のタイトル |
| summary | いいえ | チェック実行の要約 (Markdown 形式対応) |
| text | いいえ | チェック実行の詳細 (Markdown 形式対応) |

### オプション

| オプション | 説明 |
|--------|-------------|
| -d, --debug | 詳細な出力を含むデバッグモードを有効にする |

### 高度な使用方法

#### ファイルからのテキスト読み込み

テキストが長い場合、`file://` プレフィックスを使用してファイルを参照できます：

```
prcb-checks "Lint Report" completed failure "Lint Errors" "問題が見つかりました" file:///path/to/report.txt
```

これにより `/path/to/report.txt` の内容を読み込み、text パラメータとして使用します。

## AWS CodeBuild との連携

### 基本的なセットアップ

1. GitHub App を作成し、リポジトリにインストールする
2. 秘密鍵を AWS Secrets Manager に保存する
3. 必要な環境変数を CodeBuild プロジェクトに追加する
4. buildspec.yml に prcb-checks コマンドを含める

### buildspec.yml の例

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install prcb-checks
  
  pre_build:
    commands:
      - prcb-checks "ビルドチェック" in_progress

  build:
    commands:
      - echo "ビルドステップの実行中..."
      # ビルドコマンドをここに記述
      
  post_build:
    commands:
      - |
        if [ $CODEBUILD_BUILD_SUCCEEDING -eq 1 ]; then
          prcb-checks "ビルドチェック" completed success "ビルド成功" "ビルドは正常に完了しました。"
        else
          prcb-checks "ビルドチェック" completed failure "ビルド失敗" "ビルド中にエラーが発生しました。"
        fi
```

### CodePipeline 連携

CodePipeline と共に使用する場合、`CODEPIPELINE_FULL_REPOSITORY_NAME` 環境変数が正しく設定されていることを確認してください。このツールは CodePipeline からの実行か直接 CodeBuild からの実行かを自動的に検出し、それに応じてリポジトリ情報を取得します。

## 開発

### インストール

```
pip install -e ".[dev]"
```

### テストの実行

開発モードでインストールした後、以下のコマンドでテストを実行できます：

```
pytest
```

カバレッジレポートを生成するには：

```
pytest --cov=prcb_checks --cov-report=term-missing
```

### ビルド

```
python -m build
```

## GitHub Checks API 連携

prcb-checks は GitHub Check Runs を API 経由で作成するプロセスを簡素化します。このツールは以下を処理します：

1. GitHub App を使用した GitHub API との認証
2. AWS Secrets Manager からの秘密鍵の取得
3. GitHub API 認証用の JWT トークンの作成
4. GitHub Checks API へのチェック情報の送信

GitHub Checks API の詳細については、[GitHub のドキュメント](https://docs.github.com/ja/rest/checks/runs)を参照してください。