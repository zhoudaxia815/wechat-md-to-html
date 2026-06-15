# 微信公众号 Markdown → HTML 转换器

一键将 Markdown 文章转为微信公众号兼容 HTML（全内联样式，移动端不丢格式）。

## 用法

```bash
python wechat_md_to_html.py input.md output.html
```

## 功能

- 全部样式内联 style="" ，微信移动端不剥离
- 自动识别并格式化：引用块、提示词块、行动块、互动钩子、表格
- 零 CSS class、零 style 块、零 div

## 示例

```bash
python wechat_md_to_html.py 文章1_初稿.md 文章1_发布版.html
# → 复制 HTML 内容 → 粘贴到公众号后台 → 发布
```

