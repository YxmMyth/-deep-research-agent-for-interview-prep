"""
进度追踪模块 - 线程安全的进度状态管理和时间预估

核心功能：
- 实时进度追踪（当前阶段、完成百分比、剩余时间）
- 动态时间预估（基于已完成任务的平均速度）
- 线程安全设计（支持后台任务更新）
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class AnalysisStage(Enum):
    """分析阶段枚举"""
    INITIALIZING = "initializing"
    PLANNER = "planner"
    JD_RESEARCH = "jd_research"
    JD_RESEARCH_COMPLETE = "jd_research_complete"
    INTERVIEW_RESEARCH = "interview_research"
    INTERVIEW_RESEARCH_COMPLETE = "interview_research_complete"
    GAP_ANALYSIS = "gap_analysis"
    REPORT_WRITING = "report_writing"
    CRITIC = "critic"
    COMPLETE = "complete"
    ERROR = "error"


# 阶段显示名称映射
STAGE_DISPLAY_NAMES = {
    AnalysisStage.INITIALIZING: "⚙️ 初始化工作流",
    AnalysisStage.PLANNER: "📋 生成搜索计划",
    AnalysisStage.JD_RESEARCH: "🔍 搜索职位描述 (JD)",
    AnalysisStage.JD_RESEARCH_COMPLETE: "✅ JD 搜索完成",
    AnalysisStage.INTERVIEW_RESEARCH: "🔍 搜索面试经验",
    AnalysisStage.INTERVIEW_RESEARCH_COMPLETE: "✅ 面经搜索完成",
    AnalysisStage.GAP_ANALYSIS: "📊 分析技能差距",
    AnalysisStage.REPORT_WRITING: "✍️ 生成备战报告",
    AnalysisStage.CRITIC: "🔎 评审报告质量",
    AnalysisStage.COMPLETE: "✅ 分析完成",
    AnalysisStage.ERROR: "❌ 分析失败",
}

# 阶段基准进度百分比（用于时间预估）
STAGE_BASE_PROGRESS = {
    AnalysisStage.INITIALIZING: 0.0,
    AnalysisStage.PLANNER: 5.0,
    AnalysisStage.JD_RESEARCH: 10.0,
    AnalysisStage.JD_RESEARCH_COMPLETE: 35.0,
    AnalysisStage.INTERVIEW_RESEARCH: 40.0,
    AnalysisStage.INTERVIEW_RESEARCH_COMPLETE: 65.0,
    AnalysisStage.GAP_ANALYSIS: 70.0,
    AnalysisStage.REPORT_WRITING: 85.0,
    AnalysisStage.CRITIC: 95.0,
    AnalysisStage.COMPLETE: 100.0,
    AnalysisStage.ERROR: 0.0,
}


@dataclass
class ProgressState:
    """进度状态数据结构"""
    current_stage: str = AnalysisStage.INITIALIZING.value
    current_stage_display: str = STAGE_DISPLAY_NAMES[AnalysisStage.INITIALIZING]
    progress_percent: float = 0.0
    total_tasks: int = 0  # 总任务数（页面数）
    completed_tasks: int = 0  # 已完成任务数
    current_url: str = ""  # 当前处理的 URL
    estimated_remaining_seconds: float = 0.0  # 预估剩余时间
    average_time_per_task: float = 0.0  # 平均每页用时
    start_time: float = field(default_factory=time.time)
    successful_extractions: int = 0  # 成功提取数量
    failed_extractions: int = 0  # 失败提取数量

    def get_formatted_remaining_time(self) -> str:
        """获取格式化的剩余时间"""
        if self.estimated_remaining_seconds < 60:
            return f"{int(self.estimated_remaining_seconds)}秒"
        elif self.estimated_remaining_seconds < 3600:
            minutes = int(self.estimated_remaining_seconds / 60)
            seconds = int(self.estimated_remaining_seconds % 60)
            return f"{minutes}分{seconds}秒"
        else:
            hours = int(self.estimated_remaining_seconds / 3600)
            minutes = int((self.estimated_remaining_seconds % 3600) / 60)
            return f"{hours}小时{minutes}分"

    def get_success_rate(self) -> float:
        """计算成功率"""
        total = self.successful_extractions + self.failed_extractions
        if total == 0:
            return 0.0
        return (self.successful_extractions / total) * 100


class ProgressTracker:
    """
    线程安全的进度追踪器

    使用说明：
        1. 在开始分析前调用 reset() 重置状态
        2. 在每个阶段开始时调用 update_stage()
        3. 在处理每个 URL 时调用 update_url_progress()
        4. 在提取完成时调用 record_extraction_result()
        5. UI 线程调用 get_state() 获取当前进度
    """

    def __init__(self):
        self._state = ProgressState()
        self._lock = threading.Lock()
        self._task_start_times = []  # 记录每个任务的开始时间
        self._task_durations = []  # 记录每个任务的耗时

    def reset(self):
        """重置进度状态"""
        with self._lock:
            self._state = ProgressState()
            self._task_start_times = []
            self._task_durations = []

    def update_stage(self, stage: AnalysisStage, progress: Optional[float] = None):
        """
        更新当前阶段

        Args:
            stage: 分析阶段（使用 AnalysisStage 枚举）
            progress: 可选，手动指定进度百分比（如果为 None 则使用阶段基准进度）
        """
        with self._lock:
            self._state.current_stage = stage.value
            self._state.current_stage_display = STAGE_DISPLAY_NAMES.get(stage, stage.value)

            if progress is not None:
                self._state.progress_percent = progress
            else:
                self._state.progress_percent = STAGE_BASE_PROGRESS.get(stage, 0.0)

    def update_url_progress(
        self,
        current_url: str,
        completed: int,
        total: int,
        stage: AnalysisStage
    ):
        """
        更新 URL 处理进度

        Args:
            current_url: 当前处理的 URL
            completed: 已完成数量
            total: 总数量
            stage: 当前阶段（用于计算进度百分比）
        """
        with self._lock:
            self._state.current_url = current_url
            self._state.completed_tasks = completed
            self._state.total_tasks = total

            # 记录任务开始时间（第一次看到这个 URL 时）
            if len(self._task_start_times) < completed:
                self._task_start_times.append(time.time())

            # 计算阶段内的进度
            if total > 0:
                stage_progress = (completed / total) * 100

                # 获取当前阶段的基准进度范围
                base_progress = STAGE_BASE_PROGRESS.get(stage, 0.0)

                # 根据不同阶段计算进度范围
                if stage == AnalysisStage.JD_RESEARCH:
                    # JD 研究：10% - 35%
                    self._state.progress_percent = base_progress + (stage_progress * 0.25)
                elif stage == AnalysisStage.INTERVIEW_RESEARCH:
                    # 面经研究：40% - 65%
                    self._state.progress_percent = base_progress + (stage_progress * 0.25)
                else:
                    # 其他阶段使用基准进度
                    self._state.progress_percent = base_progress + (stage_progress * 0.1)

            # 更新剩余时间预估
            self._update_time_estimate()

    def record_extraction_result(self, success: bool, duration: Optional[float] = None):
        """
        记录提取结果（用于统计成功率和计算平均速度）

        Args:
            success: 是否成功
            duration: 可选，任务耗时（秒）
        """
        with self._lock:
            if success:
                self._state.successful_extractions += 1
            else:
                self._state.failed_extractions += 1

            # 记录任务耗时
            if duration is not None:
                self._task_durations.append(duration)
            elif self._task_start_times:
                # 如果没有提供耗时，计算最近一个任务的耗时
                start_time = self._task_start_times[-1]
                duration = time.time() - start_time
                self._task_durations.append(duration)

            # 更新平均耗时
            if self._task_durations:
                self._state.average_time_per_task = sum(self._task_durations) / len(self._task_durations)

            # 更新剩余时间预估
            self._update_time_estimate()

    def _update_time_estimate(self):
        """更新剩余时间预估"""
        # 如果没有已完成任务，使用预估值
        if self._state.total_tasks == 0 or self._state.completed_tasks == 0:
            # 初始预估：基于阶段
            remaining_percent = 100 - self._state.progress_percent
            # 假设平均每页 3 秒（包含网络、解析、LLM 调用）
            estimated_total_seconds = 180  # 3 分钟
            self._state.estimated_remaining_seconds = (remaining_percent / 100) * estimated_total_seconds
            return

        # 基于实际速度预估
        remaining_tasks = self._state.total_tasks - self._state.completed_tasks

        # 如果有平均耗时数据，使用它
        if self._state.average_time_per_task > 0:
            self._state.estimated_remaining_seconds = remaining_tasks * self._state.average_time_per_task
        else:
            # 否则使用默认预估（每页 3 秒）
            self._state.estimated_remaining_seconds = remaining_tasks * 3

    def get_state(self) -> ProgressState:
        """
        获取当前进度状态（线程安全）

        Returns:
            ProgressState 的副本（避免外部修改）
        """
        with self._lock:
            # 返回副本以避免外部修改
            import copy
            return copy.copy(self._state)

    def set_analysis_mode(self, mode: str):
        """
        设置分析模式（用于调整时间预估）

        Args:
            mode: "quick" 或 "standard"
        """
        with self._lock:
            # 快速模式的任务数量更少，时间预估可以更乐观
            if mode == "quick":
                # 快速模式：每页预估 2 秒
                pass
            else:
                # 标准模式：每页预估 3 秒
                pass


# 全局单例模式（所有线程共享同一个实例）
_global_progress_tracker = None
_tracker_lock = threading.Lock()


def get_progress_tracker() -> ProgressTracker:
    """
    获取全局唯一的进度追踪器实例（线程安全）

    所有线程（UI线程和后台线程）共享同一个实例，
    确保进度更新能被UI线程读取到。

    Returns:
        全局唯一的 ProgressTracker 实例
    """
    global _global_progress_tracker
    if _global_progress_tracker is None:
        with _tracker_lock:
            # 双重检查锁定模式（Double-Checked Locking）
            if _global_progress_tracker is None:
                _global_progress_tracker = ProgressTracker()
    return _global_progress_tracker


def reset_progress_tracker():
    """重置全局进度追踪器"""
    tracker = get_progress_tracker()
    tracker.reset()
