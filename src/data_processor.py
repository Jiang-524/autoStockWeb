"""
data_processor.py - 股票数据处理与存储模块

负责格式化股票数据并保存为 JSON 文件。
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataProcessor:
    """股票数据处理器"""

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化数据处理器

        Args:
            data_dir: 数据保存目录，默认为项目根目录下的 data/
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"数据目录: {self.data_dir}")

    def format_data(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        格式化原始数据为统一结构

        Args:
            raw_data: 原始股票数据列表

        Returns:
            格式化后的数据字典
        """
        formatted_stocks = []

        for item in raw_data:
            if not item:
                continue

            # 提取并转换数值
            formatted = {
                "stock_code": item.get("stock_code", ""),
                "stock_name": item.get("stock_name", ""),
                "current_price": self._to_float(item.get("current_price")),
                "change_percent": self._to_float(item.get("change_percent")),
                "volume": self._to_float(item.get("volume")),
                "turnover": self._to_float(item.get("turnover")),
                "high": self._to_float(item.get("high")),
                "low": self._to_float(item.get("low")),
                "open": self._to_float(item.get("open")),
                "previous_close": self._to_float(item.get("previous_close")),
                "fetch_time": item.get("fetch_time", ""),
                "data_source": item.get("data_source", "unknown"),
            }

            # 如果存在错误信息，保留它
            if "error" in item:
                formatted["error"] = item["error"]

            formatted_stocks.append(formatted)

        return {
            "meta": {
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_count": len(formatted_stocks),
                "success_count": sum(1 for s in formatted_stocks if "error" not in s),
                "data_version": "1.0",
            },
            "stocks": formatted_stocks,
        }

    def _to_float(self, value: Any) -> Optional[float]:
        """
        安全地将值转换为浮点数

        Args:
            value: 待转换的值

        Returns:
            转换后的浮点数，失败返回 None
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # 处理中文数字格式
            cleaned = value.replace(",", "").replace("，", "")
            # 处理单位
            if "万" in cleaned:
                cleaned = cleaned.replace("万", "")
                try:
                    return float(cleaned) * 10000
                except ValueError:
                    pass
            if "亿" in cleaned:
                cleaned = cleaned.replace("亿", "")
                try:
                    return float(cleaned) * 100000000
                except ValueError:
                    pass
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def save_to_json(
        self,
        data: Dict[str, Any],
        filename: Optional[str] = None,
        pretty: bool = True,
    ) -> str:
        """
        保存数据为 JSON 文件

        Args:
            data: 要保存的数据
            filename: 文件名，默认自动生成
            pretty: 是否格式化输出

        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stock_data_{timestamp}.json"

        filepath = self.data_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                if pretty:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(data, f, ensure_ascii=False)

            logger.info(f"数据已保存: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            raise

    def save_raw_data(
        self,
        raw_data: List[Dict[str, Any]],
        filename: Optional[str] = None,
    ) -> str:
        """
        便捷方法：格式化并保存原始数据

        Args:
            raw_data: 原始股票数据列表
            filename: 文件名

        Returns:
            保存的文件路径
        """
        formatted = self.format_data(raw_data)
        return self.save_to_json(formatted, filename)

    def list_data_files(self) -> List[str]:
        """
        列出数据目录中的所有 JSON 文件

        Returns:
            文件名列表
        """
        files = sorted(self.data_dir.glob("*.json"))
        return [f.name for f in files]

    def read_data_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        读取数据文件

        Args:
            filename: 文件名

        Returns:
            文件内容，失败返回 None
        """
        filepath = self.data_dir / filename
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None


if __name__ == "__main__":
    # 简单测试
    logging.basicConfig(level=logging.INFO)

    processor = DataProcessor()

    # 测试数据
    test_data = [
        {
            "stock_code": "002747",
            "stock_name": "埃斯顿",
            "current_price": "25.30",
            "change_percent": "2.15%",
            "volume": "125000",
            "turnover": "3162500",
            "high": "26.00",
            "low": "24.80",
            "open": "25.00",
            "previous_close": "24.77",
            "fetch_time": "2024-01-01 10:00:00",
            "data_source": "test",
        }
    ]

    result = processor.save_raw_data(test_data)
    print(f"保存到: {result}")
