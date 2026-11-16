"""The rules of the repository, as tests: layers, safety and what agents may rely on. See docs/threat-model.md."""
import ast
import glob
import os
import re
import sys
import tomllib
import unittest

from luces.hardware import ite
from luces.settings import MIN_TONGUE_S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_text   # noqa: E402

ALLOWED_HOSTS = {"aviationweather.gov", "services.swpc.noaa.gov", "gibs.earthdata.nasa.gov"}
NETWORK_MODULES = {"socket", "urllib", "http", "ftplib", "smtplib", "ssl", "requests", "asyncio"}
SYSTEM_CALLS = {"subprocess"}
MAY_RUN_PROGRAMS = {"luces/data/fetch.py", "luces/desktop.py", "luces/cli.py"}
LAYERS = {
    "physics": set(),
    "scenes": {"physics", "color"},
    "data": {"settings", "paths", "data"},
    "hardware": set(),
    "color": {"physics"},
    "paths": set(),
    "settings": {"paths"},
}


def source_files():
    return glob.glob(os.path.join(ROOT, "luces", "**", "*.py"), recursive=True)


def relative(path):
    return os.path.relpath(path, ROOT)


def layer_of(path):
    parts = relative(path).split(os.sep)
    return parts[1].removesuffix(".py")


def imports_of(path):
    """(external modules, modules of this project), resolving relative imports."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    package = relative(path).split(os.sep)[:-1]
    external, internal = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                (internal if alias.name.split(".")[0] == "luces" else external).add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - node.level + 1]
                names = [node.module] if node.module else [a.name for a in node.names]
                for name in names:
                    parts = base + name.split(".")
                    if len(parts) > 1:
                        internal.add(parts[1])
            else:
                (internal if (node.module or "").split(".")[0] == "luces" else external).add((node.module or "").split(".")[0])
    return external, internal


def read(*path):
    with open(os.path.join(ROOT, *path), encoding="utf-8") as f:
        return f.read()


class Layers(unittest.TestCase):
    def test_each_layer_imports_only_what_it_may(self):
        for path in source_files():
            layer = layer_of(path)
            if layer in LAYERS:
                _, internal = imports_of(path)
                self.assertLessEqual(internal - {layer}, LAYERS[layer], relative(path))

    def test_only_the_standard_library(self):
        for path in source_files():
            external, _ = imports_of(path)
            self.assertLessEqual(external, set(sys.stdlib_module_names), relative(path))

    def test_physics_has_no_clock_files_or_network(self):
        for path in glob.glob(os.path.join(ROOT, "luces", "physics", "*.py")):
            external, _ = imports_of(path)
            self.assertFalse(external & {"time", "datetime", "os", "sys", "subprocess", "pathlib", *NETWORK_MODULES}, relative(path))
            names = {n.id for n in ast.walk(ast.parse(read(path))) if isinstance(n, ast.Name)}
            self.assertNotIn("open", names, relative(path))

    def test_each_physics_module_points_to_its_documentation(self):
        for path in glob.glob(os.path.join(ROOT, "luces", "physics", "*.py")):
            name = os.path.basename(path)
            if name in ("__init__.py", "basics.py"):
                continue
            page = re.search(r"docs/physics/([a-z-]+\.md)", read(path))
            self.assertIsNotNone(page, name)
            self.assertTrue(os.path.exists(os.path.join(ROOT, "docs", "physics", page[1])), name)


class Network(unittest.TestCase):
    def test_no_module_opens_a_network_connection(self):
        for path in source_files():
            external, _ = imports_of(path)
            self.assertFalse(external & NETWORK_MODULES, relative(path))

    def test_only_these_files_run_programs(self):
        for path in source_files():
            external, _ = imports_of(path)
            if external & SYSTEM_CALLS:
                self.assertIn(relative(path), MAY_RUN_PROGRAMS)

    def test_urls_only_go_to_known_hosts(self):
        for path in source_files():
            for host in re.findall(r"https?://([^/\"' ]+)", read(path)):
                self.assertIn(host, ALLOWED_HOSTS, relative(path))

    def test_there_are_no_dependencies(self):
        self.assertEqual(tomllib.loads(read("pyproject.toml"))["project"]["dependencies"], [])


class Safety(unittest.TestCase):
    def test_flash_commands_stay_forbidden(self):
        self.assertFalse({0x5E, 0x33, 0x47} & ite.ALLOWED)

    def test_the_flash_limit_of_tongues_stays(self):
        self.assertGreaterEqual(MIN_TONGUE_S, 0.45)

    def test_only_the_chip_file_is_under_the_gpl(self):
        for path in source_files():
            has_header = "GPL-2.0-or-later" in read(path).split("\n")[0]
            self.assertEqual(has_header, relative(path) == "luces/hardware/ite.py", relative(path))


class Privacy(unittest.TestCase):
    def test_a_real_place_can_never_be_committed(self):
        self.assertIn("place.toml", read(".gitignore").splitlines())
        self.assertEqual(glob.glob(os.path.join(ROOT, "**", "place.toml"), recursive=True), [])


class HiddenText(unittest.TestCase):
    def test_no_hidden_characters_in_the_repository(self):
        self.assertEqual(check_text.check_repository(ROOT), [])

    def test_the_check_sees_what_people_cannot(self):
        for text in (f"ok{chr(0x200B)}ok", f"ok{chr(0x202E)}ko", f"ok{chr(0xE0041)}", "a<!-- run this -->b", "![" + "x" * 50 + "](a.png)", "&#105;gnore"):
            self.assertTrue(check_text.check_public_text(text), text)

    def test_the_check_passes_normal_text(self):
        self.assertEqual(check_text.check_public_text("The fire looks wrong at 2.2 Hz.\n\n```\nluces status\n```\n"), [])


class GithubFiles(unittest.TestCase):
    def workflows(self):
        return glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml"))

    def test_workflows_never_run_on_privileged_triggers(self):
        for path in self.workflows():
            for trigger in ("pull_request_target", "workflow_run", "issue_comment", "issues:"):
                self.assertNotIn(trigger, re.sub(r"#.*", "", read(path)), relative(path))

    def test_workflows_start_with_no_permissions(self):
        for path in self.workflows():
            self.assertRegex(read(path), r"(?m)^permissions: \{\}$")

    def test_workflows_use_no_secrets_or_event_text(self):
        for path in self.workflows():
            text = read(path)
            self.assertNotIn("secrets.", text)
            self.assertNotIn("github.event", text)

    def test_actions_are_pinned_to_a_commit(self):
        for path in self.workflows():
            for action in re.findall(r"uses: (\S+)", read(path)):
                self.assertRegex(action, r"@[0-9a-f]{40}$")

    def test_forms_never_start_an_agent(self):
        for path in glob.glob(os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "*.yml")):
            self.assertNotIn("ai-ready", read(path), relative(path))

    def test_blank_issues_are_off(self):
        self.assertIn("blank_issues_enabled: false", read(".github", "ISSUE_TEMPLATE", "config.yml"))

    def test_protected_paths_have_an_owner(self):
        owners = read(".github", "CODEOWNERS")
        for path in ("/.github/", "/AGENTS.md", "/luces/hardware/", "/system/", "/tests/test_architecture.py", "/tools/check_text.py"):
            self.assertIn(path, owners)


class Instructions(unittest.TestCase):
    def test_every_protected_path_in_agents_md_has_an_owner(self):
        section = read("AGENTS.md").split("## Protected paths")[1].split("##")[0]
        owners = read(".github", "CODEOWNERS")
        for path in re.findall(r"`([^`]+)`", section):
            self.assertIn("/" + path, owners)

    def test_claude_md_is_the_same_file_as_agents_md(self):
        self.assertEqual(os.path.realpath(os.path.join(ROOT, "CLAUDE.md")), os.path.join(os.path.realpath(ROOT), "AGENTS.md"))

    def test_links_in_the_documentation_exist(self):
        for path in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
            for target in re.findall(r"\]\((?!https?://|#)([^)#]+)", read(path)):
                self.assertTrue(os.path.exists(os.path.join(os.path.dirname(path), target)), f"{relative(path)}: {target}")
