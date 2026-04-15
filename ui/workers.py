from __future__ import annotations

from time import perf_counter

from PySide6.QtCore import QObject, Signal, Slot

from domain.models import AnalysisSummary, Scenario
from engine.planner import AnalysisCancelled, PlanningEngine


class AnalysisWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(object, object, float)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, planning_engine: PlanningEngine, scenario: Scenario) -> None:
        super().__init__()
        self._planning_engine = planning_engine
        self._scenario = scenario
        self._cancel_requested = False

    @Slot()
    def run(self) -> None:
        started = perf_counter()
        try:
            self.progress.emit(5, "Preparing analysis")
            analysis = self._planning_engine.analyze(
                self._scenario,
                should_cancel=self._should_cancel,
                progress_callback=self._emit_progress,
            )
        except AnalysisCancelled:
            self.cancelled.emit()
            return
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.failed.emit(str(exc))
            return

        elapsed_ms = (perf_counter() - started) * 1000.0
        self.finished.emit(self._scenario, analysis, elapsed_ms)

    @Slot()
    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _should_cancel(self) -> bool:
        return self._cancel_requested

    def _emit_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)


class ComparisonWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(object, object, object, object, float)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, planning_engine: PlanningEngine, left_scenario: Scenario, right_scenario: Scenario) -> None:
        super().__init__()
        self._planning_engine = planning_engine
        self._left_scenario = left_scenario
        self._right_scenario = right_scenario
        self._cancel_requested = False

    @Slot()
    def run(self) -> None:
        started = perf_counter()
        try:
            self.progress.emit(5, "Preparing comparison")
            left_analysis = self._planning_engine.analyze(
                self._left_scenario,
                should_cancel=self._should_cancel,
                progress_callback=self._left_progress,
            )
            right_analysis = self._planning_engine.analyze(
                self._right_scenario,
                should_cancel=self._should_cancel,
                progress_callback=self._right_progress,
            )
        except AnalysisCancelled:
            self.cancelled.emit()
            return
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.failed.emit(str(exc))
            return

        elapsed_ms = (perf_counter() - started) * 1000.0
        self.finished.emit(
            self._left_scenario,
            self._right_scenario,
            left_analysis,
            right_analysis,
            elapsed_ms,
        )

    @Slot()
    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _should_cancel(self) -> bool:
        return self._cancel_requested

    def _left_progress(self, percent: int, message: str) -> None:
        scaled = min(50, max(8, int(percent * 0.5)))
        self.progress.emit(scaled, f"Scenario A: {message}")

    def _right_progress(self, percent: int, message: str) -> None:
        scaled = min(100, max(50, 50 + int(percent * 0.5)))
        self.progress.emit(scaled, f"Scenario B: {message}")
