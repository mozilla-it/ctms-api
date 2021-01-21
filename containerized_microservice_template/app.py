from typing import List, Optional

import uvicorn
from fastapi import Body, FastAPI, Path, Query
from fastapi.responses import RedirectResponse

from containerized_microservice_template.models import (
    APIRequest,
    APIResponse,
    ExampleAPIRequest,
    ExampleAPIResponse,
)

app = FastAPI(
    title="Containerized Microservice",
    description="Containerized microservice template with some examples.",
    version="0.1.0",
)


@app.get("/")
def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """

    return RedirectResponse(url="./docs")


@app.post(
    "/api/{path_param}",
    summary="Post with Path, Query, and Body Params",
    response_description="JSON provided from request is passed through.",
)
def post_with_path_body_and_query(
    path_param: str = Path(..., title="An example path_param"),
    request=Body(..., embed=False),
    query_params: Optional[str] = Query(None),
):
    """POST to /api/{path_param} potentially with a JSON Body and optionally query params.

    - Args:
        - **path_param (str)**: Path param desired to traverse
        - **request (Body)**: JSON body upon HTTP Request
        - **query_params (Optional[str])**: Query parameters can be provided if desired

    - Returns:
        - **response**: returns the input request
    """

    # If you DO NOT know the model representation of the API Request,
    # use this method to get the body necessary to generate the model.
    return request


@app.post(
    "/api",
    summary="Post with APIRequest Model as JSON Body",
    response_description="JSON provided from request is passed through.",
    response_model=APIResponse,
)
def post_api_by_models(request: APIRequest = Body(..., embed=False)):
    """POST to /api with a JSON Body in the form of an APIRequest model.

    - Args:
        - **request (APIRequest)**: JSON body upon HTTP Request in the APIRequest model form

    - Returns:
        - **response**: returns the input request in the APIResponse model form
    """

    # If you DO know the model representation of the API Request,
    # construct a model then replace the models in use here.
    return request


# TODO: Remove the Example below ----
@app.post(
    "/example",
    summary="Example Models in use",
    response_description="JSON provided from request has a field filtered",
    response_model=ExampleAPIResponse,
)
def example(request: ExampleAPIRequest):
    """POST to /example with a HTTP Request consisting of a Body in the form of the ExampleAPIRequest model

    - Args:
        - **request (ExampleAPIRequest)**: JSON body upon HTTP Request in the ExampleAPIRequest model form

    - Returns:
        - **response**: returns the input request in the form of an ExampleAPIResponse model
    """

    # Purely an example with models
    return request


# TODO: Remove the Example above ----


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health")
def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
