import json

import pytest
from PIL import Image
from typer.testing import CliRunner


def _write_image(path, color, *, size=(32, 32), pixel=None):
    image = Image.new("RGBA", size, color)
    if pixel is not None:
        position, value = pixel
        image.putpixel(position, value)
    image.save(path)


class TestImageDiffCLI:
    """Black-box tests for the quickthumb diff command."""

    def test_should_report_exact_matches_as_json(self, tmp_path):
        """diff emits a successful structured result for identical images"""
        from quickthumb.cli import app

        # given: two identical golden-image files
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        _write_image(expected_path, (32, 64, 128, 255))
        _write_image(actual_path, (32, 64, 128, 255))

        # when: the images are compared in JSON mode
        result = CliRunner().invoke(
            app,
            ["diff", str(expected_path), str(actual_path), "--format", "json"],
        )

        # then: the result is an exact match with stable hash metrics
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["matches"] is True
        assert payload["exact"] is True
        assert payload["different_pixels"] == 0
        assert payload["hash_distance"] == 0
        assert payload["hash_similarity"] == 1.0

    def test_should_tolerate_small_raster_noise(self, tmp_path):
        """diff ignores small anti-aliasing noise within the default tolerance"""
        from quickthumb.cli import app

        # given: an image whose actual render differs by one low-amplitude pixel
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        _write_image(expected_path, (255, 255, 255, 255))
        _write_image(
            actual_path,
            (255, 255, 255, 255),
            pixel=((12, 12), (255, 254, 255, 255)),
        )

        # when: the images are compared with the default golden-image settings
        result = CliRunner().invoke(app, ["diff", str(expected_path), str(actual_path)])

        # then: the comparison passes while retaining the raw error measurement
        assert result.exit_code == 0
        assert "MATCH" in result.output
        assert "different pixels: 0/1024" in result.output
        assert "max channel delta: 1" in result.output

    def test_should_fail_and_write_a_visual_diff_for_significant_changes(self, tmp_path):
        """diff exits one and writes a difference image for a failed comparison"""
        from quickthumb.cli import app

        # given: a white golden image and a visibly different black render
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        diff_path = tmp_path / "diff.png"
        _write_image(expected_path, (255, 255, 255, 255))
        _write_image(actual_path, (0, 0, 0, 255))

        # when: the images are compared and a visual diff is requested
        result = CliRunner().invoke(
            app,
            [
                "diff",
                str(expected_path),
                str(actual_path),
                "--format",
                "json",
                "--output",
                str(diff_path),
            ],
        )

        # then: CI receives a mismatch and the diff contains changed pixels
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["matches"] is False
        assert payload["different_pixels"] == 1024
        assert payload["diff_output"] == str(diff_path)
        with Image.open(diff_path) as diff_image:
            assert diff_image.getpixel((0, 0)) == (255, 255, 255, 0)

    def test_should_write_rgb_visual_diffs_as_jpeg(self, tmp_path):
        """diff writes a valid RGB image when the requested output is JPEG"""
        from quickthumb.cli import app

        # given: two image files and a JPEG diff destination
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        diff_path = tmp_path / "diff.jpg"
        _write_image(expected_path, (255, 255, 255, 255))
        _write_image(actual_path, (0, 0, 0, 255))

        # when: the images are compared with a JPEG visual diff requested
        result = CliRunner().invoke(
            app,
            ["diff", str(expected_path), str(actual_path), "--output", str(diff_path)],
        )

        # then: the command reports the mismatch and leaves a JPEG-readable diff
        assert result.exit_code == 1
        with Image.open(diff_path) as diff_image:
            assert diff_image.mode == "RGB"
            assert diff_image.format == "JPEG"

    def test_should_report_dimension_mismatches(self, tmp_path):
        """diff reports incompatible image dimensions as a failed comparison"""
        from quickthumb.cli import app

        # given: images with different canvas dimensions
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        _write_image(expected_path, (255, 255, 255, 255), size=(32, 32))
        _write_image(actual_path, (255, 255, 255, 255), size=(16, 16))

        # when: the images are compared in JSON mode
        result = CliRunner().invoke(
            app,
            ["diff", str(expected_path), str(actual_path), "--format", "json"],
        )

        # then: the mismatch includes both sizes and a useful reason
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["matches"] is False
        assert payload["expected_size"] == [32, 32]
        assert payload["actual_size"] == [16, 16]
        assert payload["reason"] == "image dimensions differ"

    def test_should_reject_a_small_high_contrast_patch_by_default(self, tmp_path):
        """diff does not hide a visible localized change behind the hash threshold"""
        from quickthumb.cli import app

        # given: a white image with a small black patch in the actual render
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        _write_image(expected_path, (255, 255, 255, 255), size=(32, 32))
        actual_image = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
        for x in range(14, 17):
            for y in range(14, 17):
                actual_image.putpixel((x, y), (0, 0, 0, 255))
        actual_image.save(actual_path)

        # when: the images are compared with the default strict diff ratio
        result = CliRunner().invoke(
            app,
            ["diff", str(expected_path), str(actual_path), "--format", "json"],
        )

        # then: the visible patch is reported as a mismatch
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["matches"] is False
        assert payload["different_pixels"] == 9
        assert payload["max_different_pixel_ratio"] == 0.0

    def test_should_reject_unknown_output_formats(self, tmp_path):
        """diff exits one before reading images when its output format is invalid"""
        from quickthumb.cli import app

        # given: paths that would otherwise be valid image inputs
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        _write_image(expected_path, (255, 255, 255, 255))
        _write_image(actual_path, (255, 255, 255, 255))

        # when: an unsupported structured-output format is requested
        result = CliRunner().invoke(
            app,
            ["diff", str(expected_path), str(actual_path), "--format", "yaml"],
        )

        # then: the CLI explains the accepted formats
        assert result.exit_code == 1
        assert "Must be one of: text, json" in result.output


class TestImageDiffAPI:
    """Black-box tests for the public golden-image assertion helper."""

    def test_should_assert_similar_images(self, tmp_path):
        """assert_image_similar returns metrics for an accepted comparison"""
        from quickthumb import assert_image_similar

        # given: two image files with identical pixels
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        _write_image(expected_path, (12, 34, 56, 255))
        _write_image(actual_path, (12, 34, 56, 255))

        # when: the public CI assertion is called
        comparison = assert_image_similar(expected_path, actual_path)

        # then: it returns the structured comparison for further reporting
        assert comparison.matches is True
        assert comparison.exact is True

    def test_should_ignore_hidden_rgb_changes_in_transparent_pixels(self):
        """compare_images measures visible output instead of hidden transparent RGB"""
        from quickthumb import compare_images

        # given: fully transparent pixels with different hidden RGB values
        expected = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
        actual = Image.new("RGBA", (2, 2), (255, 0, 0, 0))

        # when: the public image comparison uses zero tolerance
        comparison = compare_images(
            expected,
            actual,
            pixel_tolerance=0,
            max_different_pixel_ratio=0.0,
        )

        # then: invisible channel differences do not count as changed pixels
        assert comparison.matches is True
        assert comparison.exact is True
        assert comparison.different_pixels == 0
        assert comparison.different_pixel_ratio == 0.0

    def test_should_raise_a_readable_assertion_for_failed_comparison(self, tmp_path):
        """assert_image_similar raises a readable failure for changed images"""
        from quickthumb import assert_image_similar

        # given: two materially different images
        expected_path = tmp_path / "expected.png"
        actual_path = tmp_path / "actual.png"
        _write_image(expected_path, (255, 255, 255, 255))
        _write_image(actual_path, (0, 0, 0, 255))

        # when: the public CI assertion is called
        with pytest.raises(AssertionError) as error:
            assert_image_similar(expected_path, actual_path)

        # then: the exception identifies the failed comparison
        assert "MISMATCH" in str(error.value)
        assert "different pixels: 1024/1024" in str(error.value)
