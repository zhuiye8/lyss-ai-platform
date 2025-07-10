# -*- coding: utf-8 -*-
"""
供应商凭证业务逻辑服务

处理供应商凭证相关的业务逻辑和规则
"""

import uuid
import time
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx

from ..repositories.supplier_repository import SupplierRepository
from ..core.encryption import credential_manager
from ..models.schemas.supplier import (
    SupplierCredentialCreateRequest,
    SupplierCredentialUpdateRequest,
    SupplierCredentialResponse,
    SupplierCredentialDetailResponse,
    SupplierCredentialListParams,
    SupplierTestRequest,
    SupplierTestResponse,
    SUPPORTED_PROVIDERS
)
from ..models.database.supplier_credential import SupplierCredential

logger = structlog.get_logger()


class SupplierService:
    """供应商凭证服务类"""
    
    def __init__(self, db_session: AsyncSession):
        """
        初始化供应商服务
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self.supplier_repo = SupplierRepository(db_session)
    
    async def create_credential(
        self,
        request_data: SupplierCredentialCreateRequest,
        tenant_id: str,
        request_id: str
    ) -> SupplierCredentialResponse:
        """
        创建供应商凭证
        
        Args:
            request_data: 凭证创建请求数据
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            创建的凭证信息
            
        Raises:
            ValueError: 当数据验证失败时
        """
        try:
            logger.info(
                "开始创建供应商凭证",
                request_id=request_id,
                tenant_id=tenant_id,
                provider_name=request_data.provider_name,
                operation="create_credential"
            )
            
            # 验证供应商名称
            if request_data.provider_name not in SUPPORTED_PROVIDERS:
                raise ValueError(f"不支持的供应商: {request_data.provider_name}")
            
            # 验证API密钥格式（如果有格式要求）
            provider_info = SUPPORTED_PROVIDERS[request_data.provider_name]
            if provider_info.get("api_key_pattern"):
                import re
                if not re.match(provider_info["api_key_pattern"], request_data.api_key):
                    raise ValueError(f"API密钥格式不正确")
            
            # 检查同一租户下是否已存在相同的供应商配置
            existing_credential = await self.supplier_repo.get_by_provider_and_display_name(
                uuid.UUID(tenant_id),
                request_data.provider_name,
                request_data.display_name
            )
            if existing_credential:
                raise ValueError("该供应商配置已存在")
            
            # 使用加密管理器存储凭证
            credential_id = await credential_manager.store_encrypted_credential(
                self.db,
                tenant_id,
                request_data.provider_name,
                request_data.display_name,
                request_data.api_key,
                request_data.base_url,
                request_data.model_configs or {}
            )
            
            # 获取创建的凭证信息
            credential = await self.supplier_repo.get_by_id_in_tenant(
                uuid.UUID(credential_id), uuid.UUID(tenant_id)
            )
            
            # 记录成功日志
            logger.info(
                "供应商凭证创建成功",
                request_id=request_id,
                tenant_id=tenant_id,
                credential_id=credential_id,
                provider_name=request_data.provider_name,
                operation="create_credential"
            )
            
            # 转换为响应格式
            return await self._convert_to_response(credential)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "供应商凭证创建失败",
                request_id=request_id,
                tenant_id=tenant_id,
                error=str(e),
                operation="create_credential"
            )
            raise
    
    async def get_credentials_paginated(
        self,
        tenant_id: str,
        params: SupplierCredentialListParams,
        request_id: str
    ) -> Tuple[List[SupplierCredentialResponse], int]:
        """
        分页获取供应商凭证列表
        
        Args:
            tenant_id: 租户ID
            params: 查询参数
            request_id: 请求ID
            
        Returns:
            凭证列表和总数的元组
        """
        try:
            # 构建过滤条件
            filters = {"tenant_id": uuid.UUID(tenant_id)}
            
            if params.provider_name:
                filters["provider_name"] = params.provider_name
            if params.is_active is not None:
                filters["is_active"] = params.is_active
            
            # 计算偏移量
            offset = (params.page - 1) * params.page_size
            
            # 获取凭证列表
            credentials = await self.supplier_repo.get_credentials_by_filters(
                filters=filters,
                order_by=params.sort_by,
                order_desc=(params.sort_order == "desc"),
                limit=params.page_size,
                offset=offset
            )
            
            # 获取总数
            total_count = await self.supplier_repo.count_credentials_by_filters(filters)
            
            # 转换为响应格式
            credential_responses = []
            for credential in credentials:
                credential_response = await self._convert_to_response(credential)
                credential_responses.append(credential_response)
            
            logger.info(
                "供应商凭证列表获取成功",
                request_id=request_id,
                tenant_id=tenant_id,
                count=len(credential_responses),
                total=total_count,
                operation="get_credentials_paginated"
            )
            
            return credential_responses, total_count
            
        except Exception as e:
            logger.error(
                "获取供应商凭证列表失败",
                request_id=request_id,
                tenant_id=tenant_id,
                error=str(e),
                operation="get_credentials_paginated"
            )
            raise
    
    async def get_credential_detail(
        self,
        credential_id: uuid.UUID,
        tenant_id: str,
        request_id: str
    ) -> Optional[SupplierCredentialDetailResponse]:
        """
        获取供应商凭证详细信息
        
        Args:
            credential_id: 凭证ID
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            凭证详细信息或None
        """
        try:
            # 获取凭证信息
            credential = await self.supplier_repo.get_by_id_in_tenant(
                credential_id, uuid.UUID(tenant_id)
            )
            
            if not credential:
                return None
            
            # 获取使用统计信息
            stats = await self.supplier_repo.get_credential_stats(credential_id)
            
            # 构建详细响应
            credential_detail = SupplierCredentialDetailResponse(
                id=credential.id,
                tenant_id=credential.tenant_id,
                provider_name=credential.provider_name,
                display_name=credential.display_name,
                base_url=credential.base_url,
                model_configs=credential.model_configs,
                is_active=credential.is_active,
                created_at=credential.created_at,
                updated_at=credential.updated_at,
                # 统计信息
                last_used_at=stats.get("last_used_at"),
                usage_count=stats.get("usage_count", 0),
                error_count=stats.get("error_count", 0),
                last_error_at=stats.get("last_error_at"),
                last_error_message=stats.get("last_error_message")
            )
            
            logger.info(
                "供应商凭证详情获取成功",
                request_id=request_id,
                credential_id=str(credential_id),
                tenant_id=tenant_id,
                operation="get_credential_detail"
            )
            
            return credential_detail
            
        except Exception as e:
            logger.error(
                "获取供应商凭证详情失败",
                request_id=request_id,
                credential_id=str(credential_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="get_credential_detail"
            )
            raise
    
    async def update_credential(
        self,
        credential_id: uuid.UUID,
        request_data: SupplierCredentialUpdateRequest,
        tenant_id: str,
        request_id: str
    ) -> Optional[SupplierCredentialResponse]:
        """
        更新供应商凭证信息
        
        Args:
            credential_id: 凭证ID
            request_data: 更新请求数据
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            更新后的凭证信息或None
        """
        try:
            # 检查凭证是否存在
            existing_credential = await self.supplier_repo.get_by_id_in_tenant(
                credential_id, uuid.UUID(tenant_id)
            )
            if not existing_credential:
                return None
            
            # 准备更新数据
            update_data = {}
            
            # 处理基本信息更新
            if request_data.display_name is not None:
                # 检查显示名称是否与其他凭证冲突
                conflict_credential = await self.supplier_repo.get_by_provider_and_display_name(
                    uuid.UUID(tenant_id),
                    existing_credential.provider_name,
                    request_data.display_name
                )
                if conflict_credential and conflict_credential.id != credential_id:
                    raise ValueError("该显示名称已被使用")
                update_data["display_name"] = request_data.display_name
            
            if request_data.base_url is not None:
                update_data["base_url"] = request_data.base_url
            
            if request_data.model_configs is not None:
                update_data["model_configs"] = request_data.model_configs
            
            if request_data.is_active is not None:
                update_data["is_active"] = request_data.is_active
            
            # 处理API密钥更新（需要重新加密）
            if request_data.api_key:
                encrypted_key = await credential_manager.encrypt_credential(
                    self.db, request_data.api_key
                )
                update_data["encrypted_api_key"] = encrypted_key
            
            # 执行更新
            if update_data:
                credential = await self.supplier_repo.update(credential_id, update_data)
                
                logger.info(
                    "供应商凭证更新成功",
                    request_id=request_id,
                    credential_id=str(credential_id),
                    tenant_id=tenant_id,
                    updated_fields=list(update_data.keys()),
                    operation="update_credential"
                )
                
                return await self._convert_to_response(credential)
            
            # 没有更新数据，返回原凭证信息
            return await self._convert_to_response(existing_credential)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "供应商凭证更新失败",
                request_id=request_id,
                credential_id=str(credential_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="update_credential"
            )
            raise
    
    async def delete_credential(
        self,
        credential_id: uuid.UUID,
        tenant_id: str,
        request_id: str
    ) -> bool:
        """
        删除供应商凭证
        
        Args:
            credential_id: 凭证ID
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            是否删除成功
        """
        try:
            # 检查凭证是否存在
            credential = await self.supplier_repo.get_by_id_in_tenant(
                credential_id, uuid.UUID(tenant_id)
            )
            if not credential:
                return False
            
            # 执行删除
            success = await self.supplier_repo.delete(credential_id)
            
            if success:
                logger.info(
                    "供应商凭证删除成功",
                    request_id=request_id,
                    credential_id=str(credential_id),
                    tenant_id=tenant_id,
                    operation="delete_credential"
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "供应商凭证删除失败",
                request_id=request_id,
                credential_id=str(credential_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="delete_credential"
            )
            raise
    
    async def test_credential(
        self,
        credential_id: uuid.UUID,
        test_request: SupplierTestRequest,
        tenant_id: str,
        request_id: str
    ) -> Optional[SupplierTestResponse]:
        """
        测试供应商API连接
        
        Args:
            credential_id: 凭证ID
            test_request: 测试请求数据
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            测试结果或None
        """
        try:
            # 获取解密的凭证信息
            credential_data = await credential_manager.get_decrypted_credential(
                self.db, str(credential_id), tenant_id
            )
            
            if not credential_data:
                return None
            
            start_time = time.time()
            
            # 根据供应商类型进行测试
            test_result = await self._perform_provider_test(
                credential_data, test_request, request_id
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 构建测试响应
            test_response = SupplierTestResponse(
                success=test_result["success"],
                test_type=test_request.test_type,
                response_time_ms=response_time_ms,
                provider_name=credential_data["provider_name"],
                model_name=test_request.model_name,
                result_data=test_result.get("data"),
                error_message=test_result.get("error_message"),
                error_code=test_result.get("error_code"),
                available_models=test_result.get("available_models"),
                api_version=test_result.get("api_version"),
                rate_limit_info=test_result.get("rate_limit_info")
            )
            
            logger.info(
                "供应商连接测试完成",
                request_id=request_id,
                credential_id=str(credential_id),
                tenant_id=tenant_id,
                success=test_result["success"],
                response_time_ms=response_time_ms,
                operation="test_credential"
            )
            
            return test_response
            
        except Exception as e:
            logger.error(
                "供应商连接测试失败",
                request_id=request_id,
                credential_id=str(credential_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="test_credential"
            )
            raise
    
    async def _perform_provider_test(
        self,
        credential_data: Dict[str, Any],
        test_request: SupplierTestRequest,
        request_id: str
    ) -> Dict[str, Any]:
        """
        执行具体的供应商测试
        
        Args:
            credential_data: 解密的凭证数据
            test_request: 测试请求
            request_id: 请求ID
            
        Returns:
            测试结果字典
        """
        provider_name = credential_data["provider_name"]
        api_key = credential_data["api_key"]
        base_url = credential_data["base_url"]
        
        try:
            # 这里实现基础的连接测试
            # 实际生产环境中应该根据不同供应商实现具体的测试逻辑
            
            if test_request.test_type == "connection":
                # 简单的连接测试
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # 根据供应商构建测试URL
                    if provider_name == "openai":
                        test_url = f"{base_url}/models"
                        headers = {"Authorization": f"Bearer {api_key}"}
                    elif provider_name == "anthropic":
                        test_url = f"{base_url}/v1/messages"
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "anthropic-version": "2023-06-01"
                        }
                    else:
                        # 自定义供应商，只做基础连接测试
                        test_url = base_url
                        headers = {"Authorization": f"Bearer {api_key}"}
                    
                    response = await client.get(test_url, headers=headers)
                    
                    if response.status_code in [200, 401, 403]:
                        # 200表示成功，401/403表示连接正常但权限问题
                        return {
                            "success": response.status_code == 200,
                            "data": {"status_code": response.status_code},
                            "error_message": None if response.status_code == 200 else "API密钥可能无效"
                        }
                    else:
                        return {
                            "success": False,
                            "error_message": f"HTTP {response.status_code}: {response.text[:200]}"
                        }
            
            else:
                # 其他测试类型暂时返回成功
                return {
                    "success": True,
                    "data": {"message": f"{test_request.test_type} 测试完成"}
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "error_message": "连接超时"
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error_message": f"连接错误: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error_message": f"测试失败: {str(e)}"
            }
    
    async def _convert_to_response(self, credential: SupplierCredential) -> SupplierCredentialResponse:
        """
        将凭证实体转换为响应格式
        
        Args:
            credential: 凭证实体
            
        Returns:
            凭证响应格式
        """
        return SupplierCredentialResponse(
            id=credential.id,
            tenant_id=credential.tenant_id,
            provider_name=credential.provider_name,
            display_name=credential.display_name,
            base_url=credential.base_url,
            model_configs=credential.model_configs,
            is_active=credential.is_active,
            created_at=credential.created_at,
            updated_at=credential.updated_at
        )