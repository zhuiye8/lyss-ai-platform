/**
 * 对话服务API
 * 与Backend API Gateway的EINO Service集成
 */

import httpClient from './http';
import { 
  Conversation,
  ChatMessage,
  CreateConversationRequest,
  UpdateConversationRequest,
  ConversationFilters,
  ConversationStats
} from '@/types/chat';
import { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/common';

export class ConversationService {
  private static readonly BASE_URL = '/api/v1/conversations';

  /**
   * 获取对话列表
   */
  static async getConversations(params?: PaginationParams & ConversationFilters): Promise<ApiResponse<PaginatedResponse<Conversation>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<Conversation>>>(
        this.BASE_URL,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取对话列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取单个对话详情
   */
  static async getConversation(id: string): Promise<ApiResponse<Conversation>> {
    try {
      const response = await httpClient.get<ApiResponse<Conversation>>(
        `${this.BASE_URL}/${id}`
      );
      return response;
    } catch (error) {
      console.error('获取对话详情失败:', error);
      throw error;
    }
  }

  /**
   * 创建对话
   */
  static async createConversation(data: CreateConversationRequest): Promise<ApiResponse<Conversation>> {
    try {
      const response = await httpClient.post<ApiResponse<Conversation>>(
        this.BASE_URL,
        data
      );
      return response;
    } catch (error) {
      console.error('创建对话失败:', error);
      throw error;
    }
  }

  /**
   * 更新对话
   */
  static async updateConversation(
    id: string,
    data: UpdateConversationRequest
  ): Promise<ApiResponse<Conversation>> {
    try {
      const response = await httpClient.put<ApiResponse<Conversation>>(
        `${this.BASE_URL}/${id}`,
        data
      );
      return response;
    } catch (error) {
      console.error('更新对话失败:', error);
      throw error;
    }
  }

  /**
   * 删除对话
   */
  static async deleteConversation(id: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.delete<ApiResponse<null>>(
        `${this.BASE_URL}/${id}`
      );
      return response;
    } catch (error) {
      console.error('删除对话失败:', error);
      throw error;
    }
  }

  /**
   * 获取对话消息
   */
  static async getConversationMessages(
    id: string,
    params?: PaginationParams
  ): Promise<ApiResponse<PaginatedResponse<ChatMessage>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<ChatMessage>>>(
        `${this.BASE_URL}/${id}/messages`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取对话消息失败:', error);
      throw error;
    }
  }

  /**
   * 归档对话
   */
  static async archiveConversation(id: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/${id}/archive`
      );
      return response;
    } catch (error) {
      console.error('归档对话失败:', error);
      throw error;
    }
  }

  /**
   * 取消归档对话
   */
  static async unarchiveConversation(id: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/${id}/unarchive`
      );
      return response;
    } catch (error) {
      console.error('取消归档对话失败:', error);
      throw error;
    }
  }

  /**
   * 分享对话
   */
  static async shareConversation(id: string, options?: {
    is_public?: boolean;
    expires_at?: string;
    password?: string;
  }): Promise<ApiResponse<{
    share_id: string;
    share_url: string;
    expires_at?: string;
  }>> {
    try {
      const response = await httpClient.post<ApiResponse<{
        share_id: string;
        share_url: string;
        expires_at?: string;
      }>>(
        `${this.BASE_URL}/${id}/share`,
        options
      );
      return response;
    } catch (error) {
      console.error('分享对话失败:', error);
      throw error;
    }
  }

  /**
   * 取消分享对话
   */
  static async unshareConversation(id: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/${id}/unshare`
      );
      return response;
    } catch (error) {
      console.error('取消分享对话失败:', error);
      throw error;
    }
  }

  /**
   * 复制对话
   */
  static async duplicateConversation(
    id: string,
    options?: {
      title?: string;
      include_messages?: boolean;
    }
  ): Promise<ApiResponse<Conversation>> {
    try {
      const response = await httpClient.post<ApiResponse<Conversation>>(
        `${this.BASE_URL}/${id}/duplicate`,
        options
      );
      return response;
    } catch (error) {
      console.error('复制对话失败:', error);
      throw error;
    }
  }

  /**
   * 批量删除对话
   */
  static async batchDeleteConversations(ids: string[]): Promise<ApiResponse<{
    deleted_count: number;
    failed_ids: string[];
  }>> {
    try {
      const response = await httpClient.post<ApiResponse<{
        deleted_count: number;
        failed_ids: string[];
      }>>(
        `${this.BASE_URL}/batch-delete`,
        { conversation_ids: ids }
      );
      return response;
    } catch (error) {
      console.error('批量删除对话失败:', error);
      throw error;
    }
  }

  /**
   * 批量归档对话
   */
  static async batchArchiveConversations(ids: string[]): Promise<ApiResponse<{
    archived_count: number;
    failed_ids: string[];
  }>> {
    try {
      const response = await httpClient.post<ApiResponse<{
        archived_count: number;
        failed_ids: string[];
      }>>(
        `${this.BASE_URL}/batch-archive`,
        { conversation_ids: ids }
      );
      return response;
    } catch (error) {
      console.error('批量归档对话失败:', error);
      throw error;
    }
  }

  /**
   * 搜索对话
   */
  static async searchConversations(params: {
    query: string;
    filters?: ConversationFilters;
    highlight?: boolean;
  } & PaginationParams): Promise<ApiResponse<PaginatedResponse<Conversation & {
    highlights?: {
      title?: string[];
      content?: string[];
    };
    relevance_score?: number;
  }>>> {
    try {
      const response = await httpClient.post<ApiResponse<PaginatedResponse<Conversation & {
        highlights?: {
          title?: string[];
          content?: string[];
        };
        relevance_score?: number;
      }>>>(
        `${this.BASE_URL}/search`,
        params
      );
      return response;
    } catch (error) {
      console.error('搜索对话失败:', error);
      throw error;
    }
  }

  /**
   * 获取对话统计
   */
  static async getConversationStats(params?: {
    start_date?: string;
    end_date?: string;
    group_by?: 'day' | 'week' | 'month';
  }): Promise<ApiResponse<ConversationStats>> {
    try {
      const response = await httpClient.get<ApiResponse<ConversationStats>>(
        `${this.BASE_URL}/stats`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取对话统计失败:', error);
      throw error;
    }
  }

  /**
   * 导出对话
   */
  static async exportConversation(
    id: string,
    format: 'json' | 'markdown' | 'txt' | 'pdf'
  ): Promise<Blob> {
    try {
      const response = await httpClient.getInstance().get(
        `${this.BASE_URL}/${id}/export`,
        {
          params: { format },
          responseType: 'blob',
        }
      );
      return response.data;
    } catch (error) {
      console.error('导出对话失败:', error);
      throw error;
    }
  }

  /**
   * 批量导出对话
   */
  static async exportConversations(params: {
    conversation_ids?: string[];
    filters?: ConversationFilters;
    format: 'json' | 'zip';
  }): Promise<Blob> {
    try {
      const response = await httpClient.getInstance().post(
        `${this.BASE_URL}/export`,
        params,
        {
          responseType: 'blob',
        }
      );
      return response.data;
    } catch (error) {
      console.error('批量导出对话失败:', error);
      throw error;
    }
  }

  /**
   * 获取对话标签
   */
  static async getConversationTags(): Promise<ApiResponse<Array<{
    tag: string;
    count: number;
  }>>> {
    try {
      const response = await httpClient.get<ApiResponse<Array<{
        tag: string;
        count: number;
      }>>>(
        `${this.BASE_URL}/tags`
      );
      return response;
    } catch (error) {
      console.error('获取对话标签失败:', error);
      throw error;
    }
  }

  /**
   * 自动生成对话标题
   */
  static async generateTitle(id: string): Promise<ApiResponse<{ title: string }>> {
    try {
      const response = await httpClient.post<ApiResponse<{ title: string }>>(
        `${this.BASE_URL}/${id}/generate-title`
      );
      return response;
    } catch (error) {
      console.error('生成对话标题失败:', error);
      throw error;
    }
  }

  /**
   * 获取相关对话推荐
   */
  static async getRelatedConversations(
    id: string,
    limit?: number
  ): Promise<ApiResponse<Array<Conversation & { similarity_score: number }>>> {
    try {
      const response = await httpClient.get<ApiResponse<Array<Conversation & { similarity_score: number }>>>(
        `${this.BASE_URL}/${id}/related`,
        { params: { limit } }
      );
      return response;
    } catch (error) {
      console.error('获取相关对话推荐失败:', error);
      throw error;
    }
  }
}