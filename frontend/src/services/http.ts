/**
 * HTTP客户端配置和拦截器
 * 根据docs/frontend.md规范，与Backend API Gateway集成
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';
import { ApiResponse, ApiError } from '@/types/common';

// 获取环境变量配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const JWT_STORAGE_KEY = import.meta.env.VITE_JWT_STORAGE_KEY || 'lyss_access_token';
const REFRESH_TOKEN_KEY = import.meta.env.VITE_REFRESH_TOKEN_KEY || 'lyss_refresh_token';

// HTTP客户端实例
class HttpClient {
  private instance: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (error?: any) => void;
  }> = [];

  constructor() {
    // 创建axios实例
    this.instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 设置请求拦截器
    this.setupRequestInterceptors();
    
    // 设置响应拦截器
    this.setupResponseInterceptors();
  }

  /**
   * 设置请求拦截器
   */
  private setupRequestInterceptors(): void {
    this.instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // 添加JWT令牌
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // 添加请求ID（用于追踪）
        const requestId = this.generateRequestId();
        config.headers['X-Request-ID'] = requestId;

        // 添加时间戳
        config.metadata = {
          ...config.metadata,
          startTime: Date.now(),
          requestId,
        };

        return config;
      },
      (error: AxiosError) => {
        console.error('请求拦截器错误:', error);
        return Promise.reject(error);
      }
    );
  }

  /**
   * 设置响应拦截器
   */
  private setupResponseInterceptors(): void {
    this.instance.interceptors.response.use(
      (response) => {
        // 记录请求耗时
        const startTime = response.config.metadata?.startTime;
        if (startTime) {
          const duration = Date.now() - startTime;
          console.debug(`API请求完成: ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`);
        }

        // 处理统一响应格式
        const apiResponse: ApiResponse = response.data;
        
        if (apiResponse.success) {
          // 成功响应，返回data字段
          return {
            ...response,
            data: apiResponse.data,
          };
        } else {
          // 业务逻辑错误
          const error = apiResponse.error || {
            code: '5003',
            message: '服务器内部错误',
          };
          
          this.handleApiError(error);
          throw new Error(error.message);
        }
      },
      (error: AxiosError) => {
        // HTTP错误处理
        return this.handleHttpError(error);
      }
    );
  }

  /**
   * 处理HTTP错误
   */
  private async handleHttpError(error: AxiosError): Promise<never> {
    const { response, config } = error;
    
    if (response?.status === 401) {
      // 未认证或令牌过期
      return this.handleUnauthorized(config);
    }
    
    if (response?.status === 403) {
      // 权限不足
      message.error('权限不足，无法访问该资源');
      throw error;
    }
    
    if (response?.status === 429) {
      // 请求频率过高
      message.warning('请求过于频繁，请稍后再试');
      throw error;
    }
    
    if (response?.status >= 500) {
      // 服务器错误
      message.error('服务器内部错误，请稍后重试');
      throw error;
    }
    
    // 其他错误
    const errorMessage = this.extractErrorMessage(error);
    message.error(errorMessage);
    throw error;
  }

  /**
   * 处理API业务错误
   */
  private handleApiError(apiError: ApiError): void {
    const { code, message: errorMessage } = apiError;
    
    // 根据STANDARDS.md中的错误代码进行处理
    switch (code) {
      case '2001':
        message.error('请先登录');
        this.redirectToLogin();
        break;
      case '2002':
        message.error('登录已过期，请重新登录');
        this.redirectToLogin();
        break;
      case '2003':
        message.error('令牌无效，请重新登录');
        this.redirectToLogin();
        break;
      case '2004':
        message.error('权限不足');
        break;
      case '3001':
        message.error('租户不存在');
        break;
      case '3003':
        message.error('用户不存在');
        break;
      case '5004':
        message.error('服务暂时不可用，请稍后重试');
        break;
      default:
        message.error(errorMessage || '操作失败');
    }
  }

  /**
   * 处理未认证错误，尝试刷新令牌
   */
  private async handleUnauthorized(originalRequest?: InternalAxiosRequestConfig): Promise<never> {
    if (this.isRefreshing) {
      // 正在刷新令牌，将请求加入队列
      return new Promise((resolve, reject) => {
        this.failedQueue.push({ resolve, reject });
      });
    }

    this.isRefreshing = true;

    try {
      await this.refreshAccessToken();
      
      // 刷新成功，重试失败的请求
      this.processQueue(null);
      
      if (originalRequest) {
        const token = this.getAccessToken();
        if (token) {
          originalRequest.headers.Authorization = `Bearer ${token}`;
        }
        return this.instance.request(originalRequest);
      }
    } catch (refreshError) {
      // 刷新失败，清除认证信息并重定向到登录页
      this.processQueue(refreshError);
      this.clearAuthTokens();
      this.redirectToLogin();
    } finally {
      this.isRefreshing = false;
    }

    throw new Error('认证失败');
  }

  /**
   * 刷新访问令牌
   */
  private async refreshAccessToken(): Promise<void> {
    const refreshToken = this.getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('无刷新令牌');
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      });

      const { data } = response.data;
      
      if (data?.access_token) {
        this.setAccessToken(data.access_token);
      } else {
        throw new Error('刷新令牌响应无效');
      }
    } catch (error) {
      console.error('刷新令牌失败:', error);
      throw error;
    }
  }

  /**
   * 处理令牌刷新队列
   */
  private processQueue(error: any): void {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    });
    
    this.failedQueue = [];
  }

  /**
   * 提取错误信息
   */
  private extractErrorMessage(error: AxiosError): string {
    if (error.response?.data) {
      const data = error.response.data as any;
      
      if (data.error?.message) {
        return data.error.message;
      }
      
      if (data.message) {
        return data.message;
      }
    }
    
    if (error.message) {
      return error.message;
    }
    
    return '网络连接失败';
  }

  /**
   * 生成请求ID
   */
  private generateRequestId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2);
    return `req-${timestamp}-${random}`;
  }

  /**
   * 获取访问令牌
   */
  private getAccessToken(): string | null {
    return localStorage.getItem(JWT_STORAGE_KEY);
  }

  /**
   * 设置访问令牌
   */
  private setAccessToken(token: string): void {
    localStorage.setItem(JWT_STORAGE_KEY, token);
  }

  /**
   * 获取刷新令牌
   */
  private getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  /**
   * 清除认证令牌
   */
  private clearAuthTokens(): void {
    localStorage.removeItem(JWT_STORAGE_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  /**
   * 重定向到登录页
   */
  private redirectToLogin(): void {
    // 保存当前路径，登录后跳转回来
    const currentPath = window.location.pathname + window.location.search;
    if (currentPath !== '/login') {
      sessionStorage.setItem('redirect_after_login', currentPath);
    }
    
    window.location.href = '/login';
  }

  /**
   * 获取axios实例
   */
  public getInstance(): AxiosInstance {
    return this.instance;
  }

  /**
   * GET请求
   */
  public get<T = any>(url: string, params?: any): Promise<T> {
    return this.instance.get(url, { params });
  }

  /**
   * POST请求
   */
  public post<T = any>(url: string, data?: any): Promise<T> {
    return this.instance.post(url, data);
  }

  /**
   * PUT请求
   */
  public put<T = any>(url: string, data?: any): Promise<T> {
    return this.instance.put(url, data);
  }

  /**
   * PATCH请求
   */
  public patch<T = any>(url: string, data?: any): Promise<T> {
    return this.instance.patch(url, data);
  }

  /**
   * DELETE请求
   */
  public delete<T = any>(url: string): Promise<T> {
    return this.instance.delete(url);
  }
}

// 创建HTTP客户端实例
const httpClient = new HttpClient();

// 导出实例和类型
export default httpClient;
export type { HttpClient };