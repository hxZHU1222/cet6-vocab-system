# CET-6 Vocabulary System

一个用于英语六级词汇与句型学习的本地 Web 应用。项目包含 948 个六级词条和一组六级写作句型，支持每日新词、复习、默写、错词/弱词追踪、句型卡片学习和学习统计。

> 本仓库适合个人学习、自托管和二次开发。仓库中不包含个人学习记录、数据库文件或本地密钥。

## 功能

- 词汇学习：每日新词、今日复习、随机学习、弱词与错词复习。
- 词汇默写：根据学习记录生成默写任务，记录错误并支持后续复习。
- 句型学习：六级写作句型库、每日句型学习与复习。
- 首页 Dashboard：合并展示词汇任务和句型任务。
- 统计页：展示词汇与句型的学习进度。
- CSV 导入：支持导入内置词库与句型库，也可以替换成自己的学习材料。
- 本地访问密码：适合部署在个人服务器或本机使用。

## 仓库内容

```text
cet6-vocab-system/
├─ backend/                 # Flask 后端、页面模板、静态资源
├─ data/
│  ├─ cet6_words.csv        # 内置 948 个六级词条
│  ├─ cet6_words_sample.csv # 少量样例词，便于快速测试
│  └─ cet6_sentence_patterns_import.csv # 六级写作句型导入表
├─ deployment/              # 可选的 Gunicorn / Nginx 部署示例
├─ instance/.gitkeep        # 本地数据库目录占位，不提交数据库
├─ wsgi.py                  # 生产环境入口
├─ README.md
└─ LICENSE
```

## 隐私与数据说明

本仓库已经移除以下内容：

- `backend/.env`：本地密钥、访问密码和数据库配置。
- `instance/*.db`：SQLite 数据库和个人学习记录。
- `__pycache__/` 与 `*.pyc`：Python 缓存文件。
- 个人服务器 IP、个人 Windows 路径和历史升级文档。

公开上传 GitHub 前，请确认不要提交：

```text
backend/.env
instance/*.db
exports/
backups/
__pycache__/
*.pyc
```

## 本地运行

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

### 2. 创建本地配置

```bash
cp backend/.env.example backend/.env
```

Windows PowerShell 可使用：

```powershell
Copy-Item backend\.env.example backend\.env
```

建议至少修改 `backend/.env` 中的：

```text
SECRET_KEY=change-me-to-a-long-random-string
APP_PASSWORD=cet6-local
```

### 3. 初始化数据库

```bash
python -m flask --app backend.app:create_app init-db
```

### 4. 导入内置词库与句型库

```bash
python -m flask --app backend.app:create_app import-default-words
python -m flask --app backend.app:create_app import-default-sentence-patterns
```

其中 `data/cet6_words.csv` 包含 948 个词条；句型库来自 `data/cet6_sentence_patterns_import.csv`。

### 5. 启动应用

```bash
python -m flask --app backend.app:create_app --debug run --host=127.0.0.1 --port=5000
```

浏览器打开：

```text
http://127.0.0.1:5000/
```

默认访问密码见 `backend/.env` 的 `APP_PASSWORD`。

## 常用命令

```bash
# 初始化或升级数据库表
python -m flask --app backend.app:create_app init-db
python -m flask --app backend.app:create_app upgrade-db

# 导入完整内置词库和句型库
python -m flask --app backend.app:create_app import-default-words
python -m flask --app backend.app:create_app import-default-sentence-patterns

# 只导入少量样例词，便于快速测试
python -m flask --app backend.app:create_app import-sample-words

# 查看词库、句型库和学习记录数量
python -m flask --app backend.app:create_app library-status

# 清空学习记录，但保留词库和句型库
python -m flask --app backend.app:create_app reset-all-learning
```

## 页面与接口

主要页面：

```text
/                  Dashboard
/study             词汇学习
/dictation         词汇默写
/patterns          句型库
/patterns/study    句型学习
/stats             学习统计
/words/import      词库导入
/patterns/import   句型导入
```

主要 API：

```text
GET  /api/dashboard/today
GET  /api/words/today
GET  /api/words/study?mode=today_new|today_review|weak|wrong|random|preview|mastered
POST /api/words/grade
GET  /api/words/dictation-session?mode=today|random|wrong|weak|learned
POST /api/words/dictation-submit
GET  /api/sentence-patterns/today
GET  /api/sentence-patterns/study?mode=today_new|today_review|new|review|weak|all
POST /api/sentence-patterns/grade
```

## 开源许可证

本项目采用 [MIT License](LICENSE)。你可以学习、使用、修改、分发和商用本项目代码，但需要保留原始版权声明和许可证文本。
