---
tags: [okureyasu]
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Skill]
---

（ここまでの会話）

利用者: Docker のイメージが大きすぎる。どうしたら小さくなる？

アシスタント: イメージを小さくする方法は主に4つあります。
1. マルチステージビルドを使い、ビルドに必要なツールを最終イメージに含めない。
2. ベースイメージを `python:3.12-slim` や `alpine` のような小さいものにする。
3. `.dockerignore` で `node_modules` や `.git` をビルドコンテキストから外す。
4. `RUN apt-get update && apt-get install -y ... && rm -rf /var/lib/apt/lists/*` のように、インストールと後片付けを同じ RUN にまとめる。
この4つで、500MB 以上あったイメージが 100MB 台になることもよくあります。

利用者: /okureyasu
