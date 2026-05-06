"""
env.py - SUMO 交通環境包裝

把 SUMO 模擬器包裝成強化學習環境
定義 State / Action / Reward

State：  sₜ = [Q_N, Q_E, Q_S, Q_W, φₜ] ← 5 維向量
Action： {0: Keep, 1: Change}
Reward： rₜ = -Σ wₗ(t)  (所有車道累積等待時間的負值)
"""

import os
import sys
import numpy as np
import traci

# ============================================================
# 常數設定
# ============================================================
# 紅綠燈 ID（SUMO 自動產生的 ID 通常是 'center' 或 'cluster...'）
TLS_ID = "center"

# 安全約束
MIN_GREEN_TIME = 10    # 最小綠燈時間（秒）
YELLOW_TIME    = 3     # 黃燈時間（秒）
ALL_RED_TIME   = 1     # 全紅清空時間（秒）
DECISION_STEP  = 5     # 每幾秒做一次決策

# 號誌相位數量（四向路口通常有 4 個相位）
NUM_PHASES = 4

# 狀態空間維度
STATE_DIM = 5   # [Q_N, Q_E, Q_S, Q_W, φₜ]

# 動作空間維度
ACTION_DIM = 2  # 0=Keep, 1=Change


class TrafficEnv:
    """
    SUMO 交通路口強化學習環境

    使用方式：
        env = TrafficEnv()
        state = env.reset()
        for _ in range(1000):
            action = agent.select_action(state)
            next_state, reward, done = env.step(action)
            state = next_state
            if done:
                break
        env.close()
    """

    def __init__(self, cfg_path: str, use_gui: bool = False):
        """
        初始化環境

        Args:
            cfg_path:  SUMO 設定檔路徑（simulation.sumocfg）
            use_gui:   是否開啟 SUMO 視覺化介面（訓練時建議 False）
        """
        self.cfg_path  = cfg_path
        self.use_gui   = use_gui
        self.step_count = 0          # 目前模擬步數
        self.green_time = 0          # 當前相位已持續的綠燈時間
        self.current_phase = 0       # 當前號誌相位
        self.episode_waiting = 0.0   # 這個 episode 的累積等待時間
        self._tls_id = None          # 實際的紅綠燈 ID（啟動後取得）

    # ----------------------------------------------------------
    # reset：開始新的一局模擬
    # ----------------------------------------------------------
    def reset(self) -> np.ndarray:
        """
        重置環境，開始新的 episode

        Returns:
            state: 初始狀態向量（5 維）
        """
        # 如果 SUMO 已在跑，先關閉
        try:
            traci.close()
        except:
            pass

        # 組合 SUMO 啟動指令
        sumo_binary = "sumo-gui" if self.use_gui else "sumo"
        sumo_cmd = [
            sumo_binary,
            "-c", self.cfg_path,
            "--no-warnings",
            "--no-step-log",
            "--waiting-time-memory", "1000",  # 記憶等待時間的時間窗口
        ]

        # 啟動 SUMO
        traci.start(sumo_cmd)

        # 取得紅綠燈 ID
        tls_list = traci.trafficlight.getIDList()
        if len(tls_list) == 0:
            raise RuntimeError("找不到紅綠燈！請確認路網設定正確")
        self._tls_id = tls_list[0]

        # 重置計數器
        self.step_count      = 0
        self.green_time      = 0
        self.current_phase   = 0
        self.episode_waiting = 0.0

        # 設定初始相位
        traci.trafficlight.setPhase(self._tls_id, self.current_phase)

        # 跑幾步讓車輛進入路口
        for _ in range(10):
            traci.simulationStep()
        self.step_count = 10

        return self._get_state()

    # ----------------------------------------------------------
    # step：執行一個動作
    # ----------------------------------------------------------
    def step(self, action: int):
        """
        執行動作，讓模擬前進 DECISION_STEP 秒

        Args:
            action: 0 = Keep（維持當前相位）
                    1 = Change（切換到下一相位）

        Returns:
            next_state: 下一個狀態（5 維向量）
            reward:     即時獎勵（負的累積等待時間）
            done:       是否結束（模擬時間到）
        """
        # ── 安全約束：最小綠燈時間 ──
        if action == 1 and self.green_time < MIN_GREEN_TIME:
            action = 0  # 強制維持，不切換

        # ── 執行動作 ──
        if action == 1:
            # 插入黃燈過渡
            self._do_phase_change()
        # action == 0 就什麼都不做（維持當前相位）

        # ── 讓模擬跑 DECISION_STEP 秒 ──
        total_waiting = 0.0
        for _ in range(DECISION_STEP):
            traci.simulationStep()
            self.step_count  += 1
            self.green_time  += 1

            # 累加這一步的等待時間
            total_waiting += self._get_total_waiting_time()

            # 檢查模擬是否結束
            if traci.simulation.getMinExpectedNumber() <= 0:
                break

        # ── 計算 Reward ──
        reward = -total_waiting  # 等待越久，懲罰越大

        self.episode_waiting += total_waiting

        # ── 取得下一個狀態 ──
        next_state = self._get_state()

        # ── 判斷是否結束 ──
        # SUMO 模擬時間到，或路上沒有車了
        done = (traci.simulation.getMinExpectedNumber() <= 0 or
                self.step_count >= 3600)

        return next_state, reward, done

    # ----------------------------------------------------------
    # close：關閉模擬
    # ----------------------------------------------------------
    def close(self):
        """關閉 SUMO 模擬"""
        try:
            traci.close()
        except:
            pass

    # ----------------------------------------------------------
    # 內部方法
    # ----------------------------------------------------------
    def _get_state(self) -> np.ndarray:
        """
        取得目前的狀態向量

        Returns:
            state: [Q_N, Q_E, Q_S, Q_W, φₜ]（5 維 float32）
        """
        # 取得四個方向進入路口的車道 ID
        # SUMO 的車道 ID 格式：edge_id + "_" + lane_index
        lane_map = {
            "N": "north_in_0",
            "E": "east_in_0",
            "S": "south_in_0",
            "W": "west_in_0",
        }

        queue = []
        for direction, lane_id in lane_map.items():
            try:
                # 取得停等車輛數（速度 < 0.1 m/s 視為停等）
                q = traci.lane.getLastStepHaltingNumber(lane_id)
            except:
                q = 0
            queue.append(float(q))

        # 取得當前號誌相位
        try:
            phase = float(traci.trafficlight.getPhase(self._tls_id))
        except:
            phase = float(self.current_phase)

        # 組合成狀態向量
        state = np.array(queue + [phase], dtype=np.float32)
        return state

    def _get_total_waiting_time(self) -> float:
        """
        取得所有車輛的累積等待時間總和

        Returns:
            total_waiting: 所有車輛等待時間的加總（秒）
        """
        total = 0.0
        for veh_id in traci.vehicle.getIDList():
            total += traci.vehicle.getAccumulatedWaitingTime(veh_id)
        return total

    def _do_phase_change(self):
        """
        執行號誌相位切換（含黃燈過渡）
        1. 先插入黃燈（YELLOW_TIME 秒）
        2. 再插入全紅（ALL_RED_TIME 秒）
        3. 切換到下一個相位
        """
        # 黃燈相位（在 SUMO 中，黃燈通常是下一個相位 + 1 或特定設定）
        # 這裡用簡單方式：直接設定短暫的黃燈狀態
        yellow_state = "y" * len(
            traci.trafficlight.getRedYellowGreenState(self._tls_id)
        )
        all_red_state = "r" * len(yellow_state)

        # 黃燈
        traci.trafficlight.setRedYellowGreenState(self._tls_id, yellow_state)
        for _ in range(YELLOW_TIME):
            traci.simulationStep()
            self.step_count += 1

        # 全紅
        traci.trafficlight.setRedYellowGreenState(self._tls_id, all_red_state)
        for _ in range(ALL_RED_TIME):
            traci.simulationStep()
            self.step_count += 1

        # 切換到下一個相位
        self.current_phase = (self.current_phase + 1) % NUM_PHASES
        traci.trafficlight.setPhase(self._tls_id, self.current_phase)

        # 重置綠燈計時
        self.green_time = 0

    @property
    def state_dim(self) -> int:
        """狀態空間維度"""
        return STATE_DIM

    @property
    def action_dim(self) -> int:
        """動作空間維度"""
        return ACTION_DIM

    def get_episode_waiting(self) -> float:
        """取得這個 episode 的總累積等待時間"""
        return self.episode_waiting
