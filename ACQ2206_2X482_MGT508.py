
import MDSplus

class ACQ2206_2X482_MGT508(MDSplus.Device):
    """
    Represents an ACQ2206 chassis with 2x ACQ482ELF modules and a MGT508 DRAM card
    """
    
    _TRIGGER_SOURCE_D0_OPTIONS = [
        'EXT',
        'HDMI',
        'GPG0',
        'WRTT0',
    ]
    """
    Trigger Source options for Signal Highway d0
    * EXT: External Trigger
    * HDMI: HDMI Trigger
    * GPG0: Gateway Pulse Generator Trigger
    * WRTT0: White Rabbit Trigger
    """

    _TRIGGER_SOURCE_D1_OPTIONS = [
        'STRIG',
        'HDMI_GPIO',
        'GPG1',
        'FP_SYNC',
        'WRTT1',
    ]
    """
    Trigger Source options for Signal Highway d1
    * STRIG: Software Trigger
    * HDMI_GPIO: HDMI General Purpose I/O Trigger
    * GPG1: Gateway Pulse Generator Trigger
    * FP_SYNC: Front Panel SYNC port
    * WRTT1: White Rabbit Trigger
    """

    parts = [
        {
            'path': ':COMMENT',
            'type': 'text',
            'options': ('no_write_shot',),
        },
        {
            'path': ':ACQ_ADDRESS',
            'type': 'text',
            'options': ('no_write_shot',),
        },
        {
            'path': ':MGT_ADDRESS',
            'type': 'text',
            'options': ('no_write_shot',),
        },
        {
            'path': ':FREQUENCY',
            'type': 'numeric',
            'value': 25_000_000,
            'options': ('no_write_shot',),
        },
        {
            'path':':SAMPLES',
            'type':'numeric',
            'value': 125_000_000,
            'options':('no_write_shot',),
        },
        {
            'path': ':INIT_ACTION',
            'type': 'action',
            'valueExpr': "Action(Dispatch('MDSIP_SERVER','INIT',50,None),Method(None,'INIT',head))",
            'options': ('no_write_shot',)
        },
        {
            'path': ':TRIGGER',
            'type': 'structure',
        },
        {
            'path': ':TRIGGER:TIMESTAMP', # Or TIME_OF_DAY
            'type': 'numeric',
            'options': ('write_shot',),
        },
        {
            'path': ':TRIGGER:SOURCE',
            'type': 'text',
            'value': 'EXT',
            'options': ('no_write_shot',),
        },
        {
            'path': ':RUNNING',
            'type': 'numeric',
            # 'on': False,
            'options': ('no_write_model',),
        },
        {
            'path': ':EVENT_NAME',
            'type': 'text',
            'value': 'ACQ2206_STORE',
            'options': ('no_write_shot',),
        },
        {
            'path': ':INPUTS',
            'type': 'structure',
        },
    ]

    for i in range(32):
        parts.append({
            'path': f':INPUTS:INPUT_{(i + 1):02}',
            'type': 'signal',
            'options': ('no_write_model',),
        })


    def soft_trigger(self):
        import time
        import acq400_hapi

        uut = acq400_hapi.factory(self.ACQ_ADDRESS.data())

        while acq400_hapi.pv(uut.s0.CONTINUOUS_STATE) != 'ARM':
            time.sleep(1)

        uut.s0.soft_trigger = '1'

    SOFT_TRIGGER = soft_trigger

    def abort(self):
        import acq400_hapi

        uut = acq400_hapi.factory(self.ACQ_ADDRESS.data())
        # uut.s0.set_abort = '1'
        uut.s0.CONTINUOUS = '0'

        self.RUNNING.on = False

    ABORT = abort

    def init(self):
        import time
        import math
        import numpy
        import socket
        import acq400_hapi
        from acq400_hapi.acq400 import Mgt508Ports
        acq400_hapi.Mgt508Ports = Mgt508Ports
        from datetime import datetime

        try:
            acq400_hapi.Mgt508
        except:
            raise Exception('You need a newer version of acq400_hapi')
        
        self.RUNNING.on = True
        
        acq_address = self.ACQ_ADDRESS.data()
        mgt_address = self.MGT_ADDRESS.data()
        
        self.dprint(1, f'Connecting to ACQ {acq_address} / MGT {mgt_address}')

        # Get the ACQ/MGT Siteclient objects
        uut = acq400_hapi.factory(acq_address)
        mgt = acq400_hapi.Mgt508(mgt_address)

        # Configure the aggregator to send data do the MGT? We think?
        uut.cA.aggregator = 'sites=1,2,3,4 spad=0 on'

        # Transfer the "sample size in bytes" from the ACQ to the MGT
        mgt.s0.ssb = uut.s0.ssb

        # Wait for the device to be in a clean, IDLE state
        while acq400_hapi.pv(uut.s0.CONTINUOUS_STATE) != 'IDLE':
            uut.s0.CONTINUOUS = 0
            self.dprint(1, f'WARNING: requesting {uut.uut} to stop')
            time.sleep(1)

        # If the trigger takes too long, then the MGT will give up on the PULL
        # in order to prevent this, we set the timeout to a huge number
        mgt.s0.AXIDMA_ONCE_TO_MSEC = int(60 * 60 * 24 * 1000) # 24 hours in msec

        # The channel data is not packed in the regular linear order, instead you
        # have to check the channel_mapping for the order, and then unpack the data
        channel_mapping = list(map(int, uut.s0.channel_mapping.split(',')))
        channel_count = len(channel_mapping)

        sample_count = int(self.SAMPLES.data())

        role = 'master'
        frequency = int(self.FREQUENCY.data())
        clock_period = float(1.0 / self.FREQUENCY.data())

        # We need to determine the timing highway based on the trigger source
        # The two highways are d0 and d1
        trigger_source = str(self.TRIGGER.SOURCE.data()).upper()
        if trigger_source in self._TRIGGER_SOURCE_D0_OPTIONS:
            trg_dx = 'd0'
        elif trigger_source in self._TRIGGER_SOURCE_D1_OPTIONS:
            trg_dx = 'd1'

        # Ideally we wouldn't do this every time, but there shouldn't be any harm other
        # than it taking a little while to run
        sync_role = f'{role} {frequency} TRG:DX={trg_dx}'
        self.dprint(1, f'Setting sync_role="{sync_role}"')
        uut.s0.sync_role = sync_role

        self.dprint(1, f'Setting trigger source to {trigger_source}')
        if trg_dx == 'd0':
            uut.s0.SIG_SRC_TRG_0 = trigger_source
        elif trg_dx == 'd1':
            uut.s0.SIG_SRC_TRG_1 = trigger_source
        
        # The MGT508 deals in "buffers", not in "samples", so we need to convert our
        # (sample count * sample size) into bytes, and then into megabytes for some reason
        total_bytes = sample_count * channel_count * uut.data_size()
        total_mb = int(math.ceil(total_bytes / 1_000_000))

        self.dprint(1, f'Setting capture length to {total_mb}MB')
        mgt.set_capture_length(total_mb)

        try:

            # So long as the "auto soft trigger" is disabled, this will arm the device for capture
            # Note that this looks a lot like streaming, internally the ACQ is running in a streaming
            # mode, not in transient
            self.dprint(1, f'Arming')
            uut.s0.CONTINUOUS = '1'
                
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pull_address = (mgt_address, acq400_hapi.Mgt508Ports.PULL)
            self.dprint(1, f'Connecting to {pull_address} to initiate PULL')
            s.connect(pull_address)

            # Might be problematic on some systems
            s.setblocking(False)

            finished = False
            with s.makefile() as f:
                while self.RUNNING.on:
                    try:
                        line = f.readline().rstrip()
                    except socket.timeout:
                        continue
                    except socket.error:
                        break

                    if len(line) == 0:
                        continue

                    if not line[0].isnumeric():
                        self.dprint(1, f'PULL: {line}')

                    if line == 'stall detected':
                        break

                    if line == 'finished':
                        finished = True
                        break

            uut.s0.CONTINUOUS = '0'

            if not finished:
                raise Exception('Failed to PULL the whole data with the MGT508')

            # We download the data from the MGT508, not from the ACQ, so we need to connect to that
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_address = (mgt_address, acq400_hapi.Mgt508Ports.READ)
            self.dprint(1, f'Connecting to {pull_address} to initiate READ')
            s.connect(data_address)

            # Attempt to read all the bytes into one massive buffer
            # TODO: This could use some better error handling
            buffer = bytearray(total_bytes)
            view = memoryview(buffer)

            self.dprint(1, f'Waiting for {total_bytes} bytes')

            before = datetime.now()

            while self.RUNNING.on and len(view) > 0:
                try:
                    bytes_read = s.recv_into(view)
                    view = view[ bytes_read : ]

                except socket.timeout:
                    continue

                except socket.error:
                    break
            
            after = datetime.now()
            self.dprint(1, f'Download took {after - before}s')

            # All channels share the same dimension
            begin = 0
            end = clock_period * (sample_count - 1)
            dim = MDSplus.Dimension(None, MDSplus.Range(begin, end, clock_period))

            # The ACQ482 has 14-bit accuracy, but thankfully they get padded up to 16-bit/2-bytes
            # per sample before transmission. We then unpack and reshape the buffer into data[channel][sample]
            data = numpy.frombuffer(buffer, dtype='int16')
            data = data.reshape((sample_count, channel_count,))

            # We need follow the channel mapping in order to get the correct data for each channel
            # otherwise we might write the data for channel 5 into INPUT_03 by accident
            for chan_index in channel_mapping:
                self.dprint(1, f'Writing data for channel {chan_index + 1}')
                input_node = self.getNode(f'INPUTS:INPUT_{(chan_index + 1):02}')
                input_node.record = MDSplus.Signal(data[:, chan_index], None, dim)

            # Inform the world that we've acquired data
            event_name = str(self.EVENT_NAME.data())
            MDSplus.Event(event_name)
        
        finally:
            # Ensure that we stop the STREAM no matter what
            uut.s0.CONTINUOUS = '0'

    INIT = init