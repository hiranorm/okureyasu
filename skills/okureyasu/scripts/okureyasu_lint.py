#!/usr/bin/env python3
"""okureyasu_lint: 京ことばの文章から、京都らしくない形を拾う検査スクリプト。

コードブロック、インラインコード、URL、引用（> で始まる行）、HTML コメントは検査しない。
標準ライブラリだけで動く。

使い方:
    python3 okureyasu_lint.py [--level assari|hannari|kotteri] [--json] [--min-severity info|warn|error] FILE...
    cat out.md | python3 okureyasu_lint.py -

終了コード: error が1件でもあれば 1、なければ 0。読めないファイルがあれば 2。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

LEVELS = ("assari", "hannari", "kotteri")
SEVERITY_ORDER = {"info": 0, "warn": 1, "error": 2}

# 文の切れ目や行頭を表す後読み用の文字
BOUNDARY = r"(?:^|(?<=[。．！？!?\n「『（(、\s]))"
# 文末らしさを表す先読み
END = r"(?=$|[。．、，！？!?」』）)\s…ー〜])"


@dataclass
class Rule:
    id: str
    severity: str
    pattern: str
    message: str
    suggest: Optional[Callable[[re.Match], str]] = None
    levels: tuple = LEVELS
    exclude: tuple = ()  # 一致した前後の文脈にこれらの語があれば除外する
    flags: int = 0
    regex: re.Pattern = field(init=False)

    def __post_init__(self) -> None:
        self.regex = re.compile(self.pattern, self.flags | re.MULTILINE)


def fixed(text: str) -> Callable[[re.Match], str]:
    return lambda m: text


# 5段動詞の連用形（い段）→ 未然形（あ段）。「言いはる」→「言わはる」の提案に使う。
I_TO_A = {
    "い": "わ", "き": "か", "ぎ": "が", "し": "さ", "ち": "た",
    "に": "な", "び": "ば", "み": "ま", "り": "ら",
}

# はる が連用形に付いていたら大阪式になる5段動詞の語幹（い段まで）
GODAN_RENYO = [
    "言い", "書き", "行き", "読み", "思い", "使い", "持ち", "待ち", "聞き", "話し",
    "出し", "作り", "知り", "分かり", "わかり", "帰り", "入り", "取り", "撮り", "買い",
    "会い", "歩き", "呼び", "遊び", "頼み", "住み", "飲み", "休み", "選び", "直し",
    "探し", "押し", "消し", "返し", "動き", "置き", "開き", "届き", "続き", "変わり",
    "始まり", "困り", "走り", "送り", "払い", "手伝い", "習い", "洗い", "笑い", "通い",
    "もらい", "貰い", "やり", "渡し", "残し", "戻し", "回し", "落とし", "試し", "足し",
    "増やし", "減らし", "壊し", "隠し", "示し", "起こし", "動かし", "鳴らし", "貼り",
    "切り", "触り", "怒り", "喜び", "悩み", "急ぎ", "泳ぎ", "脱ぎ", "防ぎ", "頑張り",
    "見積もり", "繋ぎ", "つなぎ", "書き込み", "読み込み", "立ち", "勝ち", "死に",
    "なり", "あり",
]
GODAN_RENYO = [s for s in GODAN_RENYO if s[-1] in I_TO_A]


def haru_suggest(m: re.Match) -> str:
    stem = m.group("stem")
    return stem[:-1] + I_TO_A[stem[-1]] + m.group("haru")


# 「い段＋へん」で「ひん」になるべき1段動詞と、「見へん」型
HI_HEN_STEMS = [
    "起き", "落ち", "借り", "生き", "伸び", "浴び", "過ぎ", "信じ", "感じ", "閉じ",
    "でき", "足り", "降り", "用い", "飽き", "尽き", "満ち", "延び", "老い",
]

ADJ_STEMS = [
    "高", "安", "早", "速", "遅", "良", "よろし", "うれし", "嬉し", "悲し", "難し",
    "むつかし", "むずかし", "ややこし", "おいし", "美味し", "新し", "古", "長", "短",
    "多", "少な", "大き", "小さ", "重", "軽", "強", "弱", "広", "狭", "深", "浅", "寒",
    "暑", "熱", "冷た", "痛", "固", "硬", "柔らか", "細か", "危な", "面白", "楽し",
    "正し", "詳し", "珍し", "厳し", "優し", "易し", "やさし", "美し", "恥ずかし",
    "忙し", "ほし", "欲し", "な", "い", "よ", "ありがた", "すご", "凄", "ひど", "酷",
    "しんど", "えら", "怖", "こわ", "眠", "ねむ", "うるさ", "汚", "きたな", "暗",
    "明る", "赤", "青", "白", "黒", "丸", "近", "遠", "太", "細", "賢", "かしこ",
    "ずるい", "らし", "っぽ", "やす", "にく", "づら", "た",
]
ADJ_STEMS = sorted(set(ADJ_STEMS), key=len, reverse=True)


def adj_suggest(m: re.Match) -> str:
    stem = m.group("stem")
    special = {"な": "おへん（ないのどす）", "い": "よろしおす", "よ": "よろしおす", "た": "〜とうおす（〜たいのどす）"}
    if stem in special:
        return special[stem]
    if stem.endswith("し"):
        # よろしい→よろしおす、おいしい→おいしおす（しゅうおす が縮まった形）
        return f"{stem}おす／{stem}ゅうございます"
    return f"{stem}うおす／{stem}うございます（ウ音便＋おす）"


RULES: list[Rule] = [
    # ---- 大阪弁の混入（error） ----
    Rule("osaka-seya", "error",
         r"(?<![一-龥ァ-ヶさわらまかたなはばやえけてねめれせみ])せや(?=$|[なねけかでろんしさ。、！？!?\s])",
         "「せや」は大阪の形", fixed("そや")),
    Rule("osaka-keehen", "error", r"け[えー]へん|こ[おー]へん|来[えー]へん",
         "「来る」の否定は京都では「きいひん」", fixed("きいひん／きやへん")),
    Rule("osaka-nen", "error",
         r"(?<=[やるたてんいへうくすつぬむぶぐ])ねん(?=$|[。、！？!?」』）)\s…なでやかけ])",
         "「〜ねん」は大阪の形", fixed("〜ね／〜にゃ／〜んや"),
         exclude=("ざんねん", "しゅうねん", "せんねん", "ぜんねん", "らいねん", "きょねん")),
    Rule("osaka-ten", "warn",
         r"(?<=[しっいんきちみりびぎ])てん(?=$|[。、！？!?」』）)\s…]|や[。、！？!?\s]|やん)",
         "過去の「〜てん」は大阪の形", fixed("〜たんや")),
    Rule("osaka-merchant", "error",
         r"まっせ|でっせ|まんねん|まんがな|でんがな|おまへん|おます(?!る)",
         "大阪の商人言葉", fixed("〜ますえ／〜どすえ／おへん／おす")),
    Rule("osaka-nahare", "error", r"なはれ", "「なはる」の命令は京都では「なはい」",
         fixed("〜なはい／〜とくれやす")),
    Rule("osaka-amechan", "error", r"飴ちゃん|あめちゃん", "京都は「飴さん」", fixed("飴さん")),
    Rule("osaka-iteru", "warn", r"(?:^|(?<=[、。！？!?\s「が]))いて(?:る|へん)",
         "「いる」に「いる」を重ねる「いてる」は大阪の形", fixed("いる／いやはる")),
    Rule("osaka-yanke", "error", r"やんけ", "「やんけ」はぞんざいで京ことばにない", fixed("〜やんか／〜どすがな")),
    Rule("osaka-chuu", "warn", r"っちゅう", "「〜っちゅう」は大阪寄り", fixed("〜ゆう／〜いう")),
    Rule("osaka-moota", "warn", r"(?<=[てで])もう?た(?=$|[。、！？!?」わなで\s])",
         "「〜てもた／〜てもうた」は大阪寄り", fixed("〜てしもた")),
    Rule("osaka-donai", "info", r"どない|こない(?!だ)|そない|あない",
         "こない・そない・あない・どない は大阪の言葉とする資料がある", fixed("こう／そう／ああ／どう")),
    Rule("mahyo", "warn", r"まひょ", "このスキルでは「〜ましょ」に揃える（「〜まひょ」は大阪の商人言葉にも聞こえやすい）", fixed("〜ましょ")),
    Rule("maheN", "warn", r"(?<![かお])まへん",
         "このスキルでは「〜ません」「おへん」に揃える（「〜まへん」は京都でも聞かれるが、大阪の商人言葉にも聞こえやすい）", fixed("〜ません／おへん")),

    # ---- 敬語・否定の接続（error） ----
    Rule("haru-renyou", "error",
         r"(?P<stem>" + "|".join(map(re.escape, GODAN_RENYO)) + r")(?P<haru>は(?:る|った|って|ります|りま|らへん|らん|り))",
         "5段動詞の「はる」は未然形に付く（連用形に付けるのは大阪の形）", haru_suggest),
    Rule("hi-hen", "error",
         r"(?:" + "|".join(map(re.escape, HI_HEN_STEMS)) + r")へん",
         "い段の後の「へん」は「ひん」になる", fixed("〜ひん（起きひん、できひん）")),
    Rule("mi-hen", "error", r"(?<![ぁ-ん])見へん|(?<![ぁ-んい])しへん",
         "「見る」「する」の否定は「見いひん」「しいひん／せえへん」", fixed("見いひん／しいひん")),
    Rule("you-dekin", "error",
         r"よう(?:でき|読め|書け|言え|見え|行け|わかれ)(?:ん|へん|ひん)",
         "「よう〜ん」（能力・気持ち）と可能形の否定（状況）を混ぜた形", fixed("ようせん／できひん、よう読まん／読めへん")),

    # ---- どす・おす の誤用（error） ----
    Rule("adj-dosu", "error",
         r"(?P<stem>" + "|".join(map(re.escape, ADJ_STEMS)) + r")い(?:どす|どした|どして|どっしゃろ)",
         "形容詞に「どす」は付かない", adj_suggest,
         exclude=("違いどす", "間違いどす", "思いどす", "願いどす", "扱いどす", "使いどす", "手伝いどす",
                  "具合どす", "場合どす", "気遣いどす", "迷いどす", "勢いどす", "住まいどす", "支払いどす",
                  "どないどす", "どないどし", "こないどす", "そないどす", "あないどす", "どないどっ")),
    Rule("ee-dosu", "error", r"ええどす", "形容詞に「どす」は付かない", fixed("よろしおす")),
    Rule("verb-dosu", "error",
         r"(?<![のん])(?:する|ある|いる|なる|できる|れる|せる|ます|くる|わかる|分かる)どす",
         "動詞に「どす」は付かない", fixed("〜ます／〜んどす")),
    Rule("question-dosue", "warn",
         r"(?:何|なに|なん|誰|だれ|どう|どこ|いつ|どれ|どちら|なんで)どすえ",
         "疑問詞＋どす＋え は使われない", fixed("〜どす？／〜どすやろ")),

    # ---- 文頭の「や」（error） ----
    Rule("initial-ya", "error",
         BOUNDARY + r"や(?:けど|けれど|けども|さかい|から|のに|し(?=[、。]))",
         "「や」は文頭に立たない", fixed("そやけど／そやさかい／そうどすけど")),

    # ---- 見下す言い方（warn） ----
    Rule("oru-aux", "warn",
         r"[てで]お(?:る|った|らん|らへん)(?=$|[。、？！?!」よでなのんけわ\s])|(?<=[しっいんきちみりびぎえけげせてねべめれ])と(?:る|った|らん|らへん)(?=$|[。、？！?!」よでなのんけわ\s])",
         "「〜ておる／〜とる」は京都では見下す響きがある", fixed("〜てる／〜てはる")),
    Rule("oru-main", "warn",
         r"(?<=[がもにへ、])お(?:る|った|らん|らへん)(?=$|[。、？！?!」よでなのんけわ\s])",
         "本動詞の「おる」は京都では見下す響きがある（謙譲の「おります」は可）", fixed("いる／いやはる"),
         exclude=("におう", "におった", "におって")),
    Rule("yoru-aux", "warn",
         r"(?<=[しいきちみりびぎ])よる(?=$|[。、？！?!」わでなの\s])",
         "補助動詞の「〜よる」は見下す響きがある", fixed("〜てはる／〜てる")),
    Rule("command-ro", "warn",
         r"(?:見|し|寝|起き|食べ|やめ|止め|決め|調べ|確かめ|入れ|変え|考え)ろ(?=$|[。、！？!?」よ\s])",
         "命令形の「〜ろ」は京都では強すぎる", fixed("〜い（見い、せい）／〜とくれやす")),

    # ---- 東京の言い方（warn） ----
    Rule("tokyo-kke", "warn", r"っけ(?=$|[。、？！?!」\s])", "「〜っけ」は京ことばにない", fixed("〜かいな")),
    Rule("tokyo-jan", "warn", r"じゃん", "「〜じゃん」は京ことばにない", fixed("〜やんか")),
    Rule("tokyo-janai", "warn", r"じゃない", "「〜じゃない」は京ことばでは「〜やない」", fixed("〜やない／〜おへん")),
    Rule("tokyo-sa", "warn", r"(?<=[でてがのはもど])さ(?=[、。！？!?\s]|$)",
         "間投の「〜さ」は京ことばにない", fixed("〜な")),
    Rule("tokyo-da", "warn",
         r"(?<![んいでち])だ(?=$|[。！？!?」』\s])|(?<![んいでち])だ(?:から|けど|けれど|って|よ|ね)",
         "断定の「だ」は京ことばでは「や」「どす」", fixed("〜や／〜どす"),
         exclude=("まだ", "ただ", "なんだか")),
    Rule("yo-announce", "warn", r"(?:どす|ます|おす|です|や)よ(?=$|[。、！？!?」\s])",
         "告知の「よ」は共通語に聞こえる", fixed("〜え／〜で／〜な")),

    # ---- 濃さに合わない形 ----
    Rule("new-meccha", "warn", r"めっちゃ|むっちゃ|めちゃめちゃ",
         "「めっちゃ」は新しい言い方（話し手が若返る）", fixed("えらい／ものすご／ようけ"),
         levels=("hannari", "kotteri")),
    Rule("new-henkatta", "info", r"[へひ]んかった|んかった(?=$|[。、！？!?」\s])",
         "「〜へんかった」は新しい言い方", fixed("〜へなんだ／〜なんだ／〜ませなんだ"),
         levels=("hannari", "kotteri")),
    Rule("kara-reason", "info", r"(?:どす|ます|おす|です|や|そや)から(?!だ|ず)",
         "理由の「から」は京ことばでは「さかい」「し」", fixed("〜さかい／〜し"),
         levels=("hannari", "kotteri")),
    Rule("yoshi", "info", r"(?<=[きしちにびみりいえけせてねべめれ])よし(?=$|[。、！？!?」\s])",
         "「〜しよし」は昭和以降の女性の言い方で、性別を決めない話し手に合わない", fixed("〜とくれやす")),
    Rule("dosu-in-assari", "info", r"どす|おす(?!る)|おへん",
         "あっさりでは どす・おす を使わない", fixed("〜です／〜や"), levels=("assari",)),
    Rule("desu-in-kotteri", "info", r"です",
         "こってりでは名詞の後は「どす」「でございます」", fixed("〜どす／〜でございます"),
         levels=("kotteri",)),

    # ---- 人称（warn） ----
    Rule("anata", "warn", r"あなた", "「あなた」は京ことばではほとんど使わない", fixed("（主語を言わず「はる」で示す）")),
    Rule("anta", "info", r"あんた(?!はん)", "「あんた」は初対面にはなれなれしい", fixed("（主語を言わず「はる」で示す）"),
         levels=("hannari", "kotteri")),

    # ---- 意味が逆になりうる形（info） ----
    Rule("iehen", "info", r"(?:言え|書け|読め|行け|使え|待て)へん",
         "京都の「言えへん」は「言えない」の意味（大阪では「言わない」）", fixed("「〜ない」の意味なら 言わへん／書かへん")),

    # ---- AIの定型（info） ----
    Rule("ai-praise", "info", r"素晴らしい(?:ご?質問|視点|着眼点)|いい質問|ええ質問",
         "冒頭の称賛はAIの定型", fixed("（抜いて本題から）")),
    Rule("ai-closing", "info",
         r"いかがでしたか|いかがどしたか|お役に立て(?:れ)?ば幸い|お気軽に(?:お申し付け|ご質問|どうぞ|聞いて)|他に(?:何か)?(?:お手伝い|ご質問)",
         "結びの定型はAIの定型", fixed("（抜く）")),
    Rule("ai-ack", "info", r"(?:もちろんです|承知(?:いた)?しました|かしこまりました)[！!]",
         "感嘆つきの了解はAIの定型", fixed("へえ／よろしおす")),
    Rule("exclaim", "info", r"[！!]", "「！」ははんなりした声に合わない", fixed("。")),
    Rule("emoji", "info",
         r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\U0001F100-\U0001F1FF]",
         "絵文字は使わない", fixed("（抜く）")),
]

RULES_BY_ID = {r.id: r for r in RULES}


# ---------------------------------------------------------------------------
# 前処理: 検査しない部分を同じ長さの空白に置き換える（行と桁を保つ）
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
URL_RE = re.compile(r"https?://[^\s)>\]」』]+|www\.[^\s)>\]」』]+")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
LINK_TARGET_RE = re.compile(r"\]\(([^)]*)\)")


def _blank(s: str) -> str:
    return re.sub(r"[^\n]", " ", s)


def mask(text: str) -> str:
    text = HTML_COMMENT_RE.sub(lambda m: _blank(m.group(0)), text)
    out_lines = []
    in_fence = False
    fence_mark = ""
    for line in text.split("\n"):
        m = FENCE_RE.match(line)
        if in_fence:
            out_lines.append(_blank(line))
            if m and m.group(2)[0] == fence_mark[0] and len(m.group(2)) >= len(fence_mark):
                in_fence = False
            continue
        if m:
            in_fence = True
            fence_mark = m.group(2)
            out_lines.append(_blank(line))
            continue
        if line.lstrip().startswith(">"):
            out_lines.append(_blank(line))
            continue
        if line.startswith("    ") or line.startswith("\t"):
            # インデントされたコードブロックらしい行（箇条書きの続きは除く）
            stripped = line.lstrip()
            if not re.match(r"([-*+]|\d+[.)])\s", stripped):
                out_lines.append(_blank(line))
                continue
        line = INLINE_CODE_RE.sub(lambda mm: _blank(mm.group(0)), line)
        line = LINK_TARGET_RE.sub(lambda mm: "](" + _blank(mm.group(1)) + ")", line)
        line = URL_RE.sub(lambda mm: _blank(mm.group(0)), line)
        out_lines.append(line)
    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# 検査
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    path: str
    line: int
    col: int
    rule: str
    severity: str
    match: str
    message: str
    suggestion: str


def _line_col(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    last_nl = text.rfind("\n", 0, pos)
    col = pos - last_nl  # 1始まり
    return line, col


def lint_text(text: str, level: str = "hannari", path: str = "<stdin>",
              min_severity: str = "info") -> list[Finding]:
    if level not in LEVELS:
        raise ValueError(f"unknown level: {level}")
    masked = mask(text)
    findings: list[Finding] = []
    for rule in RULES:
        if level not in rule.levels:
            continue
        if SEVERITY_ORDER[rule.severity] < SEVERITY_ORDER[min_severity]:
            continue
        for m in rule.regex.finditer(masked):
            if not m.group(0).strip():
                continue
            if rule.exclude:
                window = masked[max(0, m.start() - 4): m.end() + 4]
                if any(ex in window for ex in rule.exclude):
                    continue
            line, col = _line_col(masked, m.start())
            suggestion = rule.suggest(m) if rule.suggest else ""
            findings.append(Finding(path, line, col, rule.id, rule.severity,
                                    m.group(0), rule.message, suggestion))
    if level == "assari" and SEVERITY_ORDER["warn"] >= SEVERITY_ORDER[min_severity]:
        findings.extend(_polite_runs(masked, path))
    findings.sort(key=lambda f: (f.path, f.line, f.col, -SEVERITY_ORDER[f.severity]))
    return findings


# あっさりで「です・ます」の文末が続いたら知らせる（訛った丁寧語になっている合図）
POLITE_END_RE = re.compile(r"(?:です|ます|ました|ません|でした|ましょう|ましょ|ませんか|ますか|ですか|ください|下さい)[ねよなわか]?[。！？!?]?$")
SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
POLITE_RUN = 3


def _polite_runs(masked: str, path: str) -> list[Finding]:
    out: list[Finding] = []
    run: list[re.Match] = []
    for m in SENTENCE_RE.finditer(masked):
        sent = m.group(0).strip()
        if not sent:
            continue
        if POLITE_END_RE.search(sent):
            run.append(m)
            if len(run) == POLITE_RUN:
                first = run[0]
                line, col = _line_col(masked, first.start() + (len(first.group(0)) - len(first.group(0).lstrip())))
                out.append(Finding(path, line, col, "assari-polite-run", "warn", sent[-12:],
                                   f"あっさりで「です・ます」の文末が{POLITE_RUN}文続いている（訛った丁寧語に聞こえる）",
                                   "〜や／〜わ／〜へん／〜しといた で言い切る"))
        else:
            run = []
    return out


def format_finding(f: Finding) -> str:
    sug = f" → {f.suggestion}" if f.suggestion else ""
    return f"{f.path}:{f.line}:{f.col}: [{f.severity}] {f.rule} 「{f.match}」{sug}（{f.message}）"


def main(argv: Optional[Iterable[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="京ことばの文章から京都らしくない形を拾う")
    ap.add_argument("files", nargs="+", help="検査するファイル（- で標準入力）")
    ap.add_argument("--level", choices=LEVELS, default="hannari", help="濃さ（既定: hannari）")
    ap.add_argument("--json", action="store_true", help="JSON で出力する")
    ap.add_argument("--min-severity", choices=list(SEVERITY_ORDER), default="info",
                    help="この重さ以上だけ出す（既定: info）")
    args = ap.parse_args(list(argv) if argv is not None else None)

    all_findings: list[Finding] = []
    status = 0
    for path in args.files:
        try:
            if path == "-":
                text = sys.stdin.read()
                name = "<stdin>"
            else:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                name = path
        except OSError as e:
            print(f"{path}: 読めません: {e}", file=sys.stderr)
            status = 2
            continue
        all_findings.extend(lint_text(text, args.level, name, args.min_severity))

    if args.json:
        print(json.dumps([f.__dict__ for f in all_findings], ensure_ascii=False, indent=2))
    else:
        for f in all_findings:
            print(format_finding(f))
        counts = {s: sum(1 for f in all_findings if f.severity == s) for s in ("error", "warn", "info")}
        print(f"-- error {counts['error']} / warn {counts['warn']} / info {counts['info']}（level={args.level}）",
              file=sys.stderr)

    if status:
        return status
    return 1 if any(f.severity == "error" for f in all_findings) else 0


if __name__ == "__main__":
    sys.exit(main())
