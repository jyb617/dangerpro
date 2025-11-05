#!/usr/bin/env python3
"""
摄像头调试测试脚本
用于测试摄像头是否可用，以及调试代码是否正常工作
"""

import cv2
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_camera_access(camera_id=0):
    """测试摄像头访问"""
    logger.info("=" * 60)
    logger.info(f"测试摄像头访问: camera_id={camera_id}")

    try:
        logger.info(f"正在打开摄像头 {camera_id}...")
        cap = cv2.VideoCapture(camera_id)

        if not cap.isOpened():
            logger.error(f"❌ 无法打开摄像头 {camera_id}")
            logger.error("可能原因:")
            logger.error("  1. 摄像头不存在")
            logger.error("  2. 摄像头权限不足")
            logger.error("  3. 摄像头被其他程序占用")
            logger.error("  4. 在容器/虚拟环境中运行无法访问主机摄像头")
            return False

        # 获取摄像头信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        logger.info(f"✅ 摄像头 {camera_id} 打开成功!")
        logger.info(f"摄像头参数:")
        logger.info(f"  - 分辨率: {width}x{height}")
        logger.info(f"  - 帧率: {fps} fps")

        # 尝试读取一帧
        logger.info("尝试读取一帧...")
        ret, frame = cap.read()

        if ret:
            logger.info(f"✅ 成功读取帧: shape={frame.shape}, dtype={frame.dtype}")
        else:
            logger.error("❌ 无法读取帧")
            cap.release()
            return False

        cap.release()
        logger.info("✅ 摄像头测试成功!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"异常堆栈:\n{traceback.format_exc()}")
        return False

def test_models_exist():
    """测试模型文件是否存在"""
    logger.info("=" * 60)
    logger.info("检查模型文件...")

    import os

    detection_model = "inferences/models/detection-fp32.onnx"
    extraction_model = "inferences/models/extraction-fp32.onnx"

    all_exist = True

    if os.path.exists(detection_model):
        size = os.path.getsize(detection_model) / (1024 * 1024)
        logger.info(f"✅ 检测模型存在: {detection_model} ({size:.2f} MB)")
    else:
        logger.error(f"❌ 检测模型不存在: {detection_model}")
        all_exist = False

    if os.path.exists(extraction_model):
        size = os.path.getsize(extraction_model) / (1024 * 1024)
        logger.info(f"✅ 特征提取模型存在: {extraction_model} ({size:.2f} MB)")
    else:
        logger.error(f"❌ 特征提取模型不存在: {extraction_model}")
        all_exist = False

    if not all_exist:
        logger.error("")
        logger.error("模型文件缺失! 请按照以下步骤获取:")
        logger.error("  1. 从项目 GitHub Release 下载模型文件")
        logger.error("  2. 或联系项目作者获取模型文件")
        logger.error("  3. 将模型文件放入 inferences/models/ 目录")

    logger.info("=" * 60)
    return all_exist

def main():
    """主函数"""
    logger.info("🔍 开始摄像头和系统调试测试")
    logger.info("")

    # 测试摄像头
    camera_ok = test_camera_access(0)

    # 测试模型文件
    models_ok = test_models_exist()

    # 总结
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试总结:")
    logger.info(f"  - 摄像头访问: {'✅ 通过' if camera_ok else '❌ 失败'}")
    logger.info(f"  - 模型文件: {'✅ 完整' if models_ok else '❌ 缺失'}")

    if camera_ok and models_ok:
        logger.info("")
        logger.info("🎉 系统准备就绪! 可以开始实时检测")
        logger.info("下一步:")
        logger.info("  1. 启动 Flask 服务端")
        logger.info("  2. 启动 Web 客户端")
        logger.info("  3. 创建实时检测会话，source='0'")
        return 0
    else:
        logger.info("")
        logger.info("⚠️ 系统未就绪，请先解决上述问题")
        if not camera_ok:
            logger.info("")
            logger.info("摄像头问题解决方案:")
            logger.info("  - 如果在容器中运行: 必须在本地机器运行 Flask 服务端")
            logger.info("  - 如果在本地运行: 检查摄像头权限和驱动")
            logger.info("  - 临时方案: 使用视频文件进行测试")
        return 1

    logger.info("=" * 60)

if __name__ == "__main__":
    sys.exit(main())
