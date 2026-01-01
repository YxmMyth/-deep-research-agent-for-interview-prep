"""
配置管理
集中管理 API Keys 和模型配置
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = Field(default="openai", description="LLM 提供商: openai 或 anthropic")
    model: str = Field(default="gpt-4o", description="模型名称")
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1)


class APIConfig(BaseModel):
    """API 配置"""
    github_token: Optional[str] = None
    tavily_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class Config(BaseModel):
    """全局配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    api: APIConfig = Field(default_factory=APIConfig)

    # 工具配置
    max_github_repos: int = Field(default=5, ge=1, le=20)
    max_search_results: int = Field(default=10, ge=1, le=50)

    # 工作流配置
    max_iterations: int = Field(default=3, ge=1, le=10)


def load_config() -> Config:
    """
    从环境变量加载配置

    Returns:
        Config 实例
    """
    return Config(
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096"))
        ),
        api=APIConfig(
            github_token=os.getenv("GITHUB_TOKEN"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        ),
        max_github_repos=int(os.getenv("MAX_GITHUB_REPOS", "5")),
        max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", "10")),
        max_iterations=int(os.getenv("MAX_ITERATIONS", "3"))
    )


# 全局配置实例
config = load_config()
