import threading
import collections
import cv2
import time
import toml
import numpy as np
import logging
import traceback
import inferences.engines as engines

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("初始化实时检测模块")

configs = toml.load('inferences/configs/config.toml')
logger.info(f"配置文件加载成功: inferences/configs/config.toml")

segment_length = configs['segment-length']
history_length = configs['history-length']

capture_interval = configs['capture-interval']
prepare_interval = configs['prepare-interval']
predict_interval = configs['predict-interval']

logger.info(f"配置参数: segment_length={segment_length}, history_length={history_length}")
logger.info(f"时间间隔: capture={capture_interval}s, prepare={prepare_interval}s, predict={predict_interval}s")


def execute_task_in_seconds(task, args=None, target_seconds=0):
    start_seconds = time.perf_counter()

    if args is None:
        task_execution_result = task()
    else:
        task_execution_result = task(args)

    finish_seconds = time.perf_counter()

    delta_seconds = finish_seconds - start_seconds
    delay_seconds = target_seconds - delta_seconds

    if delay_seconds > 0:
        time.sleep(delay_seconds)

    return task_execution_result


class RealtimeInferenceSession:
    def __init__(self, source):
        logger.info("=" * 60)
        logger.info(f"创建实时检测会话: source='{source}'")

        # 初始化视频捕获
        try:
            self.capture = self._open_video_source(source)

            # 获取视频信息
            width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.capture.get(cv2.CAP_PROP_FPS))

            logger.info(f"✅ 视频源打开成功!")
            logger.info(f"视频参数: 分辨率={width}x{height}, 帧率={fps}fps")

        except Exception as e:
            logger.error(f"❌ 初始化视频捕获失败: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            raise

        # 初始化队列
        logger.info(f"初始化队列: segment_queue(maxlen={segment_length}), feature_queue(maxlen={history_length})")
        self.segment_queue = collections.deque(maxlen=segment_length)
        self.feature_queue = collections.deque(maxlen=history_length)

        # 初始化线程控制标志
        self.capture_running = True
        self.prepare_running = True
        self.predict_running = True

        # 初始化共享变量
        self.current_frame = None
        self.current_score = None

        # 初始化统计计数器
        self.frame_count = 0
        self.segment_count = 0
        self.predict_count = 0
        self.error_count = 0

        # 初始化锁
        self.current_lock = threading.Lock()
        self.segment_lock = threading.Lock()

        # 启动工作线程
        logger.info("启动工作线程...")
        self.capture_thread = threading.Thread(target=self.capture_process, name="CaptureThread")
        self.prepare_thread = threading.Thread(target=self.prepare_process, name="PrepareThread")
        self.predict_thread = threading.Thread(target=self.predict_process, name="PredictThread")

        self.capture_thread.start()
        self.prepare_thread.start()
        self.predict_thread.start()

        logger.info("✅ 所有线程启动成功")
        logger.info("=" * 60)

    def __del__(self):
        self.release()

    def _open_video_source(self, source):
        """
        智能打开视频源，支持多种后端
        在 Windows 上优先使用 DirectShow
        """
        import platform
        import sys

        logger.info(f"正在打开视频源: {source}")
        logger.info(f"操作系统: {platform.system()}")

        # 尝试不同的方式打开摄像头
        backends_to_try = []

        # 判断是否为摄像头索引
        is_camera_index = isinstance(source, int) or (isinstance(source, str) and source.isdigit())

        if is_camera_index:
            source_int = int(source) if isinstance(source, str) else source

            # Windows 系统优先尝试 DirectShow
            if platform.system() == 'Windows':
                backends_to_try = [
                    (cv2.CAP_DSHOW, "DirectShow"),
                    (cv2.CAP_MSMF, "Microsoft Media Foundation"),
                    (cv2.CAP_ANY, "Auto")
                ]
            else:
                backends_to_try = [
                    (cv2.CAP_ANY, "Auto"),
                    (cv2.CAP_V4L2, "V4L2"),
                ]

            # 尝试不同的后端
            for backend, backend_name in backends_to_try:
                logger.info(f"  尝试使用 {backend_name} 后端...")

                try:
                    cap = cv2.VideoCapture(source_int, backend)

                    if cap.isOpened():
                        # 尝试读取一帧验证
                        ret, frame = cap.read()
                        if ret:
                            logger.info(f"  ✅ 使用 {backend_name} 后端成功!")
                            return cap
                        else:
                            logger.warning(f"  ⚠️ {backend_name} 打开成功但无法读取帧")
                            cap.release()
                    else:
                        logger.warning(f"  ⚠️ {backend_name} 无法打开")

                except Exception as e:
                    logger.warning(f"  ⚠️ {backend_name} 出错: {e}")
                    continue

            # 所有后端都失败
            logger.error(f"❌ 无法打开摄像头 {source}")
            logger.error("可能原因:")
            logger.error("  1. 摄像头不存在或未连接")
            logger.error("  2. 摄像头权限不足 (Windows: 设置->隐私->相机)")
            logger.error("  3. 摄像头被其他程序占用 (Zoom, Teams, 微信等)")
            logger.error("  4. 摄像头驱动问题")
            logger.error("")
            logger.error("调试建议:")
            logger.error(f"  1. 运行: python test_windows_camera.py")
            logger.error("  2. 检查设备管理器中的摄像头状态")
            logger.error("  3. 尝试使用 Windows 相机应用测试摄像头")
            logger.error("  4. 尝试不同的摄像头索引 (0, 1, 2...)")

            raise RuntimeError(f"Failed to open camera: {source}")

        else:
            # 文件路径或 RTSP 地址
            logger.info(f"  检测到文件路径或网络地址: {source}")

            cap = cv2.VideoCapture(source)

            if not cap.isOpened():
                logger.error(f"❌ 无法打开视频源: {source}")
                logger.error("可能原因:")
                logger.error("  1. 文件不存在或路径错误")
                logger.error("  2. 视频格式不支持")
                logger.error("  3. RTSP 地址错误或网络不通")
                logger.error("  4. 缺少相应的解码器")

                raise RuntimeError(f"Failed to open video source: {source}")

            # 验证能否读取
            ret, frame = cap.read()
            if not ret:
                logger.error(f"❌ 视频源打开成功但无法读取帧")
                cap.release()
                raise RuntimeError(f"Cannot read from video source: {source}")

            logger.info(f"  ✅ 视频源打开成功!")
            return cap

    def capture_task(self):
        try:
            read_success, captured_frame = self.capture.read()

            if read_success:
                with self.current_lock:
                    self.current_frame = captured_frame
                    self.frame_count += 1

                # 每100帧输出一次统计
                if self.frame_count % 100 == 0:
                    logger.debug(f"📹 已捕获 {self.frame_count} 帧, 当前segment队列长度: {len(self.segment_queue)}")
            else:
                logger.warning(f"⚠️ 读取帧失败 (尝试 {self.frame_count + 1})")
                self.error_count += 1

        except Exception as e:
            logger.error(f"❌ capture_task异常: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            self.error_count += 1

    def capture_process(self):
        logger.info("🎬 CaptureThread 开始运行")
        try:
            while self.capture_running:
                execute_task_in_seconds(self.capture_task, target_seconds=capture_interval)
        except Exception as e:
            logger.error(f"❌ capture_process异常: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
        finally:
            logger.info("🎬 CaptureThread 已停止")

    def prepare_task(self):
        try:
            with self.current_lock:
                current_frame = self.current_frame

            if current_frame is not None:
                # 预处理帧
                preprocessed = engines.frame_preprocess(current_frame)

                with self.segment_lock:
                    self.segment_queue.append(preprocessed)

                # 当segment队列满时输出日志
                if len(self.segment_queue) == segment_length:
                    self.segment_count += 1
                    logger.debug(f"📦 Segment队列已满 ({segment_length}帧), 准备进行特征提取 (第{self.segment_count}个segment)")

        except Exception as e:
            logger.error(f"❌ prepare_task异常: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            self.error_count += 1

    def prepare_process(self):
        logger.info("🔧 PrepareThread 开始运行")
        try:
            while self.prepare_running:
                execute_task_in_seconds(self.prepare_task, target_seconds=prepare_interval)
        except Exception as e:
            logger.error(f"❌ prepare_process异常: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
        finally:
            logger.info("🔧 PrepareThread 已停止")

    def load_segment_frames(self):
        if not len(self.segment_queue) == segment_length:
            current_segment_frames = None
        else:
            current_segment_frames = self.segment_queue.copy()
            self.segment_queue.clear()

        return current_segment_frames

    def predict_task(self):
        try:
            with self.segment_lock:
                segment_frames = self.load_segment_frames()

            if segment_frames is not None:
                logger.debug(f"🔍 开始处理 segment (feature_queue长度: {len(self.feature_queue)})")

                # 特征提取
                logger.debug("   → 步骤1: segment预处理")
                preprocessed_segment = engines.segment_preprocess(segment_frames)

                logger.debug("   → 步骤2: 特征提取")
                extracted_features = engines.extract_segment_features(preprocessed_segment)
                self.feature_queue.append(extracted_features)

                logger.debug(f"   → 步骤3: 特征序列准备 (队列长度: {len(self.feature_queue)})")
                features = np.stack(self.feature_queue, axis=0)
                features = engines.features_preprocess(features)

                logger.debug("   → 步骤4: 异常检测推理")
                realtime_scores = engines.detection_by_features(features)

                with self.current_lock:
                    self.current_score = realtime_scores[-1]
                    self.predict_count += 1

                logger.info(f"✅ 推理完成 (#{self.predict_count}): 当前异常得分 = {self.current_score:.4f}")

        except Exception as e:
            logger.error(f"❌ predict_task异常: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            self.error_count += 1

    def predict_process(self):
        logger.info("🧠 PredictThread 开始运行")
        try:
            while self.predict_running:
                execute_task_in_seconds(self.predict_task, target_seconds=predict_interval)
        except Exception as e:
            logger.error(f"❌ predict_process异常: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
        finally:
            logger.info("🧠 PredictThread 已停止")

    def get_result(self):
        with self.current_lock:
            result_frame = self.current_frame
            result_score = self.current_score

        if result_frame is None:
            return None

        if result_score is None:
            return None

        return engines.draw_detection_result(result_frame, result_score)

    def release(self):
        logger.info("=" * 60)
        logger.info("正在释放实时检测会话...")

        # 停止所有线程
        logger.info("停止工作线程...")
        self.capture_running = False
        self.prepare_running = False
        self.predict_running = False

        # 等待线程结束
        logger.info("等待CaptureThread结束...")
        self.capture_thread.join(timeout=5)
        logger.info("等待PrepareThread结束...")
        self.prepare_thread.join(timeout=5)
        logger.info("等待PredictThread结束...")
        self.predict_thread.join(timeout=5)

        # 释放摄像头
        logger.info("释放视频捕获资源...")
        self.capture.release()

        # 输出统计信息
        logger.info("=" * 60)
        logger.info("会话统计信息:")
        logger.info(f"  - 总捕获帧数: {self.frame_count}")
        logger.info(f"  - 处理segment数: {self.segment_count}")
        logger.info(f"  - 推理次数: {self.predict_count}")
        logger.info(f"  - 错误次数: {self.error_count}")
        logger.info("会话已释放")
        logger.info("=" * 60)
