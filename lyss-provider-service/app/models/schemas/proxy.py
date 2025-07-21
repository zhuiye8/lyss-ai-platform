"""
API透明代理相关的数据模型

定义聊天完成请求和响应的Pydantic模型，兼容OpenAI API格式。
支持标准请求和流式响应格式。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class MessageRole(str, Enum):
    """消息角色枚举"""
    system = "system"
    user = "user"
    assistant = "assistant"
    function = "function"
    tool = "tool"


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者名称")
    function_call: Optional[Dict[str, Any]] = Field(None, description="函数调用信息")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用列表")
    tool_call_id: Optional[str] = Field(None, description="工具调用ID")


class FunctionCall(BaseModel):
    """函数调用模型"""
    name: str = Field(..., description="函数名称")
    arguments: str = Field(..., description="函数参数（JSON字符串）")


class ToolCall(BaseModel):
    """工具调用模型"""
    id: str = Field(..., description="调用ID")
    type: str = Field("function", description="调用类型")
    function: FunctionCall = Field(..., description="函数调用详情")


class Function(BaseModel):
    """函数定义模型"""
    name: str = Field(..., description="函数名称")
    description: Optional[str] = Field(None, description="函数描述")
    parameters: Dict[str, Any] = Field(..., description="函数参数模式")


class Tool(BaseModel):
    """工具定义模型"""
    type: str = Field("function", description="工具类型")
    function: Function = Field(..., description="函数定义")


class ChatRequest(BaseModel):
    """聊天完成请求模型"""
    model: str = Field(..., description="使用的模型名称")
    messages: List[ChatMessage] = Field(..., description="对话消息列表", min_items=1)
    temperature: Optional[float] = Field(1.0, description="生成温度", ge=0.0, le=2.0)
    top_p: Optional[float] = Field(1.0, description="核心采样参数", ge=0.0, le=1.0)
    n: Optional[int] = Field(1, description="生成的回复数量", ge=1, le=10)
    stream: Optional[bool] = Field(False, description="是否流式响应")
    stop: Optional[Union[str, List[str]]] = Field(None, description="停止序列")
    max_tokens: Optional[int] = Field(None, description="最大生成tokens", ge=1)
    presence_penalty: Optional[float] = Field(0.0, description="存在惩罚", ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(0.0, description="频率惩罚", ge=-2.0, le=2.0)
    logit_bias: Optional[Dict[str, float]] = Field(None, description="logit偏置")
    user: Optional[str] = Field(None, description="用户标识")
    functions: Optional[List[Function]] = Field(None, description="可用函数列表")
    function_call: Optional[Union[str, Dict[str, str]]] = Field(None, description="函数调用控制")
    tools: Optional[List[Tool]] = Field(None, description="可用工具列表")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(None, description="工具选择控制")
    response_format: Optional[Dict[str, str]] = Field(None, description="响应格式")
    seed: Optional[int] = Field(None, description="随机种子")
    
    @validator('messages')
    def validate_messages(cls, v):
        """验证消息列表"""
        if not v:
            raise ValueError("消息列表不能为空")
        return v
    
    @validator('model')
    def validate_model(cls, v):
        """验证模型名称"""
        if not v or not v.strip():
            raise ValueError("模型名称不能为空")
        return v.strip()


class TokenUsage(BaseModel):
    """Token使用情况模型"""
    prompt_tokens: int = Field(..., description="输入tokens数量")
    completion_tokens: int = Field(..., description="生成tokens数量")
    total_tokens: int = Field(..., description="总tokens数量")


class Choice(BaseModel):
    """聊天完成选择模型"""
    index: int = Field(..., description="选择索引")
    message: ChatMessage = Field(..., description="生成的消息")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    logprobs: Optional[Dict[str, Any]] = Field(None, description="log概率信息")


class ChatResponse(BaseModel):
    """聊天完成响应模型"""
    id: str = Field(..., description="响应ID")
    object: str = Field("chat.completion", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[Choice] = Field(..., description="生成选择列表")
    usage: TokenUsage = Field(..., description="Token使用情况")
    system_fingerprint: Optional[str] = Field(None, description="系统指纹")


class StreamChoice(BaseModel):
    """流式响应选择模型"""
    index: int = Field(..., description="选择索引")
    delta: Dict[str, Any] = Field(..., description="增量消息内容")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    logprobs: Optional[Dict[str, Any]] = Field(None, description="log概率信息")


class ChatStreamResponse(BaseModel):
    """流式聊天完成响应模型"""
    id: str = Field(..., description="响应ID")
    object: str = Field("chat.completion.chunk", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[StreamChoice] = Field(..., description="流式选择列表")
    system_fingerprint: Optional[str] = Field(None, description="系统指纹")


class ProxyRequestLog(BaseModel):
    """代理请求日志模型"""
    request_id: str = Field(..., description="请求ID")
    tenant_id: str = Field(..., description="租户ID")
    model: str = Field(..., description="请求模型")
    channel_id: Optional[str] = Field(None, description="使用的渠道ID")
    provider_id: Optional[str] = Field(None, description="供应商ID")
    request_time: float = Field(..., description="请求时间戳")
    response_time: Optional[float] = Field(None, description="响应时间戳")
    duration: Optional[float] = Field(None, description="处理耗时（毫秒）")
    status: str = Field(..., description="请求状态")
    prompt_tokens: Optional[int] = Field(None, description="输入tokens")
    completion_tokens: Optional[int] = Field(None, description="生成tokens")
    total_tokens: Optional[int] = Field(None, description="总tokens")
    error_message: Optional[str] = Field(None, description="错误消息")
    retry_count: Optional[int] = Field(0, description="重试次数")
    load_balancer_algorithm: Optional[str] = Field(None, description="负载均衡算法")


class ErrorDetail(BaseModel):
    """错误详情模型"""
    message: str = Field(..., description="错误消息")
    type: str = Field(..., description="错误类型")
    code: Optional[str] = Field(None, description="错误代码")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: ErrorDetail = Field(..., description="错误详情")


class ProxyStats(BaseModel):
    """代理统计信息模型"""
    tenant_id: str = Field(..., description="租户ID")
    total_requests: int = Field(..., description="总请求数")
    successful_requests: int = Field(..., description="成功请求数")
    failed_requests: int = Field(..., description="失败请求数")
    avg_response_time: float = Field(..., description="平均响应时间")
    total_tokens_used: int = Field(..., description="总token使用量")
    model_usage: Dict[str, int] = Field(..., description="模型使用统计")
    channel_usage: Dict[str, int] = Field(..., description="渠道使用统计")
    error_types: Dict[str, int] = Field(..., description="错误类型统计")
    time_period: str = Field(..., description="统计时间段")
    generated_at: str = Field(..., description="生成时间")


class HealthStatus(BaseModel):
    """健康状态模型"""
    status: str = Field(..., description="健康状态")
    timestamp: int = Field(..., description="检查时间戳")
    version: str = Field(..., description="服务版本")
    channels: Dict[str, Any] = Field(..., description="渠道状态")
    proxy_handler: Dict[str, str] = Field(..., description="代理处理器状态")
    error: Optional[str] = Field(None, description="错误信息")


class ModelInfo(BaseModel):
    """模型信息模型"""
    id: str = Field(..., description="模型ID")
    object: str = Field("model", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    owned_by: str = Field(..., description="拥有者")
    permission: List[str] = Field(default_factory=list, description="权限列表")
    root: str = Field(..., description="根模型")
    parent: Optional[str] = Field(None, description="父模型")


class ModelListResponse(BaseModel):
    """模型列表响应模型"""
    object: str = Field("list", description="对象类型")
    data: List[ModelInfo] = Field(..., description="模型列表")