import pathlib
import py_sri as sri

def test_parser():
    input = pathlib.Path("tests/html/input/")
    output = pathlib.Path("tests/html/output/")
    for file in input.iterdir():
        run_file(file, output)

def run_file(file, output_path):
    parser = sri.Parser()
    with open(file, "r") as f:
        html = f.read()
    parser.feed(html)
    new_html = parser.stringify()
    with open(output_path / file.name, "r") as f:
        assert new_html == f.read().strip()

if __name__ == "__main__":
    test_parser()
