# 前端启动文档

本项目前端不需要单独启动 `npm` 服务。前端页面由 FastAPI 后端静态托管，所以启动后端服务后，直接在浏览器访问服务地址即可。

## 1. 进入项目目录

```powershell
cd E:\111tiaozhanketi--ai--game\maze
```

## 2. 安装依赖

如果已经安装过，可以跳过这一步。

```powershell
E:\anaconda3\python.exe -m pip install -r requirements.txt
```

如果你使用的是当前命令行里的默认 Python，也可以运行：

```powershell
python -m pip install -r requirements.txt
```

## 3. 启动服务

推荐使用 8000 端口：

```powershell
E:\anaconda3\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

如果 8000 端口已经被占用，就换一个端口，例如 8001：

```powershell
E:\anaconda3\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

## 4. 打开前端页面

如果服务启动在 8000 端口，打开：

```text
http://127.0.0.1:8000/
```

如果服务启动在 8001 端口，打开：

```text
http://127.0.0.1:8001/
```

不要直接双击 `frontend/index.html` 打开。直接用 `file:///` 打开会导致 `/static/js/app.js`、`/static/css/style.css`、`/resources/背景.mp4` 等资源加载失败。

## 5. 页面资源说明

- 前端入口：`frontend/index.html`
- 样式文件：`frontend/static/css/style.css`
- 前端逻辑：`frontend/static/js/app.js`
- API 封装：`frontend/static/js/api.js`
- 登录背景和 Boss 视频资源：`resources/`
- 地图 JSON：`map/`

这些资源都会通过 FastAPI 服务自动挂载：

- `/static/...`
- `/resources/...`
- `/map/...`
- `/api/...`

## 6. 停止服务

在启动服务的命令行窗口里按：

```text
Ctrl + C
```

## 7. 常见问题

### 页面白屏

优先确认你打开的是：

```text
http://127.0.0.1:8000/
```

或实际启动时使用的端口地址，而不是 `file:///.../frontend/index.html`。

### 8000 端口被占用

换端口启动：

```powershell
E:\anaconda3\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

然后访问：

```text
http://127.0.0.1:8001/
```

### 修改前端后浏览器没变化

按 `Ctrl + F5` 强制刷新页面。当前首页已经设置了 `Cache-Control: no-store`，正常情况下刷新后会加载最新文件。
