import pytest


def test_uploading_audio_creates_a_queued_upload_job(env) -> None:
    response = env.upload()

    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "queued"
    assert job["source_kind"] == "upload"
    assert job["source"] == "talk.mp3"
    assert env.client.get(f"/jobs/{job['id']}").json()["status"] == "queued"


def test_uploaded_media_flows_through_the_pipeline_to_a_result(env) -> None:
    job_id = env.upload(b"the-real-bytes").json()["id"]
    env.runner.run_all()

    assert env.preparer.contents == [b"the-real-bytes"]
    assert env.fetcher.urls == []
    job = env.client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "completed"
    analysis = env.client.get(f"/analyses/{job['analysis_id']}").json()
    assert analysis["transcript"] == "hello from the video"
    assert analysis["title"] == "A Fake Title"


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("clip.mp4", "video/mp4"),
        ("clip.mov", "video/quicktime"),
        ("voice.wav", "audio/wav"),
        ("talk.m4a", "audio/x-m4a"),
        ("talk.MP3", "application/octet-stream"),
    ],
)
def test_supported_audio_and_video_types_are_accepted(env, filename, content_type) -> None:
    assert env.upload(filename=filename, content_type=content_type).status_code == 202


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("notes.pdf", "application/pdf"),
        ("script.exe", "application/octet-stream"),
        ("noextension", "audio/mpeg"),
        ("fake.mp3", "text/plain"),
    ],
)
def test_unsupported_types_are_rejected_with_a_clear_message(env, filename, content_type) -> None:
    response = env.upload(filename=filename, content_type=content_type)

    assert response.status_code == 415
    assert "audio or video" in response.json()["detail"]
    assert env.runner.pending == []
    assert env.tmp_entries() == []


def test_oversize_uploads_are_rejected_and_leave_nothing_behind(env) -> None:
    response = env.upload(b"x" * 2048)

    assert response.status_code == 413
    assert "too large" in response.json()["detail"]
    assert env.runner.pending == []
    assert env.tmp_entries() == []


def test_upload_exactly_at_the_limit_is_accepted(env) -> None:
    assert env.upload(b"x" * 1024).status_code == 202


def test_missing_file_is_rejected(env) -> None:
    response = env.client.post("/jobs/upload", data={"other": "x"})

    assert response.status_code == 422
    assert env.tmp_entries() == []


def test_upload_is_removed_after_success(env) -> None:
    env.upload()
    assert len(env.tmp_entries()) == 1  # held until the job runs
    env.runner.run_all()

    assert env.tmp_entries() == []
    assert not env.preparer.workdirs[0].exists()


def test_upload_is_removed_after_a_processing_failure(env) -> None:
    job_id = env.upload().json()["id"]
    env.preparer.error = RuntimeError("could not decode media")
    env.runner.run_all()

    job = env.client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "could not decode media" in job["error"]
    assert env.tmp_entries() == []


def test_upload_is_removed_when_analysis_fails(env) -> None:
    env.upload()
    env.analyzer.error = RuntimeError("llm down")
    env.runner.run_all()

    assert env.tmp_entries() == []


def test_leftover_temp_files_from_a_crash_are_cleared_on_restart(env) -> None:
    env.upload()  # job never runs; service "crashes"
    assert len(env.tmp_entries()) == 1

    env.restart()

    assert env.tmp_entries() == []


def test_each_upload_is_a_fresh_job(env) -> None:
    first = env.upload().json()["id"]
    second = env.upload().json()["id"]
    env.runner.run_all()

    assert first != second
    ids = {env.client.get(f"/jobs/{i}").json()["analysis_id"] for i in (first, second)}
    assert len(ids) == 2
