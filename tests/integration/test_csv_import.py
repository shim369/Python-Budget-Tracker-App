"""IT-CSV: CSV import through the API (REQ-018, 019)."""

from tests.integration.helpers import assert_error, csv_rows, import_csv


def test_it_csv_01_normal(client):
    raw = 'amount,date,memo,category\n"1,200",2026/10/1,ランチ,食費\n3980,2026-10-02,洗剤,daily goods\n800,2026-10-03,,Food\n'
    report = import_csv(client, raw.encode()).json()
    assert (report["imported_count"], report["error_count"], report["duplicate_count"]) == (3, 0, 0)
    items = client.get("/api/expenses?month=2026-10").json()["items"]
    assert sorted((i["date"], i["amount"], i["category_id"], i["memo"]) for i in items) == [
        ("2026-10-01", 1200, "cat-000001", "ランチ"),
        ("2026-10-02", 3980, "cat-000002", "洗剤"),
        ("2026-10-03", 800, "cat-000001", ""),
    ]


def test_it_csv_02_partially_invalid(client):
    raw = (
        "date,amount,category,memo\n"
        "2026-10-01,100,food,a\n"
        "2026-13-01,100,food,b\n"
        "2026-10-02,100,food,c\n"
        "2026-10-03,-5,food,d\n"
        "2026-10-04,100,food,e\n"
    )
    response = import_csv(client, raw.encode())
    assert response.status_code == 200
    report = response.json()
    assert (report["total_rows"], report["imported_count"], report["error_count"]) == (5, 3, 2)
    assert [(e["line"], e["field"], e["code"]) for e in report["errors"]] == [
        (3, "date", "INVALID_DATE"),
        (5, "amount", "INVALID_AMOUNT"),
    ]


def test_it_csv_03_all_invalid_keeps_file(client, data_file):
    before = data_file.read_bytes()
    report = import_csv(client, b"date,amount,category\nx,1,food\n2026-10-01,0,food\n").json()
    assert (report["imported_count"], report["error_count"]) == (0, 2)
    assert data_file.read_bytes() == before


def test_it_csv_04_empty(client):
    assert_error(import_csv(client, b""), 400, "CSV_EMPTY")
    assert_error(import_csv(client, b"date,amount,category,memo\n\n"), 400, "CSV_EMPTY")


def test_it_csv_05_too_large(client):
    raw = csv_rows(1).encode() + b"#" * (1_048_576)
    assert_error(import_csv(client, raw), 413, "CSV_TOO_LARGE")
    assert client.get("/api/expenses?month=2026-10").json()["count"] == 0


def test_it_csv_06_too_many_rows(client):
    raw = csv_rows(5_001).encode()
    assert len(raw) < 1_048_576
    error = assert_error(import_csv(client, raw), 413, "CSV_TOO_MANY_ROWS")
    assert error["details"][0]["params"] == {"max": 5_000}
    assert client.get("/api/expenses?month=2026-10").json()["count"] == 0


def test_it_csv_07_row_limit_boundary(client):
    assert import_csv(client, csv_rows(5_000).encode()).json()["imported_count"] == 5_000
    assert client.get("/api/expenses?month=2026-10").json()["count"] == 5_000


def test_it_csv_08_shift_jis_and_bom(client):
    sjis = "date,amount,category,memo\n2026-10-01,500,食費,髙島屋①\n".encode("cp932")
    report = import_csv(client, sjis).json()
    assert (report["encoding"], report["imported_count"]) == ("shift_jis", 1)
    bom = b"\xef\xbb\xbf" + "date,amount,category,memo\n2026-10-02,600,日用品,ドラッグストア\n".encode()
    report = import_csv(client, bom).json()
    assert (report["encoding"], report["imported_count"]) == ("utf-8-sig", 1)
    memos = {i["memo"] for i in client.get("/api/expenses?month=2026-10").json()["items"]}
    assert memos == {"髙島屋①", "ドラッグストア"}


def test_it_csv_09_utf16_is_unsupported(client):
    """BUG-001 retest."""
    raw = "date,amount,category,memo\n2026-10-01,500,food,x\n".encode("utf-16")
    assert_error(import_csv(client, raw), 400, "CSV_ENCODING_UNSUPPORTED")


def test_it_csv_10_duplicate_in_file(client):
    raw = "date,amount,category,memo\n2026-10-01,500,food,x\n2026/10/1,500,食費,x\n"
    report = import_csv(client, raw.encode()).json()
    assert (report["imported_count"], report["duplicate_count"]) == (1, 1)
    assert report["errors"] == [{"line": 3, "field": None, "code": "DUPLICATE_IN_FILE", "value": None}]


def test_it_csv_11_reimport_same_file(client):
    raw = csv_rows(3).encode()
    assert import_csv(client, raw).json()["imported_count"] == 3
    report = import_csv(client, raw).json()
    assert (report["imported_count"], report["duplicate_count"]) == (0, 3)
    assert {e["code"] for e in report["errors"]} == {"DUPLICATE_EXISTING"}
    assert client.get("/api/expenses?month=2026-10").json()["count"] == 3


def test_it_csv_12_media_type_and_header(client):
    assert_error(import_csv(client, b"x", {"Content-Type": "application/json"}), 415, "CSV_UNSUPPORTED_MEDIA_TYPE")
    assert_error(import_csv(client, b"x", {"Content-Type": "multipart/form-data"}), 415, "CSV_UNSUPPORTED_MEDIA_TYPE")
    assert import_csv(client, csv_rows(1).encode(), {"Content-Type": "text/csv; charset=utf-8"}).status_code == 200
    error = assert_error(import_csv(client, b"date,amonut,category\n2026-10-01,1,food\n"), 400, "CSV_HEADER_INVALID")
    assert {(d["field"], d["code"]) for d in error["details"]} == {
        ("amonut", "UNKNOWN_COLUMN"),
        ("amount", "MISSING_COLUMN"),
    }
