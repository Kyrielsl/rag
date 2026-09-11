# RAG 企业知识库

面向企业的私有化知识库系统：文件上传 → 内容提取 → 分类路由 → 存储 → 精确查询。MVP 支持 txt/csv/json。

> 当前状态：设计完成，进入实现阶段。设计文档保留在本地 `docs/`（不纳入版本控制）。

## 技术栈

Python(FastAPI) · PostgreSQL · S3 兼容对象存储（本地 MinIO，上线切 S3）· Docker · LangChain + DeepSeek（OpenAI 兼容格式）· pgvector（中期）

## 路线

- MVP：txt/csv/json、内容提取、LLM 分类路由、精确查询、JWT/RBAC/审计
- 中期：更多文件类型、内容分析优化、语义检索、pgvector
- 长期：客户定制、用户画像、专业化 Skills、体验优化