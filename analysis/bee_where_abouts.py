import csv
import numpy
import matplotlib.pyplot

def plot (filename, sampling_length, sampling_delta):
    with open (filename, 'r') as fd:
        reader = csv.reader (fd, delimiter = ';', quoting = csv.QUOTE_NONNUMERIC)
        data = numpy.array ([row for row in reader])
    figure_width, figure_height = 12, 4
    margin_left, margin_right  = 0.75, 0.1
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    axes = figure.subplots (
        nrows = 1,
        ncols = 3,
        gridspec_kw = {
            'width_ratios' : [2, 1, 2],
            'wspace' : 0.5,
            'right' : 1 - margin_right / figure_width,
            'left' : margin_left / figure_width,
        }
    )
    axes [0].boxplot (
        data [:, 3:7],
        labels = ['core\n1st period', 'leaf\n1st period', 'core\n3rd period', 'leaf\n3rd period']
    )
    axes [0].set_ylim (-0.03, 1.03)
    axes [0].set_ylabel ('absolute\nsensor activity (a.u.)')
    axes [1].violinplot (
        data [:, 7:9],
    )
    axes [1].set_ylim (-1.03, 1.03)
    axes [1].set_ylabel ('leaf-core\nsensor activity (a.u.)')
    axes [2].scatter (
        data [:, 7],
        data [:, 8]
    )
    axes [2].set_xlabel ('leaf-core sensor activity\nfirst period (a.u.)')
    axes [2].set_xlim (-1.03, 1.03)
    axes [2].set_ylabel ('leaf-core sensor activity\nthird period (a.u.)')
    axes [2].set_ylim (-1.03, 1.03)
    figure.suptitle ('Sensor activity\nlast {}s of first and third period'.format (sampling_length))
    figure.savefig ('bee-where-about_L={}_D={}.png'.format (sampling_length, sampling_delta))
