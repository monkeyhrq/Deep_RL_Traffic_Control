# 📐 MDP 數學建模

將交通路口控制問題形式化為馬可夫決策過程（Markov Decision Process）。

---

## MDP 五元組 (5-tuple)

$$\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$$

| 元素 | 說明 |
|------|------|
| 𝒮 | State Space 狀態空間 |
| 𝒜 | Action Space 動作空間 |
| 𝒫 | Transition Probability 轉移機率（由 SUMO 模擬器決定） |
| ℛ | Reward Function 獎勵函數 |
| γ | Discount Factor 折扣因子（0.95） |

---

## 1️⃣ State Space (狀態空間)

### 數學定義
$$s_t = [Q_N, Q_E, Q_S, Q_W, \varphi_t] \in \mathbb{R}^5$$

### 變數說明

| 變數 | 範圍 | 說明 |
|------|------|------|
| Q_N, Q_E, Q_S, Q_W | ℕ ≥ 0 | 北/東/南/西四向當前停等車輛數 |
| φₜ | {0, 1, 2, 3} | 當前號誌相位編號 |

### 停等判定
車輛速度 v < 0.1 m/s 時視為停等狀態。

### 設計正當性

**為什麼選 5 維簡潔狀態？**

1. **避免維度詛咒**：相較於 DTSE 矩陣 (Genders, 2016) 需 60×60 維、訓練成本高 100+ 倍
2. **聚焦核心資訊**：佇列長度已充分反映壅塞程度，是 reward 的主要驅動因子
3. **感測器友善**：實務部署只需四向車輛計數器（線圈/相機），易落地
4. **可擴展性**：未來可加入平均車速、相位持續時間等特徵

---

## 2️⃣ Action Space (動作空間)

### 數學定義
$$\mathcal{A} = \{a_0, a_1\} = \{\text{Keep}, \text{Change}\}$$

### 動作說明

#### a₀ = Keep（維持當前相位）
$$\varphi_{t+1} = \varphi_t$$

- **適用情境**：當前相位車流仍未疏散完畢
- **決策週期**：每 5 秒做一次決策

#### a₁ = Change（切換下一相位）
$$\varphi_{t+1} = (\varphi_t + 1) \bmod 4$$

- **過渡保護**：自動安插 3 秒黃燈 + 1 秒全紅
- **後續處理**：切換後重置綠燈計時器

### 安全約束 (Safety Constraints)

| 約束 | 條件 | 說明 |
|------|------|------|
| C1：最小綠燈時間 | t_green ≥ t_min = 10s | 若未達最小綠燈，強制忽略 Change |
| C2：黃燈過渡保護 | Yellow = 3s, All-Red = 1s | 確保駕駛安全與物理切換 |
| C3：決策週期 | Δt_decision = 5s | Agent 每 5 秒觀測並決策一次 |

---

## 3️⃣ Reward Function (獎勵函數)

### 數學定義
$$r_t = -\sum_{\ell \in \mathcal{L}} w_\ell(t)$$

### 變數說明

| 變數 | 說明 |
|------|------|
| rₜ | 在時刻 t 獲得的即時獎勵（≤ 0） |
| wₗ(t) | 車道 ℓ 在時刻 t 的累積等待時間（秒） |
| ℒ | {N, E, S, W} 四個進入車道集合 |
| Σ | 對所有車道累積等待時間求和 |

### 設計邏輯

1. **懲罰結構**：等待時間越長 → 懲罰越大（rₜ 越負）
2. **長期目標**：Agent 為了最大化 Σγᵏrₜ₊ₖ，必須最小化總等待時間
3. **天然優先級**：自動優先處理「等最久」的車流方向
4. **理想狀態**：rₜ → 0（理想無等待）

---

## 4️⃣ 核心數學目標

### 累積折扣回報
$$G_t = \sum_{k=0}^{\infty} \gamma^k \cdot r_{t+k+1}$$

### 動作價值函數
$$Q^\pi(s, a) = \mathbb{E}_\pi\left[G_t \mid s_t = s, a_t = a\right]$$

### 最優策略
$$\pi^*(s) = \arg\max_a Q^*(s, a)$$

### Bellman 最優方程
$$Q^*(s, a) = \mathbb{E}\left[r + \gamma \cdot \max_{a'} Q^*(s', a') \mid s, a\right]$$

---

## 5️⃣ DQN 演算法

### 神經網路架構

```
Input Layer:    sₜ ∈ ℝ⁵ (5 維狀態向量)
                    ↓
Hidden Layer 1: FC 128 + ReLU
                    ↓
Hidden Layer 2: FC 64 + ReLU
                    ↓
Output Layer:   Q(s, a₀), Q(s, a₁) ∈ ℝ²  (Linear, no activation)
```

### Loss Function (TD Error 最小化)

$$L(\theta) = \mathbb{E}_{(s,a,r,s') \sim \mathcal{D}}\left[\left(y_t - Q(s_t, a_t; \theta)\right)^2\right]$$

其中 TD Target：

$$y_t = r_t + \gamma \cdot \max_{a'} Q(s_{t+1}, a'; \theta^-)$$

### 變數說明

| 變數 | 說明 |
|------|------|
| θ | Policy Network 權重（每步更新） |
| θ⁻ | Target Network 權重（每 C 步同步一次） |
| 𝒟 | Replay Buffer（經驗回放池） |
| yₜ | TD Target — 由 Bellman 方程計算的目標 Q 值 |

---

## 6️⃣ 穩定化機制

### Experience Replay
- 儲存 (s, a, r, s', done) 五元組於 Replay Buffer
- 容量：50,000
- 每次訓練從中隨機抽樣 batch_size = 32
- **目的**：打破連續時間序列的資料相關性

### Target Network
- 結構與 Policy Network 完全相同
- 每 C = 500 步將 Policy Network 參數複製到 Target Network
- **目的**：穩定 TD Target 計算，避免 Q-value 劇烈震盪

---

## 7️⃣ 訓練流程 (Pseudo Code)

```python
Initialize replay buffer D with capacity N=50000
Initialize policy network Q with random weights θ
Initialize target network Q̂ with weights θ⁻ = θ

for episode = 1 to M:
    Reset SUMO environment, get initial state s₁
    for t = 1 to T:
        # ε-greedy 探索
        With probability ε select random action aₜ
        Otherwise select aₜ = argmaxₐ Q(sₜ, a; θ)

        # 執行動作（含安全約束檢查）
        if aₜ == Change and t_green < 10s:
            aₜ = Keep  # 強制忽略
        Execute aₜ in SUMO via TraCI
        Observe reward rₜ and next state sₜ₊₁

        # 儲存經驗
        Store (sₜ, aₜ, rₜ, sₜ₊₁) in D

        # 訓練
        Sample minibatch from D
        Compute TD target: yⱼ = rⱼ + γ·maxₐ' Q̂(sⱼ₊₁, a'; θ⁻)
        Perform gradient descent on (yⱼ - Q(sⱼ, aⱼ; θ))²

        # 同步 Target Network
        Every C=500 steps: θ⁻ ← θ

    Decay ε ← max(0.05, ε × 0.995)
```
