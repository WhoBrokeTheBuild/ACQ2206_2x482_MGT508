
import MDSplus
from matplotlib import pyplot

ch = 1
import sys
if len(sys.argv) > 1:
    ch = int(sys.argv[1])

t = MDSplus.Tree('mgttest', 42)

fig, ax = pyplot.subplots(8, 4, figsize=(10, 10))

for i in range(32):
    ch = i + 1

    node = t.ACQ.INPUTS.getNode(f'INPUT_{ch:02}')
    x = node.data()
    y = node.dim_of().data()

    # TODO: Parse FREQUENCY
    one_sine = 9_000_000 // 1000 # The sine wave is at 1KHz
    x1 = x[ : one_sine ]
    y1 = y[ : one_sine ]

    ax.flat[i].set_title(f"Ch {ch:02}")
    ax.flat[i].plot(y1, x1, color='blue')

    x2 = x[ one_sine : one_sine * 2 ]
    y2 = y[ one_sine : one_sine * 2 ]
    ax.flat[i].plot(y2, x2, color='orange')


fig.tight_layout()
pyplot.show()

