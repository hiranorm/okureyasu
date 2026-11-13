---
tags: [okureyasu]
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Skill]
---

京ことばで、何が起きてるか教えて。

```
$ pytest -q
..F.....F.
FAILED tests/test_price.py::test_tax_included - assert 1080 == 1100
FAILED tests/test_price.py::test_round_half - assert 104 == 105
2 failed, 8 passed in 0.31s
```
