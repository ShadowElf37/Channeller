import warnings

class IndustrialGradeWarningSuppressor(warnings.catch_warnings):
    def __enter__(self, *args):
        super().__enter__()
        warnings.simplefilter('ignore')

"""
with IndustrialGradeWarningSuppressor():
    ...
"""