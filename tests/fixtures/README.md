# MCR scoring fixtures

## `mcr-81-green-book-gold.tsv`

- 来源：`mahjong-mcr-java` 2.0，`src/test/resources/mcr-81-green-book-gold.tsv`。
- 上游仓库：<https://github.com/Arbousier1/mahjong-mcr-java>
- 固定版本：提交 `Arbousier1/mahjong-mcr-java@2.0` 中随附文件，SHA-256 为
  `a03e1d251e8dc10bf1a88517b8605a6c47afb981ffd3719fd58746c813c6efe7`。
- 许可证：MIT；原始版权声明和上游 NOTICE 见仓库根目录的 `THIRD_PARTY_NOTICES.md`。
- 规范依据：WMO 2006 *Mahjong Competition Rules (Green Book)*，详见
  `docs/rules.md`。

该文件是上游仓库作者编写的 81 个计番元素的正向样例，不是 WMO 官方发布
的测试集。项目用它做第三方交叉校验；遇到与本项目规则解释不一致时，以
Green Book 原文为准，并在 `docs/rules.md` 记录裁定。

`SHUANGJIANKE` 样例只含 7 个可计番分，因此其和牌形成立，但不满足 MCR
8 番起和门槛。测试同时检查番种识别与门槛，不把它当作可宣布和牌的对局。
