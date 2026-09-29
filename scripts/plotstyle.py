import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Reference categorical palette (dataviz skill, validated light-mode order)
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
CLASS_COLOR = {'BH': '#2a78d6', 'NS': '#eb6834'}
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'axes.edgecolor': INK2,
                     'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.grid': True,
                     'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False,
                     'lines.linewidth': 1.6, 'font.size': 9, 'axes.titlesize': 10, 'legend.frameon': False,
                     'savefig.dpi': 150, 'savefig.bbox': 'tight'})


def source_colors(source_ids):
    return {s: SERIES[i % len(SERIES)] for i, s in enumerate(source_ids)}
