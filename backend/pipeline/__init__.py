"""
Pipeline __init__
导出便捷函数供 pipeline/run.py 调用。
"""
from pipeline.writer import SQLiteWriter
from pipeline.exporter import StaticExporter

__all__ = ["SQLiteWriter", "StaticExporter"]
