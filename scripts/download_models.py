#!/usr/bin/env python3
"""
模型下载脚本
用于提前下载嵌入模型到本地，避免运行时网络连接问题
"""

import os
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_embedding_model(model_name: str, local_path: str = None):
    """
    下载嵌入模型到本地
    
    Args:
        model_name: 模型名称，如 'all-MiniLM-L6-v2'
        local_path: 本地存储路径，如果为None则使用默认缓存路径
    """
    try:
        logger.info(f"开始下载嵌入模型: {model_name}")
        
        # 如果指定了本地路径，设置缓存目录
        if local_path:
            os.environ['SENTENCE_TRANSFORMERS_HOME'] = local_path
            logger.info(f"设置模型缓存目录: {local_path}")
        
        # 下载模型
        model = SentenceTransformer(model_name)
        
        # 获取实际存储路径
        cache_dir = model._modules['0'].auto_model.config._name_or_path
        logger.info(f"模型下载完成，存储路径: {cache_dir}")
        
        # 测试模型
        test_text = "这是一个测试文本"
        embedding = model.encode(test_text)
        logger.info(f"模型测试成功，嵌入维度: {embedding.shape}")
        
        return True
        
    except Exception as e:
        logger.error(f"下载模型失败: {e}")
        return False

def download_all_models():
    """
    下载项目所需的所有模型
    """
    # 创建本地模型目录
    models_dir = project_root / "models" / "embeddings"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"模型存储目录: {models_dir}")
    
    # 读取配置中的模型
    settings = get_settings()
    current_model = settings.embedding_model
    
    # 要下载的模型列表
    models_to_download = [
        current_model,  # 当前配置的模型
        "all-MiniLM-L6-v2",  # 备用模型
        "paraphrase-multilingual-MiniLM-L12-v2",  # 多语言模型
    ]
    
    # 去重
    models_to_download = list(set(models_to_download))
    
    success_count = 0
    for model_name in models_to_download:
        logger.info(f"\n{'='*50}")
        logger.info(f"下载模型: {model_name}")
        logger.info(f"{'='*50}")
        
        if download_embedding_model(model_name, str(models_dir)):
            success_count += 1
            logger.info(f"✅ {model_name} 下载成功")
        else:
            logger.error(f"❌ {model_name} 下载失败")
    
    logger.info(f"\n下载完成: {success_count}/{len(models_to_download)} 个模型下载成功")
    
    if success_count > 0:
        logger.info(f"\n模型存储位置: {models_dir}")
        logger.info("请更新配置文件以使用本地模型路径")
    
    return success_count == len(models_to_download)

def show_cache_info():
    """
    显示当前模型缓存信息
    """
    import sentence_transformers
    
    # 默认缓存目录
    default_cache = sentence_transformers.util.get_cache_folder()
    logger.info(f"默认缓存目录: {default_cache}")
    
    # 检查环境变量
    custom_cache = os.environ.get('SENTENCE_TRANSFORMERS_HOME')
    if custom_cache:
        logger.info(f"自定义缓存目录: {custom_cache}")
    
    # 列出已缓存的模型
    cache_path = Path(custom_cache if custom_cache else default_cache)
    if cache_path.exists():
        models = [d.name for d in cache_path.iterdir() if d.is_dir()]
        if models:
            logger.info(f"已缓存的模型: {models}")
        else:
            logger.info("暂无缓存的模型")
    else:
        logger.info("缓存目录不存在")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="下载嵌入模型到本地")
    parser.add_argument("--model", "-m", help="指定要下载的模型名称")
    parser.add_argument("--path", "-p", help="指定本地存储路径")
    parser.add_argument("--all", "-a", action="store_true", help="下载所有项目需要的模型")
    parser.add_argument("--info", "-i", action="store_true", help="显示缓存信息")
    
    args = parser.parse_args()
    
    if args.info:
        show_cache_info()
    elif args.all:
        download_all_models()
    elif args.model:
        download_embedding_model(args.model, args.path)
    else:
        print("使用示例:")
        print("  python download_models.py --all                    # 下载所有模型")
        print("  python download_models.py --model all-MiniLM-L6-v2 # 下载指定模型")
        print("  python download_models.py --info                   # 显示缓存信息")
        parser.print_help()