"""
watch_agent.py
載入訓練好的模型，用 SUMO GUI 觀察 AI 如何控制號誌

執行方式：
    python watch_agent.py

你會看到：
    - SUMO GUI 視窗開啟（車子在動、號誌在切換）
    - Anaconda Prompt 顯示即時的 State / Action / Reward
"""

import os
import sys
import time
import torch
import numpy as np

# ── 設定 SUMO_HOME ──
if "SUMO_HOME" not in os.environ:
    default = r"C:\Program Files (x86)\Eclipse\Sumo"
    if os.path.exists(default):
        os.environ["SUMO_HOME"] = default

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
SUMO_CFG  = os.path.join(BASE_DIR, "sumo", "simulation.sumocfg")
MODEL_PATH = os.path.join(BASE_DIR, "checkpoints", "best_model.pth")

from src.env   import TrafficEnv
from src.model import QNetwork

# ============================================================
# 設定
# ============================================================
EPISODES  = 3      # 觀察幾局（跑完會自動重開）
USE_GUI   = True   # 開啟 SUMO GUI


def watch():
    print("=" * 60)
    print("👁️  載入模型，開始觀察 AI 控制號誌")
    print("=" * 60)

    # ── 確認模型存在 ──
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 找不到模型：{MODEL_PATH}")
        print("   請先執行 python train.py 訓練模型")
        return

    # ── 載入模型 ──
    device = torch.device("cpu")
    model  = QNetwork(state_dim=5, action_dim=2).to(device)
    checkpoint = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(checkpoint['policy_net'])
    model.eval()
    print(f"✅ 模型載入成功：{MODEL_PATH}")
    print(f"   訓練時的 Epsilon：{checkpoint['epsilon']:.4f}")
    print(f"   訓練步數：{checkpoint['train_step']}")

    # ── 建立環境（開啟 GUI）──
    env = TrafficEnv(cfg_path=SUMO_CFG, use_gui=USE_GUI)

    action_names = {0: "Keep  🟢", 1: "Change 🔄"}

    for ep in range(1, EPISODES + 1):
        print(f"\n{'='*60}")
        print(f"  Episode {ep} / {EPISODES}  —  SUMO GUI 已開啟，觀察 AI 決策")
        print(f"{'='*60}")
        print(f"{'Step':>6} | {'State (N,E,S,W,φ)':>25} | {'Action':>12} | {'Reward':>10} | {'累計等待':>10}")
        print("-" * 80)

        state      = env.reset()
        total_reward  = 0.0
        step_count = 0

        while True:
            # AI 選擇動作（純貪婪，不探索）
            with torch.no_grad():
                state_t = torch.FloatTensor(state).unsqueeze(0)
                q_vals  = model(state_t)
                action  = q_vals.argmax(dim=1).item()

            # 執行動作
            next_state, reward, done = env.step(action)

            total_reward += reward
            step_count   += 1

            # 每 5 步顯示一次
            if step_count % 5 == 0:
                q_str = f"[{state[0]:.0f},{state[1]:.0f},{state[2]:.0f},{state[3]:.0f},φ{state[4]:.0f}]"
                print(f"{step_count:>6} | {q_str:>25} | {action_names[action]:>12} | "
                      f"{reward:>10.1f} | {env.get_episode_waiting():>10.1f}")

            state = next_state

            if done:
                break

        print("-" * 80)
        print(f"  Episode {ep} 結束 | 總 Reward：{total_reward:.1f} | "
              f"總等待時間：{env.get_episode_waiting():.1f} 秒")

        if ep < EPISODES:
            print(f"\n  ⏳ 3 秒後開始下一局...")
            time.sleep(3)

    env.close()
    print(f"\n{'='*60}")
    print("✅ 觀察結束！")
    print("=" * 60)


if __name__ == "__main__":
    watch()
