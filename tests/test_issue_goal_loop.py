from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/github-issue-driven-dev/SKILL.md"
AGENTS_TEMPLATE = ROOT / "skills/github-issue-driven-dev/assets/repo-AGENTS-template.md"
CLI = ROOT / "skills/github-issue-driven-dev/scripts/codex-gh-workflow"


def require(path: Path, phrases: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 500, f"{path} exceeds 500 lines"
    for phrase in phrases:
        assert phrase in text, f"{phrase!r} missing from {path}"


require(
    SKILL,
    [
        "## One Issue, One Goal Loop",
        "select the smallest unmet acceptance criterion",
        "Re-evaluate the whole Issue",
        "blocked report",
    ],
)
require(
    AGENTS_TEMPLATE,
    [
        "1 Issueを1つのゴールループとして扱い",
        "未達成なら同じIssue内で次の周回を行う",
        "blocked reportと再開点",
    ],
)

subprocess.run(["bash", "-n", str(CLI)], check=True)
with tempfile.TemporaryDirectory(prefix="issue-goal-loop-") as temp:
    repo = Path(temp)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/nanameru/template-validation.git"],
        cwd=repo,
        check=True,
    )
    subprocess.run([str(CLI), "install-repo-templates"], cwd=repo, check=True, capture_output=True)
    feature = (repo / ".github/ISSUE_TEMPLATE/feature.yml").read_text(encoding="utf-8")
    bug = (repo / ".github/ISSUE_TEMPLATE/bug.yml").read_text(encoding="utf-8")
    for phrase in ["ループゴール", "受入条件", "検証方法・終了条件・強制停止条件", "周回ナレッジログ"]:
        assert phrase in feature, f"{phrase!r} missing from generated feature template"
    for phrase in ["受入条件", "検証方法・終了条件・強制停止条件", "周回ナレッジログ"]:
        assert phrase in bug, f"{phrase!r} missing from generated bug template"

print("GitHub Issue goal loop mapping: OK")
