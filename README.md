# Kixxy - Call Data Analytics Tool

A Python command-line tool for analyzing call data exported from Kixie/HubSpot CRM. Provides comprehensive insights into call performance, agent productivity, and conversion metrics.

## Features

- **Call Owner Analysis** - Track calls by agent with disposition breakdowns
- **Disposition Metrics** - Group calls by outcome (Voicemail, Interested, Not Interested, etc.)
- **Time Analysis** - Identify optimal calling hours and days of the week
- **Source Effectiveness** - Compare PowerDialer vs Manual Dial vs other sources
- **Campaign Performance** - Analyze conversion rates by campaign/list
- **Area Code Analytics** - Contact rates by geographic region
- **Conversion Funnel** - Track dials-to-interested ratio
- **Agent Session Time** - Calculate actual time spent on the dialer vs talk time
- **Weekly Summary** - Business week (Mon-Fri) productivity breakdown
- **Interested Leads Export** - Summary of converted leads with CRM links

## Installation

```bash
git clone https://github.com/msifoss/kixxy.git
cd kixxy
```

No external dependencies required - uses Python standard library only.

## Usage

```bash
# Basic usage - prints report to console
python kixxy.py input/calls.csv

# Save report to file
python kixxy.py input/calls.csv -o report.txt

# Export data to CSV files
python kixxy.py input/calls.csv --csv output/analysis.csv

# Both report and CSV export
python kixxy.py input/calls.csv -o report.txt --csv output/analysis.csv
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `input` | Input CSV file path (positional argument) |
| `-o, --output` | Save report to specified file |
| `--csv` | Export data to CSV files (creates 9 files with this base name) |
| `-h, --help` | Show help message |

## Input File Format

The tool expects a CSV export from Kixie with the following columns:

| Column | Description |
|--------|-------------|
| Date | Call timestamp (MM/DD/YYYY, HH:MM AM/PM) |
| Agent First Name | Name of the call agent |
| Type | Incoming or Outgoing |
| Status | Answered or Missed |
| Disposition | Call outcome (Voicemail, Interested, Not Interested, etc.) |
| Duration | Call length (M:SS or H:MM:SS) |
| Source | Call source (POWERDIALER, MANUAL-DIAL, etc.) |
| Source Link | Campaign/list name |
| CRM Link | HubSpot contact URL |
| CRM Contact ID | HubSpot contact ID |
| To Number | Destination phone number |

## Report Sections

### Overall Summary
```
Total Calls: 499
Total Duration: 4:36:09
Answered: 488 (97.8%)
Missed: 11 (2.2%)
Total Time on Phones: 58:27:08 (58.45 hours)
```

### Weekly Hours on Phones (Mon-Fri)
Shows weekly productivity with phone time, talk time, and efficiency percentage.

### Daily Call Hours Breakdown
Day-by-day breakdown of calls made and time spent.

### Conversion Rate Tracking
Daily conversion rates with interested lead counts.

### Time-of-Day Analysis
Hourly and day-of-week breakdown showing:
- Total calls
- Live answer rate
- Interested conversions

### Source Effectiveness
Compare call sources by conversion rate and voicemail rate.

### Contact Rate by Area Code
Geographic analysis of live answer rates.

### Calls-to-Conversion Funnel
```
Total Dials:              499  (100%)
  -> Connected:           488  (97.8%)
  -> Live Conversations:  228  (45.7%)
  -> Interested:           10  (2.0%)

Dials per Interested Lead: 49.9:1
```

### Campaign Performance
Compare campaigns by calls, conversions, and efficiency.

### Agent Dialer Session Time
Tracks actual time spent on the dialer per agent per day:
- First call time
- Last call time
- Session duration (last call end - first call start)
- Talk time vs session time efficiency

### Interested Leads Summary
List of all "Interested" outcomes with:
- Date/time
- Phone number
- Call duration
- CRM link for follow-up

## CSV Export Files

When using `--csv output/analysis.csv`, the following files are created:

| File | Contents |
|------|----------|
| `analysis_summary.csv` | Overall metrics |
| `analysis_daily.csv` | Daily breakdown |
| `analysis_dispositions.csv` | Disposition stats |
| `analysis_sources.csv` | Source effectiveness |
| `analysis_campaigns.csv` | Campaign performance |
| `analysis_area_codes.csv` | Area code contact rates |
| `analysis_agents.csv` | Agent statistics |
| `analysis_interested_leads.csv` | Interested lead details |
| `analysis_agent_sessions.csv` | Agent session times |

## Key Metrics Explained

### Efficiency
`Efficiency = Talk Time / Session Time × 100`

Measures how much of the agent's dialer session was spent actually talking vs waiting (ringing, voicemails, between calls).

### Live Answer Rate
`Live Answer Rate = Live Conversations / Total Calls × 100`

Excludes voicemails, bad numbers, and no-outcome calls.

### Conversion Rate
`Conversion Rate = Interested / Total Calls × 100`

Percentage of calls resulting in an "Interested" disposition.

## Example Output

```
================================================================================
CALL DATA ANALYSIS REPORT
================================================================================
Date Range: September 02, 2025 - November 25, 2025 (85 days)
Total Records: 499

================================================================================
OVERALL SUMMARY
================================================================================
Total Calls: 499
Total Duration: 4:36:09
Answered: 488 (97.8%)
Missed: 11 (2.2%)
Outgoing: 492 (98.6%)
Incoming: 7 (1.4%)
Avg Duration (answered): 0:33
Total Time on Phones: 58:27:08 (58.45 hours)
```

## License

MIT License

## Contributing

Pull requests welcome. For major changes, please open an issue first to discuss proposed changes.
