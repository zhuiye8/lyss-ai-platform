/**
 * Lyss AI Platform - HTTP请求工具
 * 功能描述: 基于axios的统一HTTP请求封装
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { message } from 'antd'
import { ApiResponse, ApiError } from '@/types'

// 创建axios实例
const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 60000, // 60秒超时
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // 添加认证token
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 添加租户信息
    const tenantId = localStorage.getItem('tenant_id')
    if (tenantId && config.headers) {
      config.headers['X-Tenant-ID'] = tenantId
    }

    // 添加请求ID用于追踪
    const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    if (config.headers) {
      config.headers['X-Request-ID'] = requestId
    }

    console.log(`[请求] ${config.method?.toUpperCase()} ${config.url}`, config.data)
    return config
  },
  (error) => {
    console.error('[请求错误]', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const { data } = response
    
    console.log(`[响应] ${response.config.method?.toUpperCase()} ${response.config.url}`, data)

    // 检查业务状态码
    if (data.success) {
      return response
    } else {
      // 业务错误
      const errorMsg = data.message || '请求失败'
      message.error(errorMsg)
      
      const apiError = new ApiError(
        errorMsg,
        response.status,
        data.errors?.[0]?.code || 'UNKNOWN_ERROR',
        data.errors
      )
      return Promise.reject(apiError)
    }
  },
  (error) => {
    console.error('[响应错误]', error)

    // 网络错误或其他错误
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // 未授权，清除token并跳转到登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user_info')
          message.error('登录已过期，请重新登录')
          window.location.href = '/login'
          break
          
        case 403:
          message.error('权限不足，无法访问该资源')
          break
          
        case 404:
          message.error('请求的资源不存在')
          break
          
        case 429:
          message.error('请求过于频繁，请稍后再试')
          break
          
        case 500:
          message.error('服务器内部错误，请稍后再试')
          break
          
        default:
          const errorMsg = data?.message || error.message || '网络错误'
          message.error(errorMsg)
      }
      
      const apiError = new ApiError(
        data?.message || error.message,
        status,
        data?.errors?.[0]?.code || 'HTTP_ERROR',
        data?.errors
      )
      return Promise.reject(apiError)
    } else if (error.request) {
      // 请求已发出但没有收到响应
      message.error('网络连接失败，请检查网络')
      return Promise.reject(new ApiError('网络连接失败', 0, 'NETWORK_ERROR'))
    } else {
      // 其他错误
      message.error('请求配置错误')
      return Promise.reject(new ApiError(error.message, 0, 'CONFIG_ERROR'))
    }
  }
)

// 导出请求方法
export const get = <T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> => {
  return request.get(url, config)
}

export const post = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> => {
  return request.post(url, data, config)
}

export const put = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> => {
  return request.put(url, data, config)
}

export const del = <T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> => {
  return request.delete(url, config)
}

export const patch = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> => {
  return request.patch(url, data, config)
}

// 文件上传
export const upload = <T = any>(url: string, file: File, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> => {
  const formData = new FormData()
  formData.append('file', file)
  
  return request.post(url, formData, {
    ...config,
    headers: {
      'Content-Type': 'multipart/form-data',
      ...config?.headers,
    },
  })
}

// 流式请求（用于AI聊天）
export const streamRequest = (url: string, data?: any, config?: AxiosRequestConfig) => {
  return request.post(url, data, {
    ...config,
    responseType: 'stream',
    headers: {
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
      ...config?.headers,
    },
  })
}

export default request