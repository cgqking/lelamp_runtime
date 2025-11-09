# LeLamp 运行时

![](./assets/images/Banner.png)

此仓库包含用于控制 LeLamp 的运行时代码。运行时提供了对机器人台灯的全面控制系统，包括电机控制、录制/回放功能、语音交互和测试能力。

[LeLamp](https://github.com/humancomputerlab/LeLamp) 是一个基于 [Apple 的 Elegnt](https://machinelearning.apple.com/research/elegnt-expressive-functional-movement) 开源的机器人台灯，由 [[Human Computer Lab]](https://www.humancomputerlab.com/) 制作。

## 概览

LeLamp 运行时是基于 Python 的控制系统，负责与 LeLamp 的硬件组件交互，包括：

- 用于关节运动的舵机电机
- 音频系统（麦克风和扬声器）
- RGB LED 灯光
- 摄像头系统
- 语音交互功能

## 项目结构

```
lelamp_runtime/
├── main.py                 # 主运行入口
├── pyproject.toml         # 项目配置与依赖
├── lelamp/                # 核心包
│   ├── setup_motors.py    # 电机配置与设置
│   ├── calibrate.py       # 电机校准工具
│   ├── list_recordings.py # 列出所有录制的动作
│   ├── record.py          # 动作录制功能
│   ├── replay.py          # 动作回放功能
│   ├── follower/          # Follower 模式相关实现
│   ├── leader/            # Leader 模式相关实现
│   └── test/              # 硬件测试模块
└── uv.lock               # 依赖锁文件
```

## 安装

### 前置要求

- 安装 UV 包管理器
- 硬件组件已正确组装（详情见主 LeLamp 文档）

### 设置

1. 克隆运行时仓库：

```bash
git clone https://github.com/humancomputerlab/lelamp_runtime.git
cd lelamp_runtime
```

2. 安装 UV（如果尚未安装）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. 安装依赖：

```bash
# 如果在个人电脑上运行
uv sync

# 如果在树莓派上运行
uv sync --extra hardware
```

**注意**：对于电机设置和控制，LeLamp 运行时可以在你的电脑上运行，仅需执行 `uv sync` 即可。对于连接到 head Pi 的其他功能（例如 LED 控制、音频、摄像头），需要在对应的树莓派上安装运行并执行 `uv sync --extra hardware`。

如果遇到 LFS（Git Large File Storage）相关问题，请运行：

```bash
GIT_LFS_SKIP_SMUDGE=1 uv sync
```

如果安装过程较慢，可以使用下面的环境变量来加速：

```bash
export UV_CONCURRENT_DOWNLOADS=1
```

### 依赖

运行时包含几个关键依赖：

- **feetech-servo-sdk**：用于舵机电机控制
- **lerobot**：机器人框架集成
- **livekit-agents**：实时语音交互
- **numpy**：数值计算
- **sounddevice**：音频输入/输出
- **adafruit-circuitpython-neopixel**：RGB LED 控制（硬件）
- **rpi-ws281x**：Raspberry Pi LED 控制（硬件）

## 核心功能

在继续之前，建议先阅读本项目的控制教程：[LeLamp 控制指南](https://github.com/humancomputerlab/LeLamp/blob/master/docs/5.%20LeLamp%20Control.md)。

### 1. 电机设置与校准

1. **查找舵机驱动端口**：

此命令会查找你的电机驱动器所连接的端口。

```bash
uv run lerobot-find-port
```

2. **用唯一 ID 设置电机**：

此命令为 LeLamp 的每个电机设置唯一 ID。

```bash
uv run -m lelamp.setup_motors --id your_lamp_name --port the_port_found_in_previous_step
```

3. **校准电机**：

此命令用于校准电机。

```bash
sudo uv run -m lelamp.calibrate --id your_lamp_name --port the_port_found_in_previous_step
```

校准过程将会：

- 同时校准 follower 和 leader 模式
- 确保舵机定位和响应正确
- 设置基线位置以获得准确的运动

### 2. 单元测试

运行时包含用于验证所有硬件组件的测试模块：

#### RGB 灯

```bash
# 需要以 sudo 权限运行以访问硬件
sudo uv run -m lelamp.test.test_rgb
```

#### 音频系统（麦克风与扬声器）

```bash
uv run -m lelamp.test.test_audio
```

#### 电机

```bash
uv run -m lelamp.test.test_motors --id your_lamp_name --port the_port_found_in_previous_step
```

### 3. 录制与回放动作

LeLamp 的一项核心功能是能够录制并回放动作序列：

#### 录制动作

要录制动作序列：

```bash
uv run -m lelamp.record --id your_lamp_name --port the_port_found_in_previous_step --name movement_sequence_name
```

此操作将：

- 将灯置于录制模式
- 允许你手动操作灯以录制动作
- 将动作数据保存为 CSV 文件

#### 回放动作

要回放已录制的动作：

```bash
uv run -m lelamp.replay --id your_lamp_name --port the_port_found_in_previous_step --name movement_sequence_name
```

回放系统将会：

- 从 CSV 文件加载动作数据
- 按正确的时间执行录制的动作
- 重现原始的运动序列

#### 列出录制文件

要查看某个灯的所有录制文件：

```bash
uv run -m lelamp.list_recordings --id your_lamp_name
```

该命令将显示：

- 指定灯的所有可用录制文件
- 每个文件的行数等信息
- 可用于回放的录制名称

#### 文件格式

录制的动作以 CSV 文件保存，命名格式为：
`{sequence_name}.csv`

## 4. 开机自启

如果希望在机器启动时运行 LeLamp 的语音应用，可以创建一个 systemd 服务文件：

```bash
sudo nano /etc/systemd/system/lelamp.service
```

添加以下内容：

```ini
[Unit]
Description=Lelamp Runtime Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/lelamp_runtime
ExecStart=/usr/bin/sudo uv run main.py console
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

然后启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable lelamp.service
sudo systemctl start lelamp.service
```

其他服务控制命令：

```bash
# 禁用开机启动
sudo systemctl disable lelamp.service

# 停止当前运行的服务
sudo systemctl stop lelamp.service

# 检查状态（应显示 "disabled" 或 "inactive"）
sudo systemctl status lelamp.service
```

注意：每次运行的启动时间可能不同，长时间运行（>1 小时）可能会造成电机过热或损耗。

## 示例应用

下面是用来测试 LeLamp 能力的示例应用。

### LiveKit 语音代理

要在 LeLamp 上运行对话代理，请在目标树莓派的仓库根目录下创建一个 `.env` 文件，包含以下内容：

```bash
OPENAI_API_KEY=
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

有关如何获取 LiveKit 密钥，请参考 [LiveKit 指南](https://docs.livekit.io/agents/start/voice-ai/)。安装 LiveKit CLI 后可以运行：

```bash
lk app env -w
cat .env.local
```

这会自动在本地创建一个 `.env.local` 文件，其中包含来自 LiveKit 的所有密钥。

关于 OpenAI 密钥的获取，请参考 OpenAI 的常见问题或控制台获取方法。

然后可以运行代理应用：

```bash
# 只需运行一次以下载所需文件
sudo uv run main.py download-files

# 下面任选其一
# 离散动画模式
sudo uv run main.py console

# 平滑动画模式
sudo uv run smooth_animation.py console
```

如果你的灯的 id 不是 `lelamp`，请在 `main.py` 中更改：

```py
async def entrypoint(ctx: agents.JobContext):
    agent = LeLamp(lamp_id="lelamp") # <- 在这里更改名称
```

## 贡献

本项目由 Human Computer Lab 以开源方式维护，欢迎通过 GitHub 仓库提交贡献。

## 许可证

有关许可证信息，请查看主仓库 [LeLamp](https://github.com/humancomputerlab/LeLamp)。
