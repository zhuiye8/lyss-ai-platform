"""
响应数据模型

定义API代理层返回的响应数据结构，
统一为OpenAI格式的响应格式。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatChoice(BaseModel):
    """聊天选择模型"""
    index: int = Field(..., description="选择索引")
    message: Dict[str, Any] = Field(..., description="回复消息")
    finish_reason: Optional[str] = Field(None, description="结束原因")


class ChatUsage(BaseModel):
    """使用统计模型"""
    prompt_tokens: int = Field(..., description="输入token数")
    completion_tokens: int = Field(..., description="输出token数")
    total_tokens: int = Field(..., description="总token数")


class ChatResponse(BaseModel):
    """聊天完成响应模型（OpenAI格式）"""
    id: str = Field(..., description="响应ID")
    object: str = Field("chat.completion", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[ChatChoice] = Field(..., description="回复选择列表")
    usage: ChatUsage = Field(..., description="使用统计")
    system_fingerprint: Optional[str] = Field(None, description="系统指纹")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-3.5-turbo-0613",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "你好！我是Claude，一个AI助手。"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 9,
                    "completion_tokens": 12,
                    "total_tokens": 21
                }
            }
        }


class StreamChoice(BaseModel):
    """流式选择模型"""
    index: int = Field(..., description="选择索引")
    delta: Dict[str, Any] = Field(..., description="增量数据")
    finish_reason: Optional[str] = Field(None, description="结束原因")


class StreamResponse(BaseModel):
    """流式响应模型"""
    id: str = Field(..., description="响应ID")
    object: str = Field("chat.completion.chunk", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[StreamChoice] = Field(..., description="流式选择列表")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "chatcmpl-123",
                "object": "chat.completion.chunk",
                "created": 1677652288,
                "model": "gpt-3.5-turbo-0613",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "你好"
                        },
                        "finish_reason": None
                    }
                ]
            }
        }


class ProxyResponse(BaseModel):
    """内部代理响应模型"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    channel_id: int = Field(..., description="使用的Channel ID")
    provider_id: str = Field(..., description="供应商ID")
    response_time: float = Field(..., description="响应时间（毫秒）")
    tokens_used: int = Field(0, description="使用的token数")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "id": "chatcmpl-123",
                    "choices": [{"message": {"content": "Hello!"}}]
                },
                "channel_id": 1,
                "provider_id": "openai",
                "response_time": 234.5,
                "tokens_used": 21
            }
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: Dict[str, Any] = Field(..., description="错误信息")
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "message": "Invalid API key provided",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key"
                }
            }
        }