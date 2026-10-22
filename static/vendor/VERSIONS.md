# Vendored front-end libraries

These files are committed so that the app works fully offline (NFR-004, AD-02).
Do **not** replace them with CDN references. Do not edit them by hand.

| File | Library | Version | Source file in package | License |
|---|---|---|---|---|
| `alpine.min.js` | Alpine.js | 3.17.4 | `alpinejs@3.17.4/dist/cdn.min.js` | MIT |
| `chart.umd.min.js` | Chart.js | 4.5.1 | `chart.js@4.5.1/dist/chart.umd.min.js` | MIT |
| `pico.min.css` | Pico CSS | 2.1.1 | `@picocss/pico@2.1.1/css/pico.min.css` | MIT |

## Provenance

Downloaded on 2026-10-23 from the official npm registry tarballs.
The tarball integrity was checked against the `dist.integrity` value published by the registry.

| Package | Tarball | npm integrity (sha512) |
|---|---|---|
| alpinejs 3.17.4 | https://registry.npmjs.org/alpinejs/-/alpinejs-3.17.4.tgz | `sha512-N2gsr+58XVUt7OAPKnUGiKPDtkd+xbSGTae8C8IJxeRdkkhBJPIautkJ+qcwb7lcjJ/QK3/CPVIbN20JPvtK7A==` |
| chart.js 4.5.1 | https://registry.npmjs.org/chart.js/-/chart.js-4.5.1.tgz | `sha512-GIjfiT9dbmHRiYi6Nl2yFCq7kkwdkp1W/lp2J99rX0yo9tgJGn3lKQATztIjb5tVtevcBtIdICNWqlq5+E8/Pw==` |
| @picocss/pico 2.1.1 | https://registry.npmjs.org/@picocss/pico/-/pico-2.1.1.tgz | `sha512-kIDugA7Ps4U+2BHxiNHmvgPIQDWPDU4IeU6TNRdvXQM1uZX+FibqDQT2xUOnnO2yq/LUHcwnGlu1hvf4KfXnMg==` |

SHA-256 of the vendored files (verify with `shasum -a 256 static/vendor/*.min.*`):

```
232519394c6c8fdba6f362b1d9da16106db513cdbf899011f00daab4051df31c  alpine.min.js
48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a  chart.umd.min.js
fbc9a63fc9fc9f72d12fd7fc9806e11fa9f77ae4f9cad146b27003a1119ba3db  pico.min.css
```

## Version selection notes

- At the time of vendoring, npm `latest` was alpinejs 3.17.5 (published 2026-10-20) and chart.js 4.6.1 (published 2026-10-22).
  The previous stable releases were chosen instead, because releases only a few days old have no track record yet.
  The chart.js 4.6.x line also had no 4.6.0 visible on npm.
  The features used here (Alpine `x-data` / `x-show` / stores, Chart.js `pie` / `bar`) are the same in both lines.
- Alpine.js is the script-tag build (`cdn.min.js`), and Chart.js is the UMD build.
  The Chart.js ESM build imports `@kurkle/color` by bare specifier, which needs a bundler or an import map (AD-02).
- `chart.umd.min.js` ends with a `sourceMappingURL` comment. The `.map` file is intentionally not vendored.
  Only browser devtools request it; the app does not.
- No vendored file loads remote resources at runtime. Pico uses inline `data:` SVG icons only.

## Licenses

### Alpine.js — MIT License

Copyright © 2019-2025 Caleb Porzio and contributors

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

### Chart.js — The MIT License (MIT)

Copyright (c) 2014-2024 Chart.js Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Pico CSS — MIT License

Copyright (c) 2019-2024 Pico

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
