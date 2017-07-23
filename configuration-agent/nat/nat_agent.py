from common.agent import ConfigurationAgent
from common.utils import check_validity_initial_params
from nat.nat_monitor import NatMonitor

import sys
import logging

class NatAgent():

    def __init__(self, nf_type, datadisk_path, on_change_interval=None):

        logging.debug("Nat agent started...")

        configurationAgent = ConfigurationAgent("nat", nf_type, datadisk_path, on_change_interval)

        configurationAgent.start_monitoring(NatMonitor)

        configurationAgent.start_rest_controller("nat.rest_api.nat_rest_start")


if __name__ == "__main__":
        res = check_validity_initial_params(sys.argv)
        if type(res) != str:
            nf_type = res[0]
            datadisk_path = res[1]
            on_change_interval = res[2]
            NatAgent(nf_type, datadisk_path, on_change_interval)
        else:
            error = res
            print(error)