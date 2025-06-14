from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime, timezone, timedelta

from database import get_db_connection

app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义数据模型
class UpdateProductProcess(BaseModel):
    productCode: str
    processType: str
    employeeName: str
    timeField: str
    employeeField: str
    timestamp: str

class BatchUpdateProductProcess(BaseModel):
    productCodes: List[str]
    processType: str
    employeeName: str

class DeleteProductProcess(BaseModel):
    productCode: str
    processType: str
    employeeName: str
    timeField: str
    employeeField: str

# API端点
@app.get("/")
async def root():
    return {"message": "产品管理系统API"}

@app.get("/api/test")
async def test_api():
    """
    简单的测试接口，验证API是否正常工作
    """
    return {
        "status": "ok",
        "message": "API服务正常运行",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/updateProductProcess")
async def update_product_process(data: UpdateProductProcess):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 查询产品型号
        cursor.execute('SELECT "产品型号" FROM products WHERE "产品编码" = %s', (data.productCode,))
        product_row = cursor.fetchone()
        product_model = product_row["产品型号"] if product_row and isinstance(product_row, dict) else (product_row[0] if product_row else None)
        # 检查是否在exception表
        if data.processType == 'wiring':
            skip_check = False
            if product_model:
                cursor.execute('SELECT 1 FROM exception WHERE "产品型号" = %s LIMIT 1', (product_model,))
                exception_row = cursor.fetchone()
                if exception_row:
                    skip_check = True
            if not skip_check:
                cursor.execute(
                    'SELECT "绕线时间" FROM products WHERE "绕线员工" = %s AND "绕线时间" IS NOT NULL ORDER BY "绕线时间" DESC LIMIT 1',
                    (data.employeeName,)
                )
                row = cursor.fetchone()
                if row:
                    latest_time = row["绕线时间"] if isinstance(row, dict) else row[0]
                    try:
                        from datetime import timezone
                        now = datetime.now(timezone.utc)
                        t2 = datetime.fromisoformat(str(latest_time).replace('Z', '+00:00'))
                        if abs((now - t2).total_seconds()) < 300:
                            conn.close()
                            raise HTTPException(status_code=400, detail="两次录入绕线工序时间间隔小于5分钟，禁止录入")
                    except Exception as e:
                        pass
        else:
            # 查不到产品型号，默认校验
            cursor.execute(
                'SELECT "绕线时间" FROM products WHERE "绕线员工" = %s AND "绕线时间" IS NOT NULL ORDER BY "绕线时间" DESC LIMIT 1',
                (data.employeeName,)
            )
            row = cursor.fetchone()
            if row:
                latest_time = row["绕线时间"] if isinstance(row, dict) else row[0]
                try:
                    from datetime import timezone
                    now = datetime.now(timezone.utc)
                    t2 = datetime.fromisoformat(str(latest_time).replace('Z', '+00:00'))
                    if abs((now - t2).total_seconds()) < 300:
                        conn.close()
                        raise HTTPException(status_code=400, detail="两次录入绕线工序时间间隔小于5分钟，禁止录入")
                except Exception as e:
                    # 日期格式异常不拦截
                    pass
        # 检查产品是否存在
        cursor.execute(
            "SELECT * FROM products WHERE \"产品编码\" = %s",
            (data.productCode,)
        )
        product = cursor.fetchone()
        if not product:
            # 修改：如果产品不存在，则直接插入新记录，而不是返回错误
            print(f"产品不存在，创建新记录: {data.productCode}")
            insert_data = {
                "产品编码": data.productCode,
                data.timeField: data.timestamp
            }
            if data.employeeField:
                insert_data[data.employeeField] = data.employeeName
            columns = ', '.join([f'"{k}"' for k in insert_data.keys()])
            placeholders = ', '.join(['%s'] * len(insert_data))
            values = list(insert_data.values())
            query = f'INSERT INTO products ({columns}) VALUES ({placeholders})'
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return {"success": True}
        # 检查工序字段是否已有数据
        if product[data.timeField]:
            conn.close()
            raise HTTPException(status_code=400, detail="该产品的该工序已存在数据，不能覆盖")
        # 更新数据
        update_data = {data.timeField: data.timestamp}
        if data.employeeField:
            update_data[data.employeeField] = data.employeeName
        update_fields = ", ".join([f'"{k}" = %s' for k in update_data.keys()])
        update_values = list(update_data.values())
        query = f"UPDATE products SET {update_fields} WHERE \"产品编码\" = %s"
        cursor.execute(query, update_values + [data.productCode])
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batchUpdateProductProcess")
async def batch_update_product_process(data: BatchUpdateProductProcess):
    results = []
    
    for code in data.productCodes:
        try:
            # 构建单个更新请求
            update_data = UpdateProductProcess(
                productCode=code,
                processType=data.processType,
                employeeName=data.employeeName,
                timeField=get_time_field(data.processType),
                employeeField=get_employee_field(data.processType),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # 尝试更新
            try:
                await update_product_process(update_data)
                results.append({"code": code, "success": True})
            except HTTPException as e:
                # 记录错误信息但继续处理其他产品
                print(f"更新产品失败: {code}, 错误: {str(e.detail)}")
                # 如果是400错误（工序已存在），则标记为失败，其他错误(如404-产品不存在)不再出现因为修改了函数
                results.append({"code": code, "success": False, "error": str(e.detail)})
        except Exception as e:
            print(f"处理产品异常: {code}, 错误: {str(e)}")
            results.append({"code": code, "success": False, "error": str(e)})
    
    return {"results": results}

@app.get("/api/getProductDetails")
async def get_product_details(productCode: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM products WHERE \"产品编码\" = %s",
            (productCode,)
        )
        product = cursor.fetchone()
        
        if not product:
            raise HTTPException(status_code=404, detail="产品不存在")
        
        return {"data": dict(product)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/getUserMonthlyProducts")
async def get_user_monthly_products(employeeName: str, startDate: str, endDate: str):
    conn = None
    try:
        # 先获取所有产品
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT * FROM products 
        WHERE ("绕线员工" LIKE %s OR "嵌线员工" LIKE %s OR "接线员工" LIKE %s OR 
                   "压装员工" LIKE %s OR "车止口员工" LIKE %s OR "浸漆员工" LIKE %s)
        ORDER BY "产品编码"
        """
        
        # 在参数两侧添加%以进行模糊匹配
        search_name = f"%{employeeName.strip()}%"
        cursor.execute(query, [search_name] * 6)
        products = cursor.fetchall()
        
        # 查询完毕后关闭连接
        conn.close()
        conn = None
        
        # 在Python中过滤日期范围
        try:
            start_date = datetime.fromisoformat(startDate.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(endDate.replace('Z', '+00:00'))
            print(f"[DEBUG] 日期解析成功: start_date={start_date}, end_date={end_date}")
        except Exception as e:
            print(f"[ERROR] 日期解析错误: {str(e)}")
            # 如果日期解析失败，使用当前月份范围
            now = datetime.now()
            start_date = datetime(now.year, now.month, 1)
            # 正确处理月份溢出
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
            end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
            
        print(f"[DEBUG] 日期范围: {start_date.isoformat()} 至 {end_date.isoformat()}")
        
        filtered_products = []
        for product in products:
            try:
                # 检查员工是否在时间范围内参与了工序，使用更宽松的匹配
                if is_employee_match(product.get("绕线员工"), employeeName) and is_in_time_range(product, "绕线时间", employeeName, start_date, end_date) or \
                   is_employee_match(product.get("嵌线员工"), employeeName) and is_in_time_range(product, "嵌线时间", employeeName, start_date, end_date) or \
                   is_employee_match(product.get("接线员工"), employeeName) and is_in_time_range(product, "接线时间", employeeName, start_date, end_date) or \
                   is_employee_match(product.get("压装员工"), employeeName) and is_in_time_range(product, "压装时间", employeeName, start_date, end_date) or \
                   is_employee_match(product.get("车止口员工"), employeeName) and is_in_time_range(product, "车止口时间", employeeName, start_date, end_date) or \
                   is_employee_match(product.get("浸漆员工"), employeeName) and is_in_time_range(product, "浸漆时间", employeeName, start_date, end_date):
                    filtered_products.append(dict(product))
            except Exception as e:
                print(f"[ERROR] 处理产品时出错: {str(e)}")
        
        print(f"[DEBUG] 过滤后产品数量: {len(filtered_products)}")
        
        # 返回响应，添加特殊标记以便前端处理
        response = {
            "data": filtered_products,
            "client_info": {
                "is_ios": False
            }
        }
        
        return response
    except Exception as e:
        print(f"[ERROR] 总体异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.get("/api/getUserMonthlyTransactions")
async def get_user_monthly_transactions(employeeName: str, startDate: str, endDate: str):
    conn = None
    try:
        print(f"查询月度交易: employeeName={employeeName}, startDate={startDate}, endDate={endDate}")
        
        # 先获取所有产品
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT * FROM products 
        WHERE ("绕线员工" LIKE %s OR "嵌线员工" LIKE %s OR "接线员工" LIKE %s OR 
                   "压装员工" LIKE %s OR "车止口员工" LIKE %s OR "浸漆员工" LIKE %s)
        ORDER BY "产品编码"
        """
        
        # 在参数两侧添加%以进行模糊匹配
        search_name = f"%{employeeName.strip()}%"
        cursor.execute(query, [search_name] * 6)
        products = cursor.fetchall()
        
        print(f"查询到 {len(products)} 条产品记录")
        
        # 查询完毕后关闭连接
        conn.close()
        conn = None
        
        # 处理成交易记录格式
        try:
            start_date = datetime.fromisoformat(startDate.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(endDate.replace('Z', '+00:00'))
        except Exception as e:
            print(f"日期解析错误: {str(e)}")
            # 如果日期解析失败，使用当前月份范围
            now = datetime.now()
            start_date = datetime(now.year, now.month, 1)
            # 正确处理月份溢出
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
            end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        
        transactions = []
        
        for product in products:
            try:
                product_dict = dict(product)
                
                # 检查每个工序，使用更宽松的员工名称匹配
                if is_employee_match(product_dict.get("绕线员工"), employeeName) and is_date_in_range(product_dict.get("绕线时间"), start_date, end_date):
                    transactions.append({
                        "process": "绕线",
                        "productCode": product_dict.get("产品编码"),
                        "model": product_dict.get("产品型号", "未知型号"),
                        "time": product_dict.get("绕线时间")
                    })
                
                if is_employee_match(product_dict.get("嵌线员工"), employeeName) and is_date_in_range(product_dict.get("嵌线时间"), start_date, end_date):
                    transactions.append({
                        "process": "嵌线",
                        "productCode": product_dict.get("产品编码"),
                        "model": product_dict.get("产品型号", "未知型号"),
                        "time": product_dict.get("嵌线时间")
                    })
                
                if is_employee_match(product_dict.get("接线员工"), employeeName) and is_date_in_range(product_dict.get("接线时间"), start_date, end_date):
                    transactions.append({
                        "process": "接线",
                        "productCode": product_dict.get("产品编码"),
                        "model": product_dict.get("产品型号", "未知型号"),
                        "time": product_dict.get("接线时间")
                    })
                
                if is_employee_match(product_dict.get("压装员工"), employeeName) and is_date_in_range(product_dict.get("压装时间"), start_date, end_date):
                    transactions.append({
                        "process": "压装",
                        "productCode": product_dict.get("产品编码"),
                        "model": product_dict.get("产品型号", "未知型号"),
                        "time": product_dict.get("压装时间")
                    })
                
                if is_employee_match(product_dict.get("车止口员工"), employeeName) and is_date_in_range(product_dict.get("车止口时间"), start_date, end_date):
                    transactions.append({
                        "process": "车止口",
                        "productCode": product_dict.get("产品编码"),
                        "model": product_dict.get("产品型号", "未知型号"),
                        "time": product_dict.get("车止口时间")
                    })

                if is_employee_match(product_dict.get("浸漆员工"), employeeName) and is_date_in_range(product_dict.get("浸漆时间"), start_date, end_date):
                    transactions.append({
                        "process": "浸漆",
                        "productCode": product_dict.get("产品编码"),
                        "model": product_dict.get("产品型号", "未知型号"),
                        "time": product_dict.get("浸漆时间")
                    })
            except Exception as e:
                print(f"处理产品交易记录时出错: {str(e)}")
                # 继续处理下一个产品
                continue
        
        print(f"筛选后 {len(transactions)} 条交易记录在时间范围内")
        
        return {"data": transactions}
    except Exception as e:
        print(f"查询月度交易失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/deleteProductProcess")
async def delete_product_process(data: DeleteProductProcess):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 检查产品是否存在
        cursor.execute(
            "SELECT * FROM products WHERE \"产品编码\" = %s",
            (data.productCode,)
        )
        product = cursor.fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="产品不存在")
        # 检查是否是当前用户的工序 - 浸漆工序特殊处理
        if data.employeeField and data.processType != '浸漆' and product[data.employeeField] != data.employeeName:
            raise HTTPException(status_code=403, detail="不是当前用户的工序")
        # 清除工序信息
        update_data = {data.timeField: None}
        if data.employeeField:
            update_data[data.employeeField] = None
        update_fields = ", ".join([f"\"{k}\" = %s" for k in update_data.keys()])
        update_values = list(update_data.values())
        query = f"UPDATE products SET {update_fields} WHERE \"产品编码\" = %s"
        cursor.execute(query, update_values + [data.productCode])
        conn.commit()
        return {"success": True}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# 辅助函数
def get_time_field(process_type):
    process_name = get_chinese_process_name(process_type)
    return f"{process_name}时间"

def get_employee_field(process_type):
    process_name = get_chinese_process_name(process_type)
    return f"{process_name}员工"

def get_chinese_process_name(process_type):
    mapping = {
        'wiring': '绕线',
        'embedding': '嵌线',
        'wiring_connect': '接线',
        'pressing': '压装',
        'stopper': '车止口',
        'immersion': '浸漆'
    }
    return mapping.get(process_type, process_type)

def is_employee_match(db_employee, query_employee):
    if not db_employee or not query_employee:
        return False
    
    # 移除所有空格后比较
    db_clean = db_employee.replace(" ", "").strip()
    query_clean = query_employee.replace(" ", "").strip()
    
    # 检查一个是否包含另一个
    return db_clean in query_clean or query_clean in db_clean

def is_in_time_range(product, time_field, employee_name, start_date, end_date):
    if not product or time_field not in product or not product.get(time_field):
        return False
    
    time_value = product.get(time_field)
    try:
        # 直接处理datetime对象
        if isinstance(time_value, datetime):
            print(f"日期对象直接比较: {time_field}={time_value}")
            # 确保时区正确处理
            if time_value.tzinfo is not None and start_date.tzinfo is None:
                # 如果需要，可以移除时区信息或调整时区
                time_naive = time_value.replace(tzinfo=None)
                result = start_date <= time_naive <= end_date
            else:
                result = start_date <= time_value <= end_date
            
            if result:
                print(f"时间在范围内: {time_field}={time_value}, 比较结果={result}")
            return result
        
        # 处理字符串格式日期
        time_str = str(time_value)
        try:
            time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            # 尝试其他格式
            formats = ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", 
                       "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]
            for fmt in formats:
                try:
                    time = datetime.strptime(time_str, fmt)
                    break
                except:
                    continue
            else:
                # 如果所有格式都失败
                return False
                
        # 确保时区一致
        if time.tzinfo is not None and start_date.tzinfo is None:
            time = time.replace(tzinfo=None)
            
        result = start_date <= time <= end_date
        if result:
            print(f"时间在范围内: {time_field}={time_str}, 比较结果={result}")
        return result
    except Exception as e:
        print(f"时间格式错误: {time_field}={time_value}, 错误={str(e)}")
        return False

def is_date_in_range(date_value, start_date, end_date):
    if not date_value:
        return False
    
    try:
        # 直接处理datetime对象
        if isinstance(date_value, datetime):
            print(f"日期对象直接比较: {date_value}")
            # 确保时区正确处理
            if date_value.tzinfo is not None and start_date.tzinfo is None:
                # 如果需要，可以移除时区信息或调整时区
                date_naive = date_value.replace(tzinfo=None)
                result = start_date <= date_naive <= end_date
            else:
                result = start_date <= date_value <= end_date
            
            if result:
                print(f"日期在范围内: {date_value}, 比较结果={result}")
            return result
            
        # 处理字符串格式日期
        date_str = str(date_value)
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            # 尝试其他格式
            formats = ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", 
                       "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]
            for fmt in formats:
                try:
                    date = datetime.strptime(date_str, fmt)
                    break
                except:
                    continue
            else:
                # 如果所有格式都失败
                return False
        
        # 确保时区一致
        if date.tzinfo is not None and start_date.tzinfo is None:
            date = date.replace(tzinfo=None)
            
        result = start_date <= date <= end_date
        if result:
            print(f"日期在范围内: {date_str}, 比较结果={result}")
        return result
    except Exception as e:
        print(f"日期格式错误: {date_value}, 错误={str(e)}")
        return False

@app.get("/api/getMonthRange")
async def get_month_range():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 尝试从数据库获取月份范围
        try:
            # 查询month_range表
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'month_range'")
            columns = [col["column_name"] for col in cursor.fetchall()]
            print(f"month_range表的列: {columns}")
            
            cursor.execute("SELECT * FROM month_range ORDER BY id DESC LIMIT 1")
            range_data = cursor.fetchone()
            
            if range_data:
                print(f"获取到月份范围数据: {range_data}")
                # 尝试确定正确的列名
                start_date_field = None
                end_date_field = None
                
                # 查找可能的开始日期和结束日期字段
                for field in ["month_start", "start_date", "startdate", "start_time"]:
                    if field in range_data:
                        start_date_field = field
                        break
                
                for field in ["month_end", "end_date", "enddate", "end_time"]:
                    if field in range_data:
                        end_date_field = field
                        break
                
                if start_date_field and end_date_field:
                    print(f"使用字段: start={start_date_field}, end={end_date_field}")
                    start_date = range_data[start_date_field]
                    end_date = range_data[end_date_field]
                    
                    if start_date and end_date:
                        return {
                            "data": {
                                "startDate": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
                                "endDate": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
                            }
                        }
                else:
                    print(f"无法找到合适的日期字段，返回默认日期")
            else:
                print("没有找到月份范围数据")
                
        except Exception as db_error:
            print(f"查询month_range表出错: {str(db_error)}")
            
        return {
            "data": {
                "startDate": first_day.isoformat(),
                "endDate": last_day.isoformat()
            }
        }
    except Exception as e:
        print(f"获取月份范围出错: {str(e)}")
        # 出错时返回当前月份
        now = datetime.now()
        first_day = datetime(now.year, now.month, 1)
        # 正确处理月份溢出
        if now.month == 12:
            last_day = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
        last_day = datetime(last_day.year, last_day.month, last_day.day, 23, 59, 59)
        
        return {
            "data": {
                "startDate": first_day.isoformat(),
                "endDate": last_day.isoformat()
            }
        }

@app.get("/api/modelSeries")
async def get_model_series():
    """
    获取所有产品型号与工艺分类信息
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM model_series')
        rows = cursor.fetchall()
        return {"data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/seriesProcesses")
async def get_series_processes():
    """
    获取所有工艺分类与工序流程信息
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM series_processes')
        rows = cursor.fetchall()
        return {"data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/getUserTodayProcessCount")
async def get_user_today_process_count(employeeName: str = Query(...)):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 获取东八区时区
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz)
        start_date = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz)
        end_date = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=tz)
        # 查询所有与该员工有关的产品
        query = '''
        SELECT * FROM products 
        WHERE ("绕线员工" LIKE %s OR "嵌线员工" LIKE %s OR "接线员工" LIKE %s OR 
                   "压装员工" LIKE %s OR "车止口员工" LIKE %s OR "浸漆员工" LIKE %s)
        '''
        search_name = f"%{employeeName.strip()}%"
        cursor.execute(query, [search_name] * 6)
        products = cursor.fetchall()
        conn.close()
        conn = None
        # 统计每个工序今日数量
        process_map = {
            "绕线": ("绕线员工", "绕线时间"),
            "嵌线": ("嵌线员工", "嵌线时间"),
            "接线": ("接线员工", "接线时间"),
            "压装": ("压装员工", "压装时间"),
            "车止口": ("车止口员工", "车止口时间"),
            "浸漆": ("浸漆员工", "浸漆时间")
        }
        result = []
        for process, (emp_field, time_field) in process_map.items():
            count = 0
            for product in products:
                if is_employee_match(product.get(emp_field), employeeName):
                    t = product.get(time_field)
                    if t:
                        try:
                            # 统一转为东八区时间
                            if isinstance(t, str):
                                dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=tz)
                                else:
                                    dt = dt.astimezone(tz)
                            elif isinstance(t, datetime):
                                if t.tzinfo is None:
                                    dt = t.replace(tzinfo=tz)
                                else:
                                    dt = t.astimezone(tz)
                            else:
                                continue
                            if start_date <= dt <= end_date:
                                count += 1
                        except Exception:
                            continue
            if count > 0:
                result.append({"process": process, "count": count})
        return {"data": result}
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))
