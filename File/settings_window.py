"""
灵动岛设置窗口 - PyQt6版本
提供美观、现代化的设置界面
"""
import sys
import json
import os
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, 
                             QCheckBox, QGroupBox, QScrollArea, QDialog,
                             QLineEdit, QTextEdit, QTimeEdit,
                             QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SettingsDialog(QDialog):
    """设置对话框"""
    
    # 定义信号，用于向主窗口传递设置变更
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("⚙️ 动态岛监控设置")
        self.setFixedSize(550, 750)
        self.setModal(True)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                height: 8px;
                background: #ecf0f1;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #bbb;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #2980b9;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTimeEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
                background-color: white;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("⚙️ 动态岛监控系统设置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(12)
        
        # 外观设置
        appearance_group = self.create_appearance_group()
        scroll_layout.addWidget(appearance_group)
        
        # 透明度设置
        opacity_group = self.create_opacity_group()
        scroll_layout.addWidget(opacity_group)
        
        # 刷新频率设置
        refresh_group = self.create_refresh_group()
        scroll_layout.addWidget(refresh_group)
        
        # 显示内容设置
        display_group = self.create_display_group()
        scroll_layout.addWidget(display_group)
        
        # 闹钟功能
        alarm_group = self.create_alarm_group()
        scroll_layout.addWidget(alarm_group)
        
        # 备忘录功能
        memo_group = self.create_memo_group()
        scroll_layout.addWidget(memo_group)
        
        # 关于信息
        about_group = self.create_about_group()
        scroll_layout.addWidget(about_group)
        
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        save_btn = QPushButton("💾 保存并关闭")
        save_btn.clicked.connect(self.save_and_close)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_appearance_group(self):
        """创建外观设置组"""
        group = QGroupBox("🎨 外观设置")
        layout = QVBoxLayout(group)
        
        # 当前主题显示
        theme_layout = QHBoxLayout()
        theme_label = QLabel("当前主题:")
        theme_label.setStyleSheet("font-size: 13px;")
        self.theme_value_label = QLabel("🌙 深色模式" if self.settings.get("is_dark", True) else "☀️ 浅色模式")
        self.theme_value_label.setStyleSheet("font-weight: bold; color: #3498db;")
        theme_layout.addWidget(theme_label)
        theme_layout.addStretch()
        theme_layout.addWidget(self.theme_value_label)
        layout.addLayout(theme_layout)
        
        # 切换主题按钮
        toggle_btn = QPushButton("🔄 切换主题")
        toggle_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(toggle_btn)
        
        return group
    
    def create_opacity_group(self):
        """创建透明度设置组"""
        group = QGroupBox("🔍 透明度设置")
        layout = QVBoxLayout(group)
        
        # 当前透明度显示
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("当前透明度:")
        opacity_label.setStyleSheet("font-size: 13px;")
        current_opacity = int(self.settings.get("opacity", 0.95) * 100)
        self.opacity_value_label = QLabel(f"{current_opacity}%")
        self.opacity_value_label.setStyleSheet("font-weight: bold; color: #9b59b6;")
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addStretch()
        opacity_layout.addWidget(self.opacity_value_label)
        layout.addLayout(opacity_layout)
        
        # 透明度滑块
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(current_opacity)
        self.opacity_slider.valueChanged.connect(self.on_opacity_change)
        layout.addWidget(self.opacity_slider)
        
        # 标签
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("透明"))
        label_layout.addStretch()
        label_layout.addWidget(QLabel("不透明"))
        layout.addLayout(label_layout)
        
        return group
    
    def create_refresh_group(self):
        """创建刷新频率设置组"""
        group = QGroupBox("⚡ 刷新频率")
        layout = QVBoxLayout(group)
        
        # 当前刷新率显示
        rate_layout = QHBoxLayout()
        rate_label = QLabel("当前刷新间隔:")
        rate_label.setStyleSheet("font-size: 13px;")
        current_interval = self.settings.get("refresh_interval", 1000)
        rate_text = {500: "0.5秒", 1000: "1秒", 2000: "2秒", 3000: "3秒"}.get(current_interval, "1秒")
        self.rate_value_label = QLabel(rate_text)
        self.rate_value_label.setStyleSheet("font-weight: bold; color: #e67e22;")
        rate_layout.addWidget(rate_label)
        rate_layout.addStretch()
        rate_layout.addWidget(self.rate_value_label)
        layout.addLayout(rate_layout)
        
        # 刷新率选择按钮
        btn_layout = QHBoxLayout()
        rates = [("0.5秒", 500), ("1秒", 1000), ("2秒", 2000), ("3秒", 3000)]
        for text, value in rates:
            btn = QPushButton(text)
            btn.setCheckable(True)
            if value == current_interval:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, v=value, t=text: self.change_refresh_rate(v, t))
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        return group
    
    def create_display_group(self):
        """创建显示内容设置组"""
        group = QGroupBox("📊 显示内容")
        layout = QVBoxLayout(group)
        
        # CPU使用率
        self.cpu_check = QCheckBox("CPU 使用率")
        self.cpu_check.setChecked(self.settings.get("show_cpu", True))
        layout.addWidget(self.cpu_check)
        
        # 内存使用率
        self.ram_check = QCheckBox("内存使用率")
        self.ram_check.setChecked(self.settings.get("show_ram", True))
        layout.addWidget(self.ram_check)
        
        # 电池状态
        self.bat_check = QCheckBox("电池状态")
        self.bat_check.setChecked(self.settings.get("show_battery", True))
        layout.addWidget(self.bat_check)
        
        return group
    
    def create_alarm_group(self):
        """创建闹钟功能组"""
        group = QGroupBox("⏰ 闹钟提醒")
        layout = QVBoxLayout(group)
        
        # 闹钟列表
        self.alarm_list = QListWidget()
        self.alarm_list.setMaximumHeight(100)
        self.refresh_alarm_list()
        layout.addWidget(self.alarm_list)
        
        # 按钮
        btn_layout = QHBoxLayout()
        add_alarm_btn = QPushButton("➕ 添加闹钟")
        add_alarm_btn.clicked.connect(self.add_alarm_dialog)
        delete_alarm_btn = QPushButton("🗑️ 删除选中")
        delete_alarm_btn.clicked.connect(self.delete_alarm)
        btn_layout.addWidget(add_alarm_btn)
        btn_layout.addWidget(delete_alarm_btn)
        layout.addLayout(btn_layout)
        
        return group
    
    def create_memo_group(self):
        """创建备忘录功能组"""
        group = QGroupBox("📝 备忘录")
        layout = QVBoxLayout(group)
        
        # 备忘录列表
        self.memo_list = QListWidget()
        self.memo_list.setMaximumHeight(120)
        self.refresh_memo_list()
        layout.addWidget(self.memo_list)
        
        # 按钮
        btn_layout = QHBoxLayout()
        add_memo_btn = QPushButton("➕ 添加备忘")
        add_memo_btn.clicked.connect(self.add_memo_dialog)
        delete_memo_btn = QPushButton("🗑️ 删除选中")
        delete_memo_btn.clicked.connect(self.delete_memo)
        btn_layout.addWidget(add_memo_btn)
        btn_layout.addWidget(delete_memo_btn)
        layout.addLayout(btn_layout)
        
        return group
    
    def create_about_group(self):
        """创建关于信息组"""
        group = QGroupBox("ℹ️ 关于")
        layout = QVBoxLayout(group)
        
        info_text = """动态岛监控系统 v1.0
实时监控系统资源状态

功能特性：
• 圆角窗口设计
• 深色/浅色主题切换
• 透明度调节
• 自定义刷新频率
• 灵活的内容显示
• 闹钟提醒功能
• 备忘录管理"""
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #777; font-size: 12px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        return group
    
    def load_settings(self):
        """加载设置"""
        pass
    
    def toggle_theme(self):
        """切换主题"""
        is_dark = not self.settings.get("is_dark", True)
        self.settings["is_dark"] = is_dark
        self.theme_value_label.setText("🌙 深色模式" if is_dark else "☀️ 浅色模式")
    
    def on_opacity_change(self, value):
        """透明度变化"""
        self.opacity_value_label.setText(f"{value}%")
        self.settings["opacity"] = value / 100.0
    
    def change_refresh_rate(self, interval_ms, text):
        """更改刷新频率"""
        self.settings["refresh_interval"] = interval_ms
        self.rate_value_label.setText(text)
    
    def refresh_alarm_list(self):
        """刷新闹钟列表"""
        self.alarm_list.clear()
        alarms = self.settings.get("alarms", [])
        for alarm in alarms:
            time_str = alarm.get("time", "")
            label = alarm.get("label", "闹钟")
            enabled = "✅" if alarm.get("enabled", True) else "❌"
            item = QListWidgetItem(f"{enabled} {time_str} - {label}")
            self.alarm_list.addItem(item)
    
    def refresh_memo_list(self):
        """刷新备忘录列表"""
        self.memo_list.clear()
        memos = self.settings.get("memos", [])
        for memo in memos:
            title = memo.get("title", "无标题")
            content = memo.get("content", "")[:30]
            item = QListWidgetItem(f"📌 {title}: {content}...")
            self.memo_list.addItem(item)
    
    def add_alarm_dialog(self):
        """添加闹钟对话框"""
        dialog = AlarmDialog(self)
        if dialog.exec():
            alarm_data = dialog.get_alarm_data()
            if alarm_data:
                alarms = self.settings.get("alarms", [])
                alarms.append(alarm_data)
                self.settings["alarms"] = alarms
                self.refresh_alarm_list()
    
    def delete_alarm(self):
        """删除闹钟"""
        current_row = self.alarm_list.currentRow()
        if current_row >= 0:
            alarms = self.settings.get("alarms", [])
            alarms.pop(current_row)
            self.settings["alarms"] = alarms
            self.alarm_list.takeItem(current_row)
    
    def add_memo_dialog(self):
        """添加备忘录对话框"""
        dialog = MemoDialog(self)
        if dialog.exec():
            memo_data = dialog.get_memo_data()
            if memo_data:
                memos = self.settings.get("memos", [])
                memos.append(memo_data)
                self.settings["memos"] = memos
                self.refresh_memo_list()
    
    def delete_memo(self):
        """删除备忘录"""
        current_row = self.memo_list.currentRow()
        if current_row >= 0:
            memos = self.settings.get("memos", [])
            memos.pop(current_row)
            self.settings["memos"] = memos
            self.memo_list.takeItem(current_row)
    
    def save_and_close(self):
        """保存设置并关闭"""
        # 更新显示内容设置
        self.settings["show_cpu"] = self.cpu_check.isChecked()
        self.settings["show_ram"] = self.ram_check.isChecked()
        self.settings["show_battery"] = self.bat_check.isChecked()
        
        # 发射信号通知主窗口
        self.settings_changed.emit(self.settings)
        self.accept()


class AlarmDialog(QDialog):
    """闹钟添加对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加闹钟")
        self.setFixedSize(350, 200)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 时间选择
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("闹钟时间:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(self.time_edit.currentTime())
        time_layout.addWidget(self.time_edit)
        layout.addLayout(time_layout)
        
        # 标签输入
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("闹钟标签:"))
        self.label_edit = QLineEdit("闹钟")
        label_layout.addWidget(self.label_edit)
        layout.addLayout(label_layout)
        
        # 启用状态
        self.enable_check = QCheckBox("启用闹钟")
        self.enable_check.setChecked(True)
        layout.addWidget(self.enable_check)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("✓ 保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("✖ 取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_alarm_data(self):
        """获取闹钟数据"""
        return {
            "time": self.time_edit.time().toString("HH:mm"),
            "label": self.label_edit.text() or "闹钟",
            "enabled": self.enable_check.isChecked()
        }


class MemoDialog(QDialog):
    """备忘录添加对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加备忘录")
        self.setFixedSize(400, 300)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 标题输入
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_edit = QLineEdit()
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        
        # 内容输入
        layout.addWidget(QLabel("内容:"))
        self.content_edit = QTextEdit()
        self.content_edit.setMaximumHeight(150)
        layout.addWidget(self.content_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("✓ 保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("✖ 取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_memo_data(self):
        """获取备忘录数据"""
        return {
            "title": self.title_edit.text() or "无标题",
            "content": self.content_edit.toPlainText(),
            "created_at": time.strftime("%Y-%m-%d %H:%M")
        }


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    dialog.show()
    sys.exit(app.exec())
