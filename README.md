# Lead scorer evals

An evaluation set for the prompt that scored investor prospects in an investor-acquisition system I built with Claude Code for a private Gulf real estate fund. The system and the client are described in the case study at https://yz-builds.netlify.app/case-study-01.html. I built this evaluation set with Claude Code after the engagement ended.

The scorer reads a prospect's profile and returns a 0 to 10 score, a hot, warm or cold label, and one of six buyer profiles. The set checks whether it applies its own scoring rules correctly and gives the same answer each time. It cannot show whether those rules pick people who would invest; only outreach could, and none was sent.

## What is here

- `cases.py`: 40 synthetic prospects. Each has the label and buyer profile the scoring rules should give, and a note on what the case tests.
- `run_eval.py`: sends each case to the Claude API in the tool's message format, grades the reply, and reports label accuracy, whether the score falls in the label's band, profile accuracy, and whether all runs of a case agree. `--capcode` applies the code-side rule from round three.
- `per_run.csv`: every graded run, 960 rows (40 cases, 3 runs, 2 models, 4 prompt versions).

The scoring prompt is not included, because it describes the client's fund. The model's raw replies are left out for the same reason. To run the set, supply your own prompt that returns JSON with `verdict`, `overall`, `persona` and `data_quality` fields, and put `ANTHROPIC_API_KEY=...` in a `.env` file next to the script.

```
python run_eval.py --model claude-sonnet-4-6 --prompt your_prompt.txt --runs 3 --tag test --workers 4
```

## Results

| Prompt | Model | Labels right | Profiles right | Cases with all 3 runs agreeing |
|---|---|---|---|---|
| v1 (as it ran) | Sonnet 4.6 | 83.3% | 92.5% | 39 of 40 |
| v2 | Sonnet 4.6 | 87.5% | 95.0% | 40 of 40 |
| v3 (kept) | Sonnet 4.6 | 87.5% | 97.5% | 40 of 40 |
| v4 | Sonnet 4.6 | 86.7% | 96.7% | 39 of 40 |
| v1 (as it ran) | Haiku 4.5 | 76.7% | 84.2% | 39 of 40 |
| v2 | Haiku 4.5 | 86.7% | 83.3% | 39 of 40 |
| v3 (kept) | Haiku 4.5 | 84.2% | 89.2% | 39 of 40 |
| v4 | Haiku 4.5 | 86.7% | 90.8% | 39 of 40 |

Sonnet 4.6 is the model the live tool called.

## What changed in each round

v1 treated work in Islamic finance or a Gulf family business as proof that a person had money of their own to invest. It scored one prospect hot even though they said their capital was locked up (case 15), scored a consultant obstetrician warm because it did not treat clinical titles as senior (case 40), and put students and research assistants in the catch-all allocator profile.

v2 added a rule on capacity and intent, capped the score at 6 when capital is locked up or limited, added senior clinical titles, and moved students and researchers under academics.

v3 stopped counting a board seat at a family-owned company as capacity, and made Islamic finance, family-office or endowment work decide the profile ahead of location.

v4 asked the model to quote the words in each profile that showed personal capital, and code lowered any hot label without a quote to warm. On Sonnet it fixed case 19 and broke cases 5, 22 and 39. For cases 16 and 37 the model quoted a family-business role as its evidence, so the rule never fired. Requiring the quote to appear word for word in the profile did worse (80.0% of labels on Sonnet), because the model rewords slightly even when the evidence is real. I kept v3.

Sonnet's remaining wrong labels on v3 are cases 11, 16, 18, 19 and 37. Three of them (16, 19, 37) are the same over-rating of senior Gulf business and Islamic finance roles. Those three are partly judgment calls on whether a family-business role implies personal capital; the expected labels reflect my reading of the scoring rules.
