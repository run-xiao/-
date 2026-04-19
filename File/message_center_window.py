"""
消息中心窗口模块
显示所有系统通知和历史记录
"""
import tkinter as tk
from tkinter import ttk

# 导入通用工具函数
from manager_utils import load_messages, save_messages


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
