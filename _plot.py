
import MDSplus
from matplotlib import pyplot

ch = 1
import sys
if len(sys.argv) > 1:
    ch = int(sys.argv[1])

t = MDSplus.Tree('mgttest', 42)

node = t.ACQ.INPUTS.getNode(f'INPUT_{ch:02}')
x = node.data()
y = node.dim_of().data()

# one_sine = t.ACQ.FREQUENCY.data() // 1000 # The sine wave is at 1KHz
# x = x[ : one_sine ]
# y = y[ : one_sine ]

pyplot.plot(y, x)
pyplot.show()
