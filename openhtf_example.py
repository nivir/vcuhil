import openhtf as htf
from openhtf.output.callbacks import console_summary, json_factory
from openhtf.util import conf

@htf.measures(htf.Measurement("vcu_current").doc("Supply Current").in_range(0.1, 0.2))
def analog_read(test):
    test.measurements.vcu_current = 0

class SupplyPlug(htf.plugs.BasePlug):
    @conf.inject_positional_args
    def __init__(self, supply_hostname, supply_port):
        super.__init__()
        #self._supply =

test = htf.Test(analog_read)
test.add_output_callbacks(
    json_factory.OutputToJSON(
        './SampleJSON.{start_time_millis}.json', indent=4
    )
)
test.add_output_callbacks(console_summary.ConsoleSummary())
test.execute()