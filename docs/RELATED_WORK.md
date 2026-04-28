# 📚 Related Work — 相關研究

## 文獻比較總表 (Article Summary Table)

| 方法 | 代表文獻 | 決策邏輯 | 實測效能 (vs Fixed) | 缺點 |
|------|---------|---------|---------------------|------|
| **Fixed-Time** 定時控制 | Webster (1958) | 依歷史數據設定固定循環 | 基準 (LOS E: 55–80s) | 缺乏彈性、易綠燈空轉 |
| **Actuated** 感應式控制 | SCATS / SCOOT | 線圈觸發 (Rule-based) 被動反應 | 延遲 ↓ 12% | 僅單一車道、無全局最佳化 |
| **Q-Learning** 表格式 RL | Wiering (2000) | Q-Table 查表式學習 | 延遲 ↓ ~30% | 狀態空間爆炸、難擴展 |
| **DQN** 深度 Q 網路 | Genders & Razavi (2016) | 神經網路逼近 Q 值 | 延遲 ↓ 82% / 佇列 ↓ 66% | 訓練不穩定、需穩定化機制 |
| **★ 本研究** | — | DQN + Experience Replay + Target Network | 目標：等待時間 ↓ 30%+ | 需大量訓練樣本 |

---

## 三大流派分類

### 第一類：傳統規則式控制 (Rule-based)

#### Webster (1958) — 經典定時號誌公式
- 最早的數學化交通號誌設計理論
- 基於泊松到達假設與排隊理論
- **限制**：依賴專家經驗，無法應對突發車流

#### SCATS / SCOOT — 自適應系統
- 1980s 發展的感應式控制系統
- 透過路面線圈感測器觸發號誌切換
- **限制**：僅考量單一局部車道，無全局視野

---

### 第二類：傳統機器學習方法

#### Wiering (2000) — Q-Learning 應用於交通控制
- 首次將強化學習引入交通號誌控制領域
- 採用 Q-Table 表格式學習
- **限制**：狀態空間隨路口複雜度指數成長，難以擴展

#### 模糊邏輯控制器 (Fuzzy Logic)
- 用模糊規則處理車流不確定性
- **限制**：仍需手工設計規則，缺乏自主學習能力

---

### 第三類：深度強化學習方法（本研究所屬）

#### Genders & Razavi (2016) ⭐ 重要基準
**論文**：*Using a Deep Reinforcement Learning Agent for Traffic Signal Control*

**主要貢獻**：
- 首次將 DQN 應用於交通號誌控制
- 使用 DTSE (Discrete Traffic State Encoding) 作為狀態表示
- 在 SUMO 平台驗證效能

**實驗結果** (vs Fixed-Time)：
- 累積延遲 ↓ 82%
- 平均佇列長度 ↓ 66%
- 平均旅行時間 ↓ 20%

#### van der Pol (2016) — Double DQN / Dueling DQN
- 改善 DQN 的 Q-value 高估問題
- 引入 Advantage 函數分離

#### Chu et al. (2019) — Multi-Agent DRL
**論文**：*Multi-Agent Deep RL for Large-Scale Traffic Signal Control*
- 將單路口 DQN 擴展到多路口協調
- 處理 Green Wave 綠波協調問題

#### Pan et al. (2023) — DQN + Memory Palace
- 引入記憶宮殿機制改善訓練效率
- **效能**：Waiting Time ↓ 57.1% ~ 100%、Queue ↓ 40.9% ~ 100%

#### Pri-DDQN (2024) — Double DQN + Prioritized Experience Replay
- 結合優先經驗回放
- **效能**：Waiting Time ↓ 21.5% (vs Fixed)

#### Liu et al. (PMC, 2022) — DQN vs SAC 比較
- 比較離散動作 (DQN) 與連續動作 (SAC) 的效能
- **效能**：Avg Delay 5.13s

---

## 量化效能對照（前人研究）

| 文獻 | 方法 | Waiting Time ↓ | Queue Length ↓ | Travel Time ↓ | 模擬器 |
|------|------|---------------|----------------|---------------|--------|
| Genders & Razavi (2016) | Deep CNN + DQN | — | 66% | 20% | SUMO |
| Pan et al. (2023) | DQN + Memory Palace | 57.1% ~ 100% | 40.9% ~ 100% | 16.8% ~ 68% | SUMO |
| Pri-DDQN (2024) | Double DQN + PER | 21.5% (vs Fixed) | 顯著縮短 | — | SUMO |
| Liu et al. (PMC, 2022) | DQN vs SAC | Avg Delay 5.13s | — | — | SUMO |

---

## 本研究的定位

> **結合 DQN 學習能力與 SUMO 模擬真實性，突破靜態規則極限，實現全局動態最佳化。**

### 與既有方法的差異
1. **相較傳統規則式**：具備自主學習能力，無需專家手工調規
2. **相較 Q-Learning**：可處理高維連續狀態，避免維度詛咒
3. **相較複雜 DRL 變體**：使用簡潔 5 維狀態，易於部署且訓練成本低
4. **相較 Multi-Agent**：聚焦單路口最佳化（Proof of Concept），未來可擴展
