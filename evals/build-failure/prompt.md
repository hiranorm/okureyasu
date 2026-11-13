---
tags: [okureyasu]
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Skill]
---

京都弁で頼むわ。npm run build したらこれ出た

```
src/api/user.ts:42:7 - error TS2322: Type 'string | undefined' is not assignable to type 'string'.
  Type 'undefined' is not assignable to type 'string'.

42       name: user.displayName,
         ~~~~
Found 1 error in src/api/user.ts:42
```
