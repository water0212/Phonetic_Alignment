from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap


OUT_DIR = Path("report_figures_20260907")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_REG = r"C:\Windows\Fonts\msjh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msjhbd.ttc"


def font(size, bold=False):
    path = FONT_BOLD if bold and Path(FONT_BOLD).exists() else FONT_REG
    return ImageFont.truetype(path, size)


COLORS = {
    "blue": "#1f5f99",
    "blue2": "#2f75b5",
    "light_blue": "#eaf3fb",
    "green": "#2e7d4f",
    "light_green": "#edf7ef",
    "orange": "#c56b1d",
    "light_orange": "#fff2df",
    "gray": "#5f6b7a",
    "line": "#7890a8",
    "black": "#111111",
    "white": "#ffffff",
    "red": "#d62828",
}


def wrap_by_width(draw, text, fnt, width):
    lines = []
    for paragraph in str(text).split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            test = current + ch
            if draw.textbbox((0, 0), test, font=fnt)[2] <= width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def draw_wrapped(draw, xy, text, fnt, fill, width, line_gap=8, anchor=None):
    x, y = xy
    lines = wrap_by_width(draw, text, fnt, width)
    total_h = sum(draw.textbbox((0, 0), line, font=fnt)[3] - draw.textbbox((0, 0), line, font=fnt)[1] for line in lines)
    total_h += line_gap * (len(lines) - 1)
    if anchor == "mm":
        y -= total_h / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fnt)
        h = bbox[3] - bbox[1]
        if anchor == "mm":
            w = bbox[2] - bbox[0]
            draw.text((x - w / 2, y), line, font=fnt, fill=fill)
        else:
            draw.text((x, y), line, font=fnt, fill=fill)
        y += h + line_gap


def rounded_box(draw, xy, title, body="", fill="#ffffff", outline="#7890a8", title_fill="#1f5f99",
                w=None, h=None, radius=24):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=3)
    pad = 24
    draw_wrapped(draw, (x1 + pad, y1 + pad), title, font(34, True), title_fill, x2 - x1 - pad * 2, line_gap=8)
    if body:
        draw_wrapped(draw, (x1 + pad, y1 + 82), body, font(25), COLORS["black"], x2 - x1 - pad * 2, line_gap=8)


def arrow(draw, start, end, color=None, width=5):
    color = color or COLORS["line"]
    draw.line([start, end], fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 18
    pts = [
        (x2, y2),
        (x2 - size * math.cos(ang - math.pi / 6), y2 - size * math.sin(ang - math.pi / 6)),
        (x2 - size * math.cos(ang + math.pi / 6), y2 - size * math.sin(ang + math.pi / 6)),
    ]
    draw.polygon(pts, fill=color)


def save(img, name):
    path = OUT_DIR / name
    img.save(path, dpi=(220, 220))
    print(path.resolve())


def base_canvas(title, subtitle=None, w=1900, h=1100):
    img = Image.new("RGB", (w, h), COLORS["white"])
    d = ImageDraw.Draw(img)
    d.text((70, 52), title, font=font(46, True), fill=COLORS["blue"])
    if subtitle:
        d.text((72, 115), subtitle, font=font(25), fill=COLORS["gray"])
    return img, d


def data_preprocessing():
    img, d = base_canvas("新詞辭典資料清洗與標準化流程", "目的：讓各族新詞資料進入後續分類、統計與推薦流程前，具有一致格式。")
    boxes = [
        ("原始新詞辭典 JSON", "各族新詞資料；key 為中文新詞，value 中保存族語譯詞、語義標註與方言資訊。"),
        ("中文 key 標準化", "刪除括號補充說明，例如：原民會（全稱：原住民族委員會）→ 原民會。"),
        ("撞名與特殊詞處理", "若刪括號後造成重名，改保留可區分的名稱；親屬詞以 related_keys 保存完整展開項。"),
        ("方言別保留", "同一中文詞在不同方言可有不同族語譯詞，使用 dialect 欄位保留來源方言。"),
        ("清洗版與分類資料", "輸出可供借詞、單詞、詞組三種推薦系統使用的標準化資料。"),
    ]
    y = 185
    prev_center = None
    for idx, (t, b) in enumerate(boxes):
        fill = COLORS["light_blue"] if idx in (0, 4) else COLORS["light_green"]
        rounded_box(d, (220, y, 1680, y + 130), t, b, fill=fill)
        center = (950, y + 130)
        if prev_center:
            arrow(d, prev_center, (950, y - 6))
        prev_center = center
        y += 175
    save(img, "figure_2_data_preprocessing.png")


def system_overview():
    img, d = base_canvas("三種新詞推薦系統整體架構", "依新詞形成方式選擇推薦策略；三種評估口徑不可直接互相比較。")
    rounded_box(d, (710, 170, 1190, 285), "輸入：中文新詞", "例如：健保、收養、高速公路", fill=COLORS["light_blue"])
    rounded_box(d, (710, 360, 1190, 470), "新詞類型判斷", "借詞／單詞／詞組", fill=COLORS["light_orange"], title_fill=COLORS["orange"])
    arrow(d, (950, 285), (950, 360))
    modules = [
        ((95, 600, 575, 835), "借詞推薦", "適用：音譯或中借詞\n方法：漢語聲韻母 → 族語音段\n輸出：候選族語音形\n評估：整詞、聲母、韻母正確率"),
        ((710, 600, 1190, 835), "單詞推薦", "適用：單一族語詞表示的新詞\n方法：詞嵌入與餘弦相似度\n輸出：語義最接近候選詞\n評估：直接命中、辭典內命中"),
        ((1325, 600, 1805, 835), "詞組推薦", "適用：多個族語詞組成的新詞\n方法：GPT-OSS 拆義 + 辭典候選\n輸出：族語詞組候選\n評估：組件命中率"),
    ]
    for xy, t, b in modules:
        rounded_box(d, xy, t, b, fill=COLORS["light_green"])
    arrow(d, (950, 470), (335, 600))
    arrow(d, (950, 470), (950, 600))
    arrow(d, (950, 470), (1565, 600))
    rounded_box(d, (455, 915, 1445, 1055), "共同目的", "提供可追蹤、可評估的候選詞，輔助人工造詞與族語新詞審查。", fill="#f6f8fb")
    for x in (335, 950, 1565):
        arrow(d, (x, 835), (950, 925))
    save(img, "figure_2_system_overview.png")


def loanword_pipeline():
    img, d = base_canvas("借詞推薦系統音韻對齊流程", "核心：先建立漢語聲韻母與族語音段的對應關係，再用對照表產生新詞候選。", h=1220)
    steps = [
        ((80, 190, 445, 380), "1 清洗版借詞資料", "中借、未明說等借詞資料\n含中文詞與族語答案"),
        ((535, 190, 900, 380), "2 取得中文拼音", "優先查 ch_dict.json\n未命中則查 CEDICT 標準化表"),
        ((990, 190, 1355, 380), "3 中文聲韻母拆分", "例：健保\nj,ian / b,ao"),
        ((1445, 190, 1810, 380), "4 族語音節拆分", "例：cinpaw\ncin / pa / w\nc,in / p,a / 0c,w"),
        ((300, 600, 680, 790), "5 動態規劃對齊", "維持音節順序\n找出總分最高的音節對應"),
        ((760, 600, 1140, 790), "6 中文缺失合併", "多出的族語音節\n嘗試向左或向右合併"),
        ((1220, 600, 1600, 790), "7 建立對照表", "統計 b→p、ian→in 等次數\n形成附錄一對照總表"),
        ((760, 935, 1140, 1115), "8 推薦與驗證", "依對照表產生候選音段\n用 LOOCV 評估正確率"),
    ]
    for xy, t, b in steps:
        fill = COLORS["light_blue"] if t.startswith(("1", "8")) else COLORS["light_green"]
        rounded_box(d, xy, t, b, fill=fill)
    for a, b in [((445,285),(535,285)),((900,285),(990,285)),((1355,285),(1445,285)),
                 ((1628,380),(490,600)),((680,695),(760,695)),((1140,695),(1220,695)),
                 ((1410,790),(950,935))]:
        arrow(d, a, b)
    save(img, "figure_3_loanword_pipeline.png")


def semantic_pipelines():
    img, d = base_canvas("單詞與詞組推薦流程比較", "單詞重視「辭典候選是否命中」；詞組重視「官方答案組件是否被找回」。")
    d.text((235, 175), "單詞推薦系統", font=font(36, True), fill=COLORS["blue"])
    d.text((1190, 175), "詞組推薦系統", font=font(36, True), fill=COLORS["blue"])
    left = [
        ("中文新詞", "例如：收養"),
        ("轉為中文語義向量", "SentenceTransformer 產生詞向量"),
        ("辭典中文釋義向量", "把族語辭典中的中文釋義轉成向量"),
        ("計算餘弦相似度", "依相似度排序候選族語詞"),
        ("輸出最佳候選", "評估是否命中官方新詞族語"),
    ]
    right = [
        ("中文詞組型新詞", "例如：高速公路"),
        ("GPT-OSS 拆解概念", "拆成：高速、道路等概念"),
        ("概念查找辭典候選", "與族語辭典中文釋義做相似度比對"),
        ("GPT-OSS 選擇組合", "由候選詞中組成 2 至 5 個族語詞"),
        ("組件命中評估", "比對官方答案中哪些組件被找回"),
    ]
    def lane(x, items):
        y = 245
        prev = None
        for idx, (t, b) in enumerate(items):
            rounded_box(d, (x, y, x + 620, y + 115), t, b, fill=COLORS["light_green"] if idx else COLORS["light_blue"])
            if prev:
                arrow(d, prev, (x + 310, y - 7))
            prev = (x + 310, y + 115)
            y += 150
    lane(110, left)
    lane(1110, right)
    d.line([(950, 210), (950, 1030)], fill=COLORS["line"], width=3)
    save(img, "figure_4_5_semantic_pipelines.png")


def dp_example():
    img, d = base_canvas("健保 / cinpaw 的動態規劃對齊示意", "紅色路徑代表最佳音節對齊；多出的族語音節先標為「中文缺失」，後續再嘗試合併。")
    # top labels
    d.text((150, 185), "中文：健保 → jian / bao", font=font(31, True), fill=COLORS["blue"])
    d.text((150, 235), "族語：cinpaw → cin / pa / w", font=font(31, True), fill=COLORS["green"])
    # table
    x0, y0 = 350, 340
    cw, ch = 260, 115
    headers = ["Start", "cin", "pa", "0c,w"]
    rows = ["Start", "jian", "bao"]
    vals = [
        ["0.00", "← 0.00", "← 0.00", "← 0.00"],
        ["↑ -9999", "↖ 1.50", "← 1.50", "← 1.50"],
        ["↑ -9999", "↑ -9999", "↖ 2.97", "← 2.97"],
    ]
    # draw grid
    for r in range(4):
        for c in range(5):
            x1 = x0 + c * cw
            y1 = y0 + r * ch
            x2 = x1 + cw
            y2 = y1 + ch
            fill = "#eaf3fb" if r == 0 or c == 0 else "#fffbe8"
            if (r, c) in [(1,1),(2,2),(3,3),(3,4)]:
                fill = "#fff2cc"
            d.rectangle((x1, y1, x2, y2), fill=fill, outline=COLORS["line"], width=3)
    # headers
    d.text((x0 + cw*0.5 - 45, y0 + 35), "", font=font(26, True), fill=COLORS["black"])
    for idx, h in enumerate(headers):
        d.text((x0 + (idx+1)*cw + 80, y0 + 35), h, font=font(30, True), fill=COLORS["black"])
    for idx, rname in enumerate(rows):
        d.text((x0 + 70, y0 + (idx+1)*ch + 35), rname, font=font(30, True), fill=COLORS["black"])
    for r, row in enumerate(vals):
        for c, val in enumerate(row):
            color = COLORS["red"] if (r, c) in [(0,0),(1,1),(2,2),(2,3)] else COLORS["gray"]
            d.text((x0 + (c+1)*cw + 55, y0 + (r+1)*ch + 35), val, font=font(28, True if color == COLORS["red"] else False), fill=color)
    # emphasize best-path cells without covering the numbers
    for r, c in [(1, 1), (2, 2), (3, 3), (3, 4)]:
        x1 = x0 + c * cw + 8
        y1 = y0 + r * ch + 8
        x2 = x1 + cw - 16
        y2 = y1 + ch - 16
        d.rounded_rectangle((x1, y1, x2, y2), radius=12, outline=COLORS["red"], width=4)
    # result boxes
    rounded_box(d, (185, 835, 650, 1045), "第一輪對齊", "jian 對 cin\nbao 對 pa\n0c,w 為中文缺失", fill=COLORS["light_blue"])
    rounded_box(d, (760, 835, 1225, 1045), "合併處理", "pa + w → paw\n重新計算 bao 對 paw", fill=COLORS["light_orange"], title_fill=COLORS["orange"])
    rounded_box(d, (1335, 835, 1800, 1045), "最終結果", "jian 對 cin\nbao 對 paw", fill=COLORS["light_green"])
    arrow(d, (650, 940), (760, 940))
    arrow(d, (1225, 940), (1335, 940))
    save(img, "figure_3_dp_alignment_example.png")


if __name__ == "__main__":
    data_preprocessing()
    system_overview()
    loanword_pipeline()
    semantic_pipelines()
    dp_example()
