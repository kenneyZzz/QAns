# QAns安装部署

## 🚀 快速开始
### 1. 项目环境配置
```
# 新建虚拟环境
conda create -n QAns python=3.10
conda activate QAns
pip install -r requirements.txt
```

### 2. 关系型数据MySQL数据库部署和表初始化

```
cd deploy
docker compose -p qans -f docker-compose-mysql.yml up -d
# 表初始化
python ..\qans_server\init\init_mysql_db.py
```

### 3. 向量数据库Milvus部署和初始化

```
cd ../deploy
# windows
.\milvus-windows-install.bat start

# linux
bash milvus-linux-install.sh start

# 创建collection
python ..\qans_server\init\init_milvus_db.py
```
### 4. 项目配置部署
- qans_server/.env文件，LLM和向量模型API KEY配置，模型也可以替换为其他的。
[通义千问密钥配置URL](https://bailian.console.aliyun.com/?spm=5176.29597918.J_SEsSjsNv72yRuRFS2VknO.2.13587b08b2LUke&tab=model#/api-key)

```python
# LLM 配置
# 阿里通义千问
LLM_API_KEY=
# 向量模型
LLM_EMBEDDING_API_KEY=
```
- 项目部署
```
# qans_server
cd ..
# 当前目录是QAns根目录
python -m uvicorn qans_server.main:app --host localhost --port 8000 --reload

#qans_web
cd qans_web
npm i 
npm run dev
```
####  QAns系统首页地址：
http://localhost:5173/
