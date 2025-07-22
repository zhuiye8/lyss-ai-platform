# -*- coding: utf-8 -*-
"""
用户画像分析器模块

基于用户行为数据分析用户特征和偏好，提供个性化推荐服务。
参考架构文档设计，支持多维度用户画像分析和智能推荐系统。

核心功能：
- 用户行为模式分析
- 个性化偏好识别
- 智能推荐生成
- 用户参与度评分
- 同类用户比较分析
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database.user import User, UserStatus
from ..core.database_engine import get_db_session
from ..utils.analytics import (
    calculate_engagement_score,
    analyze_behavior_patterns,
    generate_user_segments,
    calculate_similarity_score
)

logger = logging.getLogger(__name__)

class UserProfileAnalyzer:
    """
    用户画像分析器
    
    基于用户行为数据进行深度分析，生成用户画像和个性化推荐。
    支持多时间段分析、同类用户比较、趋势分析等高级功能。
    """
    
    def __init__(self):
        self.analysis_periods = {
            "daily": 1,
            "weekly": 7, 
            "monthly": 30,
            "quarterly": 90,
            "yearly": 365
        }
        
        # 分析配置
        self.min_activities_for_analysis = 5  # 最小活动数量
        self.similarity_threshold = 0.7  # 用户相似度阈值
        self.trend_analysis_periods = ["weekly", "monthly", "quarterly"]
        
    async def analyze_user_behavior(
        self,
        user_id: str,
        period: str = "monthly",
        include_trends: bool = False,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        分析用户行为模式
        
        Args:
            user_id: 用户ID
            period: 分析时间段
            include_trends: 是否包含趋势分析
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 完整的行为分析结果
        """
        if db is None:
            async with get_db_session() as session:
                return await self._analyze_behavior_impl(
                    user_id, period, include_trends, session
                )
        else:
            return await self._analyze_behavior_impl(
                user_id, period, include_trends, db
            )
    
    async def _analyze_behavior_impl(
        self,
        user_id: str,
        period: str,
        include_trends: bool,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """行为分析实现"""
        try:
            # 验证用户存在性
            user = await self._get_user_basic_info(user_id, db)
            if not user:
                raise ValueError("用户不存在")
            
            days = self.analysis_periods.get(period, 30)
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 1. 基础活动统计
            activity_stats = await self._get_activity_statistics(
                user_id, start_date, db
            )
            
            # 检查活动数量是否足够分析
            if activity_stats["total_activities"] < self.min_activities_for_analysis:
                return {
                    "user_id": user_id,
                    "status": "insufficient_data",
                    "message": f"用户活动数量不足({activity_stats['total_activities']})，需要至少{self.min_activities_for_analysis}次活动",
                    "period": period,
                    "analyzed_at": datetime.utcnow().isoformat()
                }
            
            # 2. 模型使用分析
            model_usage = await self._analyze_model_usage(user_id, start_date, db)
            
            # 3. 对话模式分析
            conversation_patterns = await self._analyze_conversation_patterns(
                user_id, start_date, db
            )
            
            # 4. 活跃时段分析
            active_hours = await self._analyze_active_hours(user_id, start_date, db)
            
            # 5. 功能偏好分析
            feature_preferences = await self._analyze_feature_usage(
                user_id, start_date, db
            )
            
            # 6. 生成用户标签
            user_tags = await self._generate_user_tags(
                activity_stats, model_usage, conversation_patterns, feature_preferences
            )
            
            # 7. 计算参与度评分
            engagement_score = calculate_engagement_score(
                activity_stats, conversation_patterns
            )
            
            # 8. 用户分类
            user_segment = generate_user_segments(
                activity_stats, engagement_score, model_usage
            )
            
            result = {
                "user_id": user_id,
                "status": "success",
                "analysis_period": period,
                "analyzed_at": datetime.utcnow().isoformat(),
                "data_quality": {
                    "total_activities": activity_stats["total_activities"],
                    "active_days": activity_stats["active_days"],
                    "data_sufficiency": "sufficient" if activity_stats["total_activities"] >= self.min_activities_for_analysis else "limited"
                },
                "activity_stats": activity_stats,
                "model_usage": model_usage,
                "conversation_patterns": conversation_patterns,
                "active_hours": active_hours,
                "feature_preferences": feature_preferences,
                "user_tags": user_tags,
                "engagement_score": engagement_score,
                "user_segment": user_segment
            }
            
            # 9. 趋势分析（可选）
            if include_trends:
                trends = await self._analyze_user_trends(user_id, db)
                result["trends"] = trends
            
            return result
            
        except Exception as e:
            logger.error(f"用户行为分析失败 [{user_id}]: {e}")
            return {
                "user_id": user_id,
                "status": "error",
                "error": str(e),
                "analyzed_at": datetime.utcnow().isoformat()
            }
    
    async def update_user_preferences(
        self,
        user_id: str,
        preference_updates: Dict[str, Any],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        更新用户偏好设置
        
        Args:
            user_id: 用户ID
            preference_updates: 偏好更新数据
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 更新结果
        """
        if db is None:
            async with get_db_session() as session:
                return await self._update_preferences_impl(
                    user_id, preference_updates, session
                )
        else:
            return await self._update_preferences_impl(
                user_id, preference_updates, db
            )
    
    async def _update_preferences_impl(
        self,
        user_id: str,
        preference_updates: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """偏好更新实现"""
        try:
            # 获取用户画像
            user_profile = await self._get_user_profile(user_id, db)
            
            if not user_profile:
                # 如果不存在画像，创建新的
                user_profile = await self._create_user_profile(user_id, db)
            
            # 验证偏好数据
            validated_prefs = self._validate_preferences(preference_updates)
            
            # 合并偏好设置
            current_prefs = user_profile.get("preferences", {})
            current_prefs.update(validated_prefs)
            
            # 更新数据库
            await self._save_user_preferences(user_id, current_prefs, db)
            
            # 记录偏好变更
            await self._log_preference_change(user_id, validated_prefs, db)
            
            await db.commit()
            
            logger.info(f"用户偏好更新成功: {user_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "updated_preferences": list(validated_prefs.keys()),
                "message": "偏好设置更新成功"
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"用户偏好更新失败 [{user_id}]: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }
    
    async def get_personalized_recommendations(
        self,
        user_id: str,
        recommendation_type: str = "models",
        limit: int = 10,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        获取个性化推荐
        
        Args:
            user_id: 用户ID
            recommendation_type: 推荐类型 (models, features, settings, content)
            limit: 推荐数量
            db: 数据库会话
            
        Returns:
            List[Dict[str, Any]]: 推荐列表
        """
        if db is None:
            async with get_db_session() as session:
                return await self._get_recommendations_impl(
                    user_id, recommendation_type, limit, session
                )
        else:
            return await self._get_recommendations_impl(
                user_id, recommendation_type, limit, db
            )
    
    async def _get_recommendations_impl(
        self,
        user_id: str,
        recommendation_type: str,
        limit: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """推荐生成实现"""
        try:
            # 获取用户行为分析
            behavior_analysis = await self.analyze_user_behavior(user_id, db=db)
            
            if behavior_analysis["status"] != "success":
                return []
            
            # 根据推荐类型生成推荐
            if recommendation_type == "models":
                return await self._recommend_models(user_id, behavior_analysis, limit, db)
            elif recommendation_type == "features":
                return await self._recommend_features(user_id, behavior_analysis, limit, db)
            elif recommendation_type == "settings":
                return await self._recommend_settings(user_id, behavior_analysis, limit, db)
            elif recommendation_type == "content":
                return await self._recommend_content(user_id, behavior_analysis, limit, db)
            else:
                raise ValueError(f"不支持的推荐类型: {recommendation_type}")
                
        except Exception as e:
            logger.error(f"个性化推荐生成失败 [{user_id}]: {e}")
            return []
    
    async def generate_user_insights(
        self,
        user_id: str,
        include_peer_comparison: bool = True,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        生成用户洞察报告
        
        Args:
            user_id: 用户ID
            include_peer_comparison: 是否包含同类用户比较
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 洞察报告
        """
        if db is None:
            async with get_db_session() as session:
                return await self._generate_insights_impl(
                    user_id, include_peer_comparison, session
                )
        else:
            return await self._generate_insights_impl(
                user_id, include_peer_comparison, db
            )
    
    async def _generate_insights_impl(
        self,
        user_id: str,
        include_peer_comparison: bool,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """洞察生成实现"""
        try:
            # 多周期行为分析
            analyses = {}
            for period in self.trend_analysis_periods:
                analyses[period] = await self.analyze_user_behavior(
                    user_id, period, db=db
                )
            
            # 趋势分析
            trends = await self._analyze_user_trends_from_analyses(analyses)
            
            # 同类用户比较
            peer_comparison = None
            if include_peer_comparison:
                peer_comparison = await self._compare_with_peer_users(
                    user_id, analyses["monthly"], db
                )
            
            # 改进建议
            improvement_suggestions = await self._generate_improvement_suggestions(
                user_id, analyses["monthly"], trends
            )
            
            # 生成洞察摘要
            insights_summary = await self._generate_insights_summary(
                analyses["monthly"], trends, peer_comparison
            )
            
            return {
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "current_period": analyses["monthly"],
                "trends": trends,
                "peer_comparison": peer_comparison,
                "improvement_suggestions": improvement_suggestions,
                "insights_summary": insights_summary,
                "data_quality": {
                    "analysis_periods": list(analyses.keys()),
                    "data_sufficiency": all(
                        analysis.get("status") == "success" 
                        for analysis in analyses.values()
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"用户洞察生成失败 [{user_id}]: {e}")
            return {
                "user_id": user_id,
                "status": "error",
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    # 私有辅助方法
    async def _get_user_basic_info(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """获取用户基本信息"""
        stmt = select(User).where(
            and_(User.id == user_id, User.status.in_([
                UserStatus.ACTIVE, UserStatus.INACTIVE
            ]))
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "status": user.status.value,
                "created_at": user.created_at,
                "tenant_id": user.tenant_id
            }
        return None
    
    async def _get_activity_statistics(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """获取活动统计（占位符方法）"""
        # 这里应该从user_activities表获取数据
        # 暂时返回模拟数据
        return {
            "total_activities": 45,
            "active_days": 18,
            "avg_activities_per_day": 2.5,
            "last_activity": datetime.utcnow().isoformat(),
            "activity_types": {
                "chat_message": 30,
                "login": 18,
                "feature_usage": 15,
                "model_usage": 12
            }
        }
    
    async def _analyze_model_usage(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """分析模型使用情况（占位符方法）"""
        # 这里应该从活动表分析模型使用
        return {
            "favorite_models": ["gpt-4", "claude-3", "deepseek"],
            "model_distribution": {
                "gpt-4": {"count": 20, "percentage": 45.5},
                "claude-3": {"count": 15, "percentage": 34.1},
                "deepseek": {"count": 9, "percentage": 20.4}
            },
            "total_model_calls": 44,
            "unique_models_used": 3
        }
    
    async def _analyze_conversation_patterns(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """分析对话模式（占位符方法）"""
        return {
            "avg_messages_per_conversation": 8.5,
            "conversation_length_distribution": {
                "short": 12,    # 1-5条消息
                "medium": 18,   # 6-20条消息  
                "long": 4       # 21+条消息
            },
            "popular_topics": {
                "技术问题": 15,
                "代码调试": 12,
                "产品咨询": 8
            },
            "peak_conversation_hours": [9, 14, 20]
        }
    
    async def _analyze_active_hours(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, int]:
        """分析活跃时段（占位符方法）"""
        return {
            "morning": 15,    # 6-12点
            "afternoon": 20,  # 12-18点  
            "evening": 18,    # 18-24点
            "night": 2        # 0-6点
        }
    
    async def _analyze_feature_usage(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """分析功能使用（占位符方法）"""
        return {
            "most_used_features": ["对话", "模型切换", "历史记录"],
            "feature_frequency": {
                "chat": 30,
                "model_switch": 15,
                "history": 12,
                "export": 3
            }
        }
    
    async def _generate_user_tags(
        self,
        activity_stats: Dict[str, Any],
        model_usage: Dict[str, Any], 
        conversation_patterns: Dict[str, Any],
        feature_preferences: Dict[str, Any]
    ) -> List[str]:
        """生成用户标签"""
        tags = []
        
        # 基于活跃度的标签
        if activity_stats["avg_activities_per_day"] > 3:
            tags.append("高活跃用户")
        elif activity_stats["avg_activities_per_day"] > 1:
            tags.append("中等活跃用户")
        else:
            tags.append("低活跃用户")
        
        # 基于模型使用的标签
        favorite_model = model_usage["favorite_models"][0] if model_usage["favorite_models"] else None
        if favorite_model:
            tags.append(f"{favorite_model}偏好用户")
        
        # 基于对话模式的标签
        avg_length = conversation_patterns["avg_messages_per_conversation"]
        if avg_length > 15:
            tags.append("深度对话用户")
        elif avg_length > 5:
            tags.append("标准对话用户") 
        else:
            tags.append("简短对话用户")
        
        return tags
    
    def _validate_preferences(
        self,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证偏好数据"""
        validated = {}
        
        # 定义允许的偏好字段和验证规则
        allowed_preferences = {
            "language": ["zh-CN", "en-US", "ja-JP"],
            "theme": ["light", "dark", "auto"],
            "timezone": str,
            "notification_enabled": bool,
            "default_model": str,
            "response_format": ["text", "markdown", "html"]
        }
        
        for key, value in preferences.items():
            if key in allowed_preferences:
                expected_type = allowed_preferences[key]
                
                if isinstance(expected_type, list):
                    if value in expected_type:
                        validated[key] = value
                elif isinstance(expected_type, type):
                    if isinstance(value, expected_type):
                        validated[key] = value
        
        return validated
    
    async def _get_user_profile(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """获取用户画像（占位符方法）"""
        # 这里应该从user_profiles表获取
        return None
    
    async def _create_user_profile(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """创建用户画像（占位符方法）"""
        # 这里应该创建新的UserProfile记录
        return {"preferences": {}}
    
    async def _save_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        db: AsyncSession
    ):
        """保存用户偏好（占位符方法）"""
        # 这里应该更新user_profiles表
        pass
    
    async def _log_preference_change(
        self,
        user_id: str,
        changes: Dict[str, Any],
        db: AsyncSession
    ):
        """记录偏好变更（占位符方法）"""
        # 这里应该记录到user_events表
        pass
    
    async def _recommend_models(
        self,
        user_id: str,
        behavior_analysis: Dict[str, Any],
        limit: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """推荐模型（占位符方法）"""
        return [
            {"model": "gpt-4-turbo", "reason": "基于您的复杂对话需求", "score": 0.95},
            {"model": "claude-3-sonnet", "reason": "适合您的技术类问题", "score": 0.88}
        ][:limit]
    
    async def _recommend_features(
        self,
        user_id: str,
        behavior_analysis: Dict[str, Any],
        limit: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """推荐功能（占位符方法）"""
        return [
            {"feature": "代码高亮", "reason": "您经常讨论技术问题", "score": 0.92},
            {"feature": "对话导出", "reason": "长对话记录管理", "score": 0.85}
        ][:limit]
    
    async def _recommend_settings(
        self,
        user_id: str,
        behavior_analysis: Dict[str, Any],
        limit: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """推荐设置（占位符方法）"""
        return [
            {"setting": "深色主题", "reason": "夜间使用频繁", "score": 0.78}
        ][:limit]
    
    async def _recommend_content(
        self,
        user_id: str,
        behavior_analysis: Dict[str, Any],
        limit: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """推荐内容（占位符方法）"""
        return []
    
    async def _analyze_user_trends(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """分析用户趋势（占位符方法）"""
        return {
            "activity_trend": "increasing",
            "engagement_trend": "stable",
            "model_preference_changes": []
        }
    
    async def _analyze_user_trends_from_analyses(
        self,
        analyses: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """从多周期分析中提取趋势"""
        return {
            "activity_trend": "increasing",
            "engagement_trend": "stable", 
            "model_usage_evolution": {}
        }
    
    async def _compare_with_peer_users(
        self,
        user_id: str,
        current_analysis: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """同类用户比较（占位符方法）"""
        return {
            "percentile_rank": 75,
            "similar_users_count": 156,
            "comparison_metrics": {
                "activity_level": "above_average",
                "engagement_score": "high"
            }
        }
    
    async def _generate_improvement_suggestions(
        self,
        user_id: str,
        current_analysis: Dict[str, Any],
        trends: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成改进建议"""
        suggestions = []
        
        # 基于参与度评分生成建议
        engagement_score = current_analysis.get("engagement_score", 0)
        if engagement_score < 50:
            suggestions.append({
                "category": "participation",
                "suggestion": "尝试更多功能探索，提高平台使用深度",
                "priority": "medium",
                "expected_benefit": "提升AI助手使用效率"
            })
        
        return suggestions
    
    async def _generate_insights_summary(
        self,
        current_analysis: Dict[str, Any],
        trends: Dict[str, Any],
        peer_comparison: Optional[Dict[str, Any]]
    ) -> str:
        """生成洞察摘要"""
        summary_parts = []
        
        if current_analysis.get("status") == "success":
            engagement = current_analysis.get("engagement_score", 0)
            summary_parts.append(f"您的平台参与度评分为{engagement}分")
            
            if engagement > 80:
                summary_parts.append("，表现优异")
            elif engagement > 60:
                summary_parts.append("，表现良好")
            else:
                summary_parts.append("，还有提升空间")
        
        if peer_comparison:
            rank = peer_comparison.get("percentile_rank", 50)
            summary_parts.append(f"，在同类用户中排名前{100-rank}%")
        
        return "".join(summary_parts) + "。"

# 全局用户画像分析器实例
profile_analyzer = UserProfileAnalyzer()