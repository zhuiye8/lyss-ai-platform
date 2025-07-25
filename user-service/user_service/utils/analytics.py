# -*- coding: utf-8 -*-
"""
用户分析工具模块

提供用户行为分析、参与度计算、用户分群等核心算法实现。
基于数据科学方法，支持用户画像生成和个性化推荐系统。

核心功能：
- 用户参与度评分算法
- 行为模式识别和分析
- 用户分群和相似度计算
- 趋势分析和预测
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

def calculate_engagement_score(
    activity_stats: Dict[str, Any],
    conversation_patterns: Dict[str, Any]
) -> float:
    """
    计算用户参与度评分 (0-100分)
    
    评分算法基于四个维度：
    1. 活跃度权重 (30%) - 基于登录频率和活跃天数
    2. 会话质量权重 (25%) - 基于平均会话时长
    3. 对话深度权重 (25%) - 基于平均消息数和对话复杂度
    4. 一致性权重 (20%) - 基于使用模式的一致性
    
    Args:
        activity_stats: 活动统计数据
        conversation_patterns: 对话模式数据
        
    Returns:
        float: 参与度评分 (0-100)
    """
    try:
        total_score = 0.0
        
        # 1. 活跃度评分 (30分)
        active_days = activity_stats.get("active_days", 0)
        total_activities = activity_stats.get("total_activities", 0)
        
        # 活跃天数得分 (最多15分)
        activity_score = min(active_days * 0.5, 15.0)
        
        # 活动频率得分 (最多15分) 
        avg_activities = activity_stats.get("avg_activities_per_day", 0)
        frequency_score = min(avg_activities * 2.0, 15.0)
        
        activity_total = activity_score + frequency_score
        total_score += activity_total
        
        # 2. 会话质量评分 (25分)
        avg_messages = conversation_patterns.get("avg_messages_per_conversation", 0)
        
        # 基于对话长度的质量评分
        if avg_messages >= 10:
            quality_score = 25.0
        elif avg_messages >= 5:
            quality_score = 20.0
        elif avg_messages >= 3:
            quality_score = 15.0
        elif avg_messages >= 1:
            quality_score = 10.0
        else:
            quality_score = 0.0
            
        total_score += quality_score
        
        # 3. 对话深度评分 (25分)
        length_dist = conversation_patterns.get("conversation_length_distribution", {})
        long_conversations = length_dist.get("long", 0)
        medium_conversations = length_dist.get("medium", 0)
        short_conversations = length_dist.get("short", 0)
        
        total_conversations = long_conversations + medium_conversations + short_conversations
        
        if total_conversations > 0:
            # 长对话比例权重最高
            long_ratio = long_conversations / total_conversations
            medium_ratio = medium_conversations / total_conversations
            
            depth_score = (long_ratio * 25.0 + medium_ratio * 15.0)
        else:
            depth_score = 0.0
            
        total_score += depth_score
        
        # 4. 一致性评分 (20分)
        # 基于活动分布的一致性
        if active_days > 0 and total_activities > 0:
            # 计算活动分布的标准差，越小说明越一致
            daily_avg = total_activities / active_days
            
            # 一致性评分：基于使用模式的规律性
            if daily_avg >= 2:
                consistency_score = 20.0
            elif daily_avg >= 1:
                consistency_score = 15.0
            elif daily_avg >= 0.5:
                consistency_score = 10.0
            else:
                consistency_score = 5.0
        else:
            consistency_score = 0.0
            
        total_score += consistency_score
        
        # 确保分数在0-100范围内
        final_score = max(0.0, min(100.0, total_score))
        
        logger.debug(f"参与度评分计算: 活跃度({activity_total:.1f}) + 质量({quality_score:.1f}) + 深度({depth_score:.1f}) + 一致性({consistency_score:.1f}) = {final_score:.1f}")
        
        return round(final_score, 2)
        
    except Exception as e:
        logger.error(f"参与度评分计算失败: {e}")
        return 0.0

def analyze_behavior_patterns(
    activity_data: Dict[str, Any],
    time_window_days: int = 30
) -> Dict[str, Any]:
    """
    分析用户行为模式
    
    识别用户的使用习惯、活跃时段、功能偏好等行为特征
    
    Args:
        activity_data: 用户活动数据
        time_window_days: 分析时间窗口
        
    Returns:
        Dict[str, Any]: 行为模式分析结果
    """
    try:
        patterns = {
            "usage_regularity": "unknown",
            "peak_hours": [],
            "preferred_features": [],
            "session_patterns": {},
            "activity_trends": {},
            "behavioral_tags": []
        }
        
        # 分析使用规律性
        total_activities = activity_data.get("total_activities", 0)
        active_days = activity_data.get("active_days", 0)
        
        if active_days > 0:
            avg_daily_usage = total_activities / active_days
            usage_consistency = active_days / time_window_days
            
            if usage_consistency >= 0.8 and avg_daily_usage >= 3:
                patterns["usage_regularity"] = "highly_regular"
                patterns["behavioral_tags"].append("重度用户")
            elif usage_consistency >= 0.5 and avg_daily_usage >= 1:
                patterns["usage_regularity"] = "regular"
                patterns["behavioral_tags"].append("常规用户")
            elif usage_consistency >= 0.3:
                patterns["usage_regularity"] = "occasional"
                patterns["behavioral_tags"].append("偶尔用户")
            else:
                patterns["usage_regularity"] = "sporadic"
                patterns["behavioral_tags"].append("零星用户")
        
        # 分析活跃时段（基于模拟数据）
        hourly_activity = activity_data.get("hourly_pattern", {})
        if hourly_activity:
            # 找出活动量最高的3个小时
            sorted_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)
            patterns["peak_hours"] = [int(hour) for hour, _ in sorted_hours[:3]]
        
        # 分析功能偏好
        activity_types = activity_data.get("activity_types", {})
        if activity_types:
            total_actions = sum(activity_types.values())
            feature_preferences = []
            
            for feature, count in activity_types.items():
                percentage = (count / total_actions) * 100
                feature_preferences.append({
                    "feature": feature,
                    "usage_count": count,
                    "percentage": round(percentage, 1)
                })
            
            # 按使用频率排序
            patterns["preferred_features"] = sorted(
                feature_preferences, 
                key=lambda x: x["usage_count"], 
                reverse=True
            )
        
        # 会话模式分析
        patterns["session_patterns"] = {
            "avg_session_duration": activity_data.get("avg_session_duration", 0),
            "session_frequency": "daily" if avg_daily_usage >= 1 else "weekly",
            "typical_session_size": _categorize_session_size(avg_daily_usage)
        }
        
        # 活动趋势
        patterns["activity_trends"] = {
            "overall_trend": _calculate_activity_trend(activity_data),
            "engagement_level": _categorize_engagement_level(total_activities, active_days)
        }
        
        return patterns
        
    except Exception as e:
        logger.error(f"行为模式分析失败: {e}")
        return {"error": str(e)}

def generate_user_segments(
    activity_stats: Dict[str, Any],
    engagement_score: float,
    model_usage: Dict[str, Any]
) -> Dict[str, Any]:
    """
    生成用户分群标签
    
    基于RFM模型的用户分群方法：
    - R (Recency): 最近活跃度
    - F (Frequency): 使用频率
    - M (Monetary): 使用价值（模型使用量）
    
    Args:
        activity_stats: 活动统计
        engagement_score: 参与度评分
        model_usage: 模型使用统计
        
    Returns:
        Dict[str, Any]: 用户分群结果
    """
    try:
        segment_info = {
            "primary_segment": "unknown",
            "secondary_segments": [],
            "segment_score": 0.0,
            "characteristics": [],
            "recommendations": []
        }
        
        # RFM评分计算
        rfm_scores = _calculate_rfm_scores(activity_stats, model_usage)
        
        # 主要分群判断
        if rfm_scores["total"] >= 80:
            segment_info["primary_segment"] = "champion"
            segment_info["characteristics"] = ["高价值用户", "活跃用户", "忠实用户"]
            segment_info["recommendations"] = ["提供高级功能", "邀请参与Beta测试", "用户证言收集"]
            
        elif rfm_scores["total"] >= 60:
            segment_info["primary_segment"] = "loyal_customer"
            segment_info["characteristics"] = ["忠诚用户", "定期使用", "功能需求明确"]
            segment_info["recommendations"] = ["功能推荐", "使用技巧分享", "社区互动"]
            
        elif rfm_scores["total"] >= 40:
            segment_info["primary_segment"] = "potential_loyalist"
            segment_info["characteristics"] = ["潜力用户", "使用增长", "需要引导"]
            segment_info["recommendations"] = ["产品教程", "功能介绍", "使用激励"]
            
        elif rfm_scores["total"] >= 20:
            segment_info["primary_segment"] = "new_customer"
            segment_info["characteristics"] = ["新用户", "探索阶段", "需要支持"]
            segment_info["recommendations"] = ["新手指导", "基础功能介绍", "客服支持"]
            
        else:
            segment_info["primary_segment"] = "at_risk"
            segment_info["characteristics"] = ["流失风险", "低活跃", "需要挽回"]
            segment_info["recommendations"] = ["重新激活活动", "价值提醒", "个性化推荐"]
        
        # 次要分群
        secondary_segments = []
        
        # 基于参与度的分群
        if engagement_score >= 80:
            secondary_segments.append("高参与度用户")
        elif engagement_score >= 60:
            secondary_segments.append("中等参与度用户")
        else:
            secondary_segments.append("低参与度用户")
        
        # 基于模型使用的分群
        total_model_calls = model_usage.get("total_model_calls", 0)
        if total_model_calls >= 50:
            secondary_segments.append("重度AI使用者")
        elif total_model_calls >= 20:
            secondary_segments.append("中度AI使用者")
        elif total_model_calls >= 5:
            secondary_segments.append("轻度AI使用者")
        else:
            secondary_segments.append("AI新手")
        
        segment_info["secondary_segments"] = secondary_segments
        segment_info["segment_score"] = rfm_scores["total"]
        
        return segment_info
        
    except Exception as e:
        logger.error(f"用户分群失败: {e}")
        return {"error": str(e)}

def calculate_similarity_score(
    user1_profile: Dict[str, Any],
    user2_profile: Dict[str, Any]
) -> float:
    """
    计算两个用户的相似度评分
    
    基于用户行为特征的余弦相似度计算
    
    Args:
        user1_profile: 用户1的画像数据
        user2_profile: 用户2的画像数据
        
    Returns:
        float: 相似度评分 (0-1)
    """
    try:
        # 提取特征向量
        features1 = _extract_similarity_features(user1_profile)
        features2 = _extract_similarity_features(user2_profile)
        
        # 计算余弦相似度
        similarity = _cosine_similarity(features1, features2)
        
        return round(similarity, 3)
        
    except Exception as e:
        logger.error(f"相似度计算失败: {e}")
        return 0.0

def _calculate_rfm_scores(
    activity_stats: Dict[str, Any],
    model_usage: Dict[str, Any]
) -> Dict[str, float]:
    """计算RFM评分"""
    # Recency - 最近活跃度 (基于最后活动时间)
    last_activity = activity_stats.get("last_activity")
    if last_activity:
        try:
            last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            days_since_last = (datetime.utcnow() - last_date.replace(tzinfo=None)).days
            
            if days_since_last <= 1:
                recency_score = 100
            elif days_since_last <= 7:
                recency_score = 80
            elif days_since_last <= 30:
                recency_score = 60
            elif days_since_last <= 90:
                recency_score = 40
            else:
                recency_score = 20
        except:
            recency_score = 50
    else:
        recency_score = 50
    
    # Frequency - 使用频率
    avg_activities = activity_stats.get("avg_activities_per_day", 0)
    if avg_activities >= 5:
        frequency_score = 100
    elif avg_activities >= 3:
        frequency_score = 80
    elif avg_activities >= 1:
        frequency_score = 60
    elif avg_activities >= 0.5:
        frequency_score = 40
    else:
        frequency_score = 20
    
    # Monetary - 使用价值 (基于模型调用量)
    model_calls = model_usage.get("total_model_calls", 0)
    if model_calls >= 100:
        monetary_score = 100
    elif model_calls >= 50:
        monetary_score = 80
    elif model_calls >= 20:
        monetary_score = 60
    elif model_calls >= 5:
        monetary_score = 40
    else:
        monetary_score = 20
    
    # 综合评分 (加权平均)
    total_score = (recency_score * 0.3 + frequency_score * 0.4 + monetary_score * 0.3)
    
    return {
        "recency": recency_score,
        "frequency": frequency_score,
        "monetary": monetary_score,
        "total": round(total_score, 1)
    }

def _categorize_session_size(avg_daily_usage: float) -> str:
    """分类会话规模"""
    if avg_daily_usage >= 10:
        return "intensive"
    elif avg_daily_usage >= 5:
        return "heavy"
    elif avg_daily_usage >= 2:
        return "moderate"
    elif avg_daily_usage >= 1:
        return "light"
    else:
        return "minimal"

def _calculate_activity_trend(activity_data: Dict[str, Any]) -> str:
    """计算活动趋势"""
    # 简化实现，基于活跃天数判断
    active_days = activity_data.get("active_days", 0)
    total_activities = activity_data.get("total_activities", 0)
    
    if active_days >= 20 and total_activities >= 50:
        return "increasing"
    elif active_days >= 10 and total_activities >= 20:
        return "stable"
    else:
        return "decreasing"

def _categorize_engagement_level(total_activities: int, active_days: int) -> str:
    """分类参与度水平"""
    if active_days == 0:
        return "none"
    
    avg_daily = total_activities / active_days
    
    if avg_daily >= 5:
        return "very_high"
    elif avg_daily >= 3:
        return "high"
    elif avg_daily >= 1:
        return "medium"
    elif avg_daily >= 0.5:
        return "low"
    else:
        return "very_low"

def _extract_similarity_features(profile: Dict[str, Any]) -> List[float]:
    """提取用户相似度特征向量"""
    features = []
    
    # 活动相关特征
    activity_stats = profile.get("activity_stats", {})
    features.extend([
        activity_stats.get("total_activities", 0),
        activity_stats.get("active_days", 0),
        activity_stats.get("avg_activities_per_day", 0),
    ])
    
    # 参与度特征
    features.append(profile.get("engagement_score", 0))
    
    # 模型使用特征
    model_usage = profile.get("model_usage", {})
    features.extend([
        model_usage.get("total_model_calls", 0),
        model_usage.get("unique_models_used", 0),
    ])
    
    # 对话模式特征
    conversation_patterns = profile.get("conversation_patterns", {})
    features.append(conversation_patterns.get("avg_messages_per_conversation", 0))
    
    return features

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    if len(vec1) != len(vec2):
        return 0.0
    
    # 计算点积
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # 计算向量长度
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def generate_insights_text(
    user_segment: Dict[str, Any],
    behavior_patterns: Dict[str, Any],
    engagement_score: float
) -> str:
    """
    生成用户洞察文本描述
    
    Args:
        user_segment: 用户分群信息
        behavior_patterns: 行为模式
        engagement_score: 参与度评分
        
    Returns:
        str: 洞察文本描述
    """
    try:
        insights = []
        
        # 基础描述
        primary_segment = user_segment.get("primary_segment", "unknown")
        segment_names = {
            "champion": "优质用户",
            "loyal_customer": "忠诚用户",
            "potential_loyalist": "潜力用户",
            "new_customer": "新用户",
            "at_risk": "流失风险用户"
        }
        
        segment_name = segment_names.get(primary_segment, "普通用户")
        insights.append(f"您是我们平台的{segment_name}")
        
        # 参与度描述
        if engagement_score >= 80:
            insights.append("，参与度非常高，是平台的活跃贡献者")
        elif engagement_score >= 60:
            insights.append("，参与度良好，经常使用平台功能")
        elif engagement_score >= 40:
            insights.append("，参与度中等，有进一步提升的空间")
        else:
            insights.append("，参与度较低，建议多尝试平台功能")
        
        # 使用习惯描述
        usage_regularity = behavior_patterns.get("usage_regularity", "unknown")
        if usage_regularity == "highly_regular":
            insights.append("。您的使用习惯非常规律，是我们的重度用户")
        elif usage_regularity == "regular":
            insights.append("。您有着良好的使用习惯，经常访问平台")
        elif usage_regularity == "occasional":
            insights.append("。您偶尔使用平台，可以尝试更多功能")
        else:
            insights.append("。建议建立更规律的使用习惯")
        
        # 功能偏好描述
        preferred_features = behavior_patterns.get("preferred_features", [])
        if preferred_features:
            top_feature = preferred_features[0].get("feature", "")
            if top_feature:
                insights.append(f"，最常使用{top_feature}功能")
        
        return "".join(insights) + "。"
        
    except Exception as e:
        logger.error(f"洞察文本生成失败: {e}")
        return "用户画像分析完成，详细信息请查看分析报告。"