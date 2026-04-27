# 🚦 自動化紅綠燈交通控制 — 基於深度強化學習的動態路口決策系統

> **Automated Traffic Signal Control via Deep Reinforcement Learning**
> 一個基於 DQN（Deep Q-Network）+ SUMO 模擬平台的智慧交通號誌控制研究專案

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)
[![SUMO](https://img.shields.io/badge/SUMO-1.18+-green.svg)](https://www.eclipse.org/sumo/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Proposal-orange.svg)]()

---

## 📋 專案簡介 (Abstract)

本研究針對**現代都市交通號誌控制**的痛點，提出基於深度強化學習（Deep Reinforcement Learning, DRL）的動態路口決策系統。透過 SUMO 模擬平台與 DQN 演算法，讓 AI 號誌系統具備「全局視野」，自主學習最佳號誌切換策略。

### 🎯 A–F 六大要素

| 要素 | 內容 |
|------|------|
| **A. Motivation 動機** | 智慧城市與車聯網蓬勃發展，AI 動態交通號誌已成核心研究熱點 |
| **B. But 挑戰** | 傳統定時／感應式號誌缺乏全局視野，面對動態車流效率低落 |
| **C. Cure 解藥** | 提出基於深度強化學習 (DRL) 的動態路口決策系統 |
| **D. Development 設計** | Based on DQN + SUMO 模擬平台 + TraCI API |
| **E. Experiments 實驗** | 於四向標準路口進行隨機車流壓力測試，與定時號誌 PK |
| **F. Findings 發現** | 預期顯著降低平均停等時間、縮短佇列、提升吞吐量 |

---

## 🏆 預期效能改善 (vs Fixed-Time 基準)

| 指標 | 預期改善 | 對照基準 |
|------|---------|---------|
| ⏱️ 平均停等時間 (Avg Waiting Time) | **↓ 30%+** | Fixed-Time |
| 🚗 佇列長度 (Queue Length) | **↓ 40%+** | Fixed-Time |
| 📈 整體吞吐量 (Throughput) | **↑ 20%+** | Fixed-Time |
| 🌱 CO₂ 排放 | **↓ 15%+** | 減少怠速 |

---

## 🧠 核心技術架構

```
┌─────────────────────────────────────────────────┐
│           Dashboard (Flask / Streamlit)         │
│      即時視覺化車流與 Reward 收斂曲線              │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│         TraCI (Traffic Control Interface)        │
│   每個 simulation step 抓取路況 / 下達切換指令     │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────┐      ┌──────────────────┐
│   DQN Agent  │◀────▶│  SUMO Simulator  │
│  (PyTorch)   │      │  四向標準路口     │
└──────────────┘      └──────────────────┘
   State sₜ              Reward + Next State
```

---

## 📐 MDP 數學建模

問題形式化為馬可夫決策過程 ⟨S, A, P, R, γ⟩：

### State Space (S)
$$s_t = [Q_N, Q_E, Q_S, Q_W, \varphi_t] \in \mathbb{R}^5$$

- **Q_N, Q_E, Q_S, Q_W**：東/西/南/北四向當前停等車輛數（車速 < 0.1 m/s）
- **φₜ ∈ {0, 1, 2, 3}**：當前號誌相位編號

### Action Space (A)
$$A = \{a_0, a_1\} = \{\text{Keep}, \text{Change}\}$$

- **a₀ Keep**：維持當前相位，φₜ₊₁ = φₜ
- **a₁ Change**：切換下一相位，φₜ₊₁ = (φₜ + 1) mod 4
- **安全約束**：最小綠燈時間 t_min = 10s、黃燈過渡 3s + 全紅 1s

### Reward Function (R)
$$r_t = -\sum_{\ell \in L} w_\ell(t)$$

- **wₗ(t)**：車道 ℓ 在時刻 t 的累積等待時間
- **L = {N, E, S, W}**：四個進入車道集合

### Bellman Optimal Equation
$$Q^*(s,a) = \mathbb{E}[r + \gamma \cdot \max_{a'} Q^*(s', a')]$$

### DQN Loss Function
$$L(\theta) = \mathbb{E}\left[\left(y_t - Q(s_t, a_t; \theta)\right)^2\right]$$

其中 TD Target：
$$y_t = r_t + \gamma \cdot \max_{a'} Q(s_{t+1}, a'; \theta^-)$$

- **θ**：Policy Network 權重（每步更新）
- **θ⁻**：Target Network 權重（每 C 步同步一次）

---

## ⚙️ 超參數設定

| 參數 | 數值 | 說明 |
|------|------|------|
| Learning rate α | 0.001 | Adam optimizer |
| Discount γ | 0.95 | 未來獎勵折扣率 |
| ε (起始 → 終止) | 1.0 → 0.05 | ε-greedy 探索率 |
| ε-decay | 0.995 | 每 episode 衰減 |
| Replay buffer | 50,000 | 經驗回放池容量 |
| Batch size | 32 | 訓練批次大小 |
| Target update C | 每 500 步 | 目標網路同步頻率 |
| Hidden layers | [128, 64] | 全連接層神經元數 |

---

## 📂 專案結構

```
Deep_RL_Traffic_Control/
├── README.md                           # 本檔案
├── LICENSE                             # MIT License
├── requirements.txt                    # Python 依賴套件
├── .gitignore                          # Git 忽略清單
├── Deep_RL_Traffic_Control_Final.pptx  # 專案簡報
│
├── docs/                               # 詳細文件
│   ├── ABSTRACT.md                     # 完整 A-F 摘要
│   ├── MDP_FORMULATION.md              # MDP 數學定義
│   ├── RELATED_WORK.md                 # 相關文獻整理
│   └── REFERENCES.md                   # 參考文獻
│
├── src/                                # 原始碼（待實作）
│   ├── agent/                          # DQN Agent
│   │   ├── dqn_agent.py                # DQN 主要邏輯
│   │   ├── replay_buffer.py            # Experience Replay
│   │   └── q_network.py                # Q-Network 神經網路
│   ├── env/                            # SUMO 環境包裝
│   │   ├── traffic_env.py              # Gym-style 環境介面
│   │   └── traci_wrapper.py            # TraCI API 封裝
│   ├── train.py                        # 訓練主程式
│   ├── evaluate.py                     # 評估主程式
│   └── utils/                          # 工具函式
│       ├── logger.py                   # 訓練日誌
│       └── visualizer.py               # 結果視覺化
│
├── configs/                            # 設定檔
│   ├── dqn_config.yaml                 # DQN 超參數
│   └── sumo/                           # SUMO 場景檔
│       ├── intersection.net.xml        # 路網定義
│       ├── routes.rou.xml              # 車流路徑
│       └── simulation.sumocfg          # 模擬設定
│
└── assets/                             # 圖片與資源
    └── architecture.png                # 系統架構圖
```

---

## 🚀 快速開始 (待實作)

### 環境需求
- Python 3.9+
- PyTorch 2.0+
- SUMO 1.18+
- 推薦使用 conda / venv 建立獨立環境

### 安裝步驟

```bash
# 1. Clone 專案
git clone https://github.com/<your-username>/Deep_RL_Traffic_Control.git
cd Deep_RL_Traffic_Control

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 安裝 SUMO (依作業系統)
# Windows: https://sumo.dlr.de/docs/Downloads.php
# Mac:     brew install sumo
# Linux:   sudo apt install sumo sumo-tools sumo-doc

# 5. 設定 SUMO_HOME 環境變數
export SUMO_HOME=/usr/share/sumo   # Linux
# set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo   # Windows
```

### 執行訓練

```bash
# 訓練 DQN Agent
python src/train.py --config configs/dqn_config.yaml

# 評估訓練結果
python src/evaluate.py --model checkpoints/best_model.pth
```

---

## 📚 相關文獻

| 方法 | 代表文獻 | 實測效能 (vs Fixed) |
|------|---------|---------------------|
| Fixed-Time | Webster (1958) | 基準 (LOS E: 55–80s) |
| Actuated | SCATS / SCOOT | 延遲 ↓ 12% |
| Q-Learning | Wiering (2000) | 延遲 ↓ ~30% |
| DQN | Genders & Razavi (2016) | **延遲 ↓ 82% / 佇列 ↓ 66%** |
| **本研究** | — | 目標：等待時間 ↓ 30%+ |

詳細文獻列表請見 [`docs/REFERENCES.md`](docs/REFERENCES.md)

---

## 👥 作者

- **學生姓名**：[請填寫]
- **學號**：[請填寫]
- **指導教授**：[請填寫]
- **學校**：[請填寫]
- **學期**：2026 春季

---

## 📄 授權

本專案採用 [MIT License](LICENSE) 授權。

---

## 🙏 致謝

感謝指導教授對於論文寫作框架（A-Z Framework）與簡報結構的指導。

---

<p align="center">
  <i>讓每個十字路口成為「智慧大腦」 — 資料驅動 × 動態決策 × 永續低碳</i>
</p>
