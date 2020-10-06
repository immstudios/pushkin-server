#!/usr/bin/env python3

import os
import json
import sanic
import socket
import logging
import aiofiles
import http.client

config = {
    "listen_address" : "0.0.0.0",
    "listen_port" : "9800",
    "hostname" : socket.gethostname(),
    "upload_dir" : "/mnt/cache",
    "debug" : False,
    "source_whitelist" : []
}


if os.path.exists("settings.json"):
    try:
        config.update(json.load(open("settings.json")))
    except:
        print("Unable to open settings file")


class LogFilter(logging.Filter):
    def filter(self, record):
        return False
        return not (record.request.endswith("/stat") and record.status == 200)

sanic.log.access_logger.addFilter(LogFilter())


def response(code=200, message=None, **kwargs):
    if message is None:
        message = http.client.responses[code]
    if code >= 400:
        sanic.log.logger.error(message)
    return sanic.response.json({
                "response" : code,
                "message" : message,
                **kwargs
            },
        status=code,
        )

APP_NAME = "Pushkin server"

app = sanic.Sanic(APP_NAME)
metrics_data = {
    "uploaded_files" : 0,
    "uploaded_bytes" : 0
}

@app.exception(sanic.exceptions.SanicException)
async def exception_handler(request, exception):
    status_code = exception.status_code
    return response(status_code, client=request.ip)


@app.route("/", methods=["POST"])
async def default(request):
    whitelist = config.get("source_whitelist", None)
    if whitelist and type(whitelist) == list:
        if not request.ip in whitelist:
            return response(401, "Unauthorized source IP", client=request.ip)

    push_fname = request.headers.get("X-Pushkin-Filename", None)
    push_dir  = request.headers.get("X-Pushkin-Directory", "upload")

    if not push_fname:
        return response(400, "Filename is not specified", client=request.ip)

    if push_fname.find("/") > -1 or push_dir.find("/") > -1:
        return response(400, "Slashes are not permitted in path", client=request.ip)

    target_path = os.path.join(
            config["upload_dir"],
            push_dir,
            push_fname
        )

    target_dir = os.path.split(target_path)[0]
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    async with aiofiles.open(target_path, 'wb') as f:
        await f.write(request.body)

    metrics_data["uploaded_files"] += 1
    metrics_data["uploaded_bytes"] += len(request.body)
    return response(201, "File created")

@app.route("/metrics")
async def metrics(request):
    prom = ""
    for m in metrics_data:
        prom += "pushkin_{}{{hostname=\"{}\"}} {}\n".format(
            m, config["hostname"], metrics_data[m]
        )
    return sanic.response.text(prom)

if __name__ == "__main__":
    app.run(
            host=config["listen_address"],
            port=config["listen_port"],
            auto_reload=config["debug"]
        )
