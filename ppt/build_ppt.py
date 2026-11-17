import sys, os
sys.path.insert(0, r'E:\999-Dev\04-SOG\dev\backend\.venv\Lib\site-packages')
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR

SLIDE_W, SLIDE_H = Inches(13.33), Inches(7.5)
OUT = r'E:\999-Dev\04-SOG\dev\ppt\DELV-SOG系统介绍v2.pptx'
IMG = r'E:\999-Dev\04-SOG\dev\ppt\screenshots'

BG = RGBColor(0xF0, 0xF7, 0xFF)
BG_CARD = RGBColor(0xE8, 0xF0, 0xFE)
BG_CARD_ALT = RGBColor(0xDE, 0xE8, 0xF8)
ACCENT = RGBColor(0x15, 0x65, 0xC0)
ACCENT2 = RGBColor(0x03, 0xA9, 0xF4)
ORANGE = RGBColor(0x00, 0x96, 0x88)
WHITE = RGBColor(0x0D, 0x47, 0xA1)
LIGHT = RGBColor(0x37, 0x47, 0x4F)
GRAY = RGBColor(0x90, 0xA4, 0xAE)
PURPLE = RGBColor(0x3F, 0x51, 0xB5)
YELLOW = RGBColor(0x29, 0xB6, 0xF6)
PINK = RGBColor(0x00, 0xAC, 0xD4)
STRIPE = RGBColor(0xBB, 0xDE, 0xFB)
LINE = RGBColor(0x90, 0xCA, 0xF9)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H

def blank_slide():
    s = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank) if False else prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = BG
    return s

def add_rect(s, x, y, w, h, color, radius=None, border=False):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h) if radius else s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if border or h > Inches(0.5):
        shp.line.color.rgb = LINE
        shp.line.width = Pt(0.75)
    else:
        shp.line.fill.background()
    if radius is not None:
        shp.adjustments[0] = radius
    return shp

def add_text(s, x, y, w, h, text, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT, font='Microsoft YaHei'):
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = font
    return tb

def add_multi(s, x, y, w, h, lines, size=16, color=LIGHT, bold=False, align=PP_ALIGN.LEFT, spacing=Pt(6)):
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = spacing
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bold
        run.font.name = 'Microsoft YaHei'
    return tb

def add_slide_num(s, num, total):
    add_text(s, Inches(12.3), Inches(7.0), Inches(1), Inches(0.4), f'{num:02d}/{total:02d}', 10, GRAY, False, PP_ALIGN.RIGHT)

def add_arrow_line(s, x1, y1, x2, y2, color=ACCENT, width=Pt(2)):
    conn = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    conn.line.color.rgb = color
    conn.line.width = width
    return conn

def add_box(s, x, y, w, h, title, subtitle, color):
    add_rect(s, x, y, w, h, color, 0.06)
    add_text(s, x + Inches(0.08), y + Inches(0.1), w - Inches(0.16), Inches(0.4), title, 14, WHITE, True, PP_ALIGN.CENTER)
    add_text(s, x + Inches(0.08), y + Inches(0.45), w - Inches(0.16), Inches(0.3), subtitle, 10, LIGHT, False, PP_ALIGN.CENTER)

TOTAL = 34

# ==================== SLIDE 01: COVER ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT2)
add_text(s, Inches(1.2), Inches(1.5), Inches(11), Inches(1.2), 'DELV · SOG', 72, WHITE, True)
add_text(s, Inches(1.2), Inches(2.8), Inches(11), Inches(1.0), '离散装配生产作业支援系统', 40, ACCENT, True)
card = add_rect(s, Inches(1.2), Inches(4.2), Inches(11), Inches(1.6), BG_CARD, 0.05)
add_text(s, Inches(1.6), Inches(4.4), Inches(10), Inches(0.5), '让工厂每一张订单都知道：', 20, ACCENT2, True)
add_text(s, Inches(1.6), Inches(4.95), Inches(10), Inches(0.6), '能不能开工 · 缺什么料 · 工人看什么 SOP · 质量追溯到哪一层', 22, WHITE, False)
tags = ['物料管理', 'BOM 齐套', '生产执行', '质量追溯', 'SOP 指引', '设备接入']
for i, t in enumerate(tags):
    tx = Inches(1.2 + i * 1.85)
    tag = add_rect(s, tx, Inches(6.1), Inches(1.7), Inches(0.5), STRIPE, 0.5)
    add_text(s, tx, Inches(6.12), Inches(1.7), Inches(0.5), t, 13, ACCENT, False, PP_ALIGN.CENTER)
add_slide_num(s, 1, TOTAL)

# ==================== SLIDE 02: AGENDA ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT)
add_text(s, Inches(0.8), Inches(0.3), Inches(8), Inches(0.7), '目录 · CONTENTS', 32, WHITE, True)
agenda = [
    ('01', 'SOG 是什么 & 为什么选它', '定位 · 5 大差异化', ACCENT),
    ('02', '系统管理', '登录鉴权 · 用户 · 角色 · 审计', ACCENT),
    ('03', '主数据管理', '物料 · BOM · 检验类型 · 不良代码', ACCENT2),
    ('04', '物资管理', '物料中心 · 消耗品中心 · 在制品中心 · 批次流水', ORANGE),
    ('05', '生产订单', '工单 · 生产发布 · 订单调整', YELLOW),
    ('06', '生产管理', '执行监控 · SOP · 质量 · 追溯', PURPLE),
    ('07', '设备直连', 'OPC-UA · MQTT', PINK),
    ('08', '技术架构 · 价值', '架构 · 价值 · 实施', PURPLE),
]
for i, (num, title, desc, color) in enumerate(agenda):
    col = i % 4
    row = i // 4
    x = Inches(0.8 + col * 3.15)
    y = Inches(1.6 + row * 2.9)
    card = add_rect(s, x, y, Inches(2.95), Inches(2.6), BG_CARD, 0.06)
    add_rect(s, x, y, Inches(2.95), Inches(0.08), color)
    add_text(s, x + Inches(0.2), y + Inches(0.4), Inches(2.5), Inches(0.7), num, 44, color, True, PP_ALIGN.CENTER)
    add_text(s, x + Inches(0.2), y + Inches(1.3), Inches(2.5), Inches(0.5), title, 17, WHITE, True, PP_ALIGN.CENTER)
    add_text(s, x + Inches(0.2), y + Inches(1.9), Inches(2.5), Inches(0.6), desc, 12, GRAY, False, PP_ALIGN.CENTER)
add_slide_num(s, 2, TOTAL)

# ==================== SLIDE 03: WHAT + WHY ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT)

add_text(s, Inches(0.6), Inches(0.25), Inches(6), Inches(0.6), 'SOG 是什么', 30, WHITE, True)
add_text(s, Inches(0.6), Inches(0.8), Inches(6), Inches(0.4), '上承 ERP · 下接设备 · 作业支援中枢', 13, GRAY)

layers = [
    ('上层', 'ERP / MES / PLM', GRAY),
    ('SOG 中枢', '物料 · BOM · 生产 · 质量 · SOP · 追溯', ACCENT),
    ('下层', '设备 / 工位 / 工人 · OPC-UA · MQTT', ACCENT2),
]
for i, (name, detail, color) in enumerate(layers):
    y = Inches(1.4 + i * 0.95)
    add_rect(s, Inches(0.6), y, Inches(6.0), Inches(0.82), BG_CARD, 0.04)
    add_rect(s, Inches(0.6), y, Inches(0.12), Inches(0.82), color)
    add_text(s, Inches(0.85), y + Inches(0.1), Inches(1.6), Inches(0.35), name, 16, color, True)
    add_text(s, Inches(0.85), y + Inches(0.42), Inches(5.5), Inches(0.35), detail, 13, LIGHT)

kpis = [('70+', 'API 端点'), ('17', '核心表'), ('5', 'RBAC 角色'), ('26', '前端视图')]
for i, (v, l) in enumerate(kpis):
    x = Inches(0.6 + i * 1.55)
    add_rect(s, x, Inches(4.3), Inches(1.45), Inches(1.2), BG_CARD, 0.05)
    add_text(s, x, Inches(4.35), Inches(1.45), Inches(0.6), v, 24, ACCENT2, True, PP_ALIGN.CENTER)
    add_text(s, x, Inches(4.95), Inches(1.45), Inches(0.4), l, 11, GRAY, False, PP_ALIGN.CENTER)

add_text(s, Inches(7.0), Inches(0.25), Inches(6), Inches(0.6), '为什么选择 SOG', 30, WHITE, True)
add_text(s, Inches(7.0), Inches(0.8), Inches(6), Inches(0.4), '5 大差异化能力', 13, GRAY)

diffs = [
    ('① BOM 齐套', '订单×BOM×库存 实时缺料', ACCENT),
    ('② CSV 导入', '物料/BOM/订单 一键上传', ACCENT2),
    ('③ 可视化 RBAC', '5 角色 × 35 权限 勾选即生效', ORANGE),
    ('④ 四路追溯', '正向/反向/树形/BFS 全链路', PURPLE),
    ('⑤ SOP 图片标注', 'Canvas 箭头框圆 扫码即看', YELLOW),
]
for i, (title, desc, color) in enumerate(diffs):
    y = Inches(1.4 + i * 1.1)
    add_rect(s, Inches(7.0), y, Inches(5.8), Inches(0.95), BG_CARD, 0.05)
    add_rect(s, Inches(7.0), y, Inches(0.12), Inches(0.95), color)
    add_text(s, Inches(7.25), y + Inches(0.08), Inches(5.3), Inches(0.4), title, 17, WHITE, True)
    add_text(s, Inches(7.25), y + Inches(0.48), Inches(5.3), Inches(0.4), desc, 13, LIGHT)
add_slide_num(s, 3, TOTAL)

# ==================== SLIDE 04: MODULE RELATIONSHIP FLOW ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ORANGE)
add_text(s, Inches(0.6), Inches(0.25), Inches(12), Inches(0.6), 'SOG 模块关系流程图', 30, WHITE, True)
add_text(s, Inches(0.6), Inches(0.8), Inches(12), Inches(0.4), '数据驱动的生产全链路 · 6 大模块协同运转', 13, GRAY)

# Layer 1: 主数据层
add_text(s, Inches(0.4), Inches(1.3), Inches(3), Inches(0.4), '① 主数据层', 15, ACCENT, True)
add_text(s, Inches(0.4), Inches(1.6), Inches(3), Inches(0.3), '基础 · 所有业务的源头', 10, GRAY)
bw = Inches(2.1); bh = Inches(0.75); ly1 = Inches(2.0)
layer1_color = RGBColor(0xE3, 0xF2, 0xFD)
for i, (t, sub) in enumerate([('物料主数据', '3 类型 · CSV'), ('BOM 清单', '多版本'), ('检验类型字典', '7×4 策略'), ('不良代码字典', '三级分类')]):
    x = Inches(0.5 + i * 2.3)
    add_box(s, x, ly1, bw, bh, t, sub, layer1_color)

# Layer 2: 业务中枢
add_text(s, Inches(0.4), Inches(3.0), Inches(3), Inches(0.4), '② 业务中枢层', 15, ACCENT2, True)
add_text(s, Inches(0.4), Inches(3.3), Inches(3), Inches(0.3), '核心生产流 · 主链路', 10, GRAY)
ly2 = Inches(3.6)
layer2_color = RGBColor(0xE0, 0xF2, 0xF1)
for i, (t, sub) in enumerate([('生产工单', 'CSV · 状态机'), ('生产发布', '下达 · 齐套 · 批量'), ('订单调整', '拆分 · 排产 · 锁定'), ('生产执行', '逐工序报工')]):
    x = Inches(0.5 + i * 2.3)
    add_box(s, x, ly2, bw, bh, t, sub, layer2_color)

# Arrows L1 -> L2
for i in range(4):
    cx = Inches(0.5 + i * 2.3) + bw/2
    add_arrow_line(s, cx, ly1 + bh, cx, ly2, ACCENT, Pt(1.2))

# 工单→齐套→生产→质量
add_arrow_line(s, Inches(0.5) + bw, ly2 + bh/2, Inches(2.8), ly2 + bh/2, ACCENT2, Pt(1.2))
add_arrow_line(s, Inches(2.8) + bw, ly2 + bh/2, Inches(5.1), ly2 + bh/2, ACCENT2, Pt(1.2))
add_arrow_line(s, Inches(5.1) + bw, ly2 + bh/2, Inches(7.4), ly2 + bh/2, ACCENT2, Pt(1.2))

# Layer 3: 支撑层
add_text(s, Inches(0.4), Inches(4.65), Inches(3), Inches(0.4), '③ 数据支撑层', 15, ORANGE, True)
add_text(s, Inches(0.4), Inches(4.95), Inches(3), Inches(0.3), '看板/追溯/库存消费', 10, GRAY)
ly3 = Inches(5.25)
layer3_color = RGBColor(0xF3, 0xE5, 0xF5)
for i, (t, sub) in enumerate([('物料中心', '入出盘查'), ('消耗品中心', '领用归还'), ('在制品WIP', '龄期 · 瓶颈'), ('批次追溯', '四路全链路'), ('运营看板', 'KPI 汇总')]):
    x = Inches(0.5 + i * 2.0)
    add_box(s, x, ly3, Inches(1.85), bh, t, sub, layer3_color)

# Arrows L2 -> L3
add_arrow_line(s, Inches(1.55), ly2 + bh, Inches(1.55), ly3, ORANGE, Pt(1.2))
add_arrow_line(s, Inches(6.15), ly2 + bh, Inches(6.15), ly3, ORANGE, Pt(1.2))
add_arrow_line(s, Inches(8.45), ly2 + bh, Inches(8.45), ly3, ORANGE, Pt(1.2))

# Side: 横向支撑
add_text(s, Inches(10.2), Inches(1.3), Inches(3), Inches(0.4), '横向支撑模块', 15, PURPLE, True)
add_text(s, Inches(10.2), Inches(1.6), Inches(3), Inches(0.3), '贯穿所有业务域', 10, GRAY)
for i, (t, sub) in enumerate([('系统管理', 'RBAC · 审计'), ('SOP 作业指导', '图片标注 · 扫码即看'), ('设备直连', 'OPC-UA/MQTT')]):
    y = Inches(2.0 + i * 1.05)
    add_box(s, Inches(10.2), y, Inches(2.9), bh, t, sub, RGBColor(0xE8, 0xEA, 0xF8))

add_text(s, Inches(0.4), Inches(6.9), Inches(12), Inches(0.4),
    '主数据 █  业务中枢 █  数据支撑 █  横向支撑 █   ← 数据流向   ↔ 同步联动', 10, GRAY)
add_slide_num(s, 4, TOTAL)

# ==================== HELPER: GROUP SLIDE ====================
def add_group_intro(num, title, subtitle, items, color):
    s = blank_slide()
    add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), color)
    add_text(s, Inches(0.8), Inches(1.2), Inches(12), Inches(0.9), num, 48, color, True, PP_ALIGN.LEFT)
    add_text(s, Inches(0.8), Inches(2.2), Inches(12), Inches(0.9), title, 36, WHITE, True, PP_ALIGN.LEFT)
    add_text(s, Inches(0.8), Inches(3.1), Inches(12), Inches(0.5), subtitle, 16, GRAY, False, PP_ALIGN.LEFT)
    add_rect(s, Inches(0.8), Inches(3.8), Inches(1.5), Inches(0.04), color)
    for i, (name, desc) in enumerate(items):
        col = i % 2
        row = i // 2
        x = Inches(0.8 + col * 6.2)
        y = Inches(4.1 + row * 0.95)
        add_rect(s, x, y, Inches(5.9), Inches(0.8), BG_CARD, 0.05)
        add_rect(s, x, y, Inches(0.1), Inches(0.8), color)
        add_text(s, x + Inches(0.25), y + Inches(0.05), Inches(5.5), Inches(0.35), name, 16, WHITE, True)
        add_text(s, x + Inches(0.25), y + Inches(0.42), Inches(5.5), Inches(0.3), desc, 11, LIGHT)
    return s

def add_detail_slide(group_label, num_in_group, title, img_file, feature_lines, flow_lines, color):
    s = blank_slide()
    add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), color)
    add_text(s, Inches(0.5), Inches(0.15), Inches(10), Inches(0.35), f'{group_label} · {num_in_group:02d}', 10, color, True)
    add_text(s, Inches(0.5), Inches(0.5), Inches(10), Inches(0.5), title, 24, WHITE, True)

    img_path = os.path.join(IMG, img_file)
    img_h = Inches(4.2)
    if os.path.exists(img_path):
        add_rect(s, Inches(0.4), Inches(1.1), Inches(8.3), img_h + Inches(0.2), BG_CARD, 0.03)
        s.shapes.add_picture(img_path, Inches(0.5), Inches(1.2), width=Inches(8.1), height=img_h)

    # Feature panel right
    px = Inches(8.9); py = Inches(1.1); pw = Inches(4.0); ph = Inches(5.9)
    add_rect(s, px, py, pw, ph, BG_CARD, 0.05)
    add_text(s, px + Inches(0.15), py + Inches(0.1), pw - Inches(0.3), Inches(0.4), '✦ 功能特性', 13, color, True)
    add_multi(s, px + Inches(0.15), py + Inches(0.55), pw - Inches(0.3), Inches(3.0),
        [f'• {f}' for f in feature_lines], 12, LIGHT, False, PP_ALIGN.LEFT, Pt(6))
    add_rect(s, px + Inches(0.15), py + Inches(3.6), pw - Inches(0.3), Inches(0.02), color)
    add_text(s, px + Inches(0.15), py + Inches(3.7), pw - Inches(0.3), Inches(0.4), '➤ 业务流程', 13, color, True)
    add_multi(s, px + Inches(0.15), py + Inches(4.15), pw - Inches(0.3), Inches(1.6),
        flow_lines, 11, GRAY, False, PP_ALIGN.LEFT, Pt(4))
    return s

slide_idx = 5

# ==================== MODULE 01: 系统管理 ====================
mcolor = ACCENT
s = add_group_intro('模块 · 01', '系统管理', '全系统用户、角色权限、审计追踪的统一管控',
    [('登录与鉴权', 'JWT HS256 · PBKDF2 · 5 级 RBAC 角色自动识别'),
     ('用户管理', '账号创建 · 角色分配 · 启禁用 · 密码重置'),
     ('角色授权', '可视化权限矩阵 · 6 模块 × 35 项权限 勾选即生效'),
     ('审计日志', '每次权限变更 · 关键操作全量留痕')],
    mcolor)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

details = [
    ('登录与鉴权', '01_login.png',
     ['JWT HS256 签名 · 无状态会话', 'PBKDF2-HMAC-SHA256 密码哈希', '5 级 RBAC 角色自动识别', '前端按角色动态渲染菜单', '登录态 localStorage 持久化'],
     ['输入用户名密码 → 后端校验', '返回 token + 用户角色', '前端存储 token 并刷新权限', '后续请求自动携带 token']),
    ('用户管理', '03_system_users.png',
     ['账号 CRUD · 批量启禁用', '角色下拉绑定 RBAC', '初始密码自动生成', '与 audit_log 联动审计', '权限范围按角色自动受限'],
     ['管理员创建用户', '分配角色（OPERATOR/ENGINEER/MANAGER/ADMIN）', '用户登录后只能看权限内菜单', '禁用账号后 token 校验失败']),
    ('角色授权', '04_system_roles.png',
     ['6 模块 × 35 项权限完整矩阵', '按模块分组 UI 展示', '前端勾选即时生效', 'DB role_permission 表持久化', '缓存写时失效保证一致性', 'ADMIN 特殊处理永远全权限'],
     ['管理员进入角色授权页', '选择某角色，勾选/取消权限', '点击保存 → 写入 role_permission', '内存缓存立即失效', '下次该角色请求用新权限校验']),
    ('审计日志', '05_system_logs.png',
     ['真实 audit_log 表接入', '每次权限变更自动记录', '关键操作全量留痕', '多条件过滤 + 分页', '动作类型标签着色（CREATE/UPDATE/DELETE/LOGIN）'],
     ['用户执行敏感操作', '后端中间件自动写入 audit_log', '前端审计日志页面查询展示', '按时间/用户/动作类型过滤']),
]

for i, (title, img, feats, flow) in enumerate(details):
    s = add_detail_slide('系统管理', i + 1, title, img, feats, flow, mcolor)
    add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== MODULE 02: 主数据管理 ====================
mcolor = ACCENT2
s = add_group_intro('模块 · 02', '主数据管理', '生产运营的基础源头数据 · 全字典维护',
    [('物料主数据', 'RAW / SEMI / FG · CSV 批量导入 · 幂等防重'),
     ('BOM 清单', '多版本 BOM · 激活切换 · 齐套计算入口'),
     ('检验类型字典', '7 分类 × 4 抽样策略 · 工序自动匹配'),
     ('不良代码字典', '三级分类 · 严重等级 · 检验时直接选择')],
    mcolor)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

details = [
    ('物料主数据', '06_materials.png',
     ['3 种类型：RAW 原料 / SEMI 半成品 / FG 成品', 'CSV 批量导入 + 模板下载', '编码唯一性约束 · 幂等防重', '17 个字段完整 CRUD', '删除前校验库存台账防误删'],
     ['Excel 整理物料数据', 'CSV 上传 → 后端自动解析', '已存在编码跳过 / 新编码创建', '前端列表实时刷新', '支持编辑/删除/再次导入']),
    ('BOM 清单', '07_boms.png',
     ['多版本 BOM · 激活/切换历史版本', 'CSV 批量导入 BOM 组件', '主 BOM + 替代料行', '齐套检查入口按钮直接调用', '自动关联物料主数据编码'],
     ['选择父物料 → 创建 BOM', '添加组件行（物料编码 + 用量 + 损耗）', '发布后设为激活版本', '支持多版本并行管理', '齐套检查时取激活版本']),
    ('检验类型字典', '08_inspect_types.png',
     ['7 种分类：IQC/IPQC/PQC/FQC/OQC/SPQC/CUSTOM', '4 种抽样策略：全检/GB2828/固定/自定义', '检验标准与检验类型关联', '按工序自动匹配检验类型', 'GB/T 2828 国标支持', '抽样数自动计算'],
     ['创建检验类型（如 IPQC 过程检）', '选择抽样策略（如 GB2828）', '关联检验标准明细', '绑定适用工序', '质量检验时自动下拉匹配']),
    ('不良代码字典', '09_defect_codes.png',
     ['三级分类结构（大类/中类/小类）', '严重等级标记（轻微/一般/严重）', '不良描述字段完整', '检验记录直接引用', '质量统计自动聚合'],
     ['创建不良代码分类树', '录入不良代码 + 描述 + 等级', '质量检验时下拉选择', '检验记录关联代码 ID', '后续质量报表按代码聚合']),
]

for i, (title, img, feats, flow) in enumerate(details):
    s = add_detail_slide('主数据管理', i + 1, title, img, feats, flow, mcolor)
    add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== MODULE 03: 物资管理 ====================
mcolor = ORANGE
s = add_group_intro('模块 · 03', '物资管理', '四大中心协同 · 物料 / 消耗品 / 在制品 / 批次流水 全生命周期管控',
    [('物料管理中心', '原料/成品出入库 · 批次 FIFO · 盘点 · 库存查询'),
     ('消耗品管理中心', '刀具/工装/辅料 · 低值易耗品领用归还 · 消耗预警'),
     ('在制品管理中心', 'WIP 工序间流转 · 在制龄期分析 · 瓶颈追踪'),
     ('批次与流水', '批次号全链路 · 事务流水 · 异动留痕')],
    mcolor)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

details = [
    ('物料管理中心', '10_inventory_hub.png',
     ['原料/成品双库位管理', '入库：采购收货 / 生产完工自动入库', '出库：生产领料 FIFO 自动选批次', '批次号自动生成 · 唯一追溯', '实时库存查询（按物料/批次/库位）', '盘点：打印盘点单 → 录入差异 → 自动调整'],
     ['入库：选择物料 → 输入数量/批次/库位 → 确认', '出库：选择物料 → 系统 FIFO 选最早批次 → 确认', '盘点：现场清点 → 录入差异 → 系统自动调账', '查询：多维度过滤 + 导出 Excel']),
    ('消耗品管理中心', '11_consumables_hub.png',
     ['刀具 / 工装夹具 / 辅料 独立库位', '领用登记 + 归还核销', '低值易耗品领用审批流', '消耗数量与工单关联（成本归集）', '库存低于阈值自动预警', '支持按车间/产线分配额度'],
     ['创建消耗品类目 → 设置库位和安全库存', '领用时绑定工单/工序 → 自动扣减库存', '归还时按实际剩余量核销', '月末汇总消耗报表 → 成本分摊到工单']),
    ('在制品管理中心', '12_wip_hub.png',
     ['WIP 看板实时展示各工序在制数量', '在制品龄期分析（堆叠柱图 + 热力）', '瓶颈工序自动识别（上下游速率对比）', '在制品从原料→半成品→成品全链路追踪', '支持按车间 / 产线 / 产品过滤', '超期 WIP 自动预警标红'],
     ['打开 WIP Hub → 查看各工序在制数', '龄期分析：识别哪道工序积压最久', '瓶颈识别：对比前后工序速率', '追踪在制品批次号 → 关联上游原料批次', '辅助产线平衡决策 · 排产优化']),
    ('批次与流水', '13_stock_txn.png',
     ['所有出入库操作自动写入流水（stock_transaction 表）', '7 种流水类型：入库/出库/预留/释放/报废/盘盈/盘亏', '每笔记录：批次号+物料+数量+结存+关联单据+操作人', '多维度过滤：操作类型/批次号/关键词', '数量颜色区分（绿色入/红色出）', '可按批次号反向追溯全链路异动'],
     ['任何出入库操作 → 系统自动写流水', '打开「批次与流水」页面 → 全量流水展示', '按操作类型/批次号筛选', '点击批次号 → 关联追溯模块查全链路', '结存字段实时反映每步操作后剩余库存']),
]

for i, (title, img, feats, flow) in enumerate(details):
    s = add_detail_slide('物资管理', i + 1, title, img, feats, flow, mcolor)
    add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== MODULE 04: 生产订单 ====================
mcolor = YELLOW
s = add_group_intro('模块 · 04', '生产订单', '订单全生命周期 · 工单创建 → 生产发布 → 齐套校验 → 调整下达',
    [('生产工单', 'CSV 批量导入 · 自动接收 ERP · 状态机驱动'),
     ('生产发布', '下达前齐套校验 · 批量发布 · 缺料阻塞预警'),
     ('订单调整', '拆分 · 排产 · 调数量 · 锁定 · 批量操作工作台')],
    mcolor)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

details = [
    ('生产工单', '14_orders_work.png',
     ['CSV 批量导入工单（Excel 整理上传）', '自动接收 ERP 新订单（mock 演示）', '手动新建工单表单（客户/型号/数量/优先级）', '4 张统计卡：全部 / 草稿待下达 / 在制中 / 已完工', '状态机驱动：草稿 → 下达 → 投产 → 完工 → 关闭', '下达时自动生成工序路由 + 缺料告警'],
     ['CSV 上传 或 手动新建工单', '设置优先级 P1-P5 和计划日期', '下达生产（系统自动生成工单 + 工序）', '缺料时弹窗告警提示齐套检查', '后续进入生产发布页面统一下达']),
    ('生产发布', '15_orders_release.png',
     ['专注草稿订单下达，自动过滤已下达/已完工工单', '下达前自动触发齐套检查（订单 × BOM × 库存）', '齐套率实时计算，缺料清单逐行展示', '单条下达 → 状态变更为已下达 + 自动生成工单', '批量发布 → 勾选多草稿订单一键下达', '缺料阻塞 → 先补料再发布'],
     ['进入「生产发布」页面 → 系统自动聚焦草稿订单', '输入订单数量 → 点击「下达」按钮', '后端执行齐套检查（遍历 BOM 组件查库存）', '✅ 齐套通过 → 状态 → 已下达 · 自动生成工单', '❌ 缺料阻塞 → 弹出缺料清单 → 先补料再下达']),
    ('订单调整工作台', '16_orders_adjust.png',
     ['单项调整：拆分 / 排产 / 调数量 / 锁定解锁', '批量操作：批量发布（勾选多草稿）· 批量锁定', '拆分：从前 N 台拆出新工单（弹窗输入数量）', '排产：修改计划日期（YYYY-MM-DD）', '调数量：直接改工单数量（校验正整数）', '状态保护：已锁定/取消/完工的工单禁用编辑按钮'],
     ['进入订单调整工作台 → 勾选目标工单', '单项：点击行内按钮执行拆分/排产/调数量', '批量：勾选多行 → 顶部「批量发布 / 批量锁定」', '拆分弹窗输入数量 → 自动创建新工单子项', '所有调整操作即时保存 → 列表自动刷新']),
]

for i, (title, img, feats, flow) in enumerate(details):
    s = add_detail_slide('生产订单', i + 1, title, img, feats, flow, mcolor)
    add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== MODULE 05: 生产管理 ====================
mcolor = PURPLE
s = add_group_intro('模块 · 05', '生产管理', '生产执行监控 · SOP 指引 · 质量检验 · 批次追溯',
    [('生产执行监控', '订单状态 KPI · 进度条 · 逾期预警 · 优先级看板'),
     ('SOP 作业指导', '图片上传 · Canvas 标注编辑器 · 工位扫码即看'),
     ('质量检验', '检验类型联动 · 不良代码选择 · 自动判定'),
     ('批次追溯', '正向/反向/树形/BFS 四路全链路追溯')],
    mcolor)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

details = [
    ('生产执行监控', '17_orders_monitor.png',
     ['6 张 KPI 卡：总订单 / 已下达 / 生产中 / 已完工 / 逾期 / 完工率', '状态分布条图（草稿→关闭 6 状态）', '高优先级订单单独列（P1-P2 紧急在制中）', '订单列表支持按关键词 + 状态双维度过滤', '每行可快捷执行：下达 / 投产 / 完工 / 关闭', '逾期订单计划日期自动标红', '辅助产线平衡决策 · 排产优化'],
     ['打开生产执行监控 → 查看 6 张 KPI 汇总', '左侧状态分布条图快速识别阻塞点', '左下高优先级列表聚焦紧急订单', '右侧订单列表 → 快捷按钮推进状态', '逾期标红 → 驱动管理动作']),
    ('SOP 作业指导', '19_sops.png',
     ['图片上传（JPG/PNG）· 支持多图', 'Canvas AnnotationEditor 可视化标注', '箭头 / 矩形框 / 圆形 / 文字 4 种标注工具', 'Ctrl+Z 撤销 · Ctrl+Shift+Z 重做', '归一化坐标存储（支持任意缩放不失真）', '工位扫码或生产执行页面一键展示', '可与工序管理绑定（某工序 → 对应 SOP）'],
     ['上传设备/工位/产品示意图', '打开标注编辑器', '画箭头指向重点 · 框选关键区域 · 添加文字说明', '保存 → 坐标自动归一化', '生产执行页面扫码或点击即可展示']),
    ('质量检验', '18_quality.png',
     ['检验类型下拉（从 inspect_type 接口动态加载）', '不良代码下拉（三级分类）', '抽样数自动填入（按检验类型策略）', '检验结论自动判定（合格/不合格）', '检验记录关联工单工序和批次', '支持逐工序列入多道检验项'],
     ['选择工单 → 选择工序', '检验类型自动匹配 / 手动切换', '录入抽样数、合格数、不良项目', '系统自动判定结论', '保存 → 写入 quality_inspection 表']),
    ('批次追溯', '20_trace.png',
     ['四路追溯模式：Forward / Backward / Tree / BFS', '正向追溯：成品用了哪些原料/批次', '反向追溯：某批原料去了哪些工单/成品', '树形展开展示多层 BOM 结构', 'BFS 广度优先搜索跨层级关联', '追溯结果可导出'],
     ['输入批次号 → 选择追溯方向', 'Forward：查成品 → 逐级展开用料', 'Backward：查原料 → 逐级查去向', 'Tree：以树结构可视化 BOM', 'BFS：横向优先展示所有关联批次']),
]

for i, (title, img, feats, flow) in enumerate(details):
    s = add_detail_slide('生产管理', i + 1, title, img, feats, flow, mcolor)
    add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== MODULE 06: 设备直连 ====================
mcolor = PINK
s = add_group_intro('模块 · 06', '设备直连', 'OPC-UA / MQTT 工业协议接入 · 设备数据采集',
    [('设备管理', '设备注册 · OPC-UA 节点配置 · MQTT 主题模板'),
     ('协议骨架', '两种主流工业协议占位 · 可扩展至 PLC / SCADA'),
     ('设备数据采集', '实时温度/产量/故障等参数 · 异常预警'),
     ('与生产联动', '设备状态自动触发工单状态变更')],
    mcolor)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

details = [
    ('设备管理', '21_devices.png',
     ['OPC-UA 协议模板（endpoint URL + namespace + nodeId 示例）', 'MQTT 协议模板（broker URL + topic + QoS 示例）', '设备注册 API（POST /api/devices）', '协议元数据可配置扩展', '骨架页面，后续可对接实际 PLC/SCADA', '前端展示默认节点/主题示例'],
     ['创建设备 → 选择协议类型（OPC-UA / MQTT）', '填写连接参数（endpoint / broker URL）', '配置节点 ID / 消息主题', '保存 → 后续生产执行时可关联设备', '预留实时数据采集接口']),
]

for i, (title, img, feats, flow) in enumerate(details):
    s = add_detail_slide('设备直连', i + 1, title, img, feats, flow, mcolor)
    add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== SLIDE: TECH ARCHITECTURE ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), PURPLE)
add_text(s, Inches(0.8), Inches(0.3), Inches(10), Inches(0.7), '技术架构', 36, WHITE, True)

layers_arch = [
    ('前端 · Vue 3 + Element Plus', 'Pinia 状态管理 · Vue Router 路由守卫 · Axios 拦截器 · AnnotationEditor 标注组件', ACCENT),
    ('API 网关 · FastAPI + SQLAlchemy', '70+ 端点 · RBAC require_perm 权限校验 · CSV 上传解析 · JWT HS256 鉴权', ACCENT2),
    ('数据层 · PostgreSQL 18', '17 表核心数据模型 · JSONB 灵活字段 · 唯一约束 · 部分索引 · 行锁并发控制', ORANGE),
    ('设备接入 · OPC-UA / MQTT', '协议模板骨架 · 节点配置 · 消息主题 · 可扩展至 PLC / SCADA', PURPLE),
]
for i, (name, tech, color) in enumerate(layers_arch):
    y = Inches(1.3 + i * 1.45)
    add_rect(s, Inches(0.8), y, Inches(11.7), Inches(1.25), BG_CARD, 0.05)
    add_rect(s, Inches(0.8), y, Inches(0.15), Inches(1.25), color)
    add_text(s, Inches(1.2), y + Inches(0.15), Inches(11), Inches(0.5), name, 20, WHITE, True)
    add_text(s, Inches(1.2), y + Inches(0.65), Inches(11), Inches(0.5), tech, 14, LIGHT)

stack = [('Vue 3', '#42b883'), ('FastAPI', '#009688'), ('PostgreSQL', '#336791'), ('SQLAlchemy', '#009688'), ('Pinia', '#ffd166'), ('JWT', '#00b4d8'), ('OPC-UA', '#ff8c42'), ('MQTT', '#b388ff')]
for i, (name, hexcolor) in enumerate(stack):
    col = RGBColor(int(hexcolor[1:3],16), int(hexcolor[3:5],16), int(hexcolor[5:7],16))
    x = Inches(0.8 + i * 1.55)
    add_rect(s, x, Inches(7.1), Inches(1.45), Inches(0.35), col, 0.5)
    add_text(s, x, Inches(7.1), Inches(1.45), Inches(0.35), name, 11, WHITE, True, PP_ALIGN.CENTER)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== SLIDE: CUSTOMER VALUE ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), YELLOW)
add_text(s, Inches(0.8), Inches(0.3), Inches(10), Inches(0.7), '给客户带来的价值', 36, WHITE, True)

values = [
    ('↓ 80%', '齐套等待时间', '传统 Excel 排产 → SOG 实时计算', ACCENT),
    ('↓ 30%', '物料呆滞成本', 'BOM 版本化 + 齐套检查前置', ACCENT2),
    ('↓ 40%', '质量追溯时间', '四路追溯 BFS 优先', ORANGE),
    ('↓ 60%', '新员工上手时间', 'SOP 图片标注 + 扫码', PURPLE),
    ('↑ ∞', '决策透明度', '17 表全流程可查', YELLOW),
]
for i, (num, label, desc, color) in enumerate(values):
    x = Inches(0.5 + i * 2.52)
    y = Inches(1.5)
    add_rect(s, x, y, Inches(2.4), Inches(5.2), BG_CARD, 0.06)
    add_text(s, x, y + Inches(0.8), Inches(2.4), Inches(1.2), num, 48, color, True, PP_ALIGN.CENTER)
    add_text(s, x + Inches(0.1), y + Inches(2.1), Inches(2.2), Inches(0.5), label, 18, WHITE, True, PP_ALIGN.CENTER)
    add_text(s, x + Inches(0.1), y + Inches(2.7), Inches(2.2), Inches(2.2), desc, 13, GRAY, False, PP_ALIGN.CENTER)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== SLIDE: IMPLEMENTATION ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), PINK)
add_text(s, Inches(0.8), Inches(0.3), Inches(10), Inches(0.7), '实施路径 · 2 周交付', 36, WHITE, True)

phases = [
    ('第 1 周', '基础搭建', ['系统部署 · 环境配置', '物料/BOM 历史数据 CSV 导入', '用户/角色/RBAC 权限配置', '基础数据清洗与校验'], ACCENT),
    ('第 2 周', '核心上线', ['生产工单 · 生产发布 · 订单调整启用', '质量检验对接检验类型字典', 'SOP 上传 + 工位扫码标注', '运营看板 + 执行监控 + 追溯全链路'], ACCENT2),
    ('上线后', '优化扩展', ['设备 OPC-UA / MQTT 对接', '现场操作培训 + 管理员培训', 'CSV 批量导入生产订单', '验收交付 · 支持期启动'], ORANGE),
]
for i, (time, phase, items, color) in enumerate(phases):
    x = Inches(0.8 + i * 4.15)
    y = Inches(1.5)
    add_rect(s, x, y, Inches(3.85), Inches(5.2), BG_CARD, 0.06)
    add_rect(s, x, y, Inches(3.85), Inches(0.08), color)
    add_text(s, x + Inches(0.2), y + Inches(0.3), Inches(3.5), Inches(0.5), time, 22, color, True)
    add_text(s, x + Inches(0.2), y + Inches(0.85), Inches(3.5), Inches(0.5), phase, 20, WHITE, True)
    for j, item in enumerate(items):
        add_text(s, x + Inches(0.3), y + Inches(1.6 + j * 0.7), Inches(3.3), Inches(0.5), f'▸ {item}', 15, LIGHT)
add_slide_num(s, slide_idx, TOTAL); slide_idx += 1

# ==================== SLIDE: END ====================
s = blank_slide()
add_rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT2)
add_text(s, Inches(0), Inches(2.2), SLIDE_W, Inches(1.2), '让离散装配车间', 54, WHITE, True, PP_ALIGN.CENTER)
add_text(s, Inches(0), Inches(3.4), SLIDE_W, Inches(1.0), '每一张订单都透明可查', 44, ACCENT, True, PP_ALIGN.CENTER)
add_rect(s, Inches(3), Inches(5.0), Inches(7.3), Inches(1.0), BG_CARD, 0.5)
add_text(s, Inches(0), Inches(5.2), SLIDE_W, Inches(0.6), 'DELV · SOG 离散装配生产作业支援系统', 18, ACCENT2, False, PP_ALIGN.CENTER)
add_slide_num(s, slide_idx, TOTAL)

prs.save(OUT)
print(f'PPT saved: {OUT}')
print(f'Total slides: {len(prs.slides)}')