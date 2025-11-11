import base64
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends

from motra.common import util
from motra.common.capcon import write_payload_to_file
from motra.common.capcon_protocol import *
from motra.common.schedule import (
    execute_scheduler_template,
    generate_scheduler_template,
)
from motra.server.configuration import MotraServerConfig, get_server_config
from motra.server.file_upload import handle_file_payload
from motra.server.lifespan import lifespan
from motra.server import requests

logger = logging.getLogger(__name__)
app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "Server is running"}


@app.websocket("/motra")
async def websocket_endpoint(
    websocket: WebSocket, config: MotraServerConfig = Depends(get_server_config)
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message_type")
            logger.info(f"Server: < {message} ", extra={"data": data})

            # ------------------ CLIENT_HELLO ------------------
            if data.get("message_type") == "CLIENT_HELLO":

                request = requests.validate_json(CLIENT_HELLO, data)
                if request == None:
                    await websocket.close(reason="failed validation")
                    break

                response = requests.parse_SERVER_HELLO()
                logger.info(
                    f"Server: > {response.message_type} ",
                    extra={"data": response},
                )

                # when requesting a new connection, we should clean all old stuff
                # ... we need some state
                if config.jobs_active:
                    job_id, job_file = config.pop_from_active_jobslist()

                    # TODO do some archiving step ...
                    # currently we are not interested in the server side data
                    # so we ignore it; can always check the logs

                    logger.info(f"removing old job {job_id}")
                    job_file.unlink()

                # remove all old systemd configurations
                config.schedule_units.clear()

                await websocket.send_json(util.serialize(response))

            # ------------------ REQUEST_UPLOAD ------------------
            elif data.get("message_type") == "REQUEST_UPLOAD":

                request = requests.validate_json(REQUEST_UPLOAD, data)
                if request == None:
                    await websocket.close(reason="failed validation")
                    break

                # use the base64 stream to create a file on disk
                handle_file_payload(
                    request=request,
                    workspace=config.archive_data,
                )

                response = requests.parse_UPLOAD_COMPLETE(request)
                logger.info(
                    f"Server: > {response.message_type} ",
                    extra={"data": response},
                )
                await websocket.send_json(util.serialize(response))

            # ------------------ REQUEST_CAPCON ------------------
            elif data.get("message_type") == "REQUEST_CAPCON":

                request = requests.validate_json(REQUEST_CAPCON, data)
                if request == None:
                    await websocket.close(reason="failed validation")
                    break

                pending_capcon = config.get_pending_test()
                response = requests.parse_CAPCON(pending_capcon)
                logger.info(
                    f"Server: > {response.message_type} <{response.CapConID}>",
                    extra={"data": response},
                )

                # store the configurations locally
                # the server needs to schedule a new run for the payloads,
                # also cleaning now gets an issue
                # handle_response_payload(...)
                active_payloads: list[GenericPayload] = list()
                if response.payload:

                    for payload in response.payload:
                        if "server" in payload.target:
                            # add the current id to our joblist
                            pid = payload.payload_id
                            active_payloads.append(payload)
                            current_job = config.live_data / f"{pid}.json"
                            config.add_to_active_jobslist(pid, current_job)
                            write_payload_to_file(current_job, payload=payload)

                if active_payloads:
                    for payload in active_payloads:
                        payload_unit = generate_scheduler_template(
                            "motra-server-mexec",
                            current_id=payload.payload_id,
                            start_time_delta="3s",
                            template_unit=True,
                        )
                        config.schedule_units.append(payload_unit)

                await websocket.send_json(util.serialize(response))
                config.pop_test()

            # ------------------ ACK_CAPCON ------------------
            elif data.get("message_type") == "ACK_CAPCON":

                request = requests.validate_json(ACK_CAPCON, data)
                if request == None:
                    await websocket.close(reason="failed validation")
                    break

                response = requests.parse_EXECUTE_CAPCON(request.CapConID)
                logger.info(
                    f"Server: > {response.message_type} ",
                    extra={"data": response},
                )
                await websocket.send_json(util.serialize(response))

                # do scheduled stuff...
                for command in config.schedule_units:
                    execute_scheduler_template(command)

                # remove all old systemd configurations for the next rus
                config.schedule_units.clear()

                await websocket.close()
                logger.info("Server: Sent EXECUTE and closed connection. ")
                break  # Exit the loop

            # ------------------ INVALID_DATA ------------------
            else:
                # for some reason we got a frame, we cannot parse
                logger.error("Got invalid data from Client.", extra={"data": data})
                await websocket.send_json({"message_type": "INVALID_DATA"})
                await websocket.close()

    except WebSocketDisconnect as e:
        logger.info(
            f"Client disconnected. Details: <{e.code}; {e.reason}> ",
        )
    # except TypeError as e:
    #     logger.error(
    #         "Failed to validate message from Client.. ",
    #         exc_info=1,
    #     )


def run(
    reload: bool,
    loglevel,
    port: int = 12400,
    host: str = "0.0.0.0",
):
    uvicorn.run(app, host=host, port=port, reload=reload, log_level=loglevel)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=12400, reload=True)
