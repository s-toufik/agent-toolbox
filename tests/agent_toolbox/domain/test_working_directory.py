import os

import pytest

from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.vault import Vault


def test_relative_paths_resolve_inside_the_vault(tmp_path) -> None:
    assert Vault(str(tmp_path)).resolve("out/report.md") == str(
        tmp_path.resolve() / "out" / "report.md"
    )


def test_absolute_paths_inside_the_vault_are_kept(tmp_path) -> None:
    path = str(tmp_path.resolve() / "report.md")

    assert Vault(str(tmp_path)).resolve(path) == path


@pytest.mark.parametrize("path", ["../escaped.md", "/etc/passwd", "a/../../escaped.md"])
def test_paths_outside_the_vault_are_refused(tmp_path, path) -> None:
    with pytest.raises(ToolFailure, match="is outside the vault."):
        Vault(str(tmp_path / "vault")).resolve(path)


def test_a_symlink_pointing_out_of_the_vault_is_refused(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    os.symlink(tmp_path, vault / "link")

    with pytest.raises(ToolFailure, match="is outside the vault."):
        Vault(str(vault)).resolve("link/secret.md")
