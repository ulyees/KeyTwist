# KeyTwist - 现代化的键盘快捷键映射工具

<p align="center">

<img src="https://img.shields.io/badge/版本-0.0.1-blue" alt="版本">

<img src="https://img.shields.io/badge/Python-3.7%2B-green" alt="Python">

<img src="https://img.shields.io/badge/许可证-MIT-yellow" alt="许可证">

<img src="https://img.shields.io/badge/构建-2026.03.14-lightgrey" alt="构建日期">

KeyTwist 是一款现代化的键盘快捷键映射工具，旨在解决部分软件无法自定义快捷键的问题。通过简单的规则配置，您可以将任意快捷键组合映射到另一个快捷键组合，支持双击检测、左右键区分、连击计数等高级功能。

## ✨ 核心特性

### 🎯 智能快捷键映射

- **全键支持**：支持所有标准键、功能键、修饰键（包括左右Ctrl/Alt/Shift/Win）
- **双击检测**：可设置双击特定键触发映射，如双击左Ctrl触发特定操作
- **连击计数**：支持配置连击次数（1-9次），满足复杂触发需求
- **间隔控制**：可设置最大触发间隔，确保准确识别
- **修饰键泛化**：自动匹配左右修饰键变体（如`lctrl`、`rctrl`都可匹配`ctrl`）

### 🎨 现代化图形界面

- **多标签设置**：常规、外观、规则、关于四个功能页面
- **实时预览**：快捷键录制时实时显示按键组合
- **规则管理**：直观的规则列表，支持增删改查、启用/禁用
- **主题切换**：支持浅色/深色主题，界面美观
- **字体调整**：可自定义字体家族和字号大小
- **响应式设计**：窗口大小可调，布局自适应

### ⚙️ 高级功能

- **系统托盘集成**：最小化到系统托盘，不占用任务栏空间
- **开机自启动**：支持全平台开机自启动配置
- **管理员权限**：可提权运行以拦截系统级快捷键
- **实时重载**：配置文件修改后自动重载规则
- **进程单例**：确保同一时间只运行一个实例
- **详细日志**：完整的运行日志记录，便于调试

### 🔧 技术特性

- **跨平台支持**：Windows、macOS、Linux 全平台兼容
- **高性能引擎**：基于pynput的低延迟键盘事件处理
- **原生体验**：使用wxPython构建原生界面
- **配置热更新**：修改规则无需重启程序
- **错误恢复**：完善的异常处理机制

## 📦 安装与运行

### 环境要求

- Python 3.7 或更高版本
- 操作系统：Windows 7+ / macOS 10.12+ / Linux (X11或Wayland)

### 快速开始

1. 克隆仓库或下载源码

```python
git clone https://github.com/ulyees/KeyTwist
cd KeyTwist
```

1. 安装依赖

```
pip install -r requirements.txt
```

1. 运行程序

```
python run.py
```

### 依赖说明

```
wxPython>=4.1.1      # 图形界面框架
pynput>=1.7.6        # 键盘事件监听
Pillow>=9.0.0        # 图像处理
pystray>=0.19.0      # 系统托盘支持
```

## 🚀 使用方法

### 首次运行

1. 首次运行时会自动生成默认配置文件 `hotkeys.json`
2. 程序启动后会在系统托盘中显示图标
3. 右键点击托盘图标 → 选择"打开设置"进入配置界面

### 基本配置流程

1. **常规设置**：配置启动行为、日志级别等
2. **外观设置**：选择主题、字体、图标等
3. **规则管理**：创建和管理快捷键映射规则
4. **保存应用**：点击"保存并重载"应用所有更改

### 创建映射规则

1. 进入"规则"页面，点击"新增"
2. 填写规则基本信息（ID、描述）
3. 点击"录制"按钮录制触发键和输出键
4. 配置连击次数、最大间隔等参数
5. 保存规则并重载引擎

## 📖 配置示例

### 配置文件结构

```
{
  "rules": [
    {
      "id": "unique_rule_id",
      "description": "规则描述",
      "trigger": "触发键组合",
      "output": "输出键组合",
      "count": 2,
      "max_interval": 0.45,
      "block_source": false,
      "enabled": true
    }
  ]
}
```

### 示例规则

```
{
  "rules": [
    {
      "id": "double_qw_to_ctrl_win_u",
      "description": "双击 q+w 输出 Ctrl+Win+U",
      "trigger": "q+w",
      "output": "ctrl+cmd+u",
      "count": 2,
      "max_interval": 0.45,
      "block_source": false,
      "enabled": true
    },
    {
      "id": "double_lctrl_to_shortcut",
      "description": "双击左Ctrl输出左Ctrl+Alt+X",
      "trigger": "lctrl",
      "output": "lctrl+alt+x",
      "count": 2,
      "max_interval": 0.35,
      "block_source": true,
      "enabled": true
    }
  ]
}
```

## 🎮 快捷键录制

### 录制窗口说明

- **触发方式**：按下要录制的按键组合，全部松开后自动完成
- **特殊处理**：如果系统没有正确上报松键，会在短暂静止后自动保存
- **支持纯修饰键**：可以录制仅包含修饰键的快捷键
- **清空重录**：点击"清空重录"按钮可重新录制

### 按键显示格式

程序内部使用标准化键名，但显示时会自动转换为易读格式：

- `lctrl`→ 左Ctrl
- `rshift`→ 右Shift
- `cmd`→ Win (Windows) / Command (macOS)
- 方向键使用箭头符号表示

## ⚡ 高级功能详解

### 1. 连击与间隔控制

- **count**：连续按下的次数，设置为2即为"双击触发"
- **max_interval**：多次按键之间的最大时间间隔（秒）
- 两者配合可实现精确的连击检测

### 2. 原始按键拦截

- **block_source**：设置为true时，尝试阻止原始按键事件
- **平台限制**： Windows：需要管理员权限才能可靠拦截 macOS：需要辅助功能权限 Linux：X11下可用，Wayland可能受限

### 3. 系统集成

- **开机自启动**：全平台支持，自动创建启动项
- **系统托盘**：后台运行，不干扰工作
- **单实例控制**：防止重复运行冲突
- **日志轮转**：自动记录运行状态和错误信息

## 🔧 命令行参数

```
# 普通模式（启动图形界面）
python run.py

# 引擎模式（仅运行快捷键映射引擎）
python run.py --engine

# 指定配置文件
python run.py /path/to/custom_config.json
```

## 🐛 故障排除

### 常见问题

#### 1. 快捷键不生效

- 检查规则是否已启用（enabled: true）
- 确认引擎是否正在运行（托盘图标显示"运行中"）
- 验证是否有其他程序占用相同快捷键
- 检查是否需要的管理员权限

#### 2. 程序无法启动

- 确认Python版本为3.7+
- 检查所有依赖包是否已正确安装
- 查看日志文件中的错误信息

#### 3. 按键被错误拦截

- 在规则中设置`block_source: false`
- 检查是否有多个键盘钩子程序冲突
- 尝试以管理员权限运行

### 日志位置

- 主日志：`程序目录/logs/keytwist.log`
- 引擎日志：`程序目录/logs/keytwist_engine.log`

## 📁 项目结构

```
KeyTwist/
├── gui.py              # 图形界面主模块
├── main.py             # 快捷键映射引擎
├── run.py              # 主启动器和系统集成
├── hotkeys.json        # 快捷键规则配置
├── app_settings.json   # 应用程序设置
├── icon.ico           # 程序图标
├── icon.png           # 程序图标
├── logs/              # 日志目录
├── requirements.txt   # 依赖包列表
└── README.md         # 本文档
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request来帮助改进这个项目！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](https://yuanbao.tencent.com/chat/naQivTmsDa/LICENSE)文件了解详情。

## 🆘 技术支持

- **问题反馈**：请通过GitHub Issues提交
- **邮箱**：pengxiaoyou435@gmail.com
- **注意事项**：本软件可能存在bug，欢迎反馈和改进建议

## 🌟 致谢

感谢所有贡献者和用户的支持！特别感谢以下开源项目：

- [wxPython](https://wxpython.org/)- 跨平台GUI框架
- [pynput](https://pypi.org/project/pynput/)- 键盘事件监听库
- [Pillow](https://python-pillow.org/)- 图像处理库
- [pystray](https://pypi.org/project/pystray/)- 系统托盘支持

------

让您的键盘操作更加高效、个性化！

如果有任何问题或建议，请随时联系。
