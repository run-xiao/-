"""
管理器窗口通用工具模块
提供数据加载/保存、音频播放等共享功能
"""
import json
import os
from tkinter import messagebox

# 数据文件路径（与程序同目录）
ALARM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data\\alarms.json")
MEMO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data\\memos.json")
MESSAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data\\messages.json")


def load_alarms():
    """加载闹钟数据"""
    try:
        if os.path.exists(ALARM_FILE):
            with open(ALARM_FILE, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                # 确保返回的是列表，而不是字典或其他类型
                if isinstance(data, list):
                    return data
                else:
                    print(f"⚠️ 闹钟数据格式错误（期望列表，实际为{type(data).__name__}），重置为空列表")
                    return []
    except Exception as e:
        print(f"加载闹钟数据失败: {e}")
    return []


def save_alarms(alarms):
    """保存闹钟数据"""

    try:
        if len(alarms) < 6:
            with open(ALARM_FILE, 'w', encoding='utf-8') as f:
                json.dump(alarms, f, ensure_ascii=False, indent=2)
            return True
        else:
            messagebox.showerror("错误", "无法保存闹钟数据，不得保存超过六个字符的标题")
            print("❌ 闹钟数据长度超过6个，请删除部分数据")
            return False
    except Exception as e:
        print(f"保存闹钟数据失败: {e}")
        return False


def load_memos():
    """加载备忘录数据"""
    try:
        if os.path.exists(MEMO_FILE):
            with open(MEMO_FILE, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                # 确保返回的是列表，而不是字典或其他类型
                if isinstance(data, list):
                    return data
                else:
                    print(f"⚠️ 备忘录数据格式错误（期望列表，实际为{type(data).__name__}），重置为空列表")
                    return []
    except Exception as e:
        print(f"加载备忘录数据失败: {e}")
    return []


def save_memos(memos):
    """保存备忘录数据"""
    try:
        with open(MEMO_FILE, 'w', encoding='utf-8') as f:
            json.dump(memos, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存备忘录数据失败: {e}")
        return False


def load_messages():
    """加载消息中心数据"""
    try:
        if os.path.exists(MESSAGE_FILE):
            with open(MESSAGE_FILE, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    print(f"⚠️ 消息数据格式错误，重置为空列表")
                    return []
    except Exception as e:
        print(f"加载消息数据失败: {e}")
    return []


def save_messages(messages):
    """保存消息中心数据"""
    try:
        # 只保留最近100条消息，避免文件过大
        if len(messages) > 100:
            messages = messages[-100:]
        
        with open(MESSAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存消息数据失败: {e}")
        return False


def add_message(message_type, title, content, extra_data=None):
    """添加新消息到消息中心"""
    from datetime import datetime
    
    messages = load_messages()
    
    message = {
        "id": len(messages) + 1,
        "type": message_type,  # "alarm_triggered", "snooze_created", "memo_added" 等
        "title": title,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "read": False,  # 是否已读
        "extra_data": extra_data or {}
    }
    
    messages.append(message)
    save_messages(messages)
    
    return message


def play_custom_audio(mp3_path):
    """播放自定义音频文件（模块级函数，供所有类调用）"""
    try:
        # 验证文件路径
        if not os.path.exists(mp3_path):
            print(f"⚠️ 音频文件不存在: {mp3_path}")
            return
        
        # 获取文件扩展名
        file_ext = os.path.splitext(mp3_path)[1].lower()
        
        # winsound只支持WAV格式
        if file_ext == '.wav':
            try:
                import winsound
                # SND_ASYNC: 异步播放（非阻塞）
                # SND_FILENAME: 将第一个参数解释为文件名
                winsound.PlaySound(mp3_path, winsound.SND_ASYNC | winsound.SND_FILENAME)
                print(f"🎵 正在播放 (winsound): {os.path.basename(mp3_path)}")
                return
            except Exception as e:
                print(f"⚠️ winsound播放失败: {e}，尝试其他方式...")
        
        # 对于MP3等其他格式，使用系统默认播放器
        print(f"🎵 使用系统默认播放器打开: {os.path.basename(mp3_path)}")
        os.startfile(mp3_path)
        
    except Exception as e:
        print(f"❌ 播放自定义音频失败: {e}")
        import traceback
        traceback.print_exc()


def stop_all_sounds():
    """停止所有正在播放的声音"""
    try:
        import winsound
        # SND_PURGE: 停止所有正在播放的声音
        winsound.PlaySound(None, winsound.SND_PURGE)
        print("🔇 已停止所有声音")
    except Exception as e:
        print(f"⚠️ 停止声音失败: {e}")


# 音频文件夹路径
SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm_sounds")

# 支持的音频格式
SUPPORTED_AUDIO_EXTENSIONS = ('.mp3', '.wav', '.wma', '.ogg', '.flac', '.m4a')


def scan_sound_files():
    """扫描音频文件夹，返回所有音频文件列表"""
    sound_files = []
    
    # 如果文件夹不存在，创建它
    if not os.path.exists(SOUNDS_DIR):
        try:
            os.makedirs(SOUNDS_DIR)
            print(f"✅ 已创建音频文件夹: {SOUNDS_DIR}")
            print(f"💡 请将您的音频文件放入此文件夹")
        except Exception as e:
            print(f"⚠️ 创建音频文件夹失败: {e}")
            return sound_files
    
    # 扫描文件夹中的所有音频文件
    try:
        for filename in os.listdir(SOUNDS_DIR):
            if filename.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS):
                file_path = os.path.join(SOUNDS_DIR, filename)
                if os.path.isfile(file_path):
                    sound_files.append({
                        "name": filename,  # 显示名称（不含扩展名）
                        "path": file_path,  # 完整路径
                        "type": "custom_file"  # 标记为自定义文件
                    })
        
        # 按文件名排序
        sound_files.sort(key=lambda x: x["name"].lower())
        
        if sound_files:
            print(f"🎵 发现 {len(sound_files)} 个音频文件")
        else:
            print(f"📁 音频文件夹为空，请添加音频文件到: {SOUNDS_DIR}")
            
    except Exception as e:
        print(f"⚠️ 扫描音频文件失败: {e}")
    
    return sound_files
