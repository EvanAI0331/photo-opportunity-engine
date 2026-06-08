# SpecX Integration

This project uses the desktop SpecX compiler at:

```text
/Users/xin/Desktop/specx-codex-plugin/scripts/specx_cli.py
```

The local contract source is:

```text
specx/contracts/photo_opportunity_agent.contract.json
```

Compile and verify:

```bash
./scripts/specx_compile.sh
```

Outputs:

```text
specx/compiled/photo_opportunity_agent.verify.json
specx/compiled/photo_opportunity_agent.compiled.json
specx/compiled/photo_opportunity_agent.explain.json
```

Rules:

- The source contract defines the LLM-backed agent role, execution, and output specs.
- The compiled plan must come from SpecX CLI output.
- Failed verification is a real failure.
- Do not hand-edit compiled outputs as success evidence.
- Script-only modules are tools, not agents.
