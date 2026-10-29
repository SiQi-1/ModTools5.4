#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_win.py —— 《文明6》Windows 窗口枚举、定位、移动/缩放与截图工具（ctypes）

一、用途
    给自动化脚本/AI 提供“看见并操作文明6游戏窗口”的最小能力：
    枚举游戏窗口、读取窗口与客户区矩形、移动/缩放窗口、切换前台、截图保存 PNG。
    只支持**窗口化 / 无边框窗口化**模式；独占全屏（fullscreen）下 Windows 不保证
    窗口矩形与截图可用，请先切到窗口化（游戏内：选项 → 图形 → 显示模式）。

二、依赖
    仅 Python 标准库（ctypes 调用 user32/gdi32/kernel32）。
    - 截图保存 PNG 需要 Pillow（可选）。缺少 Pillow 时自动降级写 BMP，并在返回值中标注。
    - 仅支持 Windows 10/11（x64）；屏幕分辨率与 DPI 均在运行时读取，不依赖固定值。
      本模块不启动、不结束游戏进程。

三、游戏进程与窗口识别
    游戏根目录：由同目录 civ6_game.find_game_dir() 自动探测（可用 CIV6_GAME_DIR、
               --game-dir 覆盖；不假定盘符/Steam 库路径）
    主程序：  Base/Binaries/Win64Steam/CivilizationVI.exe（DX11）
              Base/Binaries/Win64Steam/CivilizationVI_DX12.exe（DX12）
    启动器：  LaunchPad/LaunchPad.exe
    本模块按“窗口所属进程的可执行文件名”匹配，默认匹配 CivilizationVI.exe 与
    CivilizationVI_DX12.exe；加 --launcher 可把 LaunchPad 启动器窗口也纳入候选。
    同一进程可能有多个顶层窗口（主窗口 + 隐藏辅助窗口），默认只取可见窗口，
    并按面积从大到小排序后选第一个作为“主窗口”。

四、主要 API（全部可在其他脚本中 import 使用）
    enable_dpi_awareness()               开启 DPI 感知（shcore → DPI context v2 → 旧 API）
    iter_top_level_windows(...)          枚举顶层窗口，返回 list[WindowInfo]
    list_windows(...)                    对外窗口列表（all_windows=True 列所有顶层窗口）
    list_game_windows(...) / find_game_window(...)
                                         枚举/选取游戏窗口
    wait_for_window(...) / game_window(...)
                                         等待游戏窗口出现（启动后窗口可能延迟约 40s）
    get_window_rect(hwnd)                窗口矩形（屏幕坐标）
    get_client_rect(hwnd)                客户区矩形（换算成屏幕坐标）
    get_window_state(hwnd)               矩形 + 客户区 + 显示器 + DPI + 全屏猜测
    resize_window(hwnd, w, h, x, y, client_area=False)
                                         移动/缩放；client_area=True 表示 w/h 是客户区尺寸
    focus_window(hwnd)                   恢复最小化 + 置前，返回是否成功成为前台
    capture_window(hwnd=None, out_path="shot.png", ...)
                                         截图保存 PNG（PIL 缺失时 BMP 降级）；
                                         hwnd 省略时按 proc_names 自动等待/查找游戏窗口，
                                         顺序 print(PrintWindow) → screen(置前后屏幕采集) → gdi
    detect_fullscreen(hwnd)              全屏猜测，返回 {is_fullscreen, reason}

五、CLI（python civ6_win.py <子命令> [选项]）
    python civ6_win.py list                     列出游戏窗口
    python civ6_win.py list --all --json        列出所有顶层窗口（调试用）
    python civ6_win.py rect                     输出窗口/客户区矩形与状态
    python civ6_win.py rect --client            只关心客户区
    python civ6_win.py shot --out game.png      主窗口截图（默认 auto：PrintWindow→屏幕→GDI）
    python civ6_win.py shot --out game.png --client --method screen --focus
                                                客户区截图，先置前再用屏幕采集
    python civ6_win.py resize --width 1600 --height 900 --client
                                                按客户区 1600x900 缩放窗口
    python civ6_win.py focus                    恢复并置前
    说明：
      - 所有子命令都支持 --json；--hwnd/--pid/--exe 可指定非默认目标（便于调试与截别的窗口）。
      - --hwnd 接受十进制或 0x 十六进制；--wait N 在游戏窗口尚未出现时轮询 N 秒
        （实测启动后主菜单窗口可能延迟约 40s 才出现，MainWindowHandle 初始为 0）。
      - 截图 auto 模式：先 PrintWindow(PW_RENDERFULLCONTENT)（不要求前台），
        失败才置前窗口并从屏幕采集（等价 CopyFromScreen），最后用窗口 DC 兜底。
      - 退出码：0 成功；2 找不到窗口；3 截图失败；4 Win32 调用失败；1 其他错误。
    示例（PowerShell）：
      python skills/civ6-ai-play/scripts/civ6_win.py list --wait 45
      python skills/civ6-ai-play/scripts/civ6_win.py shot --out "$env:TEMP/civ6.png"

六、截图方法说明（实测经验）
    - print  : PrintWindow(..., PW_RENDERFULLCONTENT)。能截被遮挡窗口，但部分 DX11/DX12
               游戏窗口返回纯黑（尤其独占全屏/硬件覆盖），失败时 auto 会自动降级。
    - screen : 从屏幕 DC 用 BitBlt(SRCCOPY|CAPTUREBLT) 截取窗口矩形所在的屏幕区域，
               对 GPU 渲染内容最可靠；要求窗口未被遮挡（配合 --focus 使用）。
    - gdi    : 直接从窗口 DC BitBlt，等价于“截窗口表面”，对部分窗口有效，兼容性兜底。
    - 若窗口最小化：截图会抛 CaptureError，加 --focus 让工具先恢复窗口；
    - 全屏猜测为 true 时工具仍会尝试采集，但建议窗口化后再截图。

七、已知限制
    - 只处理同一桌面会话内的窗口；锁屏、UAC 安全桌面、RDP 断连后无法枚举/截图。
    - 高 DPI 下若宿主进程已固定 DPI 感知级别，本模块无法更改，矩形可能与物理像素不一致。
    - 屏幕采集截到的是“当前屏幕像素”，窗口被遮挡或被系统特效覆盖时内容不完整。
    - PrintWindow 对独占全屏、部分硬件加速窗口必然黑屏（这是 Windows API 限制，不是 bug）。
    - 游戏内 UI 缩放、窗口无边框模式由游戏选项控制，本模块不做崩溃性操作（不发按键、不点击）。
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import fnmatch
import json
import os
import sys
import time
import unicodedata
from dataclasses import dataclass
from ctypes import wintypes as wt

if sys.platform != "win32":
    raise RuntimeError("civ6_win.py 仅支持 Windows：依赖 user32.dll / gdi32.dll / kernel32.dll")

# ---------------------------------------------------------------------------
# Win32 绑定与常量
# ---------------------------------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

HWND = ctypes.c_void_p
HDC = ctypes.c_void_p
HBITMAP = ctypes.c_void_p
HGDIOBJ = ctypes.c_void_p
HMONITOR = ctypes.c_void_p

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_POPUP = 0x80000000
SW_SHOW = 5
SW_RESTORE = 9
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
PW_CLIENTONLY = 0x00000001
PW_RENDERFULLCONTENT = 0x00000002
DIB_RGB_COLORS = 0
BI_RGB = 0
MONITOR_DEFAULTTONEAREST = 0x00000002

# 游戏相关进程可执行文件名（实测）
GAME_EXES = ("CivilizationVI.exe", "CivilizationVI_DX12.exe")
LAUNCHER_EXES = ("LaunchPad.exe",)


class MONITORINFO(ctypes.Structure):
    """GetMonitorInfoW 需要的结构体。"""

    _fields_ = [
        ("cbSize", wt.DWORD),
        ("rcMonitor", wt.RECT),
        ("rcWork", wt.RECT),
        ("dwFlags", wt.DWORD),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, HWND, wt.LPARAM)

_GET_WINDOW_LONG = None  # type: ignore[assignment]
_GET_DPI_FOR_WINDOW = None
_ADJUST_WINDOW_RECT_EX_FOR_DPI = None
_SET_DPI_AWARENESS_CONTEXT = None


def _optional(dll, name):
    """取可选导出函数：老系统/精简 DLL 上可能不存在。"""
    try:
        return getattr(dll, name)
    except AttributeError:
        return None


def _setup_prototypes() -> None:
    """集中声明 ctypes 函数签名。64 位下 HWND 必须用 c_void_p 作返回类型，否则句柄会被截断。"""
    user32.GetForegroundWindow.restype = HWND

    user32.SetForegroundWindow.argtypes = [HWND]
    user32.SetForegroundWindow.restype = wt.BOOL
    user32.BringWindowToTop.argtypes = [HWND]
    user32.BringWindowToTop.restype = wt.BOOL
    user32.SetFocus.argtypes = [HWND]
    user32.SetFocus.restype = HWND
    user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
    user32.AttachThreadInput.restype = wt.BOOL
    user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(wt.DWORD)]
    user32.GetWindowThreadProcessId.restype = wt.DWORD
    user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
    user32.ShowWindow.restype = wt.BOOL
    user32.IsWindow.argtypes = [HWND]
    user32.IsWindow.restype = wt.BOOL
    user32.IsWindowVisible.argtypes = [HWND]
    user32.IsWindowVisible.restype = wt.BOOL
    user32.IsIconic.argtypes = [HWND]
    user32.IsIconic.restype = wt.BOOL
    user32.IsZoomed.argtypes = [HWND]
    user32.IsZoomed.restype = wt.BOOL
    user32.GetWindowTextLengthW.argtypes = [HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wt.RECT)]
    user32.GetWindowRect.restype = wt.BOOL
    user32.GetClientRect.argtypes = [HWND, ctypes.POINTER(wt.RECT)]
    user32.GetClientRect.restype = wt.BOOL
    user32.ClientToScreen.argtypes = [HWND, ctypes.POINTER(wt.POINT)]
    user32.ClientToScreen.restype = wt.BOOL
    user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
    user32.EnumWindows.restype = wt.BOOL
    user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wt.UINT]
    user32.SetWindowPos.restype = wt.BOOL
    user32.GetDC.argtypes = [HWND]
    user32.GetDC.restype = HDC
    user32.GetWindowDC.argtypes = [HWND]
    user32.GetWindowDC.restype = HDC
    user32.ReleaseDC.argtypes = [HWND, HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.PrintWindow.argtypes = [HWND, HDC, wt.UINT]
    user32.PrintWindow.restype = wt.BOOL
    user32.MonitorFromWindow.argtypes = [HWND, wt.DWORD]
    user32.MonitorFromWindow.restype = HMONITOR
    user32.GetMonitorInfoW.argtypes = [HMONITOR, ctypes.POINTER(MONITORINFO)]
    user32.GetMonitorInfoW.restype = wt.BOOL
    user32.AdjustWindowRectEx.argtypes = [ctypes.POINTER(wt.RECT), wt.DWORD, wt.BOOL, wt.DWORD]
    user32.AdjustWindowRectEx.restype = wt.BOOL
    user32.SetProcessDPIAware.restype = wt.BOOL

    global _GET_WINDOW_LONG, _GET_DPI_FOR_WINDOW
    global _ADJUST_WINDOW_RECT_EX_FOR_DPI, _SET_DPI_AWARENESS_CONTEXT

    _GET_WINDOW_LONG = _optional(user32, "GetWindowLongPtrW") or _optional(user32, "GetWindowLongW")
    if _GET_WINDOW_LONG is not None:
        _GET_WINDOW_LONG.argtypes = [HWND, ctypes.c_int]
        _GET_WINDOW_LONG.restype = ctypes.c_ssize_t

    _GET_DPI_FOR_WINDOW = _optional(user32, "GetDpiForWindow")
    if _GET_DPI_FOR_WINDOW is not None:
        _GET_DPI_FOR_WINDOW.argtypes = [HWND]
        _GET_DPI_FOR_WINDOW.restype = wt.UINT

    _ADJUST_WINDOW_RECT_EX_FOR_DPI = _optional(user32, "AdjustWindowRectExForDpi")
    if _ADJUST_WINDOW_RECT_EX_FOR_DPI is not None:
        _ADJUST_WINDOW_RECT_EX_FOR_DPI.argtypes = [
            ctypes.POINTER(wt.RECT), wt.DWORD, wt.BOOL, wt.DWORD, wt.UINT]
        _ADJUST_WINDOW_RECT_EX_FOR_DPI.restype = wt.BOOL

    _SET_DPI_AWARENESS_CONTEXT = _optional(user32, "SetProcessDpiAwarenessContext")
    if _SET_DPI_AWARENESS_CONTEXT is not None:
        _SET_DPI_AWARENESS_CONTEXT.argtypes = [ctypes.c_void_p]
        _SET_DPI_AWARENESS_CONTEXT.restype = wt.BOOL

    gdi32.CreateCompatibleDC.argtypes = [HDC]
    gdi32.CreateCompatibleDC.restype = HDC
    gdi32.CreateDIBSection.argtypes = [HDC, ctypes.POINTER(BITMAPINFO), wt.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD]
    gdi32.CreateDIBSection.restype = HBITMAP
    gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
    gdi32.SelectObject.restype = HGDIOBJ
    gdi32.BitBlt.argtypes = [HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             HDC, ctypes.c_int, ctypes.c_int, wt.DWORD]
    gdi32.BitBlt.restype = wt.BOOL
    gdi32.DeleteObject.argtypes = [HGDIOBJ]
    gdi32.DeleteObject.restype = wt.BOOL
    gdi32.DeleteDC.argtypes = [HDC]
    gdi32.DeleteDC.restype = wt.BOOL

    kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    kernel32.OpenProcess.restype = wt.HANDLE
    kernel32.CloseHandle.argtypes = [wt.HANDLE]
    kernel32.CloseHandle.restype = wt.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR,
                                                    ctypes.POINTER(wt.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wt.BOOL
    kernel32.GetCurrentThreadId.restype = wt.DWORD


_setup_prototypes()


# ---------------------------------------------------------------------------
# 异常类型
# ---------------------------------------------------------------------------
class Civ6WinError(RuntimeError):
    """本模块所有错误的基类。"""


class WindowNotFoundError(Civ6WinError):
    """找不到目标窗口（游戏未运行、窗口已关闭、HWND 失效等）。"""


class CaptureError(Civ6WinError):
    """截图失败（窗口最小化、全屏黑屏、GDI 失败等）。"""


class Win32CallError(Civ6WinError):
    """Win32 API 调用返回失败。"""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


def _win32_error_text(code: int) -> str:
    try:
        text = ctypes.FormatError(code).strip()
    except Exception:
        text = ""
    return text or "未知 Win32 错误"


def _raise_last_error(action: str) -> None:
    code = ctypes.get_last_error()
    raise Win32CallError(f"{action} 失败：{_win32_error_text(code)}（错误码 {code}）", code)


# ---------------------------------------------------------------------------
# DPI 感知
# ---------------------------------------------------------------------------
_DPI_READY: bool | None = None


def _dpi_context_value() -> ctypes.c_void_p:
    """DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4（按指针宽度取补码）。"""
    bits = ctypes.sizeof(ctypes.c_void_p) * 8
    return ctypes.c_void_p((-4) & ((1 << bits) - 1))


def enable_dpi_awareness() -> bool:
    """尽量把当前进程设为 DPI 感知（按实测顺序：shcore → DPI context v2 → 旧 API）。

    顺序：
      1. shcore.SetProcessDpiAwareness(2)  （PROCESS_PER_MONITOR_DPI_AWARE，Win8.1+）
      2. user32.SetProcessDpiAwarenessContext(-4)（PER_MONITOR_AWARE_V2，Win10 1703+）
      3. user32.SetProcessDPIAware()      （Vista+ 旧接口，系统级 DPI 感知）
    必须在 GetWindowRect / 截图之前调用，否则拿到的是被 DPI 虚拟化的错误尺寸
    （例如高 DPI 缩放且未声明感知时，1600x900 客户区可能被读成约 1066x600）。
    幂等：只在第一次调用时真正执行；宿主进程已固定 DPI 感知时返回 False，但 API 仍可用。
    """
    global _DPI_READY
    if _DPI_READY is not None:
        return _DPI_READY
    ok = False
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = ctypes.c_long
        ok = shcore.SetProcessDpiAwareness(2) == 0
    except Exception:
        ok = False
    if not ok and _SET_DPI_AWARENESS_CONTEXT is not None:
        try:
            ok = bool(_SET_DPI_AWARENESS_CONTEXT(_dpi_context_value()))
        except Exception:
            ok = False
    if not ok:
        try:
            ok = bool(user32.SetProcessDPIAware())
        except Exception:
            ok = False
    _DPI_READY = ok
    return ok


def _ensure_dpi_aware() -> None:
    if _DPI_READY is None:
        enable_dpi_awareness()


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rect:
    """屏幕坐标矩形（right/bottom 不含）。"""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "width": self.width,
            "height": self.height,
        }

    def __str__(self) -> str:
        return f"({self.left},{self.top},{self.right},{self.bottom}) {self.width}x{self.height}"


@dataclass
class WindowInfo:
    """一个顶层窗口的快照。"""

    hwnd: int
    pid: int
    exe: str
    title: str
    class_name: str
    rect: Rect | None = None
    visible: bool = False
    minimized: bool = False
    maximized: bool = False
    foreground: bool = False

    def to_dict(self) -> dict:
        return {
            "hwnd": self.hwnd,
            "hwnd_hex": f"0x{self.hwnd:X}",
            "pid": self.pid,
            "exe": self.exe,
            "title": self.title,
            "class_name": self.class_name,
            "rect": self.rect.to_dict() if self.rect else None,
            "visible": self.visible,
            "minimized": self.minimized,
            "maximized": self.maximized,
            "foreground": self.foreground,
        }


@dataclass
class CaptureRaw:
    """内存中的一次截图结果（BGRA，自上而下）。"""

    data: bytes
    width: int
    height: int
    method: str
    flags: int = 0


# ---------------------------------------------------------------------------
# 窗口枚举与查询
# ---------------------------------------------------------------------------
_process_name_cache: dict[int, str] = {}


def get_process_image_name(pid: int) -> str:
    """按 PID 取可执行文件名（不含路径）；取不到返回空串。结果有缓存。"""
    pid = int(pid or 0)
    if pid <= 0:
        return ""
    if pid in _process_name_cache:
        return _process_name_cache[pid]
    image = ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        try:
            capacity = wt.DWORD(2048)
            buffer = ctypes.create_unicode_buffer(capacity.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(capacity)):
                image = os.path.basename(buffer.value)
        finally:
            kernel32.CloseHandle(handle)
    _process_name_cache[pid] = image
    return image


def _window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def get_window_rect(hwnd: int) -> Rect:
    """窗口矩形（屏幕坐标，含标题栏/边框）。"""
    _ensure_dpi_aware()
    rect = wt.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        _raise_last_error("GetWindowRect")
    return Rect(rect.left, rect.top, rect.right, rect.bottom)


def get_client_rect(hwnd: int) -> Rect:
    """客户区矩形（把客户区左上角换算成屏幕坐标，尺寸来自 GetClientRect）。"""
    _ensure_dpi_aware()
    rect = wt.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        _raise_last_error("GetClientRect")
    origin = wt.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        _raise_last_error("ClientToScreen")
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    return Rect(origin.x, origin.y, origin.x + width, origin.y + height)


def get_monitor_rect(hwnd: int) -> Rect:
    """窗口所在显示器的完整矩形。"""
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not monitor:
        _raise_last_error("MonitorFromWindow")
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        _raise_last_error("GetMonitorInfoW")
    return Rect(info.rcMonitor.left, info.rcMonitor.top,
                info.rcMonitor.right, info.rcMonitor.bottom)


def get_window_dpi(hwnd: int) -> int:
    """窗口 DPI（96 = 100%）。拿不到时返回 96。"""
    if _GET_DPI_FOR_WINDOW is None:
        return 96
    try:
        dpi = int(_GET_DPI_FOR_WINDOW(hwnd))
        return dpi if dpi > 0 else 96
    except Exception:
        return 96


def _get_style(hwnd: int) -> int:
    if _GET_WINDOW_LONG is None:
        return 0
    try:
        return int(_GET_WINDOW_LONG(hwnd, GWL_STYLE))
    except Exception:
        return 0


def _get_exstyle(hwnd: int) -> int:
    if _GET_WINDOW_LONG is None:
        return 0
    try:
        return int(_GET_WINDOW_LONG(hwnd, GWL_EXSTYLE))
    except Exception:
        return 0


def detect_fullscreen(hwnd: int) -> dict:
    """猜测窗口是否处于全屏/无边框全屏状态（只做窗口矩形与样式的启发式判断）。"""
    rect = get_window_rect(hwnd)
    monitor = get_monitor_rect(hwnd)
    style = _get_style(hwnd)
    has_caption = (style & WS_CAPTION) == WS_CAPTION
    is_popup = bool(style & WS_POPUP)
    resizable = bool(style & WS_THICKFRAME)
    zoomed = bool(user32.IsZoomed(hwnd))
    covers = (rect.left <= monitor.left and rect.top <= monitor.top
              and rect.right >= monitor.right and rect.bottom >= monitor.bottom)
    is_fullscreen = bool(covers and not zoomed and (is_popup or not has_caption))
    if is_fullscreen and is_popup and not has_caption:
        reason = "窗口无边框且覆盖整个显示器：无边框全屏（borderless fullscreen）"
    elif is_fullscreen:
        reason = "窗口覆盖整个显示器且无标题栏：疑似全屏"
    elif zoomed:
        reason = "窗口已最大化（普通窗口化，可安全截图/缩放）"
    elif covers:
        reason = "窗口矩形覆盖整个显示器，但仍有标题栏/边框：窗口化"
    else:
        reason = "窗口化"
    return {
        "is_fullscreen": is_fullscreen,
        "reason": reason,
        "covers_monitor": covers,
        "maximized": zoomed,
        "has_caption": has_caption,
        "resizable": resizable,
        "monitor": monitor.to_dict(),
    }


def _make_window_info(hwnd: int, include_process_name: bool = True) -> WindowInfo:
    hwnd = int(hwnd)
    pid_value = wt.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_value))
    pid = int(pid_value.value)
    try:
        rect = get_window_rect(hwnd)
    except Civ6WinError:
        rect = None
    try:
        foreground_window = user32.GetForegroundWindow()
        foreground = bool(foreground_window) and int(foreground_window) == hwnd
    except Exception:
        foreground = False
    return WindowInfo(
        hwnd=hwnd,
        pid=pid,
        exe=get_process_image_name(pid) if include_process_name else "",
        title=_window_title(hwnd),
        class_name=_class_name(hwnd),
        rect=rect,
        visible=bool(user32.IsWindowVisible(hwnd)),
        minimized=bool(user32.IsIconic(hwnd)),
        maximized=bool(user32.IsZoomed(hwnd)),
        foreground=foreground,
    )


def iter_top_level_windows(visible_only: bool = True,
                           include_process_name: bool = True) -> list[WindowInfo]:
    """枚举当前桌面会话的顶层窗口（EnumWindows）。"""
    _ensure_dpi_aware()
    windows: list[WindowInfo] = []

    def _callback(hwnd, _lparam):
        try:
            if visible_only and not user32.IsWindowVisible(hwnd):
                return True
            info = _make_window_info(hwnd, include_process_name=include_process_name)
            windows.append(info)
        except Exception:
            pass
        return True

    callback = WNDENUMPROC(_callback)
    user32.EnumWindows(callback, 0)
    return windows


def list_game_windows(include_launcher: bool = False,
                      include_invisible: bool = False,
                      exes: list[str] | None = None) -> list[WindowInfo]:
    """列出游戏窗口，按窗口面积从大到小排序（主窗口通常最大）。"""
    wanted = exes if exes else list(GAME_EXES) + (list(LAUNCHER_EXES) if include_launcher else [])
    wanted_lower = {name.lower() for name in wanted}
    windows = [window for window in iter_top_level_windows(visible_only=not include_invisible)
               if window.exe.lower() in wanted_lower]
    windows.sort(key=lambda window: (-(window.rect.area if window.rect else 0), window.hwnd))
    return windows


def find_game_window(include_launcher: bool = False,
                     include_invisible: bool = False,
                     prefer_exe: str | None = None) -> WindowInfo | None:
    """返回游戏主窗口；找不到返回 None。prefer_exe 可优先选择某个可执行名（如 DX12）。"""
    windows = list_game_windows(include_launcher=include_launcher,
                                include_invisible=include_invisible)
    if prefer_exe:
        preferred = [window for window in windows
                     if window.exe.lower() == prefer_exe.lower()]
        if preferred:
            return preferred[0]
    return windows[0] if windows else None


def list_windows(proc_names=None,
                 all_windows: bool = False,
                 include_invisible: bool = False) -> list[WindowInfo]:
    """列出窗口（供外部统一入口调用）。

    all_windows=False：只列匹配 proc_names 的窗口（None = 游戏主程序，按面积降序）；
    all_windows=True ：列出当前会话所有顶层窗口（--all 语义）。
    """
    if all_windows:
        return iter_top_level_windows(visible_only=not include_invisible)
    if proc_names is None:
        patterns = list(GAME_EXES)
    elif isinstance(proc_names, str):
        patterns = [proc_names]
    else:
        patterns = [str(item) for item in proc_names if item]
    windows = [window for window in iter_top_level_windows(
        visible_only=not include_invisible)
        if any(_exe_matches_pattern(window.exe, pattern) for pattern in patterns)]
    windows.sort(key=lambda window: (-(window.rect.area if window.rect else 0), window.hwnd))
    return windows


def game_window(proc_names=None, timeout: float = 0.0,
                include_launcher: bool = False) -> WindowInfo:
    """返回游戏主窗口（找不到时抛 WindowNotFoundError）。

    timeout>0 时轮询等待窗口出现（启动后窗口可能延迟约 40s）；等价于
    find_window_by_proc_names(proc_names) 的便捷封装。
    """
    patterns = proc_names
    if patterns is None:
        patterns = list(GAME_EXES) + (list(LAUNCHER_EXES) if include_launcher else [])
    return wait_for_window(patterns, timeout=timeout)


def get_window_state(hwnd: int) -> dict:
    """窗口状态汇总：窗口/客户区矩形、显示器、DPI、最小化/最大化/前台、全屏猜测。"""
    _ensure_dpi_aware()
    if not user32.IsWindow(hwnd):
        raise WindowNotFoundError(f"HWND {hwnd} 无效或窗口已关闭")
    info = _make_window_info(hwnd)
    state = {
        "window": info.to_dict(),
        "client_rect": get_client_rect(hwnd).to_dict(),
        "monitor": get_monitor_rect(hwnd).to_dict(),
        "dpi": get_window_dpi(hwnd),
        "fullscreen": detect_fullscreen(hwnd),
    }
    state["dpi_scale"] = round(state["dpi"] / 96.0, 3)
    return state


# ---------------------------------------------------------------------------
# 窗口操作
# ---------------------------------------------------------------------------
def focus_window(hwnd: int) -> bool:
    """恢复最小化窗口并尝试置前；返回最终是否成为前台窗口。

    Windows 对 SetForegroundWindow 有前台锁限制，这里用 AttachThreadInput 规避：
    把当前线程与前台窗口线程、目标窗口线程临时连接，再 SetForegroundWindow。
    """
    _ensure_dpi_aware()
    if not user32.IsWindow(hwnd):
        raise WindowNotFoundError(f"HWND {hwnd} 无效或窗口已关闭")
    if user32.GetForegroundWindow() and int(user32.GetForegroundWindow()) == hwnd:
        return True
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.2)
    current_thread = kernel32.GetCurrentThreadId()
    foreground_window = user32.GetForegroundWindow()
    thread_ids: list[int] = []
    if foreground_window:
        thread_ids.append(int(user32.GetWindowThreadProcessId(foreground_window, None)))
    thread_ids.append(int(user32.GetWindowThreadProcessId(hwnd, None)))
    attached: list[int] = []
    try:
        for thread_id in sorted({tid for tid in thread_ids if tid and tid != current_thread}):
            if user32.AttachThreadInput(current_thread, thread_id, True):
                attached.append(thread_id)
        user32.BringWindowToTop(hwnd)
        user32.ShowWindow(hwnd, SW_SHOW)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        time.sleep(0.15)
    finally:
        for thread_id in attached:
            user32.AttachThreadInput(current_thread, thread_id, False)
    foreground = user32.GetForegroundWindow()
    return bool(foreground) and int(foreground) == hwnd


def resize_window(hwnd: int, width: int, height: int,
                  x: int | None = None, y: int | None = None,
                  client_area: bool = False) -> dict:
    """移动/缩放窗口。

    client_area=True 时 width/height 按**客户区**尺寸解释（通过 AdjustWindowRectEx 反算外框），
    适合“让游戏渲染区域正好是 1920x1080”的场景；否则按窗口外框尺寸设置。
    """
    _ensure_dpi_aware()
    if not user32.IsWindow(hwnd):
        raise WindowNotFoundError(f"HWND {hwnd} 无效或窗口已关闭")
    if width <= 0 or height <= 0:
        raise ValueError("宽高必须为正整数")
    was_minimized = bool(user32.IsIconic(hwnd))
    was_maximized = bool(user32.IsZoomed(hwnd))
    if was_minimized or was_maximized:
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.15)
    # 用“实测边框差值”换算客户区尺寸：对 DPI 感知与不感知的窗口都准确，
    # 比 AdjustWindowRectEx 更可靠（后者在高 DPI/DPI 虚拟化窗口上会偏差）。
    old_rect = get_window_rect(hwnd)
    old_client = get_client_rect(hwnd)
    frame_width = old_rect.width - old_client.width
    frame_height = old_rect.height - old_client.height
    offset_x = old_client.left - old_rect.left
    offset_y = old_client.top - old_rect.top
    outer_width, outer_height = int(width), int(height)
    target_x = int(x) if x is not None else old_rect.left
    target_y = int(y) if y is not None else old_rect.top
    if client_area:
        plausible = 0 <= frame_width <= 200 and 0 <= frame_height <= 200
        if plausible:
            outer_width = int(width) + frame_width
            outer_height = int(height) + frame_height
            if x is not None:
                target_x = int(x) - offset_x
            if y is not None:
                target_y = int(y) - offset_y
        else:
            # 边框差值异常（例如窗口处于特殊状态）时退回 AdjustWindowRectEx 反算
            rect = wt.RECT(0, 0, int(width), int(height))
            style = _get_style(hwnd)
            exstyle = _get_exstyle(hwnd)
            adjusted = False
            if _ADJUST_WINDOW_RECT_EX_FOR_DPI is not None:
                adjusted = bool(_ADJUST_WINDOW_RECT_EX_FOR_DPI(
                    ctypes.byref(rect), style, False, exstyle, get_window_dpi(hwnd)))
            if not adjusted:
                adjusted = bool(user32.AdjustWindowRectEx(
                    ctypes.byref(rect), style, False, exstyle))
            if adjusted:
                outer_width = rect.right - rect.left
                outer_height = rect.bottom - rect.top
    flags = SWP_NOZORDER | SWP_NOACTIVATE
    resize_attempts: list[dict] = []
    new_rect = old_rect
    new_client = old_client

    def _apply(outer_w: int, outer_h: int) -> tuple[Rect, Rect]:
        if not user32.SetWindowPos(hwnd, None, target_x, target_y,
                                   outer_w, outer_h, flags):
            _raise_last_error("SetWindowPos")
        time.sleep(0.12)
        rect_now = get_window_rect(hwnd)
        client_now = get_client_rect(hwnd)
        resize_attempts.append({
            "outer_size": {"width": outer_w, "height": outer_h},
            "rect_size": {"width": rect_now.width, "height": rect_now.height},
            "client_size": {"width": client_now.width, "height": client_now.height},
        })
        return rect_now, client_now

    new_rect, new_client = _apply(outer_width, outer_height)
    if client_area:
        diff_width = new_client.width - int(width)
        diff_height = new_client.height - int(height)
        if (diff_width or diff_height) and abs(diff_width) <= 8 and abs(diff_height) <= 8:
            # DPI 虚拟化窗口可能有 ±1~2 px 的边框取整误差：微调一次，若更差则回退
            best_outer = (outer_width, outer_height)
            best_rect, best_client = new_rect, new_client
            outer_width += diff_width
            outer_height += diff_height
            new_rect, new_client = _apply(outer_width, outer_height)
            new_diff = abs(new_client.width - int(width)) + abs(new_client.height - int(height))
            old_diff = abs(diff_width) + abs(diff_height)
            if new_diff >= old_diff:
                outer_width, outer_height = best_outer
                new_rect, new_client = _apply(outer_width, outer_height)
                resize_attempts.append({"note": "微调未改善，已回退到更接近的尺寸"})
    return {
        "hwnd": hwnd,
        "client_area_request": bool(client_area),
        "requested": {"width": int(width), "height": int(height)},
        "was_minimized": was_minimized,
        "was_maximized": was_maximized,
        "frame_size": {"width": frame_width, "height": frame_height},
        "old_rect": old_rect.to_dict(),
        "old_client_size": {"width": old_client.width, "height": old_client.height},
        "new_rect": new_rect.to_dict(),
        "new_client_rect": new_client.to_dict(),
        "actual_client_size": {"width": new_client.width, "height": new_client.height},
        "resize_attempts": resize_attempts,
        "note": "若客户区尺寸与请求不一致，可能是游戏自身锁定窗口尺寸；"
                "请在游戏选项中开启任意窗口尺寸（EnableArbitraryWindowSizing）后重试。",
    }


# ---------------------------------------------------------------------------
# 截图
# ---------------------------------------------------------------------------
class _DibSurface:
    """内存 DIB（32bpp，自上而下），供 PrintWindow/BitBlt 写入。"""

    def __init__(self, width: int, height: int):
        self.width = int(width)
        self.height = int(height)
        self.screen_dc = user32.GetDC(None)
        if not self.screen_dc:
            _raise_last_error("GetDC(NULL)")
        self.mem_dc = gdi32.CreateCompatibleDC(self.screen_dc)
        if not self.mem_dc:
            _raise_last_error("CreateCompatibleDC")
        self.bitmap = None
        self.old_object = None
        self.bits = ctypes.c_void_p()
        try:
            info = BITMAPINFO()
            info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            info.bmiHeader.biWidth = self.width
            info.bmiHeader.biHeight = -self.height  # 负高度 = 自上而下
            info.bmiHeader.biPlanes = 1
            info.bmiHeader.biBitCount = 32
            info.bmiHeader.biCompression = BI_RGB
            self.bitmap = gdi32.CreateDIBSection(
                self.mem_dc, ctypes.byref(info), DIB_RGB_COLORS,
                ctypes.byref(self.bits), None, 0)
            if not self.bitmap:
                _raise_last_error("CreateDIBSection")
            self.old_object = gdi32.SelectObject(self.mem_dc, self.bitmap)
        except Exception:
            self.close()
            raise

    def data(self) -> bytes:
        size = self.width * self.height * 4
        return ctypes.string_at(self.bits, size) if size > 0 else b""

    def close(self) -> None:
        if self.old_object:
            gdi32.SelectObject(self.mem_dc, self.old_object)
            self.old_object = None
        if self.bitmap:
            gdi32.DeleteObject(self.bitmap)
            self.bitmap = None
        if self.mem_dc:
            gdi32.DeleteDC(self.mem_dc)
            self.mem_dc = None
        if self.screen_dc:
            user32.ReleaseDC(None, self.screen_dc)
            self.screen_dc = None


def _looks_uniform(data: bytes, width: int, height: int) -> bool:
    """采样判断画面是否纯色（纯黑/纯白），用于识别 PrintWindow 黑屏。"""
    total = width * height
    if not data or total <= 0:
        return True
    view = memoryview(data)
    step = max(1, total // 2048)
    first: bytes | None = None
    for index in range(0, total, step):
        offset = index * 4
        pixel = bytes(view[offset:offset + 3])
        if first is None:
            first = pixel
        elif pixel != first:
            return False
    return True


def _exe_matches_pattern(exe: str, pattern: str) -> bool:
    """进程名匹配：支持精确名、去扩展名、子串，以及简单通配符（如 CivilizationVI*）。"""
    exe_lower = (exe or "").lower()
    pattern_lower = (pattern or "").strip().lower()
    if not exe_lower or not pattern_lower:
        return False
    if "*" in pattern_lower or "?" in pattern_lower:
        return fnmatch.fnmatch(exe_lower, pattern_lower)
    return (exe_lower == pattern_lower
            or os.path.splitext(exe_lower)[0] == pattern_lower
            or pattern_lower in exe_lower)


def find_window_by_proc_names(proc_names=None,
                              include_invisible: bool = False) -> WindowInfo:
    """按可执行名（可含通配符）找面积最大的可见顶层窗口。

    proc_names 为 None 时默认查找游戏主程序（CivilizationVI.exe / CivilizationVI_DX12.exe）；
    也接受单个字符串或字符串列表，例如 "CivilizationVI*"、"LaunchPad.exe"。
    仅返回已创建且有有效矩形的窗口；游戏启动时窗口可能晚于进程出现（实测主菜单约 40s），
    需要等待请用 wait_for_window() 或 capture_window(..., timeout=45)。
    """
    if proc_names is None:
        patterns = list(GAME_EXES)
    elif isinstance(proc_names, str):
        patterns = [proc_names]
    else:
        patterns = [str(item) for item in proc_names if item]
    windows = [window for window in iter_top_level_windows(
        visible_only=not include_invisible)
        if any(_exe_matches_pattern(window.exe, pattern) for pattern in patterns)]
    if not windows:
        raise WindowNotFoundError(
            "未找到匹配进程名 " + " / ".join(patterns) + " 的可见窗口。"
            "游戏启动后窗口可能延迟出现（实测主菜单约 40s），可加 --wait 秒数重试；"
            "或用 --hwnd/--pid 指定窗口。")
    # 优先选有实际尺寸的窗口（刚创建时 rect 可能为 0x0）
    sized = [window for window in windows if window.rect and window.rect.area > 0]
    candidates = sized or windows
    candidates.sort(key=lambda window: (-(window.rect.area if window.rect else 0), window.hwnd))
    return candidates[0]


def wait_for_window(proc_names=None, timeout: float = 45.0,
                    interval: float = 0.5,
                    include_invisible: bool = False) -> WindowInfo:
    """等待游戏窗口出现（启动后窗口可能比进程晚数十秒）。

    timeout=0 时只检查一次；超时抛 WindowNotFoundError（带重试提示）。
    """
    deadline = time.monotonic() + max(0.0, float(timeout or 0.0))
    last_error: WindowNotFoundError | None = None
    while True:
        try:
            return find_window_by_proc_names(proc_names,
                                             include_invisible=include_invisible)
        except WindowNotFoundError as exc:
            last_error = exc
            if time.monotonic() >= deadline:
                raise last_error
            time.sleep(max(0.1, interval))


def _capture_print(hwnd: int, rect: Rect, client_only: bool) -> CaptureRaw | None:
    """PrintWindow 采集。client_only 时用 PW_CLIENTONLY 直接打印客户区。"""
    width, height = rect.width, rect.height
    if width <= 0 or height <= 0:
        return None
    flag_candidates = ([PW_CLIENTONLY | PW_RENDERFULLCONTENT, PW_CLIENTONLY]
                       if client_only else [PW_RENDERFULLCONTENT, 0])
    for flags in flag_candidates:
        surface = _DibSurface(width, height)
        try:
            ok = bool(user32.PrintWindow(hwnd, surface.mem_dc, flags))
            data = surface.data() if ok else b""
        finally:
            surface.close()
        if ok and not _looks_uniform(data, width, height):
            return CaptureRaw(data, width, height, "print", flags)
    return None


def _capture_screen(rect: Rect) -> CaptureRaw | None:
    """从屏幕 DC 采集矩形区域（对 GPU 渲染最可靠）。"""
    width, height = rect.width, rect.height
    if width <= 0 or height <= 0:
        return None
    surface = _DibSurface(width, height)
    source_dc = user32.GetDC(None)
    try:
        ok = bool(gdi32.BitBlt(surface.mem_dc, 0, 0, width, height,
                               source_dc, rect.left, rect.top,
                               SRCCOPY | CAPTUREBLT))
        data = surface.data() if ok else b""
    finally:
        if source_dc:
            user32.ReleaseDC(None, source_dc)
        surface.close()
    if not ok:
        return None
    return CaptureRaw(data, width, height, "screen", SRCCOPY | CAPTUREBLT)


def _capture_gdi(hwnd: int, rect: Rect, client_only: bool) -> CaptureRaw | None:
    """从窗口 DC / 客户区 DC 直接 BitBlt（兜底方案）。"""
    width, height = rect.width, rect.height
    if width <= 0 or height <= 0:
        return None
    surface = _DibSurface(width, height)
    source_dc = user32.GetDC(hwnd) if client_only else user32.GetWindowDC(hwnd)
    try:
        ok = bool(gdi32.BitBlt(surface.mem_dc, 0, 0, width, height,
                               source_dc, 0, 0, SRCCOPY))
        data = surface.data() if ok else b""
    finally:
        if source_dc:
            user32.ReleaseDC(hwnd, source_dc)
        surface.close()
    if not ok:
        return None
    return CaptureRaw(data, width, height, "gdi", SRCCOPY)


def _write_bmp(path: str, raw: CaptureRaw) -> None:
    """Pillow 缺失时的 BMP 降级写出（24bpp，自下而上）。"""
    width, height = raw.width, raw.height
    data = raw.data
    row_padding = (4 - (width * 3) % 4) % 4
    rows: list[bytes] = []
    for y in range(height - 1, -1, -1):
        start = y * width * 4
        row = data[start:start + width * 4]
        rgb = bytearray(width * 3)
        rgb[0::3] = row[0::4]
        rgb[1::3] = row[1::4]
        rgb[2::3] = row[2::4]
        rows.append(bytes(rgb) + b"\x00" * row_padding)
    pixel_data = b"".join(rows)
    file_size = 54 + len(pixel_data)
    header = b"BM" + file_size.to_bytes(4, "little") + (0).to_bytes(4, "little") \
        + (54).to_bytes(4, "little")
    info = (40).to_bytes(4, "little") + width.to_bytes(4, "little", signed=True) \
        + height.to_bytes(4, "little", signed=True) \
        + (1).to_bytes(2, "little") + (24).to_bytes(2, "little") \
        + (0).to_bytes(4, "little") + len(pixel_data).to_bytes(4, "little") \
        + (2835).to_bytes(4, "little", signed=True) + (2835).to_bytes(4, "little", signed=True) \
        + (0).to_bytes(4, "little") + (0).to_bytes(4, "little")
    with open(path, "wb") as stream:
        stream.write(header + info + pixel_data)


def _save_capture(raw: CaptureRaw, out_path: str) -> dict:
    """把内存截图写盘：.png 优先 Pillow，缺失时降级 .bmp；.bmp 直接写 BMP。"""
    out_path = os.path.abspath(os.path.expanduser(str(out_path)))
    parent = os.path.dirname(out_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    suffix = os.path.splitext(out_path)[1].lower() or ".png"
    if suffix == ".bmp":
        _write_bmp(out_path, raw)
        return {"path": out_path, "format": "bmp", "png_via": "bmp"}
    if suffix != ".png":
        raise CaptureError(f"仅支持 .png / .bmp 输出，收到：{suffix}")
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        bmp_path = os.path.splitext(out_path)[0] + ".bmp"
        _write_bmp(bmp_path, raw)
        return {"path": bmp_path, "format": "bmp", "png_via": "bmp-fallback-missing-pillow"}
    image = Image.frombuffer("RGB", (raw.width, raw.height), raw.data,
                             "raw", "BGRX", 0, 1)
    image.save(out_path, format="PNG")
    return {"path": out_path, "format": "png", "png_via": "pillow"}


def capture_window(hwnd: int | None = None,
                   out_path: str = "shot.png",
                   client_area: bool = False,
                   method: str = "auto",
                   focus: bool = False,
                   *,
                   proc_names=None,
                   bring_to_front: bool = True,
                   timeout: float = 0.0) -> dict:
    """截图保存到 out_path。

    参数：
      hwnd          窗口句柄；省略时按 proc_names 自动查找游戏窗口
      out_path      输出路径（.png 优先 Pillow，缺失时降级 .bmp；省略则用时间戳文件名）
      client_area   True 只截客户区（不含标题栏与边框）
      method        auto（print→screen→gdi 依次降级）/ print / screen / gdi
      focus         True 时截图前先恢复并置前窗口
      proc_names    可执行名或通配符（如 "CivilizationVI*"），hwnd 省略时使用；
                    默认游戏主程序 CivilizationVI.exe / CivilizationVI_DX12.exe
      bring_to_front  True 等价于 focus=True（供外部统一 CLI 调用；截图前先置前）
    返回 dict：path/width/height/method_used/client_area/attempts/fullscreen 等（JSON 友好）。
    """
    _ensure_dpi_aware()
    if bring_to_front:
        focus = True
    if hwnd is None:
        hwnd = wait_for_window(proc_names, timeout=timeout).hwnd
    if out_path is None:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = f"civ6_shot_{stamp}.png"
    if not user32.IsWindow(hwnd):
        raise WindowNotFoundError(f"HWND {hwnd} 无效或窗口已关闭")
    method = (method or "auto").lower()
    if method not in ("auto", "print", "screen", "gdi"):
        raise ValueError(f"未知截图方法：{method}（可选 auto/print/screen/gdi）")
    if user32.IsIconic(hwnd):
        if not focus:
            raise CaptureError("窗口已最小化，无法截图。请先加 --focus 让工具恢复窗口，"
                               "或手动恢复游戏窗口后重试。")
        focus_window(hwnd)
        time.sleep(0.35)
    if focus:
        focus_window(hwnd)
        time.sleep(0.25)
    window_rect = get_window_rect(hwnd)
    client_rect = get_client_rect(hwnd)
    rect = client_rect if client_area else window_rect
    if rect.width <= 0 or rect.height <= 0:
        raise CaptureError(f"目标区域尺寸非法：{rect}（窗口可能最小化/尚未渲染完成）")
    fullscreen = detect_fullscreen(hwnd)
    order = {
        "auto": ["print", "screen", "gdi"],
        "print": ["print"],
        "screen": ["screen"],
        "gdi": ["gdi"],
    }[method]
    attempts: list[dict] = []
    raw: CaptureRaw | None = None
    auto_focused = False
    for candidate in order:
        try:
            if candidate == "print":
                raw = _capture_print(hwnd, rect, client_only=client_area)
            elif candidate == "screen":
                # 实测：PrintWindow 失败时置前窗口再从屏幕采集，成功率最高。
                if not focus and not auto_focused and not user32.IsIconic(hwnd):
                    try:
                        focus_window(hwnd)
                        auto_focused = True
                        time.sleep(0.2)
                    except Civ6WinError:
                        pass
                raw = _capture_screen(rect)
            else:
                raw = _capture_gdi(hwnd, rect, client_only=client_area)
        except Exception as exc:  # 单个方法失败不中断，继续降级
            attempts.append({"method": candidate, "ok": False, "error": str(exc)})
            raw = None
        else:
            attempts.append({"method": candidate, "ok": raw is not None})
        if raw is not None:
            break
    if raw is None:
        raise CaptureError(
            "所有截图方法均失败（窗口可能处于独占全屏、被系统保护或已关闭）。"
            "建议：游戏切窗口化、加 --focus、或改用 --method screen。")
    saved = _save_capture(raw, out_path)
    return {
        "hwnd": int(hwnd),
        "title": _window_title(hwnd),
        "client_area": bool(client_area),
        "method_requested": method,
        "method_used": raw.method,
        "method": raw.method,
        "auto_focused": auto_focused,
        "attempts": attempts,
        "width": raw.width,
        "height": raw.height,
        "rect": rect.to_dict(),
        "fullscreen": fullscreen,
        "capture_flags": raw.flags,
        **saved,
    }


# ---------------------------------------------------------------------------
# 文本对齐小工具（中文按 2 列宽计算）
# ---------------------------------------------------------------------------
def _display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def _truncate(text: str, max_width: int) -> str:
    if _display_width(text) <= max_width:
        return text
    result = ""
    width = 0
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if width + char_width > max_width - 1:
            break
        result += char
        width += char_width
    return result + "…"


def _pad(text: str, width: int) -> str:
    text = _truncate(text, width)
    return text + " " * (width - _display_width(text))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_hwnd(value: str) -> int:
    try:
        return int(value, 0)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"无效 HWND：{value}（示例：0x1A2B3C 或 1715004）")


def _target_exes(args) -> list[str]:
    if args.exe:
        return [name.lower() for name in args.exe]
    names = list(GAME_EXES)
    if args.launcher:
        names += list(LAUNCHER_EXES)
    return [name.lower() for name in names]


def _describe_not_found(args) -> str:
    if args.exe:
        return f"未找到可执行名为 {', '.join(args.exe)} 的可见窗口。"
    names = list(GAME_EXES) + (list(LAUNCHER_EXES) if args.launcher else [])
    return ("未找到《文明6》窗口（进程可执行名：" + " / ".join(names) + "）。\n"
            "提示：确认游戏已启动并处于窗口化模式；用 list --all 查看所有顶层窗口；"
            "或用 --hwnd/--pid/--exe 指定其他窗口。")


def _resolve_target_window(args) -> WindowInfo:
    if args.hwnd is not None:
        if not user32.IsWindow(args.hwnd):
            raise WindowNotFoundError(f"HWND {args.hwnd}（0x{args.hwnd:X}）无效或窗口已关闭")
        return _make_window_info(args.hwnd)
    if args.pid is not None:
        windows = [window for window in iter_top_level_windows(visible_only=True)
                   if window.pid == int(args.pid)]
        if not windows:
            raise WindowNotFoundError(f"PID {args.pid} 没有可见顶层窗口")
        windows.sort(key=lambda window: -(window.rect.area if window.rect else 0))
        return windows[0]
    exes = _target_exes(args)
    wait_seconds = float(getattr(args, "wait", 0.0) or 0.0)
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while True:
        windows = [window for window in iter_top_level_windows(visible_only=True)
                   if window.exe.lower() in exes]
        if windows:
            break
        if time.monotonic() >= deadline:
            raise WindowNotFoundError(_describe_not_found(args))
        time.sleep(0.5)
    windows.sort(key=lambda window: (-(window.rect.area if window.rect else 0), window.hwnd))
    return windows[0]


def _print_window_table(windows: list[WindowInfo], title: str) -> None:
    print(f"{title}（{len(windows)} 个）：")
    if not windows:
        return
    header = (f"{'序号':<4} {'HWND':>10} {'PID':>7}  {'EXE':<24} "
              f"{'状态':<8} {'矩形':<32} 标题")
    print(header)
    print("-" * min(140, _display_width(header) + 20))
    for index, window in enumerate(windows, 1):
        state = []
        if window.foreground:
            state.append("前台")
        if window.minimized:
            state.append("最小化")
        if window.maximized:
            state.append("最大化")
        state_text = ",".join(state) if state else "普通"
        rect_text = (f"({window.rect.left},{window.rect.top},"
                     f"{window.rect.right},{window.rect.bottom}) "
                     f"{window.rect.width}x{window.rect.height}") if window.rect else "-"
        print(f"{index:<4} 0x{window.hwnd:08X} {window.pid:>7}  "
              f"{_pad(window.exe, 24)} {_pad(state_text, 8)} "
              f"{_pad(rect_text, 32)} {_truncate(window.title, 60)}")


def cmd_list(args) -> int:
    include_invisible = bool(getattr(args, "include_invisible", False))
    if getattr(args, "all", False):
        windows = iter_top_level_windows(visible_only=not include_invisible)
        if args.exe:
            allowed = {name.lower() for name in args.exe}
            windows = [window for window in windows if window.exe.lower() in allowed]
        windows.sort(key=lambda window: (window.pid, window.hwnd))
        label = "所有顶层窗口"
    else:
        wait_seconds = float(getattr(args, "wait", 0.0) or 0.0)
        deadline = time.monotonic() + max(0.0, wait_seconds)
        while True:
            windows = list_game_windows(include_launcher=args.launcher,
                                        include_invisible=include_invisible,
                                        exes=_target_exes(args))
            if windows or time.monotonic() >= deadline:
                break
            time.sleep(0.5)
        label = "指定进程窗口" if args.exe else "游戏窗口"
    limit = int(getattr(args, "limit", 0) or 0)
    if limit > 0:
        windows = windows[:limit]
    if getattr(args, "json", False):
        print(json.dumps({"label": label, "count": len(windows),
                          "windows": [window.to_dict() for window in windows]},
                         ensure_ascii=False, indent=2))
        return 0 if windows or args.all else 2
    if not windows:
        if args.all:
            print(f"{label}：0 个。")
            return 0
        print(_describe_not_found(args), file=sys.stderr)
        return 2
    _print_window_table(windows, label)
    return 0


def cmd_rect(args) -> int:
    window = _resolve_target_window(args)
    state = get_window_state(window.hwnd)
    if getattr(args, "json", False):
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    client = state["client_rect"]
    fullscreen = state["fullscreen"]
    print(f"窗口：HWND=0x{state['window']['hwnd']:08X}  PID={state['window']['pid']}  "
          f"进程={state['window']['exe']}")
    print(f"标题：{state['window']['title']}")
    print(f"窗口矩形（屏幕坐标）：{state['window']['rect']['left']},"
          f"{state['window']['rect']['top']} → {state['window']['rect']['right']},"
          f"{state['window']['rect']['bottom']}  "
          f"{state['window']['rect']['width']}x{state['window']['rect']['height']}")
    print(f"客户区矩形（屏幕坐标）：{client['left']},{client['top']} → "
          f"{client['right']},{client['bottom']}  {client['width']}x{client['height']}")
    print(f"显示器：{state['monitor']['width']}x{state['monitor']['height']}  "
          f"DPI={state['dpi']}（缩放 {state['dpi_scale']}）")
    print(f"全屏判断：{'是' if fullscreen['is_fullscreen'] else '否'} —— {fullscreen['reason']}")
    if getattr(args, "client", False):
        print(f"客户区尺寸：{client['width']}x{client['height']}")
    return 0


def cmd_shot(args) -> int:
    window = _resolve_target_window(args)
    out_path = args.out
    if not out_path:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = f"civ6_shot_{stamp}.png"
    result = capture_window(window.hwnd, out_path,
                            client_area=bool(args.client),
                            method=args.method,
                            focus=bool(args.focus),
                            bring_to_front=bool(args.focus))
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"截图成功：{result['path']}")
    print(f"  尺寸：{result['width']}x{result['height']}  方法：{result['method_used']}"
          f"（请求 {result['method_requested']}）  客户区：{result['client_area']}")
    if result.get("format") != "png":
        print("  注意：未安装 Pillow，已降级为 BMP。安装 Pillow 后可输出 PNG："
              "python -m pip install Pillow")
    if result["fullscreen"]["is_fullscreen"]:
        print(f"  警告：{result['fullscreen']['reason']}；全屏下截图可能黑屏，建议切换窗口化。")
    return 0


def cmd_resize(args) -> int:
    window = _resolve_target_window(args)
    result = resize_window(window.hwnd, args.width, args.height,
                           x=args.x, y=args.y, client_area=bool(args.client))
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    old = result["old_rect"]
    new = result["new_rect"]
    client = result["new_client_rect"]
    print(f"窗口已调整：HWND=0x{window.hwnd:08X}")
    print(f"  窗口矩形：{old['width']}x{old['height']} → {new['width']}x{new['height']}"
          f"（屏幕坐标 {new['left']},{new['top']}）")
    print(f"  客户区：{client['width']}x{client['height']}"
          f"（请求 {result['requested']['width']}x{result['requested']['height']}"
          f"{'，客户区口径' if result['client_area_request'] else ''}）")
    if result["actual_client_size"]["width"] != result["requested"]["width"] or \
            result["actual_client_size"]["height"] != result["requested"]["height"]:
        print(f"  提示：{result['note']}")
    return 0


def cmd_focus(args) -> int:
    window = _resolve_target_window(args)
    ok = focus_window(window.hwnd)
    if getattr(args, "json", False):
        print(json.dumps({"hwnd": window.hwnd, "focused": ok,
                          "window": _make_window_info(window.hwnd).to_dict()},
                         ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if ok:
        print(f"已置前：HWND=0x{window.hwnd:08X}  {_window_title(window.hwnd)}")
    else:
        print("已尝试置前，但窗口未成为前台窗口（可能被系统前台锁限制或窗口已关闭）。",
              file=sys.stderr)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="以 JSON 输出（便于脚本/AI 解析）")
    common.add_argument("--hwnd", type=_parse_hwnd, default=None,
                        help="直接指定窗口句柄（十进制或 0x 十六进制）")
    common.add_argument("--pid", type=int, default=None,
                        help="按进程 PID 选择该进程面积最大的可见顶层窗口")
    common.add_argument("--exe", action="append", default=None, metavar="NAME",
                        help="按可执行文件名筛选窗口（可重复；默认游戏主程序）")
    common.add_argument("--launcher", action="store_true",
                        help="把 LaunchPad.exe 启动器窗口也纳入候选")
    common.add_argument("--wait", type=float, default=0.0, metavar="SECONDS",
                        help="等待游戏窗口出现最多 N 秒再报错（启动后窗口可能延迟约 40s）")

    parser = argparse.ArgumentParser(
        prog="civ6_win.py",
        description="《文明6》Windows 窗口枚举、矩形查询、移动/缩放、置前与截图（仅窗口化模式）。",
        parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python civ6_win.py list\n"
            "  python civ6_win.py list --all --json\n"
            "  python civ6_win.py rect\n"
            "  python civ6_win.py shot --out game.png --focus\n"
            "  python civ6_win.py shot --out client.png --client --method screen\n"
            "  python civ6_win.py resize --width 1600 --height 900 --client\n"
            "  python civ6_win.py focus\n"))

    subparsers = parser.add_subparsers(dest="command", metavar="{list,rect,shot,resize,focus}")

    parser_list = subparsers.add_parser(
        "list", parents=[common], help="列出游戏窗口（--all 列出所有顶层窗口）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_list.add_argument("--all", action="store_true", help="列出所有顶层窗口而非仅游戏窗口")
    parser_list.add_argument("--include-invisible", action="store_true", help="包含不可见窗口")
    parser_list.add_argument("--limit", type=int, default=0, help="最多显示 N 个（0 = 不限制）")
    parser_list.set_defaults(func=cmd_list)

    parser_rect = subparsers.add_parser(
        "rect", parents=[common], help="输出窗口矩形、客户区矩形与状态",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_rect.add_argument("--client", action="store_true", help="额外强调客户区尺寸")
    parser_rect.set_defaults(func=cmd_rect)

    parser_shot = subparsers.add_parser(
        "shot", parents=[common], help="窗口截图保存 PNG（Pillow 缺失时 BMP 降级）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_shot.add_argument("--out", default=None, metavar="PATH",
                             help="输出路径（默认 civ6_shot_时间戳.png；仅支持 .png/.bmp）")
    parser_shot.add_argument("--client", action="store_true", help="只截客户区")
    parser_shot.add_argument("--method", default="auto", choices=["auto", "print", "screen", "gdi"],
                             help="截图方法（默认 auto：print→screen→gdi 自动降级）")
    parser_shot.add_argument("--focus", action="store_true", help="截图前先恢复并置前窗口")
    parser_shot.set_defaults(func=cmd_shot)

    parser_resize = subparsers.add_parser(
        "resize", parents=[common], help="移动/缩放窗口（窗口化模式）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_resize.add_argument("--width", type=int, required=True, help="宽度")
    parser_resize.add_argument("--height", type=int, required=True, help="高度")
    parser_resize.add_argument("--x", type=int, default=None, help="窗口左上角 X（默认保持不动）")
    parser_resize.add_argument("--y", type=int, default=None, help="窗口左上角 Y（默认保持不动）")
    parser_resize.add_argument("--client", action="store_true",
                               help="宽高按客户区尺寸解释（反算外框）")
    parser_resize.set_defaults(func=cmd_resize)

    parser_focus = subparsers.add_parser(
        "focus", parents=[common], help="恢复最小化并尝试置前",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_focus.set_defaults(func=cmd_focus)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    enable_dpi_awareness()
    try:
        return int(args.func(args))
    except WindowNotFoundError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2
    except CaptureError as exc:
        print(f"[截图失败] {exc}", file=sys.stderr)
        return 3
    except Win32CallError as exc:
        print(f"[Win32 错误] {exc}", file=sys.stderr)
        return 4
    except Civ6WinError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[参数错误] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
