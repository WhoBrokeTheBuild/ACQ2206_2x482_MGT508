
import MDSplus
from ACQ2206_2X482_MGT508 import ACQ2206_2X482_MGT508

tree = MDSplus.Tree('mgttest', -1, 'NEW')
ACQ2206_2X482_MGT508.Add(tree, 'ACQ')

tree.ACQ.ACQ_ADDRESS.record = 'acq2206-014'
tree.ACQ.MGT_ADDRESS.record = 'mgt508-005'
tree.ACQ.TRIGGER.SOURCE.record = 'STRIG'
# tree.ACQ.FREQUENCY.record = 8_675_309
tree.ACQ.SAMPLES.record = 25_000_000

tree.ACQ.INPUTS.INPUT_01.on = False
tree.ACQ.INPUTS.INPUT_05.on = False
tree.ACQ.INPUTS.INPUT_10.on = False
tree.ACQ.INPUTS.INPUT_20.on = False

tree.write()
tree.close()


tree = MDSplus.Tree('mgttest', -1)
tree.createPulse(42)
tree.close()


tree = MDSplus.Tree('mgttest', 42)
tree.ACQ.init_and_store()

