import os

import pytest

from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.working_directory import WorkingDirectory


def test_relative_paths_resolve_inside_the_working_directory(tmp_path) -> None:
    assert WorkingDirectory(str(tmp_path)).resolve("out/report.md") == str(
        tmp_path.resolve() / "out" / "report.md"
    )


def test_absolute_paths_inside_the_working_directory_are_kept(tmp_path) -> None:
    path = str(tmp_path.resolve() / "report.md")

    assert WorkingDirectory(str(tmp_path)).resolve(path) == path


@pytest.mark.parametrize("path", ["../escaped.md", "/etc/passwd", "a/../../escaped.md"])
def test_paths_outside_the_working_directory_are_refused(tmp_path, path) -> None:
    with pytest.raises(ToolFailure, match="is outside the working directory."):
        WorkingDirectory(str(tmp_path / "work")).resolve(path)


def test_a_symlink_pointing_out_of_the_working_directory_is_refused(tmp_path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    os.symlink(tmp_path, work / "link")

    with pytest.raises(ToolFailure, match="is outside the working directory."):
        WorkingDirectory(str(work)).resolve("link/secret.md")
