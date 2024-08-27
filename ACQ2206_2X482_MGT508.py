
import MDSplus
import threading

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
            'path': ':RUNNING',
            'type': 'numeric',
            # 'on': False,
            'options': ('no_write_model',),
        },
        {
            'path': ':FREQUENCY',
            'type': 'any',
            'value': '25M',
            'options': ('no_write_shot',),
        },
        {
            'path': ':FREQUENCY:ACTUAL',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path':':SAMPLES',
            'type':'numeric',
            'value': 125_000_000,
            'options':('no_write_shot',),
        },
        {
            'path': ':SAMPLES:ACTUAL',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path': ':TRIGGER',
            'type': 'structure',
        },
        {
            'path': ':TRIGGER:SOURCE',
            'type': 'text',
            'value': 'EXT',
            'options': ('no_write_shot',),
        },
        {
            'path': ':TRIGGER:TIMESTAMP',
            'type': 'numeric',
            'options': ('write_shot',),
        },
        {
            'path': ':TRIGGER:TIME_OF_DAY',
            'type': 'text',
            'options': ('write_shot',),
        },
        {
            'path': ':TEMPERATURE',
            'type': 'structure',
        },
        {
            'path': ':TEMPERATURE:MAINBOARD',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path': ':TEMPERATURE:SITE1',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path': ':TEMPERATURE:SITE3',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path': ':TEMPERATURE:SITEE',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path': ':TEMPERATURE:ZYNQ',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path': ':INIT_ACTION',
            'type': 'action',
            'valueExpr': "Action(Dispatch('MDSIP_SERVER','INIT',50,None),Method(None,'INIT',head))",
            'options': ('no_write_shot',)
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
        input_path = f':INPUTS:INPUT_{(i + 1):02}'
        parts.extend([
            {
                'path': input_path,
                'type': 'signal',
                'options': ('no_write_model',),
            },
            {
                'path': f'{input_path}:COEFFICIENT',
                'type': 'numeric',
                'options': ('no_write_model',),
            },
            {
                'path': f'{input_path}:OFFSET',
                'type': 'numeric',
                'options': ('no_write_model',),
            },
        ])

    class InitAndStoreThread(threading.Thread):

        def __init__(self, device):
            super().__init__()
            self.device = device

        def run(self):
            self.device.init_and_store()

    def soft_trigger(self):
        import time
        import acq400_hapi

        uut = acq400_hapi.factory(self.ACQ_ADDRESS.data())

        state = acq400_hapi.pv(uut.s0.CONTINUOUS_STATE)
        while state != 'ARM':
            print(f'Waiting for device state to be ARM, current state {state}')
            time.sleep(1)
            state = acq400_hapi.pv(uut.s0.CONTINUOUS_STATE)

        uut.s0.soft_trigger = '1'

    SOFT_TRIGGER = soft_trigger

    def abort(self):
        import acq400_hapi

        uut = acq400_hapi.factory(self.ACQ_ADDRESS.data())
        uut.s0.CONTINUOUS = '0'
        # set_abort causes issues with the 2206
        # uut.s0.set_abort = '1'

        self.RUNNING.on = False

    ABORT = abort

    def init(self):
        thread = self.InitAndStoreThread(self)
        thread.daemon = True
        thread.start()

    INIT = init

    def init_and_store(self):
        import time
        import math
        import numpy
        import socket
        import acq400_hapi
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

        # Wait for the device to be in a clean, IDLE state
        while acq400_hapi.pv(uut.s0.CONTINUOUS_STATE) != 'IDLE':
            uut.s0.CONTINUOUS = '0'
            self.dprint(1, f'WARNING: requesting {uut.uut} to stop')
            time.sleep(1)

        # Configure the aggregator to send data do the MGT? We think?
        uut.cA.aggregator = 'sites=1,2,3,4 spad=0 on'

        # Transfer the "sample size in bytes" from the ACQ to the MGT
        mgt.s0.ssb = uut.s0.ssb

        # If the trigger takes too long, then the MGT will give up on the PULL
        # in order to prevent this, we set the timeout to a huge number
        self.dprint(1, f'Setting DMA timeout to 24h')
        mgt.s0.AXIDMA_ONCE_TO_MSEC = int(60 * 60 * 24 * 1000) # 24 hours in msec

        # The channel data is not packed in the regular linear order, instead you
        # have to check the channel_mapping for the order, and then unpack the data
        channel_mapping = list(map(int, uut.s0.channel_mapping.split(',')))
        channel_count = len(channel_mapping)

        # Fetch the coefficients and offsets for each channel
        self.dprint(1, f'Fetching calibration')
        uut.fetch_all_calibration()
        for chan_index in range(1, channel_count + 1):
            coeff = float(uut.cal_eslo[chan_index])
            offset = float(uut.cal_eoff[chan_index])

            input_node = self.getNode(f'INPUTS:INPUT_{chan_index:02}')
            input_node.COEFFICIENT.record = coeff
            input_node.OFFSET.record = offset

            self.dprint(1, f'Calibration for INPUT_{chan_index:02}, coeff {coeff}, offset {offset}')

        # We need to determine the timing highway based on the trigger source
        # The two highways are d0 and d1
        trigger_source = str(self.TRIGGER.SOURCE.data()).upper()
        self.dprint(1, f'Setting trigger source to {trigger_source}')

        if trigger_source in self._TRIGGER_SOURCE_D0_OPTIONS:
            trg_dx = 'TRG:DX=d0'
            uut.s0.SIG_SRC_TRG_0 = trigger_source
        elif trigger_source in self._TRIGGER_SOURCE_D1_OPTIONS:
            trg_dx = 'TRG:DX=d1'
            uut.s0.SIG_SRC_TRG_1 = trigger_source

        role = 'master'
        frequency = str(self.FREQUENCY.data())

        # Everything after the ; should not be trusted
        current_sync_role_parts = uut.s0.sync_role.split(';')[0].split(maxsplit=3)

        # Positional Arguments
        current_role = current_sync_role_parts[0]
        current_frequency = current_sync_role_parts[1]

        # Keyword Arguments
        current_arguments = []
        if len(current_sync_role_parts) > 2:
            current_arguments = current_sync_role_parts[2].split()

        changed = (
            role != current_role or
            frequency != current_frequency or
            trg_dx not in current_arguments
        )

        # If any part of the sync_role has changed, update it
        # This takes some time, and triggers a clock retraining which takes even more time
        if changed:
            sync_role = f'{role} {frequency} {trg_dx}'
            self.dprint(1, f'Setting sync_role="{sync_role}"')
            uut.s0.sync_role = sync_role
        else:
            self.dprint(1, f'Skipping sync_role, already configured')

        # Query the actual frequency the digitizer is running at, in case our setting didn't take
        actual_frequency = int(uut.s0.SIG_CLK_MB_SET.split()[1]) # Is this a safe knob to read from?
        self.FREQUENCY.ACTUAL.record = actual_frequency
        self.dprint(1, f'Queried frequency is {actual_frequency}')

        # Determine the time between each sample in seconds
        clock_period = float(1.0 / actual_frequency)

        # The MGT508 deals in "buffers", not in "samples", so we need to convert our
        # (sample count * sample size) into bytes, and then into megabytes for some reason
        sample_count = int(self.SAMPLES.data())
        total_bytes = sample_count * channel_count * uut.data_size()
        total_mb = int(math.ceil(total_bytes / 1_000_000))

        # Record the actual number of samples that we're getting, which is possibly more than was requested
        actual_sample_count = int(((total_mb * 1_000_000) / uut.data_size()) / channel_count)
        self.SAMPLES.ACTUAL.record = actual_sample_count
        self.dprint(1, f'Queried sample count is {actual_sample_count}')

        self.dprint(1, f'Setting capture length to {total_mb}MB')
        mgt.set_capture_length(total_mb)

        try:

            # So long as the "auto soft trigger" is disabled, this will arm the device for capture
            # Note that this looks a lot like streaming, internally the ACQ is running in a streaming
            # mode, not in transient
            self.dprint(1, f'Arming')
            uut.s0.CONTINUOUS = '1'

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                pull_address = (mgt_address, acq400_hapi.Mgt508Ports.PULL)
                self.dprint(1, f'Connecting to {pull_address} to initiate PULL')
                s.connect(pull_address)

                # Set the socket timeout to 1h
                self.dprint(1, f'Setting the PULL socket timeout to 24h')
                s.settimeout(60 * 60 * 24)

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

            if not finished:
                raise Exception('Failed to PULL the whole data with the MGT508')
            
            try:
                # Record the approximate time of the trigger
                trigger_time = time.time() - (clock_period * actual_sample_count)
                self.TRIGGER.TIMESTAMP.record = trigger_time
                self.TRIGGER.TIME_OF_DAY.record = datetime.fromtimestamp(trigger_time).isoformat()

                # Stop the data capture
                uut.s0.CONTINUOUS = '0'

                # Query temperatures for debugging, done after the PULL to get the temperature under load
                sys_temp = uut.s0.SYS_TEMP
                for sensor in sys_temp.split(','):
                    name, temp = sensor.split('=')
                    temp = float(temp)

                    if name == 'mainboard':
                        self.TEMPERATURE.MAINBOARD.record = temp
                    elif name == 'SITE1':
                        self.TEMPERATURE.SITE1.record = temp
                    elif name == 'SITE3':
                        self.TEMPERATURE.SITE3.record = temp
                    elif name == 'SITEE':
                        self.TEMPERATURE.SITEE.record = temp
                    elif name == 'ZYNQ':
                        self.TEMPERATURE.ZYNQ.record = temp

            except Exception as e:
                # Don't let any errors here cause issues with the actual data collection
                print(e)

            # We download the data from the MGT508, not from the ACQ, so we need to connect to that
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
            end = clock_period * (actual_sample_count - 1)
            dim = MDSplus.Dimension(None, MDSplus.Range(begin, end, clock_period))

            # The ACQ482 has 14-bit accuracy, but thankfully they get padded up to 16-bit/2-bytes
            # per sample before transmission. We then unpack and reshape the buffer into data[channel][sample]
            data = numpy.frombuffer(buffer, dtype='int16')
            data = data.reshape((actual_sample_count, channel_count,))

            # We need follow the channel mapping in order to get the correct data for each channel
            # otherwise we might write the data for channel 5 into INPUT_03 by accident
            for index, chan_index in enumerate(channel_mapping):
                input_node = self.getNode(f'INPUTS:INPUT_{(chan_index + 1):02}')
                if input_node.on:
                    self.dprint(1, f'Writing data for channel {chan_index + 1}')
                    input_node.record = MDSplus.Signal(
                        MDSplus.ADD(
                            MDSplus.MULTIPLY(
                                input_node.COEFFICIENT,
                                MDSplus.dVALUE()
                            ),
                            input_node.OFFSET
                        ),
                        data[:, index],
                        dim
                    )
                else:
                    self.dprint(1, f'Not writing data for channel {chan_index + 1}, input is off')

            # Inform the world that we've acquired data
            event_name = str(self.EVENT_NAME.data())
            MDSplus.Event(event_name)

        finally:
            # Ensure that we stop the STREAM no matter what
            self.dprint(1, f'Ensuring the device stops streaming')
            uut.s0.CONTINUOUS = '0'

    INIT_AND_STORE = init_and_store
