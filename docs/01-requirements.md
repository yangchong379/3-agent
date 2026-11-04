# 01 需求与成功标准

用户是需要制度或产品依据的员工。输入问题及可选历史；交付answer、citations（文档ID/日期/范围/原文字符区间）、data_gaps、status与逐步Trace。

成功标准：有据才答；模糊范围需追问；冲突需引用双方且不擅定优先级；资料外问题补查后承认不足；工具失败保留已有读取记录；步数有限且不能虚称完成。仅合成文档，无真实隐私或凭据。

| 必验收点 | 实际证据 |
|---|---|
| 明确答案 | [normal](../examples/runs/mock/normal/result.json) |
| 文档冲突 | [conflict](../examples/runs/mock/conflict/result.json)，D01/D02原文均引用，含分页补查 |
| 资料外问题 | [outside](../examples/runs/mock/outside/result.json)，两次不同查询后停止 |
| 改写相似问题 | [paraphrase](../examples/runs/mock/paraphrase/result.json)，垫付/交票等同义词仍发现冲突 |
| 上下文追问 | [context首轮](../examples/runs/mock/context/first_run.json)、[追问](../examples/runs/mock/context/result.json)，标准版转专业版 |
| 工具失败 | [read_retry](../examples/runs/mock/read_retry/result.json)、[tool_failure](../examples/runs/mock/tool_failure/result.json) |
| 替换资料后答案改变 | [single](../examples/runs/mock/single_document/result.json)30天与[replace](../examples/runs/mock/replaced_document/result.json)45天；原输入和数据同目录 |

不要求UI、上线或多Agent。成功不等于所有输入都返回answered；conflict、needs_info与out_of_scope可以是正确处理结果。
