import requests


class Reader:
    # stream uploader wrapper with method read for chunked reads
    def __init__(self, content):
        self.content = content
        self.iterator = None
        self.closed = False

    def read(self, size):
        if self.closed:
            return bytes()
        if not self.iterator:
            self.iterator = self.content.iter_content(chunk_size=size)
        try:
            return bytes(next(self.iterator))
        except StopIteration:
            self.iterator = None
            self.closed = True
            self.content.close()
            return bytes()

    def close(self):
        try:
            self.content.close()
        except Exception as e:
            print(e)


def download_file_reader(url):
    r = requests.get(url, stream=True)
    return Reader(r)


def download_saver(s3bucket, reader: Reader, object_path: str):
    s3bucket.put_object(object_path, reader, 0)

# def download_file2(url):
#     s3bucket = get_minio_client()
#     file_path = "Proj/repo/file100.txt"
#     # NOTE the stream=True parameter below
#     with requests.get(url, stream=True) as r:
#         r.raise_for_status()
#         reads = Reader(r)
#         s3bucket.put_or_replace_object(file_path, reads, 0)
#     return "OK"
