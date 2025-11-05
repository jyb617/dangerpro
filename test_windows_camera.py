#!/usr/bin/env python3
"""
Windows 摄像头调试脚本
测试不同的摄像头访问方式
"""

import cv2
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_camera_simple(index=0):
    """测试简单方式打开摄像头"""
    logger.info("=" * 60)
    logger.info(f"方法1: 简单方式 cv2.VideoCapture({index})")

    cap = cv2.VideoCapture(index)

    if cap.isOpened():
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        logger.info(f"✅ 成功! 分辨率={width}x{height}, 帧率={fps}fps")

        ret, frame = cap.read()
        if ret:
            logger.info(f"✅ 成功读取帧: shape={frame.shape}")
            cap.release()
            return True
        else:
            logger.error("❌ 无法读取帧")
            cap.release()
            return False
    else:
        logger.error(f"❌ 无法打开摄像头 {index}")
        return False

def test_camera_with_backend(index=0, backend=cv2.CAP_DSHOW):
    """使用指定后端打开摄像头"""
    backend_names = {
        cv2.CAP_DSHOW: "DirectShow",
        cv2.CAP_MSMF: "Microsoft Media Foundation",
        cv2.CAP_ANY: "Auto"
    }

    backend_name = backend_names.get(backend, f"Backend-{backend}")
    logger.info("=" * 60)
    logger.info(f"方法2: 使用 {backend_name} 后端")

    cap = cv2.VideoCapture(index, backend)

    if cap.isOpened():
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        logger.info(f"✅ 成功! 分辨率={width}x{height}, 帧率={fps}fps")

        ret, frame = cap.read()
        if ret:
            logger.info(f"✅ 成功读取帧: shape={frame.shape}")
            cap.release()
            return True, backend_name
        else:
            logger.error("❌ 无法读取帧")
            cap.release()
            return False, backend_name
    else:
        logger.error(f"❌ 无法使用 {backend_name} 打开摄像头")
        return False, backend_name

def test_all_camera_indices():
    """测试所有可能的摄像头索引"""
    logger.info("=" * 60)
    logger.info("方法3: 扫描所有摄像头索引 (0-5)")

    available_cameras = []

    for i in range(6):
        logger.info(f"\n尝试索引 {i}...")
        cap = cv2.VideoCapture(i)

        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                logger.info(f"✅ 索引 {i} 可用!")
                available_cameras.append(i)
            cap.release()
        else:
            logger.info(f"  索引 {i} 不可用")

    if available_cameras:
        logger.info(f"\n✅ 找到 {len(available_cameras)} 个可用摄像头: {available_cameras}")
        return available_cameras
    else:
        logger.error("\n❌ 未找到任何可用摄像头")
        return []

def check_opencv_build_info():
    """检查 OpenCV 编译信息"""
    logger.info("=" * 60)
    logger.info("OpenCV 信息:")
    logger.info(f"  版本: {cv2.__version__}")
    logger.info(f"  构建信息:")

    build_info = cv2.getBuildInformation()

    # 提取关键信息
    for line in build_info.split('\n'):
        if 'Video I/O' in line or 'FFMPEG' in line or 'DirectShow' in line or 'MSMF' in line:
            logger.info(f"    {line.strip()}")

def test_camera_permissions():
    """检查摄像头权限（Windows）"""
    logger.info("=" * 60)
    logger.info("Windows 摄像头权限检查:")

    try:
        import winreg

        # 检查摄像头隐私设置
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
            value, _ = winreg.QueryValueEx(key, "Value")

            if value == "Allow":
                logger.info("✅ 摄像头权限: 已允许")
            elif value == "Deny":
                logger.error("❌ 摄像头权限: 已拒绝")
                logger.error("请前往: 设置 -> 隐私 -> 相机 -> 允许应用访问相机")
            else:
                logger.warning(f"⚠️ 摄像头权限状态未知: {value}")

            winreg.CloseKey(key)
        except FileNotFoundError:
            logger.warning("⚠️ 无法读取摄像头权限设置")
        except Exception as e:
            logger.warning(f"⚠️ 检查权限时出错: {e}")

    except ImportError:
        logger.info("(非 Windows 系统，跳过权限检查)")

def provide_solutions(results):
    """根据测试结果提供解决方案"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("🔧 解决方案建议:")
    logger.info("")

    if results['simple_success'] or results['available_cameras']:
        logger.info("✅ 摄像头可用!")

        if results['best_backend']:
            logger.info(f"\n推荐使用 {results['best_backend']} 后端")
            logger.info("\n修改 realtime.py 中的初始化代码:")
            logger.info("```python")
            if "DirectShow" in results['best_backend']:
                logger.info("self.capture = cv2.VideoCapture(source, cv2.CAP_DSHOW)")
            elif "Media Foundation" in results['best_backend']:
                logger.info("self.capture = cv2.VideoCapture(source, cv2.CAP_MSMF)")
            logger.info("```")

        if results['available_cameras'] and 0 not in results['available_cameras']:
            logger.info(f"\n⚠️ 摄像头不在索引 0，使用 {results['available_cameras'][0]}")
            logger.info(f"创建会话时输入: {results['available_cameras'][0]}")

    else:
        logger.info("❌ 摄像头不可用，请检查:")
        logger.info("")
        logger.info("1. 摄像头硬件:")
        logger.info("   - 笔记本内置摄像头是否正常")
        logger.info("   - USB摄像头是否已连接")
        logger.info("   - 设备管理器中摄像头是否有黄色感叹号")
        logger.info("")
        logger.info("2. 摄像头占用:")
        logger.info("   - 关闭所有可能占用摄像头的程序")
        logger.info("   - Zoom, Teams, Skype, 微信等")
        logger.info("   - Windows 相机应用")
        logger.info("")
        logger.info("3. 系统权限:")
        logger.info("   - 设置 -> 隐私 -> 相机")
        logger.info("   - 确保允许应用访问相机")
        logger.info("   - 确保允许桌面应用访问相机")
        logger.info("")
        logger.info("4. OpenCV 驱动:")
        logger.info("   - 尝试重新安装: pip install --upgrade opencv-python")
        logger.info("")
        logger.info("5. 替代方案:")
        logger.info("   - 使用视频文件进行测试")
        logger.info("   - 使用 RTSP 网络摄像头")

def main():
    """主函数"""
    logger.info("🔍 Windows 摄像头调试工具")
    logger.info("")

    results = {
        'simple_success': False,
        'best_backend': None,
        'available_cameras': []
    }

    # 1. OpenCV 信息
    check_opencv_build_info()

    # 2. 权限检查
    test_camera_permissions()

    # 3. 简单方式
    results['simple_success'] = test_camera_simple(0)

    # 4. 不同后端
    if not results['simple_success']:
        logger.info("")
        logger.info("简单方式失败，尝试使用特定后端...")

        # DirectShow (Windows 推荐)
        success_ds, name_ds = test_camera_with_backend(0, cv2.CAP_DSHOW)
        if success_ds:
            results['best_backend'] = name_ds

        # MSMF
        if not success_ds:
            success_msmf, name_msmf = test_camera_with_backend(0, cv2.CAP_MSMF)
            if success_msmf:
                results['best_backend'] = name_msmf

    # 5. 扫描所有索引
    if not results['simple_success'] and not results['best_backend']:
        logger.info("")
        logger.info("尝试所有索引...")
        results['available_cameras'] = test_all_camera_indices()

    # 6. 提供解决方案
    provide_solutions(results)

    logger.info("")
    logger.info("=" * 60)

    return 0 if (results['simple_success'] or results['best_backend'] or results['available_cameras']) else 1

if __name__ == "__main__":
    sys.exit(main())
