# 设计参考

- 用户打开的 [iOS and iPadOS 27 (Community)](https://www.figma.com/design/zBPZSmrQxYuv50yaY1hfZF/iOS-and-iPadOS-27--Community-?node-id=10403-2)：只读查看 Materials 内的 Liquid Glass 和 Scroll Edge Effect，未修改 Figma 文件。此页面为社区文件，不据此断言官方系统版本或技术实现。
- [Apple HIG · Typography](https://developer.apple.com/design/human-interface-guidelines/typography)：系统字体、明确层级、阅读清晰度。页面使用 CSS 系统字体栈；不同操作系统使用各自可用字体，没有分发 SF 字体。
- [Apple HIG · Materials](https://developer.apple.com/design/human-interface-guidelines/materials)：材质主要服务导航和控件层级；海报内容保持清晰。
- [React Bits · Circular Gallery](https://reactbits.dev/components/circular-gallery)：参考逐张浏览、侧面可见邻图和直接打开图片的路径。
- [React Bits · Accordion Gallery](https://reactbits.dev/components/accordion-gallery)：参考悬停/聚焦与内容层级，未采用默认裁切或灰度处理。
- [React Bits · Stack](https://reactbits.dev/components/stack)：考察叠卡交互；本版采用更直接的左右浏览。

本版没有集成上述 React Bits 源码。后续如果直接复用，需保留其 [MIT + Commons Clause](https://github.com/DavidHDev/react-bits/blob/main/LICENSE.md) 许可说明并再检查实际依赖与性能。

本轮使用 Impeccable 做目标与布局探索、Design Taste Frontend 做视觉检查，参考 React 性能指南限制同时显示的主海报数量。实际素材均为既有客户展厅批准海报。
