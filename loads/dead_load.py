#dead_load.py
"""
Ölü Yük Analizi
TS 498
"""

from utils.report_dataframe import ReportDataFrame


class DeadLoad:

    def __init__(self, load_manager):
        self.load_manager = load_manager

    def report(self) -> ReportDataFrame:

        rows = self.load_manager.definition_rows("G")

        return ReportDataFrame(rows)

    def get_load_patterns(self) -> dict[str, float]:

        return {
            "DEAD": 1.0
        }

