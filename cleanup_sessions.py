#!/usr/bin/env python3
"""
清理数据库中的旧会话脚本
用于删除无效的实时检测会话记录
"""

import pymongo
import toml
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_config():
    """加载服务器配置"""
    try:
        configs = toml.load('servers/configs/config.toml')
        return configs['db-connection-uri']
    except Exception as e:
        logger.error(f"❌ 无法加载配置文件: {e}")
        return None

def connect_database(uri):
    """连接数据库"""
    try:
        logger.info(f"正在连接数据库: {uri}")
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)

        # 测试连接
        client.server_info()

        logger.info("✅ 数据库连接成功")
        return client
    except pymongo.errors.ServerSelectionTimeoutError:
        logger.error("❌ 无法连接数据库: 连接超时")
        logger.error("请确保 MongoDB 服务正在运行")
        return None
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return None

def list_sessions(database):
    """列出所有会话"""
    try:
        sessions = list(database.surveillance.sessions.find())

        if not sessions:
            logger.info("📭 数据库中没有会话记录")
            return []

        logger.info(f"📋 找到 {len(sessions)} 个会话:")
        logger.info("")

        for i, session in enumerate(sessions, 1):
            logger.info(f"  {i}. Session ID: {session.get('sessionId')}")
            logger.info(f"     名称: {session.get('name', 'N/A')}")
            logger.info(f"     视频源: {session.get('source', 'N/A')}")
            logger.info(f"     备注: {session.get('note', 'N/A')}")
            logger.info("")

        return sessions
    except Exception as e:
        logger.error(f"❌ 查询会话失败: {e}")
        return []

def delete_all_sessions(database, confirm=True):
    """删除所有会话"""
    if confirm:
        logger.warning("⚠️ 即将删除所有会话记录!")
        response = input("确认删除? (yes/no): ")

        if response.lower() != 'yes':
            logger.info("已取消")
            return False

    try:
        result = database.surveillance.sessions.delete_many({})
        logger.info(f"✅ 已删除 {result.deleted_count} 个会话")
        return True
    except Exception as e:
        logger.error(f"❌ 删除失败: {e}")
        return False

def delete_session_by_id(database, session_id):
    """删除指定会话"""
    try:
        result = database.surveillance.sessions.delete_one({'sessionId': session_id})

        if result.deleted_count > 0:
            logger.info(f"✅ 已删除会话: {session_id}")
            return True
        else:
            logger.warning(f"⚠️ 未找到会话: {session_id}")
            return False
    except Exception as e:
        logger.error(f"❌ 删除失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🗑️ 数据库会话清理工具")
    logger.info("=" * 60)
    logger.info("")

    # 加载配置
    db_uri = load_config()
    if not db_uri:
        logger.error("无法继续，请检查配置文件")
        return 1

    # 连接数据库
    client = connect_database(db_uri)
    if not client:
        logger.error("无法继续，请启动 MongoDB 服务")
        logger.info("")
        logger.info("启动 MongoDB:")
        logger.info("  Windows: 在服务中启动 MongoDB")
        logger.info("  Docker: docker run -d -p 27017:27017 mongo:latest")
        return 1

    database = client

    # 列出会话
    logger.info("")
    sessions = list_sessions(database)

    if not sessions:
        logger.info("✅ 数据库已清理")
        return 0

    # 询问操作
    logger.info("=" * 60)
    logger.info("请选择操作:")
    logger.info("  1. 删除所有会话")
    logger.info("  2. 删除指定会话")
    logger.info("  3. 取消")
    logger.info("")

    choice = input("请输入选项 (1-3): ").strip()

    if choice == '1':
        delete_all_sessions(database, confirm=True)
    elif choice == '2':
        session_id = input("请输入要删除的 Session ID: ").strip()
        delete_session_by_id(database, session_id)
    else:
        logger.info("已取消")

    # 关闭连接
    client.close()
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ 完成")

    return 0

if __name__ == "__main__":
    sys.exit(main())
