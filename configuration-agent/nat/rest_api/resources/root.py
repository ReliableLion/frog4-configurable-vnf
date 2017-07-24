from flask import request, Response
from flask_restplus import Resource
import json
import logging

from nat.nat_controller import NatController
from nat.rest_api.api import api

nat_root_ns = api.namespace('', 'Nat Root Resource')

@nat_root_ns.route('/', methods=['GET','PUT'])
class Nat(Resource):
    @nat_root_ns.response(200, 'Nat status retrieved.')
    @nat_root_ns.response(500, 'Internal Error.')
    def get(self):
        """
        Gets the status of the nat
        """
        try:
            natController = NatController()
            json_data = json.dumps(natController.get_full_status())
            resp = Response(json_data, status=200, mimetype="application/json")
            return resp

        except Exception as err:
            logging.debug(err)
            return Response(status=500)

    @nat_root_ns.param("Nat Configuration", "Nat Configuration to update", "body", type="string", required=True)
    @nat_root_ns.response(202, 'Nat configuration updated.')
    @nat_root_ns.response(400, 'Bad request.')
    @nat_root_ns.response(500, 'Internal Error.')
    def put(self):
        """
        Update the nat configuration
        """
        try:
            natController = NatController()
            json_data = json.loads(request.data.decode())
            natController.set_configuration(json_data)
            return Response(status=202)

        except Exception as err:
            logging.debug(err)
            return Response(status=500)