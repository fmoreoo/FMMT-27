# FMMT 27

FMMT stands for Football Manager Moneyball Tool. It is a Moneyball-style scouting tool for Football Manager 27. It reads player stats straight from the running game with one click, so there is no exporting or spreadsheet juggling. It then shows every stat as a percentile against comparable players, using the stat list from Fmplaya's FM24 Statistics Spreadsheet (see [Credits](#credits)).

The tool has two sections at the top: **My Club** and **World Scout**.

- **My Club** has four sub-tabs:
  - **Squad**: every player contracted to your club, including youth and reserves. Players out on loan are marked "On loan at X", and players on loan to you are included. In FM27 you can view All players or one team at a time: Senior Team, Reserves or an age group such as U21 or U18. Position buttons narrow the list further: pick one or more, and a player needs any of them.
  - **Shortlist**: players you have starred, grouped into folders you name with the + button.
  - **Compare**: compare up to 3 players drawn from your squad, your shortlist, or both, with radar, pizza and bar charts. A Folder dropdown limits the shortlist to one folder, or All folders to compare across them.
  - **Graphs**: the World Scout graphs, showing only your squad and/or shortlist players who have minutes, with age, minutes, foot and position filters. Shortlisted players show as a star, with their names on enlarged graphs.
- Your club is detected automatically from the save (the game's human-manager record). A "My club" picker in Squad lets you choose another club. That choice is remembered for the same save.
- **World Scout** has five tabs: Scout, Compare, All players, Graphs and Rank. Graphs can be filtered by league, club, minutes, age, market value and foot, combined with AND or OR. Players with no stored value don't match a market value filter. Custom graphs can also plot season totals (goals, assists, goals + assists, non-penalty goals, xG, xA, appearances). Rank orders players by average rating or by any stat's percentile, optionally multiplied by a league weight. **Moneyball** lists players outside your club whose market value is half their fair value or less (see below).

## Recommendations

Moneyball and Tactical fit use only senior-team players with 900 or more minutes (B and youth teams carry their parent club's league, so they'd be valued against the wrong market). Sell/Keep judges your players from the percentile pool's minimum (300 minutes unless changed). They are the tool's own reading of the stats and attributes, a prompt for your decision, not an order. They don't use potential or your tactic's roles.

- **Attributes** are read from the game for every player. The numbers are shown on the profiles of your own players only (the game shows ranges for players your scouts don't know well), but every player's scores use them. Hidden attributes such as consistency are not used.
- **Ability** is a weighted average of the attributes that matter for a position, on the 1-20 scale, for centre-backs, wide defenders and holding midfielders, midfielders and number 10s, strikers, and keepers. A player gets a score for each position they can play. The weights and age benchmarks come from [fm-scoring](https://github.com/jamiebolden/fm-scoring) by Jamie Bolden (MIT licence, see `THIRD_PARTY_NOTICES.md`), tuned toward harvestgreen22's FM27 attribute testing. Which FM position uses which score is this tool's own mapping. Scout, Squad and Shortlist show the best score as **Ability**.
- **vs Age** compares the best ability score with what's typical for the player's age: 100% means on track for a top Championship or low Premier League player once developed.

- **Performance** is the average of a position group's key stat percentiles (the stats on the profile chart), ranked within the group, so 50 is the group's median. It follows the percentile pool and "Percentiles against" in Player search.
- **Fair value** is what this save's market pays for a player's output: a least-squares fit of market value against performance, age and the league's typical value, made for each position group.
- **Moneyball** (World Scout) lists players outside your club valued at half their fair value or less, most undervalued first. Filter by position group, age, league, maximum value and wage, foot, minimum performance and minimum fair value (£0.25M by default, so near-worthless matches stay out). The game's value drops sharply as a contract runs out, so players with a few months left often top the list; the Contract left column shows it, they may be available cheaply or on a free, and "Min contract left" hides them. **Stats vs ability** is the performance percentile minus the ability percentile within the position group: well above 0, the output beats what the attributes suggest (a bargain, or a hot streak).
- **Tactical fit** (My Club) shows a formation filled with your most-played player for each slot. Change any slot and the choice is remembered for your club. Click a slot to see players elsewhere who can play it: **Upgrade** (8+ performance points better than yours), **Replacement** (within 8) or **Downgrade** (8+ worse), with a style match that compares the same stats one by one, and each candidate's ability for the slot against your player's. The same filters apply, plus a minimum style match. Tick **Left foot** on a slot to fill and search it with left-footed or two-footed players only. Performance doesn't allow for league strength, and weaker leagues make percentiles look better, so the league filter starts at "My league or stronger" (by the league ranking used in Rank).
- **Sell/Keep** (My Club) gives each player whose contract is with your club one verdict with its reasons, checked in this order: under the pool's minimum minutes, players 23 and under are judged on attributes: **Develop** at vs Age 100% or more, **Loan out** from 85%, otherwise **Release**, and older players get **Not enough data**; a contract ending within 12 months gives **Renew** (starter or backup) or **Sell now**; valued at twice their fair value or more gives **Sell high** (unless a starter under 28); not a starter or first backup gives **Surplus**; 29 or older (keepers 33) and not a starter gives **Sell before decline**; anyone else is **Keep**. Starters are your Tactical fit XI.

Click the ☆ next to any player in World Scout (or "☆ Shortlist" in a player's profile) and choose a folder. Click ★ to move them to another folder or remove them. Each player sits in one folder, and players with no folder show as Unfiled. The shortlist is kept between sessions, stored by the game's player ID.

Click any player to open their profile, laid out like the game's player screen: positions on a pitch, every stat with its percentile, a season summary including xG and xG/90, and radar, pizza and bar charts. The charts compare the player with the average for their position among senior players who reach the percentile pool, showing the real values on each chart. "Percentiles against" at the top of the profile sets the group for the whole profile, so the stat percentiles and chart always match. It starts from your Player search choice, and you can switch it to all leagues, the Top 5, the player's own league, your league or any one league. The choice stays for the next profiles you open until you set it back to "As in Player search". A league with fewer than 5 such players shows a message instead of a chart.

In Compare and Graphs, type a name to find a player.

## Requirements

- Windows 10 or 11
- Football Manager 27: the current Microsoft Store version 0.9.2435.0 (engine build 6AE8CF77-17969000), or the earlier 0.9.2409.0 (6AE563A1-175DA000) and 6ADFB11C-19E69000. Football Manager 26 (game version 26.3.2). The older game is still supported: the tool picks the right settings for the build it finds.
- Microsoft Edge (included with Windows) for the app window
- To run from source: Python 3.12 or newer. The reader uses only the standard library.

## How to use

1. Open FM27 and load your save.
2. Start the tool:
   - **Installer:** download `FMMT 27 Setup.exe` from the Releases page and run it. It needs no admin password, adds FMMT 27 to the Start Menu, and can be removed from Windows' Installed Apps. Uninstalling asks whether to also delete your settings and shortlist. No Python needed.
   - **Single exe:** download `FMMT 27.exe` from the Releases page and double-click it. Nothing is installed.
   - **From source:** double-click `Start FMMT 27.bat`.

   The tool opens in its own app window (Microsoft Edge's app mode: no tabs or address bar, with a private profile separate from your browsing). Closing that window stops the reader. Opening the exe again while it runs just brings the window back. If Edge is missing, it falls back to a small control window plus your default browser.
3. Choose which stats to use:
   - All competitive games (the default)
   - League only
   - Domestic cups
   - Continental
   - Everything, including friendlies and internationals

   Then click "Load from game". With 30,000 players a load takes about 10 seconds. The very first load after a game patch takes about 5 seconds longer, while the tool finds the game's data structures and saves their locations. A bigger database takes longer. The header shows its progress.
4. After playing more matches in FM27, click "Reload from game" to refresh the data. It finds the players again, so it also picks up a different save. The header shows the in-game date and the time of the last read. Changing the Stats selector in the header reloads it automatically.

## Settings

Click the cog at the top right to open Settings. You can pick a theme (Light, Dark, Purple or Green), a header font, a body font and the text size. Changes apply straight away and are remembered. Reset to defaults returns to Green with the original fonts. Barlow and Barlow Condensed need an internet connection; without one they fall back to Segoe UI. The other fonts come with Windows.

## Every player is listed

- Every player in the game is loaded (about 30,000 to over 120,000, depending on the save's database), including players with no minutes or incomplete stats. Missing values show as "–", and those players sort to the bottom.
- Foot filters (Left, Right or Either) are in Squad, Shortlist, Player search, All players, Graphs and Rank. They match the Foot shown on the player's profile, so Left doesn't include Either. They only change who is listed, not percentiles.
- Percentiles are measured against the "percentile pool": players with at least 300 minutes. You can change that number in Player search ("Percentile pool"). The "Minutes between" boxes in Player search are only a filter and are empty by default.
- "Percentiles against" in Player search chooses which leagues the pool is drawn from: all leagues (the default), the Top 5 leagues, your club's league, or any one league. Every player is then placed among that group's players, wherever they play, so with the Top 5 chosen a player from a smaller league is measured on a Top 5 scale. It applies to every tab. If the group has fewer than 20 values for a stat (common in leagues that keep a reduced record), that stat uses all leagues instead and is marked † on profiles. A warning shows when fewer than 20 players in a position group reach the pool there.
- Players with some minutes but fewer than the pool's minimum are still placed within the pool. They are shown faded as a small sample and rank after pool players.

## Building the exe and installer

- Install PyInstaller: `python -m pip install pyinstaller`
- For the installer, also install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
- Run `Build exe.bat`. The exe and installer are written to the `dist` folder. Without Inno Setup you still get the exe.
- For a new release, raise `AppVersion` in `installer.iss` and leave `AppId` unchanged, so the installer replaces the old version.

## How it works

- `reader/server.py` runs a local web server on 127.0.0.1 only. Nothing leaves your computer.
- `reader/fm27.py` opens the `fm.exe` process read-only. It cannot change the game or your save. It finds every player object by its C++ class name (ACTUAL_PLAYER) and reads stats, contract, club and league.
- It also finds the human manager object (HUMAN_NON_PLAYER) to work out which club you manage.
- `reader/export.py` turns this into the column names the scoring page uses (the same names as an FM24 stats export).
- `FMMT 27.html` is the whole interface: percentiles, tables and charts.
- `reader/classes.py` lists the game's C++ class names, which helps when mapping new structures.
- `reader/sanity.py` checks that the reader still reads the game correctly (see below).

## Checking the reader after a game update

With FM27 running and a save loaded, run:

```
cd reader
python sanity.py
```

It reads every player and checks that each field looks plausible: ages and heights, contract dates, minutes that fit the appearances, completed actions never above attempts, sensible pass completion and distance, and that your club is found. Each check prints OK or FAIL with examples. If a game patch moved a field, the failing checks show which one, and its offset at the top of `reader/fm27.py` needs updating. Exit code 0 means everything passed.

## Limits

- Early in a season, many players have no minutes yet, so they have no stats until they play.
- Some players have no stored market value. The game shows a placeholder for them, so they appear as "–".
- Personality, playing style and weight are not read yet, so they show "–".
- Reserve and B-team players (about 0.6%) show their parent club and its league.
- The game shows Distance/90 at a tenth of the tool's figure (1.3 km against 13.1 km). The tool shows real distance: a full-match outfielder covers 9 to 13 km.
- The tool was checked on FM27 version 0.9.2435.0 (engine build id 6AE8CF77-17969000), version 0.9.2409.0 (6AE563A1-175DA000), the earlier FM27 build 6ADFB11C-19E69000 and FM26 build 26.3.2 (6A229F1E-1D8D3000). A game patch may move some fields. Memory offsets are constants at the top of `reader/fm27.py`, and what differs between versions is in `PROFILES` there, so a patch means updating them there. An unknown build uses the newest profile and shows a warning. Run `reader/sanity.py` to find out.
- In FM27 many competitions keep only a reduced record (passes, tackles, fouls, shots, xG, xA). Other stats show "–" for those players. The same applies to matches from before the save began: an outfielder averaging under 8.5 km per 90 is missing detail for part of their minutes, and those stats show "–" too, instead of being spread thinly over all their minutes. This affects most players in many leagues outside the Premier League, Bundesliga and Serie A. Players with reduced data tend to show more shots and tackles and fewer passes per 90 than players with full data, so compare them with care. Keeper save stats come only from competitions that store saves, so they can cover far fewer minutes than the player's total.
- If you manage a national team, no club is detected. Choose one with the "My club" picker.
- Expected goals prevented comes from the game's own stored value, which runs negative for most keepers, as it does in the game. Expected save % is worked out from it and runs high.
- The game shows a scouting range for market value, which is narrow for players you know well. The tool shows the single stored value, which can sit at either end of that range. No value is stored for some players ("–"), and the game lists some of them as "Not for Sale".
- Goals Outside Box shows "–" in FM27, because the stored value exceeds total goals for many players.
- All competitive games covers club competitions. Internationals count only in "Everything".
- The in-game date in FM27 is read from a value that moves with the game's date.

## Troubleshooting

- **"Can't reach the reader"**: start the exe (or the .bat file) again; with the .bat, keep its console window open.
- **"FM27 isn't running"**: open the game, load a save, then click Load again.
- You can also open the page directly from disk, as long as the reader is running.
- **Windows SmartScreen or antivirus warns about the installer or exe**: they are unsigned and the tool reads another program's memory (read-only), which some scanners flag. Choose More info > Run anyway, or run from source with the .bat instead.
- **Log file**: `%LOCALAPPDATA%\FMMT 27\reader.log`

## Support

FMMT 27 is free. If it helps your save, you can [buy me a coffee](https://buymeacoffee.com/fmoreo). The same link is on the tool's start screen and in Settings.

## Credits

- FMMT 27 is inspired by and built on the **FM24 Statistics Spreadsheet** by **Fmplaya**: [FM24 Statistics Spreadsheet (for those that love moneyball)](https://community.sports-interactive.com/forums/topic/580105-fm24-statistics-spreadsheet-for-those-that-love-moneyball/) on the Sports Interactive Community forums. The stat list and the default league weights come from it. Thank you, Fmplaya.
- The ability weights and age benchmarks come from [**fm-scoring**](https://github.com/jamiebolden/fm-scoring) by **Jamie Bolden** ([YouTube](https://www.youtube.com/@squirrel_plays_fof4318); MIT licence, notice in `THIRD_PARTY_NOTICES.md`), tuned toward **harvestgreen22**'s FM27 attribute testing on fm-arena. Thank you, Jamie.
- The memory reader and the interface were written for this project.

## License

FMMT 27 is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. See [LICENSE](LICENSE).

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

## Disclaimer

This is an unofficial fan project. It is not affiliated with, endorsed by or connected to Sports Interactive or SEGA. Football Manager is a trademark of Sports Interactive and SEGA. The tool only reads the game's memory on your own computer and never modifies the game or your save files.
