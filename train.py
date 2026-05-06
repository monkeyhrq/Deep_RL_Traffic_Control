"""
train.py - DQN 訓練主程式

執行方式：
    python train.py

訓練過程會顯示：
    Episode | Reward | Waiting | Epsilon | Loss
    並每 10 個 Episode 儲存一次模型
"""

import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt

# 確認 SUMO_HOME
if "SUMO_HOME" not in os.environ:
    default = r"C:\Program Files (x86)\Eclipse\Sumo"
    if os.path.exists(default):
        os.environ["SUMO_HOME"] = default

# 設定路徑
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SUMO_CFG   = os.path.join(BASE_DIR, "sumo", "simulation.sumocfg")
CKPT_DIR   = os.path.join(BASE_DIR, "checkpoints")
os.makedirs(CKPT_DIR, exist_ok=True)

from src.env   import TrafficEnv
from src.agent import DQNAgent

# ============================================================
# 超參數設定
# ============================================================
EPISODES       = 200    # 訓練幾個 Episode
MAX_STEPS      = 3600   # 每個 Episode 最多跑幾步（秒）
PRINT_EVERY    = 5      # 每幾個 Episode 印一次
SAVE_EVERY     = 10     # 每幾個 Episode 存一次模型
USE_GUI        = False  # 訓練時不開 GUI（快很多）

# DQN 超參數
LR             = 0.001
GAMMA          = 0.95
EPSILON_START  = 1.0
EPSILON_END    = 0.05
EPSILON_DECAY  = 0.995
BATCH_SIZE     = 32
BUFFER_SIZE    = 50000
TARGET_UPDATE  = 500


def train():
    """主訓練函式"""

    print("=" * 60)
    print("🚦 自動化紅綠燈 DQN 訓練開始")
    print("=" * 60)
    print(f"訓練設定：")
    print(f"  Episodes:      {EPISODES}")
    print(f"  Gamma:         {GAMMA}")
    print(f"  Learning Rate: {LR}")
    print(f"  Batch Size:    {BATCH_SIZE}")
    print(f"  Buffer Size:   {BUFFER_SIZE}")
    print(f"  Target Update: 每 {TARGET_UPDATE} 步")
    print("=" * 60)

    # ── 建立環境和 Agent ──
    env   = TrafficEnv(cfg_path=SUMO_CFG, use_gui=USE_GUI)
    agent = DQNAgent(
        state_dim      = env.state_dim,
        action_dim     = env.action_dim,
        lr             = LR,
        gamma          = GAMMA,
        epsilon_start  = EPSILON_START,
        epsilon_end    = EPSILON_END,
        epsilon_decay  = EPSILON_DECAY,
        batch_size     = BATCH_SIZE,
        buffer_size    = BUFFER_SIZE,
        target_update  = TARGET_UPDATE,
    )

    # ── 記錄訓練歷程 ──
    reward_history  = []  # 每個 Episode 的總 Reward
    waiting_history = []  # 每個 Episode 的總等待時間
    loss_history    = []  # 每個 Episode 的平均 Loss
    best_reward     = float('-inf')

    print(f"\n{'Episode':>8} | {'Reward':>10} | {'Waiting(s)':>10} | {'Epsilon':>7} | {'Loss':>8}")
    print("-" * 60)

    start_time = time.time()

    for episode in range(1, EPISODES + 1):

        # ── 重置環境 ──
        state = env.reset()
        episode_reward  = 0.0
        episode_loss    = []

        # ── 跑一個 Episode ──
        while True:
            # 1. 選擇動作（ε-greedy）
            action = agent.select_action(state)

            # 2. 執行動作，取得下一個狀態和獎勵
            next_state, reward, done = env.step(action)

            # 3. 存入 Replay Buffer
            agent.store_transition(state, action, reward, next_state, done)

            # 4. 訓練一步
            loss = agent.train()
            if loss > 0:
                episode_loss.append(loss)

            # 5. 更新狀態
            state = next_state
            episode_reward += reward

            if done:
                break

        # ── Episode 結束 ──
        total_waiting = env.get_episode_waiting()
        avg_loss = np.mean(episode_loss) if episode_loss else 0.0

        reward_history.append(episode_reward)
        waiting_history.append(total_waiting)
        loss_history.append(avg_loss)

        # 衰減探索率
        agent.decay_epsilon()

        # ── 儲存最佳模型 ──
        if episode_reward > best_reward:
            best_reward = episode_reward
            agent.save(os.path.join(CKPT_DIR, "best_model.pth"))

        # ── 定期儲存 ──
        if episode % SAVE_EVERY == 0:
            agent.save(os.path.join(CKPT_DIR, f"model_ep{episode}.pth"))

        # ── 印出訓練進度 ──
        if episode % PRINT_EVERY == 0 or episode == 1:
            elapsed = time.time() - start_time
            print(f"{episode:>8} | "
                  f"{episode_reward:>10.1f} | "
                  f"{total_waiting:>10.1f} | "
                  f"{agent.epsilon:>7.3f} | "
                  f"{avg_loss:>8.4f}  "
                  f"[{elapsed:.0f}s]")

    # ── 訓練結束 ──
    env.close()

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎉 訓練完成！共 {EPISODES} 個 Episode，耗時 {elapsed:.0f} 秒")
    print(f"   最佳 Reward：{best_reward:.1f}")
    print(f"   模型已儲存至：{CKPT_DIR}")
    print("=" * 60)

    # ── 畫訓練結果圖 ──
    plot_results(reward_history, waiting_history, loss_history)


def plot_results(rewards, waitings, losses):
    """畫出訓練過程的三張圖"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # 圖 1：Reward 曲線
    axes[0].plot(rewards, alpha=0.6, color='blue', label='Reward')
    # 滑動平均
    if len(rewards) >= 10:
        ma = np.convolve(rewards, np.ones(10)/10, mode='valid')
        axes[0].plot(range(9, len(rewards)), ma, color='red', linewidth=2, label='MA-10')
    axes[0].set_title('Episode Reward')
    axes[0].set_xlabel('Episode')
    axes[0].set_ylabel('Total Reward')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # 圖 2：等待時間曲線
    axes[1].plot(waitings, alpha=0.6, color='orange', label='Waiting Time')
    if len(waitings) >= 10:
        ma = np.convolve(waitings, np.ones(10)/10, mode='valid')
        axes[1].plot(range(9, len(waitings)), ma, color='red', linewidth=2, label='MA-10')
    axes[1].set_title('Total Waiting Time')
    axes[1].set_xlabel('Episode')
    axes[1].set_ylabel('Waiting Time (s)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # 圖 3：Loss 曲線
    axes[2].plot(losses, alpha=0.6, color='green', label='Loss')
    axes[2].set_title('Training Loss')
    axes[2].set_xlabel('Episode')
    axes[2].set_ylabel('Loss')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('training_results.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 訓練結果圖已儲存：training_results.png")
    plt.show()


if __name__ == "__main__":
    train()
