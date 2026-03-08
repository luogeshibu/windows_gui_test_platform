
# Windows GUI Test Platform

一个 **Windows GUI 自动化测试平台**，支持 **鼠标、键盘、拖拽、双击、快捷键、截图、图像识别** 等自动化操作。

该项目可以：
- 自动录制用户操作
- 生成 JSON 用例
- 使用 Python 执行 GUI 自动化测试
- 支持图像识别 + 坐标操作
- 提供 GUI 测试平台界面

适用于：
- Windows桌面应用自动化测试
- GUI回归测试
- 自动化操作工具
- 测试平台开发

---

# 项目特性

支持以下自动化能力：

## 鼠标操作
- 鼠标移动
- 单击
- 双击
- 右键
- 中键
- 拖拽
- 滚轮

## 键盘操作
支持组合键，例如：

Ctrl + S  
Ctrl + O  
Win + D  
Alt + F4  

## 文本输入
支持自动输入文本：

type_text  
paste_text  

## 图像识别
支持：

click_image  
wait_image  
assert_image  

基于 **OpenCV + pyautogui**

## 自动截图
每个步骤执行后自动截图记录。

## 自动录制
可以录制用户真实操作：

鼠标  
键盘  
拖拽  
双击  
快捷键  

并自动生成 JSON 用例。

---

# 项目结构

```
windows_gui_test_platform
│
├── app
│   ├── core
│   │   ├── case_loader.py
│   │   ├── executor.py
│   │   ├── matcher.py
│   │   ├── models.py
│   │   └── recorder.py
│   │
│   ├── main.py
│   ├── ui
│   └── utils
│
├── cases
│   └── record_full_case.json
│
├── platform_gui.py
├── recorder.py
└── requirements.txt
```

---

# 环境安装

建议 Python 版本：

Python 3.9+

安装依赖：

```
pip install -r requirements.txt
```

如果需要图像识别：

```
pip install opencv-python
```

---

# 录制测试用例

运行录制器：

```
python recorder.py
```

启动后：

1. 自动记录 鼠标 / 键盘 / 拖拽 / 双击  
2. 支持 Ctrl+S / Win+D 等快捷键  
3. 按 ESC 结束录制  

结束后会生成：

```
cases/record_full_case.json
```

示例：

```json
{
  "name": "record_full_case",
  "steps": [
    {
      "action": "click_point",
      "x": 560,
      "y": 430
    },
    {
      "action": "type_text",
      "text": "hello world"
    },
    {
      "action": "hotkey",
      "keys": ["ctrl", "s"]
    }
  ]
}
```

---

# 执行测试用例

运行：

```
python app/main.py
```

默认执行：

```
cases/record_full_case.json
```

执行流程：

读取 JSON 用例  
逐步执行  
自动截图  
记录执行日志  

---

# GUI 测试平台

启动 GUI 平台：

```
python platform_gui.py
```

功能：

- 用例列表
- 执行用例
- 查看执行日志
- 自动截图
- 用例管理

---

# JSON 用例格式

## 单击

```json
{
  "action": "click_point",
  "x": 500,
  "y": 300
}
```

## 双击

```json
{
  "action": "double_click_point",
  "x": 500,
  "y": 300
}
```

## 拖拽

```json
{
  "action": "drag_point",
  "start_x": 500,
  "start_y": 300,
  "end_x": 700,
  "end_y": 500
}
```

## 快捷键

```json
{
  "action": "hotkey",
  "keys": ["ctrl", "s"]
}
```

## 输入文本

```json
{
  "action": "type_text",
  "text": "hello"
}
```

## 等待

```json
{
  "action": "sleep",
  "seconds": 2
}
```

---

# 执行日志

执行时终端输出：

STEP 1: click_point  
STEP 2: type_text  
STEP 3: hotkey  

执行失败时：

用例执行失败 ❌  

并自动保存截图。

---

# Roadmap

未来版本计划支持：

- Web UI 测试
- OCR 自动识别
- 元素定位 (UI Automation)
- 测试报告
- 用例编辑器
- CI/CD 集成
- 多分辨率适配
- AI 自动生成测试用例

---

# License

MIT License
