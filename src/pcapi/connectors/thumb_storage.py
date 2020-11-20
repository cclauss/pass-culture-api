from typing import Callable

from pcapi.domain.mediations import standardize_image
from pcapi.utils import object_storage


def create_thumb(
    model_with_thumb,
    image_as_bytes,
    image_index,
    crop_params=None,
    symlink_path=None,
):
    image_as_bytes = standardize_image(image_as_bytes, crop_params)

    object_storage.store_public_object(
        bucket="thumbs",
        id=model_with_thumb.get_thumb_storage_id(image_index),
        blob=image_as_bytes,
        content_type="image/jpeg",
        symlink_path=symlink_path,
    )
