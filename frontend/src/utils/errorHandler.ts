/**
 * 错误处理工具
 * 根据docs/frontend.md规范设计
 */

import { message } from 'antd';
import type { AxiosError } from 'axios';
import { ERROR_CODES } from '@/utils/constants';

/**
 * API错误响应结构
 */
interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  request_id?: string;
  timestamp?: string;
}

/**
 * 处理API错误
 */
export const handleApiError = (error: any): void => {
  console.error('API错误:', error);
  
  // 判断错误类型
  if (error.response) {
    // 服务器响应错误
    const response = error.response;
    const data = response.data as ApiErrorResponse;
    
    if (data?.error?.code) {
      // 有错误代码，使用映射表
      const errorMessage = ERROR_CODES[data.error.code as keyof typeof ERROR_CODES] || data.error.message;
      message.error(errorMessage);
      
      // 特殊错误处理
      switch (data.error.code) {
        case '2001':
        case '2002':
        case '2003':
          // 认证错误，清理本地状态并重定向到登录页
          localStorage.removeItem('lyss_access_token');
          localStorage.removeItem('lyss_refresh_token');
          setTimeout(() => {
            window.location.href = '/login';
          }, 1000);
          break;
        case '2004':
          // 权限不足，重定向到403页面
          window.location.href = '/403';
          break;
        default:
          break;
      }
    } else {
      // 无错误代码，使用通用错误信息
      const statusCode = response.status;
      const errorMessage = getErrorMessageByStatus(statusCode);
      message.error(errorMessage);
    }
  } else if (error.request) {
    // 网络错误
    message.error('网络连接失败，请检查网络连接');
  } else {
    // 其他错误
    const errorMessage = error.message || '操作失败';
    message.error(errorMessage);
  }
};

/**
 * 根据HTTP状态码获取错误信息
 */
const getErrorMessageByStatus = (status: number): string => {
  switch (status) {
    case 400:
      return '请求参数错误';
    case 401:
      return '未授权，请重新登录';
    case 403:
      return '没有权限执行此操作';
    case 404:
      return '请求的资源不存在';
    case 405:
      return '请求方法不允许';
    case 408:
      return '请求超时';
    case 409:
      return '资源冲突';
    case 422:
      return '请求参数验证失败';
    case 429:
      return '请求过于频繁，请稍后重试';
    case 500:
      return '服务器内部错误';
    case 501:
      return '服务器不支持该功能';
    case 502:
      return '网关错误';
    case 503:
      return '服务器暂时不可用';
    case 504:
      return '网关超时';
    default:
      return `请求失败（错误代码: ${status}）`;
  }
};

/**
 * 处理表单验证错误
 */
export const handleFormError = (error: any, form?: any): void => {
  if (error.response?.status === 422) {
    // 表单验证错误
    const data = error.response.data as ApiErrorResponse;
    if (data?.error?.details && form) {
      const fieldErrors = data.error.details;
      const fields = Object.keys(fieldErrors).map(field => ({
        name: field,
        errors: Array.isArray(fieldErrors[field]) ? fieldErrors[field] : [fieldErrors[field]],
      }));
      form.setFields(fields);
    } else {
      handleApiError(error);
    }
  } else {
    handleApiError(error);
  }
};

/**
 * 处理批量操作错误
 */
export const handleBatchError = (error: any, context?: string): void => {
  const prefix = context ? `${context}: ` : '';
  
  if (error.response?.data?.error?.details?.failed_items) {
    // 部分失败的批量操作
    const failedItems = error.response.data.error.details.failed_items;
    const failedCount = failedItems.length;
    message.error(`${prefix}${failedCount} 个项目处理失败`);
    
    // 可以进一步显示失败详情
    console.error('批量操作失败详情:', failedItems);
  } else {
    handleApiError(error);
  }
};

/**
 * 处理文件上传错误
 */
export const handleUploadError = (error: any): void => {
  if (error.response?.status === 413) {
    message.error('文件太大，请选择小于 10MB 的文件');
  } else if (error.response?.status === 415) {
    message.error('不支持的文件类型');
  } else {
    handleApiError(error);
  }
};

/**
 * 处理导出错误
 */
export const handleExportError = (error: any): void => {
  if (error.response?.status === 400) {
    message.error('导出参数错误');
  } else if (error.response?.status === 404) {
    message.error('没有可导出的数据');
  } else {
    handleApiError(error);
  }
};

/**
 * 处理流式响应错误
 */
export const handleStreamError = (error: any): void => {
  if (error.type === 'stream_error') {
    message.error('数据流中断，请重新试试');
  } else {
    handleApiError(error);
  }
};

/**
 * 获取错误信息字符串（不显示消息）
 */
export const getErrorMessage = (error: any): string => {
  if (error.response?.data?.error?.code) {
    const code = error.response.data.error.code;
    return ERROR_CODES[code as keyof typeof ERROR_CODES] || error.response.data.error.message;
  }
  
  if (error.response?.status) {
    return getErrorMessageByStatus(error.response.status);
  }
  
  if (error.request) {
    return '网络连接失败';
  }
  
  return error.message || '操作失败';
};

/**
 * 检查是否为认证错误
 */
export const isAuthError = (error: any): boolean => {
  const code = error.response?.data?.error?.code;
  return ['2001', '2002', '2003'].includes(code);
};

/**
 * 检查是否为权限错误
 */
export const isPermissionError = (error: any): boolean => {
  const code = error.response?.data?.error?.code;
  return code === '2004' || error.response?.status === 403;
};

/**
 * 检查是否为网络错误
 */
export const isNetworkError = (error: any): boolean => {
  return !error.response && error.request;
};

/**
 * 检查是否为服务器错误
 */
export const isServerError = (error: any): boolean => {
  return error.response?.status >= 500;
};

/**
 * 统一的异常处理装饰器
 */
export const withErrorHandling = <T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options?: {
    showError?: boolean;
    context?: string;
  }
): T => {
  const { showError = true, context } = options || {};
  
  return (async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    try {
      return await fn(...args);
    } catch (error) {
      if (showError) {
        if (context) {
          console.error(`${context}失败:`, error);
        }
        handleApiError(error);
      }
      throw error;
    }
  }) as T;
};