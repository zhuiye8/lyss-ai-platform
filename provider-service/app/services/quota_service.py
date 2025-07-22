"""
配额服务

处理租户配额相关的业务逻辑，包括配额检查、消耗记录、
限制管理等功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..repositories.quota_repository import QuotaRepository
from ..models.database import TenantQuotaTable
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class QuotaService:
    """配额服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.quota_repo = QuotaRepository(db)
    
    def get_tenant_quotas(self, tenant_id: str) -> List[TenantQuotaTable]:
        """
        获取租户所有配额设置
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[TenantQuotaTable]: 配额设置列表
        """
        try:
            quotas = self.quota_repo.get_all_tenant_quotas(tenant_id)
            
            # 如果没有配额设置，创建默认配额
            if not quotas:
                logger.info(f"租户 {tenant_id} 没有配额设置，创建默认配额")
                quotas = self.quota_repo.create_default_quotas(tenant_id)
            
            return quotas
            
        except Exception as e:
            logger.error(f"获取租户配额失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_quota_by_type(self, tenant_id: str, quota_type: str) -> Optional[TenantQuotaTable]:
        """
        获取指定类型的配额设置
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            
        Returns:
            Optional[TenantQuotaTable]: 配额设置
        """
        try:
            quota = self.quota_repo.get_tenant_quota(tenant_id, quota_type)
            
            # 如果指定类型的配额不存在，创建默认配额
            if not quota:
                logger.info(f"租户 {tenant_id} 的 {quota_type} 配额不存在，创建默认配额")
                self.quota_repo.create_default_quotas(tenant_id)
                quota = self.quota_repo.get_tenant_quota(tenant_id, quota_type)
            
            return quota
            
        except Exception as e:
            logger.error(f"获取配额失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def check_quota_availability(
        self,
        tenant_id: str,
        quota_type: str,
        requested_amount: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查配额是否可用
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            requested_amount: 请求的配额量
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (是否可用, 配额信息)
        """
        try:
            return self.quota_repo.check_quota_limit(tenant_id, quota_type, requested_amount)
        except Exception as e:
            logger.error(f"检查配额可用性失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def consume_quota(
        self,
        tenant_id: str,
        quota_type: str,
        amount: float,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        消耗配额
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 消耗量
            metadata: 元数据（可选）
            
        Returns:
            bool: 是否成功消耗
        """
        try:
            success = self.quota_repo.consume_quota(tenant_id, quota_type, amount)
            
            if success:
                logger.info(f"配额消耗成功 - tenant_id: {tenant_id}, type: {quota_type}, amount: {amount}")
                
                # 记录消耗历史（如果需要）
                if metadata:
                    self._record_quota_usage(tenant_id, quota_type, amount, metadata)
            else:
                logger.warning(f"配额消耗失败 - tenant_id: {tenant_id}, type: {quota_type}, amount: {amount}")
            
            return success
            
        except Exception as e:
            logger.error(f"消耗配额失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def batch_consume_quota(self, consumptions: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        批量消耗配额
        
        Args:
            consumptions: 消耗配额列表
            
        Returns:
            Dict[str, bool]: 各个消耗操作的结果
        """
        try:
            return self.quota_repo.batch_consume_quota(consumptions)
        except Exception as e:
            logger.error(f"批量消耗配额失败 - 错误: {e}")
            raise
    
    def update_quota_limit(
        self,
        tenant_id: str,
        quota_type: str,
        new_limit: float,
        reason: str = None
    ) -> bool:
        """
        更新配额限制
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            new_limit: 新的配额限制
            reason: 更新原因（可选）
            
        Returns:
            bool: 是否更新成功
        """
        try:
            success = self.quota_repo.update_quota_limit(tenant_id, quota_type, new_limit)
            
            if success:
                logger.info(f"配额限制更新成功 - tenant_id: {tenant_id}, type: {quota_type}, limit: {new_limit}, reason: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"更新配额限制失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def reset_quota(self, tenant_id: str, quota_type: str, reason: str = None) -> bool:
        """
        重置配额使用量
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            reason: 重置原因（可选）
            
        Returns:
            bool: 是否重置成功
        """
        try:
            success = self.quota_repo.reset_quota(tenant_id, quota_type)
            
            if success:
                logger.info(f"配额重置成功 - tenant_id: {tenant_id}, type: {quota_type}, reason: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"重置配额失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def get_quota_usage_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取租户配额使用统计
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            Dict[str, Any]: 配额使用统计
        """
        try:
            stats = self.quota_repo.get_quota_usage_stats(tenant_id)
            
            # 添加预警信息
            warnings = []
            for quota_type, quota_info in stats.get("quotas", {}).items():
                usage_percentage = quota_info.get("usage_percentage", 0)
                
                if usage_percentage >= 95:
                    warnings.append({
                        "type": quota_type,
                        "level": "critical",
                        "message": f"{quota_type} 配额使用率已达到 {usage_percentage}%"
                    })
                elif usage_percentage >= 80:
                    warnings.append({
                        "type": quota_type,
                        "level": "warning",
                        "message": f"{quota_type} 配额使用率已达到 {usage_percentage}%"
                    })
            
            stats["warnings"] = warnings
            stats["generated_at"] = datetime.utcnow().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"获取配额使用统计失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_approaching_limit_quotas(
        self,
        threshold_percentage: float = 80.0
    ) -> List[Dict[str, Any]]:
        """
        获取接近限制的配额列表
        
        Args:
            threshold_percentage: 阈值百分比
            
        Returns:
            List[Dict[str, Any]]: 接近限制的配额列表
        """
        try:
            return self.quota_repo.get_approaching_limit_quotas(threshold_percentage)
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
        获取配额历史使用情况
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            days: 查询天数
            
        Returns:
            List[Dict[str, Any]]: 历史使用数据
        """
        try:
            return self.quota_repo.get_quota_history(tenant_id, quota_type, days)
        except Exception as e:
            logger.error(f"获取配额历史失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def predict_quota_exhaustion(
        self,
        tenant_id: str,
        quota_type: str,
        days_to_analyze: int = 7
    ) -> Dict[str, Any]:
        """
        预测配额耗尽时间
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            days_to_analyze: 分析天数
            
        Returns:
            Dict[str, Any]: 预测结果
        """
        try:
            quota = self.quota_repo.get_tenant_quota(tenant_id, quota_type)
            if not quota:
                return {"error": "配额不存在"}
            
            # 获取历史数据
            history = self.quota_repo.get_quota_history(tenant_id, quota_type, days_to_analyze)
            
            if len(history) < 2:
                return {"error": "历史数据不足，无法进行预测"}
            
            # 计算平均日使用量
            total_usage = sum(day["used_amount"] for day in history)
            avg_daily_usage = total_usage / len(history)
            
            if avg_daily_usage <= 0:
                return {
                    "prediction": "无使用量",
                    "message": "当前无使用量，无法预测耗尽时间"
                }
            
            # 预测剩余天数
            remaining_quota = quota.quota_limit - quota.used_amount
            days_remaining = remaining_quota / avg_daily_usage
            
            # 预测耗尽日期
            exhaustion_date = datetime.utcnow() + timedelta(days=days_remaining)
            
            return {
                "tenant_id": tenant_id,
                "quota_type": quota_type,
                "current_usage": quota.used_amount,
                "quota_limit": quota.quota_limit,
                "remaining_quota": remaining_quota,
                "avg_daily_usage": round(avg_daily_usage, 2),
                "predicted_days_remaining": round(days_remaining, 1),
                "predicted_exhaustion_date": exhaustion_date.isoformat(),
                "confidence": "medium" if len(history) >= 7 else "low",
                "analyzed_days": len(history),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"预测配额耗尽失败 - tenant_id: {tenant_id}, type: {quota_type}, 错误: {e}")
            raise
    
    def create_quota_alert_rules(
        self,
        tenant_id: str,
        rules: List[Dict[str, Any]]
    ) -> List[str]:
        """
        创建配额告警规则
        
        Args:
            tenant_id: 租户ID
            rules: 告警规则列表
            
        Returns:
            List[str]: 创建的规则ID列表
        """
        try:
            # 这里可以集成告警系统
            created_rules = []
            
            for rule in rules:
                quota_type = rule.get("quota_type")
                threshold = rule.get("threshold", 80)
                alert_type = rule.get("alert_type", "email")
                
                # 验证规则
                if not quota_type or not (0 < threshold <= 100):
                    continue
                
                rule_id = f"alert_{tenant_id}_{quota_type}_{threshold}"
                
                # 在实际实现中，这里应该存储到告警规则表
                logger.info(f"创建配额告警规则 - tenant_id: {tenant_id}, rule_id: {rule_id}")
                created_rules.append(rule_id)
            
            return created_rules
            
        except Exception as e:
            logger.error(f"创建配额告警规则失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def check_and_trigger_alerts(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        检查并触发配额告警
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[Dict[str, Any]]: 触发的告警列表
        """
        try:
            # 获取接近限制的配额
            approaching_quotas = self.quota_repo.get_approaching_limit_quotas(80.0)
            
            # 过滤当前租户的配额
            tenant_approaching = [
                quota for quota in approaching_quotas
                if quota.get("tenant_id") == tenant_id
            ]
            
            alerts = []
            for quota in tenant_approaching:
                alert = {
                    "tenant_id": tenant_id,
                    "quota_type": quota["quota_type"],
                    "usage_percentage": quota["usage_percentage"],
                    "remaining_quota": quota["quota_limit"] - quota["used_amount"],
                    "alert_level": self._get_alert_level(quota["usage_percentage"]),
                    "message": self._generate_alert_message(quota),
                    "timestamp": datetime.utcnow().isoformat()
                }
                alerts.append(alert)
            
            # 在实际实现中，这里应该发送告警通知
            if alerts:
                logger.warning(f"租户 {tenant_id} 触发 {len(alerts)} 个配额告警")
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查配额告警失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def cleanup_expired_quotas(self) -> int:
        """
        清理过期的配额记录
        
        Returns:
            int: 清理的记录数量
        """
        try:
            return self.quota_repo.cleanup_expired_quotas()
        except Exception as e:
            logger.error(f"清理过期配额失败 - 错误: {e}")
            raise
    
    def _record_quota_usage(
        self,
        tenant_id: str,
        quota_type: str,
        amount: float,
        metadata: Dict[str, Any]
    ) -> None:
        """
        记录配额使用历史（内部方法）
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 使用量
            metadata: 元数据
        """
        try:
            # 在实际实现中，这里应该记录到配额使用历史表
            usage_record = {
                "tenant_id": tenant_id,
                "quota_type": quota_type,
                "amount": amount,
                "metadata": metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.debug(f"记录配额使用历史: {usage_record}")
            
        except Exception as e:
            logger.error(f"记录配额使用历史失败 - 错误: {e}")
            # 不抛出异常，因为这不应该影响主要业务逻辑
    
    def _get_alert_level(self, usage_percentage: float) -> str:
        """
        根据使用率获取告警级别
        
        Args:
            usage_percentage: 使用率百分比
            
        Returns:
            str: 告警级别
        """
        if usage_percentage >= 95:
            return "critical"
        elif usage_percentage >= 90:
            return "high"
        elif usage_percentage >= 80:
            return "medium"
        else:
            return "low"
    
    def _generate_alert_message(self, quota: Dict[str, Any]) -> str:
        """
        生成告警消息
        
        Args:
            quota: 配额信息
            
        Returns:
            str: 告警消息
        """
        usage_percentage = quota["usage_percentage"]
        quota_type = quota["quota_type"]
        
        if usage_percentage >= 95:
            return f"{quota_type} 配额即将耗尽（已使用 {usage_percentage}%），请及时处理"
        elif usage_percentage >= 90:
            return f"{quota_type} 配额使用率过高（已使用 {usage_percentage}%），建议关注"
        else:
            return f"{quota_type} 配额使用率达到 {usage_percentage}%，请注意监控"