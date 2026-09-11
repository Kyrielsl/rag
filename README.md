# RAG 企业知识库

面向企业的私有化知识库系统：文件上传 → 内容提取 → 分类路由 → 存储 → 精确查询。MVP 支持 txt/csv/json。

> 当前状态：MVP 代码已实现（M1-M5 完成，M6 部署配置已就绪）。

## 技术栈

Python(FastAPI) · PostgreSQL · Redis · S3 兼容对象存储（本地 MinIO，上线切 S3）· Docker · LangChain + DeepSeek（OpenAI 兼容格式）· pgvector（中期）

## 快速开始

1. 复制环境变量模板并填写：

   ```bash
   cp .env.example .env
   ```

2. 本地开发（Postgres + Redis + MinIO）：

   ```bash
   docker compose up -d postgres redis minio
   pip install -e .
   uvicorn app.main:app --reload
   ```

   健康检查：`GET http://localhost:8000/health`

3. 生产部署（含 Nginx HTTPS 网关，对象存储使用外部 S3）：

   ```bash
   # 将 TLS 证书放入 deploy/certs/fullchain.pem 与 deploy/certs/privkey.pem
   docker compose -f docker-compose.prod.yml up -d --build
   ```

## 主要接口

- `POST /auth/login`：管理员登录（默认 admin / admin123，上线前必须修改）
- `POST /admin/api-keys`：创建 API Key（上传/检索分离）
- `POST /uploads/...`：上传、分片、秒传、提取、分类
- `POST /search`、`GET /domains`、`GET /documents/{id}`：检索与敏感域授权
- `GET /admin/dashboard`、`GET /admin/audit`：审计与管理后台

## 路线

- MVP：txt/csv/json、内容提取、LLM 分类路由、精确查询、JWT/RBAC/审计
- 中期：更多文件类型、内容分析优化、语义检索、pgvector
- 长期：客户定制、用户画像、专业化 Skills、体验优化