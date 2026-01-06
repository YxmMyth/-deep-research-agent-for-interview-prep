"""
文件解析工具

支持从 PDF 和 TXT 文件中提取文本内容
"""

from typing import Optional


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    从 PDF 文件字节中提取文本

    Args:
        file_bytes: PDF 文件的字节内容

    Returns:
        str: 提取的文本内容

    Raises:
        Exception: PDF 解析失败时抛出异常
    """
    try:
        import fitz  # pymupdf

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts = []

        for page_num, page in enumerate(doc):
            # 提取文本
            text = page.get_text()

            # 只添加非空页面
            if text.strip():
                text_parts.append(text)

        doc.close()

        # 用双换行符连接页面，保持段落结构
        return "\n\n".join(text_parts)

    except ImportError:
        raise ImportError(
            "pymupdf 库未安装，请运行: pip install pymupdf"
        )
    except Exception as e:
        raise Exception(f"PDF 解析失败: {str(e)}")


def extract_text_from_txt(file_bytes: bytes) -> str:
    """
    从 TXT 文件字节中提取文本

    Args:
        file_bytes: TXT 文件的字节内容

    Returns:
        str: 提取的文本内容
    """
    try:
        # 尝试 UTF-8 编码
        text = file_bytes.decode("utf-8")
        return text
    except UnicodeDecodeError:
        # 如果 UTF-8 失败，尝试 GBK（中文常用编码）
        try:
            text = file_bytes.decode("gbk")
            return text
        except UnicodeDecodeError:
            # 如果都失败，尝试忽略错误
            text = file_bytes.decode("utf-8", errors="ignore")
            return text


def extract_text_from_file(file_name: str, file_bytes: bytes) -> str:
    """
    根据文件扩展名自动选择解析方法

    Args:
        file_name: 文件名
        file_bytes: 文件的字节内容

    Returns:
        str: 提取的文本内容

    Raises:
        ValueError: 不支持的文件类型
    """
    file_name_lower = file_name.lower()

    if file_name_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif file_name_lower.endswith(".txt"):
        return extract_text_from_txt(file_bytes)
    else:
        raise ValueError(
            f"不支持的文件类型: {file_name}。"
            "请上传 PDF (.pdf) 或文本文件 (.txt)"
        )
