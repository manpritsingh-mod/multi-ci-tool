"""Reporting module for parsing test and lint results.

Extracts test and lint summaries from Maven build artifacts (JUnit and Checkstyle reports)
and provides structured dataclasses for integration into pipeline results.
"""

import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TestSummary:
    """Summary of test execution results."""

    total: int
    passed: int
    failed: int
    skipped: int


@dataclass(frozen=True)
class LintSummary:
    """Summary of lint/code quality violations."""

    total_violations: int
    errors: int
    warnings: int
    infos: int


class JUnitParser:
    """Parse JUnit test reports from Maven surefire."""

    def parse(self, surefire_dir: str) -> TestSummary:
        """
        Aggregate JUnit-style test case results from all XML files in a surefire reports directory.
        
        Parameters:
            surefire_dir (str): Path to the Maven Surefire reports directory (e.g., target/surefire-reports).
        
        Returns:
            TestSummary: Aggregated counts where `total` is the number of testcases processed and `passed`, `failed`, and `skipped` are the respective counts.
        """
        total = 0
        passed = 0
        failed = 0
        skipped = 0

        try:
            if not os.path.exists(surefire_dir):
                logger.info(f"Surefire reports directory not found: {surefire_dir}")
                return TestSummary(0, 0, 0, 0)

            xml_files = [f for f in os.listdir(surefire_dir) if f.endswith(".xml")]
            if not xml_files:
                logger.info(f"No XML files found in {surefire_dir}")
                return TestSummary(0, 0, 0, 0)

            for xml_file in xml_files:
                file_path = os.path.join(surefire_dir, xml_file)
                try:
                    tree = ET.parse(file_path)
                    root = tree.getroot()

                    # Handle both <testsuite> root and direct <testcase> elements
                    testcases = root.findall(".//testcase")
                    if not testcases:
                        testcases = [root] if root.tag == "testcase" else []

                    for testcase in testcases:
                        total += 1

                        # Determine test status by checking children
                        failure = testcase.find("failure")
                        error = testcase.find("error")
                        skipped_elem = testcase.find("skipped")

                        if skipped_elem is not None:
                            skipped += 1
                        elif failure is not None or error is not None:
                            failed += 1
                        else:
                            passed += 1

                except ET.ParseError as e:
                    logger.warning(f"Malformed JUnit XML in {file_path}: {e}")
                except (PermissionError, IOError) as e:
                    logger.error(f"Error reading {file_path}: {e}")

        except FileNotFoundError:
            logger.info(f"Surefire directory not found: {surefire_dir}")
            return TestSummary(0, 0, 0, 0)
        except (PermissionError, IOError) as e:
            logger.error(f"Error accessing surefire directory {surefire_dir}: {e}")
            return TestSummary(0, 0, 0, 0)

        return TestSummary(total, passed, failed, skipped)


class CheckstyleParser:
    """Parse Checkstyle linting results."""

    def parse(self, checkstyle_path: str) -> LintSummary:
        """Parse lint violations from Checkstyle report.

        Args:
            checkstyle_path: Path to target/checkstyle-result.xml

        Returns:
            LintSummary with violation counts by severity
        """
        total_violations = 0
        errors = 0
        warnings = 0
        infos = 0

        try:
            if not os.path.exists(checkstyle_path):
                logger.info(f"Checkstyle report not found: {checkstyle_path}")
                return LintSummary(0, 0, 0, 0)

            try:
                tree = ET.parse(checkstyle_path)
                root = tree.getroot()

                # Extract all <error> elements from all <file> elements
                errors_list = root.findall(".//error")

                for error_elem in errors_list:
                    total_violations += 1

                    # Get severity attribute (default to ERROR if missing)
                    severity = error_elem.get("severity", "error").upper()

                    if severity == "ERROR":
                        errors += 1
                    elif severity == "WARNING":
                        warnings += 1
                    elif severity == "INFO":
                        infos += 1

            except ET.ParseError as e:
                logger.warning(f"Malformed Checkstyle XML at {checkstyle_path}: {e}")
                return LintSummary(0, 0, 0, 0)

        except FileNotFoundError:
            logger.info(f"Checkstyle report not found: {checkstyle_path}")
            return LintSummary(0, 0, 0, 0)
        except (PermissionError, IOError) as e:
            logger.error(f"Error reading {checkstyle_path}: {e}")
            return LintSummary(0, 0, 0, 0)

        return LintSummary(total_violations, errors, warnings, infos)
