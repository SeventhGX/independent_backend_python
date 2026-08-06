from functools import lru_cache

from matplotlib import font_manager
from matplotlib.font_manager import FontProperties

_CHINESE_FONT_CANDIDATES = (
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Source Han Sans SC",
    "Source Han Sans CN",
    "WenQuanYi Zen Hei",
    "PingFang SC",
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
)


@lru_cache(maxsize=1)
def get_chinese_font() -> FontProperties:
    for font_name in _CHINESE_FONT_CANDIDATES:
        try:
            font_path = font_manager.findfont(font_name, fallback_to_default=False)
        except ValueError:
            continue
        return FontProperties(fname=font_path)
    raise RuntimeError("未找到支持中文的字体，请安装 Noto Sans CJK 字体")
