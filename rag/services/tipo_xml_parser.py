"""
TIPO XML Parser - 解析台灣專利局的 XML 檔案
將 XML 轉換成 RAG 系統可用的專利文件格式
"""
import os
import json
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TIPOXMLParser:
    """台灣專利局 XML 解析器"""

    def parse_patent_xml(self, xml_file: str) -> Optional[Dict]:
        """
        解析單一專利 XML 檔案 (TIPO 格式: <tw-patent-grant>)

        Args:
            xml_file: XML 檔案路徑

        Returns:
            專利文件字典,格式如下:
            {
                'patent_number': '專利號',
                'application_number': '申請號',
                'title': '專利名稱',
                'abstract': '摘要',
                'description': '說明書',
                'claims': ['請求項1', '請求項2', ...],
                'inventor': '發明人',
                'applicant': '申請人',
                'application_date': '申請日',
                'publication_date': '公告日',
                'ipc_classification': 'IPC分類',
                'patent_type': '專利類別',
                'url': '檔案來源'
            }
        """
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # TIPO XML 格式使用 <tw-patent-grant> 根元素
            # 專利號在 certificate-number/document-id/doc-number
            patent_number = self._get_text(root, './/certificate-number/document-id/doc-number')
            if not patent_number:
                patent_number = self._get_text(root, './/publication-reference/document-id/doc-number')

            # 申請號在 application-reference/document-id/doc-number
            app_number = self._get_text(root, './/application-reference/document-id/doc-number')

            # 申請日和公告日
            app_date = self._get_text(root, './/application-reference/document-id/date')
            pub_date = self._get_text(root, './/publication-reference/document-id/date')

            # IPC 分類
            ipc = self._get_text(root, './/classification-ipc/main-classification')

            # 申請人 (可能有多個)
            applicants = []
            for applicant in root.findall('.//applicants/applicant'):
                name = self._get_text(applicant, './/chinese-name/last-name')
                if not name:
                    name = self._get_text(applicant, './/english-name/last-name')
                if name:
                    applicants.append(name)
            applicant_str = '; '.join(applicants) if applicants else ''

            # 發明人 (可能有多個)
            inventors = []
            for inventor in root.findall('.//inventors/inventor'):
                name = self._get_text(inventor, './/chinese-name/last-name')
                if not name:
                    name = self._get_text(inventor, './/english-name/last-name')
                if name:
                    inventors.append(name)
            inventor_str = '; '.join(inventors) if inventors else ''

            # 專利標題 (優先中文,若無則英文)
            title = self._get_text(root, './/invention-title/chinese-title')
            if not title:
                title = self._get_text(root, './/invention-title/english-title')

            # 摘要
            abstract = self._get_abstract(root)

            # 說明書
            description = self._get_description(root)

            # 請求項
            claims = self._get_claims(root)

            patent_data = {
                'patent_number': patent_number,
                'application_number': app_number,
                'title': title,
                'abstract': abstract,
                'description': description,
                'claims': claims,
                'inventor': inventor_str,
                'applicant': applicant_str,
                'application_date': app_date,
                'publication_date': pub_date,
                'ipc_classification': ipc,
                'patent_type': 'invention',  # 從資料集類型判斷
                'url': f"file://{os.path.abspath(xml_file)}"
            }

            return patent_data

        except ET.ParseError as e:
            logger.error(f"XML 解析錯誤 {xml_file}: {e}")
            return None

        except Exception as e:
            logger.error(f"處理檔案失敗 {xml_file}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_text(self, root: ET.Element, xpath: str, default: str = '') -> str:
        """取得 XML 元素的文字內容"""
        elem = root.find(xpath)
        if elem is not None and elem.text:
            return elem.text.strip()
        return default

    def _get_abstract(self, root: ET.Element) -> str:
        """
        取得摘要
        TIPO 格式在 <abstract> 標籤中,包含多個 <p> 段落
        """
        # TIPO 使用 <abstract> 標籤
        abstract_elem = root.find('.//abstract')
        if abstract_elem is not None:
            # 遞迴取得所有文字內容
            text = ''.join(abstract_elem.itertext()).strip()
            if text:
                return text

        return ''

    def _get_description(self, root: ET.Element) -> str:
        """
        取得說明書
        TIPO 格式在 <description> 標籤中,包含多個 <p> 段落
        """
        # TIPO 使用 <description> 標籤
        desc_elem = root.find('.//description')
        if desc_elem is not None:
            text = ''.join(desc_elem.itertext()).strip()
            if text:
                return text

        return ''

    def _get_claims(self, root: ET.Element) -> List[str]:
        """
        取得申請專利範圍 (請求項)
        TIPO 格式在 <claims> 標籤中,每個請求項在 <claim> 標籤內
        """
        claims = []

        # TIPO 使用 <claims><claim num="1">...</claim></claims> 結構
        claim_elems = root.findall('.//claims/claim')
        if claim_elems:
            for claim in claim_elems:
                claim_num = claim.get('num', '')
                text = ''.join(claim.itertext()).strip()
                if text:
                    if claim_num:
                        claims.append(f"請求項{claim_num}: {text}")
                    else:
                        claims.append(text)

        return claims

    def _get_persons(self, root: ET.Element, person_type: str) -> str:
        """
        取得人員資訊 (發明人/申請人)

        Args:
            person_type: 'Inventor' 或 'Applicant'
        """
        persons = []

        # 尋找所有該類型的人員
        for person in root.findall(f'.//{person_type}'):
            name = person.findtext('.//Name')
            if not name:
                name = person.findtext('.//PersonName')
            if not name:
                name = ''.join(person.itertext()).strip()

            if name:
                persons.append(name.strip())

        # 返回逗號分隔的字串
        return ', '.join(persons) if persons else ''

    def _get_ipc(self, root: ET.Element) -> str:
        """
        取得 IPC 國際專利分類
        """
        ipc_codes = []

        # 嘗試多種標籤
        for xpath in ['.//IPC', './/IPCCode', './/Classification/IPC']:
            for ipc_elem in root.findall(xpath):
                code = ''.join(ipc_elem.itertext()).strip()
                if code:
                    ipc_codes.append(code)

        return ', '.join(ipc_codes) if ipc_codes else ''

    def _get_patent_type(self, root: ET.Element) -> str:
        """
        取得專利類別 (發明/新型/設計)
        """
        # 嘗試從 PatentType 或 Kind 標籤取得
        patent_type = self._get_text(root, './/PatentType')
        if not patent_type:
            patent_type = self._get_text(root, './/Kind')

        # 標準化類別名稱
        if '發明' in patent_type:
            return 'invention'
        elif '新型' in patent_type:
            return 'utility'
        elif '設計' in patent_type:
            return 'design'

        return patent_type or 'unknown'

    def parse_index_xml(self, index_xml: str) -> List[Dict]:
        """
        解析索引 XML (index.xml)
        包含該期所有專利的基本資訊

        Args:
            index_xml: index.xml 檔案路徑

        Returns:
            專利列表,每個專利包含基本資訊
        """
        try:
            tree = ET.parse(index_xml)
            root = tree.getroot()

            patents = []

            # 尋找所有專利項目
            for patent_elem in root.findall('.//Patent'):
                patent_info = {
                    'application_number': self._get_text(patent_elem, './/ApplicationNum'),
                    'patent_number': self._get_text(patent_elem, './/CertificateNum'),
                    'title': self._get_text(patent_elem, './/InventionTitle'),
                    'xml_filename': self._get_text(patent_elem, './/FileName'),
                }
                patents.append(patent_info)

            logger.info(f"從 index.xml 解析出 {len(patents)} 個專利")
            return patents

        except Exception as e:
            logger.error(f"解析 index.xml 失敗: {e}")
            return []

    def parse_directory(
        self,
        directory: str,
        max_files: Optional[int] = None
    ) -> List[Dict]:
        """
        解析整個目錄中的所有專利 XML

        Args:
            directory: 目錄路徑
            max_files: 最多解析幾個檔案 (None = 全部)

        Returns:
            專利文件列表
        """
        patents = []
        xml_files = []

        # 遞迴尋找所有 XML 檔案 (排除 index.xml 和 dtd)
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.xml') and file.lower() not in ['index.xml', 'patent.dtd']:
                    xml_files.append(os.path.join(root, file))

        logger.info(f"找到 {len(xml_files)} 個 XML 檔案在 {directory}")

        # 限制數量
        if max_files:
            xml_files = xml_files[:max_files]
            logger.info(f"限制解析數量: {max_files}")

        # 解析每個檔案
        for i, xml_file in enumerate(xml_files, 1):
            if i % 100 == 0:
                logger.info(f"已解析 {i}/{len(xml_files)} 個檔案...")

            patent = self.parse_patent_xml(xml_file)
            if patent:
                patents.append(patent)

        logger.info(f"成功解析 {len(patents)}/{len(xml_files)} 個專利文件")
        return patents

    def save_patents_json(self, patents: List[Dict], output_file: str):
        """
        儲存專利資料為 JSON

        Args:
            patents: 專利列表
            output_file: 輸出檔案路徑
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(patents, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 已儲存 {len(patents)} 個專利至: {output_file}")


# 便利函數

def parse_patent_directory(
    directory: str,
    output_json: str,
    max_files: Optional[int] = None
) -> List[Dict]:
    """
    便利函數: 解析專利目錄並儲存為 JSON

    Args:
        directory: 專利 XML 檔案目錄
        output_json: 輸出 JSON 檔案路徑
        max_files: 最多解析幾個檔案

    Returns:
        專利列表
    """
    parser = TIPOXMLParser()
    patents = parser.parse_directory(directory, max_files)

    if patents:
        parser.save_patents_json(patents, output_json)

    return patents


if __name__ == '__main__':
    # 測試解析
    import sys

    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
    else:
        test_dir = './test_downloads'

    print(f"測試解析目錄: {test_dir}")

    patents = parse_patent_directory(
        directory=test_dir,
        output_json='parsed_patents.json',
        max_files=10  # 測試只解析 10 個
    )

    print(f"\n解析完成! 共 {len(patents)} 個專利")

    if patents:
        print("\n第一個專利範例:")
        print(json.dumps(patents[0], ensure_ascii=False, indent=2))
