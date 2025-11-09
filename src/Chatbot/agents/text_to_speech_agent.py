#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音合成智能体
将文本转换为语音，支持多种音频格式和参数配置
使用百度TTS API实现语音合成功能
"""

import os
import json
import time
import base64
import requests
from typing import Optional, Dict, Any, Union, Generator
from config.settings import settings
import logging
from pathlib import Path
import asyncio

"""
所有参数统一从项目根目录 .env 通过 config.settings 加载
"""

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextToSpeechAgent:
    """语音合成智能体"""
    
    def __init__(self):
        """初始化语音合成智能体"""
        # 从settings读取API配置
        self.api_key = settings.TTS_API_KEY.strip()
        self.api_url = settings.TTS_API_URL
        
        # Token缓存（保留以兼容现有代码）
        self._access_token = None
        self._token_expires_at = 0
        
        # 默认TTS参数 - 从settings读取
        self.default_params = {
            'lan': settings.TTS_LANG,  # 语言，固定值zh
            'ctp': '1',  # 客户端类型，web端固定值1
            'spd': settings.TTS_SPEED,  # 语速 (0-15)
            'pit': settings.TTS_PITCH,  # 音调 (0-15)
            'vol': settings.TTS_VOLUME,  # 音量 (0-15)
            'per': settings.TTS_PER,  # 发音人选择
            'aue': settings.TTS_AUE  # 音频格式
        }
        
        # 输出目录
        self.output_dir = Path(settings.TTS_OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        
        # 验证API密钥
        if not self.api_key:
            logger.warning("未找到TTS_API_KEY，请在.env文件中配置")
        else:
            logger.info(f"TTS API密钥加载成功，密钥长度: {len(self.api_key)}")
        

    def get_access_token(self) -> Optional[str]:
        """
        使用 API_KEY 和 SECRET_KEY 生成鉴权签名（Access Token）
        
        Returns:
            access_token，或是None(如果错误)
        """
        try:
            # 检查缓存的token是否还有效
            current_time = time.time()
            if self._access_token and current_time < self._token_expires_at:
                return self._access_token

            
            url = "https://aip.baidubce.com/oauth/2.0/token"


            
            response = requests.post(url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get("access_token")
                expires_in = result.get("expires_in", 2592000)  # 默认30天
                
                if access_token:
                    # 缓存token，提前5分钟过期以确保安全
                    self._access_token = access_token
                    self._token_expires_at = current_time + expires_in - 300
                    logger.info(f"获取access_token成功，有效期: {expires_in}秒")
                    return access_token
                else:
                    logger.error(f"获取access_token失败: {result}")
                    return None
            else:
                logger.error(f"请求access_token失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取access_token异常: {str(e)}")
            return None
    
    def synthesize_speech(
        self, 
        text: str, 
        output_filename: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        将文本转换为语音
        
        Args:
            text: 要转换的文本
            output_filename: 输出文件名（可选）
            **kwargs: 其他TTS参数
        
        Returns:
            包含合成结果的字典
        """
        try:
            if not text or not text.strip():
                return {
                    'success': False,
                    'error': '文本内容不能为空',
                    'error_type': 'invalid_input'
                }
            
            # 获取访问令牌
            access_token = None
            
            # 直接使用TTS_API_KEY
            if self.api_key:
                access_token = self.api_key
            else:
                return {
                    'success': False,
                    'error': '未找到TTS_API_KEY配置',
                    'error_type': 'missing_api_key'
                }
            
            # 准备请求参数
            
            # 合并参数
            params = {**self.default_params, **kwargs}
            params['tex'] = text.strip()
            params['tok'] = access_token
            params['cuid'] = 'chatbot_user'  # 用户唯一标识
            
            logger.info(f"开始语音合成，文本长度: {len(text)}")
            logger.info(f"使用API URL: {self.api_url}")
            logger.info(f"请求参数: {params}")
            
            # 使用GET方式发送请求（百度TTS推荐方式）
            import urllib.parse
            
            # 对文本进行URL编码
            encoded_text = urllib.parse.quote(text.strip(), safe='')
            params['tex'] = encoded_text
            
            # 构建GET请求URL
            query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
            full_url = f"{self.api_url}?{query_string}"
            
            logger.info(f"完整请求URL: {full_url}")
            
            # 发送GET请求
            response = requests.get(full_url, timeout=30)
            
            if response.status_code == 200:
                # 检查响应内容类型
                content_type = response.headers.get('content-type', '')
                
                if 'audio' in content_type or 'application/octet-stream' in content_type:
                    # 直接返回音频数据
                    audio_data = response.content
                    return self._save_audio_data(audio_data, output_filename, params)
                else:
                    # 可能是错误响应
                    try:
                        error_data = response.json()
                        return {
                            'success': False,
                            'error': f"API错误: {error_data}",
                            'error_type': 'api_error',
                            'response_data': error_data
                        }
                    except:
                        return {
                            'success': False,
                            'error': f"未知响应格式: {response.text[:200]}",
                            'error_type': 'invalid_response'
                        }
            else:
                return {
                    'success': False,
                    'error': f'HTTP错误: {response.status_code} - {response.text[:200]}',
                    'error_type': 'http_error',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'timeout'
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'network_error'
            }
        except Exception as e:
            error_msg = f"语音合成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'unknown_error'
            }
    
    def synthesize_speech_stream(
        self, 
        text: str, 
        chunk_size: int = 1024,
        **kwargs
    ) -> Generator[bytes, None, None]:
        """
        流式语音合成
        
        Args:
            text: 要转换的文本
            chunk_size: 数据块大小
            **kwargs: 其他TTS参数
        
        Yields:
            音频数据块
        """
        try:
            # 使用标准合成方法获取完整音频
            result = self.synthesize_speech(text, **kwargs)
            
            if result['success']:
                # 读取生成的音频文件并流式返回
                audio_file = result.get('audio_file')
                if audio_file and os.path.exists(audio_file):
                    with open(audio_file, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                else:
                    # 如果有音频数据但没有文件，直接返回数据
                    audio_data = result.get('audio_data')
                    if audio_data:
                        for i in range(0, len(audio_data), chunk_size):
                            yield audio_data[i:i + chunk_size]
            else:
                logger.error(f"语音合成失败: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"流式语音合成失败: {str(e)}")
            return

    async def synthesize_speech_stream_async(
        self, 
        text: str, 
        chunk_size: int = 1024,
        **kwargs
    ) -> Generator[bytes, None, None]:
        """
        异步流式语音合成
        
        Args:
            text: 要转换的文本
            chunk_size: 数据块大小
            **kwargs: 其他TTS参数
        
        Yields:
            音频数据块
        """
        # 在异步环境中调用同步方法
        loop = asyncio.get_event_loop()
        
        def sync_generator():
            return self.synthesize_speech_stream(text, chunk_size, **kwargs)
        
        # 在线程池中执行同步生成器
        generator = await loop.run_in_executor(None, sync_generator)
        
        for chunk in generator:
            yield chunk

    
    def _handle_direct_audio(self, response_data: Dict, output_filename: Optional[str], params: Dict) -> Dict[str, Any]:
        """处理直接返回的音频数据"""
        audio_data = response_data.get('audio_data')
        if not audio_data:
            return {
                'success': False,
                'error': '响应中未找到音频数据',
                'error_type': 'invalid_response'
            }
        
        return self._save_audio_file(audio_data, output_filename, params)
    
    def _handle_response_data(self, response_data: Dict, output_filename: Optional[str], params: Dict) -> Dict[str, Any]:
        """处理其他格式的响应数据"""
        # 尝试直接将响应作为音频数据处理
        if isinstance(response_data, dict) and len(response_data) == 1:
            # 可能是包含音频数据的单键字典
            audio_data = list(response_data.values())[0]
            if isinstance(audio_data, str):
                return self._save_audio_file(audio_data, output_filename, params)
        
        # 记录响应以便调试
        logger.info(f"收到未知格式响应: {response_data}")
        
        return {
            'success': False,
            'error': '未知的响应格式',
            'error_type': 'invalid_response',
            'response_data': response_data
        }
    

    
    def _save_audio_data(self, audio_data: bytes, output_filename: Optional[str], params: Dict) -> Dict[str, Any]:
        """保存音频数据"""
        output_path = None
        try:
            # 生成文件名
            if not output_filename:
                timestamp = int(time.time())
                format_ext = params.get('format', 'mp3-16k').split('-')[0]
                output_filename = f"tts_output_{timestamp}.{format_ext}"
            
            output_path = self.output_dir / output_filename
            
            # 直接使用音频数据（已经是bytes格式）
            audio_bytes = audio_data
            
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            
            file_size = output_path.stat().st_size
            logger.info(f"语音合成成功，文件保存至: {output_path}，大小: {file_size} bytes")
            
            return {
                'success': True,
                'message': '语音合成成功',
                'audio_file': str(output_path),
                'audio_data': audio_bytes,
                'file_size': file_size,
                'parameters': params
            }
            
        except Exception as e:
            error_msg = f"保存音频文件失败: {str(e)}"
            logger.error(error_msg)
            
            # 如果文件创建失败，尝试清理
            if output_path and output_path.exists():
                try:
                    output_path.unlink()
                    logger.info(f"清理失败的音频文件: {output_path}")
                except Exception as cleanup_e:
                    logger.warning(f"清理失败音频文件时出错: {cleanup_e}")
            
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'file_save_error'
            }
    
    def synthesize_with_custom_params(
        self,
        text: str,
        format: str = 'mp3',
        lang: str = 'zh',
        speed: int = 5,
        pitch: int = 5,
        volume: int = 5,
        per: int = 0,
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用自定义参数进行语音合成
        
        Args:
            text: 要合成的文本
            format: 音频格式 (mp3, wav, pcm)
            lang: 语言 (zh)
            speed: 语速 (0-15)
            pitch: 音调 (0-15)
            volume: 音量 (0-15)
            per: 发音人 (0=度小美, 1=度小宇, 3=度逍遥, 4=度丫丫)
            output_filename: 输出文件名
        
        Returns:
            合成结果字典
        """
        # 映射格式参数
        aue_map = {
            'mp3': 3,
            'pcm': 4,
            'wav': 6
        }
        
        custom_params = {
            'aue': aue_map.get(format, 3),
            'lan': lang,
            'spd': speed,
            'pit': pitch,
            'vol': volume,
            'per': per
        }
        
        return self.synthesize_speech(text, output_filename, **custom_params)
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """获取支持的音频格式"""
        return {
            'success': True,
            'formats': {
                'mp3': {'aue': 3, 'description': 'MP3格式，默认16k采样率'},
                'pcm': {'aue': 4, 'description': 'PCM格式，16k采样率'},
                'wav': {'aue': 6, 'description': 'WAV格式，16k采样率'}
            },
            'voices': {
                0: '度小美（女声）',
                1: '度小宇（男声）',
                3: '度逍遥（情感男声）',
                4: '度丫丫（情感女声）'
            }
        }
    
