from runtime.orchestrator import run_pipeline


def test_run_pipeline_skeleton():
    result = run_pipeline("Test dotaz")
    assert "context" in result
    assert "engine_results" in result
