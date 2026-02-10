from typing import Optional, Union

from pydantic import BaseModel

from services.utils import get_hashed_software_uid, get_sha256_checksum

from .constants import REPO_ENTITY


class Repository(BaseModel):
    description: Union[str, None] = None
    locked: bool = False
    url: Union[str, None] = None
    password: Union[str, None] = None
    software_uid: Union[str, None] = None
    sha256_checksum: Union[str, None] = None
    number_of_downloads: Optional[int] = 0

    def calculate_software_uid(self):
        self.software_uid = get_hashed_software_uid(self.url, self.password)

    def calculate_sha256_checksum(self):
        self.sha256_checksum = get_sha256_checksum(self.url)

    @property
    def repository_key(self):
        return f"{REPO_ENTITY}_{self.software_uid}"

    def serialize(self):
        data = {}
        for k in self.__fields__.keys():
            try:
                data[k] = str(getattr(self, k, ""))
            except Exception as e:
                print(e)
        return data
