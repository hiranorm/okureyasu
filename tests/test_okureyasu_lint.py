"""okureyasu_lint の回帰テスト。標準ライブラリの unittest だけで動く（pytest でも動く）。

    python3 -m unittest discover -s tests
"""

import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.join(HERE, "..", "skills", "okureyasu", "scripts")
SCRIPT = os.path.join(SCRIPT_DIR, "okureyasu_lint.py")
sys.path.insert(0, SCRIPT_DIR)

import okureyasu_lint as lint  # noqa: E402


def rules(text, level="hannari", min_severity="info"):
    return [f.rule for f in lint.lint_text(text, level=level, min_severity=min_severity)]


class DetectsNonKyotoForms(unittest.TestCase):
    """京都らしくない形を拾うこと。"""

    cases = [
        ("せやな、そう思います。", "osaka-seya"),
        ("今日は誰もけえへん。", "osaka-keehen"),
        ("何も出てこうへんとき。", "osaka-keehen"),
        ("まだ来うへん。", "osaka-keehen"),
        ("これで動くねん。", "osaka-nen"),
        ("それでよろしいでっせ。", "osaka-merchant"),
        ("問題おまへん。", "osaka-merchant"),
        ("早よしなはれ。", "osaka-nahare"),
        ("いっしょに考えまひょか。", "mahyo"),
        ("飴ちゃんどうぞ。", "osaka-amechan"),
        ("先生がそう言いはりました。", "haru-renyou"),
        ("このコード、書きはったんどすか。", "haru-renyou"),
        ("朝は起きへんのどす。", "hi-hen"),
        ("それはできへん。", "hi-hen"),
        ("その案は高いどす。", "adj-dosu"),
        ("これはおいしいどす。", "adj-dosu"),
        ("それでええどす。", "ee-dosu"),
        ("明日も実行するどす。", "verb-dosu"),
        ("これは何どすえ？", "question-dosue"),
        ("やけど、まだ動きません。", "initial-ya"),
        ("テストは通りました。やさかい、出してよろしおす。", "initial-ya"),
        ("サーバーが動いとる。", "oru-aux"),
        ("ユーザーがおる。", "oru-main"),
        ("そんな字、ようできん。", "you-dekin"),
        ("早く見ろ。", "command-ro"),
        ("あれ、何だったっけ？", "tokyo-kke"),
        ("簡単じゃん。", "tokyo-jan"),
        ("これはバグだ。", "tokyo-da"),
        ("そうどすよ。", "yo-announce"),
        ("あなたのコードどす。", "anata"),
        ("素晴らしい質問どすなあ。", "ai-praise"),
        ("いかがでしたか。", "ai-closing"),
        ("ありがとうございます！", "exclaim"),
    ]

    def test_cases(self):
        for text, expected in self.cases:
            with self.subTest(text=text):
                self.assertIn(expected, rules(text), f"{text} で {expected} を拾うはず")

    def test_haru_suggestion(self):
        f = [x for x in lint.lint_text("そう言いはった。") if x.rule == "haru-renyou"][0]
        self.assertEqual(f.suggestion, "言わはった")
        f = [x for x in lint.lint_text("よう使いはる。") if x.rule == "haru-renyou"][0]
        self.assertEqual(f.suggestion, "使わはる")

    def test_level_specific(self):
        self.assertIn("new-meccha", rules("めっちゃ速うなりました。", level="hannari"))
        self.assertNotIn("new-meccha", rules("めっちゃ速なった。", level="assari"))
        self.assertIn("dosu-in-assari", rules("そうどす。", level="assari"))
        self.assertIn("desu-in-kotteri", rules("そうです。", level="kotteri"))
        self.assertIn("new-henkatta", rules("動かへんかった。", level="hannari"))
        self.assertNotIn("new-henkatta", rules("動かへんかった。", level="assari"))

    def test_assari_polite_run(self):
        polite = "原因は設定です。直しておきました。もう一度動かしてみてください。テストも通りました。"
        self.assertIn("assari-polite-run", rules(polite, level="assari"))
        self.assertNotIn("assari-polite-run", rules(polite, level="hannari"))
        casual = "原因は設定やわ。直しといた。もういっぺん動かしてみて。テストも通りました。"
        self.assertNotIn("assari-polite-run", rules(casual, level="assari"))


class AcceptsKyotoForms(unittest.TestCase):
    """正しい京ことばを拾わないこと（誤検出の回帰）。"""

    good = [
        "担当しております。",
        "それはたいへんどしたなあ。",
        "画面が狭うて見えへん。",
        "朝早う起きはる方どす。",
        "決めはったとおりにしときました。",
        "それは違いどす。",
        "間違いおへん。",
        "ほんまかいな。",
        "そやかて、急には無理どす。",
        "でけへんもんは、でけへん。",
        "そやけど、まだ動きません。",
        "高うおす。よろしおす。むつかしおす。",
        "言わはった。書かはる。使わはった。行かはる。",
        "見いひん。いいひん。きいひん。しいひん。起きひん。",
        "何も出てきいひんときは、向こうへんに置いといて。",
        "まだ終わってへん。",
        "そう言わはっても、ようせんのどす。",
        "直しときましたさかい、もういっぺん動かしてみとくれやす。",
        "何してんの？",
        "えらい混んでんなあ。",
        "読んだ。泳いだ。",
        "残念やけど、今回は見送ります。",
        "においがしますなあ。",
        "それは私のや。",
        "ほな、見てみましょ。",
        "どないどした？",  # どない は info だが adj-dosu の誤検出をしない
        "このテスト、いつ流しても緑どすなあ。",
        "かまへんよ、の「よ」も京都ではあまり言いまへん",  # まへん は warn だが error ではない
    ]

    def test_no_errors(self):
        for text in self.good:
            with self.subTest(text=text):
                errs = [f for f in lint.lint_text(text, min_severity="error")]
                self.assertEqual(errs, [], f"{text}: {[lint.format_finding(e) for e in errs]}")

    def test_no_warnings_for_clean_prose(self):
        clean = [t for t in self.good if "まへん" not in t and "どない" not in t]
        for text in clean:
            with self.subTest(text=text):
                warns = [f for f in lint.lint_text(text, min_severity="warn")]
                self.assertEqual(warns, [], f"{text}: {[lint.format_finding(w) for w in warns]}")


class SkipsNonProse(unittest.TestCase):
    """コード、URL、引用を検査しないこと。"""

    def test_code_fence(self):
        text = "直しときました。\n\n```python\n# せやな、ねん、高いどす\nx = 1\n```\n"
        self.assertEqual(rules(text, min_severity="warn"), [])

    def test_tilde_fence(self):
        text = "~~~\nせやねん\n~~~\nよろしおす。"
        self.assertEqual(rules(text, min_severity="warn"), [])

    def test_inline_code(self):
        self.assertEqual(rules("`せやねん` いう名前の関数どす。", min_severity="warn"), [])

    def test_url(self):
        self.assertEqual(rules("詳しゅうは https://example.com/seya/nen/だ を見とくれやす。", min_severity="warn"), [])

    def test_blockquote(self):
        self.assertEqual(rules("> せやねん、これはバグだ\n\n上の発言のとおりどす。", min_severity="warn"), [])

    def test_link_target(self):
        self.assertEqual(rules("[資料](./せや/ねん.md)を見とくれやす。", min_severity="warn"), [])

    def test_line_numbers_kept(self):
        text = "```\nfoo\n```\nせやな。"
        f = lint.lint_text(text)[0]
        self.assertEqual((f.line, f.col), (4, 1))


class Cli(unittest.TestCase):
    def run_cli(self, *args, stdin=""):
        return subprocess.run([sys.executable, "-I", SCRIPT, *args], input=stdin,
                              capture_output=True, text=True, encoding="utf-8")

    def test_exit_code_error(self):
        r = self.run_cli("-", stdin="せやねん。")
        self.assertEqual(r.returncode, 1)
        self.assertIn("osaka-seya", r.stdout)

    def test_exit_code_clean(self):
        r = self.run_cli("-", stdin="よろしおす。")
        self.assertEqual(r.returncode, 0)

    def test_json(self):
        import json
        r = self.run_cli("--json", "-", stdin="高いどす。")
        data = json.loads(r.stdout)
        self.assertEqual(data[0]["rule"], "adj-dosu")

    def test_missing_file(self):
        r = self.run_cli("does-not-exist.md")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
