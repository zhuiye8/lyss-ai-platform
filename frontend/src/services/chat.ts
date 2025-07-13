/**
 * 聊天服务API
 * 与Backend API Gateway的EINO Service集成
 */

import httpClient from './http';
import { 
  ChatMessage,
  ChatResponse,
  SendMessageRequest,
  StreamChatRequest,
  StreamChatEvent,
  ChatConfig,
  ChatTemplate,
  PromptPreset
} from '@/types/chat';
import { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/common';

export class ChatService {
  private static readonly BASE_URL = '/api/v1/chat';

  /**
   * 发送消息（非流式）
   */
  static async sendMessage(request: SendMessageRequest): Promise<ApiResponse<ChatResponse>> {
    try {
      const response = await httpClient.post<ApiResponse<ChatResponse>>(
        `${this.BASE_URL}/send`,
        request
      );
      return response;
    } catch (error) {
      console.error('发送消息失败:', error);
      throw error;
    }
  }

  /**
   * 流式聊天
   */
  static async streamChat(request: StreamChatRequest): Promise<ReadableStream> {
    try {
      const response = await httpClient.getInstance().post(
        `${this.BASE_URL}/stream`,
        request,
        {
          responseType: 'stream',
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
        }
      );

      // 返回可读流
      return new ReadableStream({
        start(controller) {
          const reader = response.data.getReader();
          
          function pump(): Promise<void> {
            return reader.read().then(({ done, value }) => {
              if (done) {
                controller.close();
                return;
              }
              controller.enqueue(value);
              return pump();
            });
          }
          
          return pump();
        }
      });
    } catch (error) {
      console.error('流式聊天失败:', error);
      throw error;
    }
  }

  /**
   * 获取聊天历史
   */
  static async getChatHistory(
    conversationId: string,
    params?: PaginationParams
  ): Promise<ApiResponse<PaginatedResponse<ChatMessage>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<ChatMessage>>>(
        `${this.BASE_URL}/conversations/${conversationId}/messages`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取聊天历史失败:', error);
      throw error;
    }
  }

  /**
   * 删除消息
   */
  static async deleteMessage(messageId: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.delete<ApiResponse<null>>(
        `${this.BASE_URL}/messages/${messageId}`
      );
      return response;
    } catch (error) {
      console.error('删除消息失败:', error);
      throw error;
    }
  }

  /**
   * 编辑消息
   */
  static async editMessage(
    messageId: string,
    content: string
  ): Promise<ApiResponse<ChatMessage>> {
    try {
      const response = await httpClient.put<ApiResponse<ChatMessage>>(
        `${this.BASE_URL}/messages/${messageId}`,
        { content }
      );
      return response;
    } catch (error) {
      console.error('编辑消息失败:', error);
      throw error;
    }
  }

  /**
   * 重新生成回答
   */
  static async regenerateResponse(
    messageId: string,
    config?: Partial<ChatConfig>
  ): Promise<ApiResponse<ChatResponse>> {
    try {
      const response = await httpClient.post<ApiResponse<ChatResponse>>(
        `${this.BASE_URL}/messages/${messageId}/regenerate`,
        { config }
      );
      return response;
    } catch (error) {
      console.error('重新生成回答失败:', error);
      throw error;
    }
  }

  /**
   * 获取可用模型列表
   */
  static async getAvailableModels(supplier?: string): Promise<ApiResponse<Array<{
    id: string;
    name: string;
    provider: string;
    type: string;
    context_length: number;
    cost_per_input_token: number;
    cost_per_output_token: number;
    description?: string;
  }>>> {
    try {
      const response = await httpClient.get<ApiResponse<Array<{
        id: string;
        name: string;
        provider: string;
        type: string;
        context_length: number;
        cost_per_input_token: number;
        cost_per_output_token: number;
        description?: string;
      }>>>(
        `${this.BASE_URL}/models`,
        { params: supplier ? { supplier } : undefined }
      );
      return response;
    } catch (error) {
      console.error('获取可用模型失败:', error);
      throw error;
    }
  }

  /**
   * 获取聊天模板
   */
  static async getChatTemplates(params?: PaginationParams & {
    category?: string;
    search?: string;
  }): Promise<ApiResponse<PaginatedResponse<ChatTemplate>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<ChatTemplate>>>(
        `${this.BASE_URL}/templates`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取聊天模板失败:', error);
      throw error;
    }
  }

  /**
   * 创建聊天模板
   */
  static async createChatTemplate(data: {
    name: string;
    description: string;
    prompt: string;
    config: ChatConfig;
    category: string;
    tags: string[];
    is_public?: boolean;
  }): Promise<ApiResponse<ChatTemplate>> {
    try {
      const response = await httpClient.post<ApiResponse<ChatTemplate>>(
        `${this.BASE_URL}/templates`,
        data
      );
      return response;
    } catch (error) {
      console.error('创建聊天模板失败:', error);
      throw error;
    }
  }

  /**
   * 获取预设提示词
   */
  static async getPromptPresets(params?: PaginationParams & {
    category?: string;
    search?: string;
  }): Promise<ApiResponse<PaginatedResponse<PromptPreset>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<PromptPreset>>>(
        `${this.BASE_URL}/prompts`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取预设提示词失败:', error);
      throw error;
    }
  }

  /**
   * 创建预设提示词
   */
  static async createPromptPreset(data: {
    title: string;
    content: string;
    category: string;
    tags: string[];
  }): Promise<ApiResponse<PromptPreset>> {
    try {
      const response = await httpClient.post<ApiResponse<PromptPreset>>(
        `${this.BASE_URL}/prompts`,
        data
      );
      return response;
    } catch (error) {
      console.error('创建预设提示词失败:', error);
      throw error;
    }
  }

  /**
   * 收藏/取消收藏提示词
   */
  static async togglePromptFavorite(promptId: string): Promise<ApiResponse<{ is_favorite: boolean }>> {
    try {
      const response = await httpClient.post<ApiResponse<{ is_favorite: boolean }>>(
        `${this.BASE_URL}/prompts/${promptId}/favorite`
      );
      return response;
    } catch (error) {
      console.error('切换提示词收藏状态失败:', error);
      throw error;
    }
  }

  /**
   * 获取聊天统计
   */
  static async getChatStats(params?: {
    start_date?: string;
    end_date?: string;
    model?: string;
    supplier?: string;
  }): Promise<ApiResponse<{
    total_messages: number;
    total_tokens: number;
    total_conversations: number;
    total_cost_usd: number;
    average_response_time_ms: number;
    model_usage: Array<{
      model: string;
      count: number;
      percentage: number;
    }>;
    daily_usage: Array<{
      date: string;
      message_count: number;
      token_count: number;
      cost_usd: number;
    }>;
  }>> {
    try {
      const response = await httpClient.get<ApiResponse<{
        total_messages: number;
        total_tokens: number;
        total_conversations: number;
        total_cost_usd: number;
        average_response_time_ms: number;
        model_usage: Array<{
          model: string;
          count: number;
          percentage: number;
        }>;
        daily_usage: Array<{
          date: string;
          message_count: number;
          token_count: number;
          cost_usd: number;
        }>;
      }>>(
        `${this.BASE_URL}/stats`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取聊天统计失败:', error);
      throw error;
    }
  }

  /**
   * 估算消息成本
   */
  static async estimateCost(data: {
    message: string;
    model: string;
    supplier: string;
  }): Promise<ApiResponse<{
    estimated_input_tokens: number;
    estimated_output_tokens: number;
    estimated_total_tokens: number;
    estimated_cost_usd: number;
  }>> {
    try {
      const response = await httpClient.post<ApiResponse<{
        estimated_input_tokens: number;
        estimated_output_tokens: number;
        estimated_total_tokens: number;
        estimated_cost_usd: number;
      }>>(
        `${this.BASE_URL}/estimate-cost`,
        data
      );
      return response;
    } catch (error) {
      console.error('估算消息成本失败:', error);
      throw error;
    }
  }

  /**
   * 导出聊天记录
   */
  static async exportChatHistory(params: {
    conversation_id?: string;
    format: 'json' | 'markdown' | 'txt';
    start_date?: string;
    end_date?: string;
  }): Promise<Blob> {
    try {
      const response = await httpClient.getInstance().get(
        `${this.BASE_URL}/export`,
        {
          params,
          responseType: 'blob',
        }
      );
      return response.data;
    } catch (error) {
      console.error('导出聊天记录失败:', error);
      throw error;
    }
  }

  /**
   * 停止流式聊天
   */
  static async stopStreaming(executionId: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/stop/${executionId}`
      );
      return response;
    } catch (error) {
      console.error('停止流式聊天失败:', error);
      throw error;
    }
  }
}