"""
demo_compare.py - Fixed-Time vs AI 即時對比展示

執行方式：
    python demo_compare.py

會做兩件事：
1. 先跑 Fixed-Time 號誌 300 秒，顯示即時狀態
2. 再跑 AI（Double DQN）號誌 300 秒，顯示即時狀態
3. 最後產出對比圖（demo_comparison.png）

錄影建議：
    用 Win + Alt + R 錄下整個畫面
    讓觀眾看到兩個版本的差異
"""

import os
import sys
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
DEMO_STEPS   = 600    # 每個版本跑幾秒（600秒 = 10分鐘）
FIXED_GREEN  = 42     # Fixed-Time 每相位綠燈秒數（與 SUMO 預設號誌一致）
MIN_GREEN    = 10     # AI 最小綠燈秒數
DECISION_INT = 5      # AI 決策間隔
YELLOW_TIME  = 3
ALL_RED_TIME = 1
USE_GUI      = True   # 開啟 SUMO GUI
RANDOM_SEED  = 42     # 固定隨機種子（讓兩個版本車流一樣）


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def start_sumo(use_gui=True):
    """啟動 SUMO"""
    try:
        traci.close()
    except:
        pass

    binary = "sumo-gui" if use_gui else "sumo"
    traci.start([
        binary, "-c", SUMO_CFG,
        "--no-warnings", "--no-step-log",
        "--waiting-time-memory", "1000",
        "--seed", str(RANDOM_SEED),   # 固定隨機種子，讓兩個版本車流完全一樣
    ])

    tls_id     = traci.trafficlight.getIDList()[0]
    logic      = traci.trafficlight.getAllProgramLogics(tls_id)[0]
    num_phases = len(logic.phases)
    program_id = traci.trafficlight.getProgram(tls_id)

    for _ in range(10):
        traci.simulationStep()

    return tls_id, num_phases, program_id


def get_queues():
    """取得四向佇列長度"""
    lanes = {
        "N": "north_in_0",
        "E": "east_in_0",
        "S": "south_in_0",
        "W": "west_in_0",
    }
    result = {}
    for d, lane in lanes.items():
        try:
            result[d] = traci.lane.getLastStepHaltingNumber(lane)
        except:
            result[d] = 0
    return result


def get_avg_waiting():
    """取得平均等待時間"""
    vehs = traci.vehicle.getIDList()
    if not vehs:
        return 0.0
    return sum(traci.vehicle.getWaitingTime(v) for v in vehs) / len(vehs)


def do_phase_change(tls_id, program_id, current_phase, num_phases):
    """執行號誌相位切換（含黃燈）"""
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

    # +2 跳過 SUMO 的黃燈相位（相位結構：綠→黃→綠→黃，只跳綠燈）
    current_phase = (current_phase + 2) % num_phases
    traci.trafficlight.setProgram(tls_id, program_id)
    traci.trafficlight.setPhase(tls_id, current_phase)
    return current_phase


def print_status(method, step, total, queues, avg_wait, action_str, phase, vehicles):
    """印出即時狀態（清版重印）"""
    bar_len  = 40
    progress = int((step / total) * bar_len)
    bar      = "█" * progress + "░" * (bar_len - progress)

    # 佇列視覺化（每台車用 ■ 表示，最多 20 個）
    def queue_bar(n):
        filled = min(n, 20)
        return "■" * filled + "□" * (20 - filled) + f" {n}台"

    phase_names = {0: "南北向↕ 綠燈", 2: "東西向↔ 綠燈"}
    phase_str = phase_names.get(int(phase), f"相位 {int(phase)}")

    print("\n" + "="*60)
    if method == "FIXED":
        print(f"  ⏱️  方法一：Fixed-Time 定時號誌（每 {FIXED_GREEN} 秒切換）")
    else:
        print(f"  🤖  方法二：AI Double DQN 智慧號誌")
    print("="*60)
    print(f"  進度：[{bar}] {step}/{total} 秒")
    print(f"  目前號誌：{phase_str}")
    print(f"  AI 決策：{action_str}")
    print(f"  路口車輛：{vehicles} 台")
    print(f"  平均等待：{avg_wait:.1f} 秒/台")
    print()
    print(f"  北向 ↓  {queue_bar(queues['N'])}")
    print(f"  南向 ↑  {queue_bar(queues['S'])}")
    print(f"  東向 ←  {queue_bar(queues['E'])}")
    print(f"  西向 →  {queue_bar(queues['W'])}")
    print("="*60)

    if method == "FIXED":
        print("  💡 定時號誌：不管車多車少，固定每 42 秒切換一次")
    else:
        print("  💡 AI 號誌：根據各方向車輛數，智慧決定何時切換")


# ============================================================
# 方法 1：Fixed-Time 展示
# ============================================================
def run_fixed_time():
    """跑 Fixed-Time 展示，回傳逐步數據"""
    print("\n" + "🔴" * 30)
    print("  開始展示 Fixed-Time 定時號誌...")
    print("  （每 30 秒固定切換，不管車流狀況）")
    print("🔴" * 30)
    time.sleep(2)

    tls_id, num_phases, program_id = start_sumo(use_gui=USE_GUI)
    traci.trafficlight.setPhase(tls_id, 0)

    step          = 10
    phase_timer   = 0
    current_phase = 0
    vehicles_done = set()

    # 記錄數據
    waiting_log = []
    queue_log   = []
    action_log  = []

    while step < DEMO_STEPS:
        traci.simulationStep()
        step       += 1
        phase_timer += 1

        queues   = get_queues()
        avg_wait = get_avg_waiting()
        vehicles = len(traci.vehicle.getIDList())

        waiting_log.append(avg_wait)
        queue_log.append(sum(queues.values()))

        # Fixed-Time 切換邏輯
        action_str = f"維持（還有 {FIXED_GREEN - phase_timer} 秒切換）"
        if phase_timer >= FIXED_GREEN:
            action_str    = "⚡ 時間到！切換號誌"
            phase_timer   = 0
            current_phase = do_phase_change(tls_id, program_id, current_phase, num_phases)
            step += YELLOW_TIME + ALL_RED_TIME
            action_log.append(step)

        for v in traci.simulation.getArrivedIDList():
            vehicles_done.add(v)

        # 每 5 步更新畫面
        if step % 5 == 0:
            clear_screen()
            print_status("FIXED", step, DEMO_STEPS, queues,
                         avg_wait, action_str, current_phase, vehicles)

        if traci.simulation.getMinExpectedNumber() <= 0:
            break

    try:
        traci.close()
    except:
        pass

    avg_wait_total = np.mean(waiting_log) if waiting_log else 0
    print(f"\n  ✅ Fixed-Time 結束！平均等待時間：{avg_wait_total:.1f} 秒/台")
    time.sleep(2)

    return {
        "waiting_log": waiting_log,
        "queue_log":   queue_log,
        "action_log":  action_log,
        "avg_wait":    avg_wait_total,
        "throughput":  len(vehicles_done),
    }


# ============================================================
# 方法 2：AI Double DQN 展示
# ============================================================
def run_ai():
    """跑 AI 展示，回傳逐步數據"""
    print("\n" + "🟢" * 30)
    print("  開始展示 AI Double DQN 智慧號誌...")
    print("  （根據即時車流智慧決策，優先疏散壅塞方向）")
    print("🟢" * 30)
    time.sleep(2)

    # 載入模型
    device = torch.device("cpu")
    model  = QNetwork(state_dim=5, action_dim=2).to(device)
    ckpt   = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(ckpt['policy_net'])
    model.eval()

    tls_id, num_phases, program_id = start_sumo(use_gui=USE_GUI)
    traci.trafficlight.setPhase(tls_id, 0)

    step          = 10
    green_time    = 0
    current_phase = 0
    vehicles_done = set()

    waiting_log = []
    queue_log   = []
    action_log  = []

    while step < DEMO_STEPS:
        # 取得狀態
        queues = get_queues()
        state  = np.array([
            queues["N"], queues["E"], queues["S"], queues["W"],
            float(current_phase)
        ], dtype=np.float32)

        # AI 決策
        with torch.no_grad():
            st     = torch.FloatTensor(state).unsqueeze(0)
            action = model(st).argmax(dim=1).item()

        # 安全約束
        if action == 1 and green_time < MIN_GREEN:
            action = 0

        action_str = "🟢 Keep 維持（車流仍多）" if action == 0 else "🔄 Change 切換（優先疏散壅塞方向）"

        # 執行切換
        if action == 1:
            action_log.append(step)
            current_phase = do_phase_change(tls_id, program_id, current_phase, num_phases)
            step      += YELLOW_TIME + ALL_RED_TIME
            green_time = 0

        # 跑 DECISION_INT 步
        for _ in range(DECISION_INT):
            traci.simulationStep()
            step       += 1
            green_time += 1

            queues   = get_queues()
            avg_wait = get_avg_waiting()
            vehicles = len(traci.vehicle.getIDList())

            waiting_log.append(avg_wait)
            queue_log.append(sum(queues.values()))

            for v in traci.simulation.getArrivedIDList():
                vehicles_done.add(v)

            if traci.simulation.getMinExpectedNumber() <= 0:
                break

        # 每 5 步更新畫面
        if step % 5 == 0:
            clear_screen()
            print_status("AI", step, DEMO_STEPS, queues,
                         avg_wait, action_str, current_phase, vehicles)

        if traci.simulation.getMinExpectedNumber() <= 0:
            break

    try:
        traci.close()
    except:
        pass

    avg_wait_total = np.mean(waiting_log) if waiting_log else 0
    print(f"\n  ✅ AI 結束！平均等待時間：{avg_wait_total:.1f} 秒/台")
    time.sleep(2)

    return {
        "waiting_log": waiting_log,
        "queue_log":   queue_log,
        "action_log":  action_log,
        "avg_wait":    avg_wait_total,
        "throughput":  len(vehicles_done),
    }


# ============================================================
# 產出對比圖
# ============================================================
def plot_demo_comparison(fixed, ai):
    """產出最終對比圖"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Fixed-Time vs AI Double DQN — 即時對比", fontsize=15, fontweight='bold')

    steps_f = list(range(len(fixed["waiting_log"])))
    steps_a = list(range(len(ai["waiting_log"])))

    # 圖 1：等待時間對比
    ax = axes[0]
    ax.plot(steps_f, fixed["waiting_log"], color="#E63946", alpha=0.6,
            linewidth=1.5, label=f'Fixed-Time（均 {fixed["avg_wait"]:.1f}s）')
    ax.plot(steps_a, ai["waiting_log"], color="#4A9EFF", alpha=0.6,
            linewidth=1.5, label=f'AI Double DQN（均 {ai["avg_wait"]:.1f}s）')

    # 標記 AI 切換的時間點
    for t in ai["action_log"]:
        if t < len(ai["waiting_log"]):
            ax.axvline(x=t, color="#4A9EFF", alpha=0.2, linewidth=0.8)

    # 標記 Fixed 切換的時間點
    for t in fixed["action_log"]:
        if t < len(fixed["waiting_log"]):
            ax.axvline(x=t, color="#E63946", alpha=0.2, linewidth=0.8)

    ax.set_title("平均等待時間（越低越好）", fontsize=13)
    ax.set_xlabel("模擬時間（秒）")
    ax.set_ylabel("平均等待時間（秒/台）")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 圖 2：最終結果長條圖
    ax = axes[1]
    methods = ["Fixed-Time\n定時號誌", "AI Double DQN\n智慧號誌"]
    waits   = [fixed["avg_wait"], ai["avg_wait"]]
    colors  = ["#E63946", "#4A9EFF"]
    bars    = ax.bar(methods, waits, color=colors, width=0.4, edgecolor='white')

    # 顯示數值和改善幅度
    improvement = (fixed["avg_wait"] - ai["avg_wait"]) / max(fixed["avg_wait"], 1) * 100
    for bar, val in zip(bars, waits):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05,
                f'{val:.1f}s', ha='center', va='bottom', fontsize=13, fontweight='bold')

    ax.set_title(f"平均等待時間比較\nAI 改善：{improvement:+.1f}%", fontsize=13)
    ax.set_ylabel("平均等待時間（秒/台）")
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, max(waits) * 1.3)

    # 加上改善標註
    ax.annotate(f'↓ {improvement:.1f}%',
                xy=(1, ai["avg_wait"]),
                xytext=(0.5, (fixed["avg_wait"] + ai["avg_wait"]) / 2),
                fontsize=14, color='green', fontweight='bold',
                ha='center',
                arrowprops=dict(arrowstyle='->', color='green'))

    plt.tight_layout()
    out = os.path.join(BASE_DIR, "demo_comparison.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"\n📊 對比圖已儲存：{out}")
    plt.show()


# ============================================================
# 主程式
# ============================================================
def main():
    clear_screen()
    print("=" * 60)
    print("  🚦 Fixed-Time vs AI Double DQN 即時對比展示")
    print("=" * 60)
    print(f"\n  展示設定：")
    print(f"  每個版本跑 {DEMO_STEPS} 秒（10 分鐘）")
    print(f"  Fixed-Time：每 {FIXED_GREEN} 秒固定切換")
    print(f"  AI：根據即時車流智慧決策（最小綠燈 {MIN_GREEN} 秒）")
    print(f"  ✅ 兩個版本使用完全相同的車流（seed={RANDOM_SEED}），公平比較")
    print(f"\n  💡 建議現在開始錄影（Win + Alt + R）")
    print(f"\n  按 Enter 開始...")
    input()

    # 跑 Fixed-Time
    fixed_result = run_fixed_time()

    print("\n" + "="*60)
    print("  Fixed-Time 展示結束！")
    print(f"  平均等待時間：{fixed_result['avg_wait']:.1f} 秒/台")
    print(f"  通過車輛：{fixed_result['throughput']} 台")
    print("\n  按 Enter 開始 AI 展示...")
    input()

    # 跑 AI
    ai_result = run_ai()

    # 最終對比
    clear_screen()
    print("=" * 60)
    print("  📊 最終對比結果")
    print("=" * 60)
    print(f"\n  {'方法':<20} {'平均等待時間':>12} {'通過車輛':>10}")
    print(f"  {'-'*45}")
    print(f"  {'Fixed-Time 定時號誌':<20} {fixed_result['avg_wait']:>10.1f}s {fixed_result['throughput']:>10}台")
    print(f"  {'AI Double DQN':<20} {ai_result['avg_wait']:>10.1f}s {ai_result['throughput']:>10}台")

    improvement = (fixed_result['avg_wait'] - ai_result['avg_wait']) / max(fixed_result['avg_wait'], 1) * 100
    print(f"\n  🎯 AI 改善等待時間：{improvement:+.1f}%")
    print("=" * 60)

    print("\n  產出對比圖中...")
    plot_demo_comparison(fixed_result, ai_result)

    print("\n  💡 建議現在停止錄影（Win + Alt + R）")
    print("  對比圖已存為 demo_comparison.png")


if __name__ == "__main__":
    main()
