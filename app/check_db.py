from database import get_db_connection
from datetime import datetime, timedelta
import sys
sys.path.append('.')  # 确保能导入当前目录模块
from main import is_in_time_range, is_date_in_range, is_employee_match

def check_records():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询方辉的记录
    cursor.execute("""
        SELECT * FROM products 
        WHERE "绕线员工" LIKE '%方辉%' 
           OR "嵌线员工" LIKE '%方辉%' 
           OR "接线员工" LIKE '%方辉%' 
           OR "压装员工" LIKE '%方辉%' 
           OR "车止口员工" LIKE '%方辉%'
        LIMIT 5
    """)
    
    products = cursor.fetchall()
    print(f'找到 {len(products)} 条方辉的记录:')
    
    # 构建测试用的日期范围 - 确保范围足够大以包含所有记录
    start_date = datetime(2025, 3, 1)  # 2025年3月1日
    end_date = datetime(2025, 5, 1)    # 2025年5月1日
    
    for i, p in enumerate(products):
        print(f"\n记录 {i+1}:")
        print(f"  产品编码: {p.get('产品编码')}")
        print(f"  产品型号: {p.get('产品型号')}")
        print(f"  绕线员工: {p.get('绕线员工')}, 时间: {p.get('绕线时间')}")
        print(f"  嵌线员工: {p.get('嵌线员工')}, 时间: {p.get('嵌线时间')}")
        print(f"  接线员工: {p.get('接线员工')}, 时间: {p.get('接线时间')}")
        print(f"  压装员工: {p.get('压装员工')}, 时间: {p.get('压装时间')}")
        print(f"  车止口员工: {p.get('车止口员工')}, 时间: {p.get('车止口时间')}")
        
        # 测试日期范围函数
        print("\n  日期范围测试结果:")
        
        # 测试员工匹配
        绕线匹配 = is_employee_match(p.get('绕线员工'), '方辉')
        print(f"  绕线员工匹配: {绕线匹配}")
        
        # 测试日期范围
        绕线时间匹配 = is_in_time_range(p, '绕线时间', '方辉', start_date, end_date)
        print(f"  绕线时间在范围内: {绕线时间匹配}")
        
        # 直接测试日期字符串
        if p.get('绕线时间'):
            日期字符串测试 = is_date_in_range(p.get('绕线时间'), start_date, end_date)
            print(f"  绕线时间字符串测试: {日期字符串测试}")
            
        # 打印原始日期字符串
        if p.get('绕线时间'):
            print(f"  原始绕线时间: {p.get('绕线时间')}")
            print(f"  原始绕线时间类型: {type(p.get('绕线时间'))}")
    
    # 关闭连接
    conn.close()

if __name__ == "__main__":
    check_records() 