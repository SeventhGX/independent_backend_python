import logging
from logging.handlers import TimedRotatingFileHandler


class ColoredFormatter(logging.Formatter):
    """自定义的带颜色的日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"  # 重置颜色

    def format(self, record):
        # 保存原始的 levelname
        original_levelname = record.levelname
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        # 格式化消息
        result = super().format(record)
        # 恢复原始 levelname
        record.levelname = original_levelname
        return result


logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(asctime)s]%(name)s - %(levelname)s - %(message)s")

colored_formatter = ColoredFormatter("[%(asctime)s]%(name)s - %(levelname)s - %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(colored_formatter)

logger.addHandler(stream_handler)

time_file_handler = TimedRotatingFileHandler(
    "log/app.log", when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
time_file_handler.setLevel(logging.DEBUG)
time_file_handler.setFormatter(formatter)

logger.addHandler(time_file_handler)


if __name__ == "__main__":
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
