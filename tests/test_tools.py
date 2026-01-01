"""
工具测试
测试 GitHub Stats Tool 和 Tavily Search Tool
"""

import pytest
import os
from dotenv import load_dotenv

load_dotenv()

from src.tools.github_tool import GitHubStatsTool, get_github_stats
from src.tools.tavily_tool import TavilySearchTool


class TestGitHubStatsTool:
    """GitHub Stats Tool 测试"""

    @pytest.fixture
    def github_tool(self):
        return GitHubStatsTool()

    def test_search_organization(self, github_tool):
        """测试组织搜索"""
        result = github_tool._search_organization("DeepSeek")
        assert result is not None
        assert "login" in result

    def test_run_success(self, github_tool):
        """测试完整流程"""
        result = github_tool.run("DeepSeek", top_n=3)
        assert result["organization"] != "Unknown"
        assert result["total_repositories"] > 0
        assert len(result["top_repos"]) > 0
        assert result["echarts_config"] is not None

    def test_echarts_generation(self, github_tool):
        """测试 ECharts 配置生成"""
        distribution = [
            {"language": "Python", "percentage": 60.0, "repository_count": 3},
            {"language": "Go", "percentage": 40.0, "repository_count": 2}
        ]
        config = github_tool._generate_echarts_config("test-org", distribution)
        assert config is not None
        assert "title" in config
        assert "series" in config

    def test_langchain_tool(self):
        """测试 LangChain Tool 包装"""
        tool = GitHubStatsTool.get_langchain_tool()
        assert tool.name == "github_stats"


class TestTavilySearchTool:
    """Tavily Search Tool 测试"""

    @pytest.fixture
    def tavily_tool(self):
        if not os.getenv("TAVILY_API_KEY"):
            pytest.skip("TAVILY_API_KEY not set")
        return TavilySearchTool()

    def test_search_company_news(self, tavily_tool):
        """测试新闻搜索"""
        results = tavily_tool.search_company_news("DeepSeek")
        assert isinstance(results, list)
        # 注意：可能返回空列表
        if results:
            assert "title" in results[0]

    def test_search_interview_experiences(self, tavily_tool):
        """测试面试经验搜索"""
        results = tavily_tool.search_interview_experiences("ByteDance")
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
