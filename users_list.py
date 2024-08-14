import pickle


class GetUsersDumpTree:
    def __init__(self, file_path):
        self._users = []
        self._path = file_path
        self._load_file()

    def _load_file(self):
        with open(file=self._path, mode="rb") as file:
            data = pickle.load(file)
            for folder in data:
                if "child" in folder:
                    for user in folder["child"]:
                        self._users.append(user)

    @property
    def get(self):
        return self._users


