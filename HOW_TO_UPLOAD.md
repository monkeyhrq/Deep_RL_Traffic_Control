# 🚀 上傳到 GitHub 完整教學

這份教學適合**完全沒用過 GitHub** 的同學。整個流程約 **10 分鐘**。

---

## 📋 你需要先做的事

### 1️⃣ 註冊 GitHub 帳號
- 前往 https://github.com → 點 **Sign up**
- 用學校信箱註冊（學生帳號可申請免費 Pro）

### 2️⃣ 安裝 Git（如果還沒有）

| 系統 | 下載連結 |
|------|---------|
| **Windows** | https://git-scm.com/download/win |
| **Mac** | `brew install git`（或安裝 Xcode Command Line Tools）|
| **Linux** | `sudo apt install git` |

安裝完開啟終端機輸入確認：
```bash
git --version
# 應該顯示：git version 2.x.x
```

---

## 🎯 方法 A：用 GitHub 網頁直接上傳（推薦給新手 ⭐）

**完全不需要打指令！**

### Step 1：建立新 Repository
1. 登入 GitHub → 右上角 ➕ → **New repository**
2. **Repository name**：`Deep_RL_Traffic_Control`
3. **Description**：`基於深度強化學習的自動化紅綠燈交通控制系統`
4. 選 ✅ **Public**（讓老師看得到）
5. ❌ 先**不要**勾 "Add a README"（因為我們已經有 README 了）
6. 點 **Create repository**

### Step 2：上傳檔案
1. 在新 repo 頁面點 **uploading an existing file**（藍色連結）
2. **拖曳整個 `Deep_RL_Traffic_Control` 資料夾**到頁面上
3. 等待上傳完成（PPT 比較大，可能要 1–2 分鐘）
4. 下方填寫 commit message：`Initial commit: project proposal`
5. 點綠色按鈕 **Commit changes**

✅ 完成！把網址（`https://github.com/<你的帳號>/Deep_RL_Traffic_Control`）貼到作業繳交區

---

## 🎯 方法 B：用 Git 指令上傳（進階）

### Step 1：在 GitHub 建立空 repo（同上 Step 1，但不上傳）

### Step 2：在本地端打開終端機

```bash
# 進入專案資料夾
cd /path/to/Deep_RL_Traffic_Control

# 初始化 Git
git init

# 設定使用者資訊（第一次使用 Git 才需要）
git config --global user.name "你的名字"
git config --global user.email "你的信箱"

# 新增所有檔案
git add .

# 建立第一次 commit
git commit -m "Initial commit: project proposal"

# 改成 main 分支（GitHub 預設）
git branch -M main

# 連接遠端 repo（換成你的網址）
git remote add origin https://github.com/<你的帳號>/Deep_RL_Traffic_Control.git

# 推送到 GitHub
git push -u origin main
```

第一次推送會跳出登入視窗，輸入帳密或 token 即可。

---

## 🎯 方法 C：用 GitHub Desktop（圖形介面，最容易）

1. 下載 **GitHub Desktop**：https://desktop.github.com/
2. 登入 GitHub 帳號
3. 點 **File → Add Local Repository → 選擇 `Deep_RL_Traffic_Control` 資料夾**
4. 點 **Publish repository** → 確認名稱後 publish
5. 完成！

---

## ✅ 上傳後的檢查清單

進入 repo 網頁，確認：

- [ ] README.md 在首頁正確顯示（含徽章、表格、公式）
- [ ] PPT 檔案可以下載
- [ ] docs/ 資料夾下的 4 個 .md 檔都能打開
- [ ] LICENSE、.gitignore、requirements.txt 都在

---

## 🎨 加分技巧（讓 GitHub 看起來更專業）

### 1. 加上 Topics 標籤
進入 repo → 右側 ⚙️ Settings → Topics 加上：
```
reinforcement-learning, dqn, traffic-signal, sumo, smart-city,
deep-learning, pytorch, mdp, intelligent-transportation
```

### 2. 加上 About 描述
右側 ⚙️ → Description 填：
```
🚦 Deep Reinforcement Learning for Adaptive Traffic Signal Control with SUMO + DQN
```

### 3. 設定首頁顯示
有 README 就會自動顯示，但你可以再開啟 GitHub Pages 把專案變成網站：
- Settings → Pages → Source 選 main branch → Save

---

## 🆘 常見問題

**Q1：上傳後 README 沒顯示 LaTeX 公式怎麼辦？**
A：GitHub 從 2022 年起原生支援 `$...$` 與 `$$...$$` 語法，本專案已經使用，會自動渲染。

**Q2：PPT 太大上傳失敗？**
A：GitHub 單檔上限 100MB，你的 PPT 約 1.5MB 沒問題。如果遇到問題，可以用 Git LFS。

**Q3：要怎麼更新檔案？**
A：方法 A 直接在網頁拖檔覆蓋；方法 B 用：
```bash
git add .
git commit -m "Update PPT"
git push
```

**Q4：老師會看到我的修改紀錄嗎？**
A：會！這是 GitHub 的優點，可以證明你有持續更新。每次 commit 都會留下時間戳記。

---

## 🎓 給老師的繳交格式建議

在作業繳交區貼上：
```
GitHub Repository: https://github.com/<你的帳號>/Deep_RL_Traffic_Control
PPT 路徑: /Deep_RL_Traffic_Control_Final.pptx
完整摘要: /docs/ABSTRACT.md
MDP 數學定義: /docs/MDP_FORMULATION.md
YouTube 錄影: [錄影連結]
```

---

祝順利！🚀
