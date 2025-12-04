"""
MySQL Utility Module

Provides direct MySQL connection utilities.
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class MySQLUtil:
    """MySQL utility for direct database operations."""
    
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ):
        """Initialize MySQL connection parameters."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._connection = None
    
    def get_connection(self):
        """Get MySQL connection."""
        try:
            import pymysql
            if self._connection is None or not self._connection.open:
                self._connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                )
            return self._connection
        except ImportError:
            logger.warning("pymysql not installed, MySQL utility disabled")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return None
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        try:
            conn = self.get_connection()
            if conn is None:
                return []
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        try:
            conn = self.get_connection()
            if conn is None:
                return 0
            
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                conn.commit()
                return affected
        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            if self._connection:
                self._connection.rollback()
            return 0

    def insert(
            self,
            table: str,
            data: Dict[str, Any]
    ) -> int:
        """
        插入单条数据

        Args:
            table: 表名
            data: 要插入的数据字典

        Returns:
            插入记录的ID（自增主键）

        Example:
            user_id = mysql_util.insert(
                table="users",
                data={"name": "张三", "email": "zhang@example.com", "age": 25}
            )
        """

        if not data:
            raise ValueError("插入数据不能为空")
        try:
            conn = self.get_connection()
            if conn is None:
                return 0

            columns = list(data.keys())
            values = list(data.values())
            placeholders = ", ".join(["%s"] * len(values))
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            logger.debug(f"执行插入SQL: {sql}, 参数: {values}")

            with conn.cursor() as cursor:
                affected = cursor.execute(sql, values)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            if self._connection:
                self._connection.rollback()
            return 0

        if not data:
            raise ValueError("插入数据不能为空")

        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(["%s"] * len(values))

        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

        logger.debug(f"执行插入SQL: {sql}, 参数: {values}")

        with self.get_cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.lastrowid

    def close(self):
        """Close the connection."""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None

