from pydantic import BaseModel, ConfigDict, Field


class NameValue(BaseModel):
    name: str
    value: str = ""


class PostData(BaseModel):
    mimeType: str = ""
    text: str | None = None
    params: list[NameValue] = Field(default_factory=list)


class HarRequest(BaseModel):
    method: str
    url: str
    headers: list[NameValue] = Field(default_factory=list)
    queryString: list[NameValue] = Field(default_factory=list)
    postData: PostData | None = None


class Content(BaseModel):
    mimeType: str = ""
    text: str | None = None
    encoding: str | None = None


class HarResponse(BaseModel):
    status: int = 0
    headers: list[NameValue] = Field(default_factory=list)
    content: Content = Field(default_factory=Content)


class HarEntry(BaseModel):
    """Subconjunto de uma entrada HAR 1.2 usado pela análise."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    startedDateTime: str
    time: float = 0.0
    request: HarRequest
    response: HarResponse
    resource_type: str | None = Field(default=None, alias="_resourceType")

    def request_header(self, name: str) -> str | None:
        return _find(self.request.headers, name)

    def response_header(self, name: str) -> str | None:
        return _find(self.response.headers, name)


def _find(headers: list[NameValue], name: str) -> str | None:
    lname = name.lower()
    for h in headers:
        if h.name.lower() == lname:
            return h.value
    return None
