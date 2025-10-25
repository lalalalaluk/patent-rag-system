# 台灣專利商標開放資料下載教學

## 📋 目錄
- [關於開放資料](#關於開放資料)
- [資料來源](#資料來源)
- [網頁結構說明](#網頁結構說明)
- [下載方式](#下載方式)
  - [方法一：使用 FTP 軟體下載](#方法一使用-ftp-軟體下載)
  - [方法二：爬取下載連結](#方法二爬取下載連結)
  - [方法三：使用程式化批次下載](#方法三使用程式化批次下載)
- [資料集說明](#資料集說明)
- [常見問題](#常見問題)

---

## 關於開放資料

經濟部智慧財產局提供專利與商標的開放資料供民眾免費下載使用，包含：
- 發明專利公開公報
- 發明專利公告公報
- 專利說明書
- 商標註冊案公報
- 其他相關資料

**官方網站**：https://cloud.tipo.gov.tw/S220/opdata/search/trademark

⚠️ **重要提醒**：
- 本系統提供的資料集僅供加值運用，不作為准駁依據
- 所有正式資料請以經濟部智慧財產局公告為準

---

## 資料來源

### 主要資料集網站
- **專利商標開放資料下載**：https://cloud.tipo.gov.tw/S220/opdata
- **商標資料集詳細頁**：https://cloud.tipo.gov.tw/S220/opdata/detail/TrademarkRegXMLA

### 其他參考資源
- 智慧財產局官網：https://www.tipo.gov.tw
- 全球專利檢索系統 (GPSS)：https://gpss.tipo.gov.tw
- 政府資料開放平台：https://data.gov.tw

---

## 網頁結構說明

### 開放資料網站介面

智慧財產局的開放資料網站 (https://cloud.tipo.gov.tw/S220/opdata/detail/TrademarkRegXMLA) 採用 JavaScript 動態渲染，結構如下：

#### 1. 年份選擇器
- 位置：頁面上方
- 顯示格式：「歷史卷期 114 年」
- 功能：下拉選單可選擇不同民國年份（通常從 50 年至今）

#### 2. 期別列表
- **布局**：兩欄式卡片/表格排列
- **每個期別項目包含**：
  - 卷期標題：「第 XX 卷 YY 期」
  - 發布日期：民國年-月-日格式（例：114-10-18）
  - 檔案大小：括號顯示（例：77.22 MB）
  - 下載按鈕：藍色「下載路徑」連結

#### 3. 資料特性
- **卷號規律**：同一年份內卷號通常固定
- **期號排列**：由新到舊排列
- **發布頻率**：約每 2 週發布一期
- **檔案大小**：商標資料每期約 80-130 MB

### 多年份多期資料結構

由於網站包含：
- ✅ **50+ 個年份**（民國 50 年至今）
- ✅ **每年 20+ 期**（依實際公報發布數量）
- ✅ **數千個下載連結**

因此建議使用**自動化工具**批次取得下載連結和檔案。

---

## 下載方式

### 為什麼需要使用 FTP 軟體？

由於智慧財產局提供的開放資料採用 **FTP 傳輸協定**，而目前多數瀏覽器（Chrome、Edge、Firefox 等）已不支援 FTP，使用瀏覽器瀏覽時可能會顯示空白頁面。

**建議使用**：
- FTP 軟體：FileZilla、WinSCP
- 程式化工具：Python、curl 等

---

## 方法一：使用 FTP 軟體下載

### 步驟 1：下載並安裝 FileZilla

1. 前往 [FileZilla 官方網站](https://filezilla-project.org/)
2. 下載 **FileZilla Client**（依您的作業系統選擇）
3. 完成軟體安裝並執行程式

### 步驟 2：複製 FTP 連線資訊

1. 前往 [開放資料網站](https://cloud.tipo.gov.tw/S220/opdata/detail/TrademarkRegXMLA)
2. 選擇您要下載的資料集（例如：商標註冊案公報）
3. 找到特定卷期的下載路徑
4. 在下載路徑上點選滑鼠右鍵
5. 選擇「複製連結網址」

**範例 FTP 網址格式**：
```
ftp://opdata.tipo.gov.tw/TrademarkReg/50/5/
```

### 步驟 3：使用 FileZilla 連線

1. 開啟 FileZilla 軟體
2. 在上方「主機」欄位貼上剛才複製的 FTP 網址
3. 點選「快速連線」按鈕
4. 如果出現確認視窗，點選「確定」

![FileZilla 連線示意](示意圖)

### 步驟 4：下載檔案

1. 連線成功後，右側視窗會顯示 FTP 伺服器上的檔案
2. 選擇您需要的檔案或資料夾
3. 點選滑鼠右鍵選擇「下載」
4. 或直接拖曳檔案到左側的本機資料夾

**下載位置**：
- 左側視窗：您的電腦本機檔案
- 右側視窗：FTP 伺服器檔案

### 步驟 5：解決連線逾時問題（選用）

如果遇到連線逾時的情況：

1. 點選上方選單「編輯」→「設定」
2. 選擇「連線」
3. 在右側輸入框將逾時設定改為 **240 秒**或 **0 秒**（0 表示不限時）
4. 點選「確定」儲存設定

---

## 方法二：爬取下載連結

由於網站有數十個年份、每年數十期，手動複製連結非常耗時。建議使用自動化工具批次取得所有 FTP 下載連結。

### 使用 Playwright 爬取（推薦）

Playwright 可以處理 JavaScript 動態渲染的網頁，適合爬取此網站。

#### 安裝 Playwright

```bash
# 安裝 Playwright
pip install playwright

# 安裝瀏覽器
playwright install chromium
```

#### 爬取腳本範例

```python
from playwright.sync_api import sync_playwright
import json
import time

def scrape_tipo_data(url, output_file='tipo_download_links.json'):
    """
    爬取智慧財產局開放資料網站的所有下載連結
    
    Args:
        url: 資料集網址
        output_file: 輸出的 JSON 檔案名稱
    """
    with sync_playwright() as p:
        # 啟動瀏覽器
        browser = p.chromium.launch(headless=False)  # headless=True 可隱藏瀏覽器視窗
        page = browser.new_page()
        
        print(f"正在訪問網頁: {url}")
        page.goto(url, wait_until='networkidle')
        
        # 等待頁面載入
        time.sleep(3)
        
        all_data = {}
        
        # 找到年份選擇器（需根據實際 HTML 結構調整）
        year_selector = 'select'  # 或其他選擇器
        
        # 取得所有可選年份
        years = page.locator(year_selector + ' option').all_inner_texts()
        print(f"找到 {len(years)} 個年份")
        
        for year_text in years:
            year = year_text.strip().replace('年', '')
            print(f"\n處理年份: {year}")
            
            # 選擇年份
            page.select_option(year_selector, label=year_text)
            time.sleep(2)  # 等待資料載入
            
            # 找到所有期別（根據截圖，下載路徑是藍色連結）
            download_links = page.locator('a:has-text("下載路徑")').all()
            
            year_data = []
            
            for link in download_links:
                # 取得該期別的資訊
                parent = link.locator('xpath=../..').first  # 往上找到包含完整資訊的容器
                
                # 擷取卷期、日期、檔案大小（需根據實際結構調整）
                text = parent.inner_text()
                
                # 取得 FTP 連結
                ftp_url = link.get_attribute('href')
                
                period_info = {
                    'text': text.strip(),
                    'ftp_url': ftp_url
                }
                
                year_data.append(period_info)
                print(f"  - {text.split()[0] if text else 'Unknown'}: {ftp_url}")
            
            all_data[year] = year_data
        
        # 儲存為 JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 完成！共擷取 {sum(len(v) for v in all_data.values())} 個下載連結")
        print(f"✓ 已儲存至: {output_file}")
        
        browser.close()

# 使用範例
if __name__ == '__main__':
    url = 'https://cloud.tipo.gov.tw/S220/opdata/detail/TrademarkRegXMLA'
    scrape_tipo_data(url)
```

#### 更精確的爬取腳本（需檢查實際 HTML）

```python
from playwright.sync_api import sync_playwright
import json
import re

def scrape_tipo_detailed(url='https://cloud.tipo.gov.tw/S220/opdata/detail/TrademarkRegXMLA'):
    """精確爬取，包含卷期、日期、檔案大小等資訊"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        all_data = {}
        
        # 使用開發者工具檢查實際的選擇器
        # 這裡提供常見的可能性，需根據實際情況調整
        
        year_options = page.locator('select option').all()
        
        for option in year_options:
            year = option.inner_text().strip()
            if not year or '選擇' in year:
                continue
                
            print(f"\n處理: {year}")
            option.click()
            page.wait_for_timeout(2000)
            
            # 找出所有期別項目
            # 根據截圖，每個期別可能在 <div> 或 <tr> 中
            items = page.locator('.period-item, tr').all()  # 需調整
            
            year_data = []
            
            for item in items:
                try:
                    # 取得文字資訊
                    text = item.inner_text()
                    
                    # 解析卷期號（例：第 52 卷 20 期）
                    volume_match = re.search(r'第\s*(\d+)\s*卷\s*(\d+)\s*期', text)
                    
                    # 解析日期（例：114-10-18）
                    date_match = re.search(r'(\d{3}-\d{2}-\d{2})', text)
                    
                    # 解析檔案大小（例：(77.22 MB)）
                    size_match = re.search(r'\(([0-9.]+\s*[MG]B)\)', text)
                    
                    # 取得 FTP 連結
                    link = item.locator('a:has-text("下載路徑")').first
                    ftp_url = link.get_attribute('href') if link else None
                    
                    if volume_match and ftp_url:
                        period_data = {
                            'volume': volume_match.group(1),
                            'issue': volume_match.group(2),
                            'date': date_match.group(1) if date_match else None,
                            'size': size_match.group(1) if size_match else None,
                            'ftp_url': ftp_url
                        }
                        year_data.append(period_data)
                        print(f"  ✓ 第{period_data['volume']}卷{period_data['issue']}期")
                        
                except Exception as e:
                    continue
            
            all_data[year] = year_data
        
        # 儲存結果
        with open('tipo_links.json', 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        browser.close()
        
        print(f"\n✓ 共擷取 {sum(len(v) for v in all_data.values())} 個連結")
        return all_data

if __name__ == '__main__':
    data = scrape_tipo_detailed()
```

#### 輸出格式範例

```json
{
  "114": [
    {
      "volume": "52",
      "issue": "20",
      "date": "114-10-18",
      "size": "77.22 MB",
      "ftp_url": "ftp://opdata.tipo.gov.tw/TrademarkReg/114/20/"
    },
    {
      "volume": "52",
      "issue": "19",
      "date": "114-10-02",
      "size": "107.85 MB",
      "ftp_url": "ftp://opdata.tipo.gov.tw/TrademarkReg/114/19/"
    }
  ],
  "113": [...]
}
```

### 使用爬取結果

取得所有連結後，就可以：
1. 用 FileZilla 手動下載特定期別
2. 撰寫批次下載腳本（見方法三）
3. 匯出成 CSV 供其他系統使用

---

## 方法三：使用程式化批次下載

### 重要提醒：多年份、多期資料結構

智慧財產局的開放資料網站包含：
- **多個年份**：從民國 50 年至今
- **每年多期**：每期對應一個公報發布
- **每期多個檔案**：XML 檔案、圖檔等

**FTP 目錄結構範例**：
```
ftp://opdata.tipo.gov.tw/
├── TrademarkReg/          # 商標註冊案公報
│   ├── 50/                # 民國 50 年
│   │   ├── 1/            # 第 1 期
│   │   ├── 2/            # 第 2 期
│   │   └── ...
│   ├── 51/                # 民國 51 年
│   │   └── ...
│   └── 114/               # 民國 114 年（2025年）
│       └── ...
├── PatentPub/             # 發明專利公開公報
└── PatentAnn/             # 發明專利公告公報
```

### 使用 Python 批次下載

有了方法二爬取的連結清單後，就可以批次下載所有檔案。

#### 方案 1：從 JSON 讀取並批次下載

使用方法二產生的 `tipo_links.json` 進行批次下載。

```python
from ftplib import FTP
import os
import json
from urllib.parse import urlparse

def download_from_json(json_file='tipo_links.json', output_dir='./downloads'):
    """
    從 JSON 檔案讀取 FTP 連結並批次下載
    
    Args:
        json_file: 方法二產生的 JSON 檔案
        output_dir: 本地下載目錄
    """
    # 讀取連結清單
    with open(json_file, 'r', encoding='utf-8') as f:
        all_links = json.load(f)
    
    print(f"載入 {sum(len(v) for v in all_links.values())} 個下載連結")
    
    # 統計
    total_files = 0
    success_files = 0
    
    for year, periods in all_links.items():
        print(f"\n========== 處理 {year} 年 ==========")
        
        for period in periods:
            ftp_url = period.get('ftp_url')
            if not ftp_url:
                continue
            
            # 解析 FTP URL
            parsed = urlparse(ftp_url)
            host = parsed.netloc
            path = parsed.path
            
            volume = period.get('volume', 'unknown')
            issue = period.get('issue', 'unknown')
            
            print(f"\n下載第 {volume} 卷 {issue} 期...")
            
            # 建立本地目錄
            local_dir = os.path.join(output_dir, year, f"vol{volume}_iss{issue}")
            os.makedirs(local_dir, exist_ok=True)
            
            try:
                # 連線 FTP
                ftp = FTP(host, timeout=300)
                ftp.login()
                ftp.cwd(path)
                
                # 列出檔案
                files = ftp.nlst()
                print(f"  找到 {len(files)} 個檔案")
                
                # 下載每個檔案
                for filename in files:
                    local_path = os.path.join(local_dir, filename)
                    
                    try:
                        with open(local_path, 'wb') as f:
                            ftp.retrbinary(f'RETR {filename}', f.write)
                        print(f"    ✓ {filename}")
                        success_files += 1
                    except Exception as e:
                        print(f"    ✗ {filename}: {e}")
                    
                    total_files += 1
                
                ftp.quit()
                
            except Exception as e:
                print(f"  ✗ 連線失敗: {e}")
    
    print(f"\n========== 完成 ==========")
    print(f"成功下載: {success_files}/{total_files} 個檔案")

# 使用範例
if __name__ == '__main__':
    download_from_json('tipo_links.json', './tipo_data')
```

#### 方案 2：下載特定年份或期別

```python
def download_specific_periods(json_file, year=None, issues=None, output_dir='./downloads'):
    """
    下載特定年份或期別
    
    Args:
        json_file: JSON 檔案路徑
        year: 指定年份（例：'114'），None 表示全部
        issues: 指定期別列表（例：['20', '19']），None 表示全部
        output_dir: 輸出目錄
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        all_links = json.load(f)
    
    # 篩選年份
    if year:
        all_links = {year: all_links.get(year, [])}
    
    for y, periods in all_links.items():
        # 篩選期別
        if issues:
            periods = [p for p in periods if p.get('issue') in issues]
        
        for period in periods:
            ftp_url = period['ftp_url']
            print(f"下載: {y} 年第 {period['issue']} 期")
            # ... 下載邏輯同上 ...

# 使用範例
# 只下載 114 年的資料
download_specific_periods('tipo_links.json', year='114')

# 只下載特定期別
download_specific_periods('tipo_links.json', year='114', issues=['20', '19', '18'])
```

#### 方案 3：手動指定 FTP 連結下載

如果沒有使用方法二爬取，也可以手動指定連結。

```python
from ftplib import FTP
import os

def download_single_period(ftp_url, local_dir):
    """下載單一期別的所有檔案
    
    Args:
        ftp_url: FTP 連結，例如 'ftp://opdata.tipo.gov.tw/TrademarkReg/114/20/'
        local_dir: 本地下載目錄
    """
    from urllib.parse import urlparse
    
    # 解析 URL
    parsed = urlparse(ftp_url)
    host = parsed.netloc
    path = parsed.path
    
    # 建立本地目錄
    os.makedirs(local_dir, exist_ok=True)
    
    # 連線到 FTP 伺服器
    ftp = FTP(host, timeout=300)
    ftp.login()  # 匿名登入
    ftp.cwd(path)
    
    # 列出檔案
    files = ftp.nlst()
    print(f"找到 {len(files)} 個檔案")
    
    # 下載所有檔案
    for filename in files:
        local_path = os.path.join(local_dir, filename)
        print(f"正在下載: {filename}")
        
        try:
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            print(f"✓ 完成: {filename}")
        except Exception as e:
            print(f"✗ 失敗: {filename} - {e}")
    
    # 關閉連線
    ftp.quit()
    print("下載完成！")

# 使用範例
download_single_period(
    'ftp://opdata.tipo.gov.tw/TrademarkReg/114/20/',
    './downloads/114/20'
)
```

#### 方案 4：進階批次下載器（含進度條、斷點續傳）

```python
from ftplib import FTP
import os
import json
from tqdm import tqdm  # 需要: pip install tqdm
from urllib.parse import urlparse

class AdvancedTIPODownloader:
    """進階下載器：支援進度條、斷點續傳、錯誤重試"""
    
    def __init__(self, json_file='tipo_links.json'):
        self.json_file = json_file
        self.download_log = 'download_log.json'
        self.load_progress()
    
    def load_progress(self):
        """載入下載進度"""
        if os.path.exists(self.download_log):
            with open(self.download_log, 'r') as f:
                self.completed = json.load(f)
        else:
            self.completed = {}
    
    def save_progress(self):
        """儲存下載進度"""
        with open(self.download_log, 'w') as f:
            json.dump(self.completed, f, indent=2)
    
    def download_with_progress(self, output_dir='./downloads', max_retries=3):
        """帶進度條的批次下載"""
        
        # 讀取連結清單
        with open(self.json_file, 'r', encoding='utf-8') as f:
            all_links = json.load(f)
        
        # 計算總任務數
        total_periods = sum(len(periods) for periods in all_links.values())
        
        with tqdm(total=total_periods, desc="總進度") as pbar:
            for year, periods in all_links.items():
                for period in periods:
                    period_key = f"{year}_{period.get('volume')}_{period.get('issue')}"
                    
                    # 檢查是否已下載
                    if period_key in self.completed:
                        pbar.update(1)
                        continue
                    
                    ftp_url = period['ftp_url']
                    local_dir = os.path.join(
                        output_dir, year, 
                        f"vol{period['volume']}_iss{period['issue']}"
                    )
                    
                    # 重試機制
                    for attempt in range(max_retries):
                        try:
                            self.download_period(ftp_url, local_dir)
                            self.completed[period_key] = True
                            self.save_progress()
                            break
                        except Exception as e:
                            if attempt == max_retries - 1:
                                print(f"✗ 失敗 {period_key}: {e}")
                            else:
                                print(f"重試 {attempt + 1}/{max_retries}...")
                    
                    pbar.update(1)
    
    def download_period(self, ftp_url, local_dir):
        """下載單一期別"""
        from urllib.parse import urlparse
        
        parsed = urlparse(ftp_url)
        ftp = FTP(parsed.netloc, timeout=300)
        ftp.login()
        ftp.cwd(parsed.path)
        
        files = ftp.nlst()
        os.makedirs(local_dir, exist_ok=True)
        
        for filename in files:
            local_path = os.path.join(local_dir, filename)
            
            # 斷點續傳：檢查檔案是否已存在
            if os.path.exists(local_path):
                continue
            
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
        
        ftp.quit()

# 使用範例
downloader = AdvancedTIPODownloader('tipo_links.json')
downloader.download_with_progress('./tipo_data')
```

---

### 使用 curl 或 wget 下載

#### curl 批次下載

```bash
# 從 JSON 讀取並下載（需搭配 jq 工具）
cat tipo_links.json | jq -r '.[][] | .ftp_url' | while read url; do
    echo "下載: $url"
    curl -O "$url"
done
```

#### wget 批次下載

```bash
# 下載整個 FTP 目錄
wget -r -np -nH --cut-dirs=3 ftp://opdata.tipo.gov.tw/TrademarkReg/114/20/

# 參數說明：
# -r: 遞迴下載
# -np: 不追溯到父目錄
# -nH: 不建立主機名稱目錄
# --cut-dirs=3: 跳過前三層目錄結構
```

---

## 完整工作流程範例

### 步驟 1：爬取所有下載連結

```bash
# 使用 Playwright 爬取
python scrape_tipo.py
# 產生 tipo_links.json
```

### 步驟 2：檢視連結清單

```bash
# 查看 JSON 內容
cat tipo_links.json | jq '.'

# 統計各年份期數
cat tipo_links.json | jq 'to_entries | map({year: .key, count: (.value | length)})'
```

### 步驟 3：批次下載

```bash
# 使用 Python 下載器
python batch_download.py

# 或使用進階下載器（含進度條）
python advanced_download.py
```

### 步驟 4：驗證下載完整性

```python
import os
import json

def verify_downloads(json_file, download_dir):
    """驗證下載完整性"""
    with open(json_file, 'r') as f:
        all_links = json.load(f)
    
    missing = []
    
    for year, periods in all_links.items():
        for period in periods:
            vol = period['volume']
            iss = period['issue']
            local_dir = os.path.join(download_dir, year, f"vol{vol}_iss{iss}")
            
            if not os.path.exists(local_dir):
                missing.append(f"{year}/vol{vol}_iss{iss}")
    
    if missing:
        print(f"缺少 {len(missing)} 個期別:")
        for m in missing:
            print(f"  - {m}")
    else:
        print("✓ 所有檔案下載完成！")

verify_downloads('tipo_links.json', './tipo_data')
```

---

## 資料集說明

### 使用 curl 下載

適合 Linux/Mac 使用者或需要簡單腳本的情況。

```bash
# 下載單一檔案
curl -O ftp://opdata.tipo.gov.tw/TrademarkReg/50/5/檔案名稱.xml

# 批次下載整個目錄（需要先列出檔案清單）
wget -r ftp://opdata.tipo.gov.tw/TrademarkReg/50/5/
```

### 使用 wget 批次下載

```bash
# 遞迴下載整個目錄
wget -r -np -nH --cut-dirs=2 ftp://opdata.tipo.gov.tw/TrademarkReg/50/5/

# 參數說明：
# -r: 遞迴下載
# -np: 不追溯到父目錄
# -nH: 不建立主機名稱目錄
# --cut-dirs=2: 跳過前兩層目錄結構
```

---

## 資料集說明

### 商標資料集

#### 1. 商標註冊案公報（1案1XML檔）
- **資料內容**：商標種類、註冊號、申請案號、公告卷期、申請日期、商標名稱、商標權人資訊、代理人資訊、權利期間、商標圖樣、商品或服務類別等
- **檔案格式**：XML、WAV、JPEG
- **適用情境**：需要查詢特定商標案件
- **更新頻率**：定期更新（通常每期公報發布後）

#### 2. 商標註冊案公報（1卷期1XML檔）
- **資料內容**：與「1案1XML檔」相同，但整期公報打包在一個檔案
- **檔案格式**：XML、WAV、JPEG
- **適用情境**：需要批次下載某期公報的所有案件
- **更新頻率**：定期更新

#### 3. 商標註冊案公報（單頁式掃描檔）
- **資料內容**：商標註冊案公報掃描圖檔資料
- **檔案格式**：XML、TIFF
- **適用情境**：需要查看原始公報影像

### 專利資料集

#### 發明專利公開公報
- 包含專利申請案在公開階段的資訊
- 通常在申請後 18 個月公開

#### 發明專利公告公報
- 包含已獲准專利權的資訊
- 提供完整的專利說明書內容

### 資料格式說明

- **XML**：結構化資料，適合程式解析
- **TIFF/JPEG**：圖檔格式，用於商標圖樣或掃描檔
- **WAV**：音效檔（部分商標包含聲音商標）

---

## 常見問題

### Q1：為什麼瀏覽器無法開啟 FTP 連結？
**A**：現代瀏覽器已不支援 FTP 協定，建議使用 FileZilla 等 FTP 軟體，或使用程式化方式下載。

### Q2：下載速度很慢或連線逾時怎麼辦？
**A**：
1. 調整 FileZilla 逾時設定為 240 秒或 0 秒
2. 避免在尖峰時段下載
3. 使用程式化下載並加入重試機制

### Q3：如何找到特定專利或商標的資料？
**A**：
1. 先在智慧財產局的檢索系統查詢（取得申請號或公告號）
2. 根據公告日期找到對應的卷期
3. 下載該卷期的資料後再進行篩選

### Q4：資料更新頻率如何？
**A**：通常配合公報發布時間更新：
- 商標公報：每期發布後
- 專利公報：每週或每月（依類型而定）

### Q5：下載的 XML 檔案如何解析？
**A**：可使用以下方式：
- Python: `xml.etree.ElementTree` 或 `lxml`
- JavaScript: `DOMParser` 或 `xml2js`
- Java: `DocumentBuilder`
- 任何支援 XML 解析的程式語言

### Q6：資料可以商用嗎？
**A**：是的，屬於政府開放資料，遵循「政府資料開放授權條款」即可自由使用、修改、散布。但請注意：
- 資料僅供參考，不作為法律依據
- 建議標註資料來源

### Q7：如何取得最新的資料集清單？
**A**：定期檢查開放資料網站，或使用程式自動爬取目錄清單。

---

## 聯絡資訊

如有任何問題，請聯繫智慧財產局：

- **地址**：106213 臺北市大安區辛亥路2段185號3樓
- **電話**：(02) 2738-0007
- **傳真**：(02) 2377-9875
- **專利商標資料庫檢索服務台**：(02) 2376-7165、(02) 2376-7166
- **服務時間**：週一至週五 08:30-12:30、13:30-17:30

---

## 相關資源

- [智慧財產局官網](https://www.tipo.gov.tw)
- [全球專利檢索系統 GPSS](https://gpss.tipo.gov.tw)
- [專利商標開放資料](https://cloud.tipo.gov.tw/S220/opdata)
- [政府資料開放平台](https://data.gov.tw)
- [智慧財產局 Facebook](https://www.facebook.com/TIPO.gov.tw/)

---

## 版本資訊

- **文件版本**：1.0
- **最後更新**：2025年10月
- **撰寫者**：依據智慧財產局開放資料網站資訊整理

---

**授權聲明**：本教學文件依據政府資料開放授權條款提供，歡迎自由使用、修改與散布。