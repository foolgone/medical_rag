"""文件上传管理路由"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
from api.schemas import (
    FileUploadResponse, BatchUploadResponse,
    FileListResponse, DeleteDocumentsResponse, FileInfo
)
from rag.file_upload_service import FileUploadService
from loguru import logger

router = APIRouter(tags=["文件管理"])
file_service = FileUploadService()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), category: str = "general"):
    """单文件上传"""
    try:
        logger.info(f"收到文件上传: {file.filename}")
        result = await file_service.save_uploaded_file(file, category)
        return FileUploadResponse(**result, success=True, message=f"上传成功: {result['filename']}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(500, str(e))

@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_batch(files: List[UploadFile] = File(...), category: str = "general"):
    """批量上传"""
    try:
        logger.info(f"批量上传: {len(files)}个文件")
        results = await file_service.save_multiple_files(files, category)
        success_count = sum(1 for r in results if r.get('success'))
        return BatchUploadResponse(
            total=len(results),
            success_count=success_count,
            failed_count=len(results) - success_count,
            results=[FileUploadResponse(**r) for r in results if 'filepath' in r]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量上传失败: {e}")
        raise HTTPException(500, str(e))

@router.get("/files", response_model=FileListResponse)
async def list_files(category: str = None):
    """文件列表"""
    try:
        files = file_service.list_uploaded_files(category)
        return FileListResponse(
            files=[FileInfo(**f) for f in files],
            total=len(files)
        )
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(500, str(e))

@router.delete("/files/{filename}", response_model=DeleteDocumentsResponse)
async def delete_file(filename: str, category: str = "general"):
    """删除文件"""
    try:
        success = file_service.delete_file(filename, category)
        return DeleteDocumentsResponse(
            success=success,
            message=f"删除成功: {filename}" if success else f"文件不存在: {filename}"
        )
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(500, str(e))
