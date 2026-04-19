# GPU 监控功能说明

## 功能概述

动态岛监控系统现在支持智能检测电脑类型：
- **笔记本电脑**：显示电池电量（🔋 XX%）或充电状态（🔌 AC）
- **台式机**：自动切换显示GPU使用率（🎮 GPU XX%）

## 工作原理

系统通过Windows API检测电池状态：
- 如果 `BatteryLifePercent == -1`，判定为台式机
- 台式机模式下，原电池位置将显示GPU使用率

## 安装GPU监控依赖

要启用GPU使用率监控，需要安装以下任一库：

### 方法1：GPUtil（推荐）

```bash
pip install GPUtil
```

**优点：**
- 简单易用
- 支持多品牌GPU（NVIDIA、AMD、Intel等）

**缺点：**
- 更新可能不及时

### 方法2：nvidia-ml-py（仅NVIDIA）

```bash
pip install nvidia-ml-py
```

**优点：**
- NVIDIA官方库
- 稳定可靠
- 数据准确

**缺点：**
- 仅支持NVIDIA显卡

## 未安装依赖的情况

如果未安装任何GPU监控库，系统将显示：
```
🎮 GPU --
```

这表示检测到台式机，但无法获取GPU使用率。

## 显示效果

### 笔记本电脑
```
CPU 25%  RAM 60%  🔋 85%
```

### 台式机（已安装依赖）
```
CPU 25%  RAM 60%  🎮 GPU 45%
```

### 台式机（未安装依赖）
```
CPU 25%  RAM 60%  🎮 GPU --
```

## 注意事项

1. GPU监控功能仅在检测到台式机时生效
2. 笔记本用户即使安装了GPU监控库，也不会显示GPU信息（仍显示电池）
3. 如需在笔记本上也显示GPU信息，可以修改代码中的判断逻辑
4. GPU使用率刷新频率与系统刷新频率一致（可在设置中调整）

## 故障排除

### 问题：显示 "🎮 GPU --"

**解决方案：**
1. 确认已安装GPUtil或nvidia-ml-py
   ```bash
   pip list | findstr GPUtil
   pip list | findstr nvidia-ml-py
   ```

2. 重新安装依赖
   ```bash
   pip install --force-reinstall GPUtil
   ```

3. 检查是否有多个Python环境
   ```bash
   where python
   ```

### 问题：GPUtil报错

**可能原因：**
- Python版本不兼容
- 缺少系统依赖

**解决方案：**
- 尝试使用nvidia-ml-py替代
- 更新Python到最新版本

## 代码位置

相关代码位于 `LDD.py` 文件中：
- `get_battery()` - 电池检测方法
- `get_gpu_info()` - GPU信息获取方法
- `update_info()` - 信息更新主方法
