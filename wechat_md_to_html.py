#!/usr/bin/env python3
"""
Markdown → 微信公众号兼容 HTML 转换器

用法: python wechat_md_to_html.py input.md [output.html]

规则：
- 全部样式写入内联 style="..."，不使用 <style> 块和 CSS class
- 只用微信移动端可靠的元素：p, h2, blockquote, pre, strong, table, span
- 避免 div, section (样式会被微信剥离)
- 避免 border-radius (微信不支持)
"""

import re
import sys
import os

# ═══════════════════════════════════════
# 样式定义（全部内联）
# ═══════════════════════════════════════

STYLES = {
    "body": "max-width:680px;margin:0 auto;padding:20px 16px 40px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:16px;line-height:1.85;color:#333;background:#fff;",
    "h2": "font-size:18px;margin:32px 0 12px;color:#1a1a1a;font-weight:700;",
    "p": "margin:0 0 16px;",
    "hr": "border:none;border-top:1px solid #eee;margin:28px 0;",
    "blockquote": "margin:12px 0;padding:12px 16px;background-color:#f8f9fa;border-left:3px solid #e0e0e0;color:#555;font-size:15px;line-height:1.75;",
    "pre": "margin:16px 0;padding:14px 16px;background-color:#f5f7fa;font-size:14px;line-height:1.7;color:#333;border:1px solid #e8ecf1;white-space:pre-wrap;word-break:break-all;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;",
    "strong": "color:#1a1a1a;",
    "highlight": "background-color:#fff3cd;padding:2px 6px;",
    "action_block": "background-color:#f0f7ff;border-left:3px solid #5fa8d0;padding:16px 20px;margin:24px 0;",
    "action_p": "margin:0;color:#333;",
    "interaction": "margin-top:32px;padding:16px;background-color:#fafafa;text-align:center;font-size:15px;color:#666;",
    "table": "width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;",
    "th": "border:1px solid #e0e0e0;padding:10px 12px;text-align:left;background-color:#f5f7fa;font-weight:600;color:#555;",
    "td": "border:1px solid #e0e0e0;padding:10px 12px;text-align:left;color:#333;",
    "img_note": "text-align:center;color:#999;font-size:14px;",
}

HTML_WRAPPER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="{body_style}">
{content}
</body>
</html>"""

# ═══════════════════════════════════════
# 行内元素转换
# ═══════════════════════════════════════

def inline_process(text):
    """处理行内元素：加粗、高亮"""
    # **bold** → <strong>
    text = re.sub(r'\*\*(.+?)\*\*', rf'<strong style="{STYLES["strong"]}">\1</strong>', text)
    # ==highlight== → span
    text = re.sub(r'==(.+?)==', rf'<span style="{STYLES["highlight"]}">\1</span>', text)
    return text

# ═══════════════════════════════════════
# Markdown → HTML 转换
# ═══════════════════════════════════════

def md_to_wechat_html(md_text):
    lines = md_text.split('\n')
    output = []
    i = 0
    in_code_block = False
    code_lines = []
    in_table = False
    table_lines = []
    
    # 提取标题
    title = "微信公众号文章"
    for line in lines:
        m = re.match(r'^#\s+(.+)', line)
        if m:
            title = m.group(1).strip()
            break
    
    while i < len(lines):
        line = lines[i]
        
        # ── 代码块 ──
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lines = []
                i += 1
                continue
            else:
                # 结束代码块
                code_text = '\n'.join(code_lines)
                output.append(f'<pre style="{STYLES["pre"]}">{code_text}</pre>')
                in_code_block = False
                i += 1
                continue
        
        if in_code_block:
            code_lines.append(line)
            i += 1
            continue
        
        # ── 表格 ──
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
            i += 1
            # 检查下一行是否还是表格
            if i < len(lines) and '|' in lines[i] and lines[i].strip().startswith('|'):
                continue
            else:
                # 结束表格，渲染
                html = render_table(table_lines)
                output.append(html)
                in_table = False
                table_lines = []
                continue
        
        # ── 分隔线 ──
        if line.strip() in ('---', '***', '___', '—​—​—'):
            output.append(f'<hr style="{STYLES["hr"]}">')
            i += 1
            continue
        
        # ── H2 ──
        m = re.match(r'^##\s+(.+)', line)
        if m:
            text = inline_process(m.group(1))
            output.append(f'<h2 style="{STYLES["h2"]}">{text}</h2>')
            i += 1
            continue
        
        # ── H1 → H2 (微信里 H1 太大) ──
        m = re.match(r'^#\s+(.+)', line)
        if m and i > 0:  # 跳过第一行标题
            text = inline_process(m.group(1))
            output.append(f'<h2 style="{STYLES["h2"]}">{text}</h2>')
            i += 1
            continue
        
        # ── 引用块（空行 `>` 也视为引用行）──
        if line.strip().startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                stripped = lines[i].strip()
                content = stripped[1:]  # remove leading >
                if content.startswith(' '):
                    content = content[1:]
                quote_lines.append(content)
                i += 1
            
            # 多行引用（3+行）且含指令类关键词 → 用 pre 样式（提示词块）
            is_prompt = len(quote_lines) >= 3 and any(
                kw in '\n'.join(quote_lines) 
                for kw in ['问题', '要求', '不要编造', '请先', '帮我', '粘贴', '步骤', '第一步']
            )
            
            if is_prompt:
                # 用 p+br 替代 pre，微信编辑器保留换行；blockquote 已验证样式可用
                code_lines_html = '<br>'.join(quote_lines)
                output.append(f'<blockquote style="{STYLES["pre"]}"><p style="margin:0;line-height:1.7;">{code_lines_html}</p></blockquote>')
            else:
                quote_text = '<br>'.join(inline_process(l) for l in quote_lines)
                output.append(f'<blockquote style="{STYLES["blockquote"]}">{quote_text}</blockquote>')
            continue
        
        # ── 行动块 ──
        if line.strip().startswith('现在打开'):
            action_lines = [line.strip()]
            i += 1
            # 跳过空行，收集直到下一步标题/分隔线/互动钩子
            while i < len(lines):
                stripped = lines[i].strip()
                # 终止条件
                if not stripped:
                    # 空行：继续，可能是行动块内的段落间隔
                    i += 1
                    continue
                if stripped.startswith('---') or stripped.startswith('##') or stripped.startswith('**你'):
                    break
                # 如果是一个全新的句子开头（非行动块内容），也停止
                if any(stripped.startswith(kw) for kw in ['下一篇', '本文', '关注', '如果']):
                    break
                action_lines.append(stripped)
                i += 1
            action_text = '<br><br>'.join(inline_process(l) for l in action_lines)
            output.append(f'<blockquote style="{STYLES["action_block"]}"><p style="{STYLES["action_p"]}">{action_text}</p></blockquote>')
            continue
        
        # ── 互动钩子（整行加粗 + 以问号结尾）──
        stripped = line.strip()
        if (stripped.startswith('**') and stripped.endswith('**') and 
            ('？' in stripped or '?' in stripped)):
            text = inline_process(stripped)
            output.append(f'<p style="{STYLES["interaction"]}">{text}</p>')
            i += 1
            continue
        
        # ── 图片占位 ──
        m = re.match(r'!\[(.*?)\]\((.*?)\)', line.strip())
        if m:
            alt = m.group(1)
            output.append(f'<p style="{STYLES["img_note"]}">（{alt}）</p>')
            i += 1
            continue
        
        # ── 普通段落 ──
        if line.strip():
            text = inline_process(line.strip())
            output.append(f'<p style="{STYLES["p"]}">{text}</p>')
        else:
            # 空行
            output.append('')
        
        i += 1
    
    content = '\n'.join(output)
    html = HTML_WRAPPER.format(
        title=title,
        body_style=STYLES["body"],
        content=content
    )
    return html


def render_table(lines):
    """渲染 Markdown 表格"""
    if len(lines) < 2:
        return ''
    
    # 解析表头
    header_cells = [c.strip() for c in lines[0].split('|') if c.strip()]
    # 跳过分隔行
    data_start = 2 if len(lines) > 2 and re.match(r'^[\|\s\-:]+$', lines[1]) else 1
    
    html = f'<table style="{STYLES["table"]}">\n'
    
    # 表头
    html += '<tr>\n'
    for cell in header_cells:
        html += f'<th style="{STYLES["th"]}">{inline_process(cell)}</th>\n'
    html += '</tr>\n'
    
    # 数据行
    for line in lines[data_start:]:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            html += '<tr>\n'
            for cell in cells:
                html += f'<td style="{STYLES["td"]}">{inline_process(cell)}</td>\n'
            html += '</tr>\n'
    
    html += '</table>'
    return html


# ═══════════════════════════════════════
# 入口
# ═══════════════════════════════════════

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python wechat_md_to_html.py input.md [output.html]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace('.md', '.html')
    
    with open(input_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    
    html = md_to_wechat_html(md_text)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ 转换完成: {input_path} → {output_path}")
    print(f"  大小: {len(html)} 字符")
