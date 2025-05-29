#!/bin/bash

# 设置日志文件
LOG_FILE="/home/user/product_api/api.log"
echo "启动API服务: $(date)" > $LOG_FILE

# 确保需要的包已安装
echo "安装所需包..." >> $LOG_FILE
python3 -m pip install --break-system-packages -r requirements.txt >> $LOG_FILE 2>&1

# 切换到app目录并启动应用
cd app
echo "启动应用..." >> $LOG_FILE
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 >> $LOG_FILE 2>&1
