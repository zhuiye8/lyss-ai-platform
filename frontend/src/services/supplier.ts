/**
 * 供应商凭证服务API
 * 与Backend API Gateway的Tenant Service集成
 */

import httpClient from './http';
import { 
  SupplierCredential, 
  CreateSupplierCredentialRequest, 
  UpdateSupplierCredentialRequest,
  ConnectionTestResult,
  SupplierStats,
  SupplierUsageHistory,
  ModelInfo,
  AvailableProvidersResponse,
  ProviderModelsResponse,
  SupplierTestRequest,
  SupplierTestResponse
} from '@/types/supplier';
import { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/common';

export class SupplierService {
  private static readonly BASE_URL = '/api/v1/admin/suppliers';

  /**
   * 获取供应商凭证列表
   */
  static async getSupplierCredentials(params?: PaginationParams & {
    search?: string;
    provider?: string;
    status?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Promise<ApiResponse<PaginatedResponse<SupplierCredential>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<SupplierCredential>>>(
        this.BASE_URL,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取供应商凭证列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取单个供应商凭证详情
   */
  static async getSupplierCredentialDetail(
    id: string,
    options?: { include_api_key?: boolean }
  ): Promise<ApiResponse<SupplierCredential>> {
    try {
      const response = await httpClient.get<ApiResponse<SupplierCredential>>(
        `${this.BASE_URL}/${id}`,
        { params: options }
      );
      return response;
    } catch (error) {
      console.error('获取供应商凭证详情失败:', error);
      throw error;
    }
  }

  /**
   * 创建供应商凭证
   */
  static async createSupplierCredential(data: CreateSupplierCredentialRequest): Promise<ApiResponse<SupplierCredential>> {
    try {
      const response = await httpClient.post<ApiResponse<SupplierCredential>>(
        this.BASE_URL,
        data
      );
      return response;
    } catch (error) {
      console.error('创建供应商凭证失败:', error);
      throw error;
    }
  }

  /**
   * 更新供应商凭证
   */
  static async updateSupplierCredential(
    id: string,
    data: UpdateSupplierCredentialRequest
  ): Promise<ApiResponse<SupplierCredential>> {
    try {
      const response = await httpClient.put<ApiResponse<SupplierCredential>>(
        `${this.BASE_URL}/${id}`,
        data
      );
      return response;
    } catch (error) {
      console.error('更新供应商凭证失败:', error);
      throw error;
    }
  }

  /**
   * 删除供应商凭证
   */
  static async deleteSupplierCredential(id: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.delete<ApiResponse<null>>(
        `${this.BASE_URL}/${id}`
      );
      return response;
    } catch (error) {
      console.error('删除供应商凭证失败:', error);
      throw error;
    }
  }

  /**
   * 测试供应商连接
   */
  static async testConnection(id: string): Promise<ApiResponse<ConnectionTestResult>> {
    try {
      const response = await httpClient.post<ApiResponse<ConnectionTestResult>>(
        `${this.BASE_URL}/${id}/test-connection`
      );
      return response;
    } catch (error) {
      console.error('测试供应商连接失败:', error);
      throw error;
    }
  }

  /**
   * 批量测试连接
   */
  static async batchTestConnections(ids: string[]): Promise<ApiResponse<{
    results: Array<{
      id: string;
      success: boolean;
      error_message?: string;
    }>;
  }>> {
    try {
      const response = await httpClient.post<ApiResponse<{
        results: Array<{
          id: string;
          success: boolean;
          error_message?: string;
        }>;
      }>>(
        `${this.BASE_URL}/batch-test`,
        { credential_ids: ids }
      );
      return response;
    } catch (error) {
      console.error('批量测试连接失败:', error);
      throw error;
    }
  }

  /**
   * 获取供应商统计信息
   */
  static async getSupplierStats(
    id: string,
    params?: {
      start_date?: string;
      end_date?: string;
    }
  ): Promise<ApiResponse<SupplierStats>> {
    try {
      const response = await httpClient.get<ApiResponse<SupplierStats>>(
        `${this.BASE_URL}/${id}/stats`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取供应商统计信息失败:', error);
      throw error;
    }
  }

  /**
   * 获取供应商使用历史
   */
  static async getSupplierUsageHistory(
    id: string,
    params?: PaginationParams & {
      start_date?: string;
      end_date?: string;
      request_type?: string;
      status?: string;
    }
  ): Promise<ApiResponse<PaginatedResponse<SupplierUsageHistory>>> {
    try {
      const response = await httpClient.get<ApiResponse<PaginatedResponse<SupplierUsageHistory>>>(
        `${this.BASE_URL}/${id}/usage-history`,
        { params }
      );
      return response;
    } catch (error) {
      console.error('获取供应商使用历史失败:', error);
      throw error;
    }
  }

  /**
   * 获取支持的供应商列表
   */
  static async getSupportedProviders(): Promise<ApiResponse<Array<{
    provider: string;
    name: string;
    icon: string;
    description: string;
    default_endpoint?: string;
    supported_models: string[];
    documentation_url?: string;
  }>>> {
    try {
      const response = await httpClient.get<ApiResponse<Array<{
        provider: string;
        name: string;
        icon: string;
        description: string;
        default_endpoint?: string;
        supported_models: string[];
        documentation_url?: string;
      }>>>(
        `${this.BASE_URL}/supported-providers`
      );
      return response;
    } catch (error) {
      console.error('获取支持的供应商列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取供应商的可用模型
   */
  static async getProviderModels(id: string): Promise<ApiResponse<ModelInfo[]>> {
    try {
      const response = await httpClient.get<ApiResponse<ModelInfo[]>>(
        `${this.BASE_URL}/${id}/models`
      );
      return response;
    } catch (error) {
      console.error('获取供应商模型失败:', error);
      throw error;
    }
  }

  /**
   * 设置默认供应商凭证
   */
  static async setAsDefault(id: string): Promise<ApiResponse<null>> {
    try {
      const response = await httpClient.post<ApiResponse<null>>(
        `${this.BASE_URL}/${id}/set-default`
      );
      return response;
    } catch (error) {
      console.error('设置默认供应商失败:', error);
      throw error;
    }
  }

  /**
   * 批量更新供应商状态
   */
  static async batchUpdateStatus(
    ids: string[],
    action: 'enable' | 'disable'
  ): Promise<ApiResponse<{ updated_count: number }>> {
    try {
      const response = await httpClient.post<ApiResponse<{ updated_count: number }>>(
        `${this.BASE_URL}/batch-update`,
        {
          credential_ids: ids,
          action,
        }
      );
      return response;
    } catch (error) {
      console.error('批量更新供应商状态失败:', error);
      throw error;
    }
  }

  /**
   * 导出供应商凭证数据
   */
  static async exportCredentials(params?: {
    format?: 'xlsx' | 'csv';
    include_api_keys?: boolean;
    filters?: {
      search?: string;
      provider?: string;
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
      console.error('导出供应商凭证数据失败:', error);
      throw error;
    }
  }

  /**
   * 验证API密钥格式
   */
  static async validateApiKey(data: {
    provider: string;
    api_key: string;
    api_endpoint?: string;
  }): Promise<ApiResponse<{
    valid: boolean;
    error_message?: string;
    suggestions?: string[];
  }>> {
    try {
      const response = await httpClient.post<ApiResponse<{
        valid: boolean;
        error_message?: string;
        suggestions?: string[];
      }>>(
        `${this.BASE_URL}/validate-api-key`,
        data
      );
      return response;
    } catch (error) {
      console.error('验证API密钥失败:', error);
      throw error;
    }
  }

  /**
   * 获取供应商配额信息
   */
  static async getQuotaInfo(id: string): Promise<ApiResponse<{
    quota_limit?: number;
    quota_used?: number;
    quota_remaining?: number;
    reset_date?: string;
    rate_limit?: {
      requests_per_minute: number;
      tokens_per_minute: number;
    };
  }>> {
    try {
      const response = await httpClient.get<ApiResponse<{
        quota_limit?: number;
        quota_used?: number;
        quota_remaining?: number;
        reset_date?: string;
        rate_limit?: {
          requests_per_minute: number;
          tokens_per_minute: number;
        };
      }>>(
        `${this.BASE_URL}/${id}/quota`
      );
      return response;
    } catch (error) {
      console.error('获取供应商配额信息失败:', error);
      throw error;
    }
  }

  // ==================== 新增：树形结构API方法 ====================

  /**
   * 获取支持的供应商和模型树形结构
   * 调用新的后端API: GET /api/v1/admin/suppliers/available
   */
  static async getAvailableProviders(): Promise<ApiResponse<AvailableProvidersResponse>> {
    try {
      const response = await httpClient.get<ApiResponse<AvailableProvidersResponse>>(
        `${this.BASE_URL}/available`
      );
      return response;
    } catch (error) {
      console.error('获取支持的供应商和模型树形结构失败:', error);
      throw error;
    }
  }

  /**
   * 获取指定供应商的模型列表
   * 调用新的后端API: GET /api/v1/admin/suppliers/providers/{provider_name}/models
   */
  static async getProviderModelsByName(providerName: string): Promise<ApiResponse<ProviderModelsResponse>> {
    try {
      const response = await httpClient.get<ApiResponse<ProviderModelsResponse>>(
        `${this.BASE_URL}/providers/${providerName}/models`
      );
      return response;
    } catch (error) {
      console.error(`获取供应商 ${providerName} 的模型列表失败:`, error);
      throw error;
    }
  }

  /**
   * 保存前测试供应商凭证
   * 调用新的后端API: POST /api/v1/admin/suppliers/test
   */
  static async testSupplierBeforeSave(data: SupplierTestRequest): Promise<ApiResponse<SupplierTestResponse>> {
    try {
      const response = await httpClient.post<ApiResponse<SupplierTestResponse>>(
        `${this.BASE_URL}/test`,
        data
      );
      return response;
    } catch (error) {
      console.error('保存前测试供应商凭证失败:', error);
      throw error;
    }
  }
}