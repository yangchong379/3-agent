# 03 预期、实际结果与失败限制

本机Python 3.11.4，实际运行30个自动化测试通过，14/14离线场景通过。[原始报告](../examples/runs/mock/REPORT.md)、[summary](../examples/runs/mock/summary.json)、[tests](../examples/runs/mock/tests.txt)。每组目录保存input、dataset与result，result含模型动作/参数/工具观察/下一步Trace。至少明确答案、资料不足、工具失败均有实际材料。

| 场景 | 预期 | 实际 | 检查 | 证据 |
|---|---|---|---|---|
| normal | answered | answered | PASS | [input](../examples/runs/mock/normal/input.json) · [result](../examples/runs/mock/normal/result.json) |
| conflict | conflict | conflict | PASS | [input](../examples/runs/mock/conflict/input.json) · [result](../examples/runs/mock/conflict/result.json) |
| outside | out_of_scope | out_of_scope | PASS | [input](../examples/runs/mock/outside/input.json) · [result](../examples/runs/mock/outside/result.json) |
| paraphrase | conflict | conflict | PASS | [input](../examples/runs/mock/paraphrase/input.json) · [result](../examples/runs/mock/paraphrase/result.json) |
| context | answered | answered | PASS | [input](../examples/runs/mock/context/input.json) · [result](../examples/runs/mock/context/result.json) |
| scope | needs_info | needs_info | PASS | [input](../examples/runs/mock/scope/input.json) · [result](../examples/runs/mock/scope/result.json) |
| read_retry | answered | answered | PASS | [input](../examples/runs/mock/read_retry/input.json) · [result](../examples/runs/mock/read_retry/result.json) |
| tool_failure | tool_failed | tool_failed | PASS | [input](../examples/runs/mock/tool_failure/input.json) · [result](../examples/runs/mock/tool_failure/result.json) |
| single_document | answered | answered | PASS | [input](../examples/runs/mock/single_document/input.json) · [result](../examples/runs/mock/single_document/result.json) |
| replaced_document | answered | answered | PASS | [input](../examples/runs/mock/replaced_document/input.json) · [result](../examples/runs/mock/replaced_document/result.json) |
| permissions | answered | answered | PASS | [input](../examples/runs/mock/permissions/input.json) · [result](../examples/runs/mock/permissions/result.json) |
| process | answered | answered | PASS | [input](../examples/runs/mock/process/input.json) · [result](../examples/runs/mock/process/result.json) |
| unsupported_detail | out_of_scope | out_of_scope | PASS | [input](../examples/runs/mock/unsupported_detail/input.json) · [result](../examples/runs/mock/unsupported_detail/result.json) |
| step_limit | incomplete_step_limit | incomplete_step_limit | PASS | [input](../examples/runs/mock/step_limit/input.json) · [result](../examples/runs/mock/step_limit/result.json) |

测试逐项核对引用文档实际读取、版本日期一致、原文[start:end]逐字吻合、inactive文档不引用、D01/D02冲突双方出现、替换条款后30变45、历史助手说“无限制”不能覆盖专业版30分钟、分页确实读取、工具失败/协议拒绝/步数上限明确反馈。模型适配器HTTP模拟测试只验证协议，不证明远端模型效果。

开发首轮发现资料外问题一次检索后误返回needs_info；修正为明确的资料外问题需两种查询再out_of_scope，同时保留无上下文的“那多久呢”为needs_info。修正后重新执行，当前结果见上述文件，未伪造真实模型日志。

真实API评估当前未执行；14组Mock只能证明流程和保护逻辑。真实模型可能未能查全、引用集合被拒或耗尽步数。框架未使用，无框架版本需要声明。候选人可运行README命令并在live新目录追加实际记录；失败不得删除。

已知限制：有限语法可能漏读普通自然语言或表格事实；主题/意图规则只覆盖五类条款，不能证明“所有资料外问题都判对”。词项检索与全候选原文读取在小资料集可解释，在大文档库成本高。字符串引用校验保证原文一致，不能证明任意原文语义支持；本项目用受限语法和抽取式输出缩小边界。没有真实用户权限、ACL、租户隔离或线上延迟质量评估。
