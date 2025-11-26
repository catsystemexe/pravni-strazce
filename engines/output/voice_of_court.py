"""
Voice of court engine – stylizace výstupu do hlasu soudu (OS, KS, VS, NS, NSS, ÚS...).

TODO:
- definovat styly pro jednotlivé úrovně soudů
- generovat shrnutí 'jak by to mohlo znít v rozhodnutí'
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: stylizace hlasu soudu
    return EngineOutput(
        name="voice_of_court_engine",
        payload={
            "court_like_summary": "Voice of court skeleton – zde bude stylizace do hlasu soudu.",
        },
        notes=["voice_of_court_engine not fully implemented yet"],
    )
