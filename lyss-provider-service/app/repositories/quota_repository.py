"""
配额数据访问层

负责租户配额相关的数据库操作，包括配额管理、使用量追踪、限制检查等。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func
from datetime import datetime, timedelta
import logging

from .base import BaseRepository
from ..models.database import TenantQuotaTable
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class QuotaRepository(BaseRepository[TenantQuotaTable, Dict, Dict]):
    """租户配额Repository"""
    
    def __init__(self, db: Session):
        super().__init__(TenantQuotaTable, db)
    
    def get_tenant_quota(self, tenant_id: str, quota_type: str) -> Optional[TenantQuotaTable]:
        """
        获取租户指定类型的配额设置
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型 (daily_requests, daily_tokens, monthly_requests, monthly_tokens)
            
        Returns:
            TenantQuotaTable: 配额设置，未找到返回None
        """
        try:
            return self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.quota_type == quota_type
                )
            ).first()
        except Exception as e:
            logger.error(f"获取租户配额失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def get_all_tenant_quotas(self, tenant_id: str) -> List[TenantQuotaTable]:
        """
        获取租户所有配额设置
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[TenantQuotaTable]: 配额设置列表
        """
        try:
            return self.db.query(self.model).filter(
                self.model.tenant_id == tenant_id
            ).order_by(self.model.quota_type).all()
        except Exception as e:
            logger.error(f"获取租户所有配额失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def create_default_quotas(self, tenant_id: str) -> List[TenantQuotaTable]:
        """
        为租户创建默认配额设置
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[TenantQuotaTable]: 创建的配额设置列表
        """
        try:
            default_quotas = [
                {
                    "tenant_id": tenant_id,
                    "quota_type": "daily_requests",
                    "quota_limit": settings.default_daily_request_limit,
                    "used_amount": 0.0,
                    "reset_at": self._get_next_daily_reset(),
                    "is_active": True,
                    "metadata": {"created_as_default": True}
                },
                {
                    "tenant_id": tenant_id,
                    "quota_type": "daily_tokens",
                    "quota_limit": settings.default_daily_token_limit,
                    "used_amount": 0.0,
                    "reset_at": self._get_next_daily_reset(),
                    "is_active": True,
                    "metadata": {"created_as_default": True}
                },
                {
                    "tenant_id": tenant_id,
                    "quota_type": "monthly_requests",
                    "quota_limit": settings.default_monthly_request_limit,
                    "used_amount": 0.0,
                    "reset_at": self._get_next_monthly_reset(),
                    "is_active": True,
                    "metadata": {"created_as_default": True}
                },
                {
                    "tenant_id": tenant_id,
                    "quota_type": "monthly_tokens",
                    "quota_limit": settings.default_monthly_token_limit,
                    "used_amount": 0.0,
                    "reset_at": self._get_next_monthly_reset(),
                    "is_active": True,
                    "metadata": {"created_as_default": True}
                }
            ]
            
            quota_objects = []
            for quota_data in default_quotas:
                quota_obj = TenantQuotaTable(**quota_data)
                quota_objects.append(quota_obj)
            
            self.db.add_all(quota_objects)
            self.db.commit()
            
            for quota_obj in quota_objects:
                self.db.refresh(quota_obj)
            
            logger.info(f"成功为租户创建默认配额 - tenant_id: {tenant_id}")
            return quota_objects
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建默认配额失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def check_quota_limit(self, tenant_id: str, quota_type: str, amount: float) -> Tuple[bool, Dict[str, Any]]:
        """
        检查配额是否超限
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 要消耗的量
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (是否允许, 配额信息)
        """
        try:
            quota = self.get_tenant_quota(tenant_id, quota_type)
            
            if not quota:
                # 如果没有配额设置，创建默认配额
                self.create_default_quotas(tenant_id)
                quota = self.get_tenant_quota(tenant_id, quota_type)
            
            if not quota or not quota.is_active:
                return False, {"error": "配额未激活或不存在"}
            
            # 检查是否需要重置
            if datetime.utcnow() >= quota.reset_at:
                self._reset_quota(quota)
                self.db.refresh(quota)
            
            # 检查是否会超限
            new_used_amount = quota.used_amount + amount
            remaining = quota.quota_limit - quota.used_amount
            
            quota_info = {
                "quota_limit": quota.quota_limit,
                "used_amount": quota.used_amount,
                "remaining": remaining,
                "would_use": amount,
                "would_remain": quota.quota_limit - new_used_amount,
                "reset_at": quota.reset_at
            }
            
            if new_used_amount <= quota.quota_limit:
                return True, quota_info
            else:
                quota_info["error"] = "配额不足"
                return False, quota_info
        except Exception as e:
            logger.error(f"检查配额限制失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def consume_quota(self, tenant_id: str, quota_type: str, amount: float) -> bool:
        """
        消耗配额
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 消耗量
            
        Returns:
            bool: 是否成功消耗
        """
        try:
            quota = self.get_tenant_quota(tenant_id, quota_type)
            
            if not quota or not quota.is_active:
                logger.warning(f"配额不存在或未激活 - tenant_id: {tenant_id}, type: {quota_type}")
                return False
            
            # 检查是否需要重置
            if datetime.utcnow() >= quota.reset_at:
                self._reset_quota(quota)
            
            # 检查配额是否足够
            if quota.used_amount + amount > quota.quota_limit:
                logger.warning(f"配额不足 - tenant_id: {tenant_id}, type: {quota_type}, requested: {amount}, available: {quota.quota_limit - quota.used_amount}")
                return False
            
            # 更新使用量
            quota.used_amount += amount
            quota.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"成功消耗配额 - tenant_id: {tenant_id}, type: {quota_type}, amount: {amount}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"消耗配额失败 - tenant_id: {tenant_id}, type: {quota_type}, amount: {amount}, 错误: {e}")
            raise
    
    def batch_consume_quota(self, consumptions: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        批量消耗配额
        
        Args:
            consumptions: 消耗配额列表，每项包含tenant_id, quota_type, amount
            
        Returns:
            Dict[str, bool]: 各个消耗操作的结果
        """
        try:
            results = {}
            
            for i, consumption in enumerate(consumptions):
                key = f"{consumption['tenant_id']}_{consumption['quota_type']}_{i}"
                try:
                    success = self.consume_quota(
                        consumption['tenant_id'],
                        consumption['quota_type'],
                        consumption['amount']
                    )
                    results[key] = success
                except Exception as e:
                    logger.error(f"批量消耗配额项失败 - {consumption}, 错误: {e}")
                    results[key] = False
            
            return results
        except Exception as e:
            logger.error(f"批量消耗配额失败 - 错误: {e}")
            raise
    
    def update_quota_limit(self, tenant_id: str, quota_type: str, new_limit: float) -> bool:
        """
        更新配额限制
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            new_limit: 新的配额限制
            
        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.quota_type == quota_type
                )
            ).update({
                "quota_limit": new_limit,
                "updated_at": datetime.utcnow()
            })
            
            if result > 0:
                self.db.commit()
                logger.info(f"成功更新配额限制 - tenant_id: {tenant_id}, type: {quota_type}, limit: {new_limit}")
                return True
            else:
                logger.warning(f"配额不存在 - tenant_id: {tenant_id}, type: {quota_type}")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新配额限制失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def reset_quota(self, tenant_id: str, quota_type: str) -> bool:
        """
        重置配额使用量
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            
        Returns:
            bool: 是否重置成功
        """
        try:
            quota = self.get_tenant_quota(tenant_id, quota_type)
            if not quota:
                return False
            
            self._reset_quota(quota)
            self.db.commit()
            
            logger.info(f"成功重置配额 - tenant_id: {tenant_id}, type: {quota_type}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"重置配额失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def get_quota_usage_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取租户配额使用统计
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            Dict[str, Any]: 配额使用统计
        """
        try:
            quotas = self.get_all_tenant_quotas(tenant_id)
            
            stats = {
                "total_quotas": len(quotas),
                "active_quotas": 0,
                "quotas": {}
            }
            
            for quota in quotas:
                if quota.is_active:
                    stats["active_quotas"] += 1
                
                # 检查是否需要重置
                if datetime.utcnow() >= quota.reset_at:
                    self._reset_quota(quota)
                
                usage_percentage = (quota.used_amount / quota.quota_limit * 100) if quota.quota_limit > 0 else 0
                
                stats["quotas"][quota.quota_type] = {
                    "limit": quota.quota_limit,
                    "used": quota.used_amount,
                    "remaining": quota.quota_limit - quota.used_amount,
                    "usage_percentage": round(usage_percentage, 2),
                    "reset_at": quota.reset_at,
                    "is_active": quota.is_active,
                    "is_exceeded": quota.used_amount >= quota.quota_limit
                }
            
            self.db.commit()  # 提交可能的重置操作
            return stats
        except Exception as e:
            logger.error(f"获取配额使用统计失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_approaching_limit_quotas(self, threshold_percentage: float = 80.0) -> List[Dict[str, Any]]:
        """
        获取接近限制的配额列表
        
        Args:
            threshold_percentage: 阈值百分比
            
        Returns:
            List[Dict[str, Any]]: 接近限制的配额列表
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    tenant_id,
                    quota_type,
                    quota_limit,
                    used_amount,
                    (used_amount / quota_limit * 100) as usage_percentage,
                    reset_at
                FROM tenant_quotas 
                WHERE is_active = true
                    AND quota_limit > 0
                    AND (used_amount / quota_limit * 100) >= :threshold
                ORDER BY usage_percentage DESC
            """), {"threshold": threshold_percentage}).fetchall()
            
            return [
                {
                    "tenant_id": row[0],
                    "quota_type": row[1],
                    "quota_limit": row[2],
                    "used_amount": row[3],
                    "usage_percentage": float(row[4]),
                    "reset_at": row[5]
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"获取接近限制的配额失败 - 错误: {e}")
            raise
    
    def get_quota_history(
        self, 
        tenant_id: str, 
        quota_type: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取配额历史使用情况（需要配合定时任务记录历史数据）
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            days: 查询天数
            
        Returns:
            List[Dict[str, Any]]: 历史使用数据
        """
        try:
            # 这里假设有一个quota_usage_history表记录每日使用量
            # 实际实现中需要配合定时任务来记录历史数据
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            result = self.db.execute(text("""
                SELECT 
                    usage_date,
                    used_amount,
                    quota_limit,
                    (used_amount / quota_limit * 100) as usage_percentage
                FROM quota_usage_history 
                WHERE tenant_id = :tenant_id 
                    AND quota_type = :quota_type
                    AND usage_date >= :start_date 
                    AND usage_date <= :end_date
                ORDER BY usage_date ASC
            """), {
                "tenant_id": tenant_id,
                "quota_type": quota_type,
                "start_date": start_date,
                "end_date": end_date
            }).fetchall()
            
            return [
                {
                    "date": row[0],
                    "used_amount": row[1],
                    "quota_limit": row[2],
                    "usage_percentage": float(row[3] or 0)
                }
                for row in result
            ]
        except Exception as e:
            # 如果历史表不存在，返回空列表
            logger.warning(f"获取配额历史失败（可能历史表不存在） - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            return []
    
    def cleanup_expired_quotas(self) -> int:
        """
        清理过期的配额记录
        
        Returns:
            int: 清理的记录数量
        """
        try:
            # 清理超过3个月未更新且已禁用的配额
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            result = self.db.query(self.model).filter(
                and_(
                    self.model.is_active == False,
                    self.model.updated_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"成功清理 {result} 条过期配额记录")
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"清理过期配额失败 - 错误: {e}")
            raise
    
    def _reset_quota(self, quota: TenantQuotaTable) -> None:
        """
        内部方法：重置配额
        
        Args:
            quota: 配额对象
        """
        quota.used_amount = 0.0
        quota.updated_at = datetime.utcnow()
        
        # 设置下一个重置时间
        if quota.quota_type in ["daily_requests", "daily_tokens"]:
            quota.reset_at = self._get_next_daily_reset()
        elif quota.quota_type in ["monthly_requests", "monthly_tokens"]:
            quota.reset_at = self._get_next_monthly_reset()
    
    def _get_next_daily_reset(self) -> datetime:
        """获取下一个日重置时间"""
        now = datetime.utcnow()
        next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return next_reset
    
    def _get_next_monthly_reset(self) -> datetime:
        """获取下一个月重置时间"""
        now = datetime.utcnow()
        if now.month == 12:
            next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return next_reset