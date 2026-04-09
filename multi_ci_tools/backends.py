"""Build Backend Abstractions and Implementations."""

import abc
import os
from typing import List, Optional


class BuildBackend(abc.ABC):
    """Abstract base class for all CI build backends (Maven, Gradle, etc.)."""

    @abc.abstractmethod
    def build_command(self) -> List[str]:
        """Return the command to build the project without running tests."""
        pass

    @abc.abstractmethod
    def test_command(self) -> List[str]:
        """Return the command to run standard tests."""
        pass

    @abc.abstractmethod
    def smoke_test_command(self) -> Optional[List[str]]:
        """Return the command for smoke tests, or None if disabled."""
        pass

    @abc.abstractmethod
    def get_surefire_report_path(self) -> str:
        """Return the path to the surefire junit XML reports."""
        pass

    @abc.abstractmethod
    def get_checkstyle_report_path(self) -> str:
        """Return the path to the checkstyle XML report."""
        pass


class MavenBackend(BuildBackend):
    """Maven specific build backend implementation."""

    def __init__(self, workspace: str = ".") -> None:
        self.workspace = workspace

    def build_command(self) -> List[str]:
        """mvn clean install -DskipTests"""
        return ["mvn", "clean", "install", "-DskipTests"]

    def test_command(self) -> List[str]:
        """mvn test"""
        return ["mvn", "test"]

    def smoke_test_command(self) -> Optional[List[str]]:
        """Return mvn test -Psmoke if MCT_ENABLE_SMOKE=true."""
        smoke_enabled = os.environ.get("MCT_ENABLE_SMOKE", "false").lower() == "true"
        if smoke_enabled:
            return ["mvn", "test", "-Psmoke"]
        return None

    def get_surefire_report_path(self) -> str:
        """Resolves target/surefire-reports"""
        return os.path.join(self.workspace, "target", "surefire-reports")

    def get_checkstyle_report_path(self) -> str:
        """Resolves target/checkstyle-result.xml"""
        return os.path.join(self.workspace, "target", "checkstyle-result.xml")

