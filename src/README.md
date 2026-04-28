# 💻 Source Code

> 此目錄為**待實作**的原始碼結構規劃。本研究目前為 Proposal 階段，後續實作將依此結構展開。

---

## 📂 目錄規劃

```
src/
├── agent/                    # DQN Agent 模組
│   ├── __init__.py
│   ├── dqn_agent.py          # DQN 主要邏輯（含 ε-greedy）
│   ├── replay_buffer.py      # Experience Replay Buffer
│   └── q_network.py          # Q-Network 神經網路定義
│
├── env/                      # SUMO 環境包裝
│   ├── __init__.py
│   ├── traffic_env.py        # Gym-style 環境介面
│   └── traci_wrapper.py      # TraCI API 封裝
│
├── utils/                    # 工具函式
│   ├── __init__.py
│   ├── logger.py             # 訓練日誌（TensorBoard）
│   └── visualizer.py         # 結果視覺化（matplotlib）
│
├── train.py                  # 訓練主程式
└── evaluate.py               # 評估主程式
```

---

## 🎯 實作優先順序

### Phase 1：環境建置（Week 1）
- [ ] 建立 SUMO 四向標準路口場景檔
- [ ] 撰寫 `traci_wrapper.py` 封裝 SUMO 與 Python 的橋樑
- [ ] 撰寫 `traffic_env.py` 提供 Gym-style 介面（reset / step / render）

### Phase 2：DQN 核心（Week 2）
- [ ] 實作 `q_network.py`（PyTorch FC × 2）
- [ ] 實作 `replay_buffer.py`（容量 50,000）
- [ ] 實作 `dqn_agent.py`（含 Target Network）

### Phase 3：訓練與評估（Week 3）
- [ ] 撰寫 `train.py` 訓練主程式
- [ ] 撰寫 `evaluate.py` 評估主程式
- [ ] 整合 TensorBoard 日誌

### Phase 4：實驗與調優（Week 4）
- [ ] 與 Fixed-Time 基準比較
- [ ] 收集量化指標（waiting time、queue、throughput）
- [ ] 製作結果圖表

---

## 🧱 核心類別介面 (Class Interfaces)

### `TrafficEnv` (Gym-style)
```python
class TrafficEnv:
    def __init__(self, config_path: str): ...
    def reset(self) -> np.ndarray: ...
    def step(self, action: int) -> Tuple[state, reward, done, info]: ...
    def close(self): ...
```

### `DQNAgent`
```python
class DQNAgent:
    def __init__(self, config: dict): ...
    def select_action(self, state, epsilon: float) -> int: ...
    def store_transition(self, s, a, r, s_next, done): ...
    def train_step(self) -> float: ...   # returns loss
    def update_target_network(self): ...
    def save(self, path: str): ...
    def load(self, path: str): ...
```

### `ReplayBuffer`
```python
class ReplayBuffer:
    def __init__(self, capacity: int = 50000): ...
    def push(self, s, a, r, s_next, done): ...
    def sample(self, batch_size: int = 32) -> Tuple[Tensor, ...]: ...
    def __len__(self) -> int: ...
```

---

## 📝 註記

- 所有程式碼將遵循 PEP 8 規範
- 使用 type hints 增加可讀性
- 重要函式提供 docstring
- 訓練可重現（固定 random seed）
