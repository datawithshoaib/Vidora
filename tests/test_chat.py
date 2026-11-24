import sqlite3


def completed_analysis(env, url="https://www.youtube.com/watch?v=abc123XYZ_-") -> str:
    job_id = env.submit(url).json()["id"]
    env.runner.run_all()
    return env.client.get(f"/jobs/{job_id}").json()["analysis_id"]


def ask(client, analysis_id, question):
    return client.post(f"/analyses/{analysis_id}/chat", json={"question": question})


def test_asking_a_question_returns_an_answer_grounded_in_the_transcript(env) -> None:
    analysis_id = completed_analysis(env)

    response = ask(env.client, analysis_id, "What was said?")

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "What was said?"
    assert body["answer"] == "Answer to: What was said?"
    assert body["created_at"]
    call = env.answerer.calls[0]
    assert "hello from the video" in call["context"]
    assert call["question"] == "What was said?"


def test_chat_history_lists_turns_oldest_first(env) -> None:
    analysis_id = completed_analysis(env)
    assert env.client.get(f"/analyses/{analysis_id}/chat").json() == []

    ask(env.client, analysis_id, "First?")
    ask(env.client, analysis_id, "Second?")

    history = env.client.get(f"/analyses/{analysis_id}/chat").json()
    assert [turn["question"] for turn in history] == ["First?", "Second?"]
    assert history[1]["answer"] == "Answer to: Second?"


def test_follow_up_questions_receive_prior_turns_as_context(env) -> None:
    analysis_id = completed_analysis(env)

    ask(env.client, analysis_id, "Who spoke?")
    ask(env.client, analysis_id, "And what did they say?")

    assert env.answerer.calls[0]["history"] == []
    assert env.answerer.calls[1]["history"] == [("Who spoke?", "Answer to: Who spoke?")]


def test_chats_are_separate_per_analysis(env) -> None:
    first = completed_analysis(env)
    second = completed_analysis(env)

    ask(env.client, first, "Only here?")

    assert env.client.get(f"/analyses/{second}/chat").json() == []


def test_chat_history_survives_a_restart(env) -> None:
    analysis_id = completed_analysis(env)
    ask(env.client, analysis_id, "Will this persist?")

    restarted = env.restart()

    history = restarted.get(f"/analyses/{analysis_id}/chat").json()
    assert [turn["answer"] for turn in history] == ["Answer to: Will this persist?"]
    ask(restarted, analysis_id, "And a follow-up?")
    assert env.answerer.calls[-1]["history"] == [
        ("Will this persist?", "Answer to: Will this persist?")
    ]


def test_deleting_an_analysis_removes_its_chat(env) -> None:
    analysis_id = completed_analysis(env)
    ask(env.client, analysis_id, "Gone soon?")

    assert env.client.delete(f"/analyses/{analysis_id}").status_code == 204

    assert env.client.get(f"/analyses/{analysis_id}/chat").status_code == 404
    with sqlite3.connect(env.data_dir / "vidora.db") as db:
        assert db.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0] == 0


def test_unknown_analysis_returns_404(env) -> None:
    assert ask(env.client, "nope", "Hello?").status_code == 404
    assert env.client.get("/analyses/nope/chat").status_code == 404


def test_chat_on_an_unfinished_analysis_returns_409(env) -> None:
    job_id = env.submit().json()["id"]  # queued, runner not run

    response = ask(env.client, job_id, "Ready yet?")

    assert response.status_code == 409
    assert "not finished" in response.json()["detail"]
    assert env.answerer.calls == []


def test_empty_question_is_rejected(env) -> None:
    analysis_id = completed_analysis(env)

    for question in ["", "   "]:
        assert ask(env.client, analysis_id, question).status_code == 422
    assert env.client.post(f"/analyses/{analysis_id}/chat", json={}).status_code == 422
    assert env.client.get(f"/analyses/{analysis_id}/chat").json() == []


def test_answerer_failure_returns_a_clear_error_and_saves_nothing(env) -> None:
    analysis_id = completed_analysis(env)
    env.answerer.error = RuntimeError("MISTRAL_API_KEY is not set.")

    response = ask(env.client, analysis_id, "Does this work?")

    assert response.status_code == 502
    assert "MISTRAL_API_KEY" in response.json()["detail"]
    assert env.client.get(f"/analyses/{analysis_id}/chat").json() == []


def test_long_transcripts_send_only_relevant_passages(env) -> None:
    filler = " ".join(f"filler{i}" for i in range(6000))
    env.transcriber.transcribe = lambda chunks: (
        f"{filler} The budget was approved at ten thousand dollars. {filler}"
    )
    analysis_id = completed_analysis(env)

    ask(env.client, analysis_id, "How much was the budget?")

    context = env.answerer.calls[0]["context"]
    assert "budget was approved" in context
    assert len(context) < 20000  # transcript is about 100k characters
