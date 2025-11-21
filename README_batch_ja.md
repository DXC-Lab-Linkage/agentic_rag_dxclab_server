# バッチ実行ガイド

このガイドでは、バッチモードで複数の質問を処理する方法について説明します。

## 基本的な使用法

```bash
python batch_exec_graph_stream.py <入力ファイル> [オプション]
```

ここで `<入力ファイル>` は、1行に1つの質問が含まれるテキストファイルです。

## コマンドラインオプション

```
  -o, --output OUTPUT    出力ファイルパス（デフォルト: 自動生成）
  -f, --format {json,csv} 出力フォーマット（デフォルト: json）
  --max-concurrent N     最大同時リクエスト数（デフォルト: 3）
  --single-chat          すべての質問に単一チャットセッションを使用
  --delay SECONDS        リクエスト間の遅延（秒）（デフォルト: 1.0）
```

## 使用例

### 基本実行
```bash
python batch_exec_graph_stream.py sample_questions.txt
```

### オプション付き
```bash
python batch_exec_graph_stream.py sample_questions.txt \
    --single-chat \
    --delay 2.0 \
    --output results.json \
    --format json
```

## 入力ファイル形式

1行に1つの質問を含むテキストファイルを作成します：

```
機械学習とは何ですか？
例を挙げてもらえますか？
従来のプログラミングとはどう違いますか？
```

## 処理モード

1. **個別チャットセッション（デフォルト）**
   - 各質問が独立して処理されます
   - 質問が互いに関連していない場合に使用します

2. **単一チャットセッション（`--single-chat`）**
   - すべての質問が同じ会話コンテキストを共有します
   - 質問が継続的な会話を形成する場合に使用します
