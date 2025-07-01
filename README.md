# 产品API服务

## 部署步骤

1. 克隆代码到服务器：
```bash
git clone <仓库地址> /home/user/product_api
```

2. 安装必要软件：
```bash
sudo apt update
sudo apt install python3-venv python3-pip
```

3. 配置服务：
```bash
sudo cp product_api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable product_api.service
sudo systemctl start product_api.service
```

4. 查看服务状态：
```bash
sudo systemctl status product_api.service
```

5. 查看日志：
```bash
sudo journalctl -u product_api.service -f
# 或查看应用日志
cat /home/user/product_api/api.log
```