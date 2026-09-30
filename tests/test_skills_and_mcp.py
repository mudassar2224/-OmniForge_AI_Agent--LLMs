"""Tests for OmniForge Skills and MCP modules."""
import json
import pytest
from pathlib import Path

from omniforge.skills import (
    SkillMetadata,
    SkillRegistry,
    get_skill_registry,
    select_skills_for_task,
    load_skills_for_task,
    reset_skill_registry,
)
from omniforge.mcp import MCPToolManager, get_mcp_manager, reset_mcp_manager
from omniforge.mcp.servers.coding_server import (
    list_workspace,
    read_file,
    write_file,
    run_python,
)
from omniforge.mcp.servers.files_server import (
    list_files,
    read_document,
    get_file_info,
)


@pytest.fixture
def clean_registries():
    reset_skill_registry()
    reset_mcp_manager()
    yield
    reset_skill_registry()
    reset_mcp_manager()


def test_skill_registry_discovery(clean_registries):
    registry = get_skill_registry()
    skills = registry.list_skills()

    expected_skills = [
        "coding",
        "data-analysis",
        "debugging",
        "deep-research",
        "document-analysis",
        "media-generation",
        "planning",
        "report-generation",
        "source-verification",
        "web-research",
    ]

    for expected in expected_skills:
        assert expected in skills, f"Expected skill {expected} not found in {skills}"

    summaries = registry.get_skill_summaries()
    assert "planning: Break complex requests" in summaries
    assert "coding: Write, execute, test" in summaries


def test_skill_lazy_loading(clean_registries):
    registry = get_skill_registry()
    skill_meta = registry.get_skill("coding")
    assert skill_meta is not None
    assert not skill_meta.loaded
    assert skill_meta.content == ""

    # Now load the skill
    content = registry.load_skill("coding")
    assert skill_meta.loaded
    assert "Coding Skill" in content
    assert "Python 3.12" in content


def test_select_skills_for_task(clean_registries):
    registry = get_skill_registry()

    # Web search task
    selected = select_skills_for_task("Search the web for latest quantum computing breakthroughs", registry)
    assert "web-research" in selected

    # Coding and debugging task
    selected = select_skills_for_task("Fix bug and debug python traceback", registry)
    assert "debugging" in selected or "coding" in selected

    # Data analysis task
    selected = select_skills_for_task("Analyze the dataset csv using statistics", registry)
    assert "data-analysis" in selected

    # Default fallback
    selected = select_skills_for_task("Some completely unknown query", registry)
    assert selected == ["planning"]


def test_load_skills_for_task(clean_registries):
    loaded = load_skills_for_task("Please plan the research steps and search web")
    assert "planning" in loaded or "web-research" in loaded
    for name, content in loaded.items():
        assert len(content) > 0


@pytest.mark.asyncio
async def test_mcp_manager(clean_registries):
    mgr = get_mcp_manager()
    # Register a server that deliberately does not exist to ensure our real MCP stdio client gracefully catches the failure
    await mgr.register_server("test-server", "python", ["-m", "this_module_does_not_exist_12345"])
    assert not mgr.is_server_connected("test-server")

    # Connect should gracefully fail and return False (catching the FileNotFoundError or subprocess crash)
    connected = await mgr.connect_server("test-server")
    assert connected is False
    assert not mgr.is_server_connected("test-server")


@pytest.mark.asyncio
async def test_coding_server_tools(tmp_path):
    # Test write_file
    target_file = tmp_path / "hello.txt"
    write_res = await write_file(str(target_file), "Hello OmniForge!")
    assert "Successfully wrote" in write_res
    assert target_file.exists()

    # Test read_file
    read_res = await read_file(str(target_file))
    assert read_res == "Hello OmniForge!"

    # Test list_workspace
    list_res = await list_workspace(str(tmp_path))
    data = json.loads(list_res)
    assert data["count"] >= 1
    assert any(item["name"] == "hello.txt" for item in data["items"])

    # Test run_python
    code = "import sys; print('Output from python', end='')"
    py_res = await run_python(code, timeout=10)
    py_data = json.loads(py_res)
    assert py_data["exit_code"] == 0
    assert py_data["stdout"] == "Output from python"


@pytest.mark.asyncio
async def test_files_server_tools(tmp_path):
    sample_file = tmp_path / "document.md"
    sample_file.write_text("# Title\nThis is a sample document content.", encoding="utf-8")

    # Test get_file_info
    info_res = await get_file_info(str(sample_file))
    info = json.loads(info_res)
    assert info["exists"] is True
    assert info["name"] == "document.md"
    assert info["line_count"] == 2

    # Test read_document
    doc_content = await read_document(str(sample_file))
    assert "# Title" in doc_content
    assert "sample document" in doc_content

    # Test list_files
    files_res = await list_files(str(tmp_path), pattern="*.md")
    files_data = json.loads(files_res)
    assert files_data["total_matched"] == 1
