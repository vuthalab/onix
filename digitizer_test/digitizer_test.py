import PyGage
import onix.headers.pcie_digitizer.GageSupport as gs
import onix.headers.pcie_digitizer.GageConstants as gc
import time
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer


def initialize() -> int:
    status = PyGage.Initialize()
    if status < 0:
        raise Exception(f"Initialize failed with status {status}")
    else:
        handle = PyGage.GetSystem(0, 0, 0, 0)
        if handle < 0:
            raise Exception(f"GetSystem failed with code {handle}")
        return handle


def get_system_info(handle: int) -> dict:
    system_info = PyGage.GetSystemInfo(handle)
    return system_info


def configure_system(handle: int, filename: str):
    acq, sts = gs.LoadAcquisitionConfiguration(handle, filename)

    if isinstance(acq, dict) and acq:
        status = PyGage.SetAcquisitionConfig(handle, acq)
        if status < 0:
            return status
    else:
        print("Using defaults for acquisition parameters")

    if sts == gs.INI_FILE_MISSING:
        print("Missing ini file, using defaults")
    elif sts == gs.PARAMETERS_MISSING:
        print("One or more acquisition parameters missing, using defaults for missing values")

    system_info = PyGage.GetSystemInfo(handle)
    acq = PyGage.GetAcquisitionConfig(handle) # check for error - copy to GageAcquire.py

    channel_increment = gs.CalculateChannelIndexIncrement(acq['Mode'],
                                                          system_info['ChannelCount'],
                                                          system_info['BoardCount'])

    missing_parameters = False
    for i in range(1, system_info['ChannelCount'] + 1, channel_increment):
        chan, sts = gs.LoadChannelConfiguration(handle, i, filename)
        if isinstance(chan, dict) and chan:
            status = PyGage.SetChannelConfig(handle, i, chan)
            if status < 0:
                return status
        else:
            print("Using default parameters for channel ", i)

        if sts == gs.PARAMETERS_MISSING:
            missing_parameters = True

    if missing_parameters:
        print("One or more channel parameters missing, using defaults for missing values")

    missing_parameters = False
    # in this example we're only using 1 trigger source, if we use
    # system_info['TriggerMachineCount'] we'll get warnings about
    # using default values for the trigger engines that aren't in
    # the ini file
    trigger_count = 1
    for i in range(1, trigger_count + 1):
        trig, sts = gs.LoadTriggerConfiguration(handle, i, filename)
        if isinstance(trig, dict) and trig:
            status = PyGage.SetTriggerConfig(handle, i, trig)
            if status < 0:
                return status
        else:
            print("Using default parameters for trigger ", i)

        if sts == gs.PARAMETERS_MISSING:
            missing_parameters = True

    if missing_parameters:
        print("One or more trigger parameters missing, using defaults for missing values")

    status = PyGage.Commit(handle)
    return status


def get_data(handle: int, system_info: dict):
    status = PyGage.StartCapture(handle)
    if status < 0:
        return status

    status = PyGage.GetStatus(handle)
    while status != gc.ACQ_STATUS_READY:
        status = PyGage.GetStatus(handle)

    acq = PyGage.GetAcquisitionConfig(handle)
    channel_increment = gs.CalculateChannelIndexIncrement(acq['Mode'],
                                                          system_info['ChannelCount'],
                                                          system_info['BoardCount'])

    # These fields are common for all the channels

    # Validate the start address and the length. This is especially
    # necessary if trigger delay is being used.

    min_start_address = acq['TriggerDelay'] + acq['Depth'] - acq['SegmentSize']
    if app['StartPosition'] < min_start_address:
        print("\nInvalid Start Address was changed from {0} to {1}".format(app['StartPosition'],  min_start_address))
        app['StartPosition'] = min_start_address

    max_length = acq['TriggerDelay'] + acq['Depth'] - min_start_address
    if app['TransferLength'] > max_length:
        print("\nInvalid Transfer Length was changed from {0} to {1}".format(app['TransferLength'], max_length))
        app['TransferLength'] = max_length


    stHeader = {}
    if acq['ExtClk']:
        stHeader['SampleRate'] = acq['SampleRate'] / (acq['ExtClkSampleSkip'] * 1000)
    else:
        stHeader['SampleRate'] = acq['SampleRate']

    stHeader['Start'] = app['StartPosition']
    stHeader['Length'] = app['TransferLength']
    stHeader['SampleSize'] = acq['SampleSize']
    stHeader['SampleOffset'] = acq['SampleOffset']
    stHeader['SampleRes'] = acq['SampleResolution']
    stHeader['SegmentNumber'] = 1    # this example only does singe capture
    stHeader['SampleBits'] = acq['SampleBits']

    if app['SaveFileFormat'] == gs.TYPE_SIG:
        stHeader['SegmentCount'] = 1
    else:
        stHeader['SegmentCount'] = acq['SegmentCount']

    for i in range(1, system_info['ChannelCount'] + 1, channel_increment):
        buffer = PyGage.TransferData(handle, i, 0, 1, app['StartPosition'], app['TransferLength'])
        print(type(buffer[0][0]), len(buffer[0]) * 4)

    return status



if __name__ == "__main__":
    use_header = True

    if not use_header:
        config_file = "/home/onix/Documents/code/onix/digitizer_test/Acquire.ini"
        app, sts = gs.LoadApplicationConfiguration(config_file)
        handle = initialize()
        for kk in range(15):
            print(kk)
            system_info = get_system_info(handle)
            configure_system(handle, config_file)
            get_data(handle, system_info)
    else:
        dg = Digitizer()
        dg.set_acquisition_config(num_channels=1, sample_rate=1e8, segment_size=8120, segment_count=1)
        dg.set_channel_config(channel=1, range=0.1)
        dg.set_trigger_source_software()
        dg.write_configs_to_device()

        for kk in range(50):
            print(kk)
            dg.start_capture()
            dg.wait_for_data_ready()
            data_sample_rate, data = dg.get_data()
            print(data.shape)
