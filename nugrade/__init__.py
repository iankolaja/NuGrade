from .nuclide import Nuclide, Reaction
from .metric_options import MetricOptions
from .grading_functions import grade_isotope, grade_all_isotopes, plot_grades
import pandas as pd

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

pickle_path = pkg_resources.open_binary('nugrade', 'EXFOR.pkl')
exfor_data = pd.read_pickle(pickle_path, compression=None)

__all__ = ['Nuclide', 'Reaction', 'exfor_data', 'MetricOptions',
           'grade_isotope', 'grade_many_isotopes', 'plot_grades']
