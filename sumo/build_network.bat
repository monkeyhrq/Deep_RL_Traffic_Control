@echo off
REM ================================================
REM build_network.bat
REM 用 SUMO 的 netconvert 工具把 nod.xml + edg.xml
REM 合併成完整的路網檔案 intersection.net.xml
REM ================================================

echo 正在建立 SUMO 路網...
echo.

netconvert ^
    --node-files intersection.nod.xml ^
    --edge-files intersection.edg.xml ^
    --output-file intersection.net.xml ^
    --tls.default-type actuated

echo.
IF %ERRORLEVEL% == 0 (
    echo ✅ 成功！intersection.net.xml 已建立
    echo 現在可以執行 python test_sumo.py 來測試
) ELSE (
    echo ❌ 失敗！請確認 SUMO 有正確安裝並設定環境變數
)

pause
