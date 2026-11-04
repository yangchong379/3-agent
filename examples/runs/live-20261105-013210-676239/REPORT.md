# 实际运行评估报告

模式：live_model；场景14/14通过。

离线Mock只验证流程；实际远端模型决策只能由live记录证明。每组目录保存输入、原始文档、实际输出及Trace。

| 场景 | 预期 | 实际 | 断言 | 输出及Trace |
|---|---|---|---|---|
| normal | answered | answered | PASS | [result](normal/result.json) |
| conflict | conflict | conflict | PASS | [result](conflict/result.json) |
| outside | out_of_scope | out_of_scope | PASS | [result](outside/result.json) |
| paraphrase | conflict | conflict | PASS | [result](paraphrase/result.json) |
| context | answered | answered | PASS | [result](context/result.json) |
| scope | needs_info | needs_info | PASS | [result](scope/result.json) |
| read_retry | answered | answered | PASS | [result](read_retry/result.json) |
| tool_failure | tool_failed | tool_failed | PASS | [result](tool_failure/result.json) |
| single_document | answered | answered | PASS | [result](single_document/result.json) |
| replaced_document | answered | answered | PASS | [result](replaced_document/result.json) |
| permissions | answered | answered | PASS | [result](permissions/result.json) |
| process | answered | answered | PASS | [result](process/result.json) |
| unsupported_detail | out_of_scope | out_of_scope | PASS | [result](unsupported_detail/result.json) |
| step_limit | incomplete_step_limit | incomplete_step_limit | PASS | [result](step_limit/result.json) |

源码摘要：`378149c88cc23bf639abc154a0320d91dabfae12c2ae11a0430ce071953201d5`
