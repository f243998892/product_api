#!/bin/bash

# 脚本名称: restart_services.sh
# 说明: 重启产品管理系统相关的所有服务，解决iOS设备访问问题

echo "========== 开始重启服务 =========="
echo "$(date)"
echo "==================================="

# 0. 设置变量
API_DIR="/home/user/product_api"
NGINX_CONF="/etc/nginx/conf.d/nginx_product_system.conf"
NGINX_SERVICE="nginx"
PRODUCT_API_SERVICE="product_api"
NATTUNNEL_SERVICE="nattunnel"

# 1. 确保脚本具有执行权限
chmod +x "$0"
echo "脚本执行权限已设置"

# 2. 停止服务（顺序：API -> Nginx -> 内网穿透）
echo -e "\n2. 停止服务..."
echo "2.1 停止产品API服务"
sudo systemctl stop $PRODUCT_API_SERVICE || echo "警告: 无法停止API服务，可能不存在或已停止"

echo "2.2 停止Nginx服务"
sudo systemctl stop $NGINX_SERVICE || echo "警告: 无法停止Nginx服务，可能不存在或已停止"

echo "2.3 停止内网穿透服务"
sudo systemctl stop $NATTUNNEL_SERVICE || echo "警告: 无法停止内网穿透服务，可能不存在或已停止"

# 3. 确保目录存在
echo -e "\n3. 检查和准备目录..."
if [ ! -d "$API_DIR" ]; then
    echo "错误: API目录不存在，请检查路径"
    exit 1
fi

if [ ! -d "/var/www/product_system/patches" ]; then
    echo "创建补丁目录"
    sudo mkdir -p /var/www/product_system/patches
    sudo chown -R www-data:www-data /var/www/product_system/patches
fi

# 4. 应用文件修改
echo -e "\n4. 应用文件修改..."

# 确保补丁文件具有正确权限
if [ -f "/var/www/product_system/patches/ios-fix.js" ]; then
    echo "4.1 调整iOS补丁文件权限"
    sudo chmod 644 /var/www/product_system/patches/ios-fix.js
    sudo chown www-data:www-data /var/www/product_system/patches/ios-fix.js
else
    echo "警告: iOS补丁文件不存在"
fi

# 5. 启动服务（顺序：API -> Nginx -> 内网穿透）
echo -e "\n5. 启动服务..."
echo "5.1 启动产品API服务"
cd "$API_DIR" && bash run.sh &
sleep 3
echo "API服务启动中..."

echo "5.2 启动Nginx服务"
sudo systemctl start $NGINX_SERVICE
sleep 2

if [ $? -ne 0 ]; then
    echo "错误: 无法启动Nginx服务，请检查配置"
    nginx -t
else
    echo "Nginx服务已启动"
fi

echo "5.3 启动内网穿透服务"
sudo systemctl start $NATTUNNEL_SERVICE || echo "警告: 无法启动内网穿透服务，可能不存在"

# 6. 检查服务状态
echo -e "\n6. 检查服务状态..."
echo "6.1 API服务状态"
ps aux | grep -v grep | grep "uvicorn" | grep "app.main:app"

echo "6.2 Nginx服务状态"
sudo systemctl status $NGINX_SERVICE --no-pager | head -n 5

echo "6.3 内网穿透服务状态"
sudo systemctl status $NATTUNNEL_SERVICE --no-pager | head -n 5 || echo "内网穿透服务可能不是systemd管理的服务"

echo -e "\n========== 服务重启完成 =========="
echo "$(date)"
echo "===================================="

echo -e "\n如果iOS设备仍然无法正常访问，请尝试以下故障排除步骤:"
echo "1. 在iOS设备上清除浏览器缓存并重新加载页面"
echo "2. 确保iOS设备连接的是内网网络"
echo "3. 检查API日志查看iOS设备的请求是否正常到达"
echo "4. 如果还有问题，请查看 /var/log/nginx/error.log 和 $API_DIR/api.log" 