import pandas as pd

from pactum.cli import main


def _write_contract(path, csv_path, body):
    path.write_text(
        f"name: c\nsource:\n  type: csv\n  path: {csv_path}\n{body}"
    )


def test_check_passing(tmp_path):
    csv_path = tmp_path / "d.csv"
    pd.DataFrame({"id": [1, 2, 3]}).to_csv(csv_path, index=False)
    contract = tmp_path / "c.yml"
    _write_contract(
        contract,
        csv_path,
        "columns:\n  - name: id\n    dtype: integer\n    nullable: false\n    unique: true\n",
    )
    assert main(["check", str(contract), "--no-color"]) == 0


def test_check_failing(tmp_path):
    csv_path = tmp_path / "d.csv"
    pd.DataFrame({"id": [1, 1]}).to_csv(csv_path, index=False)
    contract = tmp_path / "c.yml"
    _write_contract(contract, csv_path, "columns:\n  - name: id\n    unique: true\n")
    assert main(["check", str(contract), "--no-color"]) == 1


def test_json_output(tmp_path, capsys):
    csv_path = tmp_path / "d.csv"
    pd.DataFrame({"id": [1, 2]}).to_csv(csv_path, index=False)
    contract = tmp_path / "c.yml"
    _write_contract(contract, csv_path, "columns:\n  - name: id\n    unique: true\n")
    main(["check", str(contract), "--format", "json"])
    assert '"contract": "c"' in capsys.readouterr().out


def test_init_writes_file(tmp_path):
    target = tmp_path / "new.yml"
    assert main(["init", "orders", "--output", str(target)]) == 0
    assert target.exists()
    assert "name: orders" in target.read_text()
