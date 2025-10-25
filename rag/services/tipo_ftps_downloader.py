"""
TIPO FTPS Downloader - 下載台灣專利局 FTPS 資料
注意: 台灣專利局使用 Implicit FTPS (port 990),不是 Explicit FTPS (port 21)
"""
import os
import logging
import socket
import ssl
from pathlib import Path
from typing import List, Dict, Optional
from ftplib import FTP
from urllib.parse import urlparse
from django.conf import settings

logger = logging.getLogger(__name__)


class ImplicitFTP_TLS(FTP):
    """Implicit FTPS Client (port 990)

    TIPO 使用 Implicit FTPS,連接時立即建立 TLS,不使用 STARTTLS
    """
    def __init__(self, host='', user='', passwd='', acct='',
                 keyfile=None, certfile=None, context=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                 source_address=None):

        if context is None:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        self.context = context
        self.keyfile = keyfile
        self.certfile = certfile

        super().__init__()

        self.timeout = timeout
        self.source_address = source_address

        if host:
            self.connect(host)
            if user:
                self.login(user, passwd, acct)

    def connect(self, host='', port=990, timeout=-999, source_address=None):
        """Connect to host using implicit TLS on port 990"""
        if timeout != -999:
            self.timeout = timeout
        if source_address is not None:
            self.source_address = source_address

        # Create regular socket connection
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port), self.timeout, source_address=self.source_address)

        # Immediately wrap with TLS (Implicit FTPS)
        self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
        self.af = self.sock.family

        # Get welcome message
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()

        return self.welcome

    def ntransfercmd(self, cmd, rest=None):
        """Override to use TLS for data connections"""
        conn, size = super().ntransfercmd(cmd, rest)
        # Wrap data connection with TLS
        conn = self.context.wrap_socket(conn, server_hostname=self.host)
        return conn, size


class TIPOFTPSDownloader:
    """台灣智慧財產局 FTPS 下載器 (使用 Implicit FTPS on port 990)"""

    def __init__(self, timeout: int = 300):
        """
        初始化下載器

        Args:
            timeout: 連線逾時秒數
        """
        self.timeout = timeout
        self.ftps = None

    def connect(self, host: str = 'ftp.tipo.gov.tw'):
        """
        連線到 FTPS 伺服器 (Implicit FTPS, port 990)

        Args:
            host: FTPS 伺服器主機名稱
        """
        try:
            logger.info(f"連線到 Implicit FTPS 伺服器: {host}:990")

            # 使用自訂的 Implicit FTPS 客戶端
            self.ftps = ImplicitFTP_TLS(timeout=self.timeout)
            self.ftps.connect(host, 990)

            # 匿名登入
            logger.info("匿名登入中...")
            self.ftps.login()

            # 設定被動模式
            self.ftps.set_pasv(True)

            logger.info("✓ Implicit FTPS 連線成功")
            return True

        except Exception as e:
            logger.error(f"✗ FTPS 連線失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def disconnect(self):
        """斷開 FTPS 連線"""
        if self.ftps:
            try:
                self.ftps.quit()
                logger.info("FTPS 連線已關閉")
            except:
                pass
            self.ftps = None

    def download_file(
        self,
        remote_path: str,
        filename: str,
        local_dir: str
    ) -> bool:
        """
        下載單一檔案

        Args:
            remote_path: 遠端路徑 (例: /PatentIsuRegSpecXMLA/114/PatentIsuRegSpecXMLA_052029)
            filename: 檔案名稱
            local_dir: 本地儲存目錄

        Returns:
            是否成功下載
        """
        if not self.ftps:
            logger.error("尚未連線到 FTPS 伺服器")
            return False

        try:
            # 建立本地目錄
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, filename)

            # 檢查檔案是否已存在
            if os.path.exists(local_path):
                logger.info(f"檔案已存在,跳過: {filename}")
                return True

            # 切換到遠端目錄
            self.ftps.cwd(remote_path)

            # 下載檔案
            logger.info(f"下載中: {filename}")
            with open(local_path, 'wb') as f:
                self.ftps.retrbinary(f'RETR {filename}', f.write)

            logger.info(f"✓ 下載完成: {filename}")
            return True

        except Exception as e:
            logger.error(f"✗ 下載檔案失敗 {filename}: {e}")
            return False

    def list_files(self, remote_path: str) -> List[str]:
        """
        列出遠端目錄的所有檔案

        Args:
            remote_path: 遠端路徑

        Returns:
            檔案名稱列表
        """
        if not self.ftps:
            if not self.connect():
                return []

        try:
            # 切換到目標目錄
            self.ftps.cwd(remote_path)

            # 使用 LIST 命令並解析輸出 (NLST 在某些情況下返回空)
            # LIST 格式: "drwxr-xr-x 1396 pi tipo 221184 Feb  9  2022 filename"
            lines = []
            self.ftps.retrlines('LIST', lines.append)

            # 解析檔案名稱 (最後一個空格後的內容)
            files = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 9:  # 確保有足夠的欄位
                    # 檔案名可能包含空格,取最後的所有內容
                    filename = ' '.join(parts[8:])
                    files.append(filename)

            logger.info(f"找到 {len(files)} 個檔案在 {remote_path}")
            return files

        except Exception as e:
            logger.error(f"列出檔案失敗: {e}")
            import traceback
            traceback.print_exc()
            return []

    def download_from_ftps_url(
        self,
        ftps_url: str,
        local_dir: str,
        file_filter: Optional[callable] = None,
        max_files: Optional[int] = None
    ) -> Dict[str, int]:
        """
        從 FTPS URL 下載所有檔案

        Args:
            ftps_url: FTPS URL (例: ftps://ftp.tipo.gov.tw/PatentIsuRegSpecXMLA/114/PatentIsuRegSpecXMLA_052029)
            local_dir: 本地儲存目錄
            file_filter: 檔案過濾函數 (可選,例如只下載 XML: lambda f: f.endswith('.xml'))
            max_files: 最多下載幾個檔案 (None = 全部)

        Returns:
            {'total': 總數, 'success': 成功數, 'failed': 失敗數, 'skipped': 跳過數}
        """
        # 解析 URL
        parsed = urlparse(ftps_url)
        host = parsed.netloc
        remote_path = parsed.path

        logger.info(f"準備從 FTPS 下載: {ftps_url}")
        logger.info(f"  主機: {host}")
        logger.info(f"  路徑: {remote_path}")

        # 連線
        if not self.ftps or self.ftps.host != host:
            if self.ftps:
                self.disconnect()
            if not self.connect(host):
                return {'error': 'FTPS 連線失敗'}

        # 列出檔案
        files = self.list_files(remote_path)

        # 應用過濾器
        if file_filter:
            files = [f for f in files if file_filter(f)]
            logger.info(f"過濾後剩餘 {len(files)} 個檔案")

        # 限制數量
        if max_files:
            files = files[:max_files]
            logger.info(f"限制下載數量: {len(files)} 個檔案")

        # 下載統計
        stats = {'total': len(files), 'success': 0, 'failed': 0, 'skipped': 0}

        # 逐一下載
        for filename in files:
            local_path = os.path.join(local_dir, filename)

            # 檢查是否已存在
            if os.path.exists(local_path):
                stats['skipped'] += 1
                continue

            if self.download_file(remote_path, filename, local_dir):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        logger.info(
            f"\n下載完成! 成功: {stats['success']}/{stats['total']}, "
            f"失敗: {stats['failed']}, 跳過: {stats['skipped']}"
        )

        return stats

    def download_from_links_json(
        self,
        links_json: Dict,
        output_base_dir: str,
        file_filter: Optional[callable] = None,
        year_filter: Optional[callable] = None,
        max_files_per_period: Optional[int] = None
    ) -> Dict:
        """
        從爬蟲產生的 JSON 批次下載

        Args:
            links_json: 爬蟲產生的連結 JSON (格式見 tipo_web_scraper.py)
            output_base_dir: 輸出基礎目錄
            file_filter: 檔案過濾函數 (例如只下載 XML)
            year_filter: 年份過濾函數 (例如只下載特定年份)
            max_files_per_period: 每期最多下載幾個檔案

        Returns:
            下載統計
        """
        total_stats = {
            'total_periods': 0,
            'completed_periods': 0,
            'total_files': 0,
            'success_files': 0,
            'failed_files': 0,
            'skipped_files': 0
        }

        for year, periods in links_json.items():
            # 年份過濾
            if year_filter and not year_filter(year):
                logger.info(f"跳過年份: {year}")
                continue

            logger.info(f"\n========== 處理 {year} 年 ==========")

            for period in periods:
                total_stats['total_periods'] += 1

                ftps_url = period.get('ftps_url')
                if not ftps_url:
                    logger.warning(f"缺少 ftps_url: {period}")
                    continue

                # 建立本地目錄
                volume = period.get('volume', 'unknown')
                issue = period.get('issue', 'unknown')
                local_dir = os.path.join(
                    output_base_dir,
                    year,
                    f"vol{volume}_iss{issue}"
                )

                logger.info(f"\n下載: {period.get('title', 'Unknown')} ({period.get('size', 'Unknown')})")

                # 下載
                try:
                    stats = self.download_from_ftps_url(
                        ftps_url=ftps_url,
                        local_dir=local_dir,
                        file_filter=file_filter,
                        max_files=max_files_per_period
                    )

                    if 'error' not in stats:
                        total_stats['completed_periods'] += 1
                        total_stats['total_files'] += stats['total']
                        total_stats['success_files'] += stats['success']
                        total_stats['failed_files'] += stats['failed']
                        total_stats['skipped_files'] += stats['skipped']

                except Exception as e:
                    logger.error(f"下載期別失敗: {e}")

        logger.info(f"\n========== 批次下載完成 ==========")
        logger.info(f"完成期別: {total_stats['completed_periods']}/{total_stats['total_periods']}")
        logger.info(f"成功檔案: {total_stats['success_files']}/{total_stats['total_files']}")
        logger.info(f"失敗檔案: {total_stats['failed_files']}")
        logger.info(f"跳過檔案: {total_stats['skipped_files']}")

        return total_stats


# 便利函數

def download_patent_data_from_links(
    links_json_file: str,
    output_dir: Optional[str] = None,
    xml_only: bool = True,
    latest_year_only: bool = False,
    max_files_per_period: int = None
) -> Dict:
    """
    便利函數: 從連結 JSON 檔案下載專利資料

    Args:
        links_json_file: 爬蟲產生的 JSON 檔案路徑
        output_dir: 輸出目錄 (None = 使用 settings.RAW_DATA_DIR)
        xml_only: 是否只下載 XML 檔案
        latest_year_only: 是否只下載最新年份
        max_files_per_period: 每期最多下載幾個檔案

    Returns:
        下載統計
    """
    import json

    # 讀取連結 JSON
    with open(links_json_file, 'r', encoding='utf-8') as f:
        links_json = json.load(f)

    # 設定輸出目錄
    if output_dir is None:
        output_dir = str(settings.RAW_DATA_DIR / 'patent_downloads')

    # 檔案過濾器
    file_filter = None
    if xml_only:
        file_filter = lambda f: f.lower().endswith('.xml')

    # 年份過濾器
    year_filter = None
    if latest_year_only and links_json:
        latest_year = max(links_json.keys())
        year_filter = lambda y: y == latest_year
        logger.info(f"只下載最新年份: {latest_year}")

    # 開始下載
    downloader = TIPOFTPSDownloader()

    try:
        stats = downloader.download_from_links_json(
            links_json=links_json,
            output_base_dir=output_dir,
            file_filter=file_filter,
            year_filter=year_filter,
            max_files_per_period=max_files_per_period
        )
        return stats

    finally:
        downloader.disconnect()


if __name__ == '__main__':
    # 測試下載
    import json

    # 假設已經有爬取的連結 JSON
    test_links = {
        "114": [
            {
                "volume": "52",
                "issue": "29",
                "title": "第 52 卷 29 期",
                "date": "114-10-13",
                "size": "2511.87 MB",
                "ftps_url": "ftps://ftp.tipo.gov.tw/PatentIsuRegSpecXMLA/114/PatentIsuRegSpecXMLA_052029"
            }
        ]
    }

    # 儲存為 JSON
    with open('test_links.json', 'w', encoding='utf-8') as f:
        json.dump(test_links, f, ensure_ascii=False, indent=2)

    # 測試下載 (只下載 XML,每期最多2個檔案)
    stats = download_patent_data_from_links(
        links_json_file='test_links.json',
        output_dir='./test_downloads',
        xml_only=True,
        max_files_per_period=2
    )

    print(json.dumps(stats, indent=2, ensure_ascii=False))
