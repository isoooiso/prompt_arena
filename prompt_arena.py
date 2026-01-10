# { "Depends": "py-genlayer:test" }

from genlayer import *

class PromptArena(gl.Contract):

    room_id: str
    challenge: str
    finalized: bool

    # Fully instantiated generic types only
    prompts: TreeMap[Address, str]

    # JSON string with the AI-produced leaderboard
    leaderboard_json: str

    def __init__(self, room_id: str, challenge: str):
        self.room_id = room_id
        self.challenge = challenge
        self.finalized = False
        # prompts is auto zero-initialized by GenVM
        self.leaderboard_json = ""

    # ---------- Views ----------

    @gl.public.view
    def get_room_id(self) -> str:
        return self.room_id

    @gl.public.view
    def get_challenge(self) -> str:
        return self.challenge

    @gl.public.view
    def is_finalized(self) -> bool:
        return self.finalized

    @gl.public.view
    def get_leaderboard(self) -> str:
        return self.leaderboard_json

    @gl.public.view
    def get_prompt(self, player: Address) -> str:
        if player in self.prompts:
            return self.prompts[player]
        return ""

    @gl.public.view
    def get_prompt_count(self) -> int:
        c = 0
        for _ in self.prompts:
            c += 1
        return c

    # ---------- Writes ----------

    @gl.public.write
    def submit_prompt(self, prompt: str) -> str:
        if self.finalized:
            return "Game already finalized"

        p = prompt.strip()
        if len(p) == 0:
            return "Empty prompt"

        # Limit size a bit for safety / demo
        if len(p) > 800:
            return "Prompt too long"

        self.prompts[gl.message.sender_address] = p
        return "OK"

    @gl.public.write
    def finalize(self) -> str:
        if self.finalized:
            return "Already finalized"

        # Build text for validator(s)
        lines = []
        for addr in self.prompts:
            text = self.prompts[addr]
            if len(text) > 0:
                lines.append("- " + str(addr) + ": " + text)

        if len(lines) == 0:
            return "No prompts submitted"

        input_text = (
            "ROOM: " + self.room_id + "\n"
            "CHALLENGE: " + self.challenge + "\n"
            "SUBMISSIONS:\n" + "\n".join(lines)
        )

        task = (
            "You are judging a short community game called Prompt Arena.\n"
            "Select the TOP 3 prompt submissions.\n"
            "Judge by: (1) alignment with the challenge, (2) clarity, (3) usefulness, (4) creativity.\n"
            "Return ONLY valid JSON."
        )

        criteria = (
            "Return ONLY JSON.\n"
            "Schema:\n"
            "{\n"
            "  \"room_id\": string,\n"
            "  \"challenge\": string,\n"
            "  \"winners\": [\n"
            "    { \"rank\": 1, \"player\": string, \"reason\": string },\n"
            "    { \"rank\": 2, \"player\": string, \"reason\": string },\n"
            "    { \"rank\": 3, \"player\": string, \"reason\": string }\n"
            "  ],\n"
            "  \"notes\": string\n"
            "}\n"
            "Rules:\n"
            "- rank must be 1..3\n"
            "- player must be one of the provided addresses\n"
            "- reason must be short (<= 200 chars)\n"
            "- notes must be short (<= 300 chars)\n"
        )

        # Optimistic Democracy / equivalence principle (criteria-based validation)
        result = gl.eq_principle.prompt_non_comparative(
            input=input_text,
            task=task,
            criteria=criteria
        )

        self.leaderboard_json = result
        self.finalized = True
        return "FINALIZED"
