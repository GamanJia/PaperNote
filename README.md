# PaperNote

PaperNote 是一个本地单用户论文检索与筛选工具。  
输入会议/期刊、日期区间、关键词或研究描述后，系统会从 OpenAlex 与 arXiv 拉取候选论文，并可调用 LLM 做语义筛选和摘要，最终在 Web 页面展示并支持导出。

## 平台兼容性

- 支持：macOS / Linux / Windows
- 后端：Python 3.11+
- 前端：Node.js 18+（建议 20 LTS）
- 包管理：`pip` + `npm`

可用 `conda` 或 `venv`，不强制绑定某个系统。

## 项目结构

```text
PaperNote/
  backend/
  frontend/
  data/
    searches/
    exports/
    cache/
    config/
  scripts/
    start_backend.sh
    start_frontend.sh
    start_backend.ps1
    start_frontend.ps1
    start_backend.bat
    start_frontend.bat
  .env.example
  README.md
```

## 1. 安装依赖

### 方案 A：conda（推荐）

```bash
conda create -n papernote python=3.11 -y
conda activate papernote
cd backend
pip install -r requirements.txt
cd ../frontend
npm install
```

### 方案 B：venv

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

cd backend
pip install -r requirements.txt
cd ../frontend
npm install
```

## 2. 配置环境变量

### macOS/Linux

```bash
cp .env.example .env
```

### Windows CMD

```bat
copy .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

关键变量：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL_NAME=gpt-4o-mini
OPENALEX_MAILTO=
OLLAMA_BASE_URL=http://localhost:11434
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_HOST=127.0.0.1
FRONTEND_PORT=5173
FRONTEND_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

## 3. 启动项目

默认前端：`http://127.0.0.1:5173`  
默认后端：`http://127.0.0.1:8000`

### macOS/Linux（脚本）

```bash
./scripts/start_backend.sh
./scripts/start_frontend.sh
```

### Windows PowerShell（脚本）

```powershell
.\scripts\start_backend.ps1
.\scripts\start_frontend.ps1
```

如果提示脚本执行策略限制：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Windows CMD（脚本）

```bat
scripts\start_backend.bat
scripts\start_frontend.bat
```

### 手动启动（所有系统通用）

后端：

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## 可配置端口

可通过环境变量覆盖默认端口：

- `BACKEND_HOST` / `BACKEND_PORT`
- `FRONTEND_HOST` / `FRONTEND_PORT`

启动脚本已支持这些变量。

## 代理与网络

如果你使用 SOCKS 代理访问外网，`backend/requirements.txt` 已包含 `socksio`。  
若遇到网络错误，重新安装后端依赖：

```bash
cd backend
pip install -r requirements.txt
```

建议配置 `OPENALEX_MAILTO` 为你的邮箱，以启用 OpenAlex polite pool，降低 429 限流概率。

## 数据与隐私

- 项目使用本地文件存储，不使用数据库。
- 运行时数据目录：`data/searches`、`data/cache`、`data/exports`、`data/config/settings.json`
- 仓库中仅保留 `.gitkeep`，运行数据默认不提交。
- `OPENAI_API_KEY` 放在 `.env`，不要提交到 Git。

## API 列表

- `POST /api/search`
- `GET /api/history`
- `GET /api/history/{search_id}`
- `DELETE /api/history/{search_id}`
- `POST /api/history/{search_id}/rerun`
- `POST /api/export`
- `GET /api/exports/{file_name}`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/llm/test`
- `GET /api/sources`
- `GET /healthz`
