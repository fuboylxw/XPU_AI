"""
数据库初始化脚本
创建示例数据表和数据
"""
import sqlite3
import pandas as pd
from pathlib import Path

def init_database():
    """初始化数据库"""
    db_path = Path("data/chatbi.db")
    
    # 确保data目录存在
    db_path.parent.mkdir(exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建订单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            order_date DATE NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 创建销售统计表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            revenue REAL NOT NULL,
            orders_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入示例数据
    # 用户数据
    users_data = [
        ('user1', 'user1@example.com'),
        ('user2', 'user2@example.com'),
        ('user3', 'user3@example.com'),
        ('user4', 'user4@example.com'),
        ('user5', 'user5@example.com')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO users (username, email) VALUES (?, ?)
    ''', users_data)
    
    # 订单数据
    orders_data = [
        (1, '产品A', 2, 299.0, '2024-01-15', 'completed'),
        (1, '产品B', 1, 599.0, '2024-01-16', 'completed'),
        (2, '产品C', 3, 199.0, '2024-01-17', 'pending'),
        (3, '产品A', 1, 299.0, '2024-01-18', 'completed'),
        (4, '产品D', 2, 899.0, '2024-01-19', 'shipped'),
        (5, '产品B', 1, 599.0, '2024-01-20', 'completed'),
        (2, '产品E', 1, 1299.0, '2024-01-21', 'pending'),
        (3, '产品C', 2, 199.0, '2024-01-22', 'completed')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO orders 
        (user_id, product_name, quantity, price, order_date, status) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', orders_data)
    
    # 销售统计数据
    sales_data = [
        ('2024-01', 15000.0, 25),
        ('2024-02', 18000.0, 30),
        ('2024-03', 22000.0, 35),
        ('2024-04', 19500.0, 28),
        ('2024-05', 25000.0, 40)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO sales_stats (month, revenue, orders_count) 
        VALUES (?, ?, ?)
    ''', sales_data)
    
    # 提交更改
    conn.commit()
    
    # 显示创建的数据
    print("📊 数据库初始化完成！")
    print("\n📋 数据表信息：")
    
    # 显示表结构
    tables = ['users', 'orders', 'sales_stats']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} 条记录")
    
    # 显示示例数据
    print("\n👥 用户数据示例：")
    df_users = pd.read_sql_query("SELECT * FROM users LIMIT 3", conn)
    print(df_users.to_string(index=False))
    
    print("\n📦 订单数据示例：")
    df_orders = pd.read_sql_query("""
        SELECT o.id, u.username, o.product_name, o.quantity, o.price, o.order_date, o.status
        FROM orders o
        JOIN users u ON o.user_id = u.id
        LIMIT 5
    """, conn)
    print(df_orders.to_string(index=False))
    
    print("\n📈 销售统计数据示例：")
    df_sales = pd.read_sql_query("SELECT * FROM sales_stats LIMIT 3", conn)
    print(df_sales.to_string(index=False))
    
    conn.close()
    print(f"\n✅ 数据库文件已创建: {db_path.absolute()}")

if __name__ == "__main__":
    init_database()