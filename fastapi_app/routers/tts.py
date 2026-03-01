#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS (Text-to-Speech) API路由
提供语音合成服务，支持流式音频输出
"""

import os
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging

from src.Chatbot.core.providers import get_tts_agent

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/tts", tags=["语音合成"])

class TTSRequest(BaseModel):
    """TTS请求模型"""
    text: str = Field(..., description="要转换为语音的文本", min_length=1, max_length=5000)
    format: Optional[str] = Field("mp3-16k", description="音频格式")
    lang: Optional[str] = Field("zh", description="语言")
    speed: Optional[int] = Field(5, description="语速 (0-15)", ge=0, le=15)
    pitch: Optional[int] = Field(5, description="音调 (0-15)", ge=0, le=15)
    volume: Optional[int] = Field(5, description="音量 (0-15)", ge=0, le=15)
    enable_subtitle: Optional[int] = Field(0, description="是否启用字幕 (0或1)", ge=0, le=1)


class TTSStreamRequest(BaseModel):
    """TTS流式请求模型"""
    text: str = Field(..., description="要转换为语音的文本", min_length=1, max_length=5000)
    chunk_size: Optional[int] = Field(1024, description="音频块大小", ge=256, le=8192)
    format: Optional[str] = Field("mp3-16k", description="音频格式")
    lang: Optional[str] = Field("zh", description="语言")
    speed: Optional[int] = Field(5, description="语速 (0-15)", ge=0, le=15)
    pitch: Optional[int] = Field(5, description="音调 (0-15)", ge=0, le=15)
    volume: Optional[int] = Field(5, description="音量 (0-15)", ge=0, le=15)
    enable_subtitle: Optional[int] = Field(0, description="是否启用字幕 (0或1)", ge=0, le=1)


class TTSSegmentRequest(BaseModel):
    """TTS分段流式请求模型"""
    text: str = Field(..., description="要转换为语音的文本", min_length=1, max_length=10000)
    segment_length: Optional[int] = Field(100, description="每段文本长度", ge=10, le=500)
    chunk_size: Optional[int] = Field(1024, description="音频块大小", ge=256, le=8192)
    format: Optional[str] = Field("mp3-16k", description="音频格式")
    lang: Optional[str] = Field("zh", description="语言")
    speed: Optional[int] = Field(5, description="语速 (0-15)", ge=0, le=15)
    pitch: Optional[int] = Field(5, description="音调 (0-15)", ge=0, le=15)
    volume: Optional[int] = Field(5, description="音量 (0-15)", ge=0, le=15)
    enable_subtitle: Optional[int] = Field(0, description="是否启用字幕 (0或1)", ge=0, le=1)


def _require_tts_agent():
    agent = get_tts_agent()
    if agent is None:
        raise HTTPException(status_code=503, detail="TTS服务暂不可用")
    return agent


@router.get("/status/")
async def get_tts_status():
    """获取TTS服务状态"""
    try:
        agent = _require_tts_agent()
        formats = agent.get_supported_formats()
        
        return {
            "status": "available",
            "message": "TTS服务正常运行",
            "api_configured": bool(agent.api_key),
            "supported_formats": formats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取TTS状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS服务状态检查失败: {str(e)}")


@router.post("/synthesize/")
async def synthesize_speech(request: TTSRequest):
    """
    语音合成 - 返回完整音频文件
    """
    try:
        agent = _require_tts_agent()
        
        # 执行语音合成
        result = agent.synthesize_speech(
            text=request.text,
            format=request.format,
            lang=request.lang,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume,
            enable_subtitle=request.enable_subtitle
        )
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "output_file": result.get('output_file'),
                "file_size": result.get('file_size'),
                "parameters": result.get('parameters')
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"语音合成失败: {result['error']}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音合成API错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音合成服务错误: {str(e)}")


@router.post("/stream/")
async def synthesize_speech_stream(request: TTSStreamRequest):
    """
    流式语音合成 - 返回音频流
    """
    try:
        agent = _require_tts_agent()
        
        def generate_audio_stream():
            """生成音频流"""
            try:
                for chunk in agent.synthesize_speech_stream(
                    text=request.text,
                    chunk_size=request.chunk_size,
                    format=request.format,
                    lang=request.lang,
                    speed=request.speed,
                    pitch=request.pitch,
                    volume=request.volume,
                    enable_subtitle=request.enable_subtitle
                ):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"流式音频生成错误: {str(e)}")
                yield b''
        
        # 根据格式设置Content-Type
        content_type = "audio/mpeg"  # 默认MP3
        if "wav" in request.format.lower():
            content_type = "audio/wav"
        elif "pcm" in request.format.lower():
            content_type = "audio/pcm"
        
        return StreamingResponse(
            generate_audio_stream(),
            media_type=content_type,
            headers={
                "Content-Disposition": "inline; filename=tts_stream.mp3",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        logger.error(f"流式语音合成API错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"流式语音合成服务错误: {str(e)}")


@router.post("/stream-async/")
async def synthesize_speech_stream_async(request: TTSStreamRequest):
    """
    异步流式语音合成 - 返回音频流
    """
    try:
        agent = _require_tts_agent()
        
        async def generate_audio_stream_async():
            """异步生成音频流"""
            try:
                async for chunk in agent.synthesize_speech_stream_async(
                    text=request.text,
                    chunk_size=request.chunk_size,
                    format=request.format,
                    lang=request.lang,
                    speed=request.speed,
                    pitch=request.pitch,
                    volume=request.volume,
                    enable_subtitle=request.enable_subtitle
                ):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"异步流式音频生成错误: {str(e)}")
                yield b''
        
        # 根据格式设置Content-Type
        content_type = "audio/mpeg"  # 默认MP3
        if "wav" in request.format.lower():
            content_type = "audio/wav"
        elif "pcm" in request.format.lower():
            content_type = "audio/pcm"
        
        return StreamingResponse(
            generate_audio_stream_async(),
            media_type=content_type,
            headers={
                "Content-Disposition": "inline; filename=tts_async_stream.mp3",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        logger.error(f"异步流式语音合成API错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"异步流式语音合成服务错误: {str(e)}")


@router.post("/stream-segments/")
async def synthesize_speech_segments_stream(request: TTSSegmentRequest):
    """
    分段流式语音合成 - 将长文本分段处理并返回音频流
    """
    try:
        agent = _require_tts_agent()
        
        def generate_segment_audio_stream():
            """生成分段音频流"""
            try:
                for chunk in agent.synthesize_text_segments_stream(
                    text=request.text,
                    segment_length=request.segment_length,
                    chunk_size=request.chunk_size,
                    format=request.format,
                    lang=request.lang,
                    speed=request.speed,
                    pitch=request.pitch,
                    volume=request.volume,
                    enable_subtitle=request.enable_subtitle
                ):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"分段流式音频生成错误: {str(e)}")
                yield b''
        
        # 根据格式设置Content-Type
        content_type = "audio/mpeg"  # 默认MP3
        if "wav" in request.format.lower():
            content_type = "audio/wav"
        elif "pcm" in request.format.lower():
            content_type = "audio/pcm"
        
        return StreamingResponse(
            generate_segment_audio_stream(),
            media_type=content_type,
            headers={
                "Content-Disposition": "inline; filename=tts_segment_stream.mp3",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        logger.error(f"分段流式语音合成API错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分段流式语音合成服务错误: {str(e)}")


@router.get("/formats/")
async def get_supported_formats():
    """获取支持的音频格式"""
    try:
        agent = _require_tts_agent()
        return agent.get_supported_formats()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取支持格式失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取支持格式失败: {str(e)}")
