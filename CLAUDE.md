# okureyasu（おくれやす）

AI の話し言葉を京ことば（京都弁）に仕立てる Agent Skill。[yomiyasu](https://github.com/nanaism/yomiyasu) のカウンタースキルとして、AI らしさを「引き算」ではなく「人の声を足す」方向で消す。京都らしいいけずは一滴だけ残し、愛される話し口調に仕上げる。

公開先: <https://github.com/hiranorm/okureyasu>（`npx skills add hiranorm/okureyasu`）

## 技術スタック

- Agent Skills 形式（`SKILL.md` + `references/` + `scripts/`）。仕様: <https://agentskills.io/specification>
- 検査スクリプトは Python 3 の標準ライブラリだけ（形態素解析なし）
- テストは `unittest`（`python3 -m unittest discover -s tests`）
- 配布: `npx skills add`（skills CLI）、Claude Code プラグイン（`.claude-plugin/`）

## ディレクトリ構成

```
skills/okureyasu/        スキル本体。配布されるのはここだけ
  SKILL.md               芯の規則（範囲、濃さ、文法の芯、NG 一覧、いけず、定型、点検）
  references/            詳細（grammar / vocabulary / pitfalls / ikezu / ai-tics / examples / sources）
  scripts/okureyasu_lint.py  京都らしくない形の検査
tests/                   検査スクリプトの回帰テスト
evals/                   評価ケース（skill-creator のケース形式）
docs/                    concept.md / design.md
.claude-plugin/          plugin.json / marketplace.json
```

`okureyasu-workspace/`（評価の実行結果）は `.gitignore` で除外している。

## 設計思想・運用ルール

- **包むのは物言い、中身は包まへん**。京ことばにするのは利用者に話しかける地の文だけ。コード、数値、引用、専門用語、ファイルに書くものは標準のまま。婉曲で確度を下げない。
- **SKILL.md 本体に芯の規則を置く**。話し方のスキルは毎ターン効く必要があるため、references は詳細だけ。SKILL.md は 500 行以内。
- **京ことばの正しさ**は「京言葉」サイト（akenotsuki.com/kyookotoba/）に拠る。サイトは非商用条件の転載許可なので、本文や表は写さず、事実を自分の言葉でまとめ、例文は自作する（リポジトリは MIT）。
- **NG 一覧と lint を揃える**。SKILL.md 5章の表に形を足したら、`okureyasu_lint.py` のルールとテスト（検出する例・誤検出しない例）も足す。
- **誤検出の確認**: lint を変えたら、正しい京ことばの文（サイトの「京ことばつれづれ帳」など）にかけて 0 件を確かめる。
- バージョンは `SKILL.md` の `metadata.version`、`.claude-plugin/plugin.json`、`marketplace.json` の3か所を揃える。変更は `CHANGELOG.md` に書く。

## 評価

- ケースは `evals/<case>/`（prompt.md、case.yaml、graders/）。skill-creator のケース形式に合わせている（`claude plugin eval` で読めるかは未確認。読ませるならスキル配下へ移す必要があるかもしれない）。
- 手で回すときは、スキルあり／なしのサブエージェントで各ケースを走らせ、結果を `okureyasu-workspace/iteration-N/` に置く。lint の error 件数と graders の各項目で比べる。
- 結果の要約は `docs/evaluation.md`。

## 公開手順

1. `python3 -m unittest discover -s tests` が通ることを確かめる。
2. バージョンを揃えて `CHANGELOG.md` を書く。
3. コミットして `main` に push。タグ `vX.Y.Z` を打って GitHub Release を作る。
4. ワークスペース側で `git add okureyasu` してサブモジュールの参照を更新する。

## ドキュメント索引

- [docs/concept.md](docs/concept.md) — なぜ京ことばか、yomiyasu との対比、目指す話し手
- [docs/design.md](docs/design.md) — 構成と設計判断
- [docs/evaluation.md](docs/evaluation.md) — 評価の結果
- [skills/okureyasu/SKILL.md](skills/okureyasu/SKILL.md) — スキル本体

## このプロジェクトのルール

- **タスク管理は Backlog.md を使わない**（ワークスペース規約からの意図的な逸脱）。スキルは文書とスクリプトだけで、公開リポジトリにボードは要らないため。公開後のタスクと指摘は GitHub Issues で受ける。
- **README.md** は外向けの入口（インストールと使い方、末尾に作者のアプリ群へのリンク1本）。ワークスペース規約の「最小入口」より厚いのは、公開スキルとして入れ方と使い方が要るため。
- **ドキュメントの一次情報は本ファイル（CLAUDE.md）と `docs/`**。README と内容を重複させない。
