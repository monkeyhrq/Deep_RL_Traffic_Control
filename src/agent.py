"""
agent.py - DQN Agent

包含：
1. ReplayBuffer  - 經驗回放池（打破時間序列相關性）
2. DQNAgent      - 主要的強化學習 Agent
   - ε-greedy 探索策略
   - Experience Replay 訓練
   - Target Network 穩定訓練
"""

import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
from src.model import QNetwork


# ============================================================
# ReplayBuffer：經驗回放池
# ============================================================
class ReplayBuffer:
    """
    儲存過去的 (state, action, reward, next_state, done) 經驗
    訓練時隨機抽取，打破時間序列的相關性

    Args:
        capacity: 最多存幾筆經驗（舊的會被覆蓋）
    """

    def __init__(self, capacity: int = 50000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        """
        存入一筆經驗

        Args:
            state:      當前狀態（numpy array）
            action:     執行的動作（int）
            reward:     獲得的獎勵（float）
            next_state: 下一個狀態（numpy array）
            done:       是否結束（bool）
        """
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        """
        隨機抽取一個 batch 的經驗

        Args:
            batch_size: 抽幾筆

        Returns:
            states, actions, rewards, next_states, dones（都是 Tensor）
        """
        batch = random.sample(self.buffer, batch_size)

        # 解包並轉成 numpy，再轉成 Tensor
        states, actions, rewards, next_states, dones = zip(*batch)

        states      = torch.FloatTensor(np.array(states))
        actions     = torch.LongTensor(np.array(actions))
        rewards     = torch.FloatTensor(np.array(rewards))
        next_states = torch.FloatTensor(np.array(next_states))
        dones       = torch.FloatTensor(np.array(dones, dtype=np.float32))

        return states, actions, rewards, next_states, dones

    def __len__(self):
        """目前存了幾筆經驗"""
        return len(self.buffer)


# ============================================================
# DQNAgent：主要的 RL Agent
# ============================================================
class DQNAgent:
    """
    DQN Agent：用深度強化學習控制交通號誌

    核心概念：
    - Policy Network：每步訓練，預測當前 Q 值
    - Target Network：每 C 步同步，提供穩定的 TD Target
    - ε-greedy：訓練初期多探索，後期多利用

    Args:
        state_dim:      狀態維度（5）
        action_dim:     動作數量（2）
        lr:             學習率（0.001）
        gamma:          折扣因子（0.95）
        epsilon_start:  初始探索率（1.0）
        epsilon_end:    最終探索率（0.05）
        epsilon_decay:  每個 episode 衰減率（0.995）
        batch_size:     訓練批次大小（32）
        buffer_size:    Replay Buffer 容量（50000）
        target_update:  每幾步同步 Target Network（500）
    """

    def __init__(self,
                 state_dim:      int   = 5,
                 action_dim:     int   = 2,
                 lr:             float = 0.001,
                 gamma:          float = 0.95,
                 epsilon_start:  float = 1.0,
                 epsilon_end:    float = 0.05,
                 epsilon_decay:  float = 0.995,
                 batch_size:     int   = 32,
                 buffer_size:    int   = 50000,
                 target_update:  int   = 500):

        self.state_dim     = state_dim
        self.action_dim    = action_dim
        self.gamma         = gamma
        self.epsilon       = epsilon_start
        self.epsilon_end   = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size    = batch_size
        self.target_update = target_update
        self.train_step    = 0  # 訓練了幾步（用來判斷何時同步 Target）

        # 裝置設定（有 GPU 用 GPU，沒有用 CPU）
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"使用裝置: {self.device}")

        # Policy Network（每步訓練）
        self.policy_net = QNetwork(state_dim, action_dim).to(self.device)

        # Target Network（每 C 步同步）
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()  # Target Network 不需要梯度

        # 優化器
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)

        # Loss 函數（MSE Loss）
        self.criterion = nn.MSELoss()

        # Replay Buffer
        self.replay_buffer = ReplayBuffer(buffer_size)

    # ----------------------------------------------------------
    # select_action：選擇動作（ε-greedy）
    # ----------------------------------------------------------
    def select_action(self, state: np.ndarray) -> int:
        """
        用 ε-greedy 策略選擇動作

        以 ε 的機率隨機探索（Exploration）
        以 1-ε 的機率選 Q 值最大的動作（Exploitation）

        Args:
            state: 當前狀態（numpy array，shape=(5,)）

        Returns:
            action: 0=Keep 或 1=Change
        """
        if random.random() < self.epsilon:
            # 隨機探索
            return random.randint(0, self.action_dim - 1)
        else:
            # 選 Q 值最大的動作
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            return self.policy_net.get_action(state_tensor)

    # ----------------------------------------------------------
    # store_transition：存入經驗
    # ----------------------------------------------------------
    def store_transition(self, state, action, reward, next_state, done):
        """
        把一步的經驗存入 Replay Buffer

        Args:
            state:      當前狀態
            action:     執行的動作
            reward:     獲得的獎勵
            next_state: 下一個狀態
            done:       是否結束
        """
        self.replay_buffer.push(state, action, reward, next_state, done)

    # ----------------------------------------------------------
    # train_step：訓練一步
    # ----------------------------------------------------------
    def train(self) -> float:
        """
        從 Replay Buffer 抽樣，訓練 Policy Network

        Loss = MSE(y_t - Q(s_t, a_t; θ))
        y_t  = r_t + γ * max_a' Q(s_{t+1}, a'; θ⁻)

        Returns:
            loss: 這次訓練的 loss 值（用來監控訓練進度）
        """
        # Replay Buffer 不夠多就先不訓練
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        # 從 Buffer 隨機抽樣
        states, actions, rewards, next_states, dones = \
            self.replay_buffer.sample(self.batch_size)

        # 移到裝置
        states      = states.to(self.device)
        actions     = actions.to(self.device)
        rewards     = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones       = dones.to(self.device)

        # ── 計算當前 Q 值：Q(s_t, a_t; θ) ──
        # policy_net 預測所有動作的 Q 值，再選出實際執行的動作的 Q 值
        current_q = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # ── 計算 TD Target（Double DQN）──
        # Double DQN：用 Policy Network 選動作，用 Target Network 算 Q 值
        # 避免 DQN 的高估問題
        with torch.no_grad():
            next_actions = self.policy_net(next_states).argmax(1)
            next_q = self.target_net(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)
            td_target = rewards + self.gamma * next_q * (1 - dones)

        # ── 計算 Loss 並更新 ──
        loss = self.criterion(current_q, td_target)

        self.optimizer.zero_grad()  # 清除上一步的梯度
        loss.backward()             # 反向傳播
        self.optimizer.step()       # 更新權重

        # ── 每 target_update 步同步 Target Network ──
        self.train_step += 1
        if self.train_step % self.target_update == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        return loss.item()

    # ----------------------------------------------------------
    # decay_epsilon：衰減探索率
    # ----------------------------------------------------------
    def decay_epsilon(self):
        """
        每個 episode 結束後呼叫，讓探索率慢慢降低
        從 1.0 逐漸衰減到 0.05
        """
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    # ----------------------------------------------------------
    # save / load：儲存和載入模型
    # ----------------------------------------------------------
    def save(self, path: str):
        """
        儲存模型權重

        Args:
            path: 儲存路徑（例如 'checkpoints/best_model.pth'）
        """
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer':  self.optimizer.state_dict(),
            'epsilon':    self.epsilon,
            'train_step': self.train_step,
        }, path)
        print(f"✅ 模型已儲存：{path}")

    def load(self, path: str):
        """
        載入模型權重

        Args:
            path: 模型檔案路徑
        """
        checkpoint = torch.load(path, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint['policy_net'])
        self.target_net.load_state_dict(checkpoint['target_net'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.epsilon    = checkpoint['epsilon']
        self.train_step = checkpoint['train_step']
        print(f"✅ 模型已載入：{path}")
