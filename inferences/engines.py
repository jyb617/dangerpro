import onnxruntime as ort
import cv2
import toml
import numpy as np
import logging
import traceback
import os

# 配置日志
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("初始化推理引擎模块")

# 加载配置
configs = toml.load('inferences/configs/config.toml')
logger.info("✅ 配置文件加载成功")

# 加载ONNX模型
try:
    detection_model_path = configs['detection-model-path']
    extraction_model_path = configs['extraction-model-path']

    logger.info(f"正在加载检测模型: {detection_model_path}")
    if not os.path.exists(detection_model_path):
        logger.error(f"❌ 检测模型文件不存在: {detection_model_path}")
        raise FileNotFoundError(f"Detection model not found: {detection_model_path}")

    detection_session = ort.InferenceSession(detection_model_path, providers=configs['providers'])
    logger.info(f"✅ 检测模型加载成功")
    logger.info(f"   - Providers: {detection_session.get_providers()}")

    logger.info(f"正在加载特征提取模型: {extraction_model_path}")
    if not os.path.exists(extraction_model_path):
        logger.error(f"❌ 特征提取模型文件不存在: {extraction_model_path}")
        raise FileNotFoundError(f"Extraction model not found: {extraction_model_path}")

    extraction_session = ort.InferenceSession(extraction_model_path, providers=configs['providers'])
    logger.info(f"✅ 特征提取模型加载成功")
    logger.info(f"   - Providers: {extraction_session.get_providers()}")

except Exception as e:
    logger.error(f"❌ 模型加载失败: {e}")
    logger.error(f"异常堆栈:\n{traceback.format_exc()}")
    logger.error("请检查:")
    logger.error("  1. 模型文件是否存在于 inferences/models/ 目录")
    logger.error("  2. 模型文件是否是有效的ONNX格式")
    logger.error("  3. 配置文件中的路径是否正确")
    raise

width = configs['segment-width']
height = configs['segment-height']
length = configs['segment-length']

x1 = configs['crop-x1']
x2 = configs['crop-x2']
y1 = configs['crop-y1']
y2 = configs['crop-y2']

std = configs['normalization-std']
mean = configs['normalization-mean']

smoothing_weight = np.ones(configs['smoothing-window']) / configs['smoothing-window']

logger.info(f"推理参数配置:")
logger.info(f"  - 视频段: {width}x{height}, 长度={length}帧")
logger.info(f"  - 裁剪区域: [{x1}:{x2}, {y1}:{y2}]")
logger.info(f"  - 归一化: mean={mean}, std={std}")
logger.info(f"  - 平滑窗口: {configs['smoothing-window']}")
logger.info("=" * 60)


def normalize(inputs):
    return (inputs - mean) / std


def frame_preprocess(frame):
    preprocessed = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
    preprocessed = preprocessed[y1:y2, x1:x2]

    return cv2.cvtColor(preprocessed, cv2.COLOR_BGR2RGB)


def load_next_segment(capture):
    segment_frames = []

    while len(segment_frames) < length:
        read_success, captured_frame = capture.read()

        if read_success:
            segment_frames.append(frame_preprocess(captured_frame))
        else:
            return False, None

    return True, segment_preprocess(segment_frames)


def segment_preprocess(frames):
    preprocessed = np.stack(frames, axis=0).transpose((3, 0, 1, 2))

    if configs['precision'] == 'fp16':
        preprocessed = normalize(preprocessed).astype(np.float16)
    else:
        preprocessed = normalize(preprocessed).astype(np.float32)

    return np.expand_dims(preprocessed, axis=0)


def extract_segment_features(segment):
    try:
        logger.debug(f"   特征提取输入shape: {segment.shape}, dtype: {segment.dtype}")
        extraction_outputs = extraction_session.run(['outputs'], {'inputs': segment})
        extraction_outputs = extraction_outputs[0]

        result = np.squeeze(extraction_outputs, axis=0)
        logger.debug(f"   特征提取输出shape: {result.shape}")
        return result
    except Exception as e:
        logger.error(f"❌ 特征提取失败: {e}")
        logger.error(f"   输入shape: {segment.shape}, dtype: {segment.dtype}")
        logger.error(f"异常堆栈:\n{traceback.format_exc()}")
        raise


def extract_video_features(video_path):
    features = []
    capture = cv2.VideoCapture(video_path)

    while capture.isOpened():
        load_success, preprocessed_segment = load_next_segment(capture)

        if load_success:
            features.append(extract_segment_features(preprocessed_segment))
        else:
            capture.release()

    return np.stack(features, axis=0)


def features_preprocess(features):
    if configs['precision'] == 'fp16':
        preprocessed = features.astype(np.float16)
    else:
        preprocessed = features.astype(np.float32)

    return np.expand_dims(preprocessed, axis=0)


def sigmoid(inputs):
    return 1 / (1 + np.exp(-inputs))


def detection_by_features(features):
    try:
        logger.debug(f"   异常检测输入shape: {features.shape}, dtype: {features.dtype}")
        detection_outputs = detection_session.run(['outputs'], {'inputs': features})
        detection_outputs = detection_outputs[0]

        result = sigmoid(np.squeeze(detection_outputs, axis=0))
        logger.debug(f"   异常检测输出shape: {result.shape}, 范围: [{result.min():.4f}, {result.max():.4f}]")
        return result
    except Exception as e:
        logger.error(f"❌ 异常检测推理失败: {e}")
        logger.error(f"   输入shape: {features.shape}, dtype: {features.dtype}")
        logger.error(f"异常堆栈:\n{traceback.format_exc()}")
        raise


def score_smoothing(scores):
    return np.convolve(scores, smoothing_weight, mode='same').round(decimals=2)


def expand_scores(scores):
    return np.array(scores).repeat(length, axis=0)


def detection_by_video(video_path):
    features = extract_video_features(video_path)
    features = features_preprocess(features)

    return score_smoothing(detection_by_features(features))


def anomaly_prompt_enhancement(frame, prompt):
    return cv2.putText(frame, prompt, (120, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 215), thickness=2)


def anomaly_border_enhancement(frame, border):
    x2 = frame.shape[1]
    y2 = frame.shape[0]

    return cv2.rectangle(frame, (0, 0), (x2, y2), (0, 0, 215), thickness=border)


def draw_detection_result(frame, score):
    if score > configs['anomaly-threshold']:
        frame = anomaly_prompt_enhancement(frame, configs['anomaly-prompt'])
        frame = anomaly_border_enhancement(frame, configs['anomaly-border'])

        return cv2.putText(frame, f'{score:.2f}', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 215), thickness=2)
    else:
        return cv2.putText(frame, f'{score:.2f}', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 215, 0), thickness=2)
