import json
import random
from pathlib import Path

ANIMALS = [
    "Eagles", "Buffalos", "Crocodiles", "Wolves", "Panthers", "Falcons",
    "Sharks", "Cobras", "Tigers", "Rhinos", "Hawks", "Scorpions", "Bears",
    "Lions", "Vipers", "Ravens", "Jaguars", "Leopards", "Hornets", "Mantis",
    "Stallions", "Gorillas", "Foxes", "Owls", "Lynxes", "Piranhas",
    "Condors", "Hyenas", "Barracudas", "Mustangs", "Wolverines", "Komodos",
]
PREFIXES = ["Kas", "Vor", "Zel", "Nox", "Bra", "Tyr", "Lun", "Dra", "Fen",
            "Hex", "Kry", "Mor", "Sol", "Rav", "Ash", "Jin", "Quo", "Vex",
            "Zar", "Ori"]
SUFFIXES = ["ares", "ix", "on", "ius", "ek", "ara", "oth", "us", "yn",
            "el", "ak", "ion"]
ROLES = ["TOP", "JGL", "MID", "ADC", "SUP"]

assert len(ANIMALS) == 32


def main():
    rng = random.Random(2026)  # seed fixa: mesmos times sempre
    combos = [p + s for p in PREFIXES for s in SUFFIXES]
    nicks = rng.sample(combos, 32 * 5)  # 160 nicknames únicos

    teams = []
    for i, animal in enumerate(ANIMALS):
        team_id = animal.lower()
        players = []
        for j, role in enumerate(ROLES):
            players.append({
                "id": f"{team_id}-{role.lower()}",
                "nickname": nicks[i * 5 + j],
                "role": role,
            })
        teams.append({"id": team_id, "name": animal, "players": players})

    out = Path(__file__).parent / "data" / "teams.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"teams": teams}, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"{len(teams)} times gerados em {out}")


if __name__ == "__main__":
    main()