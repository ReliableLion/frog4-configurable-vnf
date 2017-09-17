from idstools import unified2
from components.ids.ids_parser import IdsParser

class AttacksMonitor():

    def __init__(self, dd_controller):

        self.url_attackDected = "config-ids:ids/attack_detected"

        self.attack_map = {}
        self.attack_map['1000006'] = "port_scan"

        self.reader = unified2.SpoolRecordReader("/var/log/snort", "AAAsnort.log", follow=True)

        self.ddController = dd_controller
        self.idsParser = IdsParser()

    def start_monitoring(self):
        for record in self.reader:
            if isinstance(record, unified2.Event):
                if str(record['signature-id']) in self.attack_map:
                    attack_name = self.attack_map[str(record['signature-id'])]
                    src_ip = record['source-ip']
                    dst_ip = record['destination-ip']
                    attackDetected_dict = self.idsParser.get_attack_detected_dict(attack_name, src_ip, dst_ip)
                    self.ddController.publish_on_bus(self.url_attackDected, 'ADD', attackDetected_dict)
