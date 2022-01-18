from .pillowhost import PillowHostElement
from .utility import try_read_file_bytes

from PIL import Image

class Stenography:
    def __init__(self, image, *, file_path=None, steno_password=None):
        print('__init__ called.')
        self._image = image
        self._file_path = file_path
        self._steno_password = steno_password

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        del self._steno_password

    def insert_verification_data(self, **kwargs):
        try:
            steno_host = PillowHostElement(self._image)
        except FileNotFoundError:
            pass
        self._steno_password = self._generate_password()
        steno_host.insert_message(self._generate_hidden_data(), bits=1, password=self._steno_password, parasite_filename=self._file_path)
        return Image.fromarray(steno_host.data)

    @property
    def steno_password(self):
        return self._steno_password

    def _generate_hidden_data(self):
         return try_read_file_bytes(self._file_path)

    def _generate_password(self):
        return self._steno_password
