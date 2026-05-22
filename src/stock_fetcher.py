"""
stock_fetcher.py - A股实时股票数据获取模块

使用 akshare 库获取 A 股实时行情数据。
支持读取配置文件，批量获取多支股票数据。
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

import akshare as ak
import pandas as pd

# 配置日志
logger = logging.getLogger(__name__)


class StockFetcher:
    """A股实时股票数据获取器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化股票获取器

        Args:
            config_path: 股票配置文件路径，默认为 config/stocks.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "stocks.json"
        self.config_path = Path(config_path)
        self.stocks: List[Dict[str, str]] = []
        self._load_config()

    def _load_config(self) -> None:
        """加载股票配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.stocks = config.get("stocks", [])
            logger.info(f"成功加载 {len(self.stocks)} 支股票配置")
        except FileNotFoundError:
            logger.error(f"配置文件未找到: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"配置文件解析失败: {e}")
            raise

    def _format_stock_code(self, code: str, market: str) -> str:
        """
        格式化股票代码为 akshare 需要的格式

        Args:
            code: 股票代码
            market: 市场代码 (SH/SZ)

        Returns:
            格式化后的代码，如 sh688017
        """
        market_lower = market.lower()
        return f"{market_lower}{code}"

    def fetch_single_stock(self, code: str, market: str, name: str) -> Optional[Dict[str, Any]]:
        """
        获取单支股票的实时数据

        Args:
            code: 股票代码
            market: 市场代码
            name: 股票名称

        Returns:
            包含股票实时数据的字典，失败返回 None
        """
        formatted_code = self._format_stock_code(code, market)
        logger.info(f"正在获取 {name}({code}) 的实时数据...")

        try:
            # 使用 akshare 获取实时行情
            df = ak.stock_individual_spot_xq(symbol=formatted_code)

            if df is None or df.empty:
                logger.warning(f"{name}({code}) 返回空数据")
                return None

            # 提取所需字段
            data = self._parse_stock_data(df, code, name)
            logger.info(f"成功获取 {name}({code}): 当前价 {data.get('current_price', 'N/A')}")
            return data

        except Exception as e:
            logger.error(f"获取 {name}({code}) 数据失败: {e}")
            # 尝试备用方案
            return self._fetch_backup(code, market, name)

    def _parse_stock_data(self, df: pd.DataFrame, code: str, name: str) -> Dict[str, Any]:
        """
        解析 akshare 返回的 DataFrame 数据

        Args:
            df: akshare 返回的 DataFrame
            code: 股票代码
            name: 股票名称

        Returns:
            标准化后的股票数据字典
        """
        # akshare stock_individual_spot_xq 返回的列名映射
        # 根据实际返回结构调整
        try:
            # 尝试获取关键字段
            data = {
                "stock_code": code,
                "stock_name": name,
                "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "data_source": "akshare"
            }

            # DataFrame 通常是两列：item 和 value
            if "item" in df.columns and "value" in df.columns:
                values = dict(zip(df["item"], df["value"]))

                # 映射关键字段
                field_mapping = {
                    "current_price": ["现价", "最新价", "current"],
                    "change_percent": ["涨跌幅", "涨幅", "change_percent"],
                    "volume": ["成交量", "volume", "vol"],
                    "turnover": ["成交额", "turnover", "amount"],
                    "high": ["最高", "最高价", "high"],
                    "low": ["最低", "最低价", "low"],
                    "open": ["今开", "开盘价", "open"],
                    "previous_close": ["昨收", "昨收价", "previous_close", "pre_close"],
                }

                for key, possible_names in field_mapping.items():
                    for pn in possible_names:
                        if pn in values:
                            data[key] = values[pn]
                            break

                # 保存原始数据用于调试
                data["raw_data"] = values

            else:
                # 如果是标准 DataFrame 格式
                if not df.empty:
                    row = df.iloc[0]
                    data.update({
                        "current_price": row.get("最新价") or row.get("现价"),
                        "change_percent": row.get("涨跌幅"),
                        "volume": row.get("成交量"),
                        "turnover": row.get("成交额"),
                        "high": row.get("最高") or row.get("最高价"),
                        "low": row.get("最低") or row.get("最低价"),
                        "open": row.get("今开") or row.get("开盘价"),
                        "previous_close": row.get("昨收") or row.get("昨收价"),
                    })

            return data

        except Exception as e:
            logger.error(f"解析数据失败: {e}")
            return {
                "stock_code": code,
                "stock_name": name,
                "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e),
                "raw_data": df.to_dict() if df is not None else None
            }

    def _fetch_backup(self, code: str, market: str, name: str) -> Optional[Dict[str, Any]]:
        """
        备用获取方案：使用东方财富 API

        Args:
            code: 股票代码
            market: 市场代码
            name: 股票名称

        Returns:
            股票数据字典，失败返回 None
        """
        logger.info(f"尝试备用方案获取 {name}({code})...")
        try:
            # 使用 akshare 的东方财富接口
            # 注意：这个接口获取全部数据，需要筛选
            df = ak.stock_zh_a_spot_em()

            # 筛选目标股票
            target = df[df["代码"] == code]
            if target.empty:
                logger.warning(f"备用方案未找到 {code}")
                return None

            row = target.iloc[0]
            return {
                "stock_code": code,
                "stock_name": name,
                "current_price": row.get("最新价"),
                "change_percent": row.get("涨跌幅"),
                "volume": row.get("成交量"),
                "turnover": row.get("成交额"),
                "high": row.get("最高"),
                "low": row.get("最低"),
                "open": row.get("今开"),
                "previous_close": row.get("昨收"),
                "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "data_source": "akshare_backup"
            }

        except Exception as e:
            logger.error(f"备用方案也失败了: {e}")
            return None

    def fetch_all_stocks(self, delay: float = 0.5) -> List[Dict[str, Any]]:
        """
        批量获取所有配置股票的实时数据

        Args:
            delay: 请求间隔秒数，避免请求过快

        Returns:
            股票数据列表
        """
        results = []
        total = len(self.stocks)

        logger.info(f"开始获取 {total} 支股票数据...")

        for i, stock in enumerate(self.stocks, 1):
            code = stock.get("code", "")
            market = stock.get("market", "")
            name = stock.get("name", "")

            if not code or not market:
                logger.warning(f"股票配置不完整: {stock}")
                continue

            data = self.fetch_single_stock(code, market, name)
            if data:
                results.append(data)

            # 显示进度
            logger.info(f"进度: {i}/{total}")

            # 请求间隔
            if i < total:
                time.sleep(delay)

        logger.info(f"数据获取完成: 成功 {len(results)}/{total}")
        return results

    def get_stock_info(self) -> List[Dict[str, str]]:
        """获取股票配置列表"""
        return self.stocks


if __name__ == "__main__":
    # 简单测试
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    fetcher = StockFetcher()
    results = fetcher.fetch_all_stocks()
    print(f"获取到 {len(results)} 支股票数据")
    for r in results:
        print(f"{r['stock_name']}({r['stock_code']}): {r.get('current_price', 'N/A')}")
