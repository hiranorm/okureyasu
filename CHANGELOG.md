# Changelog

## 0.1.0 (未公開)

- 最初の版。
- SKILL.md: 範囲（地の文だけ）、意味の4点、話し手、濃さ3段（あっさり／はんなり／こってり）、文法の芯、書いたらあかん形、いけずの約束、AIの定型の消し方、点検の順。
- references: grammar、vocabulary、pitfalls、ikezu、ai-tics、examples、sources。
- scripts/okureyasu_lint.py: 大阪弁の混入、どす・おすの誤用、はる・へんの接続、見下す言い方、東京の言い方、濃さに合わない形、AIの定型を検査する。
- evals: 13 場面の評価ケース（iteration-1 の 7 場面と、例と重ならない iteration-2 の 6 場面）。
- あっさりを「常体が中心、です・ます は頼むときと謝るときだけ」に定義し直した（試用で「丁寧語に近い、特に途中」と指摘があったため）。lint に assari-polite-run（あっさりで です・ます の文末が3文続く）を追加。
- SKILL.md 0章: 会話が要約されるとき（/compact など）に、京ことばで話していること・濃さ・いけずの設定を要約に残すよう追加。
