# 精选包材模型：源文件与本地复建

本轮新增 14 款按原海报逐款校准的专用模型，并接入 24 款精选产品总览。**新增批次仅供本地预览；本目录的复建、接入和总览命令都不部署 production。** 既有款式的发布状态以独立发布记录为准。

## 稳定 ID 与参考依据

`poster-XXX` 沿用原海报 ID，用于源目录、GLB、客户端配置和总览状态的关联；不得按显示顺序重新编号。产品名称可修订，ID 保持不变。

以下路径均相对仓库根目录：

- 完整原海报：`docs/mobile-client-preview/assets/posters/poster-XXX.webp`。
- 精选抠图：`docs/client-motion-demo/featured-assets/poster-XXX.png`。抠图只作辅助，不能将透视侧面或裁切宽度直接当成瓶身正面宽度。
- 单款源文件：本目录下的 `poster-XXX/`，包括 `.blend`、可编辑 SVG、嵌入贴图、`model-info.json` 和 `review-config.json`。
- 导出模型：`docs/client-motion-demo/packaging-assets/poster-XXX.glb`。

模型表达的是海报可见外观。真实毫米尺寸、瓶壁厚度、隐藏连接、泵芯和密封结构均由图片推定，不能据此认定真实材料牌号、工艺或制造规格。展示高度约归一到 **2.9 个场景单位**；具体比例与实际包络见各款 `model-info.json`，该数值不是实物尺寸。

保留空包材，排除料液、泡沫、悬滴及背景道具；`poster-065` 的补充袋属于包装本体，随瓶保留。`PaperLabel` 只含无字纸标、膜或装饰底材，`LogoPrint` 包含品牌、完整产品名、容量及分隔线。原图没有纸标边界时使用透明载体示意。完整印刷单独向外展开，其前移距离必须大于标贴，回零恢复闭合排版。

## 本轮 14 个专用 builder

`build_product.py` 的 `REVIEWED_GENERATORS` 按稳定 ID 分派到下列脚本，不使用旧通用草稿轮廓替代专用模型。

| ID | 产品 | 专用脚本 |
| --- | --- | --- |
| poster-013 | Coral & Aqua | `build_coral_aqua.py` |
| poster-058 | Luminous Face Oil | `build_luminous_face_oil.py` |
| poster-059 | Essence Oil Duo | `build_essence_oil_duo.py` |
| poster-060 | AHA Body Mist | `build_aha_body_mist.py` |
| poster-061 | Oil-Infused Body Cream | `build_oil_infused_body_cream.py` |
| poster-062 | Micro Cream | `build_micro_cream.py` |
| poster-063 | Moisture Cream | `build_rich_moisture_cream.py` |
| poster-064 | Aromatic Body Lotion | `build_aromatic_body_lotion.py` |
| poster-065 | Tea Tree Shampoo | `build_tea_tree_shampoo.py` |
| poster-066 | Rose Hair Oil | `build_rose_hair_oil.py` |
| poster-067 | Amber Ginger Shampoo | `build_ginger_shampoo.py` |
| poster-068 | Essence Water | `build_essence_water.py` |
| poster-069 | Still Essential Oil | `build_still_essential_oil.py` |
| poster-070 | Daylight Essential Oil | `build_daylight_essential_oil.py` |

复建需保留配套依赖：

- `build_micro_cream.py` 同时提供 013、063、064、065 的纯建模与贴图 helper；品牌路径来自 `poster-039/print.svg`。
- `tail_model_helpers.py` 服务 066–070，读取各款已有 `print.svg` 的品牌路径。
- 058–061 也会读取本款已有 `print.svg`；不要先清空单款源目录再运行。保留 SVG、纸张、软木和法线等配套贴图。
- 使用 Blender 4.5 系列的 `bpy`、`bmesh`、`mathutils`；部分脚本依赖 Blender 自带 NumPy。SVG 栅格化调用 Node.js 与 Sharp，并使用本机字体。脚本当前记录了 Codex 运行时的绝对路径，迁移电脑时须同步检查这些路径及字体，避免排版漂移。

## Woodland 整盖简化修订

2026-10-26：poster-042新增单位变换CapAssembly，保留Closure与StopperInsert原变换并整体移动；8网格世界坐标和原材质/贴图完全相同。四组为CapAssembly、Body、PaperLabel、LogoPrint；沿用原Woodland专属场景，不新增review配置。整体升降1.20，全开相机中心2.05、视高5.1，纸标和完整印刷继续独立外展。仅本地待审，当前停在05；06尚未开始。04 Moisture已获批并单独发布client1.23，正式证据提交ea6fa9d4。

## Moisture Shampoo 整泵简化修订

2026-10-26：poster-049 将原Closure、PumpStem、Actuator嵌套进PumpAssembly，保持闭合世界坐标。纸标与完整印刷独立，空瓶几何、材质和贴图不变。本款沿用原Moisture专属场景分支，不新增review配置；整体位移及取景由packaging-scene.js维护。仅本地待审，按用户选单先做04，确认后才继续05。

## Daylight 整盖简化修订

2026-10-26：poster-070 的压纹套纸与右侧延伸边并入 Closure，连同金属盖与内侧密封件整体移动。四个展示组为 Closure、Body、PaperLabel、LogoPrint；本次四组修订仅本地待审，正式线上原五组状态以独立发布记录为准。生成器保持原几何/贴图，标贴与完整印刷外展不变。

## 单款复建与接入

在本机仓库根目录执行，以 065 为例。复建会覆盖该款生成文件；GLB 成功生成后再接入本地客户端。

```sh
cd /Users/icecream/Documents/Codex/2026-10-22/gen/work/client18

/Applications/Blender.app/Contents/MacOS/Blender \
  --background --python-exit-code 1 \
  --python docs/client-motion-demo/model-source/collection/build_product.py \
  -- poster-065

/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -B -m unittest discover -s tests -p 'test_tea_tree_shampoo_model.py' -v

/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -B scripts/integrate_reviewed_models.py poster-065
```

`--python-exit-code 1` 使 Blender 脚本异常返回失败，不能只凭“Blender quit”判断成功。更换产品时同时更换稳定 ID 和对应测试文件。测试检查实际导出几何、材质或贴图；之后还需在浏览器对照原图检查闭合、半展、全展、旋转和手机视口。

`review-config.json` 保存 `parts` 双语部件文案、`appearance` 材质提示、`explosion` 位移/缩放/旋转/时序及相机参数。与生成器内的配置同步修改，避免下次重建覆盖调整。

接入脚本校验部件节点、空包材标记及文字前移关系，更新 `src/structure/collection-products.json` 和 `packaging-manifest.json` 中该款的组件、字节数、SHA-256，再复制 GLB 到 `public/assets/packaging/`。它不会自动完成视觉验收、修改总览完成状态或发布服务器。

## 24 款统一预览的维护

总览由 `scripts/build_model_review.py` 生成，产品顺序和名称读取 `docs/client-motion-demo/src/featured.json`，海报链接读取 `src/posters.json`，状态读取 `docs/client-motion-demo/model-review-status.json`。

单款核验后，在状态文件对应 ID 下维护 `state`、`components`，以及可选的 `screenshots.closed`、`screenshots.open`、`background`。截图路径应能由本地客户端访问。`working` 表示制作中，`complete` 表示完成本地预览；只有已有独立发布依据的产品才使用 `published`。缺少状态或截图时，生成器会回退到制作中或原海报。

```sh
/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -B scripts/build_model_review.py
```

输出为 `docs/client-motion-demo/public/model-review.html`，样式和交互分别位于同一 `public/` 下的 `model-review.css`、`model-review.js`。通过运行中的本地客户端访问 `/model-review.html`，单款地址为 `/?model=poster-065`；不要用直接打开 HTML 文件代替 HTTP 预览。总览状态是维护记录，生成页面本身不代表模型已验收或已上线。
