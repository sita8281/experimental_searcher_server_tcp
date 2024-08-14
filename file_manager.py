import os
from os import listdir
from typing import Literal


class FileManager:
    def __init__(self):
        self.root = "DBs"

    def protected_path(self, path):
        if path.split("/", 1)[0] == self.root:
            return True

    def get_path_files(self):
        files_lst = {
            "SW": [],
            "NAS": [],
        }
        sw_path = f"{self.root}/SW"
        nas_path = f"{self.root}/NAS"

        for file in listdir(sw_path):
            name, extend = file.split(".")
            size = os.path.getsize(f"{sw_path}/{name}.{extend}")
            path = f"{sw_path}/{name}.{extend}"
            files_lst["SW"].append((name, extend, size, path))
        for file in listdir(nas_path):
            name, extend = file.split(".")
            size = os.path.getsize(f"{nas_path}/{name}.{extend}")
            path = f"{nas_path}/{name}.{extend}"
            files_lst["NAS"].append((name, extend, size, path))

        return files_lst

    def get_file(self, path: str):
        if not self.protected_path(path):
            raise FileNotFoundError
        with open(file=path, mode="rb") as f:
            return f.read()

    def delete_file(self, path: str):
        if not self.protected_path(path):
            raise FileNotFoundError
        os.remove(path)
        return True

    def create_file(self, filename: str, root_path: Literal["SW", "NAS"], payload: bytes):
        with open(file=f"{self.root}/{root_path}/{filename}.pickle", mode="wb") as f:
            f.write(payload)
            return True
