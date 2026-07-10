class ImageDimensions:

    @staticmethod
    def fit_size(source_size, bounding_size, allow_upscale=False):

        source_width, source_height = ImageDimensions._safe_size(
            source_size
        )
        bound_width, bound_height = ImageDimensions._safe_size(
            bounding_size
        )

        scale = min(
            bound_width / source_width,
            bound_height / source_height
        )

        if not allow_upscale:
            scale = min(scale, 1)

        width = max(1, int(round(source_width * scale)))
        height = max(1, int(round(source_height * scale)))

        return width, height

    ########################################################

    @staticmethod
    def _safe_size(size):

        try:
            width, height = size
        except Exception:
            return 1, 1

        width = ImageDimensions._safe_dimension(width)
        height = ImageDimensions._safe_dimension(height)

        return width, height

    ########################################################

    @staticmethod
    def _safe_dimension(value):

        try:
            value = int(value)
        except Exception:
            value = 1

        return max(1, value)
