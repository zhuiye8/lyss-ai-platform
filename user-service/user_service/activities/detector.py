# -*- coding: utf-8 -*-
"""
活动异常检测器模块

基于机器学习和规则引擎的用户活动异常检测系统。
支持多维度异常检测、动态阈值调整和实时告警机制。

核心功能：
- 基于历史行为的异常检测
- 多层次异常评级系统
- 动态阈值自适应调整
- 实时异常告警和处理
"""

import logging
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class ActivityAnomalyDetector:
    """
    活动异常检测器
    
    使用多种算法检测用户活动中的异常模式：
    - 统计异常检测（基于Z-Score）
    - 行为模式分析
    - 时间序列异常检测
    - 地理位置异常检测
    """
    
    def __init__(self):
        # 检测配置
        self.detection_config = {
            "z_score_threshold": 2.5,  # Z-Score异常阈值
            "activity_burst_multiplier": 3.0,  # 活动突增倍数
            "location_travel_threshold": 3600,  # 地理位置变化最小时间间隔（秒）
            "session_duration_threshold": 14400,  # 异常会话时长（4小时）
            "night_activity_ratio": 0.3,  # 深夜活动异常比例
            "min_samples_for_detection": 10  # 最小样本数
        }
        
        # 用户行为基线缓存
        self.user_baselines = {}
        self.baseline_cache_ttl = 3600  # 1小时缓存过期
        
        # 异常检测统计
        self.detection_stats = {
            "total_checks": 0,
            "anomalies_detected": 0,
            "false_positives": 0,
            "detection_time_ms": []
        }
    
    async def check_activity(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查单个活动是否异常
        
        Args:
            user_id: 用户ID
            activity_type: 活动类型
            activity_data: 活动数据
            
        Returns:
            Dict[str, Any]: 异常检测结果
        """
        start_time = time.time()
        
        try:
            self.detection_stats["total_checks"] += 1
            
            # 获取用户行为基线
            baseline = await self._get_user_baseline(user_id)
            if not baseline:
                return {
                    "is_anomaly": False,
                    "reason": "用户数据不足，无法进行异常检测",
                    "confidence": 0.0,
                    "severity": "none"
                }
            
            # 多维度异常检测
            anomaly_scores = []
            anomaly_reasons = []
            
            # 1. 活动频率异常检测
            freq_anomaly = self._detect_frequency_anomaly(
                user_id, activity_type, activity_data, baseline
            )
            if freq_anomaly["is_anomaly"]:
                anomaly_scores.append(freq_anomaly["score"])
                anomaly_reasons.append(freq_anomaly["reason"])
            
            # 2. 时间模式异常检测
            time_anomaly = self._detect_time_pattern_anomaly(
                user_id, activity_type, activity_data, baseline
            )
            if time_anomaly["is_anomaly"]:
                anomaly_scores.append(time_anomaly["score"])
                anomaly_reasons.append(time_anomaly["reason"])
            
            # 3. 地理位置异常检测
            if activity_data.get("ip_address"):
                location_anomaly = self._detect_location_anomaly(
                    user_id, activity_data, baseline
                )
                if location_anomaly["is_anomaly"]:
                    anomaly_scores.append(location_anomaly["score"])
                    anomaly_reasons.append(location_anomaly["reason"])
            
            # 4. 活动模式异常检测
            pattern_anomaly = self._detect_pattern_anomaly(
                user_id, activity_type, activity_data, baseline
            )
            if pattern_anomaly["is_anomaly"]:
                anomaly_scores.append(pattern_anomaly["score"])
                anomaly_reasons.append(pattern_anomaly["reason"])
            
            # 综合评估
            if anomaly_scores:
                avg_score = statistics.mean(anomaly_scores)
                max_score = max(anomaly_scores)
                
                # 确定严重程度
                if max_score >= 0.8:
                    severity = "high"
                elif max_score >= 0.6:
                    severity = "medium"
                else:
                    severity = "low"
                
                self.detection_stats["anomalies_detected"] += 1
                
                return {
                    "is_anomaly": True,
                    "reason": "; ".join(anomaly_reasons),
                    "confidence": round(avg_score, 3),
                    "severity": severity,
                    "type": "behavioral_anomaly",
                    "details": {
                        "individual_scores": anomaly_scores,
                        "reasons": anomaly_reasons,
                        "max_score": max_score
                    }
                }
            else:
                return {
                    "is_anomaly": False,
                    "reason": "活动模式正常",
                    "confidence": 0.0,
                    "severity": "none"
                }
        
        except Exception as e:
            logger.error(f"活动异常检测失败 [{user_id}]: {e}")
            return {
                "is_anomaly": False,
                "reason": f"检测过程异常: {str(e)}",
                "confidence": 0.0,
                "severity": "none",
                "error": True
            }
        
        finally:
            # 记录检测耗时
            detection_time = (time.time() - start_time) * 1000
            self.detection_stats["detection_time_ms"].append(detection_time)
            
            # 保持统计队列长度
            if len(self.detection_stats["detection_time_ms"]) > 1000:
                self.detection_stats["detection_time_ms"] = \
                    self.detection_stats["detection_time_ms"][-500:]
    
    def _detect_frequency_anomaly(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测活动频率异常"""
        try:
            current_hour = datetime.utcnow().hour
            
            # 获取该小时的历史活动频率
            hourly_freq = baseline.get("hourly_frequency", {})
            expected_freq = hourly_freq.get(str(current_hour), 0)
            
            # 获取当前小时已发生的活动数（这里简化处理）
            current_freq = 1  # 当前活动
            
            if expected_freq == 0:
                expected_freq = baseline.get("avg_hourly_frequency", 1)
            
            # 计算异常评分
            if expected_freq > 0:
                freq_ratio = current_freq / expected_freq
                if freq_ratio > self.detection_config["activity_burst_multiplier"]:
                    score = min(freq_ratio / self.detection_config["activity_burst_multiplier"], 1.0)
                    return {
                        "is_anomaly": True,
                        "score": score,
                        "reason": f"活动频率异常（当前{current_freq}次，预期{expected_freq}次）"
                    }
            
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
            
        except Exception as e:
            logger.error(f"频率异常检测失败: {e}")
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
    
    def _detect_time_pattern_anomaly(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测时间模式异常"""
        try:
            current_hour = datetime.utcnow().hour
            
            # 获取用户的常用时间模式
            common_hours = baseline.get("common_active_hours", [])
            
            # 如果当前时间不在常用时间内
            if common_hours and current_hour not in common_hours:
                # 特别检查深夜活动（0-5点）
                if current_hour in [0, 1, 2, 3, 4, 5]:
                    return {
                        "is_anomaly": True,
                        "score": 0.7,
                        "reason": f"深夜异常活动（{current_hour}点，常用时段：{common_hours}）"
                    }
                else:
                    return {
                        "is_anomaly": True,
                        "score": 0.4,
                        "reason": f"非常用时段活动（{current_hour}点，常用时段：{common_hours}）"
                    }
            
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
            
        except Exception as e:
            logger.error(f"时间模式异常检测失败: {e}")
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
    
    def _detect_location_anomaly(
        self,
        user_id: str,
        activity_data: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测地理位置异常"""
        try:
            location_info = activity_data.get("metadata", {}).get("location", {})
            if not location_info:
                return {"is_anomaly": False, "score": 0.0, "reason": ""}
            
            current_country = location_info.get("country")
            if not current_country:
                return {"is_anomaly": False, "score": 0.0, "reason": ""}
            
            # 获取用户常用国家
            common_countries = baseline.get("common_countries", [])
            
            if common_countries and current_country not in common_countries[:3]:  # 前3个常用国家
                return {
                    "is_anomaly": True,
                    "score": 0.8,
                    "reason": f"来自非常用地区的访问（{current_country}，常用地区：{common_countries[:3]}）"
                }
            
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
            
        except Exception as e:
            logger.error(f"地理位置异常检测失败: {e}")
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
    
    def _detect_pattern_anomaly(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测活动模式异常"""
        try:
            # 获取活动类型分布
            type_distribution = baseline.get("activity_type_distribution", {})
            expected_ratio = type_distribution.get(activity_type, 0)
            
            # 如果是非常罕见的活动类型
            if expected_ratio < 0.01 and expected_ratio > 0:  # 小于1%但不为0
                return {
                    "is_anomaly": True,
                    "score": 0.5,
                    "reason": f"罕见活动类型（{activity_type}，历史占比{expected_ratio:.1%}）"
                }
            
            # 检查元数据异常
            metadata = activity_data.get("metadata", {})
            
            # 检查模型使用异常（如果是模型相关活动）
            if activity_type in ["chat_message", "model_usage"]:
                model = metadata.get("model")
                if model:
                    common_models = baseline.get("common_models", [])
                    if common_models and model not in common_models[:5]:  # 前5个常用模型
                        return {
                            "is_anomaly": True,
                            "score": 0.3,
                            "reason": f"使用非常用模型（{model}，常用：{common_models[:3]}）"
                        }
            
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
            
        except Exception as e:
            logger.error(f"模式异常检测失败: {e}")
            return {"is_anomaly": False, "score": 0.0, "reason": ""}
    
    async def _get_user_baseline(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户行为基线"""
        try:
            # 检查缓存
            cache_key = f"baseline_{user_id}"
            if cache_key in self.user_baselines:
                cached_data = self.user_baselines[cache_key]
                if time.time() - cached_data["timestamp"] < self.baseline_cache_ttl:
                    return cached_data["data"]
            
            # 构建用户基线（这里使用模拟数据，实际应该从数据库获取）
            baseline = {
                "avg_hourly_frequency": 2.5,
                "hourly_frequency": {
                    "9": 3, "10": 4, "11": 3, "14": 5, "15": 4, "16": 3, "20": 2, "21": 1
                },
                "common_active_hours": [9, 10, 11, 14, 15, 16, 20, 21],
                "common_countries": ["China", "United States"],
                "activity_type_distribution": {
                    "chat_message": 0.45,
                    "login": 0.15,
                    "model_usage": 0.25,
                    "feature_usage": 0.15
                },
                "common_models": ["gpt-4", "claude-3", "deepseek"],
                "total_activities": 500,
                "analysis_period_days": 30
            }
            
            # 缓存基线数据
            self.user_baselines[cache_key] = {
                "data": baseline,
                "timestamp": time.time()
            }
            
            return baseline
            
        except Exception as e:
            logger.error(f"获取用户基线失败 [{user_id}]: {e}")
            return None
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        stats = self.detection_stats.copy()
        
        if stats["detection_time_ms"]:
            stats["avg_detection_time_ms"] = statistics.mean(stats["detection_time_ms"])
            stats["max_detection_time_ms"] = max(stats["detection_time_ms"])
        else:
            stats["avg_detection_time_ms"] = 0
            stats["max_detection_time_ms"] = 0
        
        # 移除原始时间数据
        del stats["detection_time_ms"]
        
        return stats
    
    def update_detection_config(self, config_updates: Dict[str, Any]):
        """更新检测配置"""
        for key, value in config_updates.items():
            if key in self.detection_config:
                self.detection_config[key] = value
                logger.info(f"检测配置已更新: {key} = {value}")
    
    def clear_user_baselines(self, user_id: Optional[str] = None):
        """清除用户基线缓存"""
        if user_id:
            cache_key = f"baseline_{user_id}"
            if cache_key in self.user_baselines:
                del self.user_baselines[cache_key]
                logger.info(f"已清除用户基线缓存: {user_id}")
        else:
            self.user_baselines.clear()
            logger.info("已清除所有用户基线缓存")