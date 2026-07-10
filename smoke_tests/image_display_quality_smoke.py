import math
import sys
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from media.image_dimensions import ImageDimensions
from media.image_loader import ImageLoader
from media.thumbnail_cache import ThumbnailCache


def assert_ratio_close(source_size, fitted_size, tolerance=0.02):

    source_ratio = source_size[0] / source_size[1]
    fitted_ratio = fitted_size[0] / fitted_size[1]

    assert math.isclose(
        source_ratio,
        fitted_ratio,
        rel_tol=tolerance
    ), (source_size, fitted_size)


def make_image(path, size, color):

    image = Image.new(
        "RGB",
        size,
        color
    )
    image.save(path)


def make_oriented_image(path):

    image = Image.new(
        "RGB",
        (80, 140),
        (200, 80, 40)
    )
    exif = Image.Exif()
    exif[274] = 6
    image.save(
        path,
        exif=exif
    )


def main():

    cases = (
        ((1600, 900), (420, 236)),
        ((900, 1600), (236, 420)),
        ((800, 800), (420, 420)),
        ((2400, 500), (420, 88)),
        ((120, 80), (120, 80))
    )

    for source, expected in cases:
        fitted = ImageDimensions.fit_size(
            source,
            (420, 420)
        )
        assert fitted == expected, (source, fitted, expected)
        assert fitted[0] <= min(source[0], 420)
        assert fitted[1] <= min(source[1], 420)
        assert_ratio_close(
            source,
            fitted
        )

    upscaled = ImageDimensions.fit_size(
        (80, 40),
        (420, 420)
    )
    assert upscaled == (80, 40), upscaled

    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        cache = ThumbnailCache(
            cache_dir=temp / "thumbs"
        )

        image_specs = (
            ("landscape.jpg", (1600, 900), (20, 40, 80)),
            ("portrait.jpg", (900, 1600), (80, 40, 20)),
            ("square.jpg", (800, 800), (50, 90, 50)),
            ("panorama.jpg", (2400, 500), (90, 50, 50)),
            ("small.jpg", (120, 80), (40, 80, 90))
        )

        for filename, size, color in image_specs:
            source = temp / filename
            make_image(
                source,
                size,
                color
            )

            thumbnail = cache.get_thumbnail(source)

            assert thumbnail is not None, source
            assert thumbnail.exists(), thumbnail

            loaded = ImageLoader.load_pil_image(thumbnail)

            assert loaded.width <= ThumbnailCache.DEFAULT_SIZE
            assert loaded.height <= ThumbnailCache.DEFAULT_SIZE
            assert_ratio_close(
                size,
                loaded.size
            )

        oriented = temp / "oriented.jpg"
        make_oriented_image(oriented)

        corrected = ImageLoader.load_pil_image(oriented)
        assert corrected.size == (140, 80), corrected.size

        default_identity = cache.cache_identity(
            temp / "landscape.jpg",
            ThumbnailCache.DEFAULT_SIZE
        )
        smaller_identity = cache.cache_identity(
            temp / "landscape.jpg",
            200
        )

        assert default_identity != smaller_identity

        original_version = cache.CACHE_VERSION
        cache.CACHE_VERSION = original_version + 1
        changed_version_identity = cache.cache_identity(
            temp / "landscape.jpg",
            ThumbnailCache.DEFAULT_SIZE
        )

        assert default_identity != changed_version_identity

    print("image_display_quality smoke passed")


if __name__ == "__main__":
    main()
