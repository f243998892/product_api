#!/bin/bash

# 显示当前内网穿透服务状态
echo "当前内网穿透服务状态："
systemctl status nattunnel.service

# 备份当前配置文件
echo "备份当前内网穿透配置文件..."
if [ -f /usr/local/nattunnel/nattunnel.ini ]; then
    sudo cp /usr/local/nattunnel/nattunnel.ini /usr/local/nattunnel/nattunnel.ini.bak
    echo "已备份至 /usr/local/nattunnel/nattunnel.ini.bak"
fi

# 复制修复后的配置文件
echo "复制修复后的配置文件..."
sudo cp /home/user/product_api/nattunnel_fixed.ini /usr/local/nattunnel/nattunnel.ini
sudo chmod 644 /usr/local/nattunnel/nattunnel.ini

# 重启内网穿透服务
echo "重启内网穿透服务..."
sudo systemctl restart nattunnel.service

# 等待服务重启
sleep 2

# 检查服务状态
echo "内网穿透服务重启后的状态："
systemctl status nattunnel.service

# 查看端口监听情况
echo "检查网络端口状态："
sudo netstat -tlnp | grep -E 'nattunnel|:80|:443'

echo "修复完成。请检查网站是否可以访问。" 