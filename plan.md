Kế hoạch xây dựng dự án Claude_WindFaculty từ đầu
1. Định nghĩa lại bản chất dự án

Tên repo:

https://github.com/WindFaculty/Claude_WindFaculty.git

Bản chất dự án:

Claude_WindFaculty không phải là một agent coding mới thay thế Claude.
Claude_WindFaculty là một bộ khung môi trường giúp Claude CLI làm việc tốt hơn, an toàn hơn, ít tốn token hơn, có validation thật hơn và có benchmark rõ ràng hơn.

Nói ngắn gọn:

Claude CLI = bộ não và agent chính.
Claude_WindFaculty = hệ sinh thái công cụ, cấu hình, policy, context, validator và benchmark xung quanh Claude CLI.

Không xây lại:

planner riêng
executor riêng
agent runtime riêng
multi-agent engine riêng
router phức tạp riêng
repair engine tự chế quá sớm

Chỉ xây:

.claude/
CLAUDE.md
skills
subagents
hooks
MCP config
tool wrappers
context packers
diff validators
test runners
benchmark scripts
artifact/report format
repo bootstrap scripts
2. Kiến trúc tổng thể mới

Kiến trúc nên xoay quanh các capability native của Claude Code:

Claude CLI / Claude Code
├── Project memory: CLAUDE.md
├── Skills: .claude/skills/
├── Subagents: .claude/agents/
├── Hooks: .claude/settings.json
├── MCP servers: .mcp.json
├── Permissions: allowed/ask/deny rules
├── Shell tools: wrapped by scripts/tools/
├── Context tools: third_party + scripts/context/
├── Validators: scripts/validate/
├── Benchmarks: benchmarks/
└── Reports: reports/

Claude Code đã có CLI command mode như claude, claude -p, resume session, plugin management và project state management; vì vậy phần runner shell chỉ cần wrap CLI và lưu artifact, không cần tạo executor riêng.

3. Cây thư mục đề xuất

Dự án mới nên bắt đầu bằng cấu trúc này:

Claude_WindFaculty/
├── README.md
├── CLAUDE.md
├── LICENSE
├── .gitignore
├── .env.example
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   ├── context-researcher.md
│   │   ├── test-diagnoser.md
│   │   ├── diff-reviewer.md
│   │   ├── security-reviewer.md
│   │   └── report-writer.md
│   ├── skills/
│   │   ├── repo-intake/
│   │   │   └── SKILL.md
│   │   ├── context-pack/
│   │   │   └── SKILL.md
│   │   ├── code-edit/
│   │   │   └── SKILL.md
│   │   ├── test-repair/
│   │   │   └── SKILL.md
│   │   ├── diff-review/
│   │   │   └── SKILL.md
│   │   ├── benchmark/
│   │   │   └── SKILL.md
│   │   └── final-report/
│   │       └── SKILL.md
│   └── commands/
│       ├── intake.md
│       ├── plan.md
│       ├── fix.md
│       ├── review.md
│       ├── benchmark.md
│       └── report.md
├── .mcp.json
├── configs/
│   ├── tools.yaml
│   ├── budgets.yaml
│   ├── context.yaml
│   ├── validation.yaml
│   └── benchmark.yaml
├── scripts/
│   ├── bootstrap/
│   │   ├── setup.ps1
│   │   ├── setup.sh
│   │   ├── clone_third_party.py
│   │   └── verify_environment.py
│   ├── context/
│   │   ├── build_index.py
│   │   ├── select_context.py
│   │   ├── compress_context.py
│   │   └── summarize_repo.py
│   ├── tools/
│   │   ├── safe_bash.py
│   │   ├── safe_git.py
│   │   ├── safe_test.py
│   │   └── safe_file.py
│   ├── validate/
│   │   ├── validate_diff.py
│   │   ├── validate_tests.py
│   │   ├── validate_secrets.py
│   │   ├── validate_context.py
│   │   └── validate_report.py
│   ├── benchmark/
│   │   ├── run_task.py
│   │   ├── run_suite.py
│   │   └── score_run.py
│   └── reports/
│       └── write_report.py
├── third_party/
│   ├── manifest.yaml
│   └── README.md
├── tasks/
│   ├── examples/
│   ├── dogfood/
│   └── benchmark/
├── benchmarks/
│   ├── suites/
│   ├── expected/
│   └── results/
├── artifacts/
│   └── .gitkeep
├── reports/
│   └── .gitkeep
└── tests/
    ├── test_bootstrap.py
    ├── test_safe_tools.py
    ├── test_context.py
    ├── test_validation.py
    └── test_benchmark.py

Điểm quan trọng: không có agent_runtime/, không có runners/claude_executor.py kiểu cũ. Claude CLI làm việc trực tiếp. Scripts chỉ hỗ trợ Claude trước, trong và sau khi chạy.

4. Vai trò của từng thành phần
4.1 CLAUDE.md

Đây là file quan trọng nhất của dự án.

Claude Code dùng CLAUDE.md để nạp project instructions vào mỗi session; tài liệu Claude cũng khuyến nghị dùng file này cho coding standards, workflow, architecture và những điều lặp lại trong mỗi phiên làm việc.

Nội dung nên có:

Project mission
Operating rules
Coding rules
Git rules
Testing rules
Context rules
Safety rules
Report requirements
Definition of Done

CLAUDE.md nên nói rõ:

Claude là agent chính.
Không sửa code khi chưa đọc task.
Không gửi whole repo vào context.
Không chạy command nguy hiểm.
Không chấp nhận patch nếu chưa có diff validation.
Không xem exit code 0 là thành công tuyệt đối.
Luôn tạo artifact/report sau mỗi task.
4.2 .claude/skills/

Skills là nơi đóng gói quy trình lặp lại. Claude Code hỗ trợ skill qua SKILL.md; skill có thể được gọi trực tiếp bằng /skill-name, và phần thân skill chỉ load khi cần, giúp giảm context/token so với nhét mọi thứ vào CLAUDE.md.

Các skill nên tạo ngay:

repo-intake
context-pack
code-edit
test-repair
diff-review
benchmark
final-report

Mỗi skill không chạy agent riêng. Nó chỉ hướng dẫn Claude CLI làm đúng quy trình.

Ví dụ:

.claude/skills/context-pack/SKILL.md

Nhiệm vụ:

Dùng claude-context, ops-codegraph, sem hoặc fallback grep để chọn context.
Không chọn quá nhiều file.
Ghi selected_context.json.
Ghi lý do chọn từng file.
4.3 .claude/agents/

Subagents dùng cho side task để tránh làm bẩn context chính. Claude Code cho phép tạo subagent có context riêng, prompt riêng, tool access riêng và permission riêng; phù hợp cho việc đọc log, tìm file, review diff, hoặc viết report mà không nhồi toàn bộ vào main conversation.

Subagents nên có:

context-researcher
test-diagnoser
diff-reviewer
security-reviewer
report-writer

Vai trò:

context-researcher: tìm file, symbol, dependency, context liên quan.
test-diagnoser: đọc test log và phân loại lỗi.
diff-reviewer: kiểm tra diff có đúng task không.
security-reviewer: kiểm tra secret, command nguy hiểm, thay đổi rủi ro.
report-writer: tổng hợp artifact thành báo cáo.
4.4 .claude/settings.json

Đây là nơi cấu hình hooks, permissions, tool behavior.

Claude Code hooks có thể chạy ở các lifecycle event như PreToolUse, Stop, Notification; hook có thể trả JSON decision để deny tool call, ví dụ chặn command phá hoại trước khi Claude thực thi.

Cần dùng hooks cho:

PreToolUse Bash
PreToolUse Write/Edit
PostToolUse Bash
Stop
Notification

Mục tiêu:

chặn command nguy hiểm
ghi log mọi command
chạy diff validator sau edit
nhắc Claude tạo report khi kết thúc
chặn sửa file ngoài allowlist nếu task có target rõ
4.5 .mcp.json

Claude Code có thể kết nối tool/data source qua MCP; MCP server giúp Claude truy cập tool ngoài như issue tracker, database, monitoring, file/search service mà không cần copy thủ công vào chat.

Trong dự án này, MCP nên dùng muộn hơn, sau khi skeleton ổn.

MCP phase đầu chỉ nên có:

filesystem MCP nếu cần
git MCP nếu cần
local context MCP nếu tự build sau

Không nên thêm quá nhiều MCP server lúc đầu vì sẽ tăng bề mặt lỗi và permission risk.

5. Repo open-source nên tải về trước

Theo file nghiên cứu bạn gửi, các repo quan trọng nhất cho context quality, dependency graph, semantic diff, secure shell, repair loop và validation đã được chọn sẵn. Với phạm vi mới, ta phân loại lại như sau.

5.1 Nhóm nên clone/vendor trực tiếp
zilliztech/claude-context
optave/ops-codegraph-tool
Ataraxy-Labs/sem
Ataraxy-Labs/claw-compactor
divagr18/SecureShell
pre-commit/pre-commit

Vai trò:

claude-context: tìm context liên quan cho Claude.
ops-codegraph-tool: tạo dependency graph và impact map.
sem: semantic diff, impact analysis, diff-aware context.
claw-compactor: nén context trước khi gửi cho Claude.
SecureShell: tham khảo/chuyển hóa rule chặn shell command nguy hiểm.
pre-commit: chạy validation hooks trước khi chấp nhận patch.
5.2 Nhóm chỉ tham khảo trước
swe-agent/swe-agent
langchain-ai/langgraph
microsoft/agent-framework
agentscope-ai/ReMe
agentmemory
cordon
OpenHarness
lm-evaluation-harness
LLMRouter

Lý do không tích hợp trực tiếp sớm:

swe-agent: có repair loop tốt nhưng nặng, không cần vì Claude CLI đã là agent.
langgraph: không cần workflow engine riêng khi Claude CLI tự điều phối.
agent-framework: có skill/schema hay nhưng Claude Code đã có skills.
ReMe/agentmemory: memory nên làm sau.
cordon: log compression nên làm sau.
OpenHarness/lm-eval: benchmark nên làm sau khi skeleton ổn.
LLMRouter: routing riêng chưa cần nếu phase đầu chỉ dùng Claude CLI.
5.3 Manifest third_party

Tạo:

third_party/manifest.yaml

Nội dung:

repos:
  claude_context:
    url: https://github.com/zilliztech/claude-context
    mode: submodule
    purpose: context_search_and_ast_chunking
    phase: 1

  ops_codegraph_tool:
    url: https://github.com/optave/ops-codegraph-tool
    mode: submodule
    purpose: dependency_graph_and_impact
    phase: 1

  sem:
    url: https://github.com/Ataraxy-Labs/sem
    mode: submodule_or_binary
    purpose: semantic_diff_and_patch_impact
    phase: 2

  claw_compactor:
    url: https://github.com/Ataraxy-Labs/claw-compactor
    mode: submodule
    purpose: context_compression
    phase: 2

  secureshell:
    url: https://github.com/divagr18/SecureShell
    mode: submodule_or_reference
    purpose: shell_permission_policy
    phase: 1

  pre_commit:
    url: https://github.com/pre-commit/pre-commit
    mode: dependency
    purpose: validation_hooks
    phase: 1
6. Roadmap triển khai từ đầu
Phase 0: Khởi tạo repo sạch

Mục tiêu: biến repo trống thành project có cấu trúc chuẩn.

Lệnh Claude sẽ được yêu cầu thực hiện:

git clone https://github.com/WindFaculty/Claude_WindFaculty.git
cd Claude_WindFaculty
git checkout -b scaffold/claude-environment-foundation

Tạo file:

README.md
CLAUDE.md
.gitignore
.env.example
LICENSE
.claude/settings.json
.mcp.json
third_party/manifest.yaml
configs/tools.yaml
configs/budgets.yaml
configs/context.yaml
configs/validation.yaml
configs/benchmark.yaml

Validation:

git status
python --version
claude --version

Deliverable:

reports/phase0_foundation.md
Phase 1: Bootstrap environment

Mục tiêu: người dùng clone repo xong có thể setup môi trường bằng 1 lệnh.

Tạo:

scripts/bootstrap/setup.ps1
scripts/bootstrap/setup.sh
scripts/bootstrap/verify_environment.py
scripts/bootstrap/clone_third_party.py

verify_environment.py kiểm tra:

git installed
python installed
node installed nếu cần
claude CLI installed
claude auth usable hoặc ít nhất claude --version chạy được
third_party manifest hợp lệ
.env không commit secret
reports/artifacts directory tồn tại

Không gọi Claude API trong script verify nếu chưa cần.

Kết quả pass:

python scripts/bootstrap/verify_environment.py

Artifact:

artifacts/environment_check.json
reports/environment_check.md
Phase 2: Claude project memory và rules

Mục tiêu: tạo CLAUDE.md đủ mạnh để Claude CLI tự vận hành đúng.

CLAUDE.md nên có các mục:

1. Project mission
2. Claude operating model
3. Required workflow
4. Context policy
5. Tool policy
6. Git policy
7. Testing policy
8. Diff validation policy
9. Report policy
10. Stop conditions

Nội dung lõi:

You are Claude Code operating inside Claude_WindFaculty.
You are the primary coding agent.
Do not delegate execution to another custom agent runtime.
Use the tools and scripts in this repository to improve your own work.
Before editing, inspect task, repo, context, and constraints.
After editing, validate diff, run relevant tests, scan secrets, and write a report.

Stop conditions:

Stop if command is dangerous.
Stop if task requires unavailable credentials.
Stop if selected context is empty.
Stop if patch changes unrelated files.
Stop if tests cannot be run and no explanation is written.
Stop if no diff was produced after claiming success.
Phase 3: Skills

Mục tiêu: chuyển các quy trình hay dùng thành Claude skills.

Tạo skill 1:

.claude/skills/repo-intake/SKILL.md

Dùng khi Claude vào một repo mới.

Output bắt buộc:

artifacts/repo_intake.json
reports/repo_intake.md

Tạo skill 2:

.claude/skills/context-pack/SKILL.md

Dùng trước khi sửa code.

Output:

artifacts/context_candidates.json
artifacts/selected_context.json
artifacts/context_pack.md

Tạo skill 3:

.claude/skills/code-edit/SKILL.md

Dùng khi bắt đầu sửa code.

Rule:

Không sửa file chưa nằm trong selected_context nếu không ghi lý do.
Không refactor rộng nếu task là bugfix nhỏ.
Không format toàn repo.

Tạo skill 4:

.claude/skills/test-repair/SKILL.md

Dùng khi test fail.

Output:

artifacts/test_failure_summary.json
artifacts/repair_plan.json
artifacts/repair_history.json

Tạo skill 5:

.claude/skills/diff-review/SKILL.md

Dùng trước khi kết luận task xong.

Output:

artifacts/diff_review.json
artifacts/patch_acceptance.json

Tạo skill 6:

.claude/skills/benchmark/SKILL.md

Dùng để chạy task benchmark.

Output:

benchmarks/results/<run_id>.json
reports/benchmark_<run_id>.md

Tạo skill 7:

.claude/skills/final-report/SKILL.md

Dùng khi kết thúc mọi task.

Output:

reports/final_<run_id>.md
Phase 4: Subagents

Mục tiêu: tách việc phụ khỏi context chính của Claude.

Tạo:

.claude/agents/context-researcher.md
.claude/agents/test-diagnoser.md
.claude/agents/diff-reviewer.md
.claude/agents/security-reviewer.md
.claude/agents/report-writer.md

Quy tắc:

Main Claude session chỉ giữ quyết định chính.
Subagent đọc nhiều log/context rồi trả summary ngắn.
Subagent không được tự ý sửa code nếu không phải vai trò của nó.

context-researcher:

Tìm file liên quan.
Tìm symbol liên quan.
Tìm test liên quan.
Trả về tối đa 20 file và lý do.

test-diagnoser:

Đọc log test.
Nén lỗi.
Phân loại root cause.
Đề xuất affected tests.

diff-reviewer:

Kiểm tra diff có đúng task không.
Phát hiện unrelated edits, broad refactor, no-op, wrong-file edit.

security-reviewer:

Kiểm tra secret, command nguy hiểm, permission escalation, destructive operation.

report-writer:

Tổng hợp artifact thành báo cáo cuối.
Không bịa kết quả test.
Không nói pass nếu không có log pass.
Phase 5: Hooks và permission

Mục tiêu: ép Claude CLI làm việc an toàn.

Tạo:

.claude/settings.json
scripts/tools/safe_bash.py
scripts/tools/safe_git.py
scripts/validate/validate_diff.py
scripts/validate/validate_secrets.py

Hook cần có:

PreToolUse Bash
PostToolUse Bash
PreToolUse Write
PreToolUse Edit
Stop

Policy command:

allow:
  - git status
  - git diff
  - git log
  - git branch
  - rg
  - grep
  - python -m pytest
  - pytest
  - ruff check
  - mypy
  - npm test
  - npm run lint
  - npm run build

ask:
  - git checkout
  - git restore
  - git clean
  - pip install
  - npm install
  - pnpm install
  - uv sync

deny:
  - rm -rf
  - del /s
  - format
  - shutdown
  - reboot
  - sudo
  - chmod -R 777
  - curl | bash
  - wget | bash
  - git push --force
  - git reset --hard

Artifact sau mỗi command:

artifacts/tool_execution_log.jsonl
artifacts/tool_policy_decisions.jsonl
Phase 6: Context tools

Mục tiêu: giúp Claude chọn đúng context, không gửi whole repo.

Clone/tích hợp:

claude-context
ops-codegraph-tool
sem
claw-compactor

Tạo wrapper:

scripts/context/build_index.py
scripts/context/select_context.py
scripts/context/compress_context.py
scripts/context/summarize_repo.py

Pipeline:

task.md
↓
extract keywords
↓
semantic search bằng claude-context
↓
dependency expansion bằng ops-codegraph
↓
semantic impact bằng sem nếu có diff
↓
compress bằng claw-compactor nếu context quá lớn
↓
ghi context_pack.md

Output:

artifacts/context_query.json
artifacts/context_candidates.json
artifacts/dependency_graph.json
artifacts/selected_context.json
artifacts/context_pack.md
artifacts/context_budget.json

Rule:

Không chọn quá 20 file trong phase đầu.
Không chọn file build/cache/generated.
Ưu tiên source + tests + config liên quan.
Mỗi file được chọn phải có lý do.
Phase 7: Validation tools

Mục tiêu: Claude không được tự kết luận “done” nếu validation thiếu.

Tạo:

scripts/validate/validate_diff.py
scripts/validate/validate_tests.py
scripts/validate/validate_context.py
scripts/validate/validate_report.py
scripts/validate/validate_secrets.py

validate_diff.py kiểm tra:

Có diff không
Có sửa đúng file liên quan không
Có sửa file ngoài task không
Có format toàn repo không
Có file binary/generated không
Có secret không
Có patch quá rộng không

Output:

artifacts/diff_validation.json

Các verdict:

PASS
NO_DIFF
WRONG_FILE_EDIT
TOO_BROAD_DIFF
UNRELATED_CHANGE
GENERATED_FILE_CHANGE
SECRET_RISK
REVIEW_REQUIRED

validate_tests.py kiểm tra:

test command đã chạy chưa
exit code
failed tests
skipped tests
log path

Output:

artifacts/test_validation.json
Phase 8: Report system

Mục tiêu: mọi run đều để lại bằng chứng.

Tạo:

scripts/reports/write_report.py
reports/templates/task_report.md
reports/templates/benchmark_report.md

Report bắt buộc có:

Task
Repo state before
Context selected
Plan
Files changed
Diff summary
Commands run
Test result
Validation result
Risk
Final verdict
Next actions

Không được có câu:

All good
Done
Should be fine
Probably fixed

nếu không có artifact chứng minh.

Final verdict chỉ được là:

PASS
PASS_WITH_WARNINGS
FAIL
SKIPPED
BLOCKED
Phase 9: Benchmark harness

Mục tiêu: đo Claude_WindFaculty có giúp Claude CLI làm tốt hơn không.

Không benchmark quá sớm. Sau khi context + validation + report chạy ổn mới làm.

Cấu trúc:

benchmarks/
├── suites/
│   ├── smoke.yaml
│   ├── bugfix.yaml
│   ├── refactor.yaml
│   └── repo_intake.yaml
├── tasks/
│   ├── task_001.md
│   ├── task_002.md
│   └── task_003.md
├── expected/
└── results/

Metrics:

success_rate
test_pass_rate
no_diff_rate
wrong_file_edit_rate
repair_count
commands_run
runtime_sec
context_files_count
report_completeness

Không cần so với Codex ngay. Trước tiên đo:

Claude CLI raw
vs
Claude CLI + Claude_WindFaculty environment

Sau đó mới so:

Claude CLI + environment
vs
Codex high
vs
manual baseline
7. Phase triển khai cụ thể
Phase 0: Foundation

Mục tiêu:

Repo có cấu trúc chuẩn.
Claude nhận instruction đúng.
Có bootstrap script.
Có settings/hooks rỗng nhưng hợp lệ.
Có manifest third_party.

Deliverables:

CLAUDE.md
.claude/settings.json
.claude/skills/repo-intake/SKILL.md
.claude/skills/final-report/SKILL.md
scripts/bootstrap/verify_environment.py
third_party/manifest.yaml
reports/phase0_foundation.md

Validation:

python scripts/bootstrap/verify_environment.py
git status
Phase 1: Claude-native workflow

Mục tiêu:

Claude có thể chạy theo quy trình chuẩn bằng skill.
Không cần context tool phức tạp.
Không cần clone nhiều repo.

Deliverables:

.claude/skills/context-pack/SKILL.md
.claude/skills/code-edit/SKILL.md
.claude/skills/diff-review/SKILL.md
.claude/skills/test-repair/SKILL.md
.claude/agents/diff-reviewer.md
.claude/agents/test-diagnoser.md

Validation:

Mở Claude CLI trong repo.
Gọi /repo-intake.
Gọi /context-pack với task mẫu.
Gọi /final-report.
Kiểm tra artifact/report có sinh ra không.
Phase 2: Safe tool layer

Mục tiêu:

Claude chạy Bash/Edit/Write nhưng bị kiểm soát.
Command nguy hiểm bị block.
Command quan trọng được log.

Deliverables:

scripts/tools/safe_bash.py
scripts/tools/safe_git.py
scripts/validate/validate_secrets.py
.claude/settings.json hooks
configs/tools.yaml

Validation:

python scripts/tools/safe_bash.py "git status"
python scripts/tools/safe_bash.py "rm -rf ."

Expected:

git status allowed
rm -rf denied
Phase 3: Context stack

Mục tiêu:

Clone repo context về.
Claude có công cụ chọn context tốt hơn grep thường.

Deliverables:

scripts/bootstrap/clone_third_party.py
scripts/context/build_index.py
scripts/context/select_context.py
scripts/context/compress_context.py
third_party/claude-context
third_party/ops-codegraph-tool
third_party/sem
third_party/claw-compactor

Validation:

python scripts/bootstrap/clone_third_party.py --only context
python scripts/context/select_context.py --repo . --task tasks/examples/sample_bug.md

Expected artifacts:

artifacts/context_candidates.json
artifacts/selected_context.json
artifacts/context_pack.md
Phase 4: Diff and test validation

Mục tiêu:

Claude không thể claim success nếu không có diff/test evidence.

Deliverables:

scripts/validate/validate_diff.py
scripts/validate/validate_tests.py
scripts/validate/validate_context.py
configs/validation.yaml
.claude/skills/diff-review/SKILL.md updated

Validation:

python scripts/validate/validate_diff.py --repo .
python scripts/validate/validate_tests.py --command "python -m pytest -q"
Phase 5: Dogfood task

Mục tiêu:

Dùng chính Claude CLI + environment mới để sửa một bug nhỏ trong repo.

Tạo task:

tasks/dogfood/001_fix_validation_bug.md

Yêu cầu Claude:

Dùng /context-pack.
Dùng /code-edit.
Chạy test.
Dùng /diff-review.
Dùng /final-report.

Pass khi có:

artifacts/context_pack.md
artifacts/diff_validation.json
artifacts/test_validation.json
reports/final_<run_id>.md
Phase 6: Benchmark smoke

Mục tiêu:

Có bộ benchmark nhỏ để đo mỗi lần thay đổi.

Deliverables:

benchmarks/suites/smoke.yaml
scripts/benchmark/run_task.py
scripts/benchmark/run_suite.py
scripts/benchmark/score_run.py
.claude/skills/benchmark/SKILL.md

Smoke suite gồm:

repo intake
context selection
safe command policy
diff validation
report generation
8. Cấu hình CLAUDE.md mẫu nên dùng
# Claude_WindFaculty

## Mission

This repository is a Claude CLI operating environment. Claude Code is the primary agent. This project provides instructions, skills, hooks, safe tool wrappers, context tools, validation scripts, benchmark scripts, and reporting templates around Claude Code.

Do not build a separate agent runtime to replace Claude Code.

## Operating model

Claude must use the repository tools to improve its own coding workflow:

1. Read the task.
2. Inspect the repository.
3. Select context.
4. Plan before editing.
5. Edit only relevant files.
6. Run validation.
7. Review the diff.
8. Write a final report.

## Hard rules

Do not send or read the whole repository unless the task explicitly requires it.
Do not run destructive commands.
Do not claim success without test or validation evidence.
Do not treat exit code 0 from any tool as sufficient proof of task success.
Do not modify unrelated files.
Do not format the entire repository unless explicitly requested.
Do not commit secrets.
Do not push forcefully.

## Required artifacts

Every task must produce:

- artifacts/context_candidates.json
- artifacts/selected_context.json
- artifacts/diff_validation.json
- artifacts/test_validation.json
- reports/final_report.md

If an artifact cannot be produced, explain why in the final report.

## Final verdicts

Use only:

- PASS
- PASS_WITH_WARNINGS
- FAIL
- BLOCKED
- SKIPPED