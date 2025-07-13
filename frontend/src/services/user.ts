/**
 * 用户服务API
 * 与Backend API Gateway的Tenant Service集成
 */

import httpClient from './http';
import { UserAPI } from '@/types/api';
import { CreateUserRequest, UpdateUserRequest } from '@/types/user';
import { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/common';

export class UserService {
  private static readonly BASE_URL = '/api/v1/admin/users';

  /**
   * 获取用户列表
   */
  static async getUsers(params?: PaginationParams & {
    search?: string;
    role?: string;
    status?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Promise<ApiResponse<PaginatedResponse<UserAPI.User>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<UserAPI.User>>>(
        this.BASE_URL,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取用户列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取单个用户详情
   */
  static async getUser(id: string): Promise<ApiResponse<UserAPI.User>> {
    try {
      const response = await httpClient.get<ApiResponse<UserAPI.User>>(
        `${this.BASE_URL}/${id}`
      );
      return response;
    } catch (error) {
      console.error('获取用户详情失败:', error);
      throw error;
    }
  }

  /**
   * 创建用户
   */
  static async createUser(data: CreateUserRequest): Promise<ApiResponse<UserAPI.User>> {
    try {
      const response = await httpClient.post<ApiResponse<UserAPI.User>>(
        this.BASE_URL,
        data
      );
      return response;
    } catch (error) {
      console.error('创建用户失败:', error);
      throw error;
    }
  }

  /**
   * 更新用户
   */
  static async updateUser(id: string, data: UpdateUserRequest): Promise<ApiResponse<UserAPI.User>> {
    try {
      const response = await httpClient.put<ApiResponse<UserAPI.User>>(
        `${this.BASE_URL}/${id}`,
        data
      );
      return response;
    } catch (error) {
      console.error('更新用户失败:', error);
      throw error;
    }
  }

  /**
   * 删除用户
   */
  static async deleteUser(id: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.delete<ApiResponse<null>>(
        `${this.BASE_URL}/${id}`
      );
      return response;
    } catch (error) {
      console.error('删除用户失败:', error);
      throw error;
    }
  }

  /**
   * 批量更新用户状态
   */
  static async batchUpdateUsers(
    userIds: string[],
    action: 'enable' | 'disable'
  ): Promise<ApiResponse<{ updated_count: number }>> {
    try {
      const response = await httpClient.post<ApiResponse<{ updated_count: number }>>(
        `${this.BASE_URL}/batch`,
        {
          user_ids: userIds,
          action,
        }
      );
      return response;
    } catch (error) {
      console.error('批量更新用户失败:', error);
      throw error;
    }
  }

  /**
   * 重置用户密码
   */
  static async resetUserPassword(id: string, newPassword: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/${id}/reset-password`,
        { new_password: newPassword }
      );
      return response;
    } catch (error) {
      console.error('重置用户密码失败:', error);
      throw error;
    }
  }

  /**
   * 获取用户统计信息
   */
  static async getUserStats(id: string): Promise<ApiResponse<{
    conversation_count: number;
    message_count: number;
    api_calls_today: number;
    api_calls_month: number;
    storage_used: number;
    last_active_at: string;
  }>> {
    try {
      const response = await httpClient.get<ApiResponse<{
        conversation_count: number;
        message_count: number;
        api_calls_today: number;
        api_calls_month: number;
        storage_used: number;
        last_active_at: string;
      }>>(
        `${this.BASE_URL}/${id}/stats`
      );
      return response;
    } catch (error) {
      console.error('获取用户统计信息失败:', error);
      throw error;
    }
  }

  /**
   * 获取用户活动日志
   */
  static async getUserActivity(
    id: string,
    params?: PaginationParams & { action?: string }
  ): Promise<ApiResponse<PaginatedResponse<{
    id: string;
    action: string;
    resource_type?: string;
    resource_id?: string;
    ip_address: string;
    user_agent: string;
    metadata?: Record<string, any>;
    created_at: string;
  }>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<{
        id: string;
        action: string;
        resource_type?: string;
        resource_id?: string;
        ip_address: string;
        user_agent: string;
        metadata?: Record<string, any>;
        created_at: string;
      }>>>(
        `${this.BASE_URL}/${id}/activity`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取用户活动日志失败:', error);
      throw error;
    }
  }

  /**
   * 导出用户数据
   */
  static async exportUsers(params?: {
    format?: 'xlsx' | 'csv';
    filters?: {
      search?: string;
      role?: string;
      status?: string;
    };
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
      console.error('导出用户数据失败:', error);
      throw error;
    }
  }

  /**
   * 邀请用户
   */
  static async inviteUser(data: {
    email: string;
    role: string;
    message?: string;
  }): Promise<ApiResponse<{
    invitation_id: string;
    expires_at: string;
  }>> {
    try {
      const response = await httpClient.post<ApiResponse<{
        invitation_id: string;
        expires_at: string;
      }>>(
        `${this.BASE_URL}/invite`,
        data
      );
      return response;
    } catch (error) {
      console.error('邀请用户失败:', error);
      throw error;
    }
  }

  /**
   * 重新发送邀请
   */
  static async resendInvitation(invitationId: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/invitations/${invitationId}/resend`
      );
      return response;
    } catch (error) {
      console.error('重新发送邀请失败:', error);
      throw error;
    }
  }

  /**
   * 取消邀请
   */
  static async cancelInvitation(invitationId: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.delete<ApiResponse<null>>(
        `${this.BASE_URL}/invitations/${invitationId}`
      );
      return response;
    } catch (error) {
      console.error('取消邀请失败:', error);
      throw error;
    }
  }
}