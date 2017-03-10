#!/usr/bin/python3
# -*- coding: utf-8 -*-

from doubledecker import clientSafe
from configuration_agent import utils

from vnf_template_library.exception import TemplateValidationError
from vnf_template_library.template import Template
from vnf_template_library.validator import ValidateTemplate

from threading import Event
from threading import Thread
import logging
import json
import time
import os
import sys
import shutil


class ConfigurationAgent(clientSafe.ClientSafe):
    """
    Configuration agent, this class is in charge to 
    talk with the configuration server to provide
    the configuration to a VNF.
    """

    def __init__(self, vnf):
        self.tenant_id = None
        self.vnf_name = None
        self.vnf_id = None
        '''
        the VNF has to start publishing a status only after receiving a configuration. Otherwise the VNF would export a potentially incoherent state
        because you can't know which state the VNF has when it starts
        '''
        self.publishable = False
        '''
        last_published_status: you have to publish a status ONLY if the state is actually changed in respect of the last one published.
        In order to do this you have to compare the last published status with the one you want to publish
        '''
        self.last_published_status = None
        '''
        is_registered_to_cs is a flag notifying if the agent is already registered to the configuration service
        Only after such a registration the agent can start exporting its status
        Registered_to_cs is a condition variable which awakes when the registration with the cs is successfull
        '''
        self.is_registered_to_cs = False
        self.registered_to_cs = Event()
        '''
        is_registered_to_dd is a flag notifying if the agent is already registered to the message broker
        Only after such a registration the agent can ask for the configuration service registration
        registered_to_dd is a condition variable which awakes when the registration with the broker is successfull
        '''
        self.is_registered_to_dd = False
        self.registered_to_dd = Event()

        '''
        datadisk_path contains the path where an external volume is attached to the VNF.
        Inside such a module you can find a metadata file containing some information about the VNF
        The datadisk contains:
        - tenant private and public keys
        - broker public key
        - key of the DD public tenant
        - template of the VNF
        - a metadata file
        - an initial configuration the VNF has tu use at bootstrap (optional)
        '''
        self.datadisk_path = "/datadisk"
        self.metadata_file = self.datadisk_path + "/metadata"
        self.tenant_keys_file = self.datadisk_path + "/tenant-keys.json"
        self.public_keys_file = self.datadisk_path + "/public-keys.json"
        self.template = self.datadisk_path + "/template.json"
        self.broker_url = None
        self.initial_configuration_path = self.datadisk_path + "/initial_configuration.json"

        self.configuration_interface = None

        assert os.path.isdir(self.datadisk_path) is True, "datadisk not mounted onto the VNF"
        assert os.path.exists(self.metadata_file) is True, "metadata file not found in datadisk"
        assert os.path.exists(self.template), "Error, VNF template not found in datadisk"
        self.read_data_disk(self.metadata_file)
        self.configuration_interface = self.get_iface_from_template()
        self.vnf = vnf(self.configuration_interface)
        if os.path.exists(self.initial_configuration_path):
            with open(self.initial_configuration_path) as configuration:
                initial_configuration = configuration.read()
            self.publishable = True
            self.configure_vnf(initial_configuration)

        self.start_agent()

    def read_data_disk(self, ds_metadata):
        """
        It reads the volume attached to the VNF (datadisk) and looks for the information the VNF needs
        It excpects to find a metadata file describing the VNF's name, ID and tenant ID
        :param ds_metadata:
        :return:
        """
        try:
            metadata = open(ds_metadata, "r")
            for line in metadata.readlines():
                words = "".join(line.split()).split('=')
                if words[0] == "tenant-id":
                    self.tenant_id = words[1]
                elif words[0] == "broker-url":
                    self.broker_url = words[1]
                elif words[0] == "vnf-name":
                    self.vnf_name = words[1]
                elif words[0] == "vnf-id":
                    self.vnf_id = words[1]
                else:
                    logging.debug("unknown keyword in metadata: " + words[0])
        except Exception as e:
            logging.debug("Error during metadata reading.\n" + str(e))
            sys.exit(1)
        finally:
            if metadata is not None:
                metadata.close()

        assert self.tenant_id is not None, "tenant-id key not found in metedata file"
        assert self.vnf_name is not None, "vnf-name key not found in metedata file"
        assert self.vnf_id is not None, "vnf-id key not found in metedata file"
        assert self.broker_url is not None, "broker-url key not found in metedata file"
        assert os.path.exists(self.public_keys_file) is True, "public_keys.json file not found in datadisk"
        assert os.path.exists(self.tenant_keys_file) is True, "tenant_keys.json file not found in datadisk"
        assert os.path.exists(self.template) is True, "template (" + self.template + ") not found in datadisk"
        assert os.path.exists(self.template) is True, "template (" + self.template + ") not found in datadisk"
        if os.path.isdir("/etc/doubledecker") is False:
            os.makedirs("/etc/doubledecker")
        if os.path.exists("/etc/doubledecker/" + self.tenant_id + "-keys.json") is False:
            shutil.copy(self.tenant_keys_file, "/etc/doubledecker/" + self.tenant_id + "-keys.json")
        if os.path.exists("/etc/doubledecker/public-keys.json") is False:
            shutil.copy(self.public_keys_file, "/etc/doubledecker/public-keys.json")

    def registration(self, name, dealerurl, customer, keyfile):
        super().__init__(name=name.encode('utf8'), 
                         dealerurl=dealerurl, 
                         customer=customer.encode('utf8'),
                         keyfile=keyfile)
        thread = Thread(target=self.start)
        thread.start()
        return thread

    def start_agent(self):
        """
        Agent core method. It manages the registrion both to the message broker and to the configuration service
        :return:
        """
        self.registered_to_dd.clear()
        self.registered_to_cs.clear()

        assert self.vnf.mac_address is not None, "Mac address is undefined"
        logging.debug("Registering to the message broker")
        thread = self.registration(name=self.vnf.mac_address,
                                   dealerurl=self.broker_url,
                                   customer=self.tenant_id,
                                   keyfile="/etc/doubledecker/" + self.tenant_id + "-keys.json")

        while self.is_registered_to_dd is False:  # waiting for the agent to be registered to DD broker
            self.registered_to_dd.wait()
        while self.is_registered_to_cs is False:  # waiting for the agent to be registered to the configuration service
            logging.debug("Waiting for registration...")
            if not self.registered_to_cs.wait(5):
                if self.is_registered_to_cs is False:
                    self.vnf_registration()
        logging.debug("Registration successful")
        while True:
            # Export the status every 3 seconds
            time.sleep(3)
            self.publish_status()
        thread.join()

    def publish_status(self):
        if self.publishable:
            if self.last_published_status != self.vnf.get_status():
                logging.debug("Publishing a new status")
                logging.debug("NEW STATUS: " + self.vnf.get_status())
                self.publish_public('public.status_exportation', self.vnf.get_status())
                self.last_published_status = self.vnf.get_status()
        
    def config(self, name, dealerURL, customer):
        super().config(name, dealerURL, customer)

    def on_data(self, dest, msg):
        msg = msg.decode()
        logging.debug("msg received: " + msg + " expected " + "REGISTERED " + self.tenant_id + '.' + self.vnf_id)
        if msg == "REGISTERED " + self.tenant_id + '.' + self.vnf_id:
            self.is_registered_to_cs = True
            self.registered_to_cs.set()
            return

        if not self.publishable:
            self.publishable = True
        logging.debug('configuring json: '+msg)
        self.configure_vnf(msg)
        # Export again the status
        self.publish_status()

    def configure_vnf(self, configuration):
        # Validate json
        exit_code, output = utils.validate_json(configuration, self.vnf.yang_model)
        if exit_code is not None:
            raise Exception("Wrong configuration file: " + output)
        else:
            logging.debug("Good validation!")

        # Configure VNF
        self.vnf.set_configuration(json.loads(configuration))

    def on_discon(self):
        pass
        
    def on_pub(self):
        pass
        
    def on_reg(self):
        self.is_registered_to_dd = True
        self.registered_to_dd.set()
        self.vnf_registration()

    def vnf_registration(self):
        msg = ""
        msg += "vnf-id:" + self.vnf_id + "\n"
        msg += "vnf-name:" + self.vnf_name + "\n"
        msg += "tenant-id:" + self.tenant_id
        logging.debug('Registering to the configuration service: ' + msg)
        self.publish_public('public.vnf_registration', msg)

    def unsubscribe(self):
        super().unsubscribe()
    
    def start(self):
        logging.basicConfig(level=logging.DEBUG)
        super().start()
        
    def on_error(self, code, msg):
        logging.debug(str(code) + ": " + str(msg))

    def get_iface_from_template(self):
        with open(self.template) as template_data:
            tmpl = json.load(template_data)

        template = Template()
        try:
            validator = ValidateTemplate()
            validator.validate(tmpl)
            template.parseDict(tmpl)
        except TemplateValidationError as e:
            logging.debug("template parsing failed")
            exit(1)

        for port in template.ports:
            if port.label == "management":
                iface = port.name + port.position.split('-')[0]
        assert iface is not None, "Error, the template does not contain a management interface"

        return iface
