#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目初始化脚本
安装依赖并初始化环境
"""
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """执行命令"""
    print(f"\n{'='*60}")
    print(f"正在{description}...")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(f"✓ {description}成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description}失败")
        print(f"错误信息: {e.stderr}")
        return False


def main():
    """主函数"""
    print("医疗RAG项目初始化")
    print("=" * 60)
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major != 3 or python_version.minor < 11:
        print(f"✗ Python版本不满足要求，需要Python 3.11+，当前版本: {python_version.major}.{python_version.minor}")
        sys.exit(1)
    
    print(f"✓ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 创建必要目录
    print("\n创建必要目录...")
    directories = ["logs", "data/medical_docs"]
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {dir_path}")
    
    # 安装依赖
    confirm = input("\n是否安装依赖包？(y/n): ")
    if confirm.lower() == 'y':
        success = run_command(
            "pip install -r requirements.txt",
            "安装依赖包"
        )
        if not success:
            print("\n请手动运行: pip install -r requirements.txt")
            sys.exit(1)
    
    # 检查Ollama
    print("\n" + "=" * 60)
    print("请确保以下服务已启动:")
    print("=" * 60)
    print("1. Ollama服务 (http://localhost:11434)")
    print("   - 下载: https://ollama.com")
    print("   - 启动: ollama serve")
    print("   - 拉取模型: ollama pull bge-m3:latest")
    print("   - 拉取模型: ollama pull qwen2.5:7b")
    print("\n2. PostgreSQL数据库")
    print("   - 确保pgvector扩展已安装")
    print("   - 创建数据库: medical_rag_db")
    
    # 复制.env文件
    env_file = Path(".env")
    env_example = Path(".env.example")
    if not env_file.exists() and env_example.exists():
        print("\n是否从.env.example创建.env配置文件？")
        confirm = input("(y/n): ")
        if confirm.lower() == 'y':
            import shutil
            shutil.copy(".env.example", ".env")
            print("✓ 已创建.env文件，请根据实际情况修改配置")
    
    print("\n" + "=" * 60)
    print("初始化完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 检查并修改 .env 配置文件（至少需要 DATABASE_URL）")
    print("2. 确保Ollama和PostgreSQL服务已启动")
    print("3. 运行: python main.py")
    print("4. 访问API文档: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
