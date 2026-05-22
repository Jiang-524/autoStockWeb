#!/usr/bin/env python3
"""
main.py - A股实时股票数据获取入口脚本

用法:
    python main.py              # 获取所有配置股票数据
    python main.py --list       # 列出已保存的数据文件
    python main.py --read <file> # 读取指定数据文件
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_fetcher import StockFetcher
from data_processor import DataProcessor


def setup_logging(level: int = logging.INFO) -> None:
    """配置日志输出"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def fetch_all_stocks() -> None:
    """获取所有股票数据并保存"""
    logger = logging.getLogger("main")

    try:
        # 初始化组件
        fetcher = StockFetcher()
        processor = DataProcessor()

        # 获取数据
        logger.info("=" * 50)
        logger.info("开始获取 A 股实时股票数据")
        logger.info("=" * 50)

        raw_data = fetcher.fetch_all_stocks(delay=0.5)

        if not raw_data:
            logger.warning("未获取到任何股票数据")
            return

        # 保存数据
        filepath = processor.save_raw_data(raw_data)

        # 输出摘要
        formatted = processor.format_data(raw_data)
        meta = formatted.get("meta", {})

        logger.info("=" * 50)
        logger.info("数据获取完成")
        logger.info(f"总计: {meta.get('total_count', 0)} 支")
        logger.info(f"成功: {meta.get('success_count', 0)} 支")
        logger.info(f"保存路径: {filepath}")
        logger.info("=" * 50)

        # 打印简要数据
        print("\n股票数据摘要:")
        print("-" * 60)
        print(f"{'名称':<10} {'代码':<8} {'当前价':<10} {'涨跌幅':<10}")
        print("-" * 60)

        for stock in formatted.get("stocks", []):
            name = stock.get("stock_name", "N/A")[:8]
            code = stock.get("stock_code", "N/A")
            price = stock.get("current_price")
            change = stock.get("change_percent")

            price_str = f"{price:.2f}" if price is not None else "N/A"
            change_str = f"{change:.2f}%" if change is not None else "N/A"

            print(f"{name:<10} {code:<8} {price_str:<10} {change_str:<10}")

        print("-" * 60)

    except Exception as e:
        logger.error(f"运行失败: {e}", exc_info=True)
        sys.exit(1)


def list_data_files() -> None:
    """列出已保存的数据文件"""
    processor = DataProcessor()
    files = processor.list_data_files()

    if not files:
        print("暂无数据文件")
        return

    print("已保存的数据文件:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f}")


def read_data_file(filename: str) -> None:
    """读取并显示数据文件内容"""
    processor = DataProcessor()
    data = processor.read_data_file(filename)

    if data is None:
        print(f"无法读取文件: {filename}")
        return

    import json

    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="A股实时股票数据获取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python main.py              # 获取所有股票数据
    python main.py --list       # 列出历史数据文件
    python main.py --read stock_data_20240101_120000.json
        """,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="列出已保存的数据文件",
    )
    parser.add_argument(
        "--read",
        metavar="FILE",
        help="读取指定的数据文件",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试日志",
    )

    args = parser.parse_args()

    # 设置日志级别
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)

    if args.list:
        list_data_files()
    elif args.read:
        read_data_file(args.read)
    else:
        fetch_all_stocks()


if __name__ == "__main__":
    main()
