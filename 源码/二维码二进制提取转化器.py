# -*- coding: utf-8 -*-
# =============================================================================
#  二维码二进制提取转化器 · QR ⇄ Binary Converter    v1.2
#  -------------------------------------------------------------------------
#  原始作者 / Original author : D_Chuan
#  版权     / Copyright       : (c) 2026 D_Chuan. All Rights Reserved.
#  使用许可 / License         : 仅限个人学习与非商业用途，禁止任何形式的商业使用；
#                              二创 / 衍生作品必须在源码中保留本原创声明（含作者与出处），
#                              并注明「基于 D_Chuan 的 二维码二进制提取转化器 修改」。
#                              完整条款见同目录 LICENSE。
#  联系方式 / Contact         : 1710079261@qq.com
#
#  ATTRIBUTION: 本文件中的图像定位与格点采样算法、矩阵结构校验、扫码自检、
#  三语词表与界面实现均为 D_Chuan 原创。任何二次分发或修改都必须保留本段信息。
# =============================================================================

"""
二维码二进制提取转化器  v1.2
-----------------------------------------
双向转换：
    图片二维码  ->  二进制矩阵（1=黑模块 0=白模块），并输出长/宽/高/位数等信息
    二进制数字  ->  二维码图片（支持智能识别粘贴的一整段混合文本、缩放导出）

作者：D_Chuan
仅依赖 Pillow，打包后为单文件免安装程序。
"""

import os
import re
import sys
import math
import tkinter as tk
from tkinter import filedialog, messagebox, font as tkfont

from PIL import Image, ImageDraw, ImageGrab, ImageOps, ImageTk

# 真实扫码引擎（zbar）：用来给每一张生成的二维码做"能不能扫"的硬校验
try:
    from pyzbar.pyzbar import decode as _zbar_decode
    SCANNER_OK = True
except Exception:
    _zbar_decode = None
    SCANNER_OK = False

# 标准二维码编码器（文字 -> 合法 QR 矩阵）
try:
    import qrcode
    from qrcode.constants import (ERROR_CORRECT_L, ERROR_CORRECT_M,
                                  ERROR_CORRECT_Q, ERROR_CORRECT_H)
    QRCODE_OK = True
except Exception:
    qrcode = None
    QRCODE_OK = False
    ERROR_CORRECT_L = ERROR_CORRECT_M = ERROR_CORRECT_Q = ERROR_CORRECT_H = None

APP_TITLE = "二维码二进制提取转化器"
APP_VERSION = "v1.2"
APP_ID = "QRBinaryConverter"

# 运行平台：windows / macos / linux。配置目录、图标格式、字体候选、窗口图标方式都按它分支。
if sys.platform.startswith("win"):
    PLATFORM = "windows"
elif sys.platform == "darwin":
    PLATFORM = "macos"
else:
    PLATFORM = "linux"

# 三平台的发行文件名（发布时按这个命名区分版本）
RELEASE_NAMES = {
    "windows": "QRBinaryConverter-%s-Windows-x64.exe" % APP_VERSION,
    "linux": "QRBinaryConverter-%s-Linux-x86_64" % APP_VERSION,
    "macos": "QRBinaryConverter-%s-macOS-%s" % (APP_VERSION, "arm64"),
}

EC_CHOICES = ("L", "M", "Q", "H")

# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
# ================================================================ 多语言
LANG_ORDER = ("zh_CN", "zh_TW", "en")
LANG_NAMES = {"zh_CN": "简体中文", "zh_TW": "繁體中文", "en": "English"}
_LANG_INDEX = {"zh_CN": 0, "zh_TW": 1, "en": 2}

# 每条为 (简体中文, 繁體中文, English)
STRINGS = {
    "app_title": ("二维码二进制提取转化器", "二維碼二進位提取轉換器", "QR ⇄ Binary Converter"),
    "subtitle": ("图片二维码 ⇄ 二进制矩阵 · 文字生成二维码 · 扫码自检",
                 "圖片二維碼 ⇄ 二進位矩陣 · 文字生成二維碼 · 掃碼自檢",
                 "Image QR ⇄ Binary Matrix · Text to QR · Scan Self-Check"),
    "sec1": ("图片  →  二进制数字", "圖片  →  二進位數字", "Image  →  Binary"),
    "sec2": ("内容  →  二维码图片", "內容  →  二維碼圖片", "Content  →  QR Image"),

    "open_image": ("打开图片", "開啟圖片", "Open Image"),
    "paste_image": ("从剪贴板粘贴", "從剪貼簿貼上", "Paste Image"),
    "redetect": ("重新识别", "重新辨識", "Re-detect"),
    "grid_on": ("网格: 开", "格線: 開", "Grid: On"),
    "grid_off": ("网格: 关", "格線: 關", "Grid: Off"),
    "copy_all": ("复制全部信息", "複製全部資訊", "Copy All Info"),
    "copy_bits": ("复制纯二进制", "複製純二進位", "Copy Bits Only"),
    "save_txt": ("保存为 TXT", "儲存為 TXT", "Save as TXT"),
    "to_right": ("填入右侧", "填入右側", "Send Right"),

    "tab_bits": ("二进制数字", "二進位數字", "Binary"),
    "tab_text": ("文字内容", "文字內容", "Text"),
    "hint_bits": ("智能识别：整段粘贴带长/宽/二进制的文本",
                 "智慧辨識：整段貼上含長/寬/二進位的文字",
                 "Smart parse: paste the whole block with size + bits"),
    "hint_text": ("输入任意文字，生成标准可扫二维码",
                 "輸入任意文字，生成標準可掃二維碼",
                 "Type any text to build a scannable QR"),
    "btn_recognize": ("智能识别并生成", "智慧辨識並生成", "Recognize & Generate"),
    "btn_fill_left": ("从左侧填入", "從左側填入", "Fill from Left"),
    "btn_clear": ("清空", "清空", "Clear"),
    "btn_paste_clip": ("粘贴剪贴板", "貼上剪貼簿", "Paste Clipboard"),
    "ec_label": ("纠错等级", "容錯等級", "Error Correction"),
    "ec_hint": ("L=容量最大  H=最难被遮挡破坏", "L=容量最大  H=最耐遮擋破壞",
                "L = max capacity · H = most resilient"),
    "btn_gen_text": ("生成二维码", "生成二維碼", "Generate QR"),
    "btn_fill_clip": ("从剪贴板填入", "從剪貼簿填入", "Fill from Clipboard"),

    "zoom": ("缩放", "縮放", "Zoom"),
    "unit_px": ("{px} px/模块", "{px} px/模組", "{px} px/module"),
    "save_png": ("保存 PNG", "儲存 PNG", "Save PNG"),
    "copy_qr_info": ("复制二维码信息", "複製二維碼資訊", "Copy QR Info"),
    "not_yet": ("尚未生成", "尚未生成", "Not generated yet"),

    "waiting": ("等待载入二维码图片…", "等待載入二維碼圖片…", "Waiting for an image…"),
    "info_ph": ("识别结果会显示在这里，可一键复制。",
                "辨識結果會顯示在這裡，可一鍵複製。",
                "The result appears here and can be copied in one click."),
    "recognizing": ("正在识别…", "正在辨識…", "Recognizing…"),
    "ph_left": ("点击「打开图片」，或用剪贴板粘贴二维码",
                "點擊「開啟圖片」，或用剪貼簿貼上二維碼",
                "Click \"Open Image\", or paste a QR from the clipboard"),
    "ph_right_bits": ("粘贴信息后点「智能识别并生成」", "貼上資訊後點「智慧辨識並生成」",
                      "Paste info, then click \"Recognize & Generate\""),
    "ph_right_text": ("输入文字后点「生成二维码」", "輸入文字後點「生成二維碼」",
                      "Type text, then click \"Generate QR\""),

    "st_recognized": ("已识别", "已辨識", "Recognized"),
    "left_status_tpl": ("{name} · {n}×{n} 模块 · {px} px/模块 · 定位图案 {f}%",
                        "{name} · {n}×{n} 模組 · {px} px/模組 · 定位圖案 {f}%",
                        "{name} · {n}×{n} modules · {px} px/module · finder {f}%"),
    "right_info_tpl": ("{n}×{n} 模块 · {px} px/模块 · 输出 {w}×{h} px · 总位数 {bits}",
                       "{n}×{n} 模組 · {px} px/模組 · 輸出 {w}×{h} px · 總位數 {bits}",
                       "{n}×{n} modules · {px} px/module · output {w}×{h} px · {bits} bits"),

    # 扫码自检
    "check_struct_fail": ("扫码自检：结构校验未通过（{p}），扫码器读不出这张图",
                          "掃碼自檢：結構校驗未通過（{p}），掃碼器讀不出這張圖",
                          "Scan check: structure failed ({p}) — scanners cannot read it"),
    "check_engine_missing": ("扫码自检：引擎未加载，仅结构校验通过",
                             "掃碼自檢：引擎未載入，僅結構校驗通過",
                             "Scan check: engine unavailable, structure passed only"),
    "check_decode_fail": ("扫码自检：未通过 · 这张图扫码器读不出内容（矩阵不是有效二维码）",
                          "掃碼自檢：未通過 · 這張圖掃碼器讀不出內容（矩陣不是有效二維碼）",
                          "Scan check: failed — the decoder reads nothing (matrix is not a valid QR)"),
    "check_text_ok": ("扫码自检：通过 · 与输入完全一致 · {d}",
                      "掃碼自檢：通過 · 與輸入完全一致 · {d}",
                      "Scan check: passed · identical to your input · {d}"),
    "check_text_bad": ("扫码自检：异常 · 扫出来是「{c}」，与输入不一致",
                       "掃碼自檢：異常 · 掃出來是「{c}」，與輸入不一致",
                       "Scan check: error — decoded \"{c}\", which differs from your input"),
    "check_bits_ok": ("扫码自检：通过 · 可扫 · 内容「{c}」",
                      "掃碼自檢：通過 · 可掃 · 內容「{c}」",
                      "Scan check: passed · decodable · \"{c}\""),
    "check_small_px": (" ｜{px}px/模块 太小，保存时自动放大", " ｜{px}px/模組 太小，儲存時自動放大",
                       "  | {px}px/module is too small; saving will upscale it"),
    "left_check_same": ("扫码自检：通过 · 与源图内容一致 · {c}",
                        "掃碼自檢：通過 · 與來源圖內容一致 · {c}",
                        "Scan check: passed · matches the source image · {c}"),
    "left_check_struct": ("扫码自检：结构校验未通过（{p}），这张图多半扫不出来",
                          "掃碼自檢：結構校驗未通過（{p}），這張圖多半掃不出來",
                          "Scan check: structure failed ({p}) — likely unreadable"),
    "left_check_fail_src_ok": ("扫码自检：重绘后扫不出内容（源图本身可解），矩阵可能有错位",
                              "掃碼自檢：重繪後掃不出內容（來源圖本身可解），矩陣可能有錯位",
                              "Scan check: redrawn QR undecodable while the source decodes — grid may be misaligned"),
    "left_check_fail_both": ("扫码自检：重绘后扫不出内容，源图也扫不出（可能太模糊或被裁）",
                             "掃碼自檢：重繪後掃不出內容，來源圖也掃不出（可能太模糊或被裁）",
                             "Scan check: neither the redrawn QR nor the source decodes (blurred or cropped?)"),
    "left_check_mismatch": ("扫码自检：重绘内容与源图不一致，请重新识别",
                            "掃碼自檢：重繪內容與來源圖不一致，請重新辨識",
                            "Scan check: redrawn content differs from the source — please re-detect"),
    "left_check_src_unreadable": ("扫码自检：通过（源图本身扫不出，重绘后可解）· {c}",
                                  "掃碼自檢：通過（來源圖本身掃不出，重繪後可解）· {c}",
                                  "Scan check: passed (source itself is unreadable, redrawn one decodes) · {c}"),
    "left_check_engine_missing": ("扫码自检：引擎未加载，仅做结构校验",
                                  "掃碼自檢：引擎未載入，僅做結構校驗",
                                  "Scan check: engine unavailable, structure check only"),

    # 复制文本里的字段
    "fi_header": ("========== 二维码二进制信息 ==========", "========== 二維碼二進位資訊 ==========",
                  "========== QR Binary Info =========="),
    "fi_type": ("类型: QR 二值矩阵 (1=黑模块, 0=白模块)", "類型: QR 二值矩陣 (1=黑模組, 0=白模組)",
                "Type: QR binary matrix (1=dark, 0=light)"),
    "fi_cols": ("长(列数): {n}", "長(列數): {n}", "Length(cols): {n}"),
    "fi_rows": ("宽(行数): {n}", "寬(行數): {n}", "Width(rows): {n}"),
    "fi_depth": ("高(位深): 1", "高(位深): 1", "Height(bit depth): 1"),
    "fi_module": ("模块像素: {px} px/模块", "模組像素: {px} px/模組", "Module size: {px} px/module"),
    "fi_size": ("图片尺寸: {w} × {h} px", "圖片尺寸: {w} × {h} px", "Image size: {w} × {h} px"),
    "fi_bits": ("总位数: {n}", "總位數: {n}", "Total bits: {n}"),
    "fi_finder": ("定位图案吻合: {v}%", "定位圖案吻合: {v}%", "Finder match: {v}%"),
    "fi_purity": ("模块纯度: {v}%", "模組純度: {v}%", "Module purity: {v}%"),
    "fi_conf": ("采样置信度: {v}%", "取樣置信度: {v}%", "Sample confidence: {v}%"),
    "fi_scan": ("扫码自检: {v}", "掃碼自檢: {v}", "Scan check: {v}"),
    "fi_matrix": ("二进制矩阵:", "二進位矩陣:", "Binary matrix:"),
    "sc_same_src": ("通过（与源图内容一致）", "通過（與來源圖內容一致）", "passed (matches source)"),
    "sc_pass": ("通过", "通過", "passed"),
    "sc_fail": ("未通过", "未通過", "failed"),
    "sc_struct": ("结构未通过", "結構未通過", "structure failed"),
    "sc_mismatch": ("内容不一致", "內容不一致", "content mismatch"),
    "sc_mismatch_input": ("与输入不一致", "與輸入不一致", "differs from input"),
    "sc_none": ("引擎未加载", "引擎未載入", "engine unavailable"),

    # 托盘/状态提示
    "msg_need_detect_copy": ("还没有识别结果可复制", "還沒有辨識結果可複製", "Nothing to copy yet"),
    "msg_need_detect_save": ("还没有识别结果可保存", "還沒有辨識結果可儲存", "Nothing to save yet"),
    "msg_need_detect": ("还没有识别结果", "還沒有辨識結果", "No result yet"),
    "msg_pick_image_first": ("请先打开一张二维码图片", "請先開啟一張二維碼圖片", "Open a QR image first"),
    "msg_copy_all_done": ("已复制全部信息（{n}×{n}）", "已複製全部資訊（{n}×{n}）",
                          "Copied all info ({n}×{n})"),
    "msg_copy_bits_done": ("已复制纯二进制 {b} 位", "已複製純二進位 {b} 位", "Copied {b} bits"),
    "msg_saved": ("已保存：{name}", "已儲存：{name}", "Saved: {name}"),
    "msg_fill_right": ("已填入右侧输入框", "已填入右側輸入框", "Sent to the right panel"),
    "msg_filled_left": ("已从左侧填入", "已從左側填入", "Filled from the left panel"),
    "msg_paste_chars": ("已粘贴 {c} 个字符", "已貼上 {c} 個字元", "Pasted {c} characters"),
    "msg_no_text_clip": ("剪贴板里没有文本", "剪貼簿裡沒有文字", "No text in the clipboard"),
    "msg_input_empty": ("输入框是空的，先粘贴内容", "輸入框是空的，請先貼上內容",
                        "The input box is empty — paste something first"),
    "msg_need_text_input": ("请先输入要生成二维码的文字", "請先輸入要生成二維碼的文字",
                            "Type some text first"),
    "msg_gen_done": ("已生成 {n}×{n} 二维码", "已生成 {n}×{n} 二維碼", "Generated a {n}×{n} QR"),
    "msg_gen_text_done": ("已按文字生成：版本 {v} · {n}×{n}", "已依文字生成：版本 {v} · {n}×{n}",
                          "Generated from text: version {v} · {n}×{n}"),
    "msg_saved_verified": ("已保存并复检通过：{name}", "已儲存並複檢通過：{name}",
                           "Saved and re-verified: {name}"),
    "msg_saved_bumped": ("（已自动放大到 {px} px/模块 以保证可扫描）",
                         "（已自動放大到 {px} px/模組 以確保可掃描）",
                         " (auto-upscaled to {px} px/module to keep it scannable)"),
    "msg_saved_no_verify": ("已保存，但复检未能解码，请换更大尺寸再存",
                            "已儲存，但複檢未能解碼，請換更大尺寸再存",
                            "Saved, but re-check failed to decode — try a larger size"),
    "msg_parse_fail": ("解析失败：{e}", "解析失敗：{e}", "Parse failed: {e}"),
    "msg_gen_fail": ("生成失败：{e}", "生成失敗：{e}", "Generation failed: {e}"),

    # 对话框
    "dlg_open": ("选择二维码图片", "選擇二維碼圖片", "Choose a QR image"),
    "dlg_save_txt": ("保存二进制信息", "儲存二進位資訊", "Save binary info"),
    "dlg_save_png": ("保存二维码图片", "儲存二維碼圖片", "Save QR image"),
    "ft_images": ("图片文件", "圖片檔案", "Image files"),
    "ft_all": ("所有文件", "所有檔案", "All files"),
    "ft_txt": ("文本文件", "文字檔案", "Text files"),
    "ft_png": ("PNG 图片", "PNG 圖片", "PNG image"),
    "err_open": ("图片打开失败：{e}", "圖片開啟失敗：{e}", "Failed to open the image: {e}"),
    "err_no_image_clip": ("剪贴板里没有图片（可先截图再按 Ctrl+V 复制图片）",
                          "剪貼簿裡沒有圖片（可先截圖再按 Ctrl+V 複製圖片）",
                          "No image in the clipboard (take a screenshot, then press Ctrl+V)"),
    "err_recognize": ("识别失败：{e}", "辨識失敗：{e}", "Detection failed: {e}"),
    "err_struct_save": ("这张矩阵结构不合法（{p}），保存出来也扫不出正确内容，已取消保存。\n请检查二进制数据是否完整、是否来自真正的二维码。",
                        "這張矩陣結構不合法（{p}），儲存出來也掃不出正確內容，已取消儲存。\n請檢查二進位資料是否完整、是否來自真正的二維碼。",
                        "This matrix is structurally invalid ({p}); the saved file could not be scanned correct. Save cancelled.\nCheck that the binary data is complete and comes from a real QR code."),
    "err_unscannable": ("扫码引擎在 4~24 px/模块 各档都读不出这张图，已取消保存。",
                        "掃碼引擎在 4~24 px/模組 各檔都讀不出這張圖，已取消儲存。",
                        "The decoder cannot read this image at any 4–24 px/module setting. Save cancelled."),
    "err_no_encoder": ("缺少二维码编码库，无法从文字生成", "缺少二維碼編碼庫，無法從文字生成",
                       "QR encoder library missing; cannot generate from text"),
    "err_copy": ("复制失败：{e}", "複製失敗：{e}", "Copy failed: {e}"),
    "err_cfg": ("无法保存语言设置：{e}", "無法儲存語言設定：{e}", "Could not save the language setting: {e}"),
    "list_sep": ("、", "、", ", "),

    # 语言
    "lang_button": ("语言: {name}", "語言: {name}", "Language: {name}"),
    "lang_title": ("语言 / Language", "語言 / Language", "Language / 語言"),
    "lang_prompt": ("请选择界面语言 · Please choose the interface language",
                    "請選擇介面語言 · Please choose the interface language",
                    "Please choose the interface language · 請選擇介面語言"),
    "lang_note": ("可随时通过标题栏右侧的语言按钮切换 · Switch anytime from the title bar",
                  "可隨時透過標題列右側的語言按鈕切換 · Switch anytime from the title bar",
                  "Switch anytime from the title bar · 可随时通过标题栏右侧的语言按钮切换"),
}


def t_(lang, key, **kw):
    """取某条文案；字典缺失时原样返回 key，便于发现漏翻。"""
    item = STRINGS.get(key)
    if not item:
        return key
    text = item[_LANG_INDEX.get(lang, 0)]
    if kw:
        try:
            text = text.format(**kw)
        except Exception:
            pass
    return text


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def config_dir():
    """按平台取配置目录：Windows 用 %APPDATA%，macOS 用 ~/Library/Application Support，
    Linux 用 $XDG_CONFIG_HOME（缺省 ~/.config）。"""
    if PLATFORM == "windows":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_ID)
    if PLATFORM == "macos":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_ID)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "qr-binary-converter")


def config_path():
    return os.path.join(config_dir(), "config.json")


def load_lang():
    try:
        import json
        p = config_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            lang = data.get("lang")
            if lang in LANG_ORDER:
                return lang
    except Exception:
        pass
    return None


def save_lang(lang):
    try:
        import json
        p = config_path()
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# ---------------------------------------------------------------- 配色
BG = "#080c14"
BG2 = "#0c131f"
CARD = "#0f1724"
BORDER = "#1c2c42"
FG = "#e8f4ff"
MUTED = "#74889f"
ACCENT = "#00e0ff"
ACCENT_D = "#0b6b7d"
ACCENT2 = "#3d7bff"
OK = "#33d6a4"
WARN = "#ffb02e"
ERR = "#ff5c7a"

FINDER_PATTERN = (
    "1111111",
    "1000001",
    "1011101",
    "1011101",
    "1011101",
    "1000001",
    "1111111",
)

_FW_MAP = {ord("０") + i: ord("0") + i for i in range(10)}
_FW_MAP.update({
    ord("："): ord(":"), ord("，"): ord(","), ord("；"): ord(";"),
    ord("　"): ord(" "), ord("（"): ord("("), ord("）"): ord(")"),
    ord("　"): ord(" "), ord("－"): ord("-"), ord("＋"): ord("+"),
    ord("＝"): ord("="), ord("、"): ord(","),
})


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
# ================================================================ 图像算法
def _prepare(img):
    """统一成 RGB / L，透明底合成到白底。"""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        return bg.convert("RGB")
    return img.convert("RGB")


def otsu_threshold(hist):
    total = sum(hist)
    if total <= 0:
        return 128
    sum_all = sum(i * h for i, h in enumerate(hist))
    w_b = 0
    sum_b = 0
    best_var = -1.0
    best_thr = 128
    for i in range(256):
        w_b += hist[i]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += i * hist[i]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best_var:
            best_var = var
            best_thr = i
    return best_thr


def _threshold_estimate(gray):
    """
    用 3% / 97% 分位的中点作为二值阈值。
    纯黑白图的直方图只有 0 和 255 两档，Otsu 会退化到 0，这里更稳。
    """
    hist = gray.histogram()
    total = sum(hist)
    if total <= 0:
        return None
    acc = 0
    lo = None
    hi = 255
    for i, h in enumerate(hist):
        acc += h
        if lo is None and acc >= total * 0.03:
            lo = i
        if acc >= total * 0.97:
            hi = i
            break
    if lo is None:
        lo = 0
    if hi - lo < 20:
        return None
    return int((lo + hi) / 2.0 + 0.5)


def _run_length(px, size, x, y, dx, dy, thr):
    """从 (x,y) 沿着 (dx,dy) 数连续暗像素个数。"""
    w, h = size
    n = 0
    fx, fy = float(x), float(y)
    while 0 <= fx < w and 0 <= fy < h:
        if px[int(fx), int(fy)] < thr:
            n += 1
        else:
            break
        fx += dx
        fy += dy
    return n


def _sample_matrix(flat, side, n, thr, dense=True, shift=(0.0, 0.0)):
    """
    把 side×side 的灰度字节数组切成 n×n 模块，返回 (bits, confidence, purity)。
    purity = 每个模块内部采样点的“纯色占比”平均值；网格对得准时接近 1，
    错位时模块会跨到相邻模块而明显下降，用来排除模块数选错、以及做亚像素对齐。
    """
    m = side / float(n)
    offs = (0.28, 0.5, 0.72) if dense else (0.5,)
    sx, sy = shift
    bits = []
    conf_sum = 0.0
    purity_sum = 0.0
    for r in range(n):
        row = []
        base_y = r * m + sy
        for c in range(n):
            base_x = c * m + sx
            s = 0
            k = 0
            dark = 0
            for dy in offs:
                yy = int(base_y + dy * m)
                yy = 0 if yy < 0 else (side - 1 if yy >= side else yy)
                line = yy * side
                for dx in offs:
                    xx = int(base_x + dx * m)
                    xx = 0 if xx < 0 else (side - 1 if xx >= side else xx)
                    v = flat[line + xx]
                    s += v
                    k += 1
                    if v < thr:
                        dark += 1
            row.append(1 if dark * 2 >= k else 0)
            conf_sum += abs(s / k - 127.5) / 127.5
            purity_sum += max(dark, k - dark) / float(k)
        bits.append(row)
    conf = conf_sum / float(n * n)
    purity = purity_sum / float(n * n)
    return bits, conf, purity


def _refine_shift(flat, side, n, thr, base=(0.0, 0.0)):
    """在一个模块以内做亚像素级对齐搜索，消除 bbox 偏移造成的落点偏差。"""
    m = side / float(n)
    step = max(1, int(math.sqrt(max(1, n * n / 220.0))))
    cells = [(r, c) for r in range(0, n, step) for c in range(0, n, step)]
    offs = (0.28, 0.5, 0.72)
    best = (base[0], base[1], -1.0)
    for sy in (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5):
        for sx in (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5):
            pure = 0.0
            for (r, c) in cells:
                base_x = c * m + sx
                base_y = r * m + sy
                dark = 0
                k = 0
                for dy in offs:
                    yy = int(base_y + dy * m)
                    yy = 0 if yy < 0 else (side - 1 if yy >= side else yy)
                    line = yy * side
                    for dx in offs:
                        xx = int(base_x + dx * m)
                        xx = 0 if xx < 0 else (side - 1 if xx >= side else xx)
                        k += 1
                        if flat[line + xx] < thr:
                            dark += 1
                pure += max(dark, k - dark) / float(k)
            pure /= float(len(cells))
            if pure > best[2]:
                best = (sx, sy, pure)
    return best[0], best[1]


def _finder_ratio(bits, n):
    """校验三个角上的 7×7 定位图案，返回吻合比例 (0~1)。"""
    if n < 9:
        return 0.0
    total = 0
    hit = 0
    for (r0, c0) in ((0, 0), (0, n - 7), (n - 7, 0)):
        for i in range(7):
            for j in range(7):
                total += 1
                if bits[r0 + i][c0 + j] == (1 if FINDER_PATTERN[i][j] == "1" else 0):
                    hit += 1
    return hit / float(total)


def _valid_sizes():
    return list(range(21, 178, 4))


def _nearest_size(v):
    sizes = _valid_sizes()
    return min(sizes, key=lambda s: abs(s - v))


def _square_crop(gray, box, delta):
    """按 bbox 取方形区域，delta = (左, 上, 右, 下) 的像素微调。"""
    w, h = gray.size
    x0, y0, x1, y1 = box
    x0 += delta[0]
    y0 += delta[1]
    x1 += delta[2]
    y1 += delta[3]
    x0 = max(0, min(w - 1, x0))
    y0 = max(0, min(h - 1, y0))
    x1 = max(x0 + 1, min(w, x1))
    y1 = max(y0 + 1, min(h, y1))
    bw, bh = x1 - x0, y1 - y0
    side = max(bw, bh)
    sq = Image.new("L", (side, side), 255)
    sq.paste(gray.crop((x0, y0, x1, y1)), ((side - bw) // 2, (side - bh) // 2))
    return sq, (x0, y0, side)


def _module_px_estimate(px, size, thr):
    """用左上定位图案最外侧的那条 7 模块黑边，估算单个模块的像素宽度。"""
    w, h = size
    horiz = 0
    for y in range(0, min(5, h)):
        if px[0, y] < thr:
            horiz = max(horiz, _run_length(px, size, 0, y, 1, 0, thr))
    vert = 0
    for x in range(0, min(5, w)):
        if px[x, 0] < thr:
            vert = max(vert, _run_length(px, size, x, 0, 0, 1, thr))
    vals = [v / 7.0 for v in (horiz, vert) if v >= 4]
    return sum(vals) / len(vals) if vals else 0.0


def _candidate_sizes(side, module_px_est, wide=False):
    """候选模块数：先由估算值取邻近几档，估算失败时全量扫描。"""
    sizes = _valid_sizes()
    cap = [s for s in sizes if side / float(s) >= 1.0]
    if not cap:
        return []
    if module_px_est > 1.2 and not wide:
        idx = sizes.index(_nearest_size(int(round(side / module_px_est))))
        out = []
        for d in (-2, -1, 0, 1, 2):
            i = idx + d
            if 0 <= i < len(sizes) and sizes[i] in cap:
                out.append(sizes[i])
        if out:
            return out
    return cap


def _score_candidate(flat, side, thr, n):
    """对一个候选模块数打分：定位图案吻合 + 模块纯度 + 采样置信度。"""
    if side / float(n) < 1.0:
        return None
    bits, conf, purity = _sample_matrix(flat, side, n, thr, dense=True)
    fr = _finder_ratio(bits, n)
    score = fr * 2.0 + purity * 4.0 + conf * 0.6
    if fr >= 0.985 and purity >= 0.98:
        score += 1.0
    return score, bits, conf, purity, fr


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def _detect_core(gray):
    """单极性识别：阈值 -> 暗区 bbox -> 候选模块数打分。失败抛 ValueError。"""
    thr = _threshold_estimate(gray)
    if thr is None:
        raise ValueError("图片几乎是纯色，找不到二维码的黑白模块")

    mask = gray.point(lambda v: 255 if v < thr else 0)
    bbox = mask.getbbox()
    if not bbox:
        raise ValueError("图片里没有找到暗色模块，无法识别二维码")

    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if bw < 21 or bh < 21:
        raise ValueError("二维码区域太小（%d×%d 像素），请换成更清晰的图片" % (bw, bh))

    deltas = ((0, 0, 0, 0), (-1, -1, 1, 1), (-2, -2, 2, 2), (1, 1, -1, -1))
    best = None
    for delta in deltas:
        sq, bb = _square_crop(gray, bbox, delta)
        side = sq.size[0]
        px = sq.load()
        flat = sq.tobytes()
        est = _module_px_estimate(px, sq.size, thr)
        for n in _candidate_sizes(side, est):
            got = _score_candidate(flat, side, thr, n)
            if got is None:
                continue
            score, bits, conf, purity, fr = got
            if best is None or score > best[0]:
                best = (score, n, conf, fr, purity, bits, sq, side, bb)
        if best is not None and best[0] >= 7.55:
            break

    if best is None:  # 兜底：全量候选扫一遍
        sq, bb = _square_crop(gray, bbox, (0, 0, 0, 0))
        side = sq.size[0]
        flat = sq.tobytes()
        for n in _candidate_sizes(side, 0.0, wide=True):
            got = _score_candidate(flat, side, thr, n)
            if got is None:
                continue
            score, bits, conf, purity, fr = got
            if best is None or score > best[0]:
                best = (score, n, conf, fr, purity, bits, sq, side, bb)

    if best is None:
        raise ValueError("无法确定二维码的模块数量，请换一张更清晰、正对拍摄的图片")

    score, n, conf, fr, purity, bits, sq, side, bb = best

    if purity < 0.995 and side / float(n) >= 1.6:
        flat = sq.tobytes()
        sx, sy = _refine_shift(flat, side, n, thr)
        if sx or sy:
            bits2, conf, purity2 = _sample_matrix(flat, side, n, thr, dense=True, shift=(sx, sy))
            fr2 = _finder_ratio(bits2, n)
            if purity2 >= purity or fr2 > fr:
                bits, purity, fr = bits2, purity2, fr2

    black = sum(sum(r) for r in bits)
    if black == 0 or black == n * n:
        raise ValueError("识别出的矩阵全是同一色，请换一张二维码图片")

    return {
        "n": n,
        "bits": bits,
        "bbox": bb,
        "module_px": side / float(n),
        "finder": fr,
        "conf": conf,
        "purity": purity,
        "_score": score,
        "threshold": thr,
    }


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def detect_qr_matrix(pil_img):
    """
    从二维码图片中提取模块矩阵。黑底白码会自动反相后再试一次。
    返回 dict: n, bits, bbox(x,y,side), module_px, finder, conf, inverted, threshold, size
    """
    rgb = _prepare(pil_img)
    base = rgb.convert("L")

    first_error = None
    result = None
    best_key = None
    for inverted in (False, True):
        g = ImageOps.invert(base) if inverted else base
        try:
            d = _detect_core(g)
        except ValueError as e:
            if first_error is None:
                first_error = e
            continue
        d["inverted"] = inverted
        key = d["_score"] - (0.15 if inverted else 0.0)
        if result is None or key > best_key:
            result = d
            best_key = key
        if not inverted and d["_score"] >= 7.4:
            break  # 正常极性已是满分，不用再试反相

    if result is None:
        raise first_error or ValueError("无法识别这张图片里的二维码")

    result["size"] = rgb.size
    return result


def _valid_n(n):
    return 21 <= n <= 177 and (n - 21) % 4 == 0


V_TEXT = {
    "square": ("矩阵不是正方形", "矩陣不是正方形", "the matrix is not square"),
    "bad_n": ("模块数 {n} 不是合法档位（21、25 … 177）",
              "模組數 {n} 不是合法等級（21、25 … 177）",
              "{n} is not a valid QR size (21, 25 … 177)"),
    "finder": ("{pos}定位图案不完整", "{pos}定位圖案不完整",
               "{pos} finder pattern is incomplete"),
    "sep": ("{pos}分隔符不干净", "{pos}分隔符不乾淨",
            "{pos} separator is not clean"),
    "timing_h": ("水平时序图案错位", "水平時序圖案錯位",
                 "horizontal timing pattern is misaligned"),
    "timing_v": ("垂直时序图案错位", "垂直時序圖案錯位",
                 "vertical timing pattern is misaligned"),
    "dark": ("右下固定暗模块缺失", "右下固定暗模組缺失",
             "bottom-right dark module is missing"),
    "desc": ("版本 {v} · {n}×{n} 模块", "版本 {v} · {n}×{n} 模組",
             "version {v} · {n}×{n} modules"),
    "pos_tl": ("左上", "左上", "top-left"),
    "pos_tr": ("右上", "右上", "top-right"),
    "pos_bl": ("左下", "左下", "bottom-left"),
}


def vt_(lang, key, **kw):
    idx = _LANG_INDEX.get(lang, 0)
    return V_TEXT[key][idx].format(**kw)


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def validate_matrix(bits, lang="zh_CN"):
    """
    二维码结构校验：三个定位图案、分隔符、时序图案、固定暗模块。
    这些是任何一台扫码器进入解码前的"门面"，缺一不可。
    返回 (ok, problems, 描述)
    """
    problems = []
    n = len(bits)
    if n == 0 or any(len(r) != n for r in bits):
        return False, [vt_(lang, "square")], ""
    if not _valid_n(n):
        return False, [vt_(lang, "bad_n", n=n)], ""

    for pos, (r0, c0) in (("pos_tl", (0, 0)), ("pos_tr", (0, n - 7)), ("pos_bl", (n - 7, 0))):
        bad = False
        for i in range(7):
            for j in range(7):
                want = 1 if FINDER_PATTERN[i][j] == "1" else 0
                if bits[r0 + i][c0 + j] != want:
                    bad = True
                    break
            if bad:
                break
        if bad:
            problems.append(vt_(lang, "finder", pos=vt_(lang, pos)))

    def blank(r0, r1, c0, c1):
        for r in range(max(0, r0), min(n, r1)):
            for c in range(max(0, c0), min(n, c1)):
                if bits[r][c]:
                    return False
        return True

    if not blank(7, 8, 0, 8) or not blank(0, 8, 7, 8):
        problems.append(vt_(lang, "sep", pos=vt_(lang, "pos_tl")))
    if not blank(7, 8, n - 8, n) or not blank(0, 8, n - 8, n - 7):
        problems.append(vt_(lang, "sep", pos=vt_(lang, "pos_tr")))
    if not blank(n - 8, n - 7, 0, 8) or not blank(n - 7, n, 7, 8):
        problems.append(vt_(lang, "sep", pos=vt_(lang, "pos_bl")))

    for c in range(8, n - 8):
        if bits[6][c] != (1 if c % 2 == 0 else 0):
            problems.append(vt_(lang, "timing_h"))
            break
    for r in range(8, n - 8):
        if bits[r][6] != (1 if r % 2 == 0 else 0):
            problems.append(vt_(lang, "timing_v"))
            break

    if bits[n - 8][8] != 1:
        problems.append(vt_(lang, "dark"))

    version = (n - 17) // 4
    desc = vt_(lang, "desc", v=version, n=n)
    return (not problems), problems, desc


def _fix_mojibake(text):
    """有些编码器会把 UTF-8 再编码一次，读出来是乱码；这里尝试还原。"""
    if not text:
        return text
    if all(ord(ch) < 128 for ch in text):
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
    except Exception:
        return text
    return fixed if fixed else text


def _text_variants(text):
    """同一段内容在不同字符集下的几种可能写法，用于宽窄比对比。"""
    out = {text}
    for codec in ("latin-1", "gbk", "shift_jis", "cp932", "big5"):
        try:
            out.add(text.encode(codec).decode("utf-8"))
        except Exception:
            pass
    try:
        out.add(text.encode("utf-8").decode("gbk"))
    except Exception:
        pass
    try:
        out.add(text.encode("utf-8").decode("shift_jis"))
    except Exception:
        pass
    return out


def texts_match(a, b):
    """比较两段扫码内容是否指的是同一份文本（容忍扫码器字符集误判）。"""
    if a is None or b is None:
        return False
    if a == b:
        return True
    return bool(_text_variants(a) & _text_variants(b))


def align_text(got, source):
    """如果只是字符集误判，把扫码结果改写成原本输入的样子再展示。"""
    if got == source:
        return got
    for v in _text_variants(got):
        if v == source:
            return v
    return got


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def scan_decode(img):
    """
    用 zbar（真实扫码器同一个引擎）解码一张图，黑白反相也会试一次。
    返回 (ok, contents[list], error)
    """
    if not SCANNER_OK:
        return False, [], "缺少扫码引擎"
    try:
        base = _prepare(img).convert("L")
    except Exception as e:
        return False, [], "图像转换失败：%s" % e

    found = []
    for inverted in (False, True):
        g = ImageOps.invert(base) if inverted else base
        try:
            res = _zbar_decode(g)
        except Exception as e:
            return False, [], "扫码引擎出错：%s" % e
        for r in res:
            try:
                txt = r.data.decode("utf-8")
            except Exception:
                txt = r.data.decode("latin-1", "ignore")
            txt = _fix_mojibake(txt)
            if txt not in found:
                found.append(txt)
        if found:
            break
    return (len(found) > 0), found, ""


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def qr_from_text(text, ec="M", version=None):
    """文字 -> 标准二维码矩阵，返回 (版本号, n, bits)。用标准编码器保证合法。"""
    if not QRCODE_OK:
        raise ValueError("缺少二维码编码库 qrcode，无法从文字生成二维码")
    body = text.rstrip("\n")
    if not body.strip():
        raise ValueError("请先输入要生成二维码的文字")
    level = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M,
             "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}[ec]
    q = qrcode.QRCode(version=version, error_correction=level, box_size=1, border=0)
    q.add_data(body, optimize=0)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    if not _valid_n(n):
        raise ValueError("内容太长，超出二维码最大容量（177×177）")
    bits = [[1 if m[r][c] else 0 for c in range(n)] for r in range(n)]
    return q.version, n, bits


def render_qr(bits, module_px=8, quiet=4, fg=(0, 0, 0), bg=(255, 255, 255)):
    """把 n×n 二进制矩阵画成标准二维码图片（四周留 quiet 模块静区）。"""
    n = len(bits)
    total = (n + quiet * 2) * module_px
    img = Image.new("RGB", (total, total), bg)
    d = ImageDraw.Draw(img)
    for r in range(n):
        row = bits[r]
        c = 0
        while c < n:
            if row[c]:
                start = c
                while c < n and row[c]:
                    c += 1
                x_start = (quiet + start) * module_px
                x_end = (quiet + c) * module_px - 1
                y0 = (quiet + r) * module_px
                y1 = y0 + module_px - 1
                d.rectangle([x_start, y0, x_end, y1], fill=fg)
            else:
                c += 1
    return img


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
# ================================================================ 文本 <-> 矩阵
def to_halfwidth(text):
    return text.translate(_FW_MAP)


def format_info(det, lang="zh_CN"):
    n = det["n"]
    lines = [
        t_(lang, "fi_header"),
        t_(lang, "fi_type"),
        t_(lang, "fi_cols", n=n),
        t_(lang, "fi_rows", n=n),
        t_(lang, "fi_depth"),
        t_(lang, "fi_module", px="%.2f" % det["module_px"]),
        t_(lang, "fi_size", w=det["size"][0], h=det["size"][1]),
        t_(lang, "fi_bits", n=n * n),
        t_(lang, "fi_finder", v="%.1f" % (det["finder"] * 100)),
        t_(lang, "fi_purity", v="%.1f" % (det.get("purity", 1.0) * 100)),
        t_(lang, "fi_conf", v="%.1f" % (det["conf"] * 100)),
    ]
    code = det.get("scan_code")
    if code:
        lines.append(t_(lang, "fi_scan", v=t_(lang, "sc_" + code)))
    lines.append("-" * 38)
    lines.append(t_(lang, "fi_matrix"))
    for row in det["bits"]:
        lines.append("".join("1" if v else "0" for v in row))
    return "\n".join(lines)


def bits_debug(det):
    n = det["n"]
    return "\n".join("".join("1" if v else "0" for v in row) for row in det["bits"])


def extract_bits(text):
    """从混杂文本里找出二进制串：优先取只含 0/1 的整行，其次取连续的 0/1 数据块。"""
    text = to_halfwidth(text)
    rows = []
    for line in text.splitlines():
        s = re.sub(r"[\s,;|_\-]+", "", line)
        if len(s) >= 21 and re.fullmatch(r"[01]+", s):
            rows.append(s)
    if rows:
        return "".join(rows)
    # 整段只由 0/1 与空白/分隔符组成的数据块（一行里带前缀或空格分组的情况）
    blocks = re.findall(r"[01](?:[01\s,;|_\-]{19,})[01]", text)
    if blocks:
        best = max(blocks, key=lambda b: len(re.sub(r"[\s,;|_\-]+", "", b)))
        clean = re.sub(r"[\s,;|_\-]+", "", best)
        if len(clean) >= 21:
            return clean
    runs = re.findall(r"[01]{21,}", text)
    return max(runs, key=len) if runs else ""


P_TEXT = {
    "no_bits": ("没有解析到二进制数字，请确认内容里包含连续的 0/1 串",
                "沒有解析到二進位數字，請確認內容裡包含連續的 0/1 串",
                "No binary digits found — make sure the pasted text contains a run of 0/1 digits"),
    "bad_count": ("二进制位数 {c} 不是合法的二维码方阵（应为 21×21=441、25×25=625 … 177×177=31329）。"
                  "请确认 0/1 串没有被截断、也没有混进别的数字；也可以在文本里写明“长(列数): N”。",
                  "二進位位數 {c} 不是合法的二維碼方陣（應為 21×21=441、25×25=625 … 177×177=31329）。"
                  "請確認 0/1 串沒有被截斷、也沒有混進別的數字；也可以在文字裡寫明「長(列數): N」。",
                  "The binary string has {c} digits, which is not a valid QR square "
                  "(21×21=441, 25×25=625 … 177×177=31329). Check that the 0/1 run is not truncated "
                  "and that no other digits slipped in — or state “Length: N” in the text."),
    "mismatch": ("二进制位数 {c} 与 {n}×{n}={e} 不符（差 {d} 位），为避免画出错误的二维码，已停止生成。"
                 "请检查 0/1 串是否完整。",
                 "二進位位數 {c} 與 {n}×{n}={e} 不符（差 {d} 位），為避免畫出錯誤的二維碼，已停止產生。"
                 "請檢查 0/1 串是否完整。",
                 "The binary string has {c} digits but a {n}×{n} QR needs {e} (off by {d}); "
                 "generation stopped so no wrong QR gets produced. Check that the 0/1 run is complete."),
}


def pt_(lang, key, **kw):
    idx = _LANG_INDEX.get(lang, 0)
    return P_TEXT[key][idx].format(**kw)


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def parse_info(text, lang="zh_CN"):
    """
    智能解析用户一股脑粘贴的内容。
    返回 (n, bits) ；解析失败抛 ValueError。
    """
    text = to_halfwidth(text)
    bits_str = extract_bits(text)
    if not bits_str:
        raise ValueError(pt_(lang, "no_bits"))

    count = len(bits_str)
    root = int(math.isqrt(count))
    n = None
    if root * root == count and _valid_n(root):
        n = root

    if n is None:
        # 只认"长/宽/行/列/模块/尺寸"这类标签后面的数字，且必须刚好等于 count
        for m in re.finditer(r"(?:长|宽|行|列|模块|尺寸|边长|長|寬|模組|邊長|Length|Width|Rows?|Cols?|Columns?|Module|Size)"
                             r"\s*[（(]?[^:：\d\n]{0,12}(\d{2,3})", text, re.IGNORECASE):
            v = int(m.group(1))
            if _valid_n(v) and v * v == count:
                n = v
                break

    if n is None:
        raise ValueError(pt_(lang, "bad_count", c=count))

    expect = n * n
    if count != expect:
        # 不静默截断/补零：那会让画出来的码扫出别的内容或干脆扫不出
        raise ValueError(pt_(lang, "mismatch", c=count, n=n, e=expect, d=expect - count))

    bits = [[1 if ch == "1" else 0 for ch in bits_str[r * n:(r + 1) * n]] for r in range(n)]
    return n, bits


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
# ================================================================ 字体 / 路径
# 三平台各自的字体候选（按优先级排列，取第一个系统里存在的）
UI_FONT_CANDIDATES = {
    "windows": ["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"],
    "macos": ["PingFang SC", "Hiragino Sans GB", "Heiti SC", "Helvetica Neue"],
    "linux": ["Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
              "WenQuanYi Zen Hei", "DejaVu Sans"],
}[PLATFORM]

MONO_FONT_CANDIDATES = {
    "windows": ["Consolas", "Cascadia Mono", "Courier New"],
    "macos": ["Menlo", "Monaco", "SF Mono", "Courier New"],
    "linux": ["DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono", "Courier New"],
}[PLATFORM]


def pick_font(root, candidates, fallback="TkDefaultFont"):
    fams = set()
    try:
        fams = set(tkfont.families(root))
    except Exception:
        pass
    for c in candidates:
        if c in fams:
            return c
    return fallback


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def icon_path():
    """Windows 用 .ico；macOS / Linux 用 .png（iconbitmap 只认 ico）。"""
    return resource_path("app.ico" if PLATFORM == "windows" else "app.png")


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def apply_window_icon(win):
    """给窗口设置图标：Windows 走 iconbitmap，macOS / Linux 走 iconphoto。失败不影响启动。"""
    ico = resource_path("app.ico")
    png = resource_path("app.png")
    if PLATFORM == "windows":
        try:
            if os.path.exists(ico):
                win.iconbitmap(ico)
                return
        except Exception:
            pass
    try:
        if os.path.exists(png):
            img = tk.PhotoImage(file=png)
            win.iconphoto(True, img)
            win._icon_photo = img          # 必须持引用，否则会被回收
            return
    except Exception:
        pass
    try:
        if os.path.exists(ico):
            win.iconbitmap(ico)
    except Exception:
        pass


class Slider(tk.Canvas):
    """深色皮肤下自绘的水平滑杆。"""

    def __init__(self, master, from_=1, to=40, value=8, command=None, bg=CARD):
        tk.Canvas.__init__(self, master, height=24, bg=bg,
                           highlightthickness=0, bd=0, cursor="hand2")
        self.from_, self.to_ = from_, to
        self.value = value
        self.command = command
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)

    def _x_range(self):
        return 7.0, max(8.0, self.winfo_width() - 7.0)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 20:
            return
        x0, x1 = self._x_range()
        mid = self.winfo_height() / 2.0
        self.create_line(x0, mid, x1, mid, fill="#1b2c42", width=4, capstyle="round")
        frac = (self.value - self.from_) / float(self.to_ - self.from_)
        kx = x0 + frac * (x1 - x0)
        self.create_line(x0, mid, kx, mid, fill="#0d7f92", width=4, capstyle="round")
        r = 6
        self.create_oval(kx - r, mid - r, kx + r, mid + r,
                         fill=ACCENT, outline="#04515c", width=1)
        self.create_oval(kx - 2, mid - 8, kx + 2, mid - 4, fill="#8ff3ff", outline="")

    def _value_at(self, x):
        x0, x1 = self._x_range()
        frac = (x - x0) / max(1.0, (x1 - x0))
        frac = min(1.0, max(0.0, frac))
        return int(round(self.from_ + frac * (self.to_ - self.from_)))

    def _on_press(self, event):
        self.set(self._value_at(event.x))

    def _on_drag(self, event):
        self.set(self._value_at(event.x))

    def set(self, value, notify=True):
        value = max(self.from_, min(self.to_, int(value)))
        if value == self.value and notify:
            self._draw()
            return
        self.value = value
        self._draw()
        if notify and self.command:
            self.command(value)


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
class LanguageDialog(tk.Toplevel):
    """语言选择框：首次启动时询问，也可随时从标题栏调出。"""

    SAMPLES = {"zh_CN": "图片二维码 ⇄ 二进制数字",
               "zh_TW": "圖片二維碼 ⇄ 二進位數字",
               "en": "Image QR ⇄ Binary"}

    def __init__(self, master, current=None):
        tk.Toplevel.__init__(self, master)
        self.choice = current or "zh_CN"
        self.current = current
        self.font = pick_font(self, UI_FONT_CANDIDATES)

        self.configure(bg=BG)
        self.title(t_("en", "lang_title"))
        self.resizable(False, False)
        apply_window_icon(self)
        try:
            self.transient(master)
        except Exception:
            pass

        w, h = 480, 330
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+%d+%d" % (w, h, (sw - w) // 2, max(60, (sh - h) // 3)))

        card = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(card, text=t_("en", "lang_title"), bg=CARD, fg=ACCENT,
                 font=(self.font, 15, "bold")).pack(pady=(16, 4))
        tk.Label(card, text=t_("en", "lang_prompt"), bg=CARD, fg=FG,
                 font=(self.font, 10)).pack(pady=(0, 14))

        for code in LANG_ORDER:
            self._make_button(card, code)

        tk.Label(card, text=t_("en", "lang_note"), bg=CARD, fg=MUTED,
                 font=(self.font, 8)).pack(pady=(14, 0))

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        try:
            self.deiconify()
            self.attributes("-topmost", True)
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass
        try:
            self.focus_force()
        except Exception:
            pass

    def _make_button(self, parent, code):
        active = (code == self.current)
        label = ("●  " if active else "    ") + LANG_NAMES[code] + "      " + self.SAMPLES[code]
        b = tk.Button(parent, text=label, command=lambda c=code: self._pick(c),
                      bg=ACCENT if active else "#16233a",
                      fg="#001a20" if active else FG,
                      activebackground="#3fe9ff", activeforeground="#001a20",
                      bd=0, relief="flat", cursor="hand2", anchor="w",
                      font=(self.font, 10), padx=14, pady=7)
        b.pack(fill="x", padx=26, pady=4)

    def _pick(self, code):
        self.choice = code
        self.destroy()

    def _cancel(self):
        self.choice = self.current or "zh_CN"
        self.destroy()


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
class App(object):
    def __init__(self, root, lang="zh_CN"):
        self.root = root
        self.lang = lang
        self.ui_font = pick_font(root, UI_FONT_CANDIDATES)
        self.mono_font = pick_font(root, MONO_FONT_CANDIDATES, "TkFixedFont")

        self.left_img = None
        self.left_det = None
        self.left_photo = None
        self.left_content = None
        self.left_name = None
        self.left_check_state = None
        self.right_bits = None
        self.right_photo = None
        self.right_img = None
        self.right_mode = "bits"
        self.qr_source_text = None
        self.right_scan_code = None
        self.ec = "M"
        self.module_px = 8
        self.grid_on = False
        self._toast_job = None

        root.title(self.t("app_title"))
        root.geometry("1280x850")
        root.minsize(1120, 780)
        root.configure(bg=BG)
        self._try_icon()

        self._build_header()
        self._build_body()

    def t(self, key, **kw):
        return t_(self.lang, key, **kw)

    # -------------------------------------------------------- 窗口骨架
    def _try_icon(self):
        apply_window_icon(self.root)

    def _build_header(self):
        self.header = tk.Canvas(self.root, height=78, bg=BG, highlightthickness=0, bd=0)
        self.header.pack(fill="x")
        self.header.bind("<Configure>", self._paint_header)
        self.btn_lang = tk.Button(self.header,
                                  text=self.t("lang_button", name=LANG_NAMES[self.lang]),
                                  command=self.choose_language,
                                  bg="#12283d", fg="#9fe8ff",
                                  activebackground="#1d3a55", activeforeground="#ffffff",
                                  bd=0, relief="flat", cursor="hand2",
                                  font=(self.ui_font, 9), padx=10, pady=3)

    def _paint_header(self, event=None):
        c = self.header
        c.delete("all")
        w = c.winfo_width()
        if w < 10:
            return
        for x in range(w):
            t = x / float(w)
            r = int(14 + 6 * t)
            g = int(34 - 12 * t)
            b = int(51 + 22 * t)
            c.create_line(x, 0, x, 70, fill="#%02x%02x%02x" % (r, g, b))
        c.create_line(0, 70, w, 70, fill=ACCENT, width=2)
        c.create_line(0, 72, w, 72, fill="#062b33")
        c.create_text(26, 30, anchor="w", text=self.t("app_title"),
                      fill="#ffffff", font=(self.ui_font, 21, "bold"))
        c.create_text(26, 55, anchor="w", text=self.t("subtitle"),
                      fill="#8fd0e0", font=(self.ui_font, 9))
        c.create_text(w - 24, 24, anchor="e", text=APP_VERSION,
                      fill="#6d8ba3", font=(self.ui_font, 10))
        c.create_window(w - 24, 52, anchor="e", window=self.btn_lang, width=136, height=26)

    def _build_body(self):
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=16, pady=(10, 14))
        self.body.rowconfigure(0, weight=1)
        self.body.columnconfigure(0, weight=1, uniform="col")
        self.body.columnconfigure(1, weight=1, uniform="col")

        left_outer = tk.Frame(self.body, bg=BORDER)
        left_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left = tk.Frame(left_outer, bg=CARD)
        left.pack(fill="both", expand=True, padx=1, pady=1)
        self._build_left(left)

        right_outer = tk.Frame(self.body, bg=BORDER)
        right_outer.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right = tk.Frame(right_outer, bg=CARD)
        right.pack(fill="both", expand=True, padx=1, pady=1)
        self._build_right(right)

    # -------------------------------------------------------- 控件工坊
    def button(self, parent, text, cmd, accent=False, width=None):
        bg = ACCENT if accent else "#16233a"
        fg = "#001a20" if accent else FG
        ab = "#4cf0ff" if accent else "#233754"
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                      activebackground=ab, activeforeground=fg,
                      bd=0, relief="flat", cursor="hand2",
                      font=(self.ui_font, 10), padx=14, pady=6)
        if width:
            b.configure(width=width)
        hover = "#3fe9ff" if accent else "#20314b"
        b.bind("<Enter>", lambda e: b.configure(bg=hover))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def label(self, parent, text="", fg=FG, size=10, bold=False, bg=CARD, anchor="w"):
        f = (self.ui_font, size, "bold") if bold else (self.ui_font, size)
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=f, anchor=anchor)

    def _section(self, parent, text, idx):
        bar = tk.Frame(parent, bg=CARD)
        bar.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(bar, text=idx, bg=CARD, fg=ACCENT,
                 font=(self.ui_font, 11, "bold")).pack(side="left")
        tk.Label(bar, text="  " + text, bg=CARD, fg=FG,
                 font=(self.ui_font, 12, "bold")).pack(side="left")
        tk.Frame(parent, bg="#1b2b40", height=1).pack(fill="x", padx=14)
        return bar

    def _text_box(self, parent, height, mono=True):
        wrap = tk.Frame(parent, bg=CARD)
        t = tk.Text(wrap, height=height, bg="#070b12", fg="#9fe8ff",
                    insertbackground=ACCENT, bd=0, relief="flat",
                    highlightthickness=1, highlightbackground=BORDER,
                    highlightcolor=ACCENT_D, wrap="none",
                    font=(self.mono_font if mono else self.ui_font, 10),
                    padx=10, pady=8, selectbackground="#2a4a63")
        ys = tk.Scrollbar(wrap, orient="vertical", command=t.yview,
                          bg="#141f30", troughcolor="#0a111c", bd=0,
                          activebackground="#2a4a63", width=10)
        xs = tk.Scrollbar(wrap, orient="horizontal", command=t.xview,
                          bg="#141f30", troughcolor="#0a111c", bd=0,
                          activebackground="#2a4a63", width=10)
        t.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        t.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        return wrap, t

    # -------------------------------------------------------- 左侧
    def _build_left(self, panel):
        self._section(panel, self.t("sec1"), "①")

        tools = tk.Frame(panel, bg=CARD)
        tools.pack(fill="x", padx=14, pady=(0, 8))
        self.button(tools, self.t("open_image"), self.open_image, accent=True).pack(side="left")
        self.button(tools, self.t("paste_image"), self.paste_image).pack(side="left", padx=8)
        self.button(tools, self.t("redetect"), self.redetect_image).pack(side="left")
        self.btn_grid = self.button(tools, self.t("grid_on") if self.grid_on else self.t("grid_off"),
                                    self.toggle_grid)
        self.btn_grid.pack(side="right")

        canvas_wrap = tk.Frame(panel, bg="#060a11", highlightthickness=1,
                               highlightbackground=BORDER)
        canvas_wrap.pack(fill="x", padx=14)
        self.left_canvas = tk.Canvas(canvas_wrap, height=250, bg="#060a11",
                                     highlightthickness=0, bd=0)
        self.left_canvas.pack(fill="both", expand=True)
        self.left_canvas.bind("<Configure>", lambda e: self._paint_left())

        self.left_status = self.label(panel, self.t("waiting"), MUTED, 9)
        self.left_status.pack(fill="x", padx=14, pady=(6, 2))

        self.left_check = self.label(panel, "", MUTED, 9)
        self.left_check.pack(fill="x", padx=14, pady=(0, 8))

        box, self.left_text = self._text_box(panel, height=10)
        box.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.left_text.insert("1.0", self.t("info_ph"))
        self.left_text.configure(fg=MUTED)

        actions = tk.Frame(panel, bg=CARD)
        actions.pack(fill="x", padx=14, pady=(0, 12))
        self.button(actions, self.t("copy_all"), lambda: self.copy_left(full=True),
                    accent=True).pack(side="left")
        self.button(actions, self.t("copy_bits"), lambda: self.copy_left(full=False)).pack(side="left", padx=8)
        self.button(actions, self.t("save_txt"), self.save_txt).pack(side="left")
        self.button(actions, self.t("to_right"), self.push_to_right).pack(side="right")

    # -------------------------------------------------------- 右侧
    def _build_right(self, panel):
        self._section(panel, self.t("sec2"), "②")

        tabs = tk.Frame(panel, bg=CARD)
        tabs.pack(fill="x", padx=14, pady=(0, 6))
        self.btn_tab_bits = self.button(tabs, self.t("tab_bits"), lambda: self.set_mode("bits"))
        self.btn_tab_bits.pack(side="left")
        self.btn_tab_text = self.button(tabs, self.t("tab_text"), lambda: self.set_mode("text"))
        self.btn_tab_text.pack(side="left", padx=8)
        self.mode_hint = self.label(tabs, "", MUTED, 9)
        self.mode_hint.pack(side="left", padx=(10, 0), fill="x", expand=True)

        self.mode_box = tk.Frame(panel, bg=CARD)
        self.mode_box.pack(fill="x")

        # ---- 二进制模式
        self.frame_bits = tk.Frame(self.mode_box, bg=CARD)
        box, self.right_text = self._text_box(self.frame_bits, height=6, mono=False)
        box.pack(fill="x", padx=14, pady=(0, 8))
        acts = tk.Frame(self.frame_bits, bg=CARD)
        acts.pack(fill="x", padx=14, pady=(0, 8))
        self.button(acts, self.t("btn_recognize"), self.build_from_text, accent=True).pack(side="left")
        self.button(acts, self.t("btn_fill_left"), self.pull_from_left).pack(side="left", padx=8)
        self.button(acts, self.t("btn_clear"), self.clear_right).pack(side="left")
        self.button(acts, self.t("btn_paste_clip"), self.paste_text).pack(side="left", padx=8)

        # ---- 文字模式
        self.frame_text = tk.Frame(self.mode_box, bg=CARD)
        box2, self.text_input = self._text_box(self.frame_text, height=4, mono=False)
        box2.pack(fill="x", padx=14, pady=(0, 8))
        opts = tk.Frame(self.frame_text, bg=CARD)
        opts.pack(fill="x", padx=14, pady=(0, 8))
        self.label(opts, self.t("ec_label"), MUTED, 9).pack(side="left")
        self.ec_buttons = {}
        for name in EC_CHOICES:
            b = self.button(opts, name, lambda n=name: self.set_ec(n), width=2)
            b.pack(side="left", padx=(6, 0))
            self.ec_buttons[name] = b
        self.label(opts, "   " + self.t("ec_hint"), MUTED, 9).pack(side="left")
        gen = tk.Frame(self.frame_text, bg=CARD)
        gen.pack(fill="x", padx=14, pady=(0, 8))
        self.button(gen, self.t("btn_gen_text"), self.build_from_input_text, accent=True).pack(side="left")
        self.button(gen, self.t("btn_fill_clip"), self.paste_text_to_input).pack(side="left", padx=8)
        self.button(gen, self.t("btn_clear"), self.clear_input_text).pack(side="left")

        canvas_wrap = tk.Frame(panel, bg="#060a11", highlightthickness=1,
                               highlightbackground=BORDER)
        canvas_wrap.pack(fill="both", expand=True, padx=14)
        self.right_canvas = tk.Canvas(canvas_wrap, bg="#060a11",
                                      highlightthickness=0, bd=0)
        self.right_canvas.pack(fill="both", expand=True)
        self.right_canvas.bind("<Configure>", lambda e: self._paint_right())

        self.right_check = self.label(panel, "", MUTED, 9)
        self.right_check.pack(fill="x", padx=14, pady=(6, 4))

        zoom_bar = tk.Frame(panel, bg=CARD)
        zoom_bar.pack(fill="x", padx=14, pady=(2, 4))
        self.label(zoom_bar, self.t("zoom"), MUTED, 9).pack(side="left")
        self.button(zoom_bar, "－", lambda: self.zoom(-1)).pack(side="left", padx=(6, 4))
        self.btn_zoom_val = self.label(zoom_bar, self.t("unit_px", px=self.module_px), ACCENT, 10, True)
        self.btn_zoom_val.pack(side="left", padx=2)
        self.button(zoom_bar, "＋", lambda: self.zoom(1)).pack(side="left", padx=4)
        self.zoom_scale = Slider(zoom_bar, from_=1, to=40, value=self.module_px,
                                 command=self.on_slide, bg=CARD)
        self.zoom_scale.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.right_info = self.label(panel, self.t("not_yet"), MUTED, 9)
        self.right_info.pack(fill="x", padx=14, pady=(0, 4))

        foot = tk.Frame(panel, bg=CARD)
        foot.pack(fill="x", padx=14, pady=(0, 12))
        self.button(foot, self.t("save_png"), self.save_png, accent=True).pack(side="left")
        self.button(foot, self.t("copy_qr_info"), self.copy_right).pack(side="left", padx=8)
        self.right_status = self.label(foot, "", MUTED, 9)
        self.right_status.pack(side="right")

        self.set_mode("bits")

    # -------------------------------------------------------- 语言
    def choose_language(self):
        dlg = LanguageDialog(self.root, self.lang)
        self.root.wait_window(dlg)
        if dlg.choice and dlg.choice != self.lang:
            self.lang = dlg.choice
            if not save_lang(self.lang):
                messagebox.showwarning(self.t("app_title"), self.t("err_cfg", e="config.json"))
            self.rebuild()

    def rebuild(self):
        """切换语言后重建界面，保留已载入的图片与已生成的结果。"""
        stash_right = ""
        stash_input = ""
        if hasattr(self, "right_text"):
            stash_right = self.right_text.get("1.0", "end").rstrip("\n")
        if hasattr(self, "text_input"):
            stash_input = self.text_input.get("1.0", "end").rstrip("\n")

        self.header.destroy()
        self.body.destroy()
        self.root.title(self.t("app_title"))
        self._build_header()
        self._build_body()

        if stash_right:
            self.right_text.delete("1.0", "end")
            self.right_text.insert("1.0", stash_right)
        if stash_input:
            self.text_input.delete("1.0", "end")
            self.text_input.insert("1.0", stash_input)

        self.set_mode(self.right_mode)
        self.zoom_scale.set(self.module_px, notify=False)
        self.btn_zoom_val.configure(text=self.t("unit_px", px=self.module_px))

        if self.left_det:
            self.left_text.configure(fg="#9fe8ff")
            self.left_text.delete("1.0", "end")
            self.left_text.insert("1.0", format_info(self.left_det, self.lang))
            self._render_left_status()
            self._render_left_check()
        if self.right_bits:
            self._render_right()
        self._paint_left()
        self._paint_right()

    # -------------------------------------------------------- 模式切换
    def _paint_tabs(self):
        for name, btn in (("bits", self.btn_tab_bits), ("text", self.btn_tab_text)):
            active = (name == self.right_mode)
            btn.configure(bg=ACCENT if active else "#16233a",
                          fg="#001a20" if active else FG)
            btn.unbind("<Enter>")
            btn.unbind("<Leave>")

    def set_mode(self, mode):
        self.right_mode = mode
        self._paint_tabs()
        if mode == "bits":
            self.frame_text.pack_forget()
            self.frame_bits.pack(fill="x")
            self.mode_hint.configure(text=self.t("hint_bits"))
        else:
            self.frame_bits.pack_forget()
            self.frame_text.pack(fill="x")
            self.mode_hint.configure(text=self.t("hint_text"))
        self._paint_right()

    def _paint_ec(self):
        for name, btn in self.ec_buttons.items():
            active = (name == self.ec)
            btn.configure(bg=ACCENT if active else "#16233a",
                          fg="#001a20" if active else FG)
            btn.unbind("<Enter>")
            btn.unbind("<Leave>")

    def set_ec(self, name):
        self.ec = name
        self._paint_ec()
        if self.right_mode == "text" and self.text_input.get("1.0", "end").strip():
            self.build_from_input_text()

    # -------------------------------------------------------- 状态
    def _set_status(self, which, text, color=MUTED):
        lb = self.left_status if which == "left" else self.right_status
        lb.configure(text=text, fg=color)

    def _render_left_status(self):
        if not self.left_det:
            return
        det = self.left_det
        q = det["finder"]
        color = OK if q >= 0.95 else (WARN if q >= 0.7 else ERR)
        txt = self.t("left_status_tpl", name=self.left_name or self.t("st_recognized"),
                     n=det["n"], px="%.2f" % det["module_px"], f=int(q * 100))
        self.left_status.configure(text=txt, fg=color)

    def _render_left_check(self):
        if not self.left_check_state:
            self.left_check.configure(text="", fg=MUTED)
            return
        key, kw, color = self.left_check_state
        self.left_check.configure(text=self.t(key, **kw), fg=color)

    # -------------------------------------------------------- 左侧逻辑
    def open_image(self):
        path = filedialog.askopenfilename(
            title=self.t("dlg_open"),
            filetypes=[(self.t("ft_images"), "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff"),
                       (self.t("ft_all"), "*.*")])
        if not path:
            return
        try:
            img = _prepare(Image.open(path))
        except Exception as e:
            messagebox.showerror(self.t("app_title"), self.t("err_open", e=e))
            return
        self.load_image(img, os.path.basename(path))

    def paste_image(self):
        try:
            data = ImageGrab.grabclipboard()
        except Exception:
            data = None
        if isinstance(data, list) and data:
            try:
                data = Image.open(data[0])
            except Exception:
                data = None
        if not isinstance(data, Image.Image):
            messagebox.showinfo(self.t("app_title"), self.t("err_no_image_clip"))
            return
        self.load_image(_prepare(data), self.t("btn_paste_clip"))

    def load_image(self, img, name):
        self.left_img = img
        self.left_det = None
        self.left_content = None
        self.left_name = name
        self.left_check_state = None
        self.left_check.configure(text="", fg=MUTED)
        self.left_text.configure(fg=MUTED)
        self.left_text.delete("1.0", "end")
        self.left_text.insert("1.0", self.t("recognizing"))
        self.root.update_idletasks()
        self._paint_left()
        self.redetect_image(silent_title=name)

    def redetect_image(self, silent_title=None):
        if self.left_img is None:
            self._set_status("left", self.t("msg_pick_image_first"), WARN)
            return
        try:
            det = detect_qr_matrix(self.left_img)
        except Exception as e:
            self.left_det = None
            self.left_check_state = None
            self.left_check.configure(text="", fg=MUTED)
            self.left_text.configure(fg=ERR)
            self.left_text.delete("1.0", "end")
            self.left_text.insert("1.0", self.t("err_recognize", e=e))
            self._set_status("left", self.t("msg_need_detect"), ERR)
            self._paint_left()
            if silent_title is None:
                messagebox.showwarning(self.t("app_title"), self.t("err_recognize", e=e))
            return

        self.left_det = det
        self.left_name = silent_title or self.t("st_recognized")
        self._left_selfcheck(det)
        info = format_info(det, self.lang)
        self.left_text.configure(fg="#9fe8ff")
        self.left_text.delete("1.0", "end")
        self.left_text.insert("1.0", info)
        self._render_left_status()
        self._render_left_check()
        self._paint_left()

    def _left_selfcheck(self, det):
        """用真实扫码引擎验证：源图能否解码、重绘后能否解码、内容是否一致。"""
        self.left_content = None
        if not SCANNER_OK:
            det["scan_code"] = "none"
            self.left_check_state = ("left_check_engine_missing", {}, WARN)
            self._render_left_check()
            return

        src_ok, src_list, _ = scan_decode(self.left_img)
        src_text = src_list[0] if src_ok else None
        self.left_content = src_text

        probe = render_qr(det["bits"], 6)
        ok, contents, _ = scan_decode(probe)
        struct_ok, problems, _ = validate_matrix(det["bits"], self.lang)

        def short(s):
            s = s.replace("\n", " ")
            return s if len(s) <= 46 else s[:43] + "…"

        if not struct_ok:
            det["scan_code"] = "struct"
            self.left_check_state = ("left_check_struct", {"p": problems[0]}, ERR)
        elif not ok:
            det["scan_code"] = "fail"
            self.left_check_state = ("left_check_fail_src_ok", {}, ERR) if src_ok \
                else ("left_check_fail_both", {}, ERR)
        elif src_ok and src_text is not None and texts_match(contents[0], src_text):
            det["scan_code"] = "same_src"
            self.left_check_state = ("left_check_same", {"c": short(src_text)}, OK)
        elif src_ok and src_text is not None:
            det["scan_code"] = "mismatch"
            self.left_check_state = ("left_check_mismatch", {}, ERR)
        else:
            det["scan_code"] = "pass"
            self.left_check_state = ("left_check_src_unreadable", {"c": short(contents[0])}, WARN)

    def toggle_grid(self):
        self.grid_on = not self.grid_on
        self.btn_grid.configure(text=self.t("grid_on") if self.grid_on else self.t("grid_off"))
        self._paint_left()

    def _paint_left(self):
        c = self.left_canvas
        c.delete("all")
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 20 or ch < 20:
            return
        if self.left_img is None:
            c.create_text(cw // 2, ch // 2, text=self.t("ph_left"),
                          fill=MUTED, font=(self.ui_font, 11))
            return
        w, h = self.left_img.size
        scale = min(cw / float(w), ch / float(h)) * 0.96
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        resample = Image.NEAREST if scale >= 1 else Image.Resampling.LANCZOS
        thumb = self.left_img.resize((nw, nh), resample)
        self.left_photo = ImageTk.PhotoImage(thumb)
        ox, oy = (cw - nw) // 2, (ch - nh) // 2
        c.create_image(ox, oy, anchor="nw", image=self.left_photo)

        if self.left_det and self.grid_on:
            n = self.left_det["n"]
            x0, y0, side = self.left_det["bbox"]
            m = side / float(n)
            step = 1
            while m * scale * step < 9 and step < n:
                step *= 2
            gx0 = ox + int(round(x0 * scale))
            gy0 = oy + int(round(y0 * scale))
            gx1 = ox + int(round((x0 + side) * scale))
            gy1 = oy + int(round((y0 + side) * scale))
            for i in range(0, n + 1, step):
                px = ox + int(round((x0 + i * m) * scale))
                py = oy + int(round((y0 + i * m) * scale))
                if gx0 < px < gx1:
                    c.create_line(px, gy0, px, gy1, fill="#2ea8c0",
                                  width=1, stipple="gray12")
                if gy0 < py < gy1:
                    c.create_line(gx0, py, gx1, py, fill="#2ea8c0",
                                  width=1, stipple="gray12")
            c.create_rectangle(gx0, gy0, gx1, gy1, outline=ACCENT, width=2)

    def copy_left(self, full=True):
        if not self.left_det:
            self._set_status("left", self.t("msg_need_detect_copy"), WARN)
            return
        text = format_info(self.left_det, self.lang) if full else bits_debug(self.left_det)
        n = self.left_det["n"]
        msg = (self.t("msg_copy_all_done", n=n) if full
               else self.t("msg_copy_bits_done", b=n * n))
        self._to_clipboard(text, "left", msg)

    def save_txt(self):
        if not self.left_det:
            self._set_status("left", self.t("msg_need_detect_save"), WARN)
            return
        path = filedialog.asksaveasfilename(
            title=self.t("dlg_save_txt"), defaultextension=".txt",
            initialfile="qr_bits_%dx%d.txt" % (self.left_det["n"], self.left_det["n"]),
            filetypes=[(self.t("ft_txt"), "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(format_info(self.left_det, self.lang))
        self._set_status("left", self.t("msg_saved", name=os.path.basename(path)), OK)

    def push_to_right(self):
        if not self.left_det:
            self._set_status("left", self.t("msg_need_detect"), WARN)
            return
        self.right_text.delete("1.0", "end")
        self.right_text.insert("1.0", format_info(self.left_det, self.lang))
        self._set_status("left", self.t("msg_fill_right"), OK)
        self.build_from_text()

    # -------------------------------------------------------- 右侧逻辑
    def pull_from_left(self):
        if not self.left_det:
            self._set_status("right", self.t("msg_need_detect"), WARN)
            return
        self.right_text.delete("1.0", "end")
        self.right_text.insert("1.0", format_info(self.left_det, self.lang))
        self._set_status("right", self.t("msg_filled_left"), OK)

    def paste_text(self):
        try:
            data = self.root.clipboard_get()
        except Exception:
            data = ""
        if not data:
            self._set_status("right", self.t("msg_no_text_clip"), WARN)
            return
        self.right_text.delete("1.0", "end")
        self.right_text.insert("1.0", data)
        self._set_status("right", self.t("msg_paste_chars", c=len(data)), OK)

    def clear_right(self):
        self.right_text.delete("1.0", "end")
        self.right_bits = None
        self.right_img = None
        self.right_photo = None
        self.qr_source_text = None
        self.right_check.configure(text="", fg=MUTED)
        self._set_status("right", "", MUTED)
        self.right_info.configure(text=self.t("not_yet"), fg=MUTED)
        self._paint_right()

    def build_from_text(self):
        raw = self.right_text.get("1.0", "end")
        if not raw.strip():
            self._set_status("right", self.t("msg_input_empty"), WARN)
            return
        try:
            n, bits = parse_info(raw, self.lang)
        except Exception as e:
            self.right_bits = None
            self.right_img = None
            self.right_check.configure(text="", fg=MUTED)
            self._paint_right()
            self.right_info.configure(text=self.t("msg_parse_fail", e=e), fg=ERR)
            self._set_status("right", self.t("msg_parse_fail", e=""), ERR)
            return
        self.right_bits = bits
        self.qr_source_text = None
        self._render_right()
        self._set_status("right", self.t("msg_gen_done", n=n), OK)

    def build_from_input_text(self):
        raw = self.text_input.get("1.0", "end")
        if not raw.strip():
            self._set_status("right", self.t("msg_need_text_input"), WARN)
            return
        if not QRCODE_OK:
            messagebox.showerror(self.t("app_title"), self.t("err_no_encoder"))
            return
        try:
            ver, n, bits = qr_from_text(raw, self.ec)
        except Exception as e:
            self.right_bits = None
            self.right_img = None
            self.right_check.configure(text="", fg=MUTED)
            self._paint_right()
            self.right_info.configure(text=self.t("msg_gen_fail", e=e), fg=ERR)
            self._set_status("right", self.t("msg_gen_fail", e=""), ERR)
            return
        self.right_bits = bits
        self.qr_source_text = raw.rstrip("\n")
        self._render_right()
        self._set_status("right", self.t("msg_gen_text_done", v=ver, n=n, m=n), OK)

    def paste_text_to_input(self):
        try:
            data = self.root.clipboard_get()
        except Exception:
            data = ""
        if not data:
            self._set_status("right", self.t("msg_no_text_clip"), WARN)
            return
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", data)
        self._set_status("right", self.t("msg_paste_chars", c=len(data)), OK)

    def clear_input_text(self):
        self.text_input.delete("1.0", "end")
        self.right_bits = None
        self.right_img = None
        self.right_check.configure(text="", fg=MUTED)
        self.right_info.configure(text=self.t("not_yet"), fg=MUTED)
        self._set_status("right", "", MUTED)
        self._paint_right()

    def _render_right(self):
        if not self.right_bits:
            return
        n = len(self.right_bits)
        img = render_qr(self.right_bits, self.module_px)
        self.right_img = img
        self.right_info.configure(
            text=self.t("right_info_tpl", n=n, px=self.module_px,
                        w=img.size[0], h=img.size[1], bits=n * n),
            fg="#8fb8cc")
        self.btn_zoom_val.configure(text=self.t("unit_px", px=self.module_px))
        self._update_right_check()
        self._paint_right()

    def _update_right_check(self):
        """结构校验 + 真实解码，验证"能不能扫、扫出来是不是同一份内容"。"""
        self.right_check_pass = False
        if not self.right_bits:
            self.right_check.configure(text="", fg=MUTED)
            return
        struct_ok, problems, desc = validate_matrix(self.right_bits, self.lang)
        if not struct_ok:
            self.right_scan_code = "struct"
            self.right_check.configure(
                text=self.t("check_struct_fail", p=problems[0]), fg=ERR)
            return
        if not SCANNER_OK:
            self.right_scan_code = "none"
            self.right_check.configure(text=self.t("check_engine_missing"), fg=WARN)
            return

        ok, contents, _ = scan_decode(render_qr(self.right_bits, 6))
        if not ok:
            self.right_scan_code = "fail"
            self.right_check.configure(text=self.t("check_decode_fail"), fg=ERR)
            return

        got = contents[0]
        if self.right_mode == "text" and self.qr_source_text is not None:
            if texts_match(got, self.qr_source_text):
                self.right_scan_code = "pass"
                self.right_check_pass = True
                self.right_check.configure(
                    text=self.t("check_text_ok", d=desc), fg=OK)
            else:
                self.right_scan_code = "mismatch_input"
                self.right_check.configure(
                    text=self.t("check_text_bad", c=got[:40]), fg=ERR)
        else:
            self.right_scan_code = "pass"
            self.right_check_pass = True
            shown = got.replace("\n", " ")
            if len(shown) > 32:
                shown = shown[:30] + "…"
            self.right_check.configure(
                text=self.t("check_bits_ok", c=shown), fg=OK)

        if self.right_check_pass and self.module_px < 4:
            self.right_check.configure(
                text=self.right_check.cget("text")
                     + self.t("check_small_px", px=self.module_px),
                fg=WARN)

    def zoom(self, delta):
        self.set_module_px(self.module_px + delta)

    def on_slide(self, val):
        try:
            v = int(float(val))
        except Exception:
            return
        if v != self.module_px:
            self.set_module_px(v, sync_slider=False)

    def set_module_px(self, v, sync_slider=True):
        v = max(1, min(40, int(v)))
        if v == self.module_px and self.right_bits:
            self.btn_zoom_val.configure(text=self.t("unit_px", px=v))
            return
        self.module_px = v
        self.btn_zoom_val.configure(text=self.t("unit_px", px=v))
        if sync_slider:
            self.zoom_scale.set(v, notify=False)
        if self.right_bits:
            self._render_right()

    def _paint_right(self):
        c = self.right_canvas
        c.delete("all")
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 20 or ch < 20:
            return
        if not self.right_img:
            hint = self.t("ph_right_text") if self.right_mode == "text" else self.t("ph_right_bits")
            c.create_text(cw // 2, ch // 2, text=hint,
                          fill=MUTED, font=(self.ui_font, 11))
            return
        w, h = self.right_img.size
        scale = min(cw / float(w), ch / float(h)) * 0.92
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        resample = Image.NEAREST if scale >= 1 else Image.Resampling.LANCZOS
        thumb = self.right_img.resize((nw, nh), resample)
        self.right_photo = ImageTk.PhotoImage(thumb)
        c.create_image((cw - nw) // 2, (ch - nh) // 2, anchor="nw", image=self.right_photo)

    def _scannable_image(self, bits, px):
        """找一个"真实可解码"的导出尺寸；1~3 px/模块 直接跳过。"""
        tried = []
        for cand in (px, max(px, 4), 6, 8, 12, 16, 24):
            if cand < 4 or cand in tried:
                continue
            tried.append(cand)
            img = render_qr(bits, cand)
            ok, contents, _ = scan_decode(img)
            if ok:
                return img, cand, contents
        return None, px, None

    def save_png(self):
        if not self.right_bits:
            self._set_status("right", self.t("not_yet"), WARN)
            return
        n = len(self.right_bits)
        struct_ok, problems, _ = validate_matrix(self.right_bits, self.lang)
        if not struct_ok:
            messagebox.showerror(self.t("app_title"), self.t("err_struct_save", p=self.t("list_sep").join(problems)))
            return

        img, px, contents = self._scannable_image(self.right_bits, self.module_px)
        if img is None:
            messagebox.showerror(self.t("app_title"), self.t("err_unscannable"))
            return

        note = ""
        if px != self.module_px:
            note = self.t("msg_saved_bumped", px=px)
            self.module_px = px
            self.btn_zoom_val.configure(text=self.t("unit_px", px=px))
            self.zoom_scale.set(px, notify=False)
            self.right_img = img
            self.right_info.configure(
                text=self.t("right_info_tpl", n=n, px=px,
                            w=img.size[0], h=img.size[1], bits=n * n), fg="#8fb8cc")
            self._paint_right()

        path = filedialog.asksaveasfilename(
            title=self.t("dlg_save_png"), defaultextension=".png",
            initialfile="qr_%dx%d_%dpx.png" % (n, n, px),
            filetypes=[(self.t("ft_png"), "*.png")])
        if not path:
            return
        img.save(path)

        # 把磁盘上的文件重新读回来解码一次，确保落盘的那张图真的能扫
        try:
            ok2, contents2, _ = scan_decode(Image.open(path))
        except Exception:
            ok2, contents2 = False, []
        if ok2 and contents2:
            self._set_status("right", self.t("msg_saved_verified", name=os.path.basename(path)) + note, OK)
        else:
            self._set_status("right", self.t("msg_saved_no_verify"), ERR)

    def copy_right(self):
        if not self.right_bits:
            self._set_status("right", self.t("not_yet"), WARN)
            return
        n = len(self.right_bits)
        det = {"n": n, "bits": self.right_bits, "module_px": float(self.module_px),
               "size": self.right_img.size, "finder": 1.0, "conf": 1.0,
               "scan_code": self.right_scan_code}
        self._to_clipboard(format_info(det, self.lang), "right",
                           self.t("msg_copy_all_done", n=n))

    # -------------------------------------------------------- 通用
    def _to_clipboard(self, text, which, msg):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception as e:
            messagebox.showerror(self.t("app_title"), self.t("err_copy", e=e))
            return
        lb = self.left_status if which == "left" else self.right_status
        lb.configure(text=msg, fg=OK)
        if self._toast_job:
            try:
                self.root.after_cancel(self._toast_job)
            except Exception:
                pass
        self._toast_job = self.root.after(3000, lambda: lb.configure(text=""))


def _selftest(out_path):
    """诊断：确认打包后扫码引擎与编码库是否可用。用法：程序 --selftest <输出文件>"""
    lines = ["SCANNER_OK=%s" % SCANNER_OK, "QRCODE_OK=%s" % QRCODE_OK]
    try:
        ver, n, bits = qr_from_text("自检 ABC 123", "M")
        lines.append("encode_version=%s n=%d" % (ver, n))
        lines.append("structure=%s" % (validate_matrix(bits),))
        ok, contents, err = scan_decode(render_qr(bits, 6))
        lines.append("decode_ok=%s" % ok)
        lines.append("decode_contents=%s" % (contents[:1],))
        lines.append("decode_err=%s" % err)
        lines.append("match=%s" % (ok and texts_match(contents[0], "自检 ABC 123")))
    except Exception as e:
        lines.append("EXCEPTION=%r" % (e,))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── 原创信息 · Original work by D_Chuan (c) 2026 ── 禁止商用 · 二创请保留本行 ──
def main():
    # 高 DPI 感知只有 Windows 需要；macOS 由系统统一按 Retina 缩放，Linux 交给桌面环境
    if PLATFORM == "windows":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    root.withdraw()
    lang = load_lang()
    if lang is None:
        dlg = LanguageDialog(root, None)
        root.wait_window(dlg)
        lang = dlg.choice or "zh_CN"
        save_lang(lang)
    App(root, lang)
    root.deiconify()
    root.lift()
    if PLATFORM == "macos":
        # macOS 上新进程的窗口常被其他窗口压住，先置顶再解除，保证一启动就在前台
        try:
            root.attributes("-topmost", True)
            root.after(400, lambda: root.attributes("-topmost", False))
            root.focus_force()
        except Exception:
            pass
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        _selftest(sys.argv[2])
        sys.exit(0)
    main()
