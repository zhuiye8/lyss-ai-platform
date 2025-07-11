/**
 * 租户管理相关API服务
 * 根据docs/frontend.md规范设计
 */

import httpClient from './http';
import { API_ENDPOINTS } from '@/utils/constants';
import { Tenant, CreateTenantRequest, UpdateTenantRequest } from '@/types/tenant';
import { ApiResponse, PaginationResponse } from '@/types/api';

/**
 * 租户管理服务类
 */
export class TenantService {
  /**
   * 获取租户列表
   */
  static async getTenants(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Promise<ApiResponse<PaginationResponse<Tenant>>> {
    const response = await httpClient.get(API_ENDPOINTS.TENANTS.LIST, { params });
    return response.data;
  }

  /**
   * 获取租户详情
   */
  static async getTenant(id: string): Promise<ApiResponse<Tenant>> {
    const response = await httpClient.get(API_ENDPOINTS.TENANTS.DETAIL(id));
    return response.data;
  }

  /**
   * 创建租户
   */
  static async createTenant(data: CreateTenantRequest): Promise<ApiResponse<Tenant>> {
    const response = await httpClient.post(API_ENDPOINTS.TENANTS.CREATE, data);
    return response.data;
  }

  /**
   * 更新租户
   */
  static async updateTenant(id: string, data: UpdateTenantRequest): Promise<ApiResponse<Tenant>> {
    const response = await httpClient.put(API_ENDPOINTS.TENANTS.UPDATE(id), data);
    return response.data;
  }

  /**
   * 删除租户
   */
  static async deleteTenant(id: string): Promise<ApiResponse<void>> {
    const response = await httpClient.delete(API_ENDPOINTS.TENANTS.DELETE(id));
    return response.data;
  }

  /**
   * 获取租户统计信息
   */
  static async getTenantStats(id: string): Promise<ApiResponse<{
    user_count: number;
    api_calls_count: number;
    storage_usage: number;
    last_active_at: string;
  }>> {
    const response = await httpClient.get(API_ENDPOINTS.TENANTS.STATS(id));
    return response.data;
  }

  /**
   * 批量操作租户
   */
  static async batchUpdateTenants(ids: string[], action: 'enable' | 'disable'): Promise<ApiResponse<void>> {
    const response = await httpClient.post('/api/v1/admin/tenants/batch', {
      tenant_ids: ids,
      action,
    });
    return response.data;
  }

  /**
   * 导出租户数据
   */
  static async exportTenants(params?: {
    format?: 'csv' | 'xlsx';
    filters?: Record<string, any>;
  }): Promise<Blob> {
    const response = await httpClient.post(
      '/api/v1/admin/tenants/export',
      params,
      { responseType: 'blob' }
    );
    return response.data;
  }
}