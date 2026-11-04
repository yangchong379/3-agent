# 企业知识问答 Agent · 题目3

为员工提供可追溯的制度或产品答案，包含文档ID、版本日期、逐字原文、资料缺口和任务状态。独立仓库：[yangchong379/3-agent](https://github.com/yangchong379/3-agent)。

当前实际验证：**30个自动化测试通过，14/14离线场景通过**。真实模型入口已实现，本轮真实模型已执行（详见新增实际记录），不能将Mock当作真实模型决策效果。

Python 3.11+、标准库，无Agent框架、无第三方运行依赖。可直接执行（Windows将python换成py -3.11）：

```bash
python scripts/run.py --input examples/inputs/normal.json --output .runtime/answer.json
python scripts/run.py --input examples/inputs/conflict.json --output .runtime/conflict.json
python -m unittest discover -s tests -v
python scripts/evaluate.py --output .runtime/recheck
```

每次评估选择新目录保留旧证据。正常CLI退出0，资料外/冲突/追问/工具失败退出2，模型错误或步数上限退出3，输入配置错误退出4。可选安装`python -m pip install -e .`后用`knowledge-agent`。

评审入口：[需求](docs/01-requirements.md)、[方案](docs/02-solution.md)、[预期/实际/失败限制](docs/03-evaluation.md)、[AI使用](docs/04-ai-usage.md)、[复盘用时](docs/05-retrospective.md)、[实际离线报告](examples/runs/mock/REPORT.md)、[实际测试结果](examples/runs/mock/tests.txt)。

输入示例：

```json
{"request_id":"employee-001","question":"报销期限多久？","history":[]}
```

history为可选的user/assistant消息列表，最多10条。只有用户历史用于解析“那专业版呢”等追问；任何历史回答均不能充当制度证据。每次问答重新检索当前文档，无跨用户记忆或缓存。

真实模型运行（本机密码窗口输入密钥，不发到聊天）：

```powershell
py -3.11 scripts/connect_deepseek.py --evaluate
py -3.11 scripts/connect_deepseek.py --retry-failed
```

也可配置`.env.example`列出的MODEL_BASE_URL、MODEL_NAME、MODEL_API_KEY、MODEL_THINKING后用`--model live`；不会自动加载.env。默认DeepSeek工具调用，HTTPS适配器复用前一项目通用逻辑，工具协议和Agent独立。模型每轮实际选择动作，观察工具结果，再决定补检索、读原文或respond；默认24步，可设1–100，超限明确未完成，不回退Mock。

本项目采用**有限条款格式与抽取式回答**：合成文档每行一个可解析条款，例如“报销期限为30天。”。检索使用主题同义词、词项和分页，无向量库；引用必须来自实际read_document。模型选择查询、原文读取、引用与结束状态；服务端复核并输出原文，不允许自由补写无法验证的事实。支持报销期限、年假额度、两档产品导出上限、删除权限、请假流程；普通长文、表格、多制度例外及任意知识问答未实现。

D01为30天、D02为15天且均有效、无优先级，即使D02日期较新仍列出冲突；不会挑15天。D09有明确inactive标记才排除。文档含恶意指令的测试文本不作为指令执行。资料缺口与短解释可能不完美，不能据此宣称生产可靠性。

真实公司认证、权限分级、租户隔离、外部文档更新、语义蕴含判断、生产检索质量和内容注入全面防护不在范围。所有制度和产品规则为合成资料，不构成真实公司政策。

## 本轮真实模型记录

真实模型业务断言14/14通过。[实际原始结果与AI复核](examples/runs/live-20261105-013210-676239/REVIEW.md)。运行代码和数据边界不变，失败不改写；实际状态与质量限制以该报告为准。
