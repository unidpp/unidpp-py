import pathlib

collect_ignore = []
if not (pathlib.Path(__file__).parent / "conformance/eu-profile/fixtures/en-18223/raw").is_dir():
    collect_ignore.append("tests/test_eu_profile.py")
