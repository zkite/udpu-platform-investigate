from pydantic import BaseModel

from domain.api.service.constants import SERVICE_DISCOVERY_PREFIX


class ServiceDiscoverySchema(BaseModel):
    host: str
    port: int
    service_type: str

    @property
    def key(self):
        return f"{SERVICE_DISCOVERY_PREFIX}_{self.service_type}_{self.host}_{self.port}"

    def serialize(self):
        data = {}
        for k in self.__fields__.keys():
            try:
                data[k] = str(getattr(self, k, ""))
            except Exception as e:
                print(e)
        return data
