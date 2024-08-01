
import MDSplus
from matplotlib import pyplot

t = MDSplus.Tree('mgttest', 42)

x = t.ACQ.INPUTS.INPUT_01.data()
y = t.ACQ.INPUTS.INPUT_01.dim_of().data()

one_sine = t.ACQ.FREQUENCY.data() // 1000 # The sine wave is at 1KHz
x = x[ : one_sine ]
y = y[ : one_sine ]

pyplot.plot(y, x)
pyplot.show()