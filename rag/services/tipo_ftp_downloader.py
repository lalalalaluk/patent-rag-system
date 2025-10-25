"""
TIPO FTP Downloader - 下載台灣智慧財產局開放資料
Based on: https://cloud.tipo.gov.tw/S220/opdata
"""
import os
import json
import logging
from ftplib import FTP
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse
from django.conf import settings

logger = logging.getLogger(__name__)


class TIPOFTPDownloader:
    """台灣智慧財產局 FTP 資料下載器"""

    FTP_HOST = "opdata.tipo.gov.tw"

    # 資料集路徑
    DATASET_PATHS = {
        'trademark_reg': 'TrademarkReg',      # 商標註冊案公報
        'patent_pub': 'PatentPub',            # 發明專利公開公報
        'patent_ann': 'PatentAnn',            # 發明專利公告公報
        'utility_pub': 'UtilityPub',          # 新型專利公開公報
        'utility_ann': 'UtilityAnn',          # 新型專利公告公報
        'design_pub': 'DesignPub',            # 設計專利公開公報
        'design_ann': 'DesignAnn',            # 設計專利公告公報
    }

    def __init__(self, timeout: int = 300):
        """
        初始化下載器

        Args:
            timeout: FTP 連線逾時秒數
        """
        self.timeout = timeout
        self.ftp = None

    def connect(self):
        """連線到 TIPO FTP 伺服器"""
        try:
            logger.info(f"連線到 FTP 伺服器: {self.FTP_HOST}")
            self.ftp = FTP(self.FTP_HOST, timeout=self.timeout)
            self.ftp.login()  # 匿名登入
            logger.info("FTP 連線成功")
            return True
        except Exception as e:
            logger.error(f"FTP 連線失敗: {e}")
            return False

    def disconnect(self):
        """斷開 FTP 連線"""
        if self.ftp:
            try:
                self.ftp.quit()
                logger.info("FTP 連線已關閉")
            except:
                pass
            self.ftp = None

    def list_years(self, dataset: str = 'patent_pub') -> List[str]:
        """
        列出指定資料集的所有年份

        Args:
            dataset: 資料集類型

        Returns:
            年份列表 (民國年)
        """
        if not self.ftp:
            if not self.connect():
                return []

        try:
            dataset_path = self.DATASET_PATHS.get(dataset, dataset)
            self.ftp.cwd(f'/{dataset_path}')

            # 列出所有目錄 (年份)
            items = []
            self.ftp.retrlines('LIST', items.append)

            # 提取年份目錄
            years = []
            for item in items:
                parts = item.split()
                if len(parts) >= 9:
                    name = parts[-1]
                    # 檢查是否為數字(年份)
                    if name.isdigit():
                        years.append(name)

            logger.info(f"找到 {len(years)} 個年份: {years[:5]}...")
            return sorted(years)

        except Exception as e:
            logger.error(f"列出年份失敗: {e}")
            return []

    def list_periods(self, dataset: str, year: str) -> List[str]:
        """
        列出指定年份的所有期別

        Args:
            dataset: 資料集類型
            year: 民國年份

        Returns:
            期別列表
        """
        if not self.ftp:
            if not self.connect():
                return []

        try:
            dataset_path = self.DATASET_PATHS.get(dataset, dataset)
            path = f'/{dataset_path}/{year}'
            self.ftp.cwd(path)

            # 列出所有目錄 (期別)
            items = []
            self.ftp.retrlines('LIST', items.append)

            # 提取期別目錄
            periods = []
            for item in items:
                parts = item.split()
                if len(parts) >= 9:
                    name = parts[-1]
                    # 檢查是否為數字(期別)
                    if name.isdigit():
                        periods.append(name)

            logger.info(f"{year}年 找到 {len(periods)} 個期別")
            return sorted(periods, key=int)

        except Exception as e:
            logger.error(f"列出期別失敗: {e}")
            return []

    def list_files(self, dataset: str, year: str, period: str) -> List[str]:
        """
        列出指定期別的所有檔案

        Args:
            dataset: 資料集類型
            year: 民國年份
            period: 期別

        Returns:
            檔案名稱列表
        """
        if not self.ftp:
            if not self.connect():
                return []

        try:
            dataset_path = self.DATASET_PATHS.get(dataset, dataset)
            path = f'/{dataset_path}/{year}/{period}'
            self.ftp.cwd(path)

            # 列出所有檔案
            files = self.ftp.nlst()
            logger.info(f"{year}年第{period}期 找到 {len(files)} 個檔案")

            return files

        except Exception as e:
            logger.error(f"列出檔案失敗: {e}")
            return []

    def download_file(
        self,
        dataset: str,
        year: str,
        period: str,
        filename: str,
        local_dir: str
    ) -> bool:
        """
        下載單一檔案

        Args:
            dataset: 資料集類型
            year: 民國年份
            period: 期別
            filename: 檔案名稱
            local_dir: 本地儲存目錄

        Returns:
            是否成功下載
        """
        if not self.ftp:
            if not self.connect():
                return False

        try:
            dataset_path = self.DATASET_PATHS.get(dataset, dataset)
            remote_path = f'/{dataset_path}/{year}/{period}'
            self.ftp.cwd(remote_path)

            # 建立本地目錄
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, filename)

            # 檢查檔案是否已存在
            if os.path.exists(local_path):
                logger.info(f"檔案已存在,跳過: {filename}")
                return True

            # 下載檔案
            logger.info(f"下載中: {filename}")
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {filename}', f.write)

            logger.info(f"下載完成: {filename}")
            return True

        except Exception as e:
            logger.error(f"下載檔案失敗 {filename}: {e}")
            return False

    def download_period(
        self,
        dataset: str,
        year: str,
        period: str,
        local_dir: str,
        file_filter: Optional[callable] = None
    ) -> Dict[str, int]:
        """
        下載整個期別的所有檔案

        Args:
            dataset: 資料集類型
            year: 民國年份
            period: 期別
            local_dir: 本地儲存目錄
            file_filter: 檔案過濾函數 (可選)

        Returns:
            下載統計 {'total': 總數, 'success': 成功數, 'failed': 失敗數}
        """
        logger.info(f"開始下載: {dataset} {year}年 第{period}期")

        # 列出檔案
        files = self.list_files(dataset, year, period)

        # 應用過濾器
        if file_filter:
            files = [f for f in files if file_filter(f)]

        # 下載統計
        stats = {'total': len(files), 'success': 0, 'failed': 0}

        # 建立本地目錄
        period_dir = os.path.join(local_dir, year, period)

        # 逐一下載
        for filename in files:
            if self.download_file(dataset, year, period, filename, period_dir):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        logger.info(
            f"下載完成: {stats['success']}/{stats['total']} 成功, "
            f"{stats['failed']} 失敗"
        )

        return stats

    def download_multiple_periods(
        self,
        dataset: str,
        year: str,
        periods: List[str],
        local_dir: str,
        file_filter: Optional[callable] = None
    ) -> Dict[str, Dict]:
        """
        批次下載多個期別

        Args:
            dataset: 資料集類型
            year: 民國年份
            periods: 期別列表
            local_dir: 本地儲存目錄
            file_filter: 檔案過濾函數 (可選)

        Returns:
            各期別的下載統計
        """
        results = {}

        for period in periods:
            try:
                stats = self.download_period(
                    dataset, year, period, local_dir, file_filter
                )
                results[period] = stats
            except Exception as e:
                logger.error(f"下載期別 {period} 失敗: {e}")
                results[period] = {'error': str(e)}

        return results

    def download_latest_period(
        self,
        dataset: str,
        local_dir: str,
        file_filter: Optional[callable] = None
    ) -> Optional[Dict]:
        """
        下載最新一期的資料

        Args:
            dataset: 資料集類型
            local_dir: 本地儲存目錄
            file_filter: 檔案過濾函數 (可選)

        Returns:
            下載統計或 None
        """
        # 取得所有年份
        years = self.list_years(dataset)
        if not years:
            logger.error("無法取得年份列表")
            return None

        # 最新年份
        latest_year = years[-1]

        # 取得該年的所有期別
        periods = self.list_periods(dataset, latest_year)
        if not periods:
            logger.error(f"無法取得 {latest_year} 年的期別列表")
            return None

        # 最新期別
        latest_period = periods[-1]

        logger.info(f"下載最新期別: {latest_year}年 第{latest_period}期")

        return self.download_period(
            dataset, latest_year, latest_period, local_dir, file_filter
        )


# 便利函數

def download_patent_data(
    dataset: str = 'patent_pub',
    year: Optional[str] = None,
    period: Optional[str] = None,
    max_periods: int = 5,
    output_dir: Optional[str] = None
) -> Dict:
    """
    便利函數: 下載專利資料

    Args:
        dataset: 資料集類型 ('patent_pub', 'patent_ann', 'utility_pub', etc.)
        year: 指定年份 (None = 最新年份)
        period: 指定期別 (None = 最新 N 期)
        max_periods: 最多下載幾期
        output_dir: 輸出目錄 (None = 使用 settings.RAW_DATA_DIR)

    Returns:
        下載結果統計
    """
    if output_dir is None:
        output_dir = settings.RAW_DATA_DIR / 'ftp_downloads' / dataset

    downloader = TIPOFTPDownloader()

    try:
        if not downloader.connect():
            return {'error': 'FTP連線失敗'}

        # 決定要下載的年份
        if year is None:
            years = downloader.list_years(dataset)
            if not years:
                return {'error': '無法取得年份列表'}
            year = years[-1]  # 最新年份

        # 決定要下載的期別
        if period is None:
            periods = downloader.list_periods(dataset, year)
            if not periods:
                return {'error': f'無法取得{year}年的期別列表'}
            # 取最新 N 期
            periods = periods[-max_periods:]
        else:
            periods = [period]

        logger.info(f"準備下載: {dataset} {year}年 期別: {periods}")

        # 只下載 XML 檔案 (節省空間)
        xml_filter = lambda f: f.endswith('.xml') or f.endswith('.XML')

        # 批次下載
        results = downloader.download_multiple_periods(
            dataset, year, periods, str(output_dir), xml_filter
        )

        return {
            'dataset': dataset,
            'year': year,
            'periods': periods,
            'results': results
        }

    finally:
        downloader.disconnect()


if __name__ == '__main__':
    # 測試下載
    result = download_patent_data(
        dataset='patent_pub',
        max_periods=2  # 下載最新 2 期
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
