# PKUAutoElective 2022 Spring

这是一个针对北京大学旧版选课系统的自动补选工具。仓库最初写于 2021–2022 年；当前版本补齐了运行依赖、缺失的验证码对象、现代 Python/NumPy/Flask 兼容性、配置检查，以及 TT 识图目前使用的 HTTPS `/predict` 接口。

> 注意：自动选课可能不符合学校当前规定，选课网站也可能已经改版。运行前请确认你有权使用，并以北京大学教务部和选课系统当前规则为准。程序会把 IAAA 凭据交给北大登录接口，并把验证码图片交给第三方 TT 识图；请自行评估账号、隐私、封禁和付费风险。

## 1. 安装

需要 Python 3.10 或更高版本。Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果 PowerShell 禁止运行激活脚本，可以不激活环境，直接使用：

```powershell
.\.venv\Scripts\python.exe main.py --help
```

macOS/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 2. 配置

项目根目录下需要两个私密文件，它们已加入 `.gitignore`：

- `config.ini`：IAAA 账号、运行参数、目标课程和规则。
- `apikey.json`：TT 识图账号和请求参数。

仓库中已经生成了带占位符的这两个文件。不要把真实密码提交到 Git，也不要把文件内容发给他人。

### `config.ini`

先填写账号：

```ini
[user]
student_id = 你的学号
password = 你的 IAAA 密码
dual_degree = false
identity = bzx
```

`dual_degree = true` 时，`identity = bzx` 表示主修身份，`identity = bfx` 表示辅双身份。普通账号保持示例值即可。

再添加目标课程。课程名、班号、开课单位必须和选课系统完全一致：

```ini
[course:algo]
name = 算法设计与分析
class = 1
school = 信息科学技术学院

[course:database]
name = 数据库概论
class = 2
school = 信息科学技术学院
```

方括号中的 `algo`、`database` 是自定义 ID。课程在配置文件里从上到下排列，越靠前优先级越高。

可选的互斥规则：

```ini
[mutex:choose_one]
courses = algo,database
```

这表示选中其中一门后忽略另一门。可选的延迟规则：

```ini
[delay:algo_quota]
course = algo
threshold = 10
```

这表示只有 `algo` 的剩余名额不超过 10 时才提交选课。

常用运行参数：

- `refresh_interval`：每轮刷新后的基础等待秒数，默认 8。
- `random_deviation`：随机偏移比例；`0.2` 表示实际间隔在基础值上下 20% 浮动。
- `elective_client_pool_size`：并行登录会话数，代码限制为 1–5；建议保持 1 或 2。
- `supply_cancel_pages`：目标课程所在的补退选计划页码；跨页时用逗号分隔，例如 `1,2`。旧的 `supply_cancel_page` 单页配置仍兼容。
- `debug_print_request` / `debug_dump_request`：仅排错时开启，日志可能含敏感信息。

微信推送默认关闭。旧代码使用 `sre24.com`，该服务的当前可用性未在本项目中保证：

```ini
[notification]
disable_push = true
token = TOKEN_HERE
verbosity = 1
minimum_interval = -1
```

### `apikey.json`

按 [TT 识图 API 文档](https://www.ttshitu.com/docs/index.html) 注册后填写：

```json
{
  "username": "你的 TT 识图账号",
  "password": "你的 TT 识图密码",
  "RecognitionTypeid": "1003",
  "Timeout": "60"
}
```

当前投票识别器会并发调用类型 `3`、`1003` 和 `7`，因此一次验证码可能产生三次第三方计费请求。
验证码连续校验失败时最多尝试 15 次；达到上限后，该课程会在本次程序运行中被忽略，避免后续刷新继续产生识图费用。重新启动程序会清除这一临时忽略状态。

## 3. 离线检查

填写完成后先运行：

```powershell
python main.py --check-config
```

检查只读取本地文件，不登录、不识图，也不提交选课。成功时会显示课程数和规则数。也可指定其他配置：

```powershell
python main.py -c .\my-config.ini -a .\my-apikey.json --check-config
```

## 4. 运行

普通运行：

```powershell
python main.py
```

同时启动只监听本机的状态接口：

```powershell
python main.py --with-monitor
```

默认监控地址为 `http://127.0.0.1:7074`，可用接口包括：

- `/stat/loop`：循环和线程状态。
- `/stat/course`：目标、当前和已忽略课程。
- `/stat/error`：错误计数。

按 `Ctrl+C` 停止程序。日志写入 `log/`，缓存写入 `cache/`；两者均不会提交到 Git。

## 5. 常见问题

- `Configuration error`：根据提示修改 `config.ini` 或 `apikey.json`，再运行 `--check-config`。
- 提示课程不在选课计划：核对课程名、班号、开课单位以及 `supply_cancel_pages`。
- 登录持续失败：先在浏览器验证 IAAA 密码，并确认选课系统当前仍兼容本项目的旧接口。
- 验证码识别失败：检查 TT 识图账号余额、识别类型和网络；第三方官方文档建议超时设为 60 秒。
- 学校页面结构变化导致 `[104] unable to parse HTML content`：这通常不是本地配置问题，而是旧解析器与当前页面不兼容。

## 许可证

[MIT License](LICENSE)
