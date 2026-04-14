"""
知识库更新服务模块
提供增量更新、全量更新、版本替换与回滚等功能
"""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from database.connection import get_db_session
from database.models import KnowledgeBaseFile, KnowledgeBaseIngestJob
from rag.document_loader import MedicalDocumentLoader
from rag.file_upload_service import FileUploadService
from rag.text_splitter import MedicalTextSplitter


class KnowledgeBaseUpdateService:
    """知识库更新服务"""

    def __init__(self, rag_chain):
        """
        初始化更新服务

        Args:
            rag_chain: RAG链实例
        """
        self.rag_chain = rag_chain
        upload_dir = "data/medical_docs"
        if getattr(self.rag_chain, "document_loader", None) is not None:
            upload_dir = str(self.rag_chain.document_loader.data_dir)
        self.file_identity = FileUploadService(upload_dir=upload_dir)
        logger.info("知识库更新服务初始化完成")

    @staticmethod
    def _build_loader(data_dir: Optional[str], enable_md5_check: bool) -> MedicalDocumentLoader:
        """创建文档加载器，并在传入目录时覆盖默认目录。"""
        loader = MedicalDocumentLoader(enable_md5_check=enable_md5_check)
        if data_dir:
            loader.data_dir = Path(data_dir)
        return loader

    @staticmethod
    def _build_result_message(
        ingested_count: int,
        skip_count: int,
        failed_count: int,
        failed_files: List[str],
    ) -> str:
        """拼接更新结果提示，明确区分文档块、跳过文件和失败文件。"""
        message = f"成功导入 {ingested_count} 个文档块，跳过 {skip_count} 个已存在文件"
        if failed_count:
            preview = "、".join(failed_files[:3])
            suffix = f"，另有 {failed_count} 个文件加载失败"
            if preview:
                suffix += f"（{preview}）"
            message += suffix
        return message

    @staticmethod
    def _parse_vector_ids(raw_value: Optional[str]) -> List[str]:
        """解析存储的向量ID列表。"""
        if not raw_value:
            return []

        try:
            return json.loads(raw_value)
        except Exception:
            return []

    def _resolve_category(self, source_path: str, category: str) -> str:
        """优先保留来源路径中的分类，其次使用请求分类。"""
        source = Path(source_path)
        data_dir = Path(getattr(getattr(self.rag_chain, "document_loader", None), "data_dir", "data/medical_docs"))
        try:
            parent = source.parent.resolve()
            root = data_dir.resolve()
            if parent != root:
                relative_parent = parent.relative_to(root)
                if relative_parent.parts:
                    return relative_parent.parts[0]
        except Exception:
            pass
        return category or "general"

    def _create_job(
        self,
        job_type: str,
        source_id: Optional[str] = None,
        file_id: Optional[int] = None,
        file_hash: Optional[str] = None,
        version: Optional[int] = None,
    ) -> int:
        """创建导入任务日志。"""
        with get_db_session() as db:
            job = KnowledgeBaseIngestJob(
                job_type=job_type,
                status="running",
                source_id=source_id,
                file_id=file_id,
                file_hash=file_hash,
                version=version,
            )
            db.add(job)
            db.flush()
            return job.id

    def _finish_job(
        self,
        job_id: int,
        status: str,
        message: str,
        chunk_count: int = 0,
        file_id: Optional[int] = None,
        version: Optional[int] = None,
    ) -> None:
        """结束任务日志。"""
        with get_db_session() as db:
            job = db.query(KnowledgeBaseIngestJob).filter(KnowledgeBaseIngestJob.id == job_id).first()
            if not job:
                return
            job.status = status
            job.message = message
            job.chunk_count = chunk_count
            if file_id is not None:
                job.file_id = file_id
            if version is not None:
                job.version = version
            job.finished_at = datetime.utcnow()

    def _prepare_file_record(self, file_path: Path, category: str) -> Dict[str, object]:
        """
        为单个源文件创建待入库版本记录。

        Returns:
            包含记录信息的字典；若内容未变化则返回 skip=True。
        """
        identity = self.file_identity.build_file_identity(file_path=file_path, category=category, original_filename=file_path.name)

        with get_db_session() as db:
            current = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.source_id == identity["source_id"]) \
                .filter(KnowledgeBaseFile.is_current.is_(True)) \
                .order_by(KnowledgeBaseFile.version.desc()) \
                .first()

            if current and current.file_hash == identity["file_hash"] and current.status == "active":
                return {
                    "skip": True,
                    "message": f"文件内容未变化，跳过版本更新: {file_path.name}",
                    "source_id": identity["source_id"],
                }

            record = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.filepath == str(file_path)) \
                .filter(KnowledgeBaseFile.file_hash == identity["file_hash"]) \
                .filter(KnowledgeBaseFile.source_id == identity["source_id"]) \
                .filter(KnowledgeBaseFile.status.in_(["uploaded", "failed", "processing"])) \
                .order_by(KnowledgeBaseFile.updated_at.desc()) \
                .first()

            latest = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.source_id == identity["source_id"]) \
                .order_by(KnowledgeBaseFile.version.desc()) \
                .first()
            if record and latest and latest.id == record.id:
                version = record.version or 1
            else:
                version = (latest.version + 1) if latest else 1

            if record:
                record.filename = file_path.name
                record.logical_name = identity["logical_name"]
                record.category = category
                record.source_type = identity["source_type"]
                record.version = max(record.version or 1, version)
                record.status = "processing"
                record.is_current = False
            else:
                record = KnowledgeBaseFile(
                    source_id=identity["source_id"],
                    filename=file_path.name,
                    filepath=str(file_path),
                    logical_name=identity["logical_name"],
                    category=category,
                    source_type=identity["source_type"],
                    file_hash=identity["file_hash"],
                    version=version,
                    status="processing",
                    is_current=False,
                )
                db.add(record)
            db.flush()

            return {
                "skip": False,
                "record_id": record.id,
                "source_id": identity["source_id"],
                "logical_name": identity["logical_name"],
                "file_hash": identity["file_hash"],
                "version": version,
                "category": category,
                "source_type": identity["source_type"],
                "filepath": str(file_path),
            }

    def _mark_record_failed(self, record_id: Optional[int], error_message: str) -> None:
        """标记单个文件版本入库失败。"""
        if not record_id:
            return

        with get_db_session() as db:
            record = db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == record_id).first()
            if not record:
                return
            record.status = "failed"
            record.is_current = False
            record.error_message = error_message

    def _activate_file_record(self, record_id: int, doc_ids: List[str]) -> None:
        """激活新版本，并让旧版本失效。"""
        record_filepath = None
        with get_db_session() as db:
            record = db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == record_id).first()
            if not record:
                return

            record_filepath = record.filepath

            previous_versions = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.source_id == record.source_id) \
                .filter(KnowledgeBaseFile.id != record.id) \
                .filter(KnowledgeBaseFile.is_current.is_(True)) \
                .all()

            for previous in previous_versions:
                previous_ids = self._parse_vector_ids(previous.vector_ids)
                if previous_ids:
                    self.rag_chain.vector_store.delete_documents(previous_ids)
                else:
                    self.rag_chain.vector_store.delete_by_metadata({"file_record_id": previous.id})

                previous.is_current = False
                previous.status = "superseded"

            record.status = "active"
            record.is_current = True
            record.chunk_count = len(doc_ids)
            record.vector_ids = json.dumps(doc_ids, ensure_ascii=False)
            record.ingested_at = datetime.utcnow()
            record.error_message = None

        if record_filepath and self.rag_chain.document_loader.md5_checker and not self.rag_chain.document_loader.md5_checker.check_file_exists(record_filepath):
            self.rag_chain.document_loader.md5_checker.add_file_record(record_filepath)

    def _find_latest_restorable_version(self, source_id: str) -> Optional[int]:
        """找到某个逻辑文件当前可恢复的最新版本。"""
        with get_db_session() as db:
            current = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.source_id == source_id) \
                .filter(KnowledgeBaseFile.is_current.is_(True)) \
                .filter(KnowledgeBaseFile.status == "active") \
                .first()
            if current:
                return None

            candidate = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.source_id == source_id) \
                .filter(KnowledgeBaseFile.status != "deleted") \
                .order_by(KnowledgeBaseFile.version.desc()) \
                .first()
            if not candidate:
                return None
            return candidate.version

    def _ingest_documents_by_file(
        self,
        loader: MedicalDocumentLoader,
        documents: List,
        category: str,
        job_type: str,
    ) -> Dict[str, object]:
        """按源文件分组执行版本化入库。"""
        grouped_docs = defaultdict(list)
        for doc in documents:
            grouped_docs[str(doc.metadata.get("source"))].append(doc)

        total_doc_ids: List[str] = []
        lifecycle_skip_count = 0
        failed_files: List[str] = []
        ingested_files = 0

        splitter = MedicalTextSplitter()

        for source_path, source_docs in grouped_docs.items():
            effective_category = self._resolve_category(source_path, category)
            file_record = None
            job_id = None

            try:
                file_record = self._prepare_file_record(Path(source_path), effective_category)
                job_id = self._create_job(
                    job_type=job_type,
                    source_id=file_record.get("source_id"),
                    file_hash=file_record.get("file_hash"),
                    version=file_record.get("version"),
                    file_id=file_record.get("record_id"),
                )

                if file_record.get("skip"):
                    lifecycle_skip_count += 1
                    self._finish_job(job_id, "success", file_record["message"])
                    continue

                metadata_map = {
                    source_path: {
                        "source_id": file_record["source_id"],
                        "file_hash": file_record["file_hash"],
                        "version": file_record["version"],
                        "file_record_id": file_record["record_id"],
                        "status": "active",
                        "category": effective_category,
                        "source_type": file_record["source_type"],
                    }
                }
                enriched_docs = loader.add_metadata(source_docs, effective_category, metadata_map)
                split_docs = splitter.split_documents(enriched_docs)
                doc_ids = self.rag_chain.vector_store.add_documents(split_docs)
                self._activate_file_record(file_record["record_id"], doc_ids)
                self._finish_job(
                    job_id,
                    "success",
                    f"成功导入 {len(doc_ids)} 个文档块",
                    chunk_count=len(doc_ids),
                    file_id=file_record["record_id"],
                    version=file_record["version"],
                )
                total_doc_ids.extend(doc_ids)
                ingested_files += 1
            except Exception as e:
                failed_files.append(Path(source_path).name)
                self._mark_record_failed(file_record.get("record_id") if file_record else None, str(e))
                if job_id:
                    self._finish_job(job_id, "failed", str(e), file_id=file_record.get("record_id") if file_record else None)
                logger.error(f"版本化导入失败 {source_path}: {e}")

        return {
            "doc_ids": total_doc_ids,
            "failed_files": failed_files,
            "failed_count": len(failed_files),
            "lifecycle_skip_count": lifecycle_skip_count,
            "ingested_file_count": ingested_files,
        }

    def incremental_update(self, data_dir: Optional[str] = None, category: str = "general") -> Dict:
        """
        增量更新：仅导入新增文件

        Args:
            data_dir: 文档目录
            category: 文档分类

        Returns:
            更新结果统计
        """
        try:
            logger.info(f"开始增量更新知识库，目录: {data_dir or 'default'}")
            loader = self._build_loader(data_dir, enable_md5_check=True)
            documents, success_count, skip_count = loader.load_directory()
            load_summary = loader.last_load_summary
            failed_count = load_summary.get("failed_count", 0)
            failed_files = list(load_summary.get("failed_files", []))

            if not documents:
                if failed_count:
                    message = self._build_result_message(0, skip_count, failed_count, failed_files)
                    logger.warning(f"增量更新未导入新文档: {message}")
                    return {
                        "success": False,
                        "ingested_count": 0,
                        "skipped_count": skip_count,
                        "message": message
                    }

                logger.info("没有新文件需要导入")
                return {
                    "success": True,
                    "ingested_count": 0,
                    "skipped_count": skip_count,
                    "message": "没有新文件需要导入"
                }

            process_result = self._ingest_documents_by_file(loader, documents, category, "incremental")
            failed_files.extend(process_result["failed_files"])
            combined_failed_count = len(failed_files)
            combined_skip_count = skip_count + process_result["lifecycle_skip_count"]
            ingested_count = len(process_result["doc_ids"])

            result = {
                "success": ingested_count > 0 or combined_failed_count == 0,
                "ingested_count": ingested_count,
                "skipped_count": combined_skip_count,
                "file_count": process_result["ingested_file_count"],
                "message": self._build_result_message(
                    ingested_count,
                    combined_skip_count,
                    combined_failed_count,
                    failed_files
                )
            }

            logger.info(f"增量更新完成: {result}")
            return result
        except Exception as e:
            logger.error(f"增量更新失败: {e}")
            return {
                "success": False,
                "ingested_count": 0,
                "skipped_count": 0,
                "message": f"更新失败: {str(e)}"
            }

    def full_update(self, data_dir: Optional[str] = None, category: str = "general", clear_first: bool = False) -> Dict:
        """
        全量更新：重新导入所有文件

        Args:
            data_dir: 文档目录
            category: 文档分类
            clear_first: 是否先清空现有数据

        Returns:
            更新结果统计
        """
        try:
            logger.info(f"开始全量更新知识库，目录: {data_dir or 'default'}")

            if clear_first:
                logger.info("清空现有知识库数据")
                self.delete_by_rule(category=category if category != "general" else None)

            loader = self._build_loader(data_dir, enable_md5_check=False)
            documents, _, _ = loader.load_directory()
            load_summary = loader.last_load_summary
            failed_files = list(load_summary.get("failed_files", []))
            failed_count = load_summary.get("failed_count", 0)

            if not documents:
                if failed_count:
                    preview = "、".join(failed_files[:3])
                    message = f"没有找到可导入的文档，且有 {failed_count} 个文件加载失败"
                    if preview:
                        message += f"（{preview}）"
                    logger.warning(message)
                    return {
                        "success": False,
                        "ingested_count": 0,
                        "message": message
                    }

                logger.warning("没有找到可导入的文档")
                return {
                    "success": True,
                    "ingested_count": 0,
                    "message": "没有找到可导入的文档"
                }

            process_result = self._ingest_documents_by_file(loader, documents, category, "full")
            failed_files.extend(process_result["failed_files"])

            result = {
                "success": len(process_result["doc_ids"]) > 0 or len(failed_files) == 0,
                "ingested_count": len(process_result["doc_ids"]),
                "message": self._build_result_message(
                    len(process_result["doc_ids"]),
                    process_result["lifecycle_skip_count"],
                    len(failed_files),
                    failed_files
                )
            }

            logger.info(f"全量更新完成: {result}")
            return result
        except Exception as e:
            logger.error(f"全量更新失败: {e}")
            return {
                "success": False,
                "ingested_count": 0,
                "message": f"更新失败: {str(e)}"
            }

    def update_single_file(self, filepath: str, category: str = "general", force: bool = False) -> Dict:
        """
        更新单个文件

        Args:
            filepath: 文件路径
            category: 文档分类
            force: 是否强制更新（忽略MD5检查）

        Returns:
            更新结果
        """
        try:
            logger.info(f"更新单个文件: {filepath}, force: {force}")
            loader = MedicalDocumentLoader(enable_md5_check=not force)
            documents, is_new = loader.load_single_file(filepath)

            if not documents:
                return {
                    "success": False,
                    "ingested_count": 0,
                    "message": "文件加载失败或文件已存在（使用force=True强制更新）"
                }

            process_result = self._ingest_documents_by_file(loader, documents, category, "single")
            if process_result["failed_count"]:
                return {
                    "success": False,
                    "ingested_count": len(process_result["doc_ids"]),
                    "is_new": is_new,
                    "message": f"更新失败: {'、'.join(process_result['failed_files'])}"
                }

            result = {
                "success": True,
                "ingested_count": len(process_result["doc_ids"]),
                "is_new": is_new,
                "message": f"成功导入 {len(process_result['doc_ids'])} 个文档块"
            }

            logger.info(f"单文件更新完成: {result}")
            return result
        except Exception as e:
            logger.error(f"单文件更新失败: {e}")
            return {
                "success": False,
                "ingested_count": 0,
                "message": f"更新失败: {str(e)}"
            }

    def delete_by_rule(
        self,
        source_id: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Dict[str, object]:
        """按 source_id / 分类 / 文件名 / 版本 删除知识库文件及向量。"""
        try:
            deleted_records = 0
            deleted_chunks = 0
            affected_source_ids = set()
            restored_versions = 0

            with get_db_session() as db:
                query = db.query(KnowledgeBaseFile)
                if source_id:
                    query = query.filter(KnowledgeBaseFile.source_id == source_id)
                if category:
                    query = query.filter(KnowledgeBaseFile.category == category)
                if source:
                    query = query.filter(KnowledgeBaseFile.filename == source)
                if version is not None:
                    query = query.filter(KnowledgeBaseFile.version == version)

                records = query.all()
                if not records:
                    return {"success": True, "deleted_records": 0, "deleted_chunks": 0, "message": "未找到符合条件的记录"}

                for record in records:
                    affected_source_ids.add(record.source_id)
                    vector_ids = self._parse_vector_ids(record.vector_ids)
                    if vector_ids:
                        self.rag_chain.vector_store.delete_documents(vector_ids)
                        deleted_chunks += len(vector_ids)
                    else:
                        self.rag_chain.vector_store.delete_by_metadata({"file_record_id": record.id})
                    record.status = "deleted"
                    record.is_current = False
                    record.error_message = None
                    deleted_records += 1

            for affected_source_id in affected_source_ids:
                target_version = self._find_latest_restorable_version(affected_source_id)
                if target_version is None:
                    continue

                restore_result = self.rollback_file(affected_source_id, target_version)
                if restore_result.get("success"):
                    restored_versions += 1
                else:
                    logger.warning(
                        "删除后恢复最新可用版本失败: source_id={}, target_version={}, message={}",
                        affected_source_id,
                        target_version,
                        restore_result.get("message"),
                    )

            return {
                "success": True,
                "deleted_records": deleted_records,
                "deleted_chunks": deleted_chunks,
                "message": (
                    f"删除 {deleted_records} 条文件记录，移除 {deleted_chunks} 个文档块"
                    + (f"，并恢复 {restored_versions} 个逻辑文件的最新可用版本" if restored_versions else "")
                )
            }
        except Exception as e:
            logger.error(f"按规则删除知识库失败: {e}")
            return {
                "success": False,
                "deleted_records": 0,
                "deleted_chunks": 0,
                "message": f"删除失败: {str(e)}"
            }

    def rollback_file(self, source_id: str, target_version: int) -> Dict[str, object]:
        """回滚到指定文件版本。"""
        try:
            with get_db_session() as db:
                target = db.query(KnowledgeBaseFile) \
                    .filter(KnowledgeBaseFile.source_id == source_id) \
                    .filter(KnowledgeBaseFile.version == target_version) \
                    .first()
                current = db.query(KnowledgeBaseFile) \
                    .filter(KnowledgeBaseFile.source_id == source_id) \
                    .filter(KnowledgeBaseFile.is_current.is_(True)) \
                    .first()

            if not target:
                return {"success": False, "message": f"未找到 source_id={source_id} version={target_version} 的记录"}

            file_path = Path(target.filepath)
            if not file_path.exists():
                return {"success": False, "message": f"回滚失败，目标版本文件不存在: {file_path}"}

            loader = MedicalDocumentLoader(enable_md5_check=False)
            documents, _ = loader.load_single_file(str(file_path))
            if not documents:
                return {"success": False, "message": "回滚失败，目标版本文件无法加载"}

            metadata_map = {
                str(file_path): {
                    "source_id": target.source_id,
                    "file_hash": target.file_hash,
                    "version": target.version,
                    "file_record_id": target.id,
                    "status": "active",
                    "category": target.category,
                    "source_type": target.source_type,
                }
            }
            enriched_docs = loader.add_metadata(documents, target.category, metadata_map)
            split_docs = MedicalTextSplitter().split_documents(enriched_docs)
            doc_ids = self.rag_chain.vector_store.add_documents(split_docs)

            with get_db_session() as db:
                current_record = db.query(KnowledgeBaseFile) \
                    .filter(KnowledgeBaseFile.source_id == source_id) \
                    .filter(KnowledgeBaseFile.is_current.is_(True)) \
                    .first()

                if current_record and current_record.id != target.id:
                    current_ids = self._parse_vector_ids(current_record.vector_ids)
                    if current_ids:
                        self.rag_chain.vector_store.delete_documents(current_ids)
                    current_record.is_current = False
                    current_record.status = "superseded"

                target_record = db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == target.id).first()
                target_record.is_current = True
                target_record.status = "active"
                target_record.chunk_count = len(doc_ids)
                target_record.vector_ids = json.dumps(doc_ids, ensure_ascii=False)
                target_record.ingested_at = datetime.utcnow()
                target_record.error_message = None

            job_id = self._create_job(
                job_type="rollback",
                source_id=target.source_id,
                file_id=target.id,
                file_hash=target.file_hash,
                version=target.version,
            )
            self._finish_job(job_id, "success", f"成功回滚到版本 {target.version}", chunk_count=len(doc_ids), file_id=target.id, version=target.version)

            return {
                "success": True,
                "message": f"成功回滚到版本 {target.version}",
                "source_id": source_id,
                "version": target.version,
                "ingested_count": len(doc_ids),
            }
        except Exception as e:
            logger.error(f"回滚文件失败: {e}")
            return {"success": False, "message": f"回滚失败: {str(e)}"}

    def list_versions(self, source_id: str) -> List[Dict[str, object]]:
        """列出某个逻辑文件的全部版本历史。"""
        with get_db_session() as db:
            rows = db.query(KnowledgeBaseFile) \
                .filter(KnowledgeBaseFile.source_id == source_id) \
                .order_by(KnowledgeBaseFile.version.desc(), KnowledgeBaseFile.updated_at.desc()) \
                .all()

            return [
                {
                    "id": row.id,
                    "source_id": row.source_id,
                    "filename": row.filename,
                    "filepath": row.filepath,
                    "logical_name": row.logical_name,
                    "category": row.category,
                    "source_type": row.source_type,
                    "file_hash": row.file_hash,
                    "version": row.version,
                    "status": row.status,
                    "is_current": row.is_current,
                    "chunk_count": row.chunk_count,
                    "error_message": row.error_message,
                    "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
                    "ingested_at": row.ingested_at.isoformat() if row.ingested_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]

    def list_ingest_jobs(self, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, object]]:
        """列出知识库导入任务日志。"""
        with get_db_session() as db:
            query = db.query(KnowledgeBaseIngestJob)
            if status:
                query = query.filter(KnowledgeBaseIngestJob.status == status)

            rows = query.order_by(
                KnowledgeBaseIngestJob.started_at.desc(),
                KnowledgeBaseIngestJob.id.desc(),
            ).limit(limit).all()

            return [
                {
                    "id": row.id,
                    "job_type": row.job_type,
                    "status": row.status,
                    "source_id": row.source_id,
                    "file_id": row.file_id,
                    "file_hash": row.file_hash,
                    "version": row.version,
                    "chunk_count": row.chunk_count,
                    "message": row.message,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                }
                for row in rows
            ]
