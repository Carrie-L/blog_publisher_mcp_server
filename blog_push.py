from mcp.server import FastMCP
import os
import shutil
import re
import subprocess
import time
import glob
import logging

# 初始化 MCP 服务器
mcp = FastMCP("blog_publisher", timeout=300)

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='blog_push.log')

# 添加博客发布工具 --dir 指定目标目录
@mcp.tool(name="blog")
async def blog_command(article_name: str, dir: str = "_Android") -> str:
    """博客发布工具

    Args:
        article_name: 要发布的文章名称
        dir: 目标目录，默认为_Android
    """
    if not article_name:
        return "错误：请提供文章名称，例如：blog MCP QuickStart Guide"

    # 确保目标目录路径格式正确
    if not dir.startswith("_"):
        dir = f"_{dir}"

    full_target_dir = os.path.join(r"I:\B-MioBlogSites", dir)

    # 确保目标目录路径格式正确
    if not dir.startswith("_"):
        dir = f"_{dir}"

    full_target_dir = os.path.join(r"I:\B-MioBlogSites", dir)

    return await publish_to_blog(article_name, full_target_dir)


@mcp.tool()
async def publish_to_blog(article_name: str, target_dir: str = r"I:\B-MioBlogSites\_Android") -> str:
    # 用于收集进度信息的列表
    progress_log = []

    # 添加进度信息的辅助函数
    def log_progress(message):
        progress_log.append(f"● {message}")
        print(message)  # 同时在控制台打印，方便调试

    log_progress(f"开始处理文章: {article_name}")

    # 定义路径
    vault_path = r"I:\B-1 笔记\Android\Android"  # Obsidian 本地目录
    attachments_path = os.path.join(vault_path, "z. attachments")  # 图片源目录
    images_target_dir = r"I:\B-MioBlogSites\assets\blogimages"  # 图片目标目录

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
            log_progress(f"错误：无法找到文章 {article_filename}")
            return "\n".join(progress_log) + f"\n❌ 无法在 {vault_path} 及其子目录中找到文章 {article_filename}"

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
    log_progress("处理文章中的图片链接...")
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
            log_progress(f"错误：无法在附件目录中找到图片 {image_path}")
            return "\n".join(progress_log) + f"\n❌ 无法在附件目录中找到图片 {image_path}"

        # 计算图片文件名和目标路径
        image_name = os.path.basename(image_path)
        image_target = os.path.join(images_target_dir, image_name)

        # 复制图片
        image_count += 1
        log_progress(f"复制图片 {image_count}/{len(images)}: {image_name}")
        shutil.copy(image_source, image_target)

    log_progress("图片复制完成。")

    # 执行auto_update.py脚本而不是休眠
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
        log_progress(f"执行auto_update.py脚本失败: {str(e)}")
        if e.stdout:
            log_progress(f"脚本输出: {e.stdout}")
        if e.stderr:
            log_progress(f"脚本错误: {e.stderr}")
        return "\n".join(progress_log) + f"\n❌ 执行auto_update.py脚本失败 - {str(e)}"
    except Exception as e:
        log_progress(f"执行脚本时发生未预期错误: {str(e)}")
        return "\n".join(progress_log) + f"\n❌ 执行脚本时发生未预期错误 - {str(e)}"

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
        log_progress(f"Git操作失败: {str(e)}")
        return "\n".join(progress_log) + f"\n❌ Git操作失败 - {str(e)}"
    except Exception as e:
        log_progress(f"发生未预期错误: {str(e)}")
        return "\n".join(progress_log) + f"\n❌ 未预期错误 - {str(e)}"

    source_location = os.path.relpath(source_file, vault_path)
    log_progress(f"全部操作完成!")

    return "\n".join(progress_log) + f"\n✅ 成功将文章 {article_name} (来自 {source_location}) 发布到博客并推送到 GitHub"


# 运行 MCP 服务器
if __name__ == "__main__":
    mcp.run()