"""
日誌管理工具

提供統一的日誌配置與管理功能
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
    format_string: Optional[str] = None
) -> None:
    """
    設定全域日誌配置
    
    Args:
        log_level: 日誌等級 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日誌文件路徑
        rotation: 日誌輪替大小
        retention: 日誌保留時間
        format_string: 自定義格式
    """
    
    # 移除預設處理器
    logger.remove()
    
    # 設定預設格式
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # 添加控制台輸出
    logger.add(
        sys.stdout,
        level=log_level,
        format=format_string,
        colorize=True,
        catch=True
    )
    
    # 添加文件輸出（如果指定）
    if log_file:
        # 確保日誌目錄存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            level=log_level,
            format=format_string.replace("<green>", "").replace("</green>", "")
                  .replace("<level>", "").replace("</level>", "")
                  .replace("<cyan>", "").replace("</cyan>", ""),
            rotation=rotation,
            retention=retention,
            catch=True,
            encoding="utf-8"
        )
    
    logger.info(f"Logging initialized - Level: {log_level}")
    if log_file:
        logger.info(f"Log file: {log_file}")


def get_logger(name: str):
    """
    獲取指定名稱的日誌器
    
    Args:
        name: 日誌器名稱
        
    Returns:
        loguru.Logger 實例
    """
    return logger.bind(name=name)


def log_trade_event(event_type: str, data: dict):
    """
    記錄交易事件的專用函數
    
    Args:
        event_type: 事件類型 (SIGNAL, ORDER, FILL, ERROR 等)
        data: 事件數據
    """
    logger.info(f"[{event_type}] {data}")


def log_strategy_decision(strategy_name: str, symbol: str, 
                         decision: str, reason: str):
    """
    記錄策略決策的專用函數
    
    Args:
        strategy_name: 策略名稱
        symbol: 交易對
        decision: 決策結果
        reason: 決策原因
    """
    logger.info(
        f"[STRATEGY] {strategy_name} | {symbol} | "
        f"Decision: {decision} | Reason: {reason}"
    )


def log_performance_metrics(metrics: dict):
    """
    記錄績效指標的專用函數
    
    Args:
        metrics: 績效指標字典
    """
    logger.info(f"[PERFORMANCE] {metrics}")


def log_system_health(component: str, status: str, details: dict = None):
    """
    記錄系統健康狀態的專用函數
    
    Args:
        component: 系統組件名稱
        status: 狀態 (HEALTHY, WARNING, ERROR)
        details: 詳細資訊
    """
    message = f"[HEALTH] {component}: {status}"
    if details:
        message += f" | Details: {details}"
    
    if status == "ERROR":
        logger.error(message)
    elif status == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)