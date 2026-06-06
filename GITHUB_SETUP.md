# GitHub 完整設置指南 🚀

**目標**: 將 3dprint-monitor 上傳到 GitHub  
**時間**: 10-15 分鐘  
**難度**: 簡單

---

## 📋 前置準備

### **1. GitHub 帳戶**
- 沒有?去 https://github.com/signup 註冊 (免費)

### **2. 安裝 Git**
```bash
# Windows 下載安裝
https://git-scm.com/download/win

# 驗證
git --version
```

### **3. 設置 Git 用戶信息**
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@gmail.com"
```

---

## 🔑 GitHub 認證設置

### **方法 A: Personal Access Token (推薦)**

#### 在 GitHub 上生成 Token:
1. 登入 GitHub → 右上角頭像 → **Settings**
2. 左側 → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. 點 **Generate new token** → **Generate new token (classic)**
4. 填入:
   - Note: `3dprint-monitor`
   - Expiration: 90 days (或更長)
   - Scopes: 勾選 `repo` (完整 repo 訪問)
5. 點 **Generate token**，**複製 token** (只會顯示一次!)

#### 在 Git 中使用:
```bash
# 將此 token 存儲為全局認證
git config --global user.email "your.email@gmail.com"

# 首次 push 時會要求密碼，輸入:
# 用戶名: [GitHub 用戶名]
# 密碼: [剛才複製的 token]

# 或直接輸入 URL (包含 token):
git remote set-url origin https://[token]@github.com/[username]/3dprint-monitor.git
```

### **方法 B: SSH 密鑰 (高級)**

```bash
# 生成 SSH 密鑰
ssh-keygen -t ed25519 -C "your.email@gmail.com"

# 複製公鑰
cat ~/.ssh/id_ed25519.pub

# 在 GitHub 上添加:
Settings → SSH and GPG keys → New SSH key
# 貼入公鑰，點 Add SSH key
```

---

## 📝 第一次上傳到 GitHub

### **步驟 1: 在 GitHub 建立倉庫**

1. 登入 GitHub
2. 點右上角 **+** → **New repository**
3. 填入:
   ```
   Repository name: 3dprint-monitor
   Description: 3D Printer Monitoring System for Bambu Lab and Creality K1C
   Public/Private: Public
   ✅ Add a README file
   ✅ Add .gitignore (選 Python)
   ✅ Choose a license (MIT)
   ```
4. 點 **Create repository**

### **步驟 2: Windows 上初始化 Git**

```bash
# 進入專案目錄
cd D:\3dprint

# 初始化 git
git init

# 設置用戶 (如果還沒設置全局)
git config user.name "Your Name"
git config user.email "your.email@gmail.com"

# 查看狀態
git status
```

### **步驟 3: 添加檔案到 Git**

```bash
# 添加所有檔案
git add .

# 或只添加特定檔案
git add src/ config/ tools/ *.md *.txt *.bat *.ps1

# 確認要添加的檔案
git status
```

### **步驟 4: 第一次提交**

```bash
git commit -m "Initial commit: 3D Printer Monitoring System

- Add support for Bambu Lab and Creality K1C printers
- Include Windows and Raspberry Pi deployment guides
- Add API server and monitoring system
- Include diagnostic and management tools"
```

### **步驟 5: 連接到 GitHub**

```bash
# 添加遠程倉庫
git remote add origin https://github.com/[你的用戶名]/3dprint-monitor.git

# 驗證
git remote -v
```

### **步驟 6: 上傳到 GitHub**

```bash
# 重命名分支為 main (GitHub 預設)
git branch -M main

# 上傳
git push -u origin main

# 首次上傳會要求認證，輸入:
# 用戶名: [GitHub 用戶名]
# 密碼: [Personal Access Token]
```

### **步驟 7: 驗證上傳**

訪問: https://github.com/[你的用戶名]/3dprint-monitor

應該看到所有檔案已上傳！

---

## 🔄 後續更新流程

修改代碼後，簡單三步更新 GitHub:

```bash
# 1. 查看變更
git status

# 2. 提交變更
git add .
git commit -m "Update: 修改說明"

# 3. 推送到 GitHub
git push
```

---

## 📥 在樹梅派上安裝

### **首次安裝**

```bash
# 樹梅派上
cd /home/pi
git clone https://github.com/[你的用戶名]/3dprint-monitor.git 3dprint
cd 3dprint
bash deploy_raspberry_pi.sh
```

### **更新到最新版本**

```bash
cd /home/pi/3dprint
git pull origin main
sudo systemctl restart printer-monitor
```

---

## 🛠️ 常用 Git 命令

```bash
# 查看提交歷史
git log --oneline -10

# 查看變更
git diff

# 查看分支
git branch

# 創建新分支
git checkout -b feature/新功能

# 切換分支
git checkout main

# 合併分支
git merge feature/新功能

# 刪除分支
git branch -d feature/新功能

# 撤銷最後一個提交 (未推送)
git reset --soft HEAD~1

# 查看遠程倉庫
git remote -v
```

---

## 📦 .gitignore 設置

建立 `.gitignore` 檔案，排除不需要上傳的檔案:

```bash
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 系統
.DS_Store
Thumbs.db

# 環境
.env
.env.local

# 數據和日誌
*.log
printer_monitor.log*
data/*.jsonl
data/*.json
downloads/
snapshots/

# 敏感信息
credentials.json
secrets.json
```

---

## 🔐 安全檢查清單

上傳前確認:

- [ ] 沒有敏感信息 (密碼、API 密鑰)
- [ ] 沒有大檔案 (>100MB)
- [ ] `.gitignore` 設置正確
- [ ] README 清晰完整
- [ ] 代碼有註解

### **查找敏感信息**

```bash
# 搜索常見敏感詞
grep -r "password\|secret\|api_key\|token" D:\3dprint

# 檢查是否有 .env 檔
dir D:\3dprint\.env*
```

---

## 📊 GitHub 頁面設置 (可選)

### **啟用 GitHub Pages**

1. Repository → **Settings** → **Pages**
2. Source: **main** (或 docs 分支)
3. 選擇主題
4. 點 **Save**

### **添加徽章到 README**

```markdown
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-green)](https://www.raspberrypi.com/)
```

---

## 🚀 分享你的倉庫

### **GitHub 連結**
```
https://github.com/[用戶名]/3dprint-monitor
```

### **在 Raspberry Pi 上安裝**
```bash
git clone https://github.com/[用戶名]/3dprint-monitor.git 3dprint
cd 3dprint
bash deploy_raspberry_pi.sh
```

### **分享到社群**
- Reddit: r/3Dprinting
- Discord: 3D Printing 伺服器
- GitHub Topics: 3dprinter, home-automation

---

## 📞 GitHub Issues 和 Discussions

### **啟用 Discussions**

Settings → **General** → **Features** → ✅ **Discussions**

這允許用戶:
- 提出問題
- 分享想法
- 討論功能

### **管理 Issues**

用戶可以報告 bug:
```
Template:
## Bug Description
## Steps to Reproduce
## Expected vs Actual
## System Info
```

---

## ✅ 完成檢查清單

- [ ] GitHub 帳戶已建立
- [ ] Git 已安裝並配置
- [ ] 倉庫已在 GitHub 建立
- [ ] 代碼已初始化為 git 倉庫
- [ ] 檔案已提交
- [ ] Remote 已添加
- [ ] 代碼已推送到 GitHub
- [ ] README 已更新
- [ ] 樹梅派上已測試 `git clone`

---

## 🎉 完成！

你的 3dprint-monitor 現在在 GitHub 上！

### **下一步:**
1. 告訴同事 GitHub 連結
2. 他們可以隨時用一行命令安裝到樹梅派
3. 你可以隨時推送更新，他們用 `git pull` 同步

### **分享命令:**
```bash
# 給任何人使用
git clone https://github.com/[你的用戶名]/3dprint-monitor.git 3dprint
cd 3dprint
bash deploy_raspberry_pi.sh
```

---

**GitHub 設置完成！🎊**

需要幫助嗎？建立 Issue 或檢查 [Discussions](https://github.com/[用戶名]/3dprint-monitor/discussions)
