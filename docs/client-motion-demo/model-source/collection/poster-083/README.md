# Matcha Shampoo — 海报本地待审

原八图批次第5张，稳定ID预留 `poster-083`。本次仅完成一款海报预览，沿用逐款查看流程。尚未注册正式海报目录、首页或可交互模型，也未发布。

## 成稿与来源

- `matcha-shampoo-poster-v1.png`：2048 × 3072，2:3高清成稿。
- `poster-preview.jpg`：1024 × 1536会话预览。
- `blender/matcha-shampoo.blend`：本机Blender可编辑产品与灯光源文件。
- `blender/build_matcha.py`：参考图比例的产品建模、材质和渲染脚本。
- `blender/matcha-product-final.png`：2000 × 2400透明产品渲染。
- `compose_poster.py`：独立字体排版与背景/接触阴影合成。

原始第5张附件为 `807d5ed3b3a626bcaa8b9e0dce041cf9.jpg`。微信临时路径已失效，本次从本会话原始用户图片附件恢复其图像字节，未凭文字重构参考；原图保留在工作区 `outputs/20261107-Matcha-Shampoo/reference-05-matcha.jpg`，未纳入Git。来源摘要见 `source-recovery.json`。

原图的矮宽深橄榄绿瓶、近乎平坦的宽肩、奶油色圆盘短嘴泵、浅绿色棋盘格标贴及500g规格作为外观依据。品牌换为liaose，保留斜体matcha品名。单瓶为空包材，未加入料体、刷子、纸盒或其他组合；未加入功效声明。

## 制作与复查

本次成稿由本机Blender制作和渲染，Pillow精确排版，不是AI图像生成结果。Krea请求因余额不足被拒绝，Runway连接需要重新认证，均未产出图像。记录见 `production-notes.json`。

首轮复查修正了标贴与瓶身相交、产品比例偏小、矩形阴影边界，以及底部接触阴影。最终完整产品、泵头轮廓、色差、文案与页边距已按实际成稿目检，主审与独立审美复查通过；结构检查见 `poster-validation.json`。

海报渲染源已保存，但还没有制作或测试可旋转/展开的GLB。材质和尺寸均是参考图推定的展示设计，不能作为实测包装结构。

复现（本机）：

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python blender/build_matcha.py -- --final
/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 compose_poster.py --product blender/matcha-product-final.png --output matcha-shampoo-poster-v1.png
```

2026-11-11 用户批准海报发布；已完成client1.48候选，远端结果见review-evidence/matcha/client148。
