"""
供应商数据访问层

负责供应商配置相关的数据库操作。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
import logging

from .base import BaseRepository
from ..models.database import ProviderConfigTable
from ..models.schemas.provider import ProviderCredentialsRequest

logger = logging.getLogger(__name__)


class ProviderRepository(BaseRepository[ProviderConfigTable, Dict, Dict]):
    """供应商Repository"""
    
    def __init__(self, db: Session):
        super().__init__(ProviderConfigTable, db)
    
    def get_by_provider_id(self, provider_id: str) -> Optional[ProviderConfigTable]:
        """
        根据供应商ID获取配置
        
        Args:
            provider_id: 供应商ID
            
        Returns:
            ProviderConfigTable: 供应商配置，未找到返回None
        """
        try:
            return self.db.query(self.model).filter(
                self.model.provider_id == provider_id
            ).first()
        except Exception as e:
            logger.error(f"根据供应商ID获取配置失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def get_active_providers(self) -> List[ProviderConfigTable]:
        """
        获取所有活跃的供应商
        
        Returns:
            List[ProviderConfigTable]: 活跃供应商列表
        """
        try:
            return self.db.query(self.model).filter(
                self.model.status == 'active'
            ).order_by(self.model.name).all()
        except Exception as e:
            logger.error(f"获取活跃供应商失败 - 错误: {e}")
            raise
    
    def search_providers(self, query: str) -> List[ProviderConfigTable]:
        """
        搜索供应商
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[ProviderConfigTable]: 匹配的供应商列表
        """
        try:
            search_pattern = f"%{query}%"
            return self.db.query(self.model).filter(
                or_(
                    self.model.name.ilike(search_pattern),
                    self.model.provider_id.ilike(search_pattern),
                    self.model.description.ilike(search_pattern)
                )
            ).order_by(self.model.name).all()
        except Exception as e:
            logger.error(f"搜索供应商失败 - query: {query}, 错误: {e}")
            raise
    
    def get_providers_by_model(self, model_name: str) -> List[ProviderConfigTable]:
        """
        根据模型名称获取支持的供应商
        
        Args:
            model_name: 模型名称
            
        Returns:
            List[ProviderConfigTable]: 支持该模型的供应商列表
        """
        try:
            return self.db.query(self.model).filter(
                and_(
                    self.model.status == 'active',
                    self.model.supported_models.contains([model_name])
                )
            ).order_by(self.model.name).all()
        except Exception as e:
            logger.error(f"根据模型获取供应商失败 - model: {model_name}, 错误: {e}")
            raise
    
    def update_provider_status(self, provider_id: str, status: str) -> bool:
        """
        更新供应商状态
        
        Args:
            provider_id: 供应商ID
            status: 新状态
            
        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.db.query(self.model).filter(
                self.model.provider_id == provider_id
            ).update({"status": status})
            
            if result > 0:
                self.db.commit()
                logger.info(f"成功更新供应商状态 - provider_id: {provider_id}, status: {status}")
                return True
            else:
                logger.warning(f"供应商不存在 - provider_id: {provider_id}")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新供应商状态失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def add_supported_model(self, provider_id: str, model_name: str) -> bool:
        """
        为供应商添加支持的模型
        
        Args:
            provider_id: 供应商ID
            model_name: 模型名称
            
        Returns:
            bool: 是否添加成功
        """
        try:
            provider = self.get_by_provider_id(provider_id)
            if not provider:
                logger.warning(f"供应商不存在 - provider_id: {provider_id}")
                return False
            
            supported_models = provider.supported_models or []
            if model_name not in supported_models:
                supported_models.append(model_name)
                
                self.db.query(self.model).filter(
                    self.model.provider_id == provider_id
                ).update({"supported_models": supported_models})
                
                self.db.commit()
                logger.info(f"成功为供应商添加模型 - provider_id: {provider_id}, model: {model_name}")
                return True
            else:
                logger.info(f"模型已存在 - provider_id: {provider_id}, model: {model_name}")
                return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"添加支持模型失败 - provider_id: {provider_id}, model: {model_name}, 错误: {e}")
            raise
    
    def remove_supported_model(self, provider_id: str, model_name: str) -> bool:
        """
        移除供应商支持的模型
        
        Args:
            provider_id: 供应商ID
            model_name: 模型名称
            
        Returns:
            bool: 是否移除成功
        """
        try:
            provider = self.get_by_provider_id(provider_id)
            if not provider:
                logger.warning(f"供应商不存在 - provider_id: {provider_id}")
                return False
            
            supported_models = provider.supported_models or []
            if model_name in supported_models:
                supported_models.remove(model_name)
                
                self.db.query(self.model).filter(
                    self.model.provider_id == provider_id
                ).update({"supported_models": supported_models})
                
                self.db.commit()
                logger.info(f"成功移除供应商模型 - provider_id: {provider_id}, model: {model_name}")
                return True
            else:
                logger.info(f"模型不存在 - provider_id: {provider_id}, model: {model_name}")
                return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"移除支持模型失败 - provider_id: {provider_id}, model: {model_name}, 错误: {e}")
            raise
    
    def get_provider_statistics(self) -> Dict[str, Any]:
        """
        获取供应商统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_providers,
                    COUNT(*) FILTER (WHERE status = 'active') as active_providers,
                    COUNT(*) FILTER (WHERE status = 'inactive') as inactive_providers,
                    COUNT(*) FILTER (WHERE status = 'disabled') as disabled_providers,
                    AVG(JSONB_ARRAY_LENGTH(supported_models)) as avg_models_per_provider
                FROM provider_configs
            """)).fetchone()
            
            return {
                "total_providers": result[0] or 0,
                "active_providers": result[1] or 0,
                "inactive_providers": result[2] or 0,
                "disabled_providers": result[3] or 0,
                "avg_models_per_provider": float(result[4] or 0)
            }
        except Exception as e:
            logger.error(f"获取供应商统计信息失败 - 错误: {e}")
            raise
    
    def get_all_supported_models(self) -> List[str]:
        """
        获取所有供应商支持的模型列表（去重）
        
        Returns:
            List[str]: 模型名称列表
        """
        try:
            result = self.db.execute(text("""
                SELECT DISTINCT jsonb_array_elements_text(supported_models) as model_name
                FROM provider_configs 
                WHERE status = 'active'
                ORDER BY model_name
            """)).fetchall()
            
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"获取所有支持的模型失败 - 错误: {e}")
            raise
    
    def get_models_by_provider(self, provider_id: str) -> List[str]:
        """
        获取指定供应商支持的模型列表
        
        Args:
            provider_id: 供应商ID
            
        Returns:
            List[str]: 模型名称列表
        """
        try:
            provider = self.get_by_provider_id(provider_id)
            if provider and provider.supported_models:
                return provider.supported_models
            return []
        except Exception as e:
            logger.error(f"获取供应商模型列表失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def batch_update_provider_configs(self, updates: List[Dict[str, Any]]) -> int:
        """
        批量更新供应商配置
        
        Args:
            updates: 更新数据列表，每个字典必须包含provider_id字段
            
        Returns:
            int: 更新的记录数量
        """
        try:
            updated_count = 0
            for update_data in updates:
                if 'provider_id' not in update_data:
                    continue
                
                provider_id = update_data.pop('provider_id')
                result = self.db.query(self.model).filter(
                    self.model.provider_id == provider_id
                ).update(update_data)
                updated_count += result
            
            self.db.commit()
            logger.info(f"成功批量更新 {updated_count} 个供应商配置")
            return updated_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量更新供应商配置失败 - 错误: {e}")
            raise