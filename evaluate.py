"""
evaluate.py - DQN vs Fixed-Time 比較評估（修正版）

執行方式：
    python evaluate.py

產出：
    - 終端機顯示詳細比較數據
    - comparison_results.png（比較圖表）
    - comparison_results.txt（數據報告）
"""

import os
import time
import torch
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Microsoft JhengHei'
matplotlib.rcParams['axes.unicode_minus'] = False

import traci

# ── 設定 SUMO_HOME ──
if "SUMO_HOME" not in os.environ:
    default = r"C:\Program Files (x86)\Eclipse\Sumo"
    if os.path.exists(default):
        os.environ["SUMO_HOME"] = default

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SUMO_CFG   = os.path.join(BASE_DIR, "sumo", "simulation.sumocfg")
MODEL_PATH = os.path.join(BASE_DIR, "checkpoints", "best_model.pth")

from src.model import QNetwork

# ============================================================
# 設定
# ============================================================
EVAL_EPISODES  = 5       # 每個方法跑幾局
MAX_STEPS      = 3600    # 每局最多幾步（秒）
FIXED_GREEN    = 30      # Fixed-Time 綠燈秒數
MIN_GREEN_TIME = 10      # DQN 最小綠燈時間
DECISION_STEP  = 5       # DQN 每幾秒決策一次
YELLOW_TIME    = 3       # 黃燈時間
ALL_RED_TIME   = 1       # 全紅時間


# ============================================================
# 共用：啟動 SUMO
# ============================================================
def start_sumo():
    try:
        traci.close()
    except:
        pass

    traci.start([
        "sumo", "-c", SUMO_CFG,
        "--no-warnings", "--no-step-log",
        "--waiting-time-memory", "1000",
    ])

    tls_id     = traci.trafficlight.getIDList()[0]
    logic      = traci.trafficlight.getAllProgramLogics(tls_id)[0]
    num_phases = len(logic.phases)
    program_id = traci.trafficlight.getProgram(tls_id)

    # 先跑 10 步讓車輛進入
    for _ in range(10):
        traci.simulationStep()

    return tls_id, num_phases, program_id


# ============================================================
# 共用：取得當下所有車輛的平均等待時間
# ============================================================
def get_avg_waiting():
    """取得目前路口所有車輛的平均等待時間（秒/台）"""
    vehs = traci.vehicle.getIDList()
    if not vehs:
        return 0.0
    total = sum(traci.vehicle.getWaitingTime(v) for v in vehs)
    return total / len(vehs)


# ============================================================
# 共用：取得四向佇列長度
# ============================================================
def get_queue_lengths():
    lanes = ["north_in_0", "east_in_0", "south_in_0", "west_in_0"]
    queues = {}
    for lane in lanes:
        try:
            queues[lane] = traci.lane.getLastStepHaltingNumber(lane)
        except:
            queues[lane] = 0
    return queues


# ============================================================
# 執行相位切換（黃燈過渡）
# ============================================================
def do_phase_change(tls_id, program_id, current_phase, num_phases):
    if num_phases <= 1:
        return current_phase

    yellow = "y" * len(traci.trafficlight.getRedYellowGreenState(tls_id))
    allred = "r" * len(yellow)

    traci.trafficlight.setRedYellowGreenState(tls_id, yellow)
    for _ in range(YELLOW_TIME):
        traci.simulationStep()

    traci.trafficlight.setRedYellowGreenState(tls_id, allred)
    for _ in range(ALL_RED_TIME):
        traci.simulationStep()

    traci.trafficlight.setProgram(tls_id, program_id)
    current_phase = (current_phase + 1) % num_phases
    traci.trafficlight.setPhase(tls_id, current_phase)
    return current_phase


# ============================================================
# 方法 1：DQN 評估
# ============================================================
def evaluate_dqn(episodes):
    print("\n" + "="*60)
    print("🤖 評估 DQN 模型...")
    print("="*60)

    device = torch.device("cpu")
    model  = QNetwork(state_dim=5, action_dim=2).to(device)
    ckpt   = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(ckpt['policy_net'])
    model.eval()

    all_avg_waiting  = []
    all_throughput   = []
    all_queue_n      = []
    all_queue_e      = []
    all_queue_s      = []
    all_queue_w      = []

    for ep in range(1, episodes + 1):
        tls_id, num_phases, program_id = start_sumo()
        traci.trafficlight.setPhase(tls_id, 0)

        step_count    = 10
        green_time    = 0
        current_phase = 0
        vehicles_done = set()
        ep_avg_waits  = []
        ep_queues     = {"N":[], "E":[], "S":[], "W":[]}

        while step_count < MAX_STEPS:
            # 取得狀態
            lanes = {
                "N": traci.lane.getLastStepHaltingNumber("north_in_0"),
                "E": traci.lane.getLastStepHaltingNumber("east_in_0"),
                "S": traci.lane.getLastStepHaltingNumber("south_in_0"),
                "W": traci.lane.getLastStepHaltingNumber("west_in_0"),
            }
            state = np.array([
                lanes["N"], lanes["E"], lanes["S"], lanes["W"],
                float(current_phase)
            ], dtype=np.float32)

            # AI 決策
            with torch.no_grad():
                st = torch.FloatTensor(state).unsqueeze(0)
                action = model(st).argmax(dim=1).item()

            # 安全約束
            if action == 1 and green_time < MIN_GREEN_TIME:
                action = 0

            # 執行切換
            if action == 1:
                current_phase = do_phase_change(
                    tls_id, program_id, current_phase, num_phases)
                step_count += YELLOW_TIME + ALL_RED_TIME
                green_time = 0

            # 跑 DECISION_STEP 步
            for _ in range(DECISION_STEP):
                traci.simulationStep()
                step_count += 1
                green_time += 1

                # 記錄指標
                aw = get_avg_waiting()
                if aw > 0:
                    ep_avg_waits.append(aw)

                q = get_queue_lengths()
                ep_queues["N"].append(q["north_in_0"])
                ep_queues["E"].append(q["east_in_0"])
                ep_queues["S"].append(q["south_in_0"])
                ep_queues["W"].append(q["west_in_0"])

                for v in traci.simulation.getArrivedIDList():
                    vehicles_done.add(v)

                if traci.simulation.getMinExpectedNumber() <= 0:
                    break

            if traci.simulation.getMinExpectedNumber() <= 0:
                break

        try:
            traci.close()
        except:
            pass

        avg_w = np.mean(ep_avg_waits) if ep_avg_waits else 0
        all_avg_waiting.append(avg_w)
        all_throughput.append(len(vehicles_done))
        all_queue_n.append(np.mean(ep_queues["N"]))
        all_queue_e.append(np.mean(ep_queues["E"]))
        all_queue_s.append(np.mean(ep_queues["S"]))
        all_queue_w.append(np.mean(ep_queues["W"]))

        print(f"  Episode {ep:>2}/{episodes} | "
              f"平均等待: {avg_w:>6.1f}s | "
              f"通過: {len(vehicles_done):>4}台 | "
              f"佇列 N:{np.mean(ep_queues['N']):.1f} "
              f"E:{np.mean(ep_queues['E']):.1f} "
              f"S:{np.mean(ep_queues['S']):.1f} "
              f"W:{np.mean(ep_queues['W']):.1f}")

    return {
        "method":        "DQN",
        "avg_waiting":   all_avg_waiting,
        "throughput":    all_throughput,
        "queue_n": all_queue_n, "queue_e": all_queue_e,
        "queue_s": all_queue_s, "queue_w": all_queue_w,
        "mean_waiting":    np.mean(all_avg_waiting),
        "mean_throughput": np.mean(all_throughput),
        "mean_queue":      np.mean(all_queue_n + all_queue_e +
                                   all_queue_s + all_queue_w),
    }


# ============================================================
# 方法 2：Fixed-Time 評估
# ============================================================
def evaluate_fixed(episodes):
    print("\n" + "="*60)
    print(f"⏱️  評估 Fixed-Time（每相位 {FIXED_GREEN} 秒）...")
    print("="*60)

    all_avg_waiting  = []
    all_throughput   = []
    all_queue_n      = []
    all_queue_e      = []
    all_queue_s      = []
    all_queue_w      = []

    for ep in range(1, episodes + 1):
        tls_id, num_phases, program_id = start_sumo()
        traci.trafficlight.setPhase(tls_id, 0)

        step_count    = 10
        phase_timer   = 0
        current_phase = 0
        vehicles_done = set()
        ep_avg_waits  = []
        ep_queues     = {"N":[], "E":[], "S":[], "W":[]}

        while step_count < MAX_STEPS:
            traci.simulationStep()
            step_count  += 1
            phase_timer += 1

            aw = get_avg_waiting()
            if aw > 0:
                ep_avg_waits.append(aw)

            q = get_queue_lengths()
            ep_queues["N"].append(q["north_in_0"])
            ep_queues["E"].append(q["east_in_0"])
            ep_queues["S"].append(q["south_in_0"])
            ep_queues["W"].append(q["west_in_0"])

            for v in traci.simulation.getArrivedIDList():
                vehicles_done.add(v)

            # Fixed-Time 切換
            if phase_timer >= FIXED_GREEN:
                phase_timer = 0
                current_phase = do_phase_change(
                    tls_id, program_id, current_phase, num_phases)
                step_count += YELLOW_TIME + ALL_RED_TIME

            if traci.simulation.getMinExpectedNumber() <= 0:
                break

        try:
            traci.close()
        except:
            pass

        avg_w = np.mean(ep_avg_waits) if ep_avg_waits else 0
        all_avg_waiting.append(avg_w)
        all_throughput.append(len(vehicles_done))
        all_queue_n.append(np.mean(ep_queues["N"]))
        all_queue_e.append(np.mean(ep_queues["E"]))
        all_queue_s.append(np.mean(ep_queues["S"]))
        all_queue_w.append(np.mean(ep_queues["W"]))

        print(f"  Episode {ep:>2}/{episodes} | "
              f"平均等待: {avg_w:>6.1f}s | "
              f"通過: {len(vehicles_done):>4}台 | "
              f"佇列 N:{np.mean(ep_queues['N']):.1f} "
              f"E:{np.mean(ep_queues['E']):.1f} "
              f"S:{np.mean(ep_queues['S']):.1f} "
              f"W:{np.mean(ep_queues['W']):.1f}")

    return {
        "method":        "Fixed-Time",
        "avg_waiting":   all_avg_waiting,
        "throughput":    all_throughput,
        "queue_n": all_queue_n, "queue_e": all_queue_e,
        "queue_s": all_queue_s, "queue_w": all_queue_w,
        "mean_waiting":    np.mean(all_avg_waiting),
        "mean_throughput": np.mean(all_throughput),
        "mean_queue":      np.mean(all_queue_n + all_queue_e +
                                   all_queue_s + all_queue_w),
    }


# ============================================================
# 產出比較圖
# ============================================================
def plot_comparison(dqn, fixed):
    eps = list(range(1, EVAL_EPISODES + 1))
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("DQN vs Fixed-Time 號誌控制效能比較", fontsize=15, fontweight='bold')

    c_dqn   = "#4A9EFF"
    c_fixed = "#E63946"

    # 圖 1：平均等待時間
    ax = axes[0]
    ax.plot(eps, dqn["avg_waiting"],   color=c_dqn,   marker='o', lw=2, ms=6,
            label=f'DQN（均 {dqn["mean_waiting"]:.1f}s）')
    ax.plot(eps, fixed["avg_waiting"], color=c_fixed, marker='s', lw=2, ms=6,
            linestyle='--', label=f'Fixed-Time（均 {fixed["mean_waiting"]:.1f}s）')
    ax.set_title("平均等待時間（越低越好）")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Avg Waiting Time (s)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 圖 2：吞吐量
    ax = axes[1]
    ax.plot(eps, dqn["throughput"],   color=c_dqn,   marker='o', lw=2, ms=6,
            label=f'DQN（均 {dqn["mean_throughput"]:.0f}台）')
    ax.plot(eps, fixed["throughput"], color=c_fixed, marker='s', lw=2, ms=6,
            linestyle='--', label=f'Fixed-Time（均 {fixed["mean_throughput"]:.0f}台）')
    ax.set_title("通過車輛數 / 吞吐量（越高越好）")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Throughput (vehicles)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 圖 3：改善幅度
    ax = axes[2]
    w_imp = (fixed["mean_waiting"] - dqn["mean_waiting"]) / max(fixed["mean_waiting"], 1) * 100
    t_imp = (dqn["mean_throughput"] - fixed["mean_throughput"]) / max(fixed["mean_throughput"], 1) * 100

    labels = ["等待時間改善%", "吞吐量提升%"]
    values = [w_imp, t_imp]
    colors = ["#06D6A0" if v > 0 else "#E63946" for v in values]

    bars = ax.bar(labels, values, color=colors, width=0.4, edgecolor='white')
    ax.axhline(0, color='gray', lw=0.8)
    ax.set_title("DQN 相較 Fixed-Time 改善幅度")
    ax.set_ylabel("改善幅度 (%)")
    ax.grid(True, alpha=0.3, axis='y')

    for bar, val in zip(bars, values):
        ypos = bar.get_height() + 0.5 if val >= 0 else bar.get_height() - 2
        ax.text(bar.get_x() + bar.get_width()/2., ypos,
                f'{val:+.1f}%', ha='center', va='bottom',
                fontsize=13, fontweight='bold')

    plt.tight_layout()
    out = os.path.join(BASE_DIR, "comparison_results.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"\n📊 比較圖已儲存：{out}")
    plt.show()


# ============================================================
# 產出文字報告
# ============================================================
def save_report(dqn, fixed):
    w_imp = (fixed["mean_waiting"] - dqn["mean_waiting"]) / max(fixed["mean_waiting"], 1) * 100
    t_imp = (dqn["mean_throughput"] - fixed["mean_throughput"]) / max(fixed["mean_throughput"], 1) * 100

    report = f"""
============================================================
  DQN vs Fixed-Time 號誌控制效能評估報告
============================================================
評估設定：{EVAL_EPISODES} 局 | 每局最長 {MAX_STEPS} 秒

  方法              | 平均等待時間(s) | 平均吞吐量(台) | 平均佇列(台)
  Fixed-Time        | {fixed['mean_waiting']:>15.1f} | {fixed['mean_throughput']:>14.0f} | {fixed['mean_queue']:>12.1f}
  DQN（本研究）     | {dqn['mean_waiting']:>15.1f} | {dqn['mean_throughput']:>14.0f} | {dqn['mean_queue']:>12.1f}

改善結果（DQN vs Fixed-Time）：
  等待時間：{w_imp:+.1f}%
  吞吐量：  {t_imp:+.1f}%
============================================================
"""
    out = os.path.join(BASE_DIR, "comparison_results.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"📄 報告已儲存：{out}")


# ============================================================
# 主程式
# ============================================================
def main():
    print("=" * 60)
    print("📊 開始評估：DQN vs Fixed-Time")
    print(f"   每個方法跑 {EVAL_EPISODES} 局，預計約 {EVAL_EPISODES * 4} 分鐘")
    print("=" * 60)

    t0 = time.time()

    dqn   = evaluate_dqn(EVAL_EPISODES)
    fixed = evaluate_fixed(EVAL_EPISODES)

    save_report(dqn, fixed)
    plot_comparison(dqn, fixed)

    print(f"\n⏱️  總耗時：{time.time()-t0:.0f} 秒")


if __name__ == "__main__":
    main()
