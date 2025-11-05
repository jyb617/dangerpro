# 快速修复指南 - 摄像头打开失败 (404错误)

## 🚨 您遇到的问题

```
❌ 无法打开视频源: 0
RuntimeError: Failed to open video source: 0
GET /api/realtimeinference/session/xxx HTTP/1.1" 404
```

## ✅ 解决方案（按顺序执行）

---

### 第1步：清理数据库中的旧会话 ⭐ **必做**

数据库中有无效的会话记录，导致同步失败。

```bash
python cleanup_sessions.py
```

选择 `1. 删除所有会话`，然后输入 `yes` 确认。

---

### 第2步：测试摄像头是否可用 ⭐ **必做**

```bash
python test_windows_camera.py
```

这个脚本会：
- ✅ 自动测试多种打开方式
- ✅ 扫描所有可用摄像头索引
- ✅ 检查权限设置
- ✅ 提供详细的诊断建议

**可能的结果：**

#### 结果A：找到可用摄像头 ✅

```
✅ 索引 0 可用!
推荐使用 DirectShow 后端
```

→ **继续第3步**

#### 结果B：摄像头权限被拒绝 ❌

```
❌ 摄像头权限: 已拒绝
```

→ **修复方法**：
1. 打开 Windows 设置
2. 隐私 → 相机
3. 开启"允许应用访问相机"
4. 开启"允许桌面应用访问相机"
5. 重新运行测试脚本

#### 结果C：摄像头被占用 ❌

```
❌ 无法打开摄像头
```

→ **修复方法**：
1. 关闭所有可能占用摄像头的程序：
   - Zoom, Teams, Skype
   - 微信视频通话
   - Windows 相机应用
   - 其他视频会议软件
2. 重新运行测试脚本

#### 结果D：摄像头在其他索引 ⚠️

```
✅ 找到 1 个可用摄像头: [1]
```

→ **创建会话时使用索引 `1` 而不是 `0`**

---

### 第3步：重启Flask服务端

**停止当前服务** (Ctrl + C)

**重新启动**：
```bash
python -m flask --app servers.server:app run --host=127.0.0.1 --port=8080
```

**现在你会看到改进的日志**：
```log
[2025-11-05 14:40:00] [INFO] 操作系统: Windows
[2025-11-05 14:40:00] [INFO]   尝试使用 DirectShow 后端...
[2025-11-05 14:40:01] [INFO]   ✅ 使用 DirectShow 后端成功!
[2025-11-05 14:40:01] [INFO] ✅ 视频源打开成功!
[2025-11-05 14:40:01] [INFO] 视频参数: 分辨率=640x480, 帧率=30fps
```

---

### 第4步：创建新的实时检测会话

1. 在Web界面点击"创建会话"
2. 填写信息：
   - 会话名称：`笔记本摄像头测试`
   - **视频源**：`0` （或测试脚本提示的其他索引）
   - 备注：`测试`
3. 点击"创建会话"

**如果成功，日志会显示**：
```log
[INFO] 创建实时检测会话: source='0'
[INFO] 操作系统: Windows
[INFO]   尝试使用 DirectShow 后端...
[INFO]   ✅ 使用 DirectShow 后端成功!
[INFO] ✅ 视频源打开成功!
[INFO] 🎬 CaptureThread 开始运行
[INFO] 🔧 PrepareThread 开始运行
[INFO] 🧠 PredictThread 开始运行
```

---

## 🔧 如果仍然失败

### 检查项1：摄像头硬件

1. 打开 Windows **设备管理器**
2. 展开"照相机"或"图像设备"
3. 检查是否有黄色感叹号
4. 如果有，右键 → 更新驱动程序

### 检查项2：在 Windows 相机应用中测试

1. 打开 Windows 自带的"相机"应用
2. 如果相机应用也无法使用，说明是硬件/驱动问题
3. 如果相机应用正常，但Python无法使用，检查权限设置

### 检查项3：使用测试视频文件

如果摄像头实在无法使用，可以用视频文件测试功能：

1. 准备一个测试视频文件（MP4格式）
2. 将文件放到项目目录，如：`D:\Python\Surveillance-main\test_video.mp4`
3. 创建会话时，视频源输入：
   ```
   D:\Python\Surveillance-main\test_video.mp4
   ```
   或使用正斜杠：
   ```
   D:/Python/Surveillance-main/test_video.mp4
   ```

---

## 📊 改进内容

本次更新：

✅ **智能摄像头打开**
- Windows 自动使用 DirectShow 后端
- 自动尝试多种后端
- 详细的错误诊断

✅ **调试工具**
- `test_windows_camera.py` - 摄像头测试
- `cleanup_sessions.py` - 数据库清理
- 详细的日志输出

✅ **更好的错误提示**
- 明确指出问题原因
- 提供具体的解决步骤

---

## 🎯 预期结果

成功后，您将在Web界面看到：
- 实时摄像头画面
- 右下角的异常得分（绿色数字）
- 流畅的视频流

---

## 📞 需要帮助？

如果问题仍未解决，请提供：

1. `test_windows_camera.py` 的完整输出
2. Flask 启动后尝试创建会话的完整日志
3. Windows 设备管理器中的摄像头状态截图
4. Windows 相机应用是否能正常使用

---

## 🚀 快速命令参考

```bash
# 1. 清理数据库
python cleanup_sessions.py

# 2. 测试摄像头
python test_windows_camera.py

# 3. 启动服务
python -m flask --app servers.server:app run --host=127.0.0.1 --port=8080

# 4. 在Web界面创建会话，视频源输入: 0
```

祝您调试顺利！🎉
