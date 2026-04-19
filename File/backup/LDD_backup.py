import tkinter as tk
import time
import ctypes
import psutil
from tkinter import Menu
import sys
import json
import os
from ctypes import wintypes

# 导入管理窗口模块
from manager_windows import AlarmManagerWindow, MemoManagerWindow, MessageCenterWindow, load_alarms, load_memos, load_messages, AlarmService

# Windows API 常量
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
LWA_ALPHA = 0x00000002
LWA_COLORKEY = 0x00000001

# Windows API 函数
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Windows 电源状态结构体
class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("Reserved1", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong)
    ]

class DynamicIsland:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        
        # 使用Tkinter attributes方法设置窗口置顶
        self.root.attributes("-topmost", True)
        
        # 使用Windows API设置分层窗口（支持透明和圆角）
        hwnd = user32.GetParent(root.winfo_id())
        style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        
        # 添加WS_EX_LAYERED（支持透明）和WS_EX_TOOLWINDOW（不在任务栏显示）
        WS_EX_TOOLWINDOW = 0x00000080
        style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
        
        user32.SetWindowLongW(hwnd, -20, style)
        
        # 设置窗口透明度（0-255）
        user32.SetLayeredWindowAttributes(hwnd, 0, int(0.95 * 255), LWA_ALPHA)
        
        # 加载设置
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        self.settings = self._load_settings()
        
        # 主题（从设置中加载，默认为深色）
        self.is_dark = self.settings.get("is_dark", True)
        self.normal_width = 200
        self.expanded_width = 500  # 增加宽度以容纳状态图标
        self.width = self.normal_width  # 初始宽度为正常宽度
        self.height = 60
        
        # 初始位置：嵌入屏幕顶部，露出80%（刚好看见大时间）
        self.y_hidden = -int(self.height * 0.2)  # 隐藏20%，露出80%
        self.y_visible = 40  # 完全显示时的Y坐标
        self.current_y = self.y_hidden  # 当前Y坐标
        
        # 颜色
        self.bg_dark = "#121212"
        self.bg_light = "#f2f2f2"
        self.fg_dark = "white"
        self.fg_light = "#222222"

        # 画布 - 背景色与初始主题一致
        initial_bg = self.bg_dark if self.is_dark else self.bg_light
        self.canvas = tk.Canvas(
            self.root, width=self.width, height=self.height,
            bg=initial_bg, highlightthickness=0
        )
        self.canvas.pack()

        # 圆角岛
        self.island = self.canvas.create_rounded_rectangle(
            0, 0, self.width, self.height, radius=30, fill=initial_bg, outline=""
        )
        
        # 屏幕居中（先设置位置）
        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - self.normal_width) // 2
        self.root.geometry(f"{self.normal_width}x{self.height}+{x}+{self.y_hidden}")
        
        # 记录当前的基准X坐标用于拖动归位参考（可选，如果完全动态计算则不需要持久化，但为了逻辑清晰，我们主要在动画中动态计算）
        
        # 强制更新窗口，确保窗口已创建完成
        self.root.update_idletasks()
        
        # 应用圆角窗口区域（在窗口完全创建后）
        self._apply_rounded_region()
        
        # 文字标签 - 使用透明背景
        # 时间标签（默认显示，大字体）
        self.time_label = tk.Label(self.canvas, font=("Segoe UI", 24, "bold"), bg=self.bg_dark, fg=self.fg_dark)
        # 根据初始宽度计算居中位置
        initial_time_x = (self.normal_width - 120) // 2  # 120是大字体时间的近似宽度
        self.time_label.place(x=initial_time_x, y=15)
        
        # 详细信息标签（默认隐藏）
        self.cpu_label  = tk.Label(self.canvas, font=("Segoe UI", 11), bg=self.bg_dark, fg=self.fg_dark)
        self.ram_label  = tk.Label(self.canvas, font=("Segoe UI", 11), bg=self.bg_dark, fg=self.fg_dark)
        self.bat_label  = tk.Label(self.canvas, font=("Segoe UI", 11), bg=self.bg_dark, fg=self.fg_dark)
        
        # 闹钟、备忘录和消息中心状态标签(可点击)
        self.alarm_status_label = tk.Label(self.canvas, text="⏰", font=("Segoe UI", 17), 
                                          bg=self.bg_dark, fg="#95a5a6", cursor="hand2")
        self.memo_status_label = tk.Label(self.canvas, text="📝", font=("Segoe UI", 17), 
                                         bg=self.bg_dark, fg="#95a5a6", cursor="hand2")
        self.message_status_label = tk.Label(self.canvas, text="📬", font=("Segoe UI", 17), 
                                            bg=self.bg_dark, fg="#95a5a6", cursor="hand2")
        
        # 绑定点击事件 - 闹钟图标打开闹钟管理窗口
        self.alarm_status_label.bind("<Button-1>", lambda e: self.open_alarm_manager())
        # 绑定点击事件 - 备忘录图标打开备忘录管理窗口
        self.memo_status_label.bind("<Button-1>", lambda e: self.open_memo_manager())
        # 绑定点击事件 - 消息中心图标打开消息中心窗口
        self.message_status_label.bind("<Button-1>", lambda e: self.open_message_center())
        
        # 初始状态：只显示时间，隐藏详细信息
        self.show_details = False
        self._current_width = self.normal_width  # 当前宽度用于动画
        self.cpu_label.place_forget()
        self.ram_label.place_forget()
        self.bat_label.place_forget()
        
        # 动画状态管理
        self._animating = False  # 动画状态锁
        self._drag_animation_id = None  # 拖动归位动画ID
        self._expand_animation_id = None  # 展开动画ID
        self._collapse_animation_id = None  # 收起动画ID
        
        # 加载显示内容设置
        self.show_cpu = self.settings.get("show_cpu", True)
        self.show_ram = self.settings.get("show_ram", True)
        self.show_battery = self.settings.get("show_battery", True)
        
        # 加载透明度设置
        opacity = self.settings.get("opacity", 0.95)
        self.root.attributes("-alpha", opacity)
        
        # 加载刷新频率设置
        self.refresh_interval = self.settings.get("refresh_interval", 1000)
        
        # 初始化闹钟服务（业务逻辑已移至manager_windows.py）
        self.alarm_service = AlarmService(self.root)
        
        # 加载备忘录和消息数据（仅用于状态显示）
        self.memos = load_memos()
        self.messages = load_messages()
        
        # 启动闹钟检查定时器
        self._start_alarm_checker()

        # 移除原有的主题切换按钮和关闭按钮，改为系统托盘操作
        # 初始化系统托盘
        self.create_tray()

        # 拖动
        self.bind_drag()
        self.bind_hover()
        self.apply_theme()
        self.update_info()
        
        # 确保窗口置顶（使用Tkinter attributes方法）
        self.root.attributes("-topmost", True)

    def create_tray(self):
        # 创建系统托盘图标
        self.tray_icon = tk.Menu(self.root, tearoff=0)
        
        # 添加主题切换菜单
        self.tray_icon.add_command(label="切换主题", command=self.toggle_theme)
        self.tray_icon.add_separator()
        self.tray_icon.add_command(label="显示设置界面", command=self.open_settings)
        self.tray_icon.add_command(label="退出程序", command=self.exit_app)

        # 系统托盘（Windows）
        try:
            import pystray
            from PIL import Image, ImageDraw

            # 创建简单的托盘图标
            def create_image():
                width = 64
                height = 64
                color1 = (0, 0, 0) if self.is_dark else (242, 242, 242)
                color2 = (255, 255, 255) if self.is_dark else (34, 34, 34)
                
                image = Image.new('RGB', (width, height), color1)
                draw = ImageDraw.Draw(image)
                draw.ellipse((16, 16, 48, 48), fill=color2)
                return image

            # 托盘菜单回调
            def on_tray_click(icon, item):
                if str(item) == "切换主题":
                    self.toggle_theme()
                    icon.icon = create_image()  # 更新托盘图标颜色
                elif str(item) == "显示设置界面":
                    self.open_settings()
                elif str(item) == "退出程序":
                    icon.stop()
                    self.exit_app()

            # 创建托盘图标
            self.icon = pystray.Icon("DynamicIsland", create_image(), "动态岛监控", menu=pystray.Menu(
                pystray.MenuItem("切换主题", on_tray_click),
                pystray.MenuItem("显示设置界面", on_tray_click),
                pystray.MenuItem("退出程序", on_tray_click)
            ))
            
            # 启动托盘图标（后台运行）
            import threading
            self.tray_thread = threading.Thread(target=self.icon.run, daemon=True)
            self.tray_thread.start()
            
        except ImportError:
            # 如果没有pystray，使用tkinter的简易托盘（仅Windows）
            self.root.tk.call('package', 'require', 'tktray')
            self.tray = self.root.tktray.CreateTrayIcon(
                icon=self.root.tk.call('image', 'create', 'photo', '-data', 
                'iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAACXBIWXMAAAsTAAALEwEAmpwYAAAFHGlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMuYWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxOCAoV2luZG93cykiIHhtcDpDcmVhdGVEYXRlPSIyMDI0LTEwLTE5VDEyOjU0OjU3LTA3OjAwIiB4bXA6TW9kaWZ5RGF0ZT0iMjAyNC0xMC0xOVQxMjo1NDo1Ny0wNzowMCIgeG1wOk1ldGFkYXRhRGF0ZT0iMjAyNC0xMC0xOVQxMjo1NDo1Ny0wNzowMCI+IDxyZGY6U2VxPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0iY3JlYXRlZCIgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlpZDowZDJiNzU5Ny05NzcwLTRiOWItYTc4NC05Nzc5Y2E4OGQ4YjUiIHN0RXZ0OndoZW49IjIwMjQtMTAtMTlUMTI6NTQ6NTctMDc6MDAiIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkFkb2JlIFBob3Rvc2hvcCBDQyAyMDE4IChXaW5kb3dzKSIvPiA8L3JkZjpTZXE+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+kk23lgAAANklEQVR42u3RAQ0AAAgDoC/r58hM58s4iNl7hSGgoKKgYBBhB4bGd48GGRgYGJ4bGh4bGd48GGRgYGJ4bGh4bGfC0+gAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAyNC0xMC0xOVQxMjo1NDo1Ny0wNzowMOo7214AAAAldEVYdGRhdGU6bW9kaWZ5ADIwMjQtMTAtMTlUMTI6NTQ6NTctMDc6MDDJ531RAAAAAElFTkSuQmCC'),
                command=self.on_tray_click
            )
            self.tray.AddMenuEntry("切换主题", self.toggle_theme)
            self.tray.AddMenuEntry("显示设置界面", self.open_settings)
            self.tray.AddMenuEntry("退出程序", self.exit_app)

    def on_tray_click(self, event):
        """简易托盘点击事件"""
        pass

    def show_window(self):
        """显示窗口"""
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def exit_app(self):
        """退出程序"""
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def apply_theme(self):
            bg = self.bg_dark if self.is_dark else self.bg_light
            fg = self.fg_dark if self.is_dark else self.fg_light
            # 画布背景保持白色（用于透明色键），不随主题变化
            self.canvas.itemconfig(self.island, fill=bg)
            for w in [self.time_label, self.cpu_label, self.ram_label, self.bat_label, 
                     self.alarm_status_label, self.memo_status_label, self.message_status_label]:
                w.config(bg=bg, fg=fg if w in [self.time_label, self.cpu_label, self.ram_label, self.bat_label] else w.cget("fg"))
            # 更新托盘图标（如果使用pystray）
            if hasattr(self, 'icon') and self.icon:
                try:
                    from PIL import Image, ImageDraw
                    width = 64
                    height = 64
                    color1 = (0, 0, 0) if self.is_dark else (242, 242, 242)
                    color2 = (255, 255, 255) if self.is_dark else (34, 34, 34)
                    
                    image = Image.new('RGB', (width, height), color1)
                    draw = ImageDraw.Draw(image)
                    draw.ellipse((16, 16, 48, 48), fill=color2)
                    self.icon.icon = image
                except:
                    pass
            
            # 应用圆角窗口区域
            self._apply_rounded_region()

    def _apply_rounded_region(self):
        """使用Windows API设置窗口圆角区域"""
        hwnd = user32.GetParent(self.root.winfo_id())
        
        # 创建圆角矩形区域
        radius = 30
        width = self.width
        height = self.height
        
        # 创建圆角矩形区域
        hrgn = gdi32.CreateRoundRectRgn(0, 0, width, height, radius * 2, radius * 2)
        
        # 应用区域到窗口
        user32.SetWindowRgn(hwnd, hrgn, True)

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        # 保存设置
        self.settings["is_dark"] = self.is_dark
        self._save_settings()
        self.apply_theme()

    def bind_drag(self):
        # 绑定左键拖动事件到所有组件
        widgets = [self.canvas, self.time_label, self.cpu_label, self.ram_label, self.bat_label]
        for widget in widgets:
            widget.bind("<Button-1>", self.start_move)
            widget.bind("<B1-Motion>", self.on_move)
            widget.bind("<ButtonRelease-1>", self.on_release_move)

    def start_move(self, e):
        self.ox, self.oy = e.x, e.y
        # 记录拖动开始时的位置
        self.drag_start_x = self.root.winfo_x()
        self.drag_start_y = self.root.winfo_y()

    def on_move(self, e):
        dx = e.x - self.ox
        dy = e.y - self.oy
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def _cancel_drag_animation(self):
        """取消正在进行的拖动归位动画"""
        if self._drag_animation_id is not None:
            try:
                self.root.after_cancel(self._drag_animation_id)
            except:
                pass
            self._drag_animation_id = None
        self._animating = False  # 释放动画锁
    
    def _cancel_all_animations(self):
        """取消所有正在进行的动画"""
        # 取消拖动归位动画
        if self._drag_animation_id is not None:
            try:
                self.root.after_cancel(self._drag_animation_id)
            except:
                pass
            self._drag_animation_id = None
        
        # 取消展开动画
        if self._expand_animation_id is not None:
            try:
                self.root.after_cancel(self._expand_animation_id)
            except:
                pass
            self._expand_animation_id = None
        
        # 取消收起动画
        if self._collapse_animation_id is not None:
            try:
                self.root.after_cancel(self._collapse_animation_id)
            except:
                pass
            self._collapse_animation_id = None
        
        # 释放动画锁
        self._animating = False

    def on_release_move(self, e):
        """鼠标释放时处理"""
        # 只有在缩小状态（未展开）时才自动归位
        if not self.show_details:
            current_x = self.root.winfo_x()
            current_y = self.root.winfo_y()
            
            # 计算应该居中的X坐标
            screen_w = self.root.winfo_screenwidth()
            target_x = (screen_w - self.width) // 2
            
            # 如果位置发生了变化，则动画归位
            if abs(current_x - target_x) > 5 or abs(current_y - self.current_y) > 5:
                # 取消之前的动画（如果有）
                self._cancel_drag_animation()
                # 启动新的归位动画
                self._animate_back_to_position(target_x, self.current_y)

    def _animate_back_to_position(self, target_x, target_y):
        """动画归位到指定位置（使用可取消的动画机制）"""
        self._animating = True  # 设置动画锁
        
        def animate_step():
            try:
                # 检查窗口是否仍然有效
                if not self.root.winfo_exists():
                    self._drag_animation_id = None
                    self._animating = False
                    return
                
                current_x = self.root.winfo_x()
                current_y = self.root.winfo_y()
                
                step_x = (target_x - current_x) * 0.3
                step_y = (target_y - current_y) * 0.3
                
                # 如果移动量很小，直接设置到目标位置
                if abs(step_x) < 0.5 and abs(step_y) < 0.5:
                    self.root.geometry(f"{self.width}x{self.height}+{int(target_x)}+{int(target_y)}")
                    self._drag_animation_id = None
                    self._animating = False  # 释放动画锁
                    return
                
                # 更新位置
                new_x = current_x + step_x
                new_y = current_y + step_y
                self.root.geometry(f"{self.width}x{self.height}+{int(new_x)}+{int(new_y)}")
                
                # 继续动画，并保存动画ID
                self._drag_animation_id = self.root.after(10, animate_step)
            except Exception as e:
                # 如果出现异常，清理状态
                print(f"拖动归位动画错误: {e}")
                self._drag_animation_id = None
                self._animating = False
        
        # 启动动画
        animate_step()

    def bind_hover(self):
        # 绑定右键点击事件到画布和所有标签
        widgets = [self.canvas, self.time_label, self.cpu_label, self.ram_label, self.bat_label]
        for widget in widgets:
            widget.bind("<Button-3>", self.on_right_click)

    def on_right_click(self, e):
        """右键点击切换显示状态"""
        # 取消所有正在进行的动画
        self._cancel_all_animations()
        
        if not self.show_details:
            # 切换到详细信息模式：先向下移动，再展开宽度
            self._expand_to_details()
        else:
            # 切换回简洁模式：先收缩宽度，再向上移动隐藏
            self._collapse_to_hidden()

    def open_settings(self):
        """打开设置窗口(单例模式)"""
        # 如果设置窗口已存在,则将其置于顶层并返回
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        
        # 创建设置窗口
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("⚙️ 动态岛监控设置")
        self.settings_window.geometry("550x750")
        self.settings_window.resizable(False, False)
        
        # 设置窗口图标（程序化生成）
        try:
            # 创建一个32x32的图标
            icon_image = tk.PhotoImage(width=32, height=32)
            
            # 绘制一个简单的齿轮图案（蓝色背景 + 白色齿轮）
            for x in range(32):
                for y in range(32):
                    # 计算到中心的距离
                    dx = x - 16
                    dy = y - 16
                    distance = (dx*dx + dy*dy) ** 0.5
                    
                    # 外圆（蓝色背景）
                    if distance < 15:
                        icon_image.put("#3498db", (x, y))
                    # 内圆（白色中心）
                    elif distance < 10:
                        icon_image.put("white", (x, y))
                    # 齿轮齿（简单实现：在特定角度添加像素）
                    elif distance < 15 and (x % 8 < 2 or y % 8 < 2):
                        icon_image.put("#2980b9", (x, y))
            
            # 设置为窗口图标
            self.settings_window.iconphoto(True, icon_image)
        except Exception as e:
            # 如果图标加载失败，忽略错误继续运行
            print(f"设置窗口图标加载失败: {e}")
        
        # 居中显示
        screen_w = self.settings_window.winfo_screenwidth()
        screen_h = self.settings_window.winfo_screenheight()
        x = (screen_w - 550) // 2
        y = (screen_h - 750) // 2
        self.settings_window.geometry(f"550x750+{x}+{y}")
        
        # 设置窗口始终在最前
        self.settings_window.attributes("-topmost", True)
        
        # 应用现代化样式
        self._apply_modern_style()
        
        # 窗口关闭时清理引用
        self.settings_window.protocol("WM_DELETE_WINDOW", self._on_settings_close)
        
        # 主容器
        main_container = tk.Frame(self.settings_window, bg="#f5f5f5")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 标题区域
        header_frame = tk.Frame(main_container, bg="#2c3e50", height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="⚙️ 动态岛监控系统设置", 
                              font=("Microsoft YaHei", 16, "bold"), 
                              fg="white", bg="#2c3e50")
        title_label.pack(expand=True)
        
        # 内容区域（使用Canvas和Scrollbar实现滚动）
        canvas = tk.Canvas(main_container, bg="#f5f5f5", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview,
                                bg="#ecf0f1", troughcolor="#bdc3c7",
                                activebackground="#95a5a6")
        scrollable_frame = tk.Frame(canvas, bg="#f5f5f5")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 内容区域
        content_frame = tk.Frame(scrollable_frame, bg="#f5f5f5", padx=20, pady=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # ========== 外观设置卡片 ==========
        self._create_appearance_card(content_frame)
        
        # ========== 透明度设置卡片 ==========
        self._create_opacity_card(content_frame)
        
        # ========== 刷新频率设置卡片 ==========
        self._create_refresh_rate_card(content_frame)
        
        # ========== 显示内容设置卡片 ==========
        self._create_display_content_card(content_frame)
        
        # ========== 关于信息卡片 ==========
        self._create_about_card(content_frame)
        
        # 底部按钮区域
        button_frame = tk.Frame(main_container, bg="#ecf0f1", pady=12)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        close_btn = tk.Button(button_frame, text="✖ 关闭", 
                             command=self._on_settings_close,
                             font=("Microsoft YaHei", 11, "bold"),
                             bg="#e74c3c", fg="white",
                             activebackground="#c0392b", activeforeground="white",
                             relief=tk.FLAT, cursor="hand2",
                             padx=35, pady=10)
        close_btn.pack()
    
    def _apply_modern_style(self):
        """应用现代化样式到设置窗口"""
        # 配置样式
        style_config = {
            'bg': '#f5f5f5',
            'fg': '#333333',
            'font': ('Microsoft YaHei', 10),
            'select_bg': '#3498db',
            'select_fg': 'white'
        }
        
        # 设置窗口背景色
        self.settings_window.configure(bg=style_config['bg'])
    
    def _create_card(self, parent, title, color, icon=""):
        """创建通用卡片框架"""
        card_frame = tk.Frame(parent, bg="white", relief=tk.RAISED, bd=1)
        card_frame.pack(fill=tk.X, pady=(0, 12))
        
        card_header = tk.Frame(card_frame, bg=color, height=35)
        card_header.pack(fill=tk.X)
        card_header.pack_propagate(False)
        
        card_title = tk.Label(card_header, text=f"{icon} {title}", 
                             font=("Segoe UI", 11, "bold"),
                             fg="white", bg=color)
        card_title.pack(side=tk.LEFT, padx=10, pady=5)
        
        card_content = tk.Frame(card_frame, bg="white", padx=15, pady=12)
        card_content.pack(fill=tk.X)
        
        return card_content
    
    def _create_appearance_card(self, parent):
        """创建外观设置卡片"""
        card_content = self._create_card(parent, "外观设置", "#3498db", "🎨")
        
        # 当前主题显示
        theme_info_frame = tk.Frame(card_content, bg="white")
        theme_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        theme_label = tk.Label(theme_info_frame, text="当前主题:", 
                              font=("Segoe UI", 10), fg="#555", bg="white")
        theme_label.pack(side=tk.LEFT)
        
        self.theme_value_label = tk.Label(theme_info_frame, 
                                         text="🌙 深色模式" if self.is_dark else "☀️ 浅色模式",
                                         font=("Segoe UI", 10, "bold"), 
                                         fg="#2c3e50", bg="white")
        self.theme_value_label.pack(side=tk.RIGHT)
        
        # 切换主题按钮
        toggle_btn = tk.Button(card_content, text="🔄 切换主题", 
                              command=self._toggle_theme_from_settings,
                              font=("Segoe UI", 10),
                              bg="#3498db", fg="white",
                              activebackground="#2980b9", activeforeground="white",
                              relief=tk.FLAT, cursor="hand2",
                              padx=20, pady=8)
        toggle_btn.pack(fill=tk.X)
    
    def _create_opacity_card(self, parent):
        """创建透明度设置卡片"""
        card_content = self._create_card(parent, "透明度设置", "#9b59b6", "🔍")
        
        # 当前透明度显示
        opacity_info_frame = tk.Frame(card_content, bg="white")
        opacity_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        opacity_label = tk.Label(opacity_info_frame, text="当前透明度:", 
                                font=("Segoe UI", 10), fg="#555", bg="white")
        opacity_label.pack(side=tk.LEFT)
        
        current_opacity = int(self.root.attributes("-alpha") * 100)
        self.opacity_value_label = tk.Label(opacity_info_frame, 
                                           text=f"{current_opacity}%",
                                           font=("Segoe UI", 10, "bold"), 
                                           fg="#9b59b6", bg="white")
        self.opacity_value_label.pack(side=tk.RIGHT)
        
        # 透明度滑块
        slider_frame = tk.Frame(card_content, bg="white")
        slider_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.opacity_slider = tk.Scale(slider_frame, from_=50, to=100, 
                                       orient=tk.HORIZONTAL,
                                       font=("Segoe UI", 9),
                                       bg="white", fg="#333",
                                       troughcolor="#ddd",
                                       sliderlength=20,
                                       length=280,
                                       showvalue=False,
                                       command=self._on_opacity_change)
        self.opacity_slider.set(current_opacity)
        self.opacity_slider.pack(fill=tk.X)
        
        # 滑块标签
        label_frame = tk.Frame(card_content, bg="white")
        label_frame.pack(fill=tk.X)
        
        tk.Label(label_frame, text="透明", font=("Segoe UI", 8), 
                fg="#999", bg="white").pack(side=tk.LEFT)
        tk.Label(label_frame, text="不透明", font=("Segoe UI", 8), 
                fg="#999", bg="white").pack(side=tk.RIGHT)
    
    def _create_refresh_rate_card(self, parent):
        """创建刷新频率设置卡片"""
        card_content = self._create_card(parent, "刷新频率", "#e67e22", "⚡")
        
        # 当前刷新率显示
        rate_info_frame = tk.Frame(card_content, bg="white")
        rate_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        rate_label = tk.Label(rate_info_frame, text="当前刷新间隔:", 
                             font=("Segoe UI", 10), fg="#555", bg="white")
        rate_label.pack(side=tk.LEFT)
        
        self.rate_value_label = tk.Label(rate_info_frame, 
                                        text="1秒",
                                        font=("Segoe UI", 10, "bold"), 
                                        fg="#e67e22", bg="white")
        self.rate_value_label.pack(side=tk.RIGHT)
        
        # 刷新率选择按钮
        btn_frame = tk.Frame(card_content, bg="white")
        btn_frame.pack(fill=tk.X)
        
        rates = [("0.5秒", 500), ("1秒", 1000), ("2秒", 2000), ("3秒", 3000)]
        for text, value in rates:
            btn = tk.Button(btn_frame, text=text, 
                           command=lambda v=value, t=text: self._change_refresh_rate(v, t),
                           font=("Segoe UI", 9),
                           bg="#ecf0f1", fg="#333",
                           activebackground="#d5dbdb", activeforeground="#333",
                           relief=tk.FLAT, cursor="hand2",
                           padx=10, pady=5)
            btn.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
    
    def _create_display_content_card(self, parent):
        """创建显示内容设置卡片"""
        card_content = self._create_card(parent, "显示内容", "#1abc9c", "📊")
        
        # CPU使用率
        cpu_frame = tk.Frame(card_content, bg="white")
        cpu_frame.pack(fill=tk.X, pady=3)
        
        self.cpu_var = tk.BooleanVar(value=True)
        cpu_check = tk.Checkbutton(cpu_frame, text="CPU 使用率", 
                                  variable=self.cpu_var,
                                  font=("Segoe UI", 10),
                                  bg="white", fg="#333",
                                  selectcolor="#ecf0f1",
                                  activebackground="white",
                                  command=self._update_display_content)
        cpu_check.pack(side=tk.LEFT)
        
        # 内存使用率
        ram_frame = tk.Frame(card_content, bg="white")
        ram_frame.pack(fill=tk.X, pady=3)
        
        self.ram_var = tk.BooleanVar(value=True)
        ram_check = tk.Checkbutton(ram_frame, text="内存使用率", 
                                  variable=self.ram_var,
                                  font=("Segoe UI", 10),
                                  bg="white", fg="#333",
                                  selectcolor="#ecf0f1",
                                  activebackground="white",
                                  command=self._update_display_content)
        ram_check.pack(side=tk.LEFT)
        
        # 电池状态
        bat_frame = tk.Frame(card_content, bg="white")
        bat_frame.pack(fill=tk.X, pady=3)
        
        self.bat_var = tk.BooleanVar(value=True)
        bat_check = tk.Checkbutton(bat_frame, text="电池状态", 
                                  variable=self.bat_var,
                                  font=("Segoe UI", 10),
                                  bg="white", fg="#333",
                                  selectcolor="#ecf0f1",
                                  activebackground="white",
                                  command=self._update_display_content)
        bat_check.pack(side=tk.LEFT)
    
    def _create_about_card(self, parent):
        """创建关于信息卡片"""
        card_content = self._create_card(parent, "关于", "#95a5a6", "ℹ️")
        
        info_text = "动态岛监控系统 v1.0\n实时监控系统资源状态\n\n功能特性：\n• 圆角窗口设计\n• 深色/浅色主题切换\n• 透明度调节\n• 自定义刷新频率\n• 灵活的内容显示"
        info_label = tk.Label(card_content, text=info_text,
                             font=("Segoe UI", 9), fg="#777", bg="white",
                             justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
    
    def _on_opacity_change(self, value):
        """透明度滑块变化回调"""
        opacity = int(value) / 100.0
        self.root.attributes("-alpha", opacity)
        self.opacity_value_label.config(text=f"{value}%")
        
        # 保存设置
        self.settings["opacity"] = opacity
        self._save_settings()
    
    def _change_refresh_rate(self, interval_ms, text):
        """更改刷新频率"""
        self.refresh_interval = interval_ms
        self.rate_value_label.config(text=text)
        
        # 重新启动更新循环
        if hasattr(self, '_update_job'):
            self.root.after_cancel(self._update_job)
        self.update_info()
        
        # 保存设置
        self.settings["refresh_interval"] = interval_ms
        self._save_settings()
    
    def _update_display_content(self):
        """更新显示内容"""
        # 保存设置
        self.settings["show_cpu"] = self.cpu_var.get()
        self.settings["show_ram"] = self.ram_var.get()
        self.settings["show_battery"] = self.bat_var.get()
        self._save_settings()
        
        # 更新内部变量
        self.show_cpu = self.cpu_var.get()
        self.show_ram = self.ram_var.get()
        self.show_battery = self.bat_var.get()
        
        # 如果当前是展开状态，立即更新显示
        if self.show_details:
            self._apply_display_content()
    
    def _apply_display_content(self):
        """应用显示内容设置"""
        # 根据设置显示或隐藏标签
        if self.show_cpu:
            self.cpu_label.place(x=130, y=20)
        else:
            self.cpu_label.place_forget()
            
        if self.show_ram:
            self.ram_label.place(x=200, y=20)
        else:
            self.ram_label.place_forget()
            
        if self.show_battery:
            self.bat_label.place(x=320, y=18)
        else:
            self.bat_label.place_forget()
    
    def _update_status_indicators(self):
        """更新闹钟、备忘录和消息中心状态指示器"""
        # 从JSON文件重新加载最新数据，确保状态同步
        self.alarms = load_alarms()
        self.memos = load_memos()
        self.messages = load_messages()
        
        # 检查是否有启用的闹钟
        has_active_alarm = any(alarm.get("enabled", True) for alarm in self.alarms)
        
        # 检查是否有备忘录
        has_memo = len(self.memos) > 0
        
        # 检查是否有未读消息
        unread_count = sum(1 for msg in self.messages if not msg.get("read", False))
        
        # 设置闹钟标签颜色和位置
        if has_active_alarm:
            self.alarm_status_label.config(fg="#3498db")  # 蓝色表示有闹钟
        else:
            self.alarm_status_label.config(fg="#95a5a6")  # 灰色表示无闹钟
        
        # 设置备忘录标签颜色和位置
        if has_memo:
            self.memo_status_label.config(fg="#3498db")  # 蓝色表示有备忘
        else:
            self.memo_status_label.config(fg="#95a5a6")  # 灰色表示无备忘
        
        # 设置消息中心标签颜色和显示未读数量
        if unread_count > 0:
            self.message_status_label.config(text=f"📬{unread_count}", fg="#e74c3c")  # 红色表示有未读消息
        else:
            self.message_status_label.config(text="📬", fg="#95a5a6")  # 灰色表示无未读消息
        
        # 显示标签（在展开模式下）- 放在最右边
        # 使用expanded_width确保位置正确，避免遮挡CPU
        message_x = self.expanded_width - 45  # 距离右边45像素
        memo_x = message_x - 32     # 备忘录在消息中心左侧32像素
        alarm_x = memo_x - 32       # 闹钟在备忘录左侧32像素
        
        self.message_status_label.place(x=message_x, y=16)
        self.alarm_status_label.place(x=alarm_x, y=16)
        self.memo_status_label.place(x=memo_x, y=16)
    
    def _toggle_theme_from_settings(self):
        """从设置窗口切换主题"""
        self.toggle_theme()
        # 更新标签显示
        if hasattr(self, 'theme_value_label') and self.theme_value_label.winfo_exists():
            self.theme_value_label.config(text="🌙 深色模式" if self.is_dark else "☀️ 浅色模式")

    def _on_settings_close(self):
        """关闭设置窗口"""
        if hasattr(self, 'settings_window'):
            # 解绑鼠标滚轮事件
            self.settings_window.unbind_all("<MouseWheel>")
            self.settings_window.destroy()
            delattr(self, 'settings_window')
            
            # 重新应用主窗口的WS_EX_TOOLWINDOW样式，防止任务栏显示
            self._reapply_toolwindow_style()
    
    def _reapply_toolwindow_style(self):
        """重新应用工具窗口样式，确保不在任务栏显示"""
        try:
            hwnd = user32.GetParent(self.root.winfo_id())
            style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            
            # 确保WS_EX_TOOLWINDOW和WS_EX_LAYERED样式都存在
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_LAYERED = 0x00080000
            
            if not (style & WS_EX_TOOLWINDOW):
                style |= WS_EX_TOOLWINDOW | WS_EX_LAYERED
                user32.SetWindowLongW(hwnd, -20, style)
                
                # 强制刷新窗口
                self.root.update_idletasks()
        except Exception as e:
            print(f"重新应用窗口样式失败: {e}")
    
    def _expand_to_details(self):
        """展开到详细信息模式（带动画）"""
        self.show_details = True
        self._animating = True  # 设置动画锁
        
        # 第一步：向下移动窗口
        self._animate_position(self.y_visible, self._switch_content_first, "expand")

    def _switch_content_first(self):
        """向下移动后先切换内容"""
        # 隐藏大字体时间
        self.time_label.place_forget()
        # 显示小字体时间和详细信息（此时窗口还是窄的）
        self.time_label.config(font=("Segoe UI", 12, "bold"))
        self.time_label.place(x=30, y=18)
        
        # 根据设置显示内容
        self._apply_display_content()
        
        # 显示闹钟和备忘录状态标签
        self._update_status_indicators()
        
        # 第二步：扩展窗口宽度（内容已经在窄窗口中显示，然后向两侧展开）
        self._animate_width(self.expanded_width, self._on_expand_complete, "expand")

    def _switch_to_simple_mode_first(self):
        """首先切换到简洁模式"""
        self.cpu_label.place_forget()
        self.ram_label.place_forget()
        self.bat_label.place_forget()
        # 隐藏闹钟和备忘录状态标签
        self.alarm_status_label.place_forget()
        self.memo_status_label.place_forget()
        self.time_label.config(font=("Segoe UI", 24, "bold"))
        
        # 更新时间位置
        time_x = (self.normal_width - 120) // 2
        self.time_label.place(x=time_x, y=15)
        
        # 第二步：收缩窗口宽度
        self._animate_width(self.normal_width, self._move_up_after_collapse, "collapse")

    def _on_expand_complete(self):
        """展开动画完成回调"""
        self._expand_animation_id = None
        self._animating = False  # 释放动画锁

    def _collapse_to_hidden(self):
        """收缩到隐藏模式（带动画）"""
        self.show_details = False
        self._animating = True  # 设置动画锁
        
        # 第一步：先切换内容（隐藏详细信息，恢复大字体）
        self._switch_to_simple_mode_first()

    def _move_up_after_collapse(self):
        """宽度收缩后向上移动隐藏"""
        self._animate_position(self.y_hidden, self._on_collapse_complete, "collapse")

    def _on_collapse_complete(self):
        """收起动画完成回调"""
        self._collapse_animation_id = None
        self._animating = False  # 释放动画锁

    def _animate_position(self, target_y, callback=None, animation_type="expand"):
        """垂直位置缓动动画（优化版，支持取消）"""
        
        def animate_step():
            try:
                if not self.root.winfo_exists():
                    return
                
                step = (target_y - self.current_y) * 0.3
                
                if abs(step) < 0.5:
                    self.current_y = target_y
                    screen_w = self.root.winfo_screenwidth()
                    x = (screen_w - self.width) // 2
                    self.root.geometry(f"{self.width}x{self.height}+{x}+{int(self.current_y)}")
                    if callback:
                        callback()
                    return
                
                self.current_y += step
                screen_w = self.root.winfo_screenwidth()
                x = (screen_w - self.width) // 2
                self.root.geometry(f"{self.width}x{self.height}+{x}+{int(self.current_y)}")
                
                # 保存动画ID以便取消
                if animation_type == "expand":
                    self._expand_animation_id = self.root.after(10, animate_step)
                elif animation_type == "collapse":
                    self._collapse_animation_id = self.root.after(10, animate_step)
                else:
                    self.root.after(10, animate_step)
            except Exception as e:
                # 如果出现异常，清理状态
                print(f"位置动画错误: {e}")
                self._drag_animation_id = None
                self._animating = False
        
        # 启动动画
        animate_step()

    def _animate_width(self, target_width, callback=None, animation_type="expand"):
        """水平宽度缓动动画（优化版，支持取消）"""
        if not hasattr(self, '_current_width'):
            self._current_width = self.width
        
        def animate_step():
            try:
                if not self.root.winfo_exists():
                    return
                
                step = (target_width - self._current_width) * 0.3
                
                if abs(step) < 1:
                    self._current_width = target_width
                    self.width = target_width
                    self._apply_geometry(target_width)
                    self._apply_rounded_region()
                    if callback:
                        callback()
                    return
                
                self._current_width += step
                self._apply_geometry(int(self._current_width))
                
                # 保存动画ID以便取消
                if animation_type == "expand":
                    self._expand_animation_id = self.root.after(10, animate_step)
                elif animation_type == "collapse":
                    self._collapse_animation_id = self.root.after(10, animate_step)
                else:
                    self.root.after(10, animate_step)
            except Exception as e:
                print(f"宽度动画错误: {e}")
        
        animate_step()

    def _apply_geometry(self, width):
        """应用几何尺寸变更"""
        # 动态计算居中位置，实现以中心为锚点的展开效果
        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - int(width)) // 2
        
        self.root.geometry(f"{int(width)}x{self.height}+{x}+{int(self.current_y)}")
        self.canvas.config(width=int(width))
        
        # 重建圆角矩形
        self.canvas.delete(self.island)
        self.island = self.canvas.create_rounded_rectangle(
            0, 0, int(width), self.height, radius=30, 
            fill=self.bg_dark if self.is_dark else self.bg_light, 
            outline=""
        )

    def get_battery(self):
        try:
            sps = SYSTEM_POWER_STATUS()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
            percent = sps.BatteryLifePercent
            if percent == 255:
                return "🔌 AC"
            elif percent == -1:
                return "台式机"
            return f"🔋 {percent}%"
        except:
            return "---"

    def update_info(self):
        self.time_label.config(text=time.strftime("%H:%M:%S"))
        
        # 根据设置显示/隐藏CPU、RAM、电池信息
        if hasattr(self, 'show_cpu') and self.show_cpu:
            self.cpu_label.config(text=f"CPU {psutil.cpu_percent(0):.0f}%")
        else:
            self.cpu_label.config(text="")
            
        if hasattr(self, 'show_ram') and self.show_ram:
            self.ram_label.config(text=f"RAM {psutil.virtual_memory().percent:.0f}%")
        else:
            self.ram_label.config(text="")
            
        if hasattr(self, 'show_battery') and self.show_battery:
            self.bat_label.config(text=self.get_battery())
        else:
            self.bat_label.config(text="")
        
        # 检查闹钟
        self._check_alarms()
        
        # 使用可配置的刷新间隔
        self.root.after(self.refresh_interval, self.update_info)

    def _start_alarm_checker(self):
        """启动闹钟检查定时器"""
        # 每分钟检查一次闹钟
        self.alarm_service.check_and_trigger_alarms()
        # 更新状态指示器（包括消息中心）
        self._update_status_indicators()
        self.root.after(60000, self._start_alarm_checker)  # 60秒后再次检查
    
    def _check_alarms(self):
        """检查闹钟（已委托给AlarmService）"""
        # 此方法保留用于兼容性，实际逻辑在AlarmService中
        self.alarm_service.check_and_trigger_alarms()

    def _load_settings(self):
        """加载设置文件"""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                return json.load(f)
        return {}

    def _save_settings(self):
        """保存设置文件"""
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f)
        
        # 如果当前是展开状态，更新状态指示器
        if self.show_details:
            self._update_status_indicators()

    def hide_window(self, event=None):
        """隐藏窗口到托盘（替代原关闭按钮）"""
        self.root.withdraw()

    def open_alarm_manager(self):
        """打开闹钟管理窗口(单例模式)"""
        if not hasattr(self, 'alarm_manager') or not self.alarm_manager.window.winfo_exists():
            self.alarm_manager = AlarmManagerWindow(self.root)
            # 重新应用主窗口的工具窗口样式,防止出现在任务栏
            self._reapply_toolwindow_style()
        else:
            self.alarm_manager.window.lift()
            self.alarm_manager.window.focus_force()
    
    def open_memo_manager(self):
        """打开备忘录管理窗口(单例模式)"""
        if not hasattr(self, 'memo_manager') or not self.memo_manager.window.winfo_exists():
            self.memo_manager = MemoManagerWindow(self.root)
            # 重新应用主窗口的工具窗口样式,防止出现在任务栏
            self._reapply_toolwindow_style()
        else:
            self.memo_manager.window.lift()
            self.memo_manager.window.focus_force()

    def open_message_center(self):
        """打开消息中心窗口(单例模式)"""
        if not hasattr(self, 'message_center') or not self.message_center.window.winfo_exists():
            self.message_center = MessageCenterWindow(self.root)
            # 重新应用主窗口的工具窗口样式,防止出现在任务栏
            self._reapply_toolwindow_style()
        else:
            self.message_center.window.lift()
            self.message_center.window.focus_force()

# 圆角矩形
def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kw):
    points = [
        x1+radius, y1,
        x2-radius, y1,
        x2, y1, x2, y1+radius,
        x2, y2-radius,
        x2, y2, x2-radius, y2,
        x1+radius, y2,
        x1, y2, x1, y2-radius,
        x1, y1+radius,
        x1, y1, x1+radius, y1
    ]
    return self.create_polygon(points, smooth=True, **kw)

tk.Canvas.create_rounded_rectangle = create_rounded_rectangle


if __name__ == "__main__":
    root = tk.Tk()
    root.title("灵动岛")
    app = DynamicIsland(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_window)
    root.mainloop()
