import hashlib


class HashManager:

    @staticmethod
    def sha256(file_path):

        sha = hashlib.sha256()

        with open(file_path, "rb") as file:

            while True:

                chunk = file.read(1024 * 1024)

                if not chunk:
                    break

                sha.update(chunk)

        return sha.hexdigest()