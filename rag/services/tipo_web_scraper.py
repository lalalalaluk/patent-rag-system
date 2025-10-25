"""
TIPO Web Scraper - 爬取台灣智慧財產局開放資料網站下載連結
使用 Playwright 處理 JavaScript 動態渲染的網頁
"""
import json
import logging
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from django.conf import settings

logger = logging.getLogger(__name__)


class TIPOWebScraper:
    """台灣智慧財產局網站爬蟲 - 取得下載連結"""

    BASE_URL = "https://cloud.tipo.gov.tw/S220/opdata"

    # 資料集 URL 對應
    DATASET_URLS = {
        # 專利公告公報
        'patent_announce_xml_single': 'detail/PatentIsuRegSpecXMLA',    # 1案1XML
        'patent_announce_xml_volume': 'detail/PatentIsuRegSpecXMLB',    # 1卷期1XML
        'patent_announce_scan_single': 'detail/PatentIsuRegSpecSTIFF',  # 單頁掃描
        'patent_announce_scan_multi': 'detail/PatentIsuRegSpecMTIFF',   # 多頁掃描

        # 發明公開公報
        'invention_pub_xml_single': 'detail/InventionPubXMLA',           # 1案1XML
        'invention_pub_xml_volume': 'detail/InventionPubXMLB',           # 1卷期1XML
        'invention_pub_scan_single': 'detail/InventionPubSTIFF',         # 單頁掃描
        'invention_pub_scan_multi': 'detail/InventionPubMTIFF',          # 多頁掃描

        # 商標
        'trademark_reg_xml_single': 'detail/TrademarkRegXMLA',           # 商標1案1XML
        'trademark_reg_xml_volume': 'detail/TrademarkRegXMLB',           # 商標1卷期1XML
    }

    def __init__(self, headless: bool = True):
        """
        初始化爬蟲

        Args:
            headless: 是否使用無頭模式
        """
        self.headless = headless

    def scrape_dataset(
        self,
        dataset_key: str,
        years: Optional[List[str]] = None,
        max_periods_per_year: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        爬取指定資料集的所有下載連結

        Args:
            dataset_key: 資料集鍵值 (參考 DATASET_URLS)
            years: 要爬取的年份列表 (None = 全部年份)
            max_periods_per_year: 每年最多爬取幾期 (None = 全部)

        Returns:
            {
                '114': [
                    {
                        'volume': '52',
                        'issue': '29',
                        'date': '114-10-13',
                        'size': '2511.87 MB',
                        'ftps_url': 'ftps://ftp.tipo.gov.tw/...',
                        'title': '第 52 卷 29 期'
                    },
                    ...
                ],
                ...
            }
        """
        if dataset_key not in self.DATASET_URLS:
            raise ValueError(f"Unknown dataset: {dataset_key}")

        url = f"{self.BASE_URL}/{self.DATASET_URLS[dataset_key]}"
        logger.info(f"爬取資料集: {dataset_key} from {url}")

        with sync_playwright() as p:
            # 啟動瀏覽器
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()

            try:
                # 訪問頁面
                logger.info(f"載入頁面: {url}")
                page.goto(url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(3000)  # 等待3秒確保 JS 渲染完成

                all_data = {}

                # 取得所有可選年份
                year_selector = 'select'
                year_options = page.locator(f'{year_selector} option').all()

                available_years = []
                for option in year_options:
                    year_text = option.inner_text().strip()
                    if year_text and year_text.isdigit():
                        available_years.append(year_text)

                logger.info(f"找到 {len(available_years)} 個年份: {available_years}")

                # 篩選要爬取的年份
                if years:
                    if '__LATEST__' in years:
                        # 特殊標記: 只要最新年份 (第一個)
                        target_years = [available_years[0]] if available_years else []
                    else:
                        target_years = [y for y in available_years if y in years]
                else:
                    target_years = available_years

                logger.info(f"將爬取以下年份: {target_years}")

                # 逐年爬取
                for year in target_years:
                    logger.info(f"\n========== 處理 {year} 年 ==========")

                    # 選擇年份
                    page.select_option(year_selector, label=year)
                    page.wait_for_timeout(2000)  # 等待資料載入

                    # 找出所有期別項目
                    # 根據觀察,每個期別在一個 generic container 中
                    # 包含:標題(第X卷Y期)、日期、下載連結、檔案大小
                    year_data = []

                    # 找所有包含 FTPS URL 的連結 (網站顯示為 "Ftp Path")
                    download_links = page.locator('a[href^="ftps://"]').all()
                    logger.info(f"  找到 {len(download_links)} 個下載連結")

                    count = 0
                    for link in download_links:
                        if max_periods_per_year and count >= max_periods_per_year:
                            break

                        try:
                            # 取得 FTPS URL
                            ftps_url = link.get_attribute('href')

                            if not ftps_url:
                                continue

                            # 往上找到包含完整資訊的容器 (兩層)
                            parent = link.locator('xpath=../..').first

                            # 取得該容器的所有文字
                            text = parent.inner_text()

                            # 解析資訊
                            # 格式範例: "Vol. 52, Iss. 29\n114-10-13\nFtp Path\n( 2511.87 MB )"

                            # 解析卷期號 (英文格式: Vol. X, Iss. Y)
                            volume_match = re.search(r'Vol\.\s*(\d+),\s*Iss\.\s*(\d+)', text)
                            # 解析日期 (民國年-月-日)
                            date_match = re.search(r'(\d{3}-\d{2}-\d{2})', text)
                            # 解析檔案大小
                            size_match = re.search(r'\(\s*([0-9.]+\s*[KMGT]?B)\s*\)', text)

                            if volume_match:
                                period_info = {
                                    'volume': volume_match.group(1),
                                    'issue': volume_match.group(2),
                                    'title': f"第 {volume_match.group(1)} 卷 {volume_match.group(2)} 期",
                                    'date': date_match.group(1) if date_match else None,
                                    'size': size_match.group(1) if size_match else None,
                                    'ftps_url': ftps_url
                                }

                                year_data.append(period_info)
                                count += 1

                                logger.info(
                                    f"    ✓ {period_info['title']} - "
                                    f"{period_info['date']} ({period_info['size']})"
                                )

                        except Exception as e:
                            logger.error(f"    ✗ 解析期別失敗: {e}")
                            continue

                    all_data[year] = year_data
                    logger.info(f"  完成 {year} 年: 共 {len(year_data)} 期")

                logger.info(f"\n✓ 爬取完成! 共 {sum(len(v) for v in all_data.values())} 個下載連結")
                return all_data

            except PlaywrightTimeout as e:
                logger.error(f"頁面載入逾時: {e}")
                return {}

            except Exception as e:
                logger.error(f"爬取失敗: {e}", exc_info=True)
                return {}

            finally:
                browser.close()

    def scrape_all_years_latest_periods(
        self,
        dataset_key: str,
        periods_per_year: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        爬取所有年份的最新 N 期資料

        Args:
            dataset_key: 資料集鍵值
            periods_per_year: 每年最新幾期

        Returns:
            下載連結資料
        """
        logger.info(f"爬取所有年份的最新 {periods_per_year} 期")
        return self.scrape_dataset(
            dataset_key=dataset_key,
            years=None,  # 所有年份
            max_periods_per_year=periods_per_year
        )

    def scrape_latest_year(
        self,
        dataset_key: str,
        max_periods: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        只爬取最新年份的資料

        Args:
            dataset_key: 資料集鍵值
            max_periods: 最多幾期

        Returns:
            下載連結資料 (只包含最新年份)
        """
        logger.info(f"爬取最新年份的最多 {max_periods} 期")

        # 使用 None 作為 years 參數，在 scrape_dataset 中只取第一個年份
        return self.scrape_dataset(
            dataset_key=dataset_key,
            years=None,  # 會自動取得所有年份，然後我們只處理第一個
            max_periods_per_year=max_periods
        )

    def save_to_json(self, data: Dict, output_file: str):
        """
        儲存爬取結果為 JSON

        Args:
            data: 爬取的資料
            output_file: 輸出檔案路徑
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 已儲存至: {output_file}")


# 便利函數

def scrape_patent_links(
    dataset_type: str = 'patent_announce_xml_single',
    latest_only: bool = True,
    max_periods: int = 5,
    output_file: Optional[str] = None
) -> Dict:
    """
    便利函數: 爬取專利下載連結

    Args:
        dataset_type: 資料集類型 (參考 TIPOWebScraper.DATASET_URLS 的 keys)
        latest_only: 是否只爬取最新年份
        max_periods: 最多幾期
        output_file: JSON 輸出檔案 (None = 不儲存)

    Returns:
        下載連結資料
    """
    scraper = TIPOWebScraper(headless=True)

    if latest_only:
        # 爬取資料,並在爬取過程中只處理第一個年份
        result = scraper.scrape_dataset(
            dataset_key=dataset_type,
            years=['__LATEST__'],  # 特殊標記,表示只要最新年份
            max_periods_per_year=max_periods
        )
    else:
        result = scraper.scrape_all_years_latest_periods(dataset_type, max_periods)

    if output_file:
        scraper.save_to_json(result, output_file)

    return result


if __name__ == '__main__':
    # 測試爬取專利公告公報
    print("測試爬取專利公告公報(1案1XML)...")

    data = scrape_patent_links(
        dataset_type='patent_announce_xml_single',
        latest_only=True,
        max_periods=3,
        output_file='tipo_patent_links.json'
    )

    print(f"\n爬取結果:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
