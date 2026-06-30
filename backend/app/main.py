# -*- coding: utf-8 -*-
"""
FastAPI 应用入口
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from app.config import settings
from app.database import db
from app.api.templates import router as templates_router
from app.api.devices import router as devices_router
from app.api.patrol import router as patrol_router
from app.api.screenshot import router as screenshot_router
from app.api.terminal import router as terminal_router
from app.websocket.ssh_terminal import router as ssh_ws_router
from app.websocket.patrol_log import router as patrol_ws_router
from app.services.task_manager import task_manager


def mount_static_files(app):
    """挂载前端静态文件（如果存在）

    打包后前端文件会被打包到 web/dist 目录
    开发模式下使用 Vite dev server，不需要挂载
    """
    static_dir = settings.STATIC_DIR
    if not os.path.exists(static_dir):
        print(f"[提示] 前端静态文件目录不存在: {static_dir}")
        print(f"[提示] 开发模式下请使用前端 dev server: http://localhost:5173")
        return

    print(f"[启动] 前端静态文件目录: {static_dir}")

    # 挂载静态资源目录（assets 等）
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    index_path = os.path.join(static_dir, "index.html")

    # 根路径返回前端首页
    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(index_path)

    # SPA 路由支持：所有非 API 的 GET 请求都返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str):
        """SPA 前端路由 fallback"""
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return {"detail": "Not Found"}
        # 先检查是否是静态文件（favicon.ico 等）
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # 否则返回 index.html，让前端路由处理
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Not Found"}


def create_app():
    """创建并配置FastAPI应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="设备巡检助手 - API服务"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    @app.on_event("startup")
    async def startup_event():
        """应用启动时初始化数据库"""
        db.init_db()
        task_manager.start_cleanup_scheduler()

    @app.get("/api/health", tags=["健康检查"])
    async def health_check():
        """健康检查接口"""
        return {"status": "ok", "message": "服务运行正常"}

    # 注册 API 路由
    app.include_router(templates_router)
    app.include_router(devices_router)
    app.include_router(patrol_router)
    app.include_router(screenshot_router)
    app.include_router(terminal_router)

    # 注册 WebSocket 路由
    app.include_router(ssh_ws_router)
    app.include_router(patrol_ws_router)

    # 挂载前端静态文件（必须在 API 路由之后，避免覆盖 API）
    mount_static_files(app)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
