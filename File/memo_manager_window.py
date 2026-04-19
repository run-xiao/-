"""
备忘录管理窗口模块
提供独立的备忘录管理界面
"""
import tkinter as tk

# 导入通用工具函数
from manager_utils import load_memos, save_memos


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
