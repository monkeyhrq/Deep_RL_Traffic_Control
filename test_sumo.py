"""
test_sumo.py
測試 SUMO 是否能正常透過 TraCI 啟動並運行

執行方式：
    python test_sumo.py

成功的話會看到：
    - SUMO 模擬跑 100 步
    - 每 10 步顯示一次車輛數量
    - 最後顯示「測試成功！」
"""

import os
import sys
import traci
import sumolib

# ============================================================
# 設定 SUMO 路徑
# ============================================================
# 確認 SUMO_HOME 環境變數有設定
if "SUMO_HOME" not in os.environ:
    # 如果沒有，嘗試常見的預設路徑
    default_path = r"C:\Program Files (x86)\Eclipse\Sumo"
    if os.path.exists(default_path):
        os.environ["SUMO_HOME"] = default_path
        print(f"⚠️  自動設定 SUMO_HOME = {default_path}")
    else:
        print("❌ 找不到 SUMO！請確認：")
        print("   1. SUMO 已安裝")
        print("   2. 環境變數 SUMO_HOME 已設定")
        sys.exit(1)

SUMO_HOME = os.environ["SUMO_HOME"]
print(f"✅ SUMO_HOME = {SUMO_HOME}")

# ============================================================
# 設定模擬檔案路徑
# ============================================================
# 取得目前這個 .py 檔案所在的資料夾
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUMO_CFG = os.path.join(BASE_DIR, "sumo", "simulation.sumocfg")

print(f"✅ 設定檔路徑 = {SUMO_CFG}")

# 確認設定檔存在
if not os.path.exists(SUMO_CFG):
    print(f"❌ 找不到 {SUMO_CFG}")
    print("   請確認 sumo/ 資料夾內有所有必要檔案")
    sys.exit(1)

# ============================================================
# 啟動 SUMO 模擬
# ============================================================
print("\n🚦 啟動 SUMO 模擬...")

# SUMO 啟動指令（不開 GUI，純後台跑）
sumo_cmd = [
    "sumo",              # 不開 GUI（訓練時用這個比較快）
    "-c", SUMO_CFG,      # 設定檔
    "--no-warnings",     # 不顯示警告（減少雜訊）
    "--no-step-log",     # 不顯示每步 log
]

try:
    # 用 TraCI 啟動 SUMO
    traci.start(sumo_cmd)
    print("✅ SUMO 啟動成功！")
    
    # ============================================================
    # 跑 100 步模擬
    # ============================================================
    print("\n📊 開始模擬（共 100 步）：")
    print("-" * 40)
    
    for step in range(100):
        # 讓 SUMO 前進一步（1 秒）
        traci.simulationStep()
        
        # 每 10 步顯示一次資訊
        if step % 10 == 0:
            # 取得目前路口的所有車輛
            vehicles = traci.vehicle.getIDList()
            vehicle_count = len(vehicles)
            
            # 取得紅綠燈狀態
            tls_list = traci.trafficlight.getIDList()
            if tls_list:
                tls_id = tls_list[0]
                tls_phase = traci.trafficlight.getPhase(tls_id)
                tls_state = traci.trafficlight.getRedYellowGreenState(tls_id)
            else:
                tls_phase = "N/A"
                tls_state = "N/A"
            
            print(f"Step {step:3d} | "
                  f"車輛數: {vehicle_count:3d} | "
                  f"號誌相位: {tls_phase} | "
                  f"號誌狀態: {tls_state}")
    
    print("-" * 40)
    
    # ============================================================
    # 關閉 SUMO
    # ============================================================
    traci.close()
    
    print("\n" + "=" * 50)
    print("🎉 測試成功！SUMO + TraCI 運作正常！")
    print("=" * 50)
    print("\n可以進入 Phase 3 開始寫 DQN Agent 了！")

except Exception as e:
    print(f"\n❌ 發生錯誤：{e}")
    print("\n可能的原因：")
    print("1. intersection.net.xml 還沒產生 → 先執行 build_network.bat")
    print("2. SUMO 環境變數沒設好 → 重新設定 SUMO_HOME")
    print("3. 模擬設定檔路徑錯誤 → 確認 sumo/ 資料夾位置")
    
    try:
        traci.close()
    except:
        pass
