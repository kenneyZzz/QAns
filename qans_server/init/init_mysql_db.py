#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MySQL数据库表初始化脚本

该脚本用于执行 qans_mysql.sql 文件，初始化数据库表结构。
使用方法：
    python init_mysql_db.py
"""

import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from qans_server.setting_config import settings


def load_sql_file(sql_file_path: Path) -> str:
    """读取SQL文件内容。
    
    Args:
        sql_file_path: SQL文件路径
        
    Returns:
        SQL文件内容字符串
    """
    if not sql_file_path.exists():
        raise FileNotFoundError(f"SQL文件不存在: {sql_file_path}")
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_sql_statements(sql_content: str) -> List[str]:
    """将SQL内容分割成独立的SQL语句。
    
    处理多行SQL语句、注释等。
    
    Args:
        sql_content: SQL文件内容
        
    Returns:
        SQL语句列表
    """
    statements = []
    current_statement = []
    in_multiline_comment = False
    
    lines = sql_content.split('\n')
    
    for line in lines:
        # 去除行尾空白
        line = line.rstrip()
        
        # 跳过空行
        if not line.strip():
            continue
        
        # 处理单行注释（整行都是注释）
        stripped = line.strip()
        if stripped.startswith('--'):
            continue
        
        # 处理多行注释
        i = 0
        while i < len(line):
            # 检查多行注释开始 /*
            if not in_multiline_comment and i < len(line) - 1 and line[i:i+2] == '/*':
                in_multiline_comment = True
                i += 2
                continue
            
            # 检查多行注释结束 */
            if in_multiline_comment and i < len(line) - 1 and line[i:i+2] == '*/':
                in_multiline_comment = False
                i += 2
                continue
            
            # 如果不在注释中，添加到当前语句
            if not in_multiline_comment:
                current_statement.append(line[i])
            
            i += 1
        
        # 如果不在注释中，添加换行符
        if not in_multiline_comment:
            current_statement.append('\n')
    
    # 将当前语句转换为字符串
    full_text = ''.join(current_statement)
    
    # 按分号分割语句
    for statement in full_text.split(';'):
        statement = statement.strip()
        # 过滤掉空语句
        if statement:
            statements.append(statement)
    
    return statements


def execute_sql_file(mysql_dsn: str, sql_file_path: Path) -> None:
    """执行SQL文件初始化数据库表。
    
    Args:
        mysql_dsn: MySQL连接字符串
        sql_file_path: SQL文件路径
    """
    print(f"正在读取SQL文件: {sql_file_path}")
    sql_content = load_sql_file(sql_file_path)
    
    print("正在解析SQL语句...")
    statements = split_sql_statements(sql_content)
    print(f"共解析出 {len(statements)} 条SQL语句")
    
    print(f"正在连接MySQL数据库...")
    try:
        engine = create_engine(mysql_dsn, pool_pre_ping=True)
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)
    
    print("✅ 数据库连接成功")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    
    with engine.connect() as conn:
        for idx, statement in enumerate(statements, 1):
            try:
                # 执行SQL语句
                conn.execute(text(statement))
                conn.commit()  # 每条语句单独提交
                
                # 提取表名用于显示（简单提取）
                table_name = "未知表"
                statement_upper = statement.upper()
                if "CREATE TABLE" in statement_upper:
                    # 尝试提取表名
                    parts = statement_upper.split("CREATE TABLE")
                    if len(parts) > 1:
                        table_part = parts[1].split()[0]
                        table_name = table_part.strip('`').strip()
                elif "DROP TABLE" in statement_upper:
                    parts = statement_upper.split("DROP TABLE")
                    if len(parts) > 1:
                        table_part = parts[1].split()[0]
                        table_name = table_part.strip('`').strip()
                
                print(f"[{idx}/{len(statements)}] ✅ 执行成功: {table_name}")
                success_count += 1
                
            except SQLAlchemyError as e:
                error_count += 1
                conn.rollback()  # 回滚当前语句
                print(f"[{idx}/{len(statements)}] ❌ 执行失败: {e}")
                # 显示SQL语句的前100个字符
                sql_preview = statement[:100].replace('\n', ' ')
                print(f"SQL语句预览: {sql_preview}...")
            except Exception as e:
                error_count += 1
                conn.rollback()  # 回滚当前语句
                print(f"[{idx}/{len(statements)}] ❌ 执行失败: {e}")
                sql_preview = statement[:100].replace('\n', ' ')
                print(f"SQL语句预览: {sql_preview}...")
    
    print("-" * 60)
    print(f"执行完成！成功: {success_count} 条, 失败: {error_count} 条")
    
    if error_count > 0:
        print("⚠️  有部分SQL语句执行失败，请检查错误信息")
        sys.exit(1)
    else:
        print("✅ 所有SQL语句执行成功，数据库表初始化完成！")


def main():
    """主函数。"""
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # 加载环境变量（从qans_server目录的.env文件）
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"已加载环境变量文件: {env_file}")
    else:
        print("尝试从当前环境加载环境变量")
    
    # 获取MySQL连接字符串
    mysql_dsn = settings.mysql_dsn
    if not mysql_dsn:
        print("❌ 错误: 未找到环境变量 MYSQL_DSN")
        print("请确保在 .env 文件中配置了 MYSQL_DSN")
        sys.exit(1)
    
    # SQL文件路径
    sql_file_path = script_dir / "qans_mysql.sql"
    
    print("=" * 60)
    print("MySQL数据库表初始化脚本")
    print("=" * 60)
    print(f"SQL文件: {sql_file_path}")
    print(f"数据库: {mysql_dsn.split('@')[-1] if '@' in mysql_dsn else mysql_dsn}")
    print("=" * 60)
    
    try:
        execute_sql_file(mysql_dsn, sql_file_path)
    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


