"""Pipeline Orchestrator."""

import logging
import os
import time
from typing import Dict, List, Optional

from multi_ci_tools.adapters.base import CIAdapter
from multi_ci_tools.backends import BuildBackend
from multi_ci_tools.exceptions import CommandError, StageError
from multi_ci_tools.executor import CommandExecutor
from multi_ci_tools.reporting import JUnitParser, CheckstyleParser
from multi_ci_tools.notifiers import create_notifiers_from_env
from multi_ci_tools.types import (
    PipelineResult,
    RunConfig,
    StageResult,
    StageStatus,
    StageState,
    StageType,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the sequential execution of CI stages."""

    STAGE_ORDER = [
        StageType.SETUP,
        StageType.BUILD,
        StageType.TEST,
        StageType.PUBLISH,
        StageType.NOTIFY,
    ]

    def __init__(
        self,
        adapter: CIAdapter,
        backend: BuildBackend,
        executor: CommandExecutor,
    ) -> None:
        self.adapter = adapter
        self.backend = backend
        self.executor = executor
        self.results: Dict[StageType, StageResult] = {}

    def _create_stage_result(
        self,
        stage: StageType,
        state: StageState,
        start_time: float,
        error: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> StageResult:
        if duration is None:
            duration = time.monotonic() - start_time
        return StageResult(
            stage=stage,
            state=state,
            duration_seconds=duration,
            error_message=error,
        )

    def execute_stage(self, stage: StageType, config: RunConfig) -> StageResult:
        """
        Run the specified pipeline stage and return its result.
        
        Parameters:
            stage (StageType): The pipeline stage to execute.
            config (RunConfig): Run configuration; if `config.skip_stages` contains `stage`, the stage is marked as skipped.
        
        Returns:
            StageResult: The outcome of the stage, including `state`, `duration_seconds`, and optional `error_message`.
            
        Notes:
            - Commands are chosen per stage and executed via the configured executor.
            - If a CommandError is raised, the result is `FAILED` and will include the exception message and, when available, the exception's duration.
            - Any other exception results in a `FAILED` result with the exception message.
        """
        start_time = time.monotonic()
        
        # Check skip logic
        if config.skip_stages and stage in config.skip_stages:
            return self._create_stage_result(stage, StageState.SKIPPED, start_time)
            
        stage_cmds = []
        if stage == StageType.BUILD:
            stage_cmds.append(self.backend.build_command())
        elif stage == StageType.TEST:
            test_cmd = self.backend.test_command()
            stage_cmds.append(test_cmd)
        elif stage == StageType.SETUP:
            # We assume checkout happens externally via Git CI step
            stage_cmds.append(["echo", "Running Environment Validation"])
        elif stage == StageType.PUBLISH:
            stage_cmds.append(["echo", "Publishing disabled in abstract"])
        elif stage == StageType.NOTIFY:
            stage_cmds.append(["echo", "Notifications disabled in abstract"])
        else:
            return self._create_stage_result(
                stage, StageState.FAILED, start_time, error=f"Unknown stage {stage.value}"
            )

        # Execute
        try:
            for cmd in stage_cmds:
                logger.info(f"Executing {stage.value}: {' '.join(cmd)}")

                self.executor.run(cmd, timeout_seconds=1800)  # 30 minute timeout default
                
            return self._create_stage_result(stage, StageState.SUCCESS, start_time)
            
        except CommandError as e:
            logger.error(f"Stage {stage.value} failed: {e}")
            # Strict mode elevates failures
            return self._create_stage_result(
                stage, StageState.FAILED, start_time, error=str(e), duration=e.duration
            )
        except Exception as e:
            logger.exception(f"Unexpected error in {stage.value}")
            return self._create_stage_result(
                stage, StageState.FAILED, start_time, error=str(e)
            )

    def run_pipeline(self, config: RunConfig, output_file: str = "ci-result.json") -> PipelineResult:
        """
        Run the CI pipeline stages in order, aggregate per-stage outcomes, parse test and lint reports, write a JSON results file, and dispatch notifications.
        
        Parameters:
            config (RunConfig): Pipeline execution settings (e.g., workspace, skip_stages, timeouts).
            output_file (str): Path to write the pipeline JSON result (defaults to "ci-result.json").
        
        Returns:
            PipelineResult: Aggregated pipeline result containing CI context, stage results, overall status,
            total duration in seconds, and optional `test_summary` and `lint_summary` if parsing succeeded.
        """
        pipeline_start = time.monotonic()
        pipeline_success = True
        
        context = self.adapter.get_context()
        logger.info(f"Starting pipeline on {context.ci_name} for branch {context.branch}")

        for stage in self.STAGE_ORDER:
            # If a previous stage failed, skip non-essential stages
            if not pipeline_success and stage not in (StageType.PUBLISH, StageType.NOTIFY):
                logger.warning(f"Skipping {stage.value} due to previous failure.")
                self.results[stage] = StageResult(
                    stage=stage,
                    state=StageState.SKIPPED,
                    duration_seconds=0.0,
                    error_message="Skipped due to prior failure."
                )
                continue

            try:
                # Use native adapter log grouping
                with self.adapter.group_log(f"Stage: {stage.value.title()}"):
                    result = self.execute_stage(stage, config)
                    self.results[stage] = result
                    if result.state == StageState.FAILED:
                        pipeline_success = False
            except Exception as e:
                logger.error(f"Agent trapped critical failure: {e}")
                pipeline_success = False

        duration = time.monotonic() - pipeline_start

        # Parse test and lint reports
        logger.info("Parsing test and lint reports")
        test_summary = None
        lint_summary = None

        try:
            junit_parser = JUnitParser()
            surefire_dir = os.path.join(context.workspace, "target", "surefire-reports")
            test_summary = junit_parser.parse(surefire_dir)
            logger.info(f"Test summary: {test_summary.total} total, {test_summary.passed} passed")
        except Exception as e:
            logger.error(f"Error parsing JUnit reports: {e}")

        try:
            checkstyle_parser = CheckstyleParser()
            checkstyle_path = os.path.join(
                context.workspace, "target", "checkstyle-result.xml"
            )
            lint_summary = checkstyle_parser.parse(checkstyle_path)
            logger.info(f"Lint summary: {lint_summary.total_violations} violations")
        except Exception as e:
            logger.error(f"Error parsing Checkstyle reports: {e}")
        
        result_payload = PipelineResult(
            ci_context=context,
            stages=list(self.results.values()),
            overall=StageStatus.PASS if pipeline_success else StageStatus.FAIL,
            duration_seconds=duration,
            test_summary=test_summary,
            lint_summary=lint_summary,
        )

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result_payload.to_json())
            logger.info(f"Pipeline results written to {output_file}")
        except Exception as e:
            logger.error(f"Failed to write results: {e}")

        # Send notifications
        logger.info("Entering NOTIFY stage")
        try:
            notifiers = create_notifiers_from_env()
            for notifier in notifiers:
                try:
                    logger.info(f"Sending notification via {notifier.__class__.__name__}")
                    notifier.notify(result_payload)
                except Exception as e:
                    logger.error(f"Notifier {notifier.__class__.__name__} failed: {e}")
                    # Continue to next notifier; never raise
        except Exception as e:
            logger.error(f"Unexpected error in NOTIFY stage: {e}")
            # Return result anyway; don't crash

        return result_payload
