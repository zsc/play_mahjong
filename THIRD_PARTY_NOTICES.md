# Third-party notices

## mahjong-mcr-java

`ocaml/mahjong_core/lib/fan.ml` 的番组合搜索和
`tests/fixtures/mcr-81-green-book-gold.tsv` 参考并改编自
[`mahjong-mcr-java`](https://github.com/Arbousier1/mahjong-mcr-java) 2.0，
版权归 Arbousier1 所有，按 MIT License 使用。

上游 `NOTICE` 同时声明其算法改编自 GB-Mahjong：

> The scoring implementation is a Java adaptation and rewrite of algorithms from
> GB-Mahjong by Zheng Fan (Copyright (c) 2019-2020), used under the MIT License.
> The upstream project is available at https://github.com/zheng-fan/GB-Mahjong;
> the migrated reference revision is a2911ad6447f31aa17e553350f9ec5dffb7d3053.

### MIT License (mahjong-mcr-java)

Copyright (c) 2026 Arbousier1

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### MIT License (GB-Mahjong)

Copyright (c) 2019 zheng-fan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 浏览器运行时

静态发布包同时提供以下许可证原文（网页的 `licenses/` 目录；源码在 `web/public/licenses/`）：

- ONNX Runtime Web 1.30.0，Microsoft Corporation，MIT：`licenses/onnxruntime.txt`。
  来源：https://github.com/microsoft/onnxruntime/blob/v1.30.0/LICENSE
- wasm_of_ocaml / js_of_ocaml 6.5.0，LGPL 2.1 含链接例外：`licenses/wasm_of_ocaml.txt`。
  原文来自固定版本 opam 安装包。生成的 loader 的两处适配见 `web/scripts/prepare.mjs`。
- OCaml 5.5.2，LGPL 2.1 含链接例外及随附组件条款：`licenses/ocaml.txt`。
- Yojson 3.0.0，BSD：`licenses/yojson.txt`。

上述 opam 许可证原文取自本地已安装的固定版本，随静态包一起分发。
