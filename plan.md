Kế hoạch chi tiết tích hợp everything-claude-code vào Claude_WindFaculty
Phase 0 — Khóa baseline đúng commit

Mục tiêu: đảm bảo mọi thay đổi bắt đầu từ đúng commit bạn đưa.

Chạy:

git clone https://github.com/WindFaculty/Claude_WindFaculty.git
cd Claude_WindFaculty
git checkout 2b2e28b0f762831f55fe881cd3bc6d81dc8551e9
git checkout -b feature/integrate-everything-claude-code
git status --short
git rev-parse HEAD

Tạo report:

reports/ecc_baseline_20260531.md

Nội dung:

# Everything Claude Code Integration Baseline

Repo: WindFaculty/Claude_WindFaculty
Base commit: 2b2e28b0f762831f55fe881cd3bc6d81dc8551e9
Integration target: WorldFlowAI/everything-claude-code
Integration mode: vendored source + selected project-level Claude config
Do not overwrite existing safe_bash.py without adapter/audit.

Tiêu chí pass:

HEAD == 2b2e28b0f762831f55fe881cd3bc6d81dc8551e9
working tree clean
branch = feature/integrate-everything-claude-code
Phase 1 — Vendor everything-claude-code

Mục tiêu: tải repo về thay vì viết lại.

Khuyến nghị dùng git subtree, không dùng submodule.

Lý do: submodule dễ lỗi khi agent/Claude/Codex chạy trong môi trường chưa init submodule. Subtree làm source nằm thật trong repo, dễ đọc, dễ diff, dễ rollback.

Chạy:

mkdir -p third_party
git subtree add \
  --prefix=third_party/everything-claude-code \
  https://github.com/WorldFlowAI/everything-claude-code.git \
  main \
  --squash

Nếu git subtree không khả dụng, dùng fallback:

mkdir -p third_party
git clone https://github.com/WorldFlowAI/everything-claude-code.git third_party/everything-claude-code
rm -rf third_party/everything-claude-code/.git

Tạo file:

third_party/everything-claude-code/VENDORING_WF.md

Nội dung:

# Vendoring Notes

Source: https://github.com/WorldFlowAI/everything-claude-code.git
Imported into: third_party/everything-claude-code
Mode: subtree or vendored copy
Reason: keep Claude_WindFaculty reproducible and avoid global ~/.claude mutation
Policy: do not edit vendored files directly unless patch is documented

Tiêu chí pass:

third_party/everything-claude-code/README.md exists
third_party/everything-claude-code/agents exists
third_party/everything-claude-code/skills exists
third_party/everything-claude-code/commands exists
third_party/everything-claude-code/rules exists
Phase 2 — Audit nội dung trước khi copy

Mục tiêu: không đưa toàn bộ vào .claude ngay.

Tạo script:

scripts/integrations/ecc/audit_ecc_inventory.py

Script này đọc cây:

third_party/everything-claude-code/agents
third_party/everything-claude-code/skills
third_party/everything-claude-code/commands
third_party/everything-claude-code/rules
third_party/everything-claude-code/hooks
third_party/everything-claude-code/mcp-configs

và xuất:

reports/ecc_inventory_20260531.md
reports/ecc_inventory_20260531.json

Báo cáo cần chia nhóm:

SAFE_TO_COPY
NEEDS_REVIEW
DO_NOT_ENABLE_YET

Quy tắc phân loại ban đầu:

agents/*.md                         SAFE_TO_COPY
commands/*.md                       SAFE_TO_COPY
rules/*.md                          SAFE_TO_COPY, nhưng cần merge không ghi đè
skills/coding-standards             SAFE_TO_COPY
skills/tdd-workflow                 SAFE_TO_COPY
skills/security-review              SAFE_TO_COPY
skills/verification-loop            SAFE_TO_COPY
skills/eval-harness                 SAFE_TO_COPY
skills/continuous-learning          NEEDS_REVIEW
skills/strategic-compact            NEEDS_REVIEW
hooks/*                             NEEDS_REVIEW
scripts/hooks/*                     NEEDS_REVIEW
mcp-configs/*                       DO_NOT_ENABLE_YET
contexts/*                          NEEDS_REVIEW

Lý do không bật MCP ngay: README cảnh báo context window có thể giảm mạnh nếu bật nhiều MCP/tool.

Tiêu chí pass:

inventory report created
no project .claude files modified yet
all hook/mcp entries marked review-first
Phase 3 — Copy chọn lọc agents/commands/skills/rules vào project .claude

Mục tiêu: dùng project-level config, không động vào global ~/.claude.

Tạo thư mục:

mkdir -p .claude/agents
mkdir -p .claude/commands
mkdir -p .claude/skills
mkdir -p .claude/rules
mkdir -p .claude/ecc

Copy nhóm an toàn:

cp third_party/everything-claude-code/agents/*.md .claude/agents/
cp third_party/everything-claude-code/commands/*.md .claude/commands/
cp third_party/everything-claude-code/rules/*.md .claude/rules/

Copy skills chọn lọc:

cp -r third_party/everything-claude-code/skills/coding-standards .claude/skills/
cp -r third_party/everything-claude-code/skills/backend-patterns .claude/skills/
cp -r third_party/everything-claude-code/skills/tdd-workflow .claude/skills/
cp -r third_party/everything-claude-code/skills/security-review .claude/skills/
cp -r third_party/everything-claude-code/skills/eval-harness .claude/skills/
cp -r third_party/everything-claude-code/skills/verification-loop .claude/skills/

Không copy vội:

mcp-configs/
hooks/hooks.json
scripts/hooks/
continuous-learning/
strategic-compact/

Tạo manifest:

.claude/ecc/selected_components.json

Ví dụ:

{
  "source": "WorldFlowAI/everything-claude-code",
  "mode": "project-level-selected-copy",
  "agents": "all",
  "commands": "all",
  "rules": "all",
  "skills": [
    "coding-standards",
    "backend-patterns",
    "tdd-workflow",
    "security-review",
    "eval-harness",
    "verification-loop"
  ],
  "hooks": "not-enabled-yet",
  "mcp": "not-enabled-yet"
}

Tiêu chí pass:

.claude/agents populated
.claude/commands populated
.claude/rules populated
.claude/skills selected only
existing .claude/settings.json preserved except planned changes
Phase 4 — Merge rules vào CLAUDE.md hoặc project instruction

Mục tiêu: Claude_WindFaculty có instruction nền rõ ràng.

Tạo hoặc cập nhật:

CLAUDE.md

Nội dung nên ngắn, không nhồi toàn bộ rules vào system prompt.

Ví dụ:

# Claude_WindFaculty Project Instructions

This project uses selected components from everything-claude-code.

Before coding:
1. Prefer planning through `.claude/commands/plan.md`.
2. Use TDD when touching executable code.
3. Run relevant verification before final response.
4. Respect `.claude/rules/security.md`.
5. Do not bypass `scripts/tools/safe_bash.py`.
6. Do not enable MCP servers unless explicitly requested.
7. Keep changes small and reviewable.

For complex tasks:
1. Use planner or architect agent first.
2. Use code-reviewer/security-reviewer before finalizing.
3. Use verification-loop skill before claiming completion.

Không nên paste toàn bộ contents của rules vào CLAUDE.md, vì sẽ đốt context. Chỉ reference file.

Tiêu chí pass:

CLAUDE.md exists
references selected ECC components
does not duplicate huge rules
preserves safe_bash policy
Phase 5 — Tích hợp commands

Mục tiêu: làm slash commands của everything-claude-code dùng được trong project.

Các command nên ưu tiên test trước:

/plan
/tdd
/verify
/code-review
/build-fix
/checkpoint
/learn

README xác nhận repo có các commands này trong commands/.

Cần tạo test thủ công:

reports/ecc_command_smoke_20260531.md

Checklist:

# ECC Command Smoke

- /plan loads
- /tdd loads
- /verify loads
- /code-review loads
- /build-fix loads
- /checkpoint loads
- /learn loads

Nếu Claude Code không nhận project-level commands, fallback là copy sang .claude/commands đúng format hoặc thêm hướng dẫn trong CLAUDE.md.

Tiêu chí pass:

commands visible to Claude Code
commands do not require MCP by default
commands do not bypass safe_bash
Phase 6 — Tích hợp agents nhưng kiểm soát model

Mục tiêu: dùng subagents nhưng không để đốt token mất kiểm soát.

README mô tả agents như subagents chuyên trách, ví dụ code-reviewer, security-reviewer, planner, architect.

Vấn đề: một số agent có thể khai báo model mạnh như opus. README ví dụ agent có field:

model: opus

Với ngân sách của bạn, không nên để default opus.

Cần tạo script audit:

scripts/integrations/ecc/audit_agent_models.py

Nhiệm vụ:

scan .claude/agents/*.md
find "model:"
report agents using opus/sonnet
recommend cheaper model or inherit default

Chính sách đề xuất:

planner              haiku / default
architect            sonnet only for complex design
tdd-guide            haiku / default
code-reviewer        haiku first, sonnet on high-risk
security-reviewer    sonnet if security-sensitive
build-error-resolver haiku first
e2e-runner           haiku/default
doc-updater          haiku/default
refactor-cleaner     haiku/default

Không sửa bừa model nếu chưa biết Claude CLI của bạn hỗ trợ model alias nào. Cách an toàn: bỏ model: khỏi agent để kế thừa default, hoặc đổi về alias hợp lệ trong Claude Code của bạn.

Tiêu chí pass:

agent model audit report created
no accidental opus default
planner/code-reviewer/security-reviewer available
Phase 7 — Hook integration không ghi đè safe_bash

Đây là phase quan trọng nhất.

Repo everything-claude-code có hooks/hooks.json và scripts/hooks/* theo README. Nhưng Claude_WindFaculty hiện đã có:

"PreToolUse": [
  {
    "tools": ["Bash"],
    "run": "python scripts/tools/safe_bash.py"
  }
]

Không được thay thẳng bằng hook của everything-claude-code.

Cần tạo adapter:

scripts/integrations/ecc/ecc_hook_bridge.py

Vai trò:

Claude PreToolUse Bash
  -> ecc_hook_bridge.py
  -> safe_bash.py
  -> optional everything-claude-code hook
  -> audit log

Giai đoạn đầu giữ nguyên behavior:

{
  "hooks": {
    "PreToolUse": [
      {
        "tools": ["Bash"],
        "run": "python scripts/integrations/ecc/ecc_hook_bridge.py --tool Bash --delegate scripts/tools/safe_bash.py"
      }
    ]
  }
}

Bridge cần làm:

Nhận stdin từ Claude hook.
Ghi raw input đã sanitize vào log.
Gọi safe_bash.py.
Nếu safe_bash.py block thì block luôn.
Nếu pass thì cho phép.
Không gọi Node hook của everything-claude-code trong phase đầu.

Audit log:

logs/ecc/hooks.jsonl

Record:

{
  "event": "PreToolUse",
  "tool": "Bash",
  "delegate": "scripts/tools/safe_bash.py",
  "decision": "allow|block",
  "timestamp": "...",
  "source": "Claude_WindFaculty+everything-claude-code"
}

Tiêu chí pass:

existing Bash protection preserved
bridge logs decision
safe_bash remains source of truth
everything hooks not enabled blindly
Phase 8 — Node.js compatibility check

everything-claude-code dùng Node.js scripts cho hook cross-platform. README nói scripts đã rewrite sang Node.js để hỗ trợ Windows/macOS/Linux.

Cần thêm check:

scripts/integrations/ecc/check_node_runtime.py

Hoặc đơn giản trong report:

node --version
npm --version

Nếu repo có tests:

cd third_party/everything-claude-code
node tests/run-all.js

README xác nhận test command là:

node tests/run-all.js

Tiêu chí pass:

node available or documented missing
everything-claude-code tests pass or skipped with reason
no hook depends on missing package manager
Phase 9 — Package manager detection

Repo everything-claude-code có logic phát hiện package manager theo thứ tự:

CLAUDE_PACKAGE_MANAGER
.claude/package-manager.json
package.json field packageManager
lock files
global config
fallback package manager

README ghi rõ các lệnh setup package manager.

Với Claude_WindFaculty, nên tạo:

.claude/package-manager.json

Nếu dự án chủ yếu Python, không cần ép npm. Nhưng vì ECC scripts là Node, nên nên đặt:

{
  "packageManager": "npm"
}

hoặc nếu bạn dùng pnpm:

{
  "packageManager": "pnpm"
}

Khuyến nghị thực tế: dùng npm trước cho đơn giản trên Windows.

Tiêu chí pass:

.claude/package-manager.json exists
setup-pm command does not override project unexpectedly
Phase 10 — MCP configs: chỉ vendor, chưa bật

Repo có:

mcp-configs/mcp-servers.json

README nói có MCP cho GitHub, Supabase, Vercel, Railway, v.v.

Không bật ngay.

Tạo:

.claude/ecc/mcp_allowlist.json

Ban đầu:

{
  "enabled": [],
  "available_from_vendor": "third_party/everything-claude-code/mcp-configs/mcp-servers.json",
  "policy": "Do not enable MCP servers without explicit project need and API key review."
}

Khi cần mới bật từng cái:

GitHub MCP: có ích cho repo operations
Filesystem MCP: rủi ro cao, chỉ bật nếu sandbox rõ
Browser/Playwright MCP: chỉ bật khi cần test UI
Cloud MCP: không bật nếu chưa có key/quota

Tiêu chí pass:

mcp config vendored
no MCP auto-enabled
API key placeholders not copied into active config
Phase 11 — Continuous learning và strategic compact

Repo có skills/hook cho:

continuous-learning
strategic-compact
memory-persistence

README mô tả memory persistence, continuous learning, strategic compact, verification loops là các phần quan trọng.

Không bật tự động ngay vì:

Có thể ghi file ngoài ý muốn.
Có thể tích lũy memory rác.
Có thể làm Claude dùng context cũ sai.
Có thể đốt token nếu compact/summarize không kiểm soát.

Làm theo 2 bước:

11.1 Manual mode

Copy skills nhưng không hook:

cp -r third_party/everything-claude-code/skills/continuous-learning .claude/skills/
cp -r third_party/everything-claude-code/skills/strategic-compact .claude/skills/

Thêm vào manifest:

{
  "continuous_learning": "manual-only",
  "strategic_compact": "manual-only"
}
11.2 Auto mode sau khi test

Chỉ bật hook sau khi có:

logs path rõ ràng
max file size
secret sanitizer
rollback policy

Tiêu chí pass:

manual learning command usable
no automatic memory write before approval
Phase 12 — Verification workflow

Mục tiêu: biến /verify và verification-loop thành quy trình test thật cho Claude_WindFaculty.

Tạo file:

.claude/ecc/verification_profile.md

Nội dung:

# Claude_WindFaculty Verification Profile

Minimum checks:
1. Validate JSON files:
   python -m json.tool .claude/settings.json

2. Validate Python scripts:
   python -m py_compile scripts/tools/safe_bash.py
   python -m py_compile scripts/integrations/ecc/ecc_hook_bridge.py

3. Run everything-claude-code tests if Node is available:
   cd third_party/everything-claude-code
   node tests/run-all.js

4. Check no active MCP secrets:
   search for YOUR_*_HERE placeholders in active config

5. Check hook schema:
   .claude/settings.json must use PreToolUse array schema.

Tiêu chí pass:

/verify knows project-specific checks
safe_bash still compiles
settings.json valid
vendor tests attempted
Cấu trúc repo sau tích hợp

Kỳ vọng sau các phase đầu:

Claude_WindFaculty/
  CLAUDE.md
  .claude/
    settings.json
    package-manager.json
    agents/
      planner.md
      architect.md
      code-reviewer.md
      security-reviewer.md
      ...
    commands/
      plan.md
      tdd.md
      verify.md
      code-review.md
      build-fix.md
      checkpoint.md
      learn.md
      ...
    rules/
      security.md
      coding-style.md
      testing.md
      git-workflow.md
      agents.md
      performance.md
    skills/
      coding-standards/
      backend-patterns/
      tdd-workflow/
      security-review/
      eval-harness/
      verification-loop/
    ecc/
      selected_components.json
      mcp_allowlist.json
      verification_profile.md
  scripts/
    tools/
      safe_bash.py
    integrations/
      ecc/
        audit_ecc_inventory.py
        audit_agent_models.py
        ecc_hook_bridge.py
        check_node_runtime.py
  third_party/
    everything-claude-code/
      README.md
      agents/
      skills/
      commands/
      rules/
      hooks/
      scripts/
      tests/
      mcp-configs/
      VENDORING_WF.md
  reports/
    ecc_baseline_20260531.md
    ecc_inventory_20260531.md
    ecc_command_smoke_20260531.md
Những phần nên tích hợp ngay
Nên tích hợp ngay
agents/planner.md
agents/architect.md
agents/code-reviewer.md
agents/security-reviewer.md
agents/build-error-resolver.md
agents/tdd-guide.md

commands/plan.md
commands/tdd.md
commands/verify.md
commands/code-review.md
commands/build-fix.md
commands/checkpoint.md

rules/security.md
rules/coding-style.md
rules/testing.md
rules/git-workflow.md
rules/performance.md

skills/tdd-workflow
skills/security-review
skills/verification-loop
skills/eval-harness
skills/coding-standards
Chỉ vendor, chưa bật
hooks/
scripts/hooks/
mcp-configs/
continuous-learning auto hooks
memory-persistence auto hooks
strategic-compact auto hooks
Không nên làm
Không copy vào ~/.claude ngay
Không bật toàn bộ MCP
Không ghi đè safe_bash.py
Không cho agent default dùng opus nếu chưa kiểm soát quota
Không paste toàn bộ rules vào CLAUDE.md
Không sửa trực tiếp third_party/everything-claude-code nếu chưa có patch note