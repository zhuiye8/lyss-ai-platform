import http from './http';
import type { ApiResponse } from '@/types/common';

/**
 * OneAPI服务集成
 * 文档参考：https://github.com/songquanpeng/one-api
 */
class OneAPIService {
  private static instance: OneAPIService;
  private basePath = '/api/oneapi';

  private constructor() {}

  public static getInstance(): OneAPIService {
    if (!OneAPIService.instance) {
      OneAPIService.instance = new OneAPIService();
    }
    return OneAPIService.instance;
  }

  /**
   * 获取渠道列表
   */
  public async getChannels(): Promise<Channel[]> {
    const response = await http.get<ApiResponse<Channel[]>>(
      `${this.basePath}/channels`
    );
    return response.data;
  }

  /**
   * 创建渠道
   */
  public async createChannel(payload: CreateChannelDto): Promise<Channel> {
    const response = await http.post<ApiResponse<Channel>>(
      `${this.basePath}/channels`,
      payload
    );
    return response.data;
  }

  /**
   * 更新用户配额
   */
  public async updateUserQuota(
    userId: number,
    quota: number
  ): Promise<{ success: boolean }> {
    const response = await http.post<ApiResponse<{ success: boolean }>>(
      `${this.basePath}/users/${userId}/quota`,
      { quota }
    );
    return response.data;
  }

  /**
   * 获取API请求日志
   */
  public async getLogs(params?: LogQueryParams): Promise<Log[]> {
    const response = await http.get<ApiResponse<Log[]>>(
      `${this.basePath}/logs`,
      { params }
    );
    return response.data;
  }
}

// 类型定义
interface Channel {
  id: number;
  name: string;
  type: string;
  status: boolean;
  balance: number;
}

interface CreateChannelDto {
  name: string;
  type: string;
  balance: number;
}

interface Log {
  id: number;
  timestamp: string;
  path: string;
  status: number;
  latency: number;
}

interface LogQueryParams {
  page?: number;
  size?: number;
  channel_id?: number;
  user_id?: number;
  status?: number;
}

export default OneAPIService.getInstance();
export type { Channel, CreateChannelDto, Log };