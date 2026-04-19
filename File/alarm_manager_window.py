"""
闹钟管理窗口模块
提供独立的闹钟管理界面
"""
import tkinter as tk
from tkinter import ttk
import os

# 导入通用工具函数
from manager_utils import load_alarms, save_alarms, scan_sound_files, play_custom_audio


class AlarmManagerWindow:
    """独立的闹钟管理窗口"""
    
    def __init__(self, parent):
        self.parent = parent
        # 从独立JSON文件加载闹钟数据
        self.alarms = load_alarms()
        
        # 如果窗口已存在,则将其置于顶层并返回
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        
        self.window = tk.Toplevel(parent)
        self.window.title("⏰ 闹钟管理")
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
        header_frame = tk.Frame(main_frame, bg="#e74c3c", height=65)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="⏰ 闹钟管理", 
                              font=("Microsoft YaHei", 16, "bold"), 
                              fg="white", bg="#e74c3c")
        title_label.pack(expand=True)
        
        # 统计信息
        stats_frame = tk.Frame(main_frame, bg="white", height=45)
        stats_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        stats_frame.pack_propagate(False)
        
        active_count = sum(1 for a in self.alarms if a.get("enabled", True))
        total_count = len(self.alarms)
        
        self.stats_label = tk.Label(stats_frame, 
                              text=f"📊 总计: {total_count} 个  |  ✅ 已启用: {active_count} 个  |  ❌ 已禁用: {total_count - active_count} 个",
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
        
        # 保存canvas引用以便后续更新
        self.content_canvas = content_canvas
        
        content_canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        # 闹钟列表容器
        self.list_container = tk.Frame(scrollable_frame, bg="#f5f5f5")
        self.list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # 强制更新布局，确保scrollable_frame大小正确
        self.window.update_idletasks()
        
        # 刷新列表
        self._refresh_list()
        
        # 再次更新，确保内容显示
        self.window.update_idletasks()
        
        # 按钮区域 - 垂直布局
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1", pady=12)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 第一行：刷新按钮（单独一行）
        refresh_btn = tk.Button(btn_frame, text="🔄 刷新列表", 
                               command=self._refresh_from_file,
                               font=("Microsoft YaHei", 10, "bold"),
                               bg="#3498db", fg="white",
                               activebackground="#2980b9", activeforeground="white",
                               relief=tk.FLAT, cursor="hand2",
                               padx=20, pady=4)
        refresh_btn.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        # 第二行：添加、删除和关闭按钮
        action_frame = tk.Frame(btn_frame, bg="#ecf0f1")
        action_frame.pack(fill=tk.X, padx=15)
        
        add_btn = tk.Button(action_frame, text="➕ 添加闹钟", 
                           command=self._add_alarm_dialog,
                           font=("Microsoft YaHei", 10, "bold"),
                           bg="#2ecc71", fg="white",
                           activebackground="#27ae60", activeforeground="white",
                           relief=tk.FLAT, cursor="hand2",
                           padx=20, pady=6)
        add_btn.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        
        delete_btn = tk.Button(action_frame, text="🗑️ 删除", 
                              command=self._delete_alarm,
                              font=("Microsoft YaHei", 10, "bold"),
                              bg="#e74c3c", fg="white",
                              activebackground="#c0392b", activeforeground="white",
                              relief=tk.FLAT, cursor="hand2",
                              padx=20, pady=8)
        delete_btn.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        
        close_btn = tk.Button(action_frame, text="✖ 关闭", 
                             command=self._on_close,
                             font=("Microsoft YaHei", 10, "bold"),
                             bg="#95a5a6", fg="white",
                             activebackground="#7f8c8d", activeforeground="white",
                             relief=tk.FLAT, cursor="hand2",
                             padx=20, pady=8)
        close_btn.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
    
    def _apply_style(self):
        """应用样式"""
        self.window.configure(bg="#f5f5f5")
    
    def _update_stats(self):
        """更新统计信息"""
        if hasattr(self, 'stats_label'):
            active_count = sum(1 for a in self.alarms if a.get("enabled", True))
            total_count = len(self.alarms)
            self.stats_label.config(
                text=f"📊 总计: {total_count} 个  |  ✅ 已启用: {active_count} 个  |  ❌ 已禁用: {total_count - active_count} 个"
            )
    
    def _play_test_sound(self, sound_type):
        """播放测试声音"""
        try:
            import winsound
            
            # 根据声音类型播放不同的提示音
            if sound_type == "default":
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif sound_type == "chime":
                winsound.MessageBeep(winsound.MB_OK)
            elif sound_type == "soft":
                winsound.MessageBeep(winsound.MB_ICONINFORMATION)
            elif sound_type == "alert":
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif sound_type == "none":
                pass  # 无声音
            else:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception as e:
            print(f"播放测试声音失败: {e}")
    
    def _play_custom_sound(self, mp3_path):
        """播放自定义MP3音频文件（委托给模块级函数）"""
        play_custom_audio(mp3_path)
    
    def _refresh_from_file(self):
        """从JSON文件重新加载数据"""
        self.alarms = load_alarms()
        print(f"已从文件重新加载 {len(self.alarms)} 个闹钟")
        self._refresh_list()
        
        # 通知父对象（灵动岛）更新状态显示
        if hasattr(self.parent, '_update_status_indicators'):
            self.parent._update_status_indicators()
    
    def _save_to_file(self):
        """保存数据到JSON文件"""
        if save_alarms(self.alarms):
            print(f"已保存 {len(self.alarms)} 个闹钟到文件")
            
            # 通知父对象（灵动岛）更新状态显示
            if hasattr(self.parent, '_update_status_indicators'):
                self.parent._update_status_indicators()
        else:
            print("保存闹钟失败！")
    
    def _refresh_list(self):
        """刷新闹钟列表"""
        # 清空现有列表
        for widget in self.list_container.winfo_children():
            widget.destroy()
        
        # 调试信息
        print(f"闹钟列表刷新: 共 {len(self.alarms)} 个闹钟")
        if self.alarms:
            print(f"闹钟数据: {self.alarms}")
        
        if not self.alarms:
            empty_label = tk.Label(self.list_container, 
                                  text="📭 暂无闹钟\n点击'添加闹钟'创建新闹钟",
                                  font=("Segoe UI", 11), fg="#999", bg="#f5f5f5",
                                  justify=tk.CENTER)
            empty_label.pack(pady=40)
            print("显示空列表提示")
        else:
            # 创建闹钟卡片
            for index, alarm in enumerate(self.alarms):
                try:
                    card = self._create_alarm_card(index, alarm)
                    card.pack(fill=tk.X, pady=3)
                    print(f"闹钟 #{index} 已显示: {alarm.get('label', '未命名')} - {alarm.get('time', '未知时间')}")
                except Exception as e:
                    # 如果某个闹钟数据有问题，跳过并打印错误
                    print(f"闹钟 #{index} 显示错误: {e}")
                    print(f"闹钟数据: {alarm}")
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
    
    def _create_alarm_card(self, index, alarm):
        """创建闹钟卡片 - 大字体标题，小字体显示时间和状态"""
        card_frame = tk.Frame(self.list_container, bg="white", relief=tk.RAISED, bd=1)
        # 移除pack_propagate和固定高度，让内容自然决定高度
        
        # 左侧状态图标
        status_frame = tk.Frame(card_frame, bg="#ecf0f1", width=65)
        status_frame.pack(side=tk.LEFT, fill=tk.Y)
        status_frame.pack_propagate(False)
        
        enabled = alarm.get("enabled", True)
        status_icon = "✅" if enabled else "❌"
        status_color = "#2ecc71" if enabled else "#95a5a6"
        
        status_label = tk.Label(status_frame, text=status_icon, 
                               font=("Segoe UI", 22), bg=status_color, fg="white")
        status_label.pack(expand=True)
        
        # 中间内容区域
        content_frame = tk.Frame(card_frame, bg="white")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # 大字体标题（闹钟标签）
        label_text = alarm.get("label", "未命名闹钟")
        title_label = tk.Label(content_frame, 
                              text=label_text,
                              font=("Microsoft YaHei", 14, "bold"), 
                              fg="#2c3e50", bg="white",
                              anchor="w")
        title_label.pack(anchor="w")
        
        # 小字体显示时间和启用状态
        time_text = alarm.get("time", "00:00")
        status_text = "已启用" if enabled else "已禁用"
        detail_text = f"⏰ {time_text}  |  {status_text}"
        
        detail_label = tk.Label(content_frame, 
                               text=detail_text,
                               font=("Segoe UI", 10), 
                               fg="#7f8c8d", bg="white",
                               anchor="w")
        detail_label.pack(anchor="w", pady=(5, 0))
        
        # 右侧操作按钮区域
        action_frame = tk.Frame(card_frame, bg="white", width=120)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y)
        action_frame.pack_propagate(False)
        
        # 切换状态按钮
        toggle_btn = tk.Button(action_frame, 
                              text="🔔" if enabled else "🔕",
                              command=lambda i=index: self._toggle_alarm(i),
                              font=("Segoe UI", 13),
                              bg="#f39c12" if enabled else "#95a5a6", fg="white",
                              activebackground="#e67e22" if enabled else "#7f8c8d",
                              activeforeground="white",
                              relief=tk.FLAT, cursor="hand2",
                              width=4, height=1)
        toggle_btn.pack(expand=False, side=tk.TOP,padx=5)
        
        # 删除按钮
        delete_btn = tk.Button(action_frame, text="    🗑️", 
                              command=lambda i=index: self._confirm_delete_alarm(i),
                              font=("Segoe UI", 13),
                              bg="#e74c3c", fg="white",
                              activebackground="#c0392b", activeforeground="white",
                              relief=tk.FLAT, cursor="hand2",
                              width=4, height=1)
        delete_btn.pack(expand=False, side=tk.TOP,padx=5)
        
        # 为整个卡片绑定双击编辑功能
        card_frame.bind("<Double-Button-1>", lambda e, i=index: self._edit_alarm_dialog(i))
        status_frame.bind("<Double-Button-1>", lambda e, i=index: self._edit_alarm_dialog(i))
        content_frame.bind("<Double-Button-1>", lambda e, i=index: self._edit_alarm_dialog(i))
        title_label.bind("<Double-Button-1>", lambda e, i=index: self._edit_alarm_dialog(i))
        detail_label.bind("<Double-Button-1>", lambda e, i=index: self._edit_alarm_dialog(i))
        
        return card_frame
    
    def _add_alarm_dialog(self):
        """添加闹钟对话框"""
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
