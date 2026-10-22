import json
import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parents[1]
MCP_CONFIG_PATH = PROJECT_ROOT / ".cursor" / "mcp.json"
SKILL_PATH = PROJECT_ROOT / ".cursor" / "skills" / "sync-catalog" / "SKILL.md"


def test_project_mcp_config_declares_pinned_local_servers() -> None:
    config = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))

    assert set(config) == {"mcpServers"}
    assert set(config["mcpServers"]) == {"metrics-mcp", "env-mcp"}
    expected_modules = {
        "metrics-mcp": "metrics_mcp.server",
        "env-mcp": "env_mcp.server",
    }
    for name, module in expected_modules.items():
        server = config["mcpServers"][name]
        assert server == {
            "type": "stdio",
            "command": "${workspaceFolder}/.venv/Scripts/python.exe",
            "args": [
                "-m",
                module,
                "--dataset",
                "${workspaceFolder}/dataset",
            ],
        }


def test_sync_catalog_skill_has_valid_frontmatter() -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n", content, re.DOTALL)

    assert match is not None
    frontmatter = yaml.safe_load(match.group("frontmatter"))
    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == SKILL_PATH.parent.name == "sync-catalog"
    assert isinstance(frontmatter["description"], str)
    assert frontmatter["description"].strip()


def test_sync_catalog_skill_encodes_safety_contract() -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")

    required_phrases = (
        "Preserve every `Purpose` and `Notes` value byte-for-byte.",
        "Never run `catalog-check --write` or `derive-catalog-data`.",
        "Make at most three checker attempts in total",
        ".venv\\Scripts\\python.exe -m catalog_check.cli --check",
        "`source_hash`",
        "Do not commit, push, open a pull request, or change branch.",
    )
    for phrase in required_phrases:
        assert phrase in content

    assert content.count("catalog_check.cli --check") == 1
