"""FM27 live reader: find every player in the running game and read their data.

Read-only. All structure knowledge lives in the constants below, so a game patch means
updating one place. The player class is located by its RTTI name, not a fixed address.

Offsets were mapped by matching memory against known player stats; percentages quoted
are match rates over thousands of players on build 6A229F1E-1D8D3000.
"""
import datetime as dt
import struct
import time
from dataclasses import dataclass

from game import engine_build
from rtti import class_vtables
from winproc import Process


@dataclass(frozen=True)
class Profile:
    """What differs between game versions; everything else below is shared."""
    name: str
    p_stats: int              # player -> stats link
    stats_to_start: int       # link target -> stats object
    human_subobject: int
    keeper_saves_summed: bool = False  # saves = held + parried + tipped, per competition
    partial_records: bool = False      # some competitions keep only a reduced record
    clock_date: int | None = None      # TRANSFER_MANAGER -> today, for versions where P_UPDATED lags
    team_rosters: bool = False         # each team lists its players (senior, reserves, age groups)
    every_player: bool = False         # also read player-staff records and generated players


# keyed by engine build id (see game.py); an unknown build uses the newest profile and gets a warning
PROFILES = {
    "6A229F1E-1D8D3000": Profile("FM26", 0x248, -0x88, 0x478),
    "6ADFB11C-19E69000": Profile("FM27", -0x180, 0x20, 0x468, keeper_saves_summed=True, partial_records=True, clock_date=0x7F4, team_rosters=True, every_player=True),
    # Store update 0.9.2409.0: same layout, checked on game screens (Messi, Son, Weverton) on 2026-11-09
    "6AE563A1-175DA000": Profile("FM27 0.9.2409", -0x180, 0x20, 0x468, keeper_saves_summed=True, partial_records=True, clock_date=0x7F4, team_rosters=True, every_player=True),
}
LATEST = "6AE563A1-175DA000"

PLAYER_CLASS = ".?AVACTUAL_PLAYER@db@@"
PLAYER_SUBOBJECT = 0x288  # all player offsets are relative to this sub-object's vtable
STAFF_PLAYER_CLASS = ".?AVACTUAL_PLAYER_AND_NON_PLAYER@db@@"  # a player who also has a staff record
STAFF_PLAYER_SUBOBJECT = 0x380
STAFF_PLAYER_SHIFT = 0xF8  # its staff data pushes every negative player offset this much further back
VIRTUAL_CLASS = ".?AVVIRTUAL_PLAYER@db@@"
LOAN_CLASS = ".?AVLOAN_CONTRACT@db@@"
HUMAN_CLASS = ".?AVHUMAN_NON_PLAYER@db@@"   # a human manager (you)
CLOCK_CLASS = ".?AVTRANSFER_MANAGER@@"      # one per game; ticks with the date on screen
TEAM_CLASS = ".?AVTEAM@db@@"
HUMAN_CONTRACT = 0x80

# --- player sub-object (P = address of the sub-object) ---------------------------
P_BEFORE, P_AFTER = 0x140, 0x2A0         # one read covers [P - BEFORE, P + AFTER)
P_ID, P_UID, P_UID2 = 0x08, 0x0C, 0x10
P_FULL_NAME, P_FIRST, P_LAST, P_COMMON = 0x40, 0x50, 0x58, 0x60
P_NATION, P_DOB, P_CONTRACT, P_LOANS = 0x68, 0x88, 0xA8, 0xB0
P_UPDATED = 0x11C                        # a per-player date; its max across players = today
P_POS = -0x138                          # 15 x u8 (1-20): GK SW DL DC DR DM ML MC MR AML AMC AMR ST WBL WBR
P_LEFT, P_RIGHT = -0x111, -0x110         # u8, 1-100 (x5 of the 1-20 shown in game)
P_HEIGHT, P_VALUE, P_CA, P_PA = -0x5A, -0x54, -0x24, -0x22
# Attributes: 54 x u8 from -0x129 (right after the position ratings), stored x5: the game shows value / 5.
# Order proven on FM27's player screens (Hull City save, 13/7/2026): 182 values matched, 108 of them predicted blind.
P_ATTRS = -0x129
ATTRS = ["Crossing", "Dribbling", "Finishing", "Heading", "Long Shots", "Marking", "Off The Ball", "Passing",
         "Penalty Taking", "Tackling", "Vision", "Handling", "Aerial Reach", "Command Of Area", "Communication", "Kicking",
         "Throwing", "Anticipation", "Decisions", "One On Ones", "Positioning", "Reflexes", "First Touch", "Technique",
         "Left Foot", "Right Foot", "Flair", "Corners", "Teamwork", "Work Rate", "Long Throws", "Eccentricity",
         "Rushing Out", "Punching", "Acceleration", "Free Kick Taking", "Strength", "Stamina", "Pace", "Jumping Reach",
         "Leadership", "Dirtiness", "Balance", "Bravery", "Consistency", "Aggression", "Agility", "Important Matches",
         "Injury Proneness", "Versatility", "Natural Fitness", "Determination", "Composure", "Concentration"]
HIDDEN_ATTRS = {"Dirtiness", "Consistency", "Important Matches", "Injury Proneness", "Versatility"}  # read, not shown
# what is exported (x5, 1-100), in this order: ATTR_NAMES in FMMT 27.html must match. Feet are exported as "foot".
SHOWN_ATTRS = [a for a in ATTRS if a not in HIDDEN_ATTRS and a not in ("Left Foot", "Right Foot")]
P_PERSONALITY = 0x70                    # 8 x u8: adaptability ambition loyalty pressure professionalism sportsmanship temperament controversy

CONTRACT_TEAM, CONTRACT_WAGE, CONTRACT_START, CONTRACT_END = 0x10, 0x20, 0x44, 0x48
CLUB_UID = 0x0C
TEAM_CLUB, TEAM_COMP = 0x30, 0x50
TEAM_SECOND, TEAM_AGE, TEAM_ROSTER = 0x28, 0x2C, 0x38   # not 0 = a second team; age limit (100 = none); begin/end of its player pointers
CLUB_LONG, CLUB_SHORT = 0xC0, 0xC8
COMP_NAME = 0x40
NATION_CODE, NATION_NAME = 0x28, 0x18

# --- season stats -----------------------------------------------------------------
SCOPES = {"competitive": 0x28, "league": 0x08, "all": 0x30, "cups": 0x10, "continental": 0x18}
# scopes that add up from single competitions; +0x00 holds friendlies, +0x20 internationals
COMPETITIONS = {"competitive": (0x08, 0x10, 0x18), "all": (0x00, 0x08, 0x10, 0x18, 0x20)}

# season entry (0x20 bytes): +0 -> record
ENTRY = {"rating_sum": (0x08, "H"), "minutes": (0x0A, "H"), "starts": (0x0C, "B"), "subs": (0x0D, "B"),
         "rated": (0x0E, "B"),  # appearances that received a rating; avg = rating_sum / (10 * rated)
         "goals": (0x0F, "B"), "assists": (0x10, "B"), "conceded": (0x11, "B"), "pens_taken": (0x12, "B"),
         "pens_scored": (0x13, "B"), "motm": (0x14, "B"), "red": (0x15, "B"), "yellow": (0x16, "B"),
         "clean_sheets": (0x17, "B")}

# stats record (0x78 bytes of u16; "h" = signed). Slots marked * hold goalkeeper stats for keepers.
RECORD = {"pas_att": 0x08, "pas_cmp": 0x0A, "tck_att": 0x0C, "tck_won": 0x0E,      # * pens faced / saved
          "hdr_att": 0x10, "hdr_won": 0x12,                                         # * saves held / parried
          "drb": 0x14, "fouls": 0x16, "fouls_won": 0x18, "shots": 0x1A, "sot": 0x1C,
          "distance10": 0x2E, "offsides": 0x30, "saves_tipped": 0x32, "op_crs_cmp": 0x34,
          "kp": 0x36, "tck_key": 0x38, "hdr_key": 0x3A, "int": 0x3C, "ccc": 0x3E, "blocks": 0x40,
          "poss_lost": 0x44, "poss_won": 0x46, "xg100": 0x48, "xa100": 0x4A, "clr": 0x4C,
          "fk": 0x50, "goals_out": 0x52, "op_crs_att": 0x5A, "shots_out": 0x5C, "xgp100": (0x5E, "h"),
          "sprints": 0x60, "pr_passes": 0x64, "pres_att": 0x66, "pres_cmp": 0x68, "op_kp": 0x6A,
          "npxg100": 0x6C, "crs_att": 0x70, "crs_cmp": 0x72, "shots_blk": 0x74, "hdr_lost": 0x76}

POS_NAMES = ["GK", "SW", "DL", "DC", "DR", "DM", "ML", "MC", "MR", "AML", "AMC", "AMR", "ST", "WBL", "WBR"]
ACCOMPLISHED = 15  # FM lists natural (20) and accomplished (15+) positions


def unpack_date(raw: int):
    doy, year = raw & 0xFFFF, raw >> 16
    if not (1 <= doy <= 366 and 1850 < year < 2200):
        return None
    return dt.date(year, 1, 1) + dt.timedelta(days=doy - 1)


def position_string(r: list[int]) -> str:
    """FM-style position text, e.g. 'D (RC), DM, M (C)'."""
    ok = {n for n, v in zip(POS_NAMES, r) if v >= ACCOMPLISHED}
    if not ok and r:
        ok = {POS_NAMES[max(range(len(r)), key=r.__getitem__)]}
    parts = []
    if "GK" in ok:
        parts.append("GK")
    for grp, pre in (("D", "D"), ("WB", "WB")):
        sides = "".join(s for s in "RLC" if f"{pre}{s}" in ok)
        if sides:
            parts.append(f"{grp} ({sides})")
    if "DM" in ok:
        parts.append("DM")
    for grp in ("M", "AM"):
        sides = "".join(s for s in "RLC" if f"{grp}{s}" in ok)
        if sides:
            parts.append(f"{grp} ({sides})")
    if "ST" in ok:
        parts.append("ST (C)")
    return ", ".join(parts)


def pointer_hits(buf: bytes, base: int, pat: bytes) -> list[int]:
    """Addresses of an 8-aligned pointer. find() tests a pattern's last byte first, and a pointer
    ends in zeros, the commonest bytes on the heap, so search on its first bytes: 8x faster."""
    needle, out = pat[:5], []
    i = buf.find(needle)
    while i != -1:
        if i % 8 == 0 and buf.startswith(pat, i):
            out.append(base + i)
        i = buf.find(needle, i + 1)
    return out


class Game:
    def __init__(self):
        self.p = Process.attach()
        self.build = engine_build(self.p)
        m = self.build.module
        self.lo, self.hi = m.base, m.base + m.size
        self.known_build = self.build.id in PROFILES
        self.prof = PROFILES.get(self.build.id, PROFILES[LATEST])
        tables = class_vtables(self.p, self.build, [PLAYER_CLASS, LOAN_CLASS, HUMAN_CLASS, CLOCK_CLASS, TEAM_CLASS, STAFF_PLAYER_CLASS, VIRTUAL_CLASS])
        vtables = tables.__getitem__
        vts = [v for v, off in vtables(PLAYER_CLASS).items() if off == PLAYER_SUBOBJECT]
        if not vts:
            raise RuntimeError("ACTUAL_PLAYER class not found - unsupported game build")
        self.player_vt = vts[0]
        self.staff_vt = next((v for v, off in vtables(STAFF_PLAYER_CLASS).items() if off == STAFF_PLAYER_SUBOBJECT), None) if self.prof.every_player else None
        self.virtual_vt = next((v for v, off in vtables(VIRTUAL_CLASS).items() if off == 0), None)
        self._staff_players: set[int] = set()
        self.unlisted = 0  # squad-list entries that match no player we read
        self.loan_vt = next(iter(vtables(LOAN_CLASS)), None)
        self.human_vt = next((v for v, off in vtables(HUMAN_CLASS).items() if off == self.prof.human_subobject), None)
        self._players: list[int] | None = None
        self._humans: list[int] | None = None
        self.clock_vt = next((v for v, off in vtables(CLOCK_CLASS).items() if off == 0), None) if self.prof.clock_date else None
        self._clock: int | None = None
        self.team_vt = next((v for v, off in vtables(TEAM_CLASS).items() if off == 0), None) if self.prof.team_rosters else None
        self._teams: list[int] = []
        self._team_of: dict = {}
        self._str: dict[int, str | None] = {}
        self._once_memo: dict = {}

    def close(self):
        self.p.close()

    # ---- discovery ----------------------------------------------------------
    def players(self, refresh: bool = False) -> list[int]:
        """Addresses of every player sub-object, staff-type players included (one pass over the heap, which also finds the clock, the human managers and the teams)."""
        if self._players is not None and not refresh:
            return self._players
        self._clock = None
        self._str.clear()  # a different save reuses the same addresses
        pat = struct.pack("<Q", self.player_vt)
        human_pat = struct.pack("<Q", self.human_vt) if self.human_vt else None
        clock_pat = struct.pack("<Q", self.clock_vt) if self.clock_vt else None
        team_pat = struct.pack("<Q", self.team_vt) if self.team_vt else None
        staff_pat = struct.pack("<Q", self.staff_vt) if self.staff_vt else None
        out, staff, humans, teams = [], [], [], []
        for base, buf in self.p.chunks(self.p.regions(private_only=True), overlap=0):
            out += pointer_hits(buf, base, pat)
            if staff_pat:
                staff += pointer_hits(buf, base, staff_pat)
            if human_pat:
                humans += pointer_hits(buf, base, human_pat)
            if team_pat:
                teams += pointer_hits(buf, base, team_pat)
            if clock_pat and self._clock is None:
                self._clock = next(iter(pointer_hits(buf, base, clock_pat)), None)
        self._staff_players = {a for a in staff if self._live(a, STAFF_PLAYER_SHIFT)}
        live = [a for a in sorted(set(out)) if self._live(a, 0)]
        self._players = sorted(live + list(self._staff_players))
        self._humans = humans
        self._teams = teams
        return self._players

    def _live(self, a: int, shift: int) -> bool:
        """Freed records stay on the heap with a broken id. Generated players never get the second id,
        so for them a contract and a stats link show the record is in use."""
        b = self.p.read(a + P_ID, 12)
        if not b:
            return False
        _id, uid, uid2 = struct.unpack("<III", b)
        if not uid:
            return False
        if uid == uid2:
            return True
        return (self.prof.every_player and not uid2 and bool(self.p.ptr(a + P_CONTRACT))
                and bool(self.p.ptr(a + self.prof.p_stats - shift)))

    def shift(self, player: int) -> int:
        return STAFF_PLAYER_SHIFT if player in self._staff_players else 0

    def today(self) -> dt.date | None:
        best = self._clock_date()
        if best:
            return best
        for a in self.players():
            d = unpack_date(self.p.u32(a + P_UPDATED) or 0)
            if d and (best is None or d > best):
                best = d
        return best

    def _clock_date(self) -> dt.date | None:
        """The date on the game's screen. None when this version has no known location for it."""
        if not self.clock_vt:
            return None
        self.players()
        if self._clock and self.p.u64(self._clock) != self.clock_vt:
            self.players(refresh=True)
        d = unpack_date(self.p.u32(self._clock + self.prof.clock_date) or 0) if self._clock else None
        return d if d and d.year >= 2000 else None  # 1/1/1900 is the game's "no date"

    # ---- strings ------------------------------------------------------------
    def lstr(self, a: int | None) -> str | None:
        """String stored as [u32 length][utf-8 bytes]; cached by address."""
        if not a:
            return None
        if a in self._str:
            return self._str[a]
        s = None
        n = self.p.u32(a)
        if n and n <= 400:
            b = self.p.read(a + 4, n)
            s = b.decode("utf-8", "replace") if b else None
        self._str[a] = s
        return s

    def _once(self, key, read):
        """What many players share (names, teams, clubs, nations) is read once per load."""
        memo = self._once_memo
        if key not in memo:
            memo[key] = read()
        return memo[key]

    def name_ref(self, a: int | None) -> str | None:
        """Name-table entry: first field points at an lstr."""
        return self._once(("name", a), lambda: self.lstr(self.p.ptr(a))) if a else None

    def club_name(self, club: int | None) -> str | None:
        return (self.lstr(self.p.ptr(club + CLUB_SHORT)) or self.lstr(self.p.ptr(club + CLUB_LONG))) if club else None

    def club_info(self, club: int | None) -> tuple:
        return self._once(("club", club), lambda: (self.club_name(club), self.p.u32(club + CLUB_UID))) if club else (None, None)

    def nation_info(self, nation: int | None) -> tuple:
        if not nation:
            return None, None
        return self._once(("nation", nation), lambda: (self.lstr(self.p.ptr(nation + NATION_CODE)), self.lstr(self.p.ptr(nation + NATION_NAME))))

    def team_club(self, team: int | None) -> int | None:
        return self._once(("team", team), lambda: self.p.ptr(team + TEAM_CLUB)) if team else None

    def division(self, team: int | None) -> str | None:
        def read():
            comp = self.p.ptr(team + TEAM_COMP)
            return self.lstr(self.p.ptr(comp + COMP_NAME)) if comp else None
        return self._once(("division", team), read) if team else None

    # ---- the human manager ----------------------------------------------------
    def my_clubs(self) -> list[dict]:
        """Clubs managed by human players: each HUMAN_NON_PLAYER holds its job contract at
        +HUMAN_CONTRACT (same layout as a player contract: +0x10 is the team)."""
        self.players()
        out = []
        for h in self._humans:
            try:
                c = self.p.ptr(h + HUMAN_CONTRACT)
                team = self.p.ptr(c + CONTRACT_TEAM) if c else None
                club = self.p.ptr(team + TEAM_CLUB) if team else None
                name = self.club_name(club)
            except (OSError, struct.error, TypeError):
                continue
            if name and not any(o["name"] == name for o in out):
                out.append({"name": name, "uid": self.p.u32(club + CLUB_UID)})
        return out

    # ---- raw structures -----------------------------------------------------
    def stats_object(self, player: int) -> int | None:
        q = self.p.ptr(player + self.prof.p_stats - self.shift(player))
        return q + self.prof.stats_to_start if q else None

    def keeper_saves(self, player: int, scope: str) -> dict | None:
        """Saves, conceded, minutes and xG prevented from only the competitions with real save data, plus clean
        sheets from every competition (the combined entry also counts friendlies for some keepers).
        Others hold a near-empty row (2 saves against 34 conceded) that would wreck the save rate, so a
        competition counts only with at least one save per goal conceded. None when a version needs none of this."""
        if not self.prof.keeper_saves_summed:
            return None
        so = self.stats_object(player)
        if not so:
            return None
        out = {"saves": 0, "conceded": 0, "minutes": 0, "xgp100": 0, "clean_sheets": 0}
        for slot in COMPETITIONS.get(scope, (SCOPES[scope],)):
            e = self.p.ptr(so + slot)
            eb = self.p.read(e, 0x20) if e else None
            rb = self.p.read(struct.unpack_from("<Q", eb, 0)[0], 0x78) if eb else None
            if eb:
                out["clean_sheets"] += eb[ENTRY["clean_sheets"][0]]
            if not rb:
                continue
            saves = sum(struct.unpack_from("<H", rb, RECORD[k])[0] for k in ("hdr_att", "hdr_won", "saves_tipped"))
            conceded = eb[ENTRY["conceded"][0]]
            if saves and saves >= conceded:
                out["saves"] += saves
                out["conceded"] += conceded
                out["minutes"] += struct.unpack_from("<H", eb, ENTRY["minutes"][0])[0]
                # FM27 keeps the xG faced in this slot; prevented = faced - conceded
                out["xgp100"] += struct.unpack_from("<H", rb, RECORD["op_crs_cmp"])[0] - conceded * 100
        return out

    def season_total(self, player: int, slots) -> tuple[dict | None, dict]:
        """Entry and record added up over several competitions."""
        e, rec = None, dict.fromkeys(RECORD, 0)
        so = self.stats_object(player)
        for slot in slots if so else ():
            entry = self.p.ptr(so + slot)
            eb = self.p.read(entry, 0x20) if entry else None
            if not eb:
                continue
            one = {k: struct.unpack_from("<" + f, eb, o)[0] for k, (o, f) in ENTRY.items()}
            e = {k: e[k] + v for k, v in one.items()} if e else one
            rb = self.p.read(struct.unpack_from("<Q", eb, 0)[0], 0x78)
            for k, spec in RECORD.items() if rb else ():
                off, f = spec if isinstance(spec, tuple) else (spec, "H")
                rec[k] += struct.unpack_from("<" + f, rb, off)[0]
        return e, rec

    def season_entry(self, player: int, slot: int = SCOPES["competitive"]) -> int | None:
        so = self.stats_object(player)
        return (self.p.ptr(so + slot) or None) if so else None

    def current_team(self, home: int | None, loans: int | None, today: dt.date | None) -> int | None:
        """The team the player plays for: an active loan's team, else the contract's team (`home`).
        `loans` (player+0xB0) points at a node whose first field is the LOAN_CONTRACT."""
        loan = self.p.ptr(loans) if loans else None
        lb = self.p.read(loan, 0x50) if loan else None
        if lb and struct.unpack_from("<Q", lb, 0)[0] == self.loan_vt:
            start = unpack_date(struct.unpack_from("<I", lb, CONTRACT_START)[0])
            stop = unpack_date(struct.unpack_from("<I", lb, CONTRACT_END)[0])
            if not today or not start or not stop or start <= today <= stop:
                t = struct.unpack_from("<Q", lb, CONTRACT_TEAM)[0]
                if t:
                    return t
        return home

    def team_rosters(self) -> dict:
        """(player, club) -> the team he is listed in. A loanee is listed by both clubs."""
        out, players, unlisted = {}, set(self._players or ()), set()
        for t in self._teams:
            d = self.p.read(t, TEAM_ROSTER + 0x10)
            first, end = struct.unpack_from("<QQ", d, TEAM_ROSTER) if d else (0, 0)
            ids = self.p.read(first, end - first) if first and 0 < end - first <= 0x1000 else None
            if not ids:
                continue
            age = d[TEAM_AGE]
            name = f"U{age}" if age < 100 else "Reserves" if struct.unpack_from("<I", d, TEAM_SECOND)[0] else "Senior Team"
            club = struct.unpack_from("<Q", d, TEAM_CLUB)[0]
            for p in struct.unpack(f"<{len(ids) // 8}Q", ids):
                a = next((p + s for s in (PLAYER_SUBOBJECT, STAFF_PLAYER_SUBOBJECT) if p + s in players), None)
                if a:
                    out[a, club] = name
                else:
                    unlisted.add(p)
        self.unlisted = sum(self.p.u64(p) != self.virtual_vt for p in unlisted)
        return out

    # ---- one player ---------------------------------------------------------
    def read_player(self, a: int, today: dt.date, scope: str = "competitive", require_minutes=True):
        slot = SCOPES[scope]
        entry = self.season_entry(a, slot)
        eb = self.p.read(entry, 0x20) if entry else None
        e = {k: struct.unpack_from("<" + f, eb, o)[0] for k, (o, f) in ENTRY.items()} if eb else None
        if require_minutes and scope != "all" and (not e or not e["minutes"]):
            return None
        rec = dict.fromkeys(RECORD, 0)  # some entries have no detailed record: count as zeros
        if eb:
            rp = struct.unpack_from("<Q", eb, 0)[0]
            rb = self.p.read(rp, 0x78) if rp else None
            if rb:
                for k, spec in RECORD.items():
                    off, f = spec if isinstance(spec, tuple) else (spec, "H")
                    rec[k] = struct.unpack_from("<" + f, rb, off)[0]
        if scope == "all" and self.prof.partial_records:   # FM27's own "all" entry leaves out friendlies and some loans
            e, rec = self.season_total(a, COMPETITIONS["all"])

        if require_minutes and (not e or not e["minutes"]):
            return None

        back = self.shift(a)
        start = P_BEFORE + back
        b = self.p.read(a - start, start + P_AFTER)
        if not b:
            return None
        u8 = lambda o: b[start + o]
        u32 = lambda o: struct.unpack_from("<I", b, start + o)[0]
        ptr = lambda o: struct.unpack_from("<Q", b, start + o)[0]
        before = lambda o: o - back  # the negative offsets, which a staff record pushes back

        common = self.name_ref(ptr(P_COMMON))
        first, last = self.name_ref(ptr(P_FIRST)), self.name_ref(ptr(P_LAST))
        name = common or " ".join(x for x in (first, last) if x) or self.lstr(ptr(P_FULL_NAME)) or "?"

        nation = ptr(P_NATION)
        contract = ptr(P_CONTRACT)
        cb = self.p.read(contract, 0x50) if contract else None
        home = struct.unpack_from("<Q", cb, CONTRACT_TEAM)[0] if cb else None   # club holding the contract
        team = self.current_team(home, ptr(P_LOANS), today)
        club, owner = self.team_club(team), self.team_club(home)
        club_name, club_uid = self.club_info(club)
        owner_name, owner_uid = self.club_info(owner)
        nat, nation_name = self.nation_info(nation)
        dob = unpack_date(u32(P_DOB))
        age = None
        if dob and today:
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        pos = list(b[start + before(P_POS): start + before(P_POS) + 15])
        lf, rf = u8(before(P_LEFT)), u8(before(P_RIGHT))
        foot = "Either" if abs(lf - rf) <= 10 and min(lf, rf) >= 70 else ("Left" if lf > rf else "Right")
        return {
            "uid": u32(P_UID), "name": name, "pos": pos, "position": position_string(pos), "age": age,
            "dob": dob.isoformat() if dob else None,
            "nat": nat,
            "nation": nation_name,
            "club": club_name,
            "club_uid": club_uid,
            "owner": owner_name if owner != club else None,
            "owner_uid": owner_uid if owner and owner != club else None,
            "division": self.division(team),
            "team": self._team_of.get((a, club)),
            "owner_team": self._team_of.get((a, owner)) if owner != club else None,
            "wage": struct.unpack_from("<I", cb, CONTRACT_WAGE)[0] if cb else None,
            # the game stores 1900-01-02 when a contract has no end date
            "contract_end": (lambda d: d.isoformat() if d and d.year >= 1950 else None)(unpack_date(struct.unpack_from("<I", cb, CONTRACT_END)[0])) if cb else None,
            "value": u32(before(P_VALUE)), "height": u8(before(P_HEIGHT)), "foot": foot,
            "ca": u8(before(P_CA)), "pa": u8(before(P_PA)),
            "attrs": [v for n, v in zip(ATTRS, b[start + before(P_ATTRS): start + before(P_ATTRS) + len(ATTRS)]) if n in SHOWN_ATTRS],
            "personality": list(b[start + P_PERSONALITY: start + P_PERSONALITY + 8]),
            "season": e, "record": rec,
            "keeper": self.keeper_saves(a, scope) if pos[0] >= ACCOMPLISHED and max(pos) == pos[0] else None,
            "partial_detail": self.prof.partial_records,
        }

    def read_all(self, scope: str = "competitive", require_minutes=True, progress=None):
        today = self.today()
        out = {}
        ps = self.players()
        self._once_memo.clear()  # the game may have moved on since the last load
        self._team_of = self.team_rosters()
        for i, a in enumerate(ps):
            try:
                r = self.read_player(a, today, scope, require_minutes)
            except (struct.error, TypeError, IndexError):
                r = None
            # a player can leave an old copy on the heap: keep the one on a squad list
            if r and (r["uid"] not in out or (r["team"] and not out[r["uid"]]["team"])):
                out[r["uid"]] = r
            if progress and i % 2000 == 0:
                progress(i, len(ps))
        return today, list(out.values())


if __name__ == "__main__":
    import json
    import sys
    t = time.time()
    g = Game()
    n = len(g.players())
    print(f"build {g.build.id}: {n} players in {time.time() - t:.1f}s")
    t = time.time()
    today, rows = g.read_all(sys.argv[1] if len(sys.argv) > 1 else "competitive")
    print(f"game date {today}; {len(rows)} players with minutes read in {time.time() - t:.1f}s")
    top = sorted(rows, key=lambda r: -(r["wage"] or 0))[:5]
    for r in top:
        print(json.dumps({k: r[k] for k in ("name", "age", "position", "club", "division", "nat", "wage", "value", "contract_end")}, ensure_ascii=False))
