/**
 * 认证服务API
 * 与Backend API Gateway的Auth Service集成
 */

import httpClient from './http';
import { AuthAPI } from '@/types/api';
import { ApiResponse } from '@/types/common';

export class AuthService {
  private static readonly BASE_URL = '/api/v1/auth';

  /**
   * 用户登录
   */
  static async login(credentials: AuthAPI.LoginRequest): Promise<ApiResponse<AuthAPI.LoginResponse>> {
    try {
      // Auth Service期望OAuth2格式的form-encoded数据
      const formData = new URLSearchParams();
      formData.append('username', credentials.email);
      formData.append('password', credentials.password);
      
      const response = await httpClient.getInstance().post(
        `${this.BASE_URL}/token`,
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );
      
      // HTTP拦截器已经提取了ApiResponse.data，所以response.data直接是登录数据
      const loginData = response.data as AuthAPI.BackendLoginResponse;
      
      // 检查登录数据是否完整
      if (!loginData || !loginData.user_info) {
        console.error('后端返回数据格式错误:', loginData);
        throw new Error('后端返回的数据格式不正确');
      }
      
      // 提取用户信息
      const userInfo = loginData.user_info;
      
      // 将后端数据转换为前端期望的格式
      const transformedData: ApiResponse<AuthAPI.LoginResponse> = {
        success: true,
        data: {
          user: {
            id: userInfo.user_id,
            email: userInfo.email,
            name: userInfo.email.split('@')[0], // 从邮箱提取用户名
            role: userInfo.role,
            tenant_id: userInfo.tenant_id,
            is_active: userInfo.is_active,
            avatar: undefined, // 后端暂时没有头像字段
          },
          access_token: loginData.access_token,
          refresh_token: loginData.refresh_token,
          expires_in: loginData.expires_in,
        },
        message: '登录成功',
        request_id: 'extracted-by-interceptor',
        timestamp: new Date().toISOString()
      };
      
      return transformedData;
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  }

  /**
   * 刷新访问令牌
   */
  static async refreshToken(refreshToken: string): Promise<ApiResponse<AuthAPI.RefreshTokenResponse>> {
    try {
      const response = await httpClient.post<ApiResponse<AuthAPI.RefreshTokenResponse>>(
        `${this.BASE_URL}/refresh`,
        { refresh_token: refreshToken }
      );
      return response;
    } catch (error) {
      console.error('刷新令牌失败:', error);
      throw error;
    }
  }

  /**
   * 用户登出
   */
  static async logout(refreshToken?: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/logout`,
        refreshToken ? { refresh_token: refreshToken } : {}
      );
      return response;
    } catch (error) {
      console.error('登出失败:', error);
      throw error;
    }
  }

  /**
   * 验证当前令牌是否有效
   */
  static async verifyToken(): Promise<ApiResponse<{ valid: boolean; user?: any }>> {
    try {
      const response = await httpClient.get<ApiResponse<{ valid: boolean; user?: any }>>(
        `${this.BASE_URL}/verify`
      );
      return response;
    } catch (error) {
      console.error('令牌验证失败:', error);
      throw error;
    }
  }

  /**
   * 获取当前用户信息
   */
  static async getCurrentUser(): Promise<ApiResponse<AuthAPI.LoginResponse['user']>> {
    try {
      const response = await httpClient.get<ApiResponse<AuthAPI.LoginResponse['user']>>(
        `${this.BASE_URL}/me`
      );
      return response;
    } catch (error) {
      console.error('获取用户信息失败:', error);
      throw error;
    }
  }

  /**
   * 修改密码
   */
  static async changePassword(data: {
    current_password: string;
    new_password: string;
  }): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/change-password`,
        data
      );
      return response;
    } catch (error) {
      console.error('修改密码失败:', error);
      throw error;
    }
  }

  /**
   * 请求密码重置
   */
  static async requestPasswordReset(email: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/request-password-reset`,
        { email }
      );
      return response;
    } catch (error) {
      console.error('请求密码重置失败:', error);
      throw error;
    }
  }

  /**
   * 重置密码
   */
  static async resetPassword(data: {
    token: string;
    new_password: string;
  }): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/reset-password`,
        data
      );
      return response;
    } catch (error) {
      console.error('重置密码失败:', error);
      throw error;
    }
  }

  /**
   * 检查邮箱是否已被使用
   */
  static async checkEmailExists(email: string): Promise<ApiResponse<{ exists: boolean }>> {
    try {
      const response = await httpClient.get<ApiResponse<{ exists: boolean }>>(
        `${this.BASE_URL}/check-email`,
        { email }
      );
      return response;
    } catch (error) {
      console.error('检查邮箱失败:', error);
      throw error;
    }
  }
}