"""
请求数据模型

定义API代理层使用的请求和响应数据结构，
支持OpenAI格式的统一API接口。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色（user, assistant, system）")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者名称")


class ChatRequest(BaseModel):
    """聊天完成请求模型（OpenAI格式）"""
    model: str = Field(..., description="使用的模型名称")
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    temperature: Optional[float] = Field(1.0, ge=0, le=2, description="采样温度")
    top_p: Optional[float] = Field(1.0, ge=0, le=1, description="核采样参数")
    n: Optional[int] = Field(1, ge=1, le=10, description="生成的回复数量")
    stream: Optional[bool] = Field(False, description="是否使用流式响应")
    stop: Optional[Union[str, List[str]]] = Field(None, description="停止序列")
    max_tokens: Optional[int] = Field(None, ge=1, description="最大生成token数")
    presence_penalty: Optional[float] = Field(0, ge=-2, le=2, description="存在惩罚")
    frequency_penalty: Optional[float] = Field(0, ge=-2, le=2, description="频率惩罚")
    logit_bias: Optional[Dict[str, float]] = Field(None, description="logit偏置")
    user: Optional[str] = Field(None, description="用户标识")
    
    class Config:
        schema_extra = {
            "example": {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "你好，请介绍一下你自己"}
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }
        }


class ProxyRequest(BaseModel):
    """内部代理请求模型"""
    original_request: ChatRequest = Field(..., description="原始请求")
    channel_id: int = Field(..., description="选择的Channel ID")
    provider_id: str = Field(..., description="供应商ID")
    params: Dict[str, Any] = Field(..., description="转换后的供应商参数")
    headers: Optional[Dict[str, str]] = Field(None, description="请求头")
    
    class Config:
        schema_extra = {
            "example": {
                "original_request": {
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hello"}]
                },
                "channel_id": 1,
                "provider_id": "openai",
                "params": {
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False
                }
            }
        }