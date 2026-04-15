"""路由聚合入口"""
from fastapi import APIRouter
from api.query_routes import router as query_router
from api.file_routes import router as file_router
from api.knowledge_routes import router as knowledge_router
from api.session_routes import router as session_router

router = APIRouter()

# 注册子路由
router.include_router(query_router)
router.include_router(file_router)
router.include_router(knowledge_router)
router.include_router(session_router)
