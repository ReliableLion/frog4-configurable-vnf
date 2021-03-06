from components.common.interface.interface_controller import InterfaceController
from components.common.interface.interface_parser import InterfaceParser
from components.common.arp_table.arpt_controller import ArpTableController
from components.common.arp_table.arpt_parser import ArpTableParser
from components.nat.nat_core.nat_core_controller import NatCoreController
from components.nat.nat_core.nat_core_parser import NatCoreParser
from components.nat.nat_table.nat_table_controller import NatTableController
from components.nat.nat_table.nat_table_parser import NatTableParser
from components.nat.floating_ip.floating_ip_controller import FloatingIpController
from components.nat.floating_ip.floating_ip_parser import FloatingIpParser
from nat.nat_parser import NatParser
import logging

class NatController():

    def __init__(self):
        self.natParser = NatParser()

        self.interfaceController = InterfaceController()
        self.interfaceParser = InterfaceParser()

        self.natCoreController = NatCoreController()
        self.natCoreParser = NatCoreParser()

        self.natTableController = NatTableController()
        self.natTableParser = NatTableParser()

        self.arpTableController = ArpTableController()
        self.arpTableParser = ArpTableParser()

        self.floatingIpController = FloatingIpController()
        self.floatingIpParser = FloatingIpParser()

    def set_configuration(self, json_configuration):

        json_interfaces = self.natParser.parse_interfaces(json_configuration)
        for json_iface in json_interfaces:
            self.configure_interface(json_iface)

        conf_nat = self.natParser.parse_nat_configuration(json_configuration)
        public_interface_id = self.natCoreParser.parse_public_interface(conf_nat)
        self.set_ip_forward(public_interface_id)
        private_interface_id = self.natCoreParser.parse_private_interface(conf_nat)

        if 'nat-table' in conf_nat:
            json_nat_table = self.natTableParser.parse_nat_table(conf_nat)
            json_nat_sessions = self.natTableParser.parse_nat_sessions(json_nat_table)
            for json_nat_session in json_nat_sessions:
                self.add_nat_session(json_nat_session)

        if 'arp-table' in conf_nat:
            json_arp_table = self.arpTableParser.parse_arp_table(conf_nat)
            json_arp_entries = self.arpTableParser.parse_arp_entries(json_arp_table)
            for json_arp_entry in json_arp_entries:
                self.add_arp_entry(json_arp_entry)

        if 'floatingIP' in conf_nat:
            json_floating_ip_list = self.floatingIpParser.parse_floating_ip_list(conf_nat)
            for curr_json_floating_ip in json_floating_ip_list:
                self.add_floating_ip(curr_json_floating_ip)
                pass


    def get_full_status(self):

        status = {}

        status["config-nat:interfaces"] = self.get_interfaces_status()
        status["config-nat:nat"] = self.get_nat_status()

        return status


    # Interfaces
    def get_interfaces_status(self):
        conf_interfaces = {}
        conf_interfaces["ifEntry"] = self.get_interfaces()
        return conf_interfaces

    # Interfaces/ifEntry
    def get_interfaces(self):
        interfaces = self.interfaceController.get_interfaces()
        interfaces_dict = []
        for interface in interfaces:
            interfaces_dict.append(self.interfaceParser.get_interface_dict(interface))
        return interfaces_dict

    def get_interface(self, name):
        interface = self.interfaceController.get_interface_by_name(name)
        if interface is None:
            raise ValueError("could not find interface: " + name)
        interface_dict = self.interfaceParser.get_interface_dict(interface)
        interface_dict = self.interfaceParser.get_interface_dict(interface)
        return interface_dict

    def configure_interface(self, json_interface):
        interface = self.interfaceParser.parse_interface(json_interface)
        if interface.type != "transparent":
            iface_found = self.interfaceController.get_interface_by_name(interface.name)
            if iface_found is not None:
                if iface_found.__eq__(interface):
                    return
            self.interfaceController.configure_interface(interface)
            logging.debug("Configured interface: " + interface.__str__())

    def update_interface(self, name, json_interface):
        interface = self.interfaceParser.parse_interface(json_interface)
        if interface.type != "transparent":
            if self.interfaceController.interface_exists(name):
                self.interfaceController.configure_interface(interface)

                logging.debug("Updated interface: " + interface.__str__())
            else:
                raise ValueError("could not find interface: " + name)

    def reset_interface(self, name):
        if not self.interfaceController.interface_exists(name):
            raise ValueError("could not find interface: " + name)
        self.interfaceController.reset_interface(name)

    def update_interface_ipv4Configuration(self, ifname, json_ipv4Configuration):
        ipv4Configuration = self.interfaceParser.parse_ipv4_configuration(json_ipv4Configuration)
        if self.interfaceController.interface_exists(ifname):
            self.interfaceController.configure_interface_ipv4Configuration(ifname, ipv4Configuration)
        else:
            raise ValueError("could not find interface: " + ifname)

    def update_interface_ipv4Configuration_address(self, ifname, address):
        if self.interfaceController.interface_exists(ifname):
            self.interfaceController.configure_interface_ipv4Configuration_address(ifname, address)
        else:
            raise ValueError("could not find interface: " + ifname)

    def update_interface_ipv4Configuration_netmask(self, ifname, netmask):
        if self.interfaceController.interface_exists(ifname):
            self.interfaceController.configure_interface_ipv4Configuration_netmask(ifname, netmask)
        else:
            raise ValueError("could not find interface: " + ifname)

    def update_interface_ipv4Configuration_default_gw(self, ifname, default_gw):
        if self.interfaceController.interface_exists(ifname):
            self.interfaceController.configure_interface_ipv4Configuration_default_gw(ifname, default_gw)
        else:
            raise ValueError("could not find interface: " + ifname)

    def get_interface_ipv4Configuration(self, name):
        if not self.interfaceController.interface_exists(name):
            raise ValueError("could not find interface: " + name)
        interface = self.interfaceController.get_interface_by_name(name)
        ipv4_configuration_dict = self.interfaceParser.get_interface_ipv4Configuration(interface.ipv4_configuration)
        return ipv4_configuration_dict

    def get_interface_ipv4Configuration_address(self, name):
        if not self.interfaceController.interface_exists(name):
            raise ValueError("could not find interface: " + name)
        interface = self.interfaceController.get_interface_by_name(name)
        return interface.ipv4_configuration.address

    def get_interface_ipv4Configuration_netmask(self, name):
        if not self.interfaceController.interface_exists(name):
            raise ValueError("could not find interface: " + name)
        interface = self.interfaceController.get_interface_by_name(name)
        return interface.ipv4_configuration.netmask

    def get_interface_ipv4Configuration_default_gw(self, name):
        if not self.interfaceController.interface_exists(name):
            raise ValueError("could not find interface: " + name)
        interface = self.interfaceController.get_interface_by_name(name)
        return interface.ipv4_configuration.default_gw

    def get_interface_ipv4Configuration_mac_address(self, name):
        if not self.interfaceController.interface_exists(name):
            raise ValueError("could not find interface: " + name)
        interface = self.interfaceController.get_interface_by_name(name)
        return interface.ipv4_configuration.mac_address


    # Nat
    def get_nat_status(self):
        nat = {}
        nat['private-interface'] = self.get_private_interface_id()
        nat['public-interface'] = self.get_public_interface_id()
        nat['nat-table'] = self.get_nat_table()
        nat['arp-table'] = self.get_arp_table()
        nat['floatingIP'] = self.get_all_floating_ip()
        return nat

    # Nat/Wan-interface
    def set_ip_forward(self, public_interface_id):
        current_public_iface_name = self.natCoreController.get_public_interface_name()
        if current_public_iface_name is None:
            public_iface = self.interfaceController.get_interface_by_id(public_interface_id)
            self.natCoreController.set_ip_forward(public_iface.name)
            logging.debug("Nat set on wan interface: " + public_iface.name)

    def unset_ip_forward(self, public_interface_id):
        current_public_iface_name = self.natCoreController.get_public_interface_name()
        if current_public_iface_name is not None:
            public_iface = self.interfaceController.get_interface_by_id(public_interface_id)
            self.natCoreController.unset_ip_forward(public_iface.name)
            logging.debug("Nat unset")

    def get_public_interface_id(self):
        public_iface_name = self.natCoreController.get_public_interface_name()
        public_iface = self.interfaceController.get_interface_by_name(public_iface_name)
        return public_iface.id

    def get_private_interface_id(self):
        public_iface_name = self.natCoreController.get_public_interface_name()
        interfaces = self.interfaceController.get_interfaces()
        for interface in interfaces:
            if interface.management == False:
                if interface.name != public_iface_name:
                    return interface.id

    # Nat/nat-table
    def get_nat_table(self):
        nat_table = {}
        nat_table['nat-session'] = self.get_nat_session()
        return nat_table

    def get_nat_session(self):
        nat_table = self.natTableController.get_nat_table()
        nat_table_dict = []
        for nat_session in nat_table:
            nat_table_dict.append(self.natTableParser.get_nat_session_dict(nat_session))
        return nat_table_dict

    def add_nat_session(self, json_nat_session):
        # not supported
        nat_session = self.natTableParser.parse_nat_session(json_nat_session)
        self.natTableController.add_nat_session(nat_session)
        #logging.debug("Added nat_session: " + nat_session.__str__())

    # Nat/arp-table
    def get_arp_table(self):
        arp_table = {}
        arp_table['arp-entry'] = self.get_arp_entry()
        return arp_table

    def get_arp_entry(self):
        arp_table = self.arpTableController.get_arp_table()
        arp_table_dict = []
        for arp_entry in arp_table:
            arp_table_dict.append(self.arpTableParser.get_arp_entry_dict(arp_entry))
        return arp_table_dict

    def add_arp_entry(self, json_arp_entry):
        arp_entry = self.arpTableParser.parse_arp_entry(json_arp_entry)
        self.arpTableController.add_arp_entry(arp_entry.ip_address, arp_entry.mac_address)
        logging.debug("Added arp_entry: " + arp_entry.__str__())

    def delete_arp_entry(self, ip_address):
        if self.arpTableController.arp_entry_exists(ip_address):
            self.arpTableController.delete_arp_entry(ip_address)
            logging.debug("Removed arp_entry with ip_address: " + ip_address)
        else:
            raise ValueError("There is no entry in arp table with ip_address: " + ip_address)

    def get_arp_table_mac_address(self, ip_address):
        return self.arpTableController.get_mac_address(ip_address)

    def update_arp_table_mac_address(self, ip_address, mac_address):
        if self.arpTableController.arp_entry_exists(ip_address):
            self.arpTableController.add_arp_entry(ip_address, mac_address)
            logging.debug("Updated arp_entry, ip_address: " + ip_address + " mac_address: " + mac_address)
        else:
            raise ValueError("There is no entry in arp table with ip_address: " + ip_address)


    # Nat/StaticBindings
    def add_floating_ip(self, json_floating_ip):
        floating_ip = self.floatingIpParser.parse_floating_ip(json_floating_ip)
        floating_ip_list = self.floatingIpController.get_all_floating_ip()
        for curr_floating_ip in floating_ip_list:
            if curr_floating_ip.__eq__(floating_ip):
                return
        wan_interface = self.natCoreController.get_public_interface_name()
        self.floatingIpController.configure_floating_ip(floating_ip, wan_interface)
        logging.debug("floating_ip set: private address " + floating_ip.private_address + " => public address" + floating_ip.public_address)

    def update_floating_ip(self, public_address, json_floating_ip):
        pass

    def update_floating_ip_private_address(self, public_address, private_address):
        pass

    def update_floating_ip_public_address(self, public_address, private_address):
        pass

    def delete_floating_ip(self, public_address):
        if self.floatingIpController.floating_ip_exists(public_address):
            self.floatingIpController.delete_floating_ip(public_address)
        else:
            raise ValueError("could not find a floating_ip with public address " + public_address)

    def get_all_floating_ip(self):
        floating_ip_list = self.floatingIpController.get_all_floating_ip()
        floating_ip_dict = []
        for floating_ip in floating_ip_list:
            floating_ip_dict.append(self.floatingIpParser.get_floating_ip_dict(floating_ip))
        return floating_ip_dict

    def get_floating_ip(self, public_address):
        floating_ip = self.floatingIpController.get_floating_ip(public_address)
        if floating_ip is None:
            raise ValueError("could not find a floating_ip with public address " + public_address)
        floating_ip_dict = self.floatingIpParser.get_floating_ip_dict(floating_ip)
        return floating_ip_dict

    def get_floating_ip_private_address(self, public_address):
        floating_ip_list = self.floatingIpController.get_all_floating_ip()
        for floating_ip in floating_ip_list:
            if floating_ip.public_address == public_address:
                return floating_ip.private_address
        raise ValueError("could not find a floating_ip with public address " + public_address)

    def get_floating_ip_public_address(self, public_address):
        floating_ip_list = self.floatingIpController.get_all_floating_ip()
        for floating_ip in floating_ip_list:
            if floating_ip.public_address == public_address:
                return floating_ip.public_address
        raise ValueError("could not find a floating_ip with public address " + public_address)
