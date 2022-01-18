def try_read_file_bytes(file_name):
    try:
        with open(file_name, "rb") as handle:
            return handle.read(-1)
    except:
        return None
