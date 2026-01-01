"""
工具模块
包含 LLM 初始化、图表生成等辅助功能
"""

from .llm import get_llm
from .charts import generate_echarts_html

__all__ = ["get_llm", "generate_echarts_html"]
