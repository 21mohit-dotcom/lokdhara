"""Test prompts for development only, so the prompted and read modes can be tried.

They are written by the team in Hindi, are not reviewed (Q-X5, Q-G7), and the read sentence is
a Hindi placeholder, not Mundari: the real sentence bank waits for Q-X6. Their keys start with
`test-` so they are easy to retire.
"""

from dataclasses import dataclass, field

SOURCE = "Lokdhara test prompt for development; not reviewed, not for real collection"


@dataclass(frozen=True)
class DevPrompt:
    prompt_key: str
    prompt_type: str
    text: str
    topic_tags: list[str] = field(default_factory=list)
    script_code: str | None = None


DEV_PROMPTS = (
    DevPrompt("test-situation-rain", "situation", "बारिश के किसी दिन के बारे में बताइए।", ["weather"]),
    DevPrompt(
        "test-situation-market",
        "situation",
        "बाज़ार जाने के बारे में बताइए: आप क्या खरीदते हैं?",
        ["food"],
    ),
    DevPrompt(
        "test-situation-festival",
        "situation",
        "आपको कौन-सा त्योहार पसंद है, और उसमें क्या होता है?",
        ["festival"],
    ),
    DevPrompt(
        "test-read-placeholder",
        "read_sentence",
        "यह एक परीक्षण वाक्य है।",
        ["test"],
        script_code="Deva",
    ),
)
