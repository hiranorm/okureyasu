---
tags: [okureyasu]
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Skill]
---

京ことばでこのコードレビューして。

```python
def proc(d):
    r = []
    for i in range(len(d)):
        if d[i]['s'] == 1 and d[i]['p'] > 0 and d[i]['p'] < 99999:
            x = d[i]['p'] * 1.1
            x = int(x)
            r.append({'id': d[i]['id'], 'p': x, 's': d[i]['s']})
    return r
```
