"""
基础Repository类

提供通用的数据访问方法，所有Repository都继承此基类。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# 泛型类型变量
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """基础Repository类"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        初始化Repository
        
        Args:
            model: SQLAlchemy模型类
            db: 数据库会话
        """
        self.model = model
        self.db = db
    
    def get(self, id: Any) -> Optional[ModelType]:
        """
        根据ID获取单个记录
        
        Args:
            id: 记录ID
            
        Returns:
            ModelType: 查找到的记录，未找到返回None
        """
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"获取记录失败 - ID: {id}, 错误: {e}")
            raise
    
    def get_multi(self, skip: int = 0, limit: int = 100, **filters) -> List[ModelType]:
        """
        获取多个记录
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            **filters: 过滤条件
            
        Returns:
            List[ModelType]: 记录列表
        """
        try:
            query = self.db.query(self.model)
            
            # 应用过滤条件
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"获取多个记录失败 - 过滤条件: {filters}, 错误: {e}")
            raise
    
    def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """
        创建新记录
        
        Args:
            obj_in: 创建数据对象
            
        Returns:
            ModelType: 创建的记录
            
        Raises:
            IntegrityError: 数据完整性错误
        """
        try:
            obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
            db_obj = self.model(**obj_in_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            logger.info(f"成功创建记录 - ID: {db_obj.id}")
            return db_obj
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"创建记录失败 - 数据完整性错误: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建记录失败 - 错误: {e}")
            raise
    
    def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """
        更新记录
        
        Args:
            db_obj: 数据库中的记录对象
            obj_in: 更新数据对象
            
        Returns:
            ModelType: 更新后的记录
        """
        try:
            obj_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, 'dict') else obj_in
            
            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            logger.info(f"成功更新记录 - ID: {db_obj.id}")
            return db_obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新记录失败 - ID: {db_obj.id}, 错误: {e}")
            raise
    
    def delete(self, *, id: Any) -> bool:
        """
        删除记录
        
        Args:
            id: 记录ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            obj = self.db.query(self.model).filter(self.model.id == id).first()
            if obj:
                self.db.delete(obj)
                self.db.commit()
                logger.info(f"成功删除记录 - ID: {id}")
                return True
            else:
                logger.warning(f"删除失败 - 记录不存在: ID: {id}")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除记录失败 - ID: {id}, 错误: {e}")
            raise
    
    def count(self, **filters) -> int:
        """
        统计记录数量
        
        Args:
            **filters: 过滤条件
            
        Returns:
            int: 记录数量
        """
        try:
            query = self.db.query(self.model)
            
            # 应用过滤条件
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
            
            return query.count()
        except Exception as e:
            logger.error(f"统计记录数量失败 - 过滤条件: {filters}, 错误: {e}")
            raise
    
    def exists(self, **filters) -> bool:
        """
        检查记录是否存在
        
        Args:
            **filters: 过滤条件
            
        Returns:
            bool: 是否存在
        """
        return self.count(**filters) > 0
    
    def bulk_create(self, *, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """
        批量创建记录
        
        Args:
            objs_in: 创建数据对象列表
            
        Returns:
            List[ModelType]: 创建的记录列表
        """
        try:
            db_objs = []
            for obj_in in objs_in:
                obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
                db_obj = self.model(**obj_in_data)
                db_objs.append(db_obj)
            
            self.db.add_all(db_objs)
            self.db.commit()
            
            for db_obj in db_objs:
                self.db.refresh(db_obj)
            
            logger.info(f"成功批量创建 {len(db_objs)} 条记录")
            return db_objs
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量创建记录失败 - 错误: {e}")
            raise
    
    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        批量更新记录
        
        Args:
            updates: 更新数据列表，每个字典必须包含id字段
            
        Returns:
            int: 更新的记录数量
        """
        try:
            updated_count = 0
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                
                obj_id = update_data.pop('id')
                result = self.db.query(self.model).filter(
                    self.model.id == obj_id
                ).update(update_data)
                updated_count += result
            
            self.db.commit()
            logger.info(f"成功批量更新 {updated_count} 条记录")
            return updated_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量更新记录失败 - 错误: {e}")
            raise
    
    def execute_raw_sql(self, sql: str, params: Dict[str, Any] = None) -> Any:
        """
        执行原生SQL
        
        Args:
            sql: SQL语句
            params: SQL参数
            
        Returns:
            Any: 执行结果
        """
        try:
            result = self.db.execute(text(sql), params or {})
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"执行原生SQL失败 - SQL: {sql}, 错误: {e}")
            raise