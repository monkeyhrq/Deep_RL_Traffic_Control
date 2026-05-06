"""
env.py - SUMO 交通環境包裝

把 SUMO 模擬器包裝成強化學習環境
定義 State / Action / Reward
"""

import os
import sys
import numpy as np
import traci

# ============================================================
# 常數設定
# ============================================================
# 安全約束
MIN_GREEN_TIME = 10    # 最小綠燈時間（秒）
YELLOW_TIME    = 3     # 黃燈時間（秒）
ALL_RED_TIME   = 1     # 全紅清空時間（秒）
DECISION_STEP  = 5     # 每幾秒做一次決策

# 狀態空間維度
STATE_DIM = 5   # [Q_N, Q_E, Q_S, Q_W, φₜ]

# 動作空間維度
ACTION_DIM = 2  # 0=Keep, 1=Change


class TrafficEnv:
    def __init__(self, cfg_path: str, use_gui: bool = False):
        self.cfg_path  = cfg_path
        self.use_gui   = use_gui
        self.step_count = 0          
        self.green_time = 0          
        self.current_phase = 0       
        self.episode_waiting = 0.0   
        self._tls_id = None          
        self.num_phases = 1          # 新增：紀錄該路口實際的相位總數
        self._program_id = None      # 新增：用來記錄原始的紅綠燈程式 ID

    def reset(self) -> np.ndarray:
        try:
            traci.close()
        except:
            pass

        sumo_binary = "sumo-gui" if self.use_gui else "sumo"
        sumo_cmd = [
            sumo_binary,
            "-c", self.cfg_path,
            "--no-warnings",
            "--no-step-log",
            "--waiting-time-memory", "1000",
        ]

        traci.start(sumo_cmd)

        tls_list = traci.trafficlight.getIDList()
        if len(tls_list) == 0:
            raise RuntimeError("找不到紅綠燈！請確認路網設定正確")
        self._tls_id = tls_list[0]

        # ── 新增：記錄原本的 program ID 並自動取得相位數量 ──
        self._program_id = traci.trafficlight.getProgram(self._tls_id)
        logic = traci.trafficlight.getAllProgramLogics(self._tls_id)[0]
        self.num_phases = len(logic.phases)
        print(f"🚥 偵測到路口 {self._tls_id} 共有 {self.num_phases} 個相位 (Program ID: {self._program_id})")
        if self.num_phases <= 1:
            print("⚠️ 警告：該路口只有 1 個相位，模型無法切換燈號！請檢查 SUMO 的 .net.xml 設定。")
        # ──────────────────────────────────────────

        self.step_count      = 0
        self.green_time      = 0
        self.current_phase   = 0
        self.episode_waiting = 0.0

        traci.trafficlight.setPhase(self._tls_id, self.current_phase)

        for _ in range(10):
            traci.simulationStep()
        self.step_count = 10

        return self._get_state()

    def step(self, action: int):
        if action == 1 and self.green_time < MIN_GREEN_TIME:
            action = 0  

        if action == 1:
            self._do_phase_change()

        total_waiting = 0.0
        for _ in range(DECISION_STEP):
            traci.simulationStep()
            self.step_count  += 1
            self.green_time  += 1

            total_waiting += self._get_total_waiting_time()

            if traci.simulation.getMinExpectedNumber() <= 0:
                break

        reward = -total_waiting  
        self.episode_waiting += total_waiting
        next_state = self._get_state()
        
        done = (traci.simulation.getMinExpectedNumber() <= 0 or
                self.step_count >= 3600)

        return next_state, reward, done

    def close(self):
        try:
            traci.close()
        except:
            pass

    def _get_state(self) -> np.ndarray:
        lane_map = {
            "N": "north_in_0",
            "E": "east_in_0",
            "S": "south_in_0",
            "W": "west_in_0",
        }

        queue = []
        for direction, lane_id in lane_map.items():
            try:
                q = traci.lane.getLastStepHaltingNumber(lane_id)
            except:
                q = 0
            queue.append(float(q))

        try:
            phase = float(traci.trafficlight.getPhase(self._tls_id))
        except:
            phase = float(self.current_phase)

        state = np.array(queue + [phase], dtype=np.float32)
        return state

    def _get_total_waiting_time(self) -> float:
        total = 0.0
        for veh_id in traci.vehicle.getIDList():
            total += traci.vehicle.getAccumulatedWaitingTime(veh_id)
        return total

    def _do_phase_change(self):
        # ── 新增防呆：如果只有一個相位，就直接返回，避免報錯 ──
        if self.num_phases <= 1:
            return
        # ────────────────────────────────────────────────────────

        yellow_state = "y" * len(
            traci.trafficlight.getRedYellowGreenState(self._tls_id)
        )
        all_red_state = "r" * len(yellow_state)

        traci.trafficlight.setRedYellowGreenState(self._tls_id, yellow_state)
        for _ in range(YELLOW_TIME):
            traci.simulationStep()
            self.step_count += 1

        traci.trafficlight.setRedYellowGreenState(self._tls_id, all_red_state)
        for _ in range(ALL_RED_TIME):
            traci.simulationStep()
            self.step_count += 1

        # ── 核心修正：在設定新相位之前，先切回原本的紅綠燈程式，解除 "online" 覆蓋 ──
        traci.trafficlight.setProgram(self._tls_id, self._program_id)
        # ─────────────────────────────────────────────────────────────────────────

        self.current_phase = (self.current_phase + 1) % self.num_phases
        traci.trafficlight.setPhase(self._tls_id, self.current_phase)

        self.green_time = 0

    @property
    def state_dim(self) -> int:
        return STATE_DIM

    @property
    def action_dim(self) -> int:
        return ACTION_DIM

    def get_episode_waiting(self) -> float:
        return self.episode_waiting