"""
Flask view for RMQ IN blueprint
Path: /
"""

from typing import Union

from flask import Response, make_response, request, session
from ftl_msa_rmq_in.msa.blueprints import BLUEPRINT_RMQ_IN
from ftl_python_lib.core.context.environment import EnvironmentContext
from ftl_python_lib.core.context.request import (REQUEST_CONTEXT_SESSION,
                                                 RequestContext)
from ftl_python_lib.core.exceptions.client_invalid_request_exception import \
    ExceptionInvalidRequest
from ftl_python_lib.core.exceptions.client_resource_not_found_exception import \
    ExceptionResourceNotFound
from ftl_python_lib.core.exceptions.server_unexpected_error_exception import \
    ExceptionUnexpectedError
from ftl_python_lib.core.log import LOGGER
from ftl_python_lib.core.microservices.api.mapping import (
    MicroserviceApiMapping, MircoserviceApiMappingResponse)
from ftl_python_lib.core.providers.clients.rabbitmq.rabbitmq import Rabbitmq
from ftl_python_lib.typings.iso20022.received_message import \
    TypeReceivedMessage


# pylint: disable=R0915
# too-many-statements
@BLUEPRINT_RMQ_IN.route("", methods=["POST"])
def post() -> Response:
    """
    Process POST request for the /msa/rmq/in endpoint
    Send new transaction
    """

    request_context: RequestContext = session.get(REQUEST_CONTEXT_SESSION)
    environ_context: EnvironmentContext = EnvironmentContext()

    LOGGER.logger.debug("Proccessing POST request for RMQ IN microservice")
    LOGGER.logger.debug(f"Request ID is {request_context.request_id}")

    # Raw message
    message_raw: Union[bytes, str] = request.data

    try:
        if len(message_raw) == 0 or message_raw is None:
            LOGGER.logger.error("Missing message body")
            raise ExceptionInvalidRequest(
                message="Missing message body", request_context=request_context
            )

        LOGGER.logger.warning(
            "Transaction Queue is present in headers. Request context will contain transaction Queue value."
        )

        rabbitmq: Rabbitmq = Rabbitmq(
            rabbitmq_username=environ_context.rabbitmq_username,
            rabbitmq_password=environ_context.rabbitmq_password,
            rabbitmq_endpoint=environ_context.rabbitmq_endpoint,
            rabbitmq_port=environ_context.rabbitmq_port
        )

        rabbitmq_connection = rabbitmq.connection()
        LOGGER.logger.debug("Rabbitmq connection is opened")

        rabbitmq_main_channel = rabbitmq_connection.channel()

        mapping: MicroserviceApiMapping = MicroserviceApiMapping(
            request_context=request_context, environ_context=environ_context
        )

        incoming: TypeReceivedMessage = TypeReceivedMessage(
            request_context=request_context,
            environ_context=environ_context,
            message_raw=request.data,
            content_type=request_context.headers_context.content_type,
        )

        try:
            incoming.fill_message_xml()
            incoming.fill_message_proc()
            incoming.fill_message_type()
        except ValueError as exception:
            LOGGER.logger.error(exception)
            raise ExceptionInvalidRequest(
                message="Received an invalid incoming message",
                request_context=request_context,
            ) from exception

        mapping_response: MircoserviceApiMappingResponse = mapping.get(
            params={
                "source": "ftl-msa-rmq-in",
                "message_type": incoming.message_type,
                "content_type": request.headers.get("Content-Type")
            }
        )

        for mapping_item in mapping_response.data:
            target: str = mapping_item.target

            properties = rabbitmq.get_properties(
                'ftl-client',
                request.headers.get("Content-Type"),
                target
            )

            rabbitmq.push_message(
                rabbitmq_main_channel,
                message_raw,
                properties,
                target.replace('queue-', 'exchange-'),
                target,
            )
            LOGGER.logger.debug(f"Put message to {target}")

        rabbitmq_connection.close()
        LOGGER.logger.debug("Rabbitmq connection is closed")

        return make_response(
            {
                "request_id": request_context.request_id,
                "status": "OK",
                "message": "Request was received",
            },
            200,
        )
    except (ExceptionInvalidRequest, ExceptionResourceNotFound) as error:
        LOGGER.logger.error(error)
        raise error
    except Exception as err:
        LOGGER.logger.error(err)
        raise ExceptionUnexpectedError(
            message=f"Unexpected server error: {str(err)}",
            request_context=request_context,
        ) from err
