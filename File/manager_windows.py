"""
管理器窗口模块 - 入口点
提供AlarmService类和统一的导入接口
"""
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
from datetime import datetime, timedelta
import os

# 导入通用工具函数
from manager_utils import (
    load_alarms, save_alarms, 
    load_memos, save_memos,
    load_messages, save_messages, add_message,
    play_custom_audio, stop_all_sounds,
    scan_sound_files
)

class AlarmService:
    """闹钟服务类，负责闹钟检查、触发和通知显示"""
    
    def __init__(self, parent_window):
        """
        初始化闹钟服务
        :param parent_window: 父窗口引用（灵动岛主窗口）
        """
        self.parent = parent_window
        self.alarms = load_alarms()
        self._last_check_time = ""  # 记录上次检查的时间，避免重复触发
    
    def check_and_trigger_alarms(self):
        """检查并触发到时的闹钟"""
        from datetime import datetime
        
        # 获取当前时间（格式：HH:MM）
        current_time = datetime.now().strftime("%H:%M")
        
        # 避免同一分钟内重复检查
        if current_time == self._last_check_time:
            return
        
        self._last_check_time = current_time
        
        # 重新加载最新数据，确保与持久化存储同步
        self.alarms = load_alarms()
        
        # 初始化计数器
        triggered_count = 0
        triggered_snooze_alarms = []  # 收集已触发的稍后提醒闹钟
        
        for alarm in self.alarms:
            if alarm.get("enabled", True) and alarm.get("time") == current_time:
                # 检查是否已经触发过（避免一分钟内多次触发）
                last_triggered = alarm.get("last_triggered", "")
                if last_triggered != current_time:
                    self.trigger_alarm(alarm)
                    # 标记为已触发
                    alarm["last_triggered"] = current_time
                    triggered_count += 1
                    
                    # 如果是稍后提醒闹钟，加入清理列表
                    if alarm.get("is_snoozing", False):
                        triggered_snooze_alarms.append(alarm.copy())
        
        # 如果有闹钟触发，保存状态
        if triggered_count > 0:
            save_alarms(self.alarms)
            print(f"✅ 触发了 {triggered_count} 个闹钟")

            if triggered_snooze_alarms:
                self._cleanup_triggered_snooze_alarms(triggered_snooze_alarms, triggered_count)
    
    def _cleanup_triggered_snooze_alarms(self, snooze_alarms, triggered_count):
        """清理已触发的稍后提醒闹钟"""
        alarms = load_alarms()
        original_count = len(alarms)
        
        # 过滤掉已触发的稍后提醒闹钟
        alarms_to_keep = []
        for alarm in alarms:
            should_keep = True
            for snooze in snooze_alarms:
                if (alarm.get("is_snooze", False) and 
                    alarm.get("time") == snooze.get("time") and 
                    alarm.get("label") == snooze.get("label")):
                    should_keep = False
                    break
            if should_keep:
                alarms_to_keep.append(alarm)
        
        # 如果有删除，保存更新后的列表
        if len(alarms_to_keep) < original_count:
            save_alarms(alarms_to_keep)
            print(f"🧹 已清理 {original_count - len(alarms_to_keep)} 个已触发的稍后提醒闹钟")
            print(f"✅ 触发了 {triggered_count} 个闹钟")
    
    def trigger_alarm(self, alarm):
        """触发单个闹钟"""
        label = alarm.get("label", "闹钟")
        time_str = alarm.get("time", "")
        
        print(f"⏰ 闹钟触发: {label} ({time_str})")
        
        # 检查是否是稍后提醒状态
        is_snoozing = alarm.get("is_snoozing", False)
        
        # 记录到消息中心
        add_message(
            message_type="alarm_triggered",
            title=f"⏰ {label}",
            content=f"闹钟已触发，时间：{time_str}",
            extra_data={"alarm_label": label, "alarm_time": time_str, "is_snoozing": is_snoozing}
        )
        
        # 播放自定义提示音（支持MP3）- 传递整个alarm对象让方法内部判断
        self.play_alarm_sound(None, alarm)
        
        # 显示可关闭的闹钟通知窗口
        self.show_closable_notification(label, time_str, alarm)
    
    def play_alarm_sound(self, sound_type, alarm=None):
        """播放闹钟声音（支持系统提示音和文件夹音频）"""
        try:
            # 兼容旧格式：如果alarm中有sound_type字段，使用新格式
            if alarm and "sound_type" in alarm:
                actual_sound_type = alarm["sound_type"]  # "system" 或 "file"
                sound_value = alarm.get("sound", "default")
                
                if actual_sound_type == "file":
                    # 播放文件夹中的音频文件
                    if os.path.exists(sound_value):
                        play_custom_audio(sound_value)
                    else:
                        print(f"⚠️ 音频文件不存在: {sound_value}，使用默认提示音")
                        import winsound
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
                elif actual_sound_type == "system":
                    # 播放系统提示音
                    self._play_system_sound(sound_value)
            else:
                # 兼容旧格式：直接使用sound_type作为系统提示音类型
                self._play_system_sound(sound_type)
        except Exception as e:
            print(f"播放闹钟声音失败: {e}")
    
    def _play_system_sound(self, sound_type):
        """播放系统提示音"""
        import winsound
        if sound_type == "default":
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif sound_type == "none":
            pass  # 无声音
        else:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
    
    def show_closable_notification(self, title, time_str, alarm):
        """显示可关闭的闹钟通知窗口（支持持续响铃和自动稍后提醒）"""
        from ctypes import wintypes
        import ctypes
        
        user32 = ctypes.windll.user32
        LWA_ALPHA = 0x00000002
        
        # 创建通知窗口
        notif_window = tk.Toplevel(self.parent)
        notif_window.overrideredirect(True)
        notif_window.attributes("-topmost", True)
        
        # 设置窗口样式为工具窗口（不在任务栏显示）
        try:
            hwnd = user32.GetParent(notif_window.winfo_id())
            style = user32.GetWindowLongW(hwnd, -20)
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_LAYERED = 0x00080000
            style |= WS_EX_TOOLWINDOW | WS_EX_LAYERED
            user32.SetWindowLongW(hwnd, -20, style)
            user32.SetLayeredWindowAttributes(hwnd, 0, int(0.95 * 255), LWA_ALPHA)
        except:
            pass
        
        # 计算右下角位置
        screen_w = notif_window.winfo_screenwidth()
        screen_h = notif_window.winfo_screenheight()
        notif_width = 350
        notif_height = 180  # 增加高度以显示倒计时
        x = screen_w - notif_width - 20
        y = screen_h - notif_height - 60
        
        notif_window.geometry(f"{notif_width}x{notif_height}+{x}+{y}")
        
        # 主容器
        main_frame = tk.Frame(notif_window, bg="#fff3cd", relief=tk.RAISED, bd=2)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题栏
        header_frame = tk.Frame(main_frame, bg="#f39c12", height=35)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="⏰ 闹钟提醒", 
                font=("Microsoft YaHei", 11, "bold"), 
                fg="white", bg="#f39c12").pack(side=tk.LEFT, padx=10, pady=5)
        
        # 内容区域
        content_frame = tk.Frame(main_frame, bg="#fff3cd")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        tk.Label(content_frame, text=title, 
                font=("Microsoft YaHei", 12, "bold"), 
                fg="#856404", bg="#fff3cd",
                anchor="w").pack(anchor="w")
        
        tk.Label(content_frame, text=f"时间：{time_str}", 
                font=("Segoe UI", 10), 
                fg="#856404", bg="#fff3cd",
                anchor="w").pack(anchor="w", pady=(3, 0))
        
        # 倒计时标签
        countdown_label = tk.Label(content_frame, text="", 
                                  font=("Segoe UI", 9), 
                                  fg="#e74c3c", bg="#fff3cd",
                                  anchor="w")
        countdown_label.pack(anchor="w", pady=(5, 0))
        
        # 按钮区域
        btn_frame = tk.Frame(main_frame, bg="#fff3cd")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 跟踪用户是否已响应
        user_responded = [False]
        
        # 获取重复次数（默认为0）
        snooze_count = alarm.get("snooze_count", 0)
        max_snooze = 3  # 最多重复3次
        
        def stop_alarm():
            """停止闹钟"""
            user_responded[0] = True
            
            # 停止当前所有声音
            stop_all_sounds()
            
            # 关闭当前通知窗口
            try:
                if notif_window.winfo_exists():
                    notif_window.destroy()
            except:
                pass
            
            # 计算5分钟后的时间
            current_time = datetime.now()
            snooze_time = current_time + timedelta(minutes=5)
            alarm["snooze_time"] = snooze_time.strftime("%H:%M")
            
            # 重置重复计数
            if "snooze_count" in alarm:
                del alarm["snooze_count"]
            save_alarms(self.alarms)
        
        stop_btn = tk.Button(btn_frame, text="✓ 停止闹钟", command=stop_alarm,
                            font=("Microsoft YaHei", 10, "bold"),
                            bg="#28a745", fg="white",
                            activebackground="#218838", activeforeground="white",
                            relief=tk.FLAT, cursor="hand2",
                            padx=15, pady=5)
        stop_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # 只有未达到最大重复次数时才显示稍后提醒按钮
        if snooze_count < max_snooze:
            snooze_btn = tk.Button(btn_frame, text=f"⏱️ 稍后提醒 ({snooze_count}/{max_snooze})", 
                                  command=lambda: self.snooze_alarm(alarm, notif_window),
                                  font=("Microsoft YaHei", 10, "bold"),
                                  bg="#17a2b8", fg="white",
                                  activebackground="#138496", activeforeground="white",
                                  relief=tk.FLAT, cursor="hand2",
                                  padx=15, pady=5)
            snooze_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # 持续响铃逻辑：循环播放音频
        remaining_time = [60]  # 剩余秒数（1分钟）
        last_play_time = [0]   # 上次播放时间（秒）
        play_interval = 4      # 播放间隔（秒），短音频建议3-5秒
        
        def update_countdown():
            """更新倒计时并持续循环响铃"""
            if not user_responded[0] and notif_window.winfo_exists():
                remaining_time[0] -= 1
                
                # 每隔指定间隔播放一次声音（循环播放）
                time_elapsed = 60 - remaining_time[0]
                if time_elapsed - last_play_time[0] >= play_interval:
                    self.play_alarm_sound(None, alarm)
                    last_play_time[0] = time_elapsed
                
                # 更新倒计时显示
                if remaining_time[0] > 0:
                    countdown_label.config(text=f"将在 {remaining_time[0]} 秒后自动稍后提醒...")
                    notif_window.after(1000, update_countdown)
                else:
                    # 时间到，自动稍后提醒
                    countdown_label.config(text="正在自动稍后提醒...")
                    notif_window.after(500, lambda: auto_snooze())
        
        def auto_snooze():
            """自动稍后提醒"""
            if not user_responded[0] and notif_window.winfo_exists():
                print(f"⚠️ 用户未响应，自动稍后提醒 (第 {snooze_count + 1}/{max_snooze} 次)")
                
                # 停止当前所有声音
                stop_all_sounds()
                
                self.snooze_alarm(alarm, notif_window, auto_trigger=True)
        
        # 窗口关闭时停止声音
        def on_window_close():
            """窗口关闭事件处理"""
            stop_all_sounds()
        
        # 绑定窗口销毁事件
        notif_window.protocol("WM_DELETE_WINDOW", lambda: [on_window_close(), notif_window.destroy()])
        
        # 启动倒计时
        update_countdown()
    
    def snooze_alarm(self, alarm, notif_window, auto_trigger=False):
        """稍后提醒功能 - 5分钟后再次提醒（直接修改原闹钟时间）"""
        from datetime import datetime, timedelta
        
        # 获取当前重复次数
        snooze_count = alarm.get("snooze_count", 0) + 1  # 增加重复计数
        max_snooze = 3
        
        # 检查是否已达到最大重复次数
        if snooze_count > max_snooze:
            print(f"⚠️ 已达到最大重复次数 ({max_snooze}次)，不再创建稍后提醒")
            
            # 停止所有声音
            stop_all_sounds()
            
            # 关闭当前通知窗口
            try:
                if notif_window.winfo_exists():
                    notif_window.destroy()
            except:
                pass
            
            # 重置稍后提醒状态
            self._reset_snooze_state(alarm)
            return
        
        # 停止当前所有声音
        stop_all_sounds()
        
        # 关闭当前通知窗口
        try:
            if notif_window.winfo_exists():
                notif_window.destroy()
        except:
            pass
        
        # 计算5分钟后的时间
        current_time = datetime.now()
        snooze_time = current_time + timedelta(minutes=5)
        snooze_time_str = snooze_time.strftime("%H:%M")
        
        label = alarm.get("label", "闹钟")
        
        print(f"⏱️ 闹钟 [{label}] 已设置为 {snooze_time_str} 再次提醒 (第 {snooze_count}/{max_snooze} 次)")
        
        # 直接修改原闹钟的时间和稍后提醒状态
        alarm["time"] = snooze_time_str
        alarm["snooze_count"] = snooze_count
        alarm["is_snoozing"] = True  # 标记为正在稍后提醒状态
        alarm["original_time"] = alarm.get("original_time", alarm.get("time"))  # 记录原始时间（如果还没有记录）
        
        # 保存更新后的闹钟列表
        save_alarms(self.alarms)
        
        # 记录到消息中心
        trigger_type = "自动" if auto_trigger else "手动"
        add_message(
            message_type="snooze_created",
            title=f"⏱️ {label}",
            content=f"{trigger_type}稍后提醒已设置，将在 {snooze_time_str} 再次触发 (第 {snooze_count}/{max_snooze} 次)",
            extra_data={
                "alarm_label": label,
                "snooze_time": snooze_time_str,
                "snooze_count": snooze_count
            }
        )
    
    def _reset_snooze_state(self, alarm):
        """重置闹钟的稍后提醒状态"""
        # 恢复原始时间（如果有记录）
        if "original_time" in alarm:
            alarm["time"] = alarm["original_time"]
            del alarm["original_time"]
        
        # 清除稍后提醒相关参数
        if "snooze_count" in alarm:
            del alarm["snooze_count"]
        if "is_snoozing" in alarm:
            del alarm["is_snoozing"]
        
        # 保存更新
        save_alarms(self.alarms)
        print(f"🔄 已重置闹钟 [{alarm.get('label', '闹钟')}] 的稍后提醒状态")

    def _add_alarm_dialog(self):
        """添加闹钟对话框"""
        dialog = tk.Toplevel(self.window)
        dialog.title("添加闹钟")
        dialog.geometry("300x200")

        label = tk.Label(dialog, text="时间:")
        label.pack(pady=10)

        time_var = tk.StringVar()
        time_entry = tk.Entry(dialog, textvariable=time_var)
        time_entry.pack(pady=10)

        def add_alarm():
            time_str = time_var.get()
            try:
                time_obj = datetime.strptime(time_str, "%H:%M")
                self.alarms.append(time_obj)
                self._update_alarm_list()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的24小时制时间（例如：13:45）")

        add_button = tk.Button(dialog, text="添加", command=add_alarm)
        add_button.pack(pady=10)

    def _edit_alarm_dialog(self, index):
        """编辑闹钟对话框"""
        dialog = tk.Toplevel(self.window)
        dialog.title("编辑闹钟")
        dialog.geometry("300x200")

        label = tk.Label(dialog, text="时间:")
        label.pack(pady=10)

        time_var = tk.StringVar(value=self.alarms[index].strftime("%H:%M"))
        time_entry = tk.Entry(dialog, textvariable=time_var)
        time_entry.pack(pady=10)

        def edit_alarm():
            time_str = time_var.get()
            try:
                time_obj = datetime.strptime(time_str, "%H:%M")
                self.alarms[index] = time_obj
                self._update_alarm_list()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的24小时制时间（例如：13:45）")

        edit_button = tk.Button(dialog, text="保存", command=edit_alarm)
        edit_button.pack(pady=10)

    def _update_alarm_list(self):
        """更新闹钟列表"""
        for widget in self.alarm_list_frame.winfo_children():
            widget.destroy()

        for index, alarm in enumerate(self.alarms):
            card_frame = tk.Frame(self.alarm_list_frame)
            card_frame.pack(pady=5, fill=tk.X)

            time_label = tk.Label(card_frame, text=alarm.strftime("%H:%M"))
            time_label.pack(side=tk.LEFT, padx=10)

            detail_label = tk.Label(card_frame, text="编辑")
            detail_label.pack(side=tk.RIGHT, padx=10)
            detail_label.bind("<Double-Button-1>", lambda e, i=index: self._edit_alarm_dialog(i))
        
        return card_frame
    
    def _add_alarm_dialog(self):
        """添加闹钟对话框"""
        dialog = tk.Toplevel(self.window)
        dialog.title("添加闹钟")
        dialog.geometry("300x200")


    def _add_alarm_dialog(self):
        """添加闹钟对话框"""
        dialog = tk.Toplevel(self.window)
        dialog.title("添加闹钟")
        dialog.geometry("300x200")


        label = tk.Label(dialog, text="时间:")
        label.pack(pady=10)

        time_var = tk.StringVar()
        time_entry = tk.Entry(dialog, textvariable=time_var)
        time_entry.pack(pady=10)

        def add_alarm():
            time_str = time_var.get()
            try:
                time_obj = datetime.strptime(time_str, "%H:%M")
                self.alarms.append(time_obj)
                self._update_alarm_list()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的24小时制时间（例如：13:45）")

        add_button = tk.Button(dialog, text="添加", command=add_alarm)
        add_button.pack(pady=10)

    def _edit_alarm_dialog(self, index):
        """编辑闹钟对话框"""
        dialog = tk.Toplevel(self.window)
        dialog.title("添加闹钟")
        dialog.geometry("400x420")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        # 居中显示
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w - 400) // 2
        y = (screen_h - 420) // 2
        dialog.geometry(f"400x420+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        header = tk.Frame(main_frame, bg="#2ecc71", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="➕ 添加新闹钟", 
                font=("Microsoft YaHei", 13, "bold"), 
                fg="white", bg="#2ecc71").pack(expand=True)
        
        # 内容
        content = tk.Frame(main_frame, bg="#f5f5f5", padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # 标签输入
        label_frame = tk.Frame(content, bg="#f5f5f5")
        label_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(label_frame, text="闹钟标签:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        label_entry = tk.Entry(label_frame, font=("Segoe UI", 11), width=30,
                              bg="white", fg="#333", relief=tk.FLAT,
                              highlightthickness=1, highlightbackground="#ddd")
        label_entry.pack(fill=tk.X, ipady=5)
        label_entry.insert(0, "新闹钟")
        label_entry.select_range(0, tk.END)
        label_entry.focus()
        
        # 时间选择
        time_frame = tk.Frame(content, bg="#f5f5f5")
        time_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(time_frame, text="闹钟时间:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        time_input_frame = tk.Frame(time_frame, bg="#f5f5f5")
        time_input_frame.pack(fill=tk.X)
        
        hour_var = tk.StringVar(value="00")
        minute_var = tk.StringVar(value="00")
        
        hour_spin = tk.Spinbox(time_input_frame, from_=0, to=23, width=5,
                             textvariable=hour_var,
                             font=("Segoe UI", 12, "bold"),
                             format="%02.0f",
                             bg="white", fg="#333",
                             buttonbackground="#ecf0f1",
                             relief=tk.FLAT,
                             highlightthickness=1,
                             highlightbackground="#ddd")
        hour_spin.pack(side=tk.LEFT, padx=2)
        
        tk.Label(time_input_frame, text=":", font=("Segoe UI", 14, "bold"), 
                fg="#333", bg="#f5f5f5").pack(side=tk.LEFT, padx=3)
        
        minute_spin = tk.Spinbox(time_input_frame, from_=0, to=59, width=5, 
                                textvariable=minute_var,
                                font=("Segoe UI", 12, "bold"),
                                format="%02.0f",
                                bg="white", fg="#333",
                                buttonbackground="#ecf0f1",
                                relief=tk.FLAT,
                                highlightthickness=1,
                                highlightbackground="#ddd")
        minute_spin.pack(side=tk.LEFT, padx=2)
        
        # 启用状态
        enable_frame = tk.Frame(content, bg="#f5f5f5")
        enable_frame.pack(fill=tk.X, pady=5)
        
        enable_var = tk.BooleanVar(value=True)
        enable_check = tk.Checkbutton(enable_frame, text="启用此闹钟", variable=enable_var,
                                     font=("Segoe UI", 10), bg="#f5f5f5",
                                     selectcolor="white", fg="#333",
                                     activebackground="#f5f5f5")
        enable_check.pack(anchor=tk.W)
        
        # 声音选择（动态加载文件夹中的音频文件）
        sound_frame = tk.Frame(content, bg="#f5f5f5")
        sound_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(sound_frame, text="提示音:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        # 扫描音频文件夹
        available_sounds = scan_sound_files()
        
        # 构建声音选项（只保留默认提示音和无声音）
        sound_options = {
            "🔔 默认提示音": {"type": "system", "value": "default"},
            "🔇 无声音": {"type": "system", "value": "none"}
        }
        
        # 添加文件夹中的音频文件
        if available_sounds:
            for sound in available_sounds:
                display_name = f"🎵 {sound['name']}"

                sound_options[display_name] = {
                    "type": "file",
                    "value": sound["path"],
                    "name": sound["name"]
                }
        
        # 创建下拉框
        sound_var = tk.StringVar(value="🔔 默认提示音")
        sound_combo = ttk.Combobox(sound_frame, textvariable=sound_var,
                                  values=list(sound_options.keys()),
                                  state="readonly", font=("Segoe UI", 10),
                                  width=28)
        sound_combo.pack(fill=tk.X, ipady=3)
        sound_combo.set("🔔 默认提示音")
        
        # 试听按钮
        def test_sound():
            selected_label = sound_var.get()
            
            if selected_label not in sound_options:
                print(f"⚠️ 错误：'{selected_label}' 不在声音选项中")
                return
            
            sound_config = sound_options[selected_label]
            
            if sound_config["type"] == "system":
                self._play_test_sound(sound_config["value"])
            elif sound_config["type"] == "file":
                audio_path = sound_config["value"]
                if os.path.exists(audio_path):
                    play_custom_audio(audio_path)
                else:
                    print(f"⚠️ 音频文件不存在: {audio_path}")
        
        test_btn = tk.Button(sound_frame, text="🔊 试听", command=test_sound,
                            font=("Segoe UI", 9),
                            bg="#3498db", fg="white",
                            activebackground="#2980b9", activeforeground="white",
                            relief=tk.FLAT, cursor="hand2",
                            padx=10, pady=2)
        test_btn.pack(anchor=tk.E, pady=(5, 0))
        
        # 按钮框架
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_alarm():
            hour = int(hour_var.get())
            minute = int(minute_var.get())
            time_str = f"{hour:02d}:{minute:02d}"
            label = label_entry.get().strip() or "闹钟"
            
            # 获取选中的声音配置
            selected_label = sound_var.get()
            if selected_label not in sound_options:
                print(f"⚠️ 错误：'{selected_label}' 不在声音选项中")
                return
            
            sound_config = sound_options[selected_label]
            
            # 创建新闹钟
            new_alarm = {
                "time": time_str,
                "label": label,
                "enabled": enable_var.get(),
                "sound_type": sound_config["type"],
                "sound": sound_config["value"]
            }
            
            # 如果是自定义文件，保存路径
            if sound_config["type"] == "file":
                new_alarm["sound_path"] = sound_config["value"]
            
            self.alarms.append(new_alarm)
            self._save_to_file()
            self._refresh_list()
            dialog.destroy()
        
        tk.Button(btn_frame, text="✓ 保存", command=save_alarm,
                 font=("Segoe UI", 10, "bold"),
                 bg="#3498db", fg="white",
                 activebackground="#2980b9", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        tk.Button(btn_frame, text="✖ 取消", command=dialog.destroy,
                 font=("Segoe UI", 10, "bold"),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def _edit_alarm_dialog(self, index):
        """编辑闹钟对话框"""
        if index < 0 or index >= len(self.alarms):
            return
        
        alarm = self.alarms[index]
        
        dialog = tk.Toplevel(self.window)
        dialog.title("编辑闹钟")
        dialog.geometry("400x420")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        # 居中显示
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w - 400) // 2
        y = (screen_h - 420) // 2
        dialog.geometry(f"400x420+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        header = tk.Frame(main_frame, bg="#3498db", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="✏️ 编辑闹钟", 
                font=("Microsoft YaHei", 13, "bold"), 
                fg="white", bg="#3498db").pack(expand=True)
        
        # 内容
        content = tk.Frame(main_frame, bg="#f5f5f5", padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # 标签输入
        label_frame = tk.Frame(content, bg="#f5f5f5")
        label_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(label_frame, text="闹钟标签:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        label_entry = tk.Entry(label_frame, font=("Segoe UI", 11), width=30,
                              bg="white", fg="#333", relief=tk.FLAT,
                              highlightthickness=1, highlightbackground="#ddd")
        label_entry.pack(fill=tk.X, ipady=5)
        label_entry.insert(0, alarm.get("label", "闹钟"))
        label_entry.select_range(0, tk.END)
        label_entry.focus()
        
        # 时间选择
        time_frame = tk.Frame(content, bg="#f5f5f5")
        time_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(time_frame, text="闹钟时间:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        time_input_frame = tk.Frame(time_frame, bg="#f5f5f5")
        time_input_frame.pack(fill=tk.X)
        
        # 解析现有时间
        time_parts = alarm.get("time", "00:00").split(":")
        hour_var = tk.StringVar(value=time_parts[0])
        minute_var = tk.StringVar(value=time_parts[1])
        
        hour_spin = tk.Spinbox(time_input_frame, from_=0, to=23, width=5, 
                             textvariable=hour_var,
                             font=("Segoe UI", 12, "bold"),
                             format="%02.0f",
                             bg="white", fg="#333",
                             buttonbackground="#ecf0f1",
                             relief=tk.FLAT,
                             highlightthickness=1,
                             highlightbackground="#ddd")
        hour_spin.pack(side=tk.LEFT, padx=2)
        
        minute_spin = tk.Spinbox(time_input_frame, from_=0, to=59, width=5, 
                                textvariable=minute_var,
                                font=("Segoe UI", 12, "bold"),
                                format="%02.0f",
                                bg="white", fg="#333",
                                buttonbackground="#ecf0f1",
                                relief=tk.FLAT,
                                highlightthickness=1,
                                highlightbackground="#ddd")
        minute_spin.pack(side=tk.LEFT, padx=2)
        
        # 启用状态
        enable_frame = tk.Frame(content, bg="#f5f5f5")
        enable_frame.pack(fill=tk.X, pady=5)
        
        enable_var = tk.BooleanVar(value=alarm.get("enabled", True))
        enable_check = tk.Checkbutton(enable_frame, text="启用此闹钟", variable=enable_var,
                                     font=("Segoe UI", 10), bg="#f5f5f5",
                                     selectcolor="white", fg="#333",
                                     activebackground="#f5f5f5")
        enable_check.pack(anchor=tk.W)
        
        # 声音选择（动态加载文件夹中的音频文件）
        sound_frame = tk.Frame(content, bg="#f5f5f5")
        sound_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(sound_frame, text="提示音:", font=("Segoe UI", 10, "bold"),
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        # 扫描音频文件夹
        available_sounds = scan_sound_files()
        
        # 构建声音选项（只保留默认提示音和无声音）
        sound_options = {
            "🔔 默认提示音": {"type": "system", "value": "default"},
            "🔇 无声音": {"type": "system", "value": "none"}
        }
        
        # 添加文件夹中的音频文件
        if available_sounds:
            for sound in available_sounds:
                display_name = f"🎵 {sound['name']}"
                sound_options[display_name] = {
                    "type": "file",
                    "value": sound["path"],
                    "name": sound["name"]
                }
        
        # 确定当前选中的声音
        current_sound_type = alarm.get("sound_type", "system")
        current_sound_value = alarm.get("sound", "default")
        
        # 查找对应的显示标签
        selected_label = "🔔 默认提示音"  # 默认值
        for label, config in sound_options.items():
            if config["type"] == current_sound_type and config["value"] == current_sound_value:
                selected_label = label
                break
        
        # 创建下拉框
        sound_var = tk.StringVar(value=selected_label)
        sound_combo = ttk.Combobox(sound_frame, textvariable=sound_var,
                                  values=list(sound_options.keys()),
                                  state="readonly", font=("Segoe UI", 10),
                                  width=28)
        sound_combo.pack(fill=tk.X, ipady=3)
        
        # 试听按钮
        def test_sound():
            selected_label = sound_var.get()
            
            if selected_label not in sound_options:
                print(f"⚠️ 错误：'{selected_label}' 不在声音选项中")
                return
            
            sound_config = sound_options[selected_label]
            
            if sound_config["type"] == "system":
                self._play_test_sound(sound_config["value"])
            elif sound_config["type"] == "file":
                audio_path = sound_config["value"]
                if os.path.exists(audio_path):
                    play_custom_audio(audio_path)
                else:
                    print(f"⚠️ 音频文件不存在: {audio_path}")
        
        test_btn = tk.Button(sound_frame, text="🔊 试听", command=test_sound,
                            font=("Segoe UI", 9),
                            bg="#3498db", fg="white",
                            activebackground="#2980b9", activeforeground="white",
                            relief=tk.FLAT, cursor="hand2",
                            padx=10, pady=2)
        test_btn.pack(anchor=tk.E, pady=(5, 0))
        
        # 按钮框架
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_alarm():
            hour = int(hour_var.get())
            minute = int(minute_var.get())
            time_str = f"{hour:02d}:{minute:02d}"
            label = label_entry.get().strip() or "闹钟"
            
            # 获取选中的声音配置
            selected_label = sound_var.get()
            if selected_label not in sound_options:
                print(f"⚠️ 错误：'{selected_label}' 不在声音选项中")
                return
            
            sound_config = sound_options[selected_label]
            
            # 更新闹钟
            self.alarms[index] = {
                "time": time_str,
                "label": label,
                "enabled": enable_var.get(),
                "sound_type": sound_config["type"],
                "sound": sound_config["value"]
            }
            
            # 如果是自定义文件，保存路径
            if sound_config["type"] == "file":
                self.alarms[index]["sound_path"] = sound_config["value"]
            
            self._save_to_file()
            self._refresh_list()
            dialog.destroy()
        
        tk.Button(btn_frame, text="✓ 保存", command=save_alarm,
                 font=("Segoe UI", 10, "bold"),
                 bg="#3498db", fg="white",
                 activebackground="#2980b9", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        tk.Button(btn_frame, text="✖ 取消", command=dialog.destroy,
                 font=("Segoe UI", 10, "bold"),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def _toggle_alarm(self, index):
        """切换闹钟启用状态"""
        if 0 <= index < len(self.alarms):
            self.alarms[index]["enabled"] = not self.alarms[index].get("enabled", True)
            self._save_to_file()
            self._refresh_list()
    
    def _confirm_delete_alarm(self, index):
        """确认删除闹钟"""
        if 0 <= index < len(self.alarms):
            self.alarms.pop(index)
            self._save_to_file()
            self._refresh_list()
    
    def _delete_alarm(self):
        """删除选中的闹钟(通过对话框选择)"""
        if not self.alarms:
            return
        
        # 创建选择对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("删除闹钟")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        # 居中显示
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w - 400) // 2
        y = (screen_h - 300) // 2
        dialog.geometry(f"400x300+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        header = tk.Frame(main_frame, bg="#e74c3c", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🗑️ 选择要删除的闹钟", 
                font=("Microsoft YaHei", 13, "bold"), 
                fg="white", bg="#e74c3c").pack(expand=True)
        
        # 列表
        list_frame = tk.Frame(main_frame, bg="#f5f5f5", padx=15, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        listbox = tk.Listbox(list_frame, font=("Segoe UI", 10),
                            bg="white", fg="#333",
                            selectbackground="#e74c3c",
                            selectforeground="white",
                            relief=tk.FLAT,
                            highlightthickness=1,
                            highlightbackground="#ddd")
        listbox.pack(fill=tk.BOTH, expand=True)
        
        for i, alarm in enumerate(self.alarms):
            label = alarm.get("label", "未命名")
            time_str = alarm.get("time", "00:00")
            enabled = "✅" if alarm.get("enabled", True) else "❌"
            listbox.insert(tk.END, f"{i+1}. {enabled} {label} - {time_str}")
        
        # 按钮
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def confirm_delete():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                self.alarms.pop(index)
                self._save_to_file()
                self._refresh_list()
                dialog.destroy()
        
        tk.Button(btn_frame, text="✓ 删除", command=confirm_delete,
                 font=("Segoe UI", 10, "bold"),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        tk.Button(btn_frame, text="✖ 取消", command=dialog.destroy,
                 font=("Segoe UI", 10, "bold"),
                 bg="#95a5a6", fg="white",
                 activebackground="#7f8c8d", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    def _on_close(self):
        """关闭窗口"""
        if hasattr(self, 'window'):
            # 通知父对象清除此窗口的引用
            if hasattr(self, 'parent'):
                # 检查是闹钟管理器还是备忘录管理器
                if hasattr(self.parent, 'alarm_manager') and self.parent.alarm_manager is self:
                    delattr(self.parent, 'alarm_manager')
                elif hasattr(self.parent, 'memo_manager') and self.parent.memo_manager is self:
                    delattr(self.parent, 'memo_manager')
            
            self.window.destroy()


class MessageCenterWindow:
    """消息中心窗口 - 显示所有系统通知和历史记录"""
    
    def __init__(self, parent):
        self.parent = parent
        self.messages = load_messages()
        
        # 如果窗口已存在，则将其置于顶层并返回
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        
        self.window = tk.Toplevel(parent)
        self.window.title("📬 消息中心")
        self.window.geometry("600x500")
        self.window.resizable(False, False)
        
        # 居中显示
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w - 600) // 2
        y = (screen_h - 500) // 2
        self.window.geometry(f"600x500+{x}+{y}")
        
        # 设置窗口始终在最前
        self.window.attributes("-topmost", True)
        
        # 应用样式
        self._apply_style()
        
        # 窗口关闭时清理
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # 构建界面
        self._build_ui()
        
        # 刷新消息列表
        self._refresh_list()
    
    def _apply_style(self):
        """应用自定义样式"""
        style = ttk.Style()
        style.configure("Message.TFrame", background="#f8f9fa")
        style.configure("Header.TFrame", background="#3498db")
        style.configure("MessageCard.TFrame", background="white", relief=tk.RAISED, bd=1)
    
    def _build_ui(self):
        """构建用户界面"""
        # 主框架
        main_frame = tk.Frame(self.window, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题栏
        header_frame = tk.Frame(main_frame, bg="#3498db", height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="📬 消息中心", 
                font=("Microsoft YaHei", 14, "bold"), 
                fg="white", bg="#3498db").pack(side=tk.LEFT, padx=15, pady=10)
        
        # 统计信息
        unread_count = sum(1 for msg in self.messages if not msg.get("read", False))
        stats_label = tk.Label(header_frame, text=f"未读: {unread_count} | 总计: {len(self.messages)}", 
                              font=("Segoe UI", 10), 
                              fg="white", bg="#3498db")
        stats_label.pack(side=tk.RIGHT, padx=15, pady=10)
        self.stats_label = stats_label
        
        # 内容区域（带滚动条）
        content_frame = tk.Frame(main_frame, bg="#f5f5f5")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建Canvas和Scrollbar
        canvas = tk.Canvas(content_frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
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
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 消息列表容器
        self.list_container = tk.Frame(scrollable_frame, bg="#f5f5f5")
        self.list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 按钮区域
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Button(btn_frame, text="🗑️ 清空所有消息", 
                 command=self._clear_all_messages,
                 font=("Microsoft YaHei", 10, "bold"),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
        
        tk.Button(btn_frame, text="✓ 标记全部已读", 
                 command=self._mark_all_read,
                 font=("Microsoft YaHei", 10, "bold"),
                 bg="#2ecc71", fg="white",
                 activebackground="#27ae60", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
        
        tk.Button(btn_frame, text="✖ 关闭", 
                 command=self._on_close,
                 font=("Microsoft YaHei", 10, "bold"),
                 bg="#95a5a6", fg="white",
                 activebackground="#7f8c8d", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
    
    def _refresh_list(self):
        """刷新消息列表"""
        # 清空现有内容
        for widget in self.list_container.winfo_children():
            widget.destroy()
        
        # 重新加载消息
        self.messages = load_messages()
        
        # 更新统计信息
        unread_count = sum(1 for msg in self.messages if not msg.get("read", False))
        self.stats_label.config(text=f"未读: {unread_count} | 总计: {len(self.messages)}")
        
        # 如果没有消息，显示提示
        if not self.messages:
            empty_label = tk.Label(self.list_container, 
                                  text="📭 暂无消息\n\n所有系统通知将显示在这里", 
                                  font=("Microsoft YaHei", 12), 
                                  fg="#95a5a6", bg="#f5f5f5",
                                  justify=tk.CENTER)
            empty_label.pack(pady=50)
            return
        
        # 按时间倒序显示（最新的在前）
        for msg in reversed(self.messages):
            self._create_message_card(msg)
    
    def _create_message_card(self, msg):
        """创建单条消息卡片"""
        card_frame = tk.Frame(self.list_container, bg="white", relief=tk.RAISED, bd=1)
        card_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # 根据消息类型设置图标和颜色
        msg_type = msg.get("type", "")
        if msg_type == "alarm_triggered":
            icon = "⏰"
            type_color = "#f39c12"
        elif msg_type == "snooze_created":
            icon = "⏱️"
            type_color = "#3498db"
        elif msg_type == "memo_added":
            icon = "📝"
            type_color = "#2ecc71"
        else:
            icon = "📢"
            type_color = "#95a5a6"
        
        # 顶部信息栏
        info_frame = tk.Frame(card_frame, bg=type_color, height=30)
        info_frame.pack(fill=tk.X)
        info_frame.pack_propagate(False)
        
        # 未读标记
        is_read = msg.get("read", False)
        read_indicator = "● " if not is_read else "○ "
        
        tk.Label(info_frame, text=f"{icon} {msg.get('title', '通知')}", 
                font=("Microsoft YaHei", 10, "bold"), 
                fg="white", bg=type_color,
                anchor="w").pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        tk.Label(info_frame, text=msg.get("timestamp", ""), 
                font=("Segoe UI", 8), 
                fg="white", bg=type_color,
                anchor="e").pack(side=tk.RIGHT, padx=10, fill=tk.Y)
        
        # 内容区域
        content_frame = tk.Frame(card_frame, bg="white")
        content_frame.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(content_frame, text=f"{read_indicator}{msg.get('content', '')}", 
                font=("Microsoft YaHei", 9), 
                fg="#2c3e50" if not is_read else "#7f8c8d", bg="white",
                anchor="w", wraplength=520, justify=tk.LEFT).pack(anchor="w")
        
        # 底部操作区
        action_frame = tk.Frame(card_frame, bg="#ecf0f1", height=35)
        action_frame.pack(fill=tk.X)
        action_frame.pack_propagate(False)
        
        # 标记已读/未读按钮
        if not is_read:
            tk.Button(action_frame, text="✓ 标记已读", 
                     command=lambda m=msg: self._mark_as_read(m["id"]),
                     font=("Segoe UI", 8),
                     bg="#2ecc71", fg="white",
                     activebackground="#27ae60", activeforeground="white",
                     relief=tk.FLAT, cursor="hand2",
                     padx=10, pady=3).pack(side=tk.LEFT, padx=5, pady=3)
        
        tk.Button(action_frame, text="🗑️ 删除", 
                 command=lambda mid=msg["id"]: self._delete_message(mid),
                 font=("Segoe UI", 8),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=10, pady=3).pack(side=tk.RIGHT, padx=5, pady=3)
    
    def _mark_as_read(self, message_id):
        """标记单条消息为已读"""
        messages = load_messages()
        for msg in messages:
            if msg["id"] == message_id:
                msg["read"] = True
                break
        
        save_messages(messages)
        self._refresh_list()
    
    def _mark_all_read(self):
        """标记所有消息为已读"""
        messages = load_messages()
        for msg in messages:
            msg["read"] = True
        
        save_messages(messages)
        self._refresh_list()
    
    def _delete_message(self, message_id):
        """删除单条消息"""
        messages = load_messages()
        messages = [msg for msg in messages if msg["id"] != message_id]
        
        # 重新分配ID
        for i, msg in enumerate(messages):
            msg["id"] = i + 1
        
        save_messages(messages)
        self._refresh_list()
    
    def _clear_all_messages(self):
        """清空所有消息"""
        # 确认对话框
        confirm_dialog = tk.Toplevel(self.window)
        confirm_dialog.title("确认清空")
        confirm_dialog.geometry("300x150")
        confirm_dialog.transient(self.window)
        confirm_dialog.grab_set()
        
        # 居中显示
        x = self.window.winfo_rootx() + (self.window.winfo_width() - 300) // 2
        y = self.window.winfo_rooty() + (self.window.winfo_height() - 150) // 2
        confirm_dialog.geometry(f"+{x}+{y}")
        
        tk.Label(confirm_dialog, text="确定要清空所有消息吗？\n此操作不可恢复！", 
                font=("Microsoft YaHei", 10), 
                justify=tk.CENTER).pack(pady=20)
        
        btn_frame = tk.Frame(confirm_dialog)
        btn_frame.pack(pady=10)
        
        def confirm():
            save_messages([])
            self._refresh_list()
            confirm_dialog.destroy()
        
        tk.Button(btn_frame, text="✓ 确定", command=confirm,
                 font=("Segoe UI", 9, "bold"),
                 bg="#e74c3c", fg="white",
                 width=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="✖ 取消", command=confirm_dialog.destroy,
                 font=("Segoe UI", 9, "bold"),
                 bg="#95a5a6", fg="white",
                 width=8).pack(side=tk.LEFT, padx=5)
    
    def _on_close(self):
        """关闭窗口"""
        if hasattr(self, 'window'):
            # 通知父对象清除此窗口的引用
            if hasattr(self.parent, 'message_center') and self.parent.message_center is self:
                delattr(self.parent, 'message_center')
            
            self.window.destroy()


class MemoManagerWindow:
    """独立的备忘录管理窗口"""
    
    def __init__(self, parent):
        self.parent = parent
        # 从独立JSON文件加载备忘录数据
        self.memos = load_memos()
        
        # 如果窗口已存在,则将其置于顶层并返回
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        
        self.window = tk.Toplevel(parent)
        self.window.title("📝 备忘录管理")
        self.window.geometry("550x600")
        self.window.resizable(False, False)
        
        # 居中显示
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w - 550) // 2
        y = (screen_h - 600) // 2
        self.window.geometry(f"550x600+{x}+{y}")
        
        # 设置窗口始终在最前
        self.window.attributes("-topmost", True)
        
        # 应用样式
        self._apply_style()
        
        # 窗口关闭时清理
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # 主容器
        main_frame = tk.Frame(self.window, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题区域
        header_frame = tk.Frame(main_frame, bg="#3498db", height=65)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📝 备忘录管理", 
                              font=("Microsoft YaHei", 16, "bold"), 
                              fg="white", bg="#3498db")
        title_label.pack(expand=True)
        
        # 统计信息
        stats_frame = tk.Frame(main_frame, bg="white", height=45)
        stats_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        stats_frame.pack_propagate(False)
        
        total_count = len(self.memos)
        
        self.stats_label = tk.Label(stats_frame, 
                              text=f"📊 总计: {total_count} 条备忘录",
                              font=("Segoe UI", 9), fg="#666", bg="white")
        self.stats_label.pack(expand=True)
        
        # 内容区域(带滚动)
        content_canvas = tk.Canvas(main_frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=content_canvas.yview,
                                bg="#ecf0f1", troughcolor="#ddd")
        scrollable_frame = tk.Frame(content_canvas, bg="#f5f5f5")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: content_canvas.configure(scrollregion=content_canvas.bbox("all"))
        )
        
        content_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        content_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            content_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        content_canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        content_canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        # 备忘录列表容器
        self.list_container = tk.Frame(scrollable_frame, bg="#f5f5f5")
        self.list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # 强制更新布局，确保scrollable_frame大小正确
        self.window.update_idletasks()
        
        # 刷新列表
        self._refresh_list()
        
        # 再次更新，确保内容显示
        self.window.update_idletasks()
        
        # 按钮区域
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=12)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        add_btn = tk.Button(btn_frame, text="➕ 添加备忘录", 
                           command=self._add_memo_dialog,
                           font=("Microsoft YaHei", 10, "bold"),
                           bg="#2ecc71", fg="white",
                           activebackground="#27ae60", activeforeground="white",
                           relief=tk.FLAT, cursor="hand2",
                           padx=20, pady=8)
        add_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        refresh_btn = tk.Button(btn_frame, text="🔄 刷新", 
                               command=self._refresh_from_file,
                               font=("Segoe UI", 10, "bold"),
                               bg="#3498db", fg="white",
                               activebackground="#2980b9", activeforeground="white",
                               relief=tk.FLAT, cursor="hand2",
                               padx=20, pady=8)
        refresh_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        delete_btn = tk.Button(btn_frame, text="删除", 
                              command=self._delete_memo,
                              font=("Microsoft YaHei", 10, "bold"),
                              bg="#e74c3c", fg="white",
                              activebackground="#c0392b", activeforeground="white",
                              relief=tk.FLAT, cursor="hand2",
                              padx=20, pady=8)
        delete_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        close_btn = tk.Button(btn_frame, text="✖ 关闭", 
                             command=self._on_close,
                             font=("Microsoft YaHei", 10, "bold"),
                             bg="#95a5a6", fg="white",
                             activebackground="#7f8c8d", activeforeground="white",
                             relief=tk.FLAT, cursor="hand2",
                             padx=20, pady=8)
        close_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    def _apply_style(self):
        """应用样式"""
        self.window.configure(bg="#f5f5f5")
    
    def _update_stats(self):
        """更新统计信息"""
        if hasattr(self, 'stats_label'):
            total_count = len(self.memos)
            self.stats_label.config(
                text=f"📊 总计: {total_count} 条备忘录"
            )
    
    def _refresh_from_file(self):
        """从JSON文件重新加载数据"""
        self.memos = load_memos()
        print(f"已从文件重新加载 {len(self.memos)} 条备忘录")
        self._refresh_list()
        self._update_stats()
        
        # 通知父对象（灵动岛）更新状态显示
        if hasattr(self.parent, '_update_status_indicators'):
            self.parent._update_status_indicators()
    
    def _save_to_file(self):
        """保存数据到JSON文件"""
        if save_memos(self.memos):
            print(f"已保存 {len(self.memos)} 条备忘录到文件")
            self._update_stats()
            
            # 通知父对象（灵动岛）更新状态显示
            if hasattr(self.parent, '_update_status_indicators'):
                self.parent._update_status_indicators()
        else:
            print("保存备忘录失败！")
    
    def _refresh_list(self):
        """刷新备忘录列表"""
        # 清空现有列表
        for widget in self.list_container.winfo_children():
            widget.destroy()
        
        # 调试信息
        print(f"备忘录列表刷新: 共 {len(self.memos)} 条备忘录")
        if self.memos:
            print(f"备忘录数据: {self.memos}")
        
        if not self.memos:
            empty_label = tk.Label(self.list_container, 
                                  text="📭 暂无备忘录\n点击'添加备忘录'创建新备忘",
                                  font=("Segoe UI", 11), fg="#999", bg="#f5f5f5",
                                  justify=tk.CENTER)
            empty_label.pack(pady=40)
            print("显示空列表提示")
        else:
            # 创建备忘录卡片
            for index, memo in enumerate(self.memos):
                try:
                    card = self._create_memo_card(index, memo)
                    card.pack(fill=tk.X, pady=3)
                    print(f"备忘录 #{index} 已显示: {memo.get('title', '无标题')}")
                except Exception as e:
                    # 如果某个备忘录数据有问题，跳过并打印错误
                    print(f"备忘录 #{index} 显示错误: {e}")
                    print(f"备忘录数据: {memo}")
                    import traceback
                    traceback.print_exc()
        
        # 强制更新布局
        self.window.update_idletasks()
        
        # 更新Canvas的scrollregion
        if hasattr(self, 'content_canvas'):
            self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))
            print(f"Canvas scrollregion已更新: {self.content_canvas.bbox('all')}")
        
        # 更新统计信息
        self._update_stats()
    
    def _create_memo_card(self, index, memo):
        """创建备忘录卡片 - 大字体标题，小字体显示约3行内容"""
        card_frame = tk.Frame(self.list_container, bg="white", relief=tk.RAISED, bd=1)
        # 不固定高度，让内容自动决定高度
        
        # 左侧序号
        num_frame = tk.Frame(card_frame, bg="#ecf0f1", width=55)
        num_frame.pack(side=tk.LEFT, fill=tk.Y)
        num_frame.pack_propagate(False)
        
        num_label = tk.Label(num_frame, text=f"#{index + 1}", 
                            font=("Segoe UI", 16, "bold"), bg="#3498db", fg="white")
        num_label.pack(expand=True)
        
        # 中间内容区域
        content_frame = tk.Frame(card_frame, bg="white")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        # 大字体标题
        title_text = memo.get("title", "无标题")
        title_label = tk.Label(content_frame, 
                              text=title_text,
                              font=("Microsoft YaHei", 14, "bold"), 
                              fg="#2c3e50", bg="white",
                              anchor="w", wraplength=350)
        title_label.pack(anchor="w")
        
        # 小字体显示内容，每行超过10个字符自动换行
        content_text = memo.get("content", "")
        if len(content_text) > 120:
            content_text = content_text[:120] + "..."
        
        # 使用Label并设置wraplength实现每行约10个字符自动换行
        # 10号字体，每个中文字符约10-12像素，10个字符约100-120像素
        content_label = tk.Label(content_frame, 
                                text=content_text,
                                font=("Segoe UI", 10), 
                                fg="#7f8c8d", bg="white",
                                anchor="nw", justify=tk.LEFT,
                                wraplength=110)  # 设置每行约10个字符的宽度
        content_label.pack(anchor="w", pady=(6, 0), fill=tk.X)
        
        # 右侧操作按钮区域
        action_frame = tk.Frame(card_frame, bg="white", width=65)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y)
        action_frame.pack_propagate(False)
        
        # 编辑按钮
        edit_btn = tk.Button(action_frame, text="✏️", 
                            command=lambda i=index: self._edit_memo_dialog(i),
                            font=("Segoe UI", 13),
                            bg="#3498db", fg="white",
                            activebackground="#2980b9", activeforeground="white",
                            relief=tk.FLAT, cursor="hand2",
                            width=4, height=1)
        edit_btn.pack(expand=False, side=tk.TOP, padx=5, pady=(5, 2))
        
        # 删除按钮
        delete_btn = tk.Button(action_frame, text="    🗑️", 
                              command=lambda i=index: self._confirm_delete_memo(i),
                              font=("Segoe UI", 13),
                              bg="#e74c3c", fg="white",
                              activebackground="#c0392b", activeforeground="white",
                              relief=tk.FLAT, cursor="hand2",
                              width=4, height=1)
        delete_btn.pack(expand=False, side=tk.TOP, padx=5, pady=(2, 5))
        
        return card_frame
    
    def _add_memo_dialog(self):
        """添加备忘录对话框"""
        dialog = tk.Toplevel(self.window)
        dialog.title("添加备忘录")
        dialog.geometry("450x400")  # 增加高度以确保按钮可见
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        # 居中显示
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w - 450) // 2
        y = (screen_h - 400) // 2
        dialog.geometry(f"450x400+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        header = tk.Frame(main_frame, bg="#2ecc71", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="➕ 添加新备忘录", 
                font=("Microsoft YaHei", 13, "bold"), 
                fg="white", bg="#2ecc71").pack(expand=True)
        
        # 内容
        content = tk.Frame(main_frame, bg="#f5f5f5", padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # 标题输入
        title_frame = tk.Frame(content, bg="#f5f5f5")
        title_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(title_frame, text="标题:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        title_entry = tk.Entry(title_frame, font=("Segoe UI", 11), width=35,
                              bg="white", fg="#333", relief=tk.FLAT,
                              highlightthickness=1, highlightbackground="#ddd")
        title_entry.pack(fill=tk.X, ipady=5)
        title_entry.insert(0, "新备忘录")
        title_entry.select_range(0, tk.END)
        title_entry.focus()
        
        # 内容输入
        content_frame = tk.Frame(content, bg="#f5f5f5")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        tk.Label(content_frame, text="内容:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        content_text = tk.Text(content_frame, font=("Segoe UI", 10), width=40, height=8,
                              bg="white", fg="#333", relief=tk.FLAT,
                              highlightthickness=1, highlightbackground="#ddd",
                              wrap=tk.WORD)
        content_text.pack(fill=tk.BOTH, expand=True, ipady=5)
        
        # 按钮
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_memo():
            title = title_entry.get().strip() or "无标题"
            memo_content = content_text.get("1.0", tk.END).strip()
            
            self.memos.append({
                "title": title,
                "content": memo_content
            })
            self._save_to_file()
            self._refresh_list()
            self._update_stats()
            dialog.destroy()
        
        tk.Button(btn_frame, text="✓ 保存", command=save_memo,
                 font=("Segoe UI", 10, "bold"),
                 bg="#2ecc71", fg="white",
                 activebackground="#27ae60", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        tk.Button(btn_frame, text="✖ 取消", command=dialog.destroy,
                 font=("Segoe UI", 10, "bold"),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    def _edit_memo_dialog(self, index):
        """编辑备忘录对话框"""
        if index < 0 or index >= len(self.memos):
            return
        
        memo = self.memos[index]
        
        dialog = tk.Toplevel(self.window)
        dialog.title("编辑备忘录")
        dialog.geometry("450x400")  # 增加高度以确保按钮可见
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        # 居中显示
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w - 450) // 2
        y = (screen_h - 400) // 2
        dialog.geometry(f"450x400+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        header = tk.Frame(main_frame, bg="#3498db", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="✏️ 编辑备忘录", 
                font=("Microsoft YaHei", 13, "bold"), 
                fg="white", bg="#3498db").pack(expand=True)
        
        # 内容
        content = tk.Frame(main_frame, bg="#f5f5f5", padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # 标题输入
        title_frame = tk.Frame(content, bg="#f5f5f5")
        title_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(title_frame, text="标题:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        title_entry = tk.Entry(title_frame, font=("Segoe UI", 11), width=35,
                              bg="white", fg="#333", relief=tk.FLAT,
                              highlightthickness=1, highlightbackground="#ddd")
        title_entry.pack(fill=tk.X, ipady=5)
        title_entry.insert(0, memo.get("title", "无标题"))
        title_entry.select_range(0, tk.END)
        title_entry.focus()
        
        # 内容输入
        content_frame = tk.Frame(content, bg="#f5f5f5")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        tk.Label(content_frame, text="内容:", font=("Segoe UI", 10, "bold"), 
                fg="#333", bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 3))
        
        content_text = tk.Text(content_frame, font=("Segoe UI", 10), width=40, height=8,
                              bg="white", fg="#333", relief=tk.FLAT,
                              highlightthickness=1, highlightbackground="#ddd",
                              wrap=tk.WORD)
        content_text.pack(fill=tk.BOTH, expand=True, ipady=5)
        content_text.insert("1.0", memo.get("content", ""))
        
        # 按钮
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_memo():
            title = title_entry.get().strip() or "无标题"
            memo_content = content_text.get("1.0", tk.END).strip()
            
            self.memos[index] = {
                "title": title,
                "content": memo_content
            }
            self._save_to_file()
            self._refresh_list()
            self._update_stats()
            dialog.destroy()
        
        tk.Button(btn_frame, text="✓ 保存", command=save_memo,
                 font=("Segoe UI", 10, "bold"),
                 bg="#3498db", fg="white",
                 activebackground="#2980b9", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        tk.Button(btn_frame, text="✖ 取消", command=dialog.destroy,
                 font=("Segoe UI", 10, "bold"),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    def _confirm_delete_memo(self, index):
        """确认删除备忘录"""
        if 0 <= index < len(self.memos):
            self.memos.pop(index)
            self._save_to_file()
            self._refresh_list()
            self._update_stats()
    
    def _delete_memo(self):
        """删除选中的备忘录(通过对话框选择)"""
        if not self.memos:
            return
        
        # 创建选择对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("删除备忘录")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        # 居中显示
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w - 400) // 2
        y = (screen_h - 300) // 2
        dialog.geometry(f"400x300+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        header = tk.Frame(main_frame, bg="#e74c3c", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🗑️ 选择要删除的备忘录", 
                font=("Microsoft YaHei", 13, "bold"), 
                fg="white", bg="#e74c3c").pack(expand=True)
        
        # 列表
        list_frame = tk.Frame(main_frame, bg="#f5f5f5", padx=15, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        listbox = tk.Listbox(list_frame, font=("Segoe UI", 10),
                            bg="white", fg="#333",
                            selectbackground="#e74c3c",
                            selectforeground="white",
                            relief=tk.FLAT,
                            highlightthickness=1,
                            highlightbackground="#ddd")
        listbox.pack(fill=tk.BOTH, expand=True)
        
        for i, memo in enumerate(self.memos):
            title = memo.get("title", "无标题")
            listbox.insert(tk.END, f"{i+1}. {title}")
        
        # 按钮
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def confirm_delete():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                self.memos.pop(index)
                self._save_to_file()
                self._refresh_list()
                dialog.destroy()
        
        tk.Button(btn_frame, text="✓ 删除", command=confirm_delete,
                 font=("Segoe UI", 10, "bold"),
                 bg="#e74c3c", fg="white",
                 activebackground="#c0392b", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        tk.Button(btn_frame, text="✖ 取消", command=dialog.destroy,
                 font=("Segoe UI", 10, "bold"),
                 bg="#95a5a6", fg="white",
                 activebackground="#7f8c8d", activeforeground="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=25, pady=6).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    def _on_close(self):
        """关闭窗口"""
        if hasattr(self, 'window'):
            # 通知父对象清除此窗口的引用
            if hasattr(self, 'parent'):
                # 检查是闹钟管理器还是备忘录管理器
                if hasattr(self.parent, 'alarm_manager') and self.parent.alarm_manager is self:
                    delattr(self.parent, 'alarm_manager')
                elif hasattr(self.parent, 'memo_manager') and self.parent.memo_manager is self:
                    delattr(self.parent, 'memo_manager')
            
            self.window.destroy()
