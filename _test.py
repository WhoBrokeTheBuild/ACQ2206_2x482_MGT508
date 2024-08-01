
import MDSplus
from ACQ2206_2X482_MGT508 import ACQ2206_2X482_MGT508

tree = MDSplus.Tree('mgttest', -1, 'NEW')
ACQ2206_2X482_MGT508.Add(tree, 'ACQ')

tree.ACQ.ACQ_ADDRESS.record = 'acq2206-014'
tree.ACQ.MGT_ADDRESS.record = 'mgt508-005'
tree.ACQ.TRIGGER.SOURCE.record = 'STRIG'
tree.ACQ.SAMPLES.record = 125_000_000

tree.write()
tree.close()


tree = MDSplus.Tree('mgttest', -1)
tree.createPulse(42)
tree.close()


tree = MDSplus.Tree('mgttest', 42)
tree.ACQ.init()

