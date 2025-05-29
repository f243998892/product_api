#!/bin/bash
# 修复iOS HTTPS访问问题的脚本

echo "========== 开始修复iOS HTTPS访问问题 =========="
echo "$(date)"
echo "============================================="

# 1. 确保证书文件权限正确
echo -e "\n1. 检查并修正证书权限..."
sudo chmod 644 /etc/nginx/ssl/private-ca/internal.crt || echo "警告: 无法修改证书权限，可能路径不存在"
sudo chmod 600 /etc/nginx/ssl/private-ca/internal.key || echo "警告: 无法修改密钥权限，可能路径不存在"

# 2. 复制特殊的iOS HTTPS参数到Nginx配置
echo -e "\n2. 应用Nginx SSL参数优化..."
if [ -f "/tmp/ios_https_fix.conf" ]; then
    sudo cp /tmp/ios_https_fix.conf /etc/nginx/conf.d/ios_https_fix.conf
    sudo chmod 644 /etc/nginx/conf.d/ios_https_fix.conf
    echo "已配置SSL优化参数"
else
    echo "错误: 未找到/tmp/ios_https_fix.conf文件"
    exit 1
fi

# 3. 修改Nginx HTTPS配置，添加iOS特定头部
echo -e "\n3. 修改Nginx配置文件，添加iOS特定头部..."

# 找到Nginx配置文件
NGINX_CONF="/etc/nginx/sites-available/nginx_product_system.conf"
if [ ! -f "$NGINX_CONF" ]; then
    # 尝试其他可能的位置
    NGINX_CONF="/etc/nginx/sites-available/product_system.conf"
    if [ ! -f "$NGINX_CONF" ]; then
        echo "错误: 找不到Nginx配置文件"
        exit 1
    fi
fi

# 创建临时文件进行修改
TEMP_CONF=$(mktemp)
cat "$NGINX_CONF" > "$TEMP_CONF"

# 检查是否已有iOS特定头部
if grep -q "X-iOS-Compatible" "$NGINX_CONF"; then
    echo "配置已存在iOS特定头部，跳过此步骤"
else
    # 在HTTPS服务器块中添加iOS特定头部
    sed -i '/server {[[:space:]]*listen 443 ssl;/,/}/s/location \/ {/location \/ {\n        # iOS特定头部\n        add_header Access-Control-Allow-Origin "*";\n        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";\n        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-iOS-Client";\n        add_header X-iOS-Compatible "true";\n        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;/' "$TEMP_CONF"
    
    # 检查修改是否成功
    if grep -q "X-iOS-Compatible" "$TEMP_CONF"; then
        sudo cp "$TEMP_CONF" "$NGINX_CONF"
        echo "成功添加iOS特定头部"
    else
        echo "警告: 无法添加iOS特定头部，使用手动方式"
        echo "请手动在 $NGINX_CONF 的HTTPS server块中添加以下内容:"
        echo '        add_header Access-Control-Allow-Origin "*";'
        echo '        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";'
        echo '        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-iOS-Client";'
        echo '        add_header X-iOS-Compatible "true";'
        echo '        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
    fi
fi

# 清理临时文件
rm -f "$TEMP_CONF"

# 4. 测试Nginx配置并重启
echo -e "\n4. 测试Nginx配置..."
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "Nginx配置测试通过，准备重启服务"
    
    # 5. 重启Nginx服务
    echo -e "\n5. 重启Nginx服务..."
    sudo systemctl restart nginx
    
    if [ $? -eq 0 ]; then
        echo "Nginx服务重启成功"
    else
        echo "错误: Nginx服务重启失败"
        exit 1
    fi
else
    echo "错误: Nginx配置测试失败，请检查配置文件"
    exit 1
fi

# 6. 重新加载iOS相关服务
echo -e "\n6. 重启API服务..."
API_DIR="/home/user/product_api"
cd "$API_DIR" && bash run.sh &
sleep 2
echo "API服务已重启"

echo -e "\n========== iOS HTTPS访问修复完成 =========="
echo "$(date)"
echo "=============================================="

echo -e "\n请在iOS设备上按照以下步骤测试HTTPS访问:"
echo "1. 安装自签名证书（如果尚未安装）"
echo "2. 在设置中完全信任证书: 设置 > 通用 > 关于本机 > 证书信任设置"
echo "3. 重新打开Safari浏览器，访问https://您的域名"
echo "4. 如果仍有问题，请尝试: 设置 > Safari > 清除历史记录与网站数据"
echo "5. 如果问题持续存在，请查看Nginx错误日志: /var/log/nginx/error.log" 