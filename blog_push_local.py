import os
import shutil
import re
import subprocess
import time
import glob
import logging
import argparse
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blog_push_local.log'),
        logging.StreamHandler(sys.stdout)  # 同时输出到控制台
    ]
)
logger = logging.getLogger(__name__)

def log_progress(message):
    """记录进度"""
    logger.info(message)
    print(f"● {message}")  # 在控制台直接显示带标记的消息

def publish_to_blog(article_name: str, target_dir: str = r"I:\B-MioBlogSites\_Android") -> str:
    """将指定文章发布到博客站点
    
    Args:
        article_name: 文章名称(不含.md后缀)
        target_dir: 目标目录
    """
    # 定义路径
    vault_path = r"I:\B-1 笔记\Android\Android"  # Obsidian 本地目录
    attachments_path = os.path.join(vault_path, "z. attachments")  # 图片源目录
    images_target_dir = r"I:\B-MioBlogSites\assets\images"  # 图片目标目录
    
    log_progress(f"开始处理文章: {article_name}")

    if "B-1 笔记" in article_name:
        source_file = article_name
        article_filename = os.path.basename(source_file)
        print(article_filename)
    else:
        log_progress(f"在 {vault_path} 中搜索文章...")

        # 在vault_path下所有子目录中查找文章
        article_filename = f"{article_name}.md"
        source_file = None

        # 搜索所有子目录
        for root, dirs, files in os.walk(vault_path):
            if article_filename in files:
                source_file = os.path.join(root, article_filename)
                break

        # 检查源文件是否存在
        if not source_file:
            error_msg = f"错误：无法在 {vault_path} 及其子目录中找到文章 {article_filename}"
            log_progress(error_msg)
            return error_msg

        log_progress(f"找到文章: {source_file}")
    
    # 源文件所在目录
    source_dir = os.path.dirname(source_file)
    
    # 创建目标目录（如果不存在）
    target_file = os.path.join(target_dir, article_filename)
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(images_target_dir, exist_ok=True)
    
    # 复制 Markdown 文件
    log_progress(f"复制文件到: {target_file}")
    shutil.copy(source_file, target_file)
    
    # 读取 Markdown 内容并处理图片链接
    log_progress("处理文章中的图片...")
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则表达式查找标准Markdown和Obsidian格式的图片链接
    std_image_pattern = r'!\[.*?\]\((.*?)\)'  # 匹配 ![alt](image_path)
    obsidian_image_pattern = r'!\[\[(.*?)\]\]'  # 匹配 ![[image_path]]
    
    std_images = re.findall(std_image_pattern, content)
    obsidian_images = re.findall(obsidian_image_pattern, content)
    
    # 合并两种格式的图片列表
    images = std_images + obsidian_images
    
    if images:
        log_progress(f"找到 {len(images)} 张图片需要处理")
    else:
        log_progress("文章中没有找到图片链接")
    
    image_count = 0
    for image_path in images:
        # 图片文件全路径 - 只在附件目录中查找
        image_source = os.path.join(attachments_path, image_path)
        
        if not os.path.exists(image_source):
            error_msg = f"错误：无法在附件目录中找到图片 {image_path}"
            log_progress(error_msg)
            return error_msg
        
        # 计算图片文件名和目标路径
        image_name = os.path.basename(image_path)
        image_target = os.path.join(images_target_dir, image_name)
        
        # 复制图片
        image_count += 1
        log_progress(f"复制图片 {image_count}/{len(images)}: {image_name}")
        shutil.copy(image_source, image_target)
        
        # 不再处理图片链接，交给auto_update.py处理
    
    # 将读取的内容原样写回，不修改图片链接
    log_progress("图片复制完成，图片链接将由auto_update.py处理")
    
    # 执行auto_update.py脚本
    auto_update_script = r"I:\B-MioBlogSites\auto_update.py"
    log_progress(f"执行auto_update.py脚本...")
    
    try:
        # 切换到目标目录以确保脚本在正确的环境中运行
        git_repo_dir = r"I:\B-MioBlogSites"
        os.chdir(git_repo_dir)
        
        # 使用Python解释器执行脚本，确保使用虚拟环境中的Python
        venv_python = os.path.join(git_repo_dir, ".venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            # 使用虚拟环境中的Python
            log_progress(f"使用虚拟环境Python执行脚本")
            result = subprocess.run([venv_python, auto_update_script], 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
        else:
            # 使用系统Python
            log_progress(f"使用系统Python执行脚本")
            result = subprocess.run(["python", auto_update_script], 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
        
        # 记录脚本输出
        if result.stdout:
            for line in result.stdout.splitlines():
                if line.strip():
                    log_progress(f"脚本输出: {line.strip()}")
        
        log_progress("auto_update.py脚本执行完成")
        
    except subprocess.CalledProcessError as e:
        error_msg = f"执行auto_update.py脚本失败: {str(e)}"
        log_progress(error_msg)
        if e.stdout:
            log_progress(f"脚本输出: {e.stdout}")
        if e.stderr:
            log_progress(f"脚本错误: {e.stderr}")
        return error_msg
    except Exception as e:
        error_msg = f"执行脚本时发生未预期错误: {str(e)}"
        log_progress(error_msg)
        return error_msg
    
    # 执行 Git 命令
    git_repo_dir = r"I:\B-MioBlogSites"
    try:
        log_progress(f"开始Git操作: 切换到仓库目录 {git_repo_dir}")
        os.chdir(git_repo_dir)
        
        log_progress("执行: git add .")
        subprocess.run(["git", "add", "."], check=True)
        
        log_progress(f"执行: git commit -m \"Add article: {article_name}\"")
        subprocess.run(["git", "commit", "-m", f"Add article: {article_name}"], check=True)
        
        log_progress("执行: git push")
        subprocess.run(["git", "push"], check=True)
        
        log_progress("Git操作完成")
    except subprocess.CalledProcessError as e:
        error_msg = f"Git操作失败: {str(e)}"
        log_progress(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"发生未预期错误: {str(e)}"
        log_progress(error_msg)
        return error_msg
    
    source_location = os.path.relpath(source_file, vault_path)
    log_progress(f"全部操作完成!")
    
    success_msg = f"成功将文章 {article_name} (来自 {source_location}) 发布到博客并推送到 GitHub"
    log_progress(success_msg)
    return success_msg

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='将Obsidian文章发布到博客站点')
    parser.add_argument('article_name', help='文章名称(不含.md后缀)')
    parser.add_argument('--dir', default='_Android', help='目标目录名称(默认为_Android)')
    
    args = parser.parse_args()
    
    # 确保目标目录格式正确
    target_dir = args.dir
    if not target_dir.startswith("_"):
        target_dir = f"_{target_dir}"
    
    full_target_dir = os.path.join(r"I:\B-MioBlogSites", target_dir)
    
    # 调用发布函数
    result = publish_to_blog(args.article_name, full_target_dir)
    print("\n" + result)

if __name__ == "__main__":
    main()