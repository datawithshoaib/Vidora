import pytest


def test_submitting_a_youtube_url_creates_a_queued_job(env) -> None:
    response = env.submit()

    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "queued"
    assert env.client.get(f"/jobs/{job['id']}").json()["status"] == "queued"


def test_job_progresses_through_steps_to_completed_analysis(env) -> None:
    job_id = env.submit().json()["id"]
    seen = []

    def snapshot():
        job = env.client.get(f"/jobs/{job_id}").json()
        seen.append((job["status"], job["step"]))

    env.fetcher.on_call = snapshot
    env.transcriber.on_call = snapshot
    env.runner.run_all()

    assert seen == [("processing", "downloading"), ("processing", "transcribing")]
    job = env.client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["error"] is None
    analysis = env.client.get(f"/analyses/{job['analysis_id']}").json()
    assert analysis["transcript"] == "hello from the video"
    assert analysis["title"] == "A Fake Title"
    assert analysis["summary"] == "- a summary"
    assert analysis["action_items"] == "1. do a thing"
    assert analysis["key_decisions"] == "1. decided a thing"
    assert analysis["open_questions"] == "1. why?"


def test_each_submission_is_a_fresh_job_and_analysis(env) -> None:
    first = env.submit().json()["id"]
    second = env.submit().json()["id"]
    env.runner.run_all()

    ids = {env.client.get(f"/jobs/{i}").json()["analysis_id"] for i in (first, second)}
    assert first != second
    assert len(ids) == 2


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "ftp://www.youtube.com/watch?v=abc123XYZ_-",
        "https://example.com/watch?v=abc123XYZ_-",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch?v=",
        "https://evilyoutube.com/watch?v=abc123XYZ_-",
    ],
)
def test_invalid_or_unsupported_urls_are_rejected_with_a_clear_message(env, url) -> None:
    response = env.submit(url)

    assert response.status_code == 422
    assert "YouTube" in response.json()["detail"]
    assert env.runner.pending == []


@pytest.mark.parametrize(
    "url",
    [
        "https://youtu.be/abc123XYZ_-",
        "https://youtube.com/watch?v=abc123XYZ_-&t=5s",
        "https://m.youtube.com/watch?v=abc123XYZ_-",
        "https://www.youtube.com/shorts/abc123XYZ_-",
    ],
)
def test_common_youtube_url_forms_are_accepted(env, url) -> None:
    assert env.submit(url).status_code == 202


def test_download_failure_marks_job_failed_with_message(env) -> None:
    env.fetcher.error = RuntimeError("video is private")
    job_id = env.submit().json()["id"]
    env.runner.run_all()

    job = env.client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "video is private" in job["error"]
    assert job["analysis_id"] is None
    assert env.analyzer.transcripts == []


def test_analysis_failure_marks_job_failed(env) -> None:
    env.analyzer.error = RuntimeError("llm unavailable")
    job_id = env.submit().json()["id"]
    env.runner.run_all()

    job = env.client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "llm unavailable" in job["error"]


def test_temporary_media_is_removed_after_success_and_failure(env) -> None:
    env.submit()
    env.runner.run_all()
    env.fetcher.error = RuntimeError("boom")
    env.submit()
    env.runner.run_all()

    assert len(env.fetcher.workdirs) == 2
    for workdir in env.fetcher.workdirs:
        assert not workdir.exists()


def test_jobs_have_isolated_temp_directories(env) -> None:
    env.submit()
    env.submit()
    env.runner.run_all()

    assert env.fetcher.workdirs[0] != env.fetcher.workdirs[1]


def test_unknown_job_and_analysis_return_404(env) -> None:
    assert env.client.get("/jobs/nope").status_code == 404
    assert env.client.get("/analyses/nope").status_code == 404


def test_transcription_receives_downloaded_chunks_only(env) -> None:
    env.submit()
    env.runner.run_all()

    assert [p.name for p in env.transcriber.calls[0]] == ["chunk_0.wav"]


def test_unfinished_jobs_are_failed_when_service_restarts(env) -> None:
    job_id = env.submit().json()["id"]  # stays queued, never run

    job = env.restart().get(f"/jobs/{job_id}").json()

    assert job["status"] == "failed"
    assert "interrupted" in job["error"].lower()


def test_completed_analysis_survives_restart(env) -> None:
    job_id = env.submit().json()["id"]
    env.runner.run_all()
    analysis_id = env.client.get(f"/jobs/{job_id}").json()["analysis_id"]

    restarted = env.restart()

    assert restarted.get(f"/analyses/{analysis_id}").json()["title"] == "A Fake Title"
    assert restarted.get(f"/jobs/{job_id}").json()["status"] == "completed"


def test_frontend_origin_may_post_jobs(env) -> None:
    response = env.client.options(
        "/jobs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_empty_transcript_fails_the_job_instead_of_saving_blank_notes(env) -> None:
    env.transcriber.transcribe = lambda chunks: "   "
    job_id = env.submit().json()["id"]
    env.runner.run_all()

    job = env.client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "speech" in job["error"].lower()
    assert job["analysis_id"] is None
    assert env.analyzer.transcripts == []
    assert env.tmp_entries() == []
