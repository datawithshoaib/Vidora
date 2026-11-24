import sqlite3


def run_job(env, url="https://www.youtube.com/watch?v=abc123XYZ_-") -> dict:
    job_id = env.submit(url).json()["id"]
    env.runner.run_all()
    return env.client.get(f"/jobs/{job_id}").json()


def test_history_is_empty_for_a_fresh_install(env) -> None:
    response = env.client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == []


def test_history_lists_newest_first_with_status_date_and_title(env) -> None:
    first = run_job(env)
    env.fetcher.error = RuntimeError("video is private")
    failed = run_job(env)
    queued = env.submit().json()

    history = env.client.get("/jobs").json()

    assert [item["id"] for item in history] == [queued["id"], failed["id"], first["id"]]
    assert [item["status"] for item in history] == ["queued", "failed", "completed"]
    assert all(item["created_at"] for item in history)
    assert history[2]["title"] == "A Fake Title"
    assert history[2]["analysis_id"] == first["analysis_id"]
    assert history[1]["title"] is None
    assert "video is private" in history[1]["error"]


def test_history_includes_uploads_by_filename(env) -> None:
    env.upload(filename="standup.mp3")
    env.runner.run_all()

    item = env.client.get("/jobs").json()[0]

    assert item["source_kind"] == "upload"
    assert item["source"] == "standup.mp3"


def test_history_and_past_analyses_survive_a_restart(env) -> None:
    job = run_job(env)
    env.fetcher.error = RuntimeError("boom")
    run_job(env)

    restarted = env.restart()

    history = restarted.get("/jobs").json()
    assert [item["status"] for item in history] == ["failed", "completed"]
    past = restarted.get(f"/analyses/{job['analysis_id']}").json()
    assert past["transcript"] == "hello from the video"


def test_resubmitting_the_same_source_creates_a_new_analysis(env) -> None:
    first = run_job(env)
    second = run_job(env)

    assert first["analysis_id"] != second["analysis_id"]
    assert len(env.client.get("/jobs").json()) == 2
    assert len(env.fetcher.urls) == 2


def test_deleting_a_job_removes_it_and_its_analysis(env) -> None:
    keep = run_job(env)
    gone = run_job(env)

    response = env.client.delete(f"/jobs/{gone['id']}")

    assert response.status_code == 204
    assert env.client.get(f"/jobs/{gone['id']}").status_code == 404
    assert env.client.get(f"/analyses/{gone['analysis_id']}").status_code == 404
    assert [item["id"] for item in env.client.get("/jobs").json()] == [keep["id"]]
    assert env.client.get(f"/analyses/{keep['analysis_id']}").status_code == 200


def test_deleting_a_failed_job_removes_it(env) -> None:
    env.fetcher.error = RuntimeError("boom")
    failed = run_job(env)

    assert env.client.delete(f"/jobs/{failed['id']}").status_code == 204
    assert env.client.get("/jobs").json() == []


def test_deleting_an_analysis_removes_it_and_its_history_entry(env) -> None:
    job = run_job(env)

    assert env.client.delete(f"/analyses/{job['analysis_id']}").status_code == 204

    assert env.client.get(f"/analyses/{job['analysis_id']}").status_code == 404
    assert env.client.get("/jobs").json() == []


def test_deletion_is_permanent_across_restart(env) -> None:
    job = run_job(env)
    env.client.delete(f"/jobs/{job['id']}")

    restarted = env.restart()

    assert restarted.get("/jobs").json() == []
    assert restarted.get(f"/analyses/{job['analysis_id']}").status_code == 404


def test_deleting_unknown_records_returns_404(env) -> None:
    assert env.client.delete("/jobs/nope").status_code == 404
    assert env.client.delete("/analyses/nope").status_code == 404


def test_deleting_an_in_progress_job_is_rejected_and_it_still_completes(env) -> None:
    job_id = env.submit().json()["id"]

    response = env.client.delete(f"/jobs/{job_id}")

    assert response.status_code == 409
    assert "in progress" in response.json()["detail"].lower()
    env.runner.run_all()
    assert env.client.get(f"/jobs/{job_id}").json()["status"] == "completed"


def test_deleting_a_job_removes_retained_artifacts_in_the_data_dir(env) -> None:
    job = run_job(env)
    leftover = env.data_dir / "tmp" / job["id"]
    leftover.mkdir(parents=True)
    (leftover / "stray.wav").write_bytes(b"x")

    env.client.delete(f"/jobs/{job['id']}")

    assert not leftover.exists()


def test_deleting_cascades_to_rows_that_reference_the_analysis(env) -> None:
    job = run_job(env)
    db = sqlite3.connect(env.data_dir / "vidora.db")
    db.execute("PRAGMA foreign_keys = ON")
    db.execute(
        "CREATE TABLE IF NOT EXISTS probe (id INTEGER PRIMARY KEY,"
        " analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE)"
    )
    db.execute("INSERT INTO probe (analysis_id) VALUES (?)", (job["analysis_id"],))
    db.commit()
    db.close()

    env.client.delete(f"/analyses/{job['analysis_id']}")

    db = sqlite3.connect(env.data_dir / "vidora.db")
    assert db.execute("SELECT COUNT(*) FROM probe").fetchone()[0] == 0


def test_no_media_remains_in_the_data_dir_after_success_or_failure(env) -> None:
    env.upload(content=b"big-media-payload")
    env.runner.run_all()
    env.preparer.error = RuntimeError("bad media")
    env.upload(content=b"other-media-payload")
    env.runner.run_all()
    run_job(env)

    files = [p for p in env.data_dir.rglob("*") if p.is_file()]
    assert [p.name for p in files if p.suffix != ".db" and not p.name.startswith("vidora.db")] == []
    assert env.tmp_entries() == []
