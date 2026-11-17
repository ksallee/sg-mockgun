"""Uploads, thumbnails and downloads: the URLs, messages and state the media methods share. No I/O.

Behaviour is api3 answers 053 to 058 in docs/api3/.
"""
import hashlib
import mimetypes
import posixpath
import urllib.parse

# api3 055: the placeholder `image` reads until the transcode ends.
TRANSIENT_PATH = "/images/status/transient/thumbnail_pending.png"

# api3 053: the Attachment of a media upload reads this until its thumbnail is made.
PENDING_STATUS = "thumbnail_pending_us"

# Field names the client sends for a thumbnail, mapped to the field they set.
THUMBNAIL_FIELDS = {
    "thumb_image": "image",
    "image": "image",
    "filmstrip_thumb_image": "filmstrip_image",
    "filmstrip_image": "filmstrip_image",
}

STORAGE_HOST = "https://sg-media-mockgun.s3.amazonaws.com"

NOT_READY = ("Unable to share thumbnail: 2\nsource_entity image is a transient thumbnail that cannot be shared. "
             "Try again later, when the final thumbnail is available\n")


def new_state():
    """Empty media state for one mock instance; plain data, so it pickles and deep-copies."""
    return {
        "files": {},  # Attachment id -> bytes
        "urls": {},  # storage URL -> Attachment id
        "pending": {},  # (entity_type, entity_id, field) -> final URL
        "thumbnail_ids": {},  # (entity_type, entity_id) -> id upload_thumbnail returned
        "next_thumbnail_id": 1,
    }


def site_url(config, path):
    """An absolute URL on the mock's site."""
    return urllib.parse.urlunparse((config.scheme, config.server, path, None, None, None))


def transient_url(config):
    return site_url(config, TRANSIENT_PATH)


def storage_url(key, filename):
    """A presigned-storage style URL: `<host>/<hex>/<hex>/<filename>?<query>` (api3 053)."""
    digest = hashlib.md5(repr(key).encode("utf-8")).hexdigest()
    return "%s/%s/%s/%s?X-Amz-Expires=900" % (STORAGE_HOST, digest, digest[::-1], urllib.parse.quote(filename))


def thumbnail_name(filename):
    """The transcoded thumbnail's file name: `<stem>_t.jpg` (api3 055)."""
    return posixpath.splitext(filename)[0] + "_t.jpg"


def content_type(filename):
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def makes_thumbnail(filename):
    """Whether the server makes a thumbnail from an uploaded file: an image or a movie."""
    return content_type(filename).split("/")[0] in ("image", "video")


def tag_names(tag_list):
    """The tag names in a comma-separated `tag_list`, in order, without blanks."""
    return [name.strip() for name in (tag_list or "").split(",") if name.strip()]


def this_file(url, name, filename, attachment_id):
    """The File/Link value an upload leaves on the Attachment and the entity field (api3 053)."""
    return {
        "url": url,
        "name": name,
        "content_type": content_type(filename),
        "link_type": "upload",
        "type": "Attachment",
        "id": attachment_id,
    }


def upload_refusal(path, config, reason):
    """The ShotgunError message for an upload the server refuses (api3 054)."""
    return ("Could not upload file successfully, but not sure why.\nPath: %s\nUrl: %s\nError: 0\n%s\n"
            % (path, site_url(config, "/upload/api_link_file"), reason))


def entity_not_found(entity_type, entity_id):
    return "entity with entity_id %s and of entity_type %s not found" % (entity_id, entity_type)


def invalid_class(entity_type):
    return "entity_type %s is not a valid class" % entity_type


def invalid_column(entity_type, field_name):
    return "Column %s isn't a valid entity column for %s" % (field_name, entity_type)


def share_missing(entity_type, entity_id):
    """The ShotgunError message for a share target that does not exist (api3 058)."""
    return "Unable to share thumbnail: 0\nCouldn't find %s with 'id'=%s in 'entities' parameter\n" % (
        entity_type, entity_id)


def download_failure(url):
    """The ShotgunFileDownloadError message for a URL with no stored file (api3 056)."""
    return "Failed to open %s\nHTTP Error 404: Not Found" % url


def attachment_download_url(config, attachment):
    """The client's get_attachment_download_url, against the mock's site (api3 057)."""
    attachment_id = None
    if isinstance(attachment, int):
        attachment_id = attachment
    elif isinstance(attachment, dict):
        try:
            url = attachment["url"]
        except KeyError:
            if "id" in attachment and "type" in attachment and attachment["type"] == "Attachment":
                attachment_id = attachment["id"]
            else:
                raise ValueError("Missing 'url' key in Attachment dict")
    elif attachment is None:
        url = None
    else:
        raise TypeError("Unable to determine download url. Expected dict, int, or NoneType. Instead got %s"
                        % type(attachment))
    if attachment_id:
        url = site_url(config, "/file_serve/attachment/%s" % urllib.parse.quote(str(attachment_id)))
    # Id 0 is falsy and leaves `url` unset: the client raises UnboundLocalError, and so does this.
    return url


def attachment_id_of(config, state, url):
    """The Attachment id a download URL serves, or None when it serves no stored file."""
    prefix = site_url(config, "/file_serve/attachment/")
    if url.startswith(prefix):
        tail = url[len(prefix):]
        return int(tail) if tail.isdigit() else None
    return state["urls"].get(url)
