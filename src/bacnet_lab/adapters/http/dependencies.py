from fastapi import Request

from bacnet_lab.bootstrap import Container


def get_container(request: Request) -> Container:
    return request.app.state.container
