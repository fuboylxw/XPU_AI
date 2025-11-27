#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别智能体
自动调用设备语音输入设备，将语音转换为文字
支持自动停止检测和百度语音识别API
"""

import os
import json
import time
import wave
import threading
import requests
import pyaudio
import numpy as np
from typing import Optional, Dict, Any
from config.settings import settings
import logging
from scipy import signal
from scipy.signal import butter, filtfilt, wiener
import os.path as osp

# 条件导入librosa
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("Warning: librosa not available, some audio processing features will be disabled")
    logger.warning("librosa not available, some audio processing features will be disabled")

"""
所有参数统一从项目根目录 .env 通过 config.settings 加载
"""

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = osp.abspath(osp.join(osp.dirname(__file__), "../../.."))
MODELS_CACHE_DIR = osp.join(PROJECT_ROOT, "models_cache")
os.environ['HF_HOME'] = MODELS_CACHE_DIR
os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE_DIR
os.environ['SENTENCE_TRANSFORMERS_HOME'] = MODELS_CACHE_DIR

class VoiceRecognitionAgent:
    """语音识别智能体"""
    
    def __init__(self):
        """初始化语音识别智能体"""
        # 统一从settings读取API与音频参数
        self.api_key = settings.VOICE_RECOGNITION_API_KEY
        self.api_url = settings.VOICE_RECOGNITION_API_URL
        
        # 音频参数
        self.format = getattr(pyaudio, settings.VOICE_AUDIO_FORMAT)
        self.channels = settings.VOICE_AUDIO_CHANNELS
        self.rate = settings.VOICE_AUDIO_RATE
        self.chunk = settings.VOICE_AUDIO_CHUNK
        self.record_seconds = settings.VOICE_RECORD_SECONDS
        self.silence_threshold = settings.VOICE_SILENCE_THRESHOLD
        self.silence_duration = settings.VOICE_SILENCE_DURATION
        
        # 音频处理参数
        self.enable_noise_reduction = settings.VOICE_ENABLE_NOISE_REDUCTION
        self.enable_audio_enhancement = settings.VOICE_ENABLE_AUDIO_ENHANCEMENT
        self.noise_reduction_strength = settings.VOICE_NOISE_REDUCTION_STRENGTH
        self.high_pass_cutoff = settings.VOICE_HIGH_PASS_CUTOFF  # 高通滤波截止频率
        self.low_pass_cutoff = settings.VOICE_LOW_PASS_CUTOFF  # 低通滤波截止频率
        
        # 录制状态
        self.is_recording = False
        self.audio_data = []
        self.audio = None
        self.stream = None
        self.whisper_model = None
        self.whisper_processor = None
        self.whisper_device = "cpu"
        
        logger.info("语音识别智能体初始化完成")
        try:
            self._initialize_whisper()
        except Exception:
            pass
    
    def get_available_devices(self) -> Dict[str, Any]:
        """获取可用的音频设备"""
        try:
            audio = pyaudio.PyAudio()
            devices = []
            default_device = None
            
            logger.info("检测可用音频设备...")
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:  # 输入设备
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
                    logger.info(f"找到输入设备 {i}: {device_info['name']}")
            
            # 尝试获取默认输入设备
            try:
                default_device_info = audio.get_default_input_device_info()
                default_device = default_device_info['index']
                logger.info(f"默认输入设备: {default_device} - {default_device_info['name']}")
            except Exception as e:
                logger.warning(f"无法获取默认输入设备: {e}")
                # 如果有可用设备，使用第一个作为默认设备
                if devices:
                    default_device = devices[0]['index']
                    logger.info(f"使用第一个可用设备作为默认设备: {default_device}")
            
            audio.terminate()
            return {
                'success': True,
                'devices': devices,
                'default_device': default_device
            }
            
        except Exception as e:
            logger.error(f"获取音频设备失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'devices': []
            }
    
    def calculate_volume(self, audio_data: bytes) -> float:
        """计算音频音量"""
        try:
            # 将字节数据转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            # 计算RMS音量
            rms = np.sqrt(np.mean(audio_array**2))
            return rms
        except Exception as e:
            logger.error(f"计算音量失败: {e}")
            return 0.0
    
    def apply_high_pass_filter(self, audio_data: np.ndarray, cutoff_freq: float = None) -> np.ndarray:
        """应用高通滤波器去除低频噪声"""
        try:
            if cutoff_freq is None:
                cutoff_freq = self.high_pass_cutoff
            
            # 设计高通滤波器
            nyquist = self.rate / 2
            normalized_cutoff = cutoff_freq / nyquist
            
            # 确保截止频率在有效范围内
            if normalized_cutoff >= 1.0:
                normalized_cutoff = 0.99
            elif normalized_cutoff <= 0.0:
                normalized_cutoff = 0.01
            
            b, a = butter(4, normalized_cutoff, btype='high')
            filtered_audio = filtfilt(b, a, audio_data)
            
            logger.debug(f"应用高通滤波器，截止频率: {cutoff_freq}Hz")
            return filtered_audio.astype(np.int16)
            
        except Exception as e:
            logger.error(f"高通滤波失败: {e}")
            return audio_data
    
    def apply_low_pass_filter(self, audio_data: np.ndarray, cutoff_freq: float = None) -> np.ndarray:
        """应用低通滤波器去除高频噪声"""
        try:
            if cutoff_freq is None:
                cutoff_freq = self.low_pass_cutoff
            
            # 设计低通滤波器
            nyquist = self.rate / 2
            normalized_cutoff = cutoff_freq / nyquist
            
            # 确保截止频率在有效范围内
            if normalized_cutoff >= 1.0:
                normalized_cutoff = 0.99
            elif normalized_cutoff <= 0.0:
                normalized_cutoff = 0.01
            
            b, a = butter(4, normalized_cutoff, btype='low')
            filtered_audio = filtfilt(b, a, audio_data)
            
            logger.debug(f"应用低通滤波器，截止频率: {cutoff_freq}Hz")
            return filtered_audio.astype(np.int16)
            
        except Exception as e:
            logger.error(f"低通滤波失败: {e}")
            return audio_data
    
    def apply_noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """应用噪声减少算法"""
        try:
            # 转换为浮点数进行处理
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # 方法1: 使用Wiener滤波器
            try:
                # 估计噪声功率（使用前10%的音频作为噪声样本）
                noise_sample_length = len(audio_float) // 10
                noise_sample = audio_float[:noise_sample_length]
                noise_power = np.var(noise_sample)
                
                # 应用Wiener滤波
                if noise_power > 0:
                    filtered_audio = wiener(audio_float, noise=noise_power * self.noise_reduction_strength)
                else:
                    filtered_audio = audio_float
                    
            except Exception as e:
                logger.warning(f"Wiener滤波失败，使用简单降噪: {e}")
                # 方法2: 简单的谱减法
                filtered_audio = self._spectral_subtraction(audio_float)
            
            # 转换回int16格式
            filtered_audio = np.clip(filtered_audio * 32768.0, -32768, 32767)
            
            logger.debug("应用噪声减少算法")
            return filtered_audio.astype(np.int16)
            
        except Exception as e:
            logger.error(f"噪声减少失败: {e}")
            return audio_data
    
    def _spectral_subtraction(self, audio_data: np.ndarray) -> np.ndarray:
        """简单的谱减法降噪"""
        try:
            if not LIBROSA_AVAILABLE:
                logger.warning("librosa不可用，跳过谱减法降噪")
                return audio_data
                
            # 使用librosa进行STFT
            stft = librosa.stft(audio_data)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # 估计噪声谱（使用前10%的帧）
            noise_frames = magnitude.shape[1] // 10
            noise_spectrum = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
            
            # 谱减法
            alpha = self.noise_reduction_strength * 2  # 减法因子
            enhanced_magnitude = magnitude - alpha * noise_spectrum
            
            # 确保幅度不为负
            enhanced_magnitude = np.maximum(enhanced_magnitude, 0.1 * magnitude)
            
            # 重构信号
            enhanced_stft = enhanced_magnitude * np.exp(1j * phase)
            enhanced_audio = librosa.istft(enhanced_stft)
            
            return enhanced_audio
            
        except Exception as e:
            logger.error(f"谱减法降噪失败: {e}")
            return audio_data
    
    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """音频标准化"""
        try:
            # 计算RMS
            rms = np.sqrt(np.mean(audio_data**2))
            
            if rms > 0:
                # 标准化到目标RMS值（约-20dB）
                target_rms = 3276.8  # 约为满量程的10%
                normalization_factor = target_rms / rms
                
                # 限制增益避免过度放大
                normalization_factor = min(normalization_factor, 3.0)
                
                normalized_audio = audio_data * normalization_factor
                
                # 防止削波
                normalized_audio = np.clip(normalized_audio, -32768, 32767)
                
                logger.debug(f"音频标准化，增益: {normalization_factor:.2f}")
                return normalized_audio.astype(np.int16)
            else:
                return audio_data
                
        except Exception as e:
            logger.error(f"音频标准化失败: {e}")
            return audio_data

    def _get_whisper_local_path(self) -> Optional[str]:
        base = osp.join(MODELS_CACHE_DIR, "models--openai--whisper-medium", "snapshots")
        if os.path.isdir(base):
            subs = [d for d in os.listdir(base) if os.path.isdir(osp.join(base, d))]
            subs.sort()
            if subs:
                return osp.join(base, subs[-1])
        return None

    def _initialize_whisper(self):
        try:
            from transformers import WhisperForConditionalGeneration, WhisperProcessor
            try:
                import torch
            except Exception:
                torch = None
            local_path = self._get_whisper_local_path()
            if local_path:
                self.whisper_processor = WhisperProcessor.from_pretrained(local_path, local_files_only=True)
                self.whisper_model = WhisperForConditionalGeneration.from_pretrained(local_path, local_files_only=True)
            else:
                self.whisper_processor = WhisperProcessor.from_pretrained("openai/whisper-medium", cache_dir=MODELS_CACHE_DIR)
                self.whisper_model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-medium", cache_dir=MODELS_CACHE_DIR)
            if torch and torch.cuda.is_available():
                try:
                    torch.set_float32_matmul_precision("high")
                except Exception:
                    pass
                try:
                    self.whisper_model.to("cuda")
                    self.whisper_device = "cuda"
                except Exception:
                    self.whisper_device = "cpu"
            else:
                self.whisper_device = "cpu"
        except Exception as e:
            logger.warning(f"Whisper初始化失败: {e}")
            self.whisper_model = None
            self.whisper_processor = None

    def recognize_speech_whisper(self, wav_filename: str) -> Dict[str, Any]:
        try:
            if self.whisper_model is None or self.whisper_processor is None:
                raise RuntimeError("Whisper未初始化")
            if LIBROSA_AVAILABLE:
                audio, sr = librosa.load(wav_filename, sr=16000)
            else:
                with wave.open(wav_filename, 'rb') as wav_file:
                    frames = wav_file.readframes(wav_file.getnframes())
                    audio_i16 = np.frombuffer(frames, dtype=np.int16)
                    audio = audio_i16.astype(np.float32) / 32768.0
                    sr = wav_file.getframerate()
                if sr != 16000 and LIBROSA_AVAILABLE:
                    audio, sr = librosa.load(wav_filename, sr=16000)
            inputs = self.whisper_processor(audio, sampling_rate=16000, return_tensors="pt")
            try:
                import torch
                input_features = inputs.input_features.to(self.whisper_device)
            except Exception:
                input_features = inputs.input_features
            prompt_ids = self.whisper_processor.get_decoder_prompt_ids(language="zh", task="transcribe")
            generated_ids = self.whisper_model.generate(input_features, forced_decoder_ids=prompt_ids)
            text = self.whisper_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return {
                'success': True,
                'text': text,
                'message': 'Whisper识别成功'
            }
        except Exception as e:
            logger.error(f"Whisper识别失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def preprocess_audio_for_recognition(self, audio_data: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        优化的音频预处理流程，专门为语音识别准备音频
        
        Args:
            audio_data: 输入音频数据
            sample_rate: 采样率
            
        Returns:
            处理后的音频数据
        """
        try:
            logger.info("开始音频预处理流程...")
            
            # 1. 音频标准化（防止溢出）
            processed_audio = self.normalize_audio(audio_data)
            
            # 2. 应用高通滤波器去除低频噪声（如空调、风扇等）
            if self.high_pass_cutoff > 0:
                processed_audio = self.apply_high_pass_filter(processed_audio, sample_rate, self.high_pass_cutoff)
                logger.debug(f"应用高通滤波器，截止频率: {self.high_pass_cutoff}Hz")
            
            # 3. 应用低通滤波器去除高频噪声
            if self.low_pass_cutoff > 0 and self.low_pass_cutoff < sample_rate / 2:
                processed_audio = self.apply_low_pass_filter(processed_audio, sample_rate, self.low_pass_cutoff)
                logger.debug(f"应用低通滤波器，截止频率: {self.low_pass_cutoff}Hz")
            
            # 4. 噪声减少处理
            if self.enable_noise_reduction:
                processed_audio = self.apply_noise_reduction(processed_audio, sample_rate, self.noise_reduction_strength)
                logger.debug(f"应用噪声减少，强度: {self.noise_reduction_strength}")
            
            # 5. 最终标准化，确保音频在合适的动态范围内
            processed_audio = self.normalize_audio(processed_audio)
            
            # 6. 检查音频质量
            audio_rms = np.sqrt(np.mean(processed_audio.astype(np.float32) ** 2))
            if audio_rms < 0.01:
                logger.warning("音频信号过弱，可能影响识别效果")
            elif audio_rms > 0.8:
                logger.warning("音频信号过强，进行额外衰减")
                processed_audio = processed_audio * 0.7
            
            logger.info(f"音频预处理完成，RMS: {audio_rms:.4f}")
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"音频预处理失败: {e}")
            return audio_data  # 返回原始数据作为备选
    
    def enhance_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """综合音频增强处理（保持向后兼容）"""
        return self.preprocess_audio_for_recognition(audio_data, sample_rate)
    
    def start_recording(self, device_index: Optional[int] = None) -> Dict[str, Any]:
        """开始录制音频"""
        try:
            self.audio = pyaudio.PyAudio()
            
            # 选择设备
            if device_index is None:
                try:
                    device_index = self.audio.get_default_input_device_info()['index']
                except Exception as e:
                    logger.warning(f"无法获取默认输入设备: {e}")
                    # 获取第一个可用的输入设备
                    for i in range(self.audio.get_device_count()):
                        device_info = self.audio.get_device_info_by_index(i)
                        if device_info['maxInputChannels'] > 0:
                            device_index = i
                            logger.info(f"使用第一个可用输入设备: {i} - {device_info['name']}")
                            break
                    
                    if device_index is None:
                        raise Exception("未找到可用的音频输入设备")
            
            logger.info(f"开始使用设备 {device_index} 录制音频...")
            
            # 打开音频流
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )
            
            self.is_recording = True
            self.audio_data = []
            
            # 开始录制线程
            recording_thread = threading.Thread(target=self._record_audio)
            recording_thread.daemon = True
            recording_thread.start()
            
            return {
                'success': True,
                'message': '开始录制音频',
                'device_index': device_index
            }
            
        except Exception as e:
            logger.error(f"开始录制失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _record_audio(self):
        """录制音频的内部方法"""
        silence_start_time = None
        start_time = time.time()
        
        logger.info("开始录制，请说话...")
        
        try:
            while self.is_recording:
                # 检查最大录制时间
                if time.time() - start_time > self.record_seconds:
                    logger.info("达到最大录制时间，停止录制")
                    break
                
                # 读取音频数据
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.audio_data.append(data)
                
                # 计算音量
                volume = self.calculate_volume(data)
                
                # 检测静音
                if volume < self.silence_threshold:
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif time.time() - silence_start_time > self.silence_duration:
                        logger.info("检测到静音，停止录制")
                        break
                else:
                    silence_start_time = None
                
                # 短暂休眠
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"录制过程中出错: {e}")
        finally:
            self.stop_recording()
    
    def stop_recording(self) -> Dict[str, Any]:
        """停止录制音频"""
        try:
            self.is_recording = False
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.audio:
                self.audio.terminate()
                self.audio = None
            
            logger.info("录制已停止")
            
            return {
                'success': True,
                'message': '录制已停止',
                'audio_length': len(self.audio_data)
            }
            
        except Exception as e:
            logger.error(f"停止录制失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_audio_to_file(self, filename: str = "temp_audio.wav") -> Dict[str, Any]:
        """保存音频到文件，并应用实时音频增强"""
        try:
            if not self.audio_data:
                return {
                    'success': False,
                    'error': '没有音频数据可保存'
                }
            
            # 合并音频数据
            combined_audio_data = b''.join(self.audio_data)
            
            # 转换音频数据为numpy数组进行增强处理
            audio_array = np.frombuffer(combined_audio_data, dtype=np.int16)
            
            # 应用优化的音频预处理
            if self.enable_noise_reduction or self.enable_audio_enhancement:
                logger.info("对录制音频进行优化预处理...")
                enhanced_audio = self.preprocess_audio_for_recognition(audio_array, self.rate)
                combined_audio_data = enhanced_audio.tobytes()
            else:
                # 即使不启用增强，也进行基本的标准化处理
                normalized_audio = self.normalize_audio(audio_array)
                combined_audio_data = normalized_audio.tobytes()
            
            # 保存为WAV文件
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(pyaudio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(combined_audio_data)
            
            logger.info(f"音频已保存到: {filename}")
            
            return {
                'success': True,
                'filename': filename,
                'message': f'音频已保存到: {filename}'
            }
            
        except Exception as e:
            logger.error(f"保存音频失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def convert_to_pcm(self, wav_filename: str, pcm_filename: str = "temp_audio.pcm") -> Dict[str, Any]:
        """将WAV文件转换为PCM格式，并应用音频增强"""
        try:
            with wave.open(wav_filename, 'rb') as wav_file:
                # 读取音频数据
                audio_data = wav_file.readframes(wav_file.getnframes())
                
                # 转换为numpy数组进行处理
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # 应用优化的音频预处理
                if self.enable_noise_reduction or self.enable_audio_enhancement:
                    logger.info("对音频进行优化预处理...")
                    enhanced_audio = self.preprocess_audio_for_recognition(audio_array, 16000)  # 假设16kHz采样率
                    
                    # 转换回字节数据
                    audio_data = enhanced_audio.tobytes()
                else:
                    # 即使不启用增强，也进行基本的标准化处理
                    normalized_audio = self.normalize_audio(audio_array)
                    audio_data = normalized_audio.tobytes()
                
                # 保存为PCM文件
                with open(pcm_filename, 'wb') as pcm_file:
                    pcm_file.write(audio_data)
            
            logger.info(f"音频已转换为PCM格式: {pcm_filename}")
            
            return {
                'success': True,
                'filename': pcm_filename,
                'message': f'音频已转换为PCM格式: {pcm_filename}'
            }
            
        except Exception as e:
            logger.error(f"转换PCM失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def recognize_speech(self, pcm_filename: str) -> Dict[str, Any]:
        """调用百度API进行语音识别"""
        try:
            # 读取PCM文件
            with open(pcm_filename, 'rb') as f:
                audio_data = f.read()
            
            # 将音频数据编码为base64
            import base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 构建请求数据
            payload = {
                "format": "pcm",
                "rate": self.rate,
                "channel": self.channels,
                "cuid": "ChatAgent_XPU_Voice_Recognition",
                "token": "",
                "speech": audio_base64,
                "len": len(audio_data)
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            logger.info("正在调用百度语音识别API...")
            
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                timeout=30
            )
            
            # 解析响应
            result = response.json()
            
            if result.get('err_no') == 0:
                recognized_text = result.get('result', [''])[0]
                logger.info(f"识别成功: {recognized_text}")
                
                return {
                    'success': True,
                    'text': recognized_text,
                    'confidence': result.get('confidence', 0),
                    'message': '语音识别成功'
                }
            else:
                error_msg = result.get('err_msg', '未知错误')
                logger.error(f"语音识别失败: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': result.get('err_no')
                }
                
        except Exception as e:
            logger.error(f"语音识别异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def recognize_voice_input(self, device_index: Optional[int] = None) -> Dict[str, Any]:
        """完整的语音输入识别流程"""
        try:
            logger.info("开始语音输入识别流程...")
            
            # 1. 检查设备
            devices_info = self.get_available_devices()
            if not devices_info['success'] or not devices_info['devices']:
                return {
                    'success': False,
                    'error': '未找到可用的音频输入设备'
                }
            
            # 2. 开始录制
            record_result = self.start_recording(device_index)
            if not record_result['success']:
                return record_result
            
            # 3. 等待录制完成
            while self.is_recording:
                time.sleep(0.1)
            
            # 4. 保存音频文件
            wav_filename = "temp_voice_input.wav"
            save_result = self.save_audio_to_file(wav_filename)
            if not save_result['success']:
                return save_result
            
            # 5. 转换为PCM格式
            pcm_filename = "temp_voice_input.pcm"
            convert_result = self.convert_to_pcm(wav_filename, pcm_filename)
            if not convert_result['success']:
                return convert_result
            
            recognition_result = None
            try:
                recognition_result = self.recognize_speech_whisper(wav_filename)
            except Exception:
                recognition_result = None
            if not recognition_result or not recognition_result.get('success'):
                recognition_result = self.recognize_speech(pcm_filename)
            
            # 7. 清理临时文件
            try:
                os.remove(wav_filename)
                os.remove(pcm_filename)
            except:
                pass
            
            return recognition_result
            
        except Exception as e:
            logger.error(f"语音输入识别流程失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    


def main():
    """主函数 - 用于测试"""
    agent = VoiceRecognitionAgent()
    
    print("=== 语音识别智能体测试 ===")
    print("1. 检测音频设备...")
    
    devices = agent.get_available_devices()
    if devices['success']:
        print(f"找到 {len(devices['devices'])} 个输入设备:")
        for device in devices['devices']:
            print(f"  - 设备 {device['index']}: {device['name']}")
    else:
        print(f"设备检测失败: {devices['error']}")
        return
    
    print("\n2. 开始语音识别测试...")
    print("请在听到提示后开始说话，系统会自动检测静音并停止录制")
    
    result = agent.test_voice_recognition()
    
    if result['success']:
        print(f"\n✅ 识别成功!")
        print(f"识别结果: {result['text']}")
        if 'confidence' in result:
            print(f"置信度: {result['confidence']}")
    else:
        print(f"\n❌ 识别失败: {result['error']}")

if __name__ == "__main__":
    main()
