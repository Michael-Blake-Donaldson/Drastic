from __future__ import annotations

from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QObject, Signal, Slot

from domain.models import AnalysisSummary, Scenario
from engine.planner import AnalysisCancelled, PlanningEngine
from services.report_export import write_text_report
from services.report_templates import build_comparison_report, build_scenario_report


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


class ScenarioExportWorker(QObject):
    """Builds and writes a scenario report entirely off the UI thread."""

    finished = Signal(object)  # Path
    failed = Signal(str)

    def __init__(
        self,
        scenario: Scenario,
        analysis: AnalysisSummary,
        timeline_day: int,
        export_directory: Path,
        variant_label: str,
    ) -> None:
        super().__init__()
        self._scenario = scenario
        self._analysis = analysis
        self._timeline_day = timeline_day
        self._export_directory = export_directory
        self._variant_label = variant_label

    @Slot()
    def run(self) -> None:
        try:
            report_text = build_scenario_report(
                self._scenario, self._analysis, timeline_day=self._timeline_day
            )
            output_path = write_text_report(
                self._export_directory,
                prefix=f"scenario_report_{self._variant_label}",
                content=report_text,
            )
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.failed.emit(str(exc))
            return
        self.finished.emit(output_path)


class ComparisonExportWorker(QObject):
    """Builds and writes a comparison report entirely off the UI thread."""

    finished = Signal(object)  # Path
    failed = Signal(str)

    def __init__(
        self,
        payload: dict[str, object],
        timeline_day: int,
        export_directory: Path,
    ) -> None:
        super().__init__()
        self._payload = payload
        self._timeline_day = timeline_day
        self._export_directory = export_directory

    @Slot()
    def run(self) -> None:
        payload = self._payload
        try:
            report_text = build_comparison_report(
                left_scenario=payload["left_scenario"],
                right_scenario=payload["right_scenario"],
                left_analysis=payload["left_analysis"],
                right_analysis=payload["right_analysis"],
                profile=payload["profile"],
                profile_weights=payload["profile_weights"],
                metric_filter=payload["metric_filter"],
                winner=payload["winner"],
                lineage_left=payload["lineage_left"],
                lineage_right=payload["lineage_right"],
                timeline_day=self._timeline_day,
            )
            output_path = write_text_report(
                self._export_directory,
                prefix="comparison_report",
                content=report_text,
            )
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.failed.emit(str(exc))
            return
        self.finished.emit(output_path)
