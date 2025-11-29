import csv
import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta
import re

def parse_duration(duration_str):
    """Convert duration string (M:SS or H:MM:SS) to total seconds"""
    if not duration_str or duration_str == '0':
        return 0
    parts = duration_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

def format_duration(seconds):
    """Format seconds as H:MM:SS or M:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def parse_date(date_str):
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str.strip('"'), "%m/%d/%Y, %I:%M %p")
    except:
        return None

def get_area_code(phone_number):
    """Extract area code from phone number"""
    digits = re.sub(r'\D', '', str(phone_number))
    if len(digits) >= 10:
        if digits.startswith('1'):
            return digits[1:4]
        return digits[:3]
    return 'Unknown'

def analyze_calls(filepath):
    # Data structures
    agents = defaultdict(lambda: {'total_calls': 0, 'total_duration': 0, 'dispositions': defaultdict(int),
                                   'call_types': defaultdict(int), 'statuses': defaultdict(int)})
    dispositions = defaultdict(lambda: {'count': 0, 'total_duration': 0})
    overall_stats = {'total_calls': 0, 'total_duration': 0, 'answered': 0, 'missed': 0,
                     'incoming': 0, 'outgoing': 0, 'interested': 0}
    sources = defaultdict(lambda: {'total': 0, 'interested': 0, 'answered': 0, 'voicemail': 0})

    # New analytics structures
    hourly_stats = defaultdict(lambda: {'total': 0, 'answered': 0, 'interested': 0, 'live_answer': 0})
    day_of_week_stats = defaultdict(lambda: {'total': 0, 'answered': 0, 'interested': 0, 'live_answer': 0})
    campaigns = defaultdict(lambda: {'total': 0, 'interested': 0, 'answered': 0, 'voicemail': 0,
                                      'not_interested': 0, 'duration': 0})
    area_codes = defaultdict(lambda: {'total': 0, 'live_answer': 0, 'voicemail': 0})

    # For conversion tracking over time
    daily_conversions = defaultdict(lambda: {'total': 0, 'interested': 0, 'duration': 0})

    # Date range tracking
    min_date = None
    max_date = None

    # Interested leads details
    interested_leads = []

    # Agent session tracking (first/last call per day per agent)
    agent_daily_sessions = defaultdict(lambda: defaultdict(lambda: {'first_call': None, 'last_call': None, 'last_call_duration': 0, 'talk_time': 0}))

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agent = row['Agent First Name']
            disposition = row['Disposition'] or 'Unknown'
            duration = parse_duration(row['Duration'])
            call_type = row['Type']
            status = row['Status']
            source = row['Source'] or 'Unknown'
            campaign = row.get('Source Link', '') or 'No Campaign'
            to_number = row.get('To Number', '')
            date_obj = parse_date(row['Date'])

            is_interested = disposition == 'Interested'
            is_voicemail = disposition == 'Voicemail'
            is_live_answer = status == 'Answered' and disposition not in ['Voicemail', 'No Call Outcome', 'Bad Number']

            # Agent stats
            agents[agent]['total_calls'] += 1
            agents[agent]['total_duration'] += duration
            agents[agent]['dispositions'][disposition] += 1
            agents[agent]['call_types'][call_type] += 1
            agents[agent]['statuses'][status] += 1

            # Disposition stats
            dispositions[disposition]['count'] += 1
            dispositions[disposition]['total_duration'] += duration

            # Overall stats
            overall_stats['total_calls'] += 1
            overall_stats['total_duration'] += duration
            if status == 'Answered':
                overall_stats['answered'] += 1
            else:
                overall_stats['missed'] += 1
            if call_type == 'Incoming':
                overall_stats['incoming'] += 1
            else:
                overall_stats['outgoing'] += 1
            if is_interested:
                overall_stats['interested'] += 1

            # Source effectiveness stats
            sources[source]['total'] += 1
            if is_interested:
                sources[source]['interested'] += 1
            if status == 'Answered':
                sources[source]['answered'] += 1
            if is_voicemail:
                sources[source]['voicemail'] += 1

            # Time-based analytics
            if date_obj:
                hour = date_obj.hour
                day_name = date_obj.strftime('%A')
                date_key = date_obj.strftime('%Y-%m-%d')

                # Track date range
                if min_date is None or date_obj < min_date:
                    min_date = date_obj
                if max_date is None or date_obj > max_date:
                    max_date = date_obj

                # Hourly stats
                hourly_stats[hour]['total'] += 1
                if status == 'Answered':
                    hourly_stats[hour]['answered'] += 1
                if is_interested:
                    hourly_stats[hour]['interested'] += 1
                if is_live_answer:
                    hourly_stats[hour]['live_answer'] += 1

                # Day of week stats
                day_of_week_stats[day_name]['total'] += 1
                if status == 'Answered':
                    day_of_week_stats[day_name]['answered'] += 1
                if is_interested:
                    day_of_week_stats[day_name]['interested'] += 1
                if is_live_answer:
                    day_of_week_stats[day_name]['live_answer'] += 1

                # Daily conversion tracking (now includes duration)
                daily_conversions[date_key]['total'] += 1
                daily_conversions[date_key]['duration'] += duration
                if is_interested:
                    daily_conversions[date_key]['interested'] += 1

                # Track agent session times (first/last call per day)
                session = agent_daily_sessions[agent][date_key]
                if session['first_call'] is None or date_obj < session['first_call']:
                    session['first_call'] = date_obj
                if session['last_call'] is None or date_obj > session['last_call']:
                    session['last_call'] = date_obj
                    session['last_call_duration'] = duration
                session['talk_time'] += duration

            # Track interested leads details
            if is_interested:
                interested_leads.append({
                    'date': row['Date'],
                    'to_number': to_number,
                    'crm_link': row.get('CRM Link', ''),
                    'crm_contact_id': row.get('CRM Contact ID', ''),
                    'duration': row['Duration'],
                    'campaign': campaign
                })

            # Campaign stats
            campaigns[campaign]['total'] += 1
            campaigns[campaign]['duration'] += duration
            if is_interested:
                campaigns[campaign]['interested'] += 1
            if status == 'Answered':
                campaigns[campaign]['answered'] += 1
            if is_voicemail:
                campaigns[campaign]['voicemail'] += 1
            if disposition == 'Not Interested':
                campaigns[campaign]['not_interested'] += 1

            # Area code contact rate
            area_code = get_area_code(to_number)
            area_codes[area_code]['total'] += 1
            if is_live_answer:
                area_codes[area_code]['live_answer'] += 1
            if is_voicemail:
                area_codes[area_code]['voicemail'] += 1

    return {
        'agents': agents,
        'dispositions': dispositions,
        'overall_stats': overall_stats,
        'sources': sources,
        'hourly_stats': hourly_stats,
        'day_of_week_stats': day_of_week_stats,
        'campaigns': campaigns,
        'area_codes': area_codes,
        'daily_conversions': daily_conversions,
        'min_date': min_date,
        'max_date': max_date,
        'interested_leads': interested_leads,
        'agent_daily_sessions': agent_daily_sessions
    }

def print_report(data):
    agents = data['agents']
    dispositions = data['dispositions']
    overall_stats = data['overall_stats']
    sources = data['sources']
    hourly_stats = data['hourly_stats']
    day_of_week_stats = data['day_of_week_stats']
    campaigns = data['campaigns']
    area_codes = data['area_codes']
    daily_conversions = data['daily_conversions']
    min_date = data['min_date']
    max_date = data['max_date']
    interested_leads = data['interested_leads']
    agent_daily_sessions = data['agent_daily_sessions']

    print("=" * 80)
    print("CALL DATA ANALYSIS REPORT")
    print("=" * 80)

    # Date Range
    if min_date and max_date:
        date_range_str = f"{min_date.strftime('%B %d, %Y')} - {max_date.strftime('%B %d, %Y')}"
        num_days = (max_date - min_date).days + 1
        print(f"Date Range: {date_range_str} ({num_days} days)")
    print(f"Total Records: {overall_stats['total_calls']}")

    # Overall Summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"Total Calls: {overall_stats['total_calls']}")
    print(f"Total Duration: {format_duration(overall_stats['total_duration'])}")
    print(f"Answered: {overall_stats['answered']} ({overall_stats['answered']/overall_stats['total_calls']*100:.1f}%)")
    print(f"Missed: {overall_stats['missed']} ({overall_stats['missed']/overall_stats['total_calls']*100:.1f}%)")
    print(f"Outgoing: {overall_stats['outgoing']} ({overall_stats['outgoing']/overall_stats['total_calls']*100:.1f}%)")
    print(f"Incoming: {overall_stats['incoming']} ({overall_stats['incoming']/overall_stats['total_calls']*100:.1f}%)")
    if overall_stats['answered'] > 0:
        avg_duration = overall_stats['total_duration'] / overall_stats['answered']
        print(f"Avg Duration (answered): {format_duration(int(avg_duration))}")

    # Calculate total time on phones (dialer session time)
    total_phone_time = 0
    for agent in agent_daily_sessions:
        for date_key in agent_daily_sessions[agent]:
            session = agent_daily_sessions[agent][date_key]
            if session['first_call'] and session['last_call']:
                last_call_end = session['last_call'].timestamp() + session['last_call_duration']
                session_seconds = last_call_end - session['first_call'].timestamp()
                total_phone_time += session_seconds
    print(f"Total Time on Phones: {format_duration(int(total_phone_time))} ({total_phone_time/3600:.2f} hours)")

    # WEEKLY HOURS ON PHONES (Business Week: Mon-Fri)
    print("\n" + "=" * 80)
    print("WEEKLY HOURS ON PHONES (Mon-Fri)")
    print("=" * 80)

    # Group sessions by business week (week starts Monday)
    weekly_sessions = defaultdict(lambda: {'phone_time': 0, 'talk_time': 0, 'days_worked': set()})
    for agent in agent_daily_sessions:
        for date_key in agent_daily_sessions[agent]:
            session = agent_daily_sessions[agent][date_key]
            if session['first_call'] and session['last_call']:
                date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                # Skip weekends
                if date_obj.weekday() >= 5:  # Saturday=5, Sunday=6
                    continue
                # Get the Monday of this week
                week_start = date_obj - timedelta(days=date_obj.weekday())
                week_key = week_start.strftime('%Y-%m-%d')

                last_call_end = session['last_call'].timestamp() + session['last_call_duration']
                session_seconds = last_call_end - session['first_call'].timestamp()
                weekly_sessions[week_key]['phone_time'] += session_seconds
                weekly_sessions[week_key]['talk_time'] += session['talk_time']
                weekly_sessions[week_key]['days_worked'].add(date_key)

    print(f"{'Week Starting':<14} {'Days':<6} {'Phone Time':<14} {'Talk Time':<12} {'Efficiency':<10}")
    print("-" * 56)
    total_weekly_phone = 0
    total_weekly_talk = 0
    for week_key in sorted(weekly_sessions.keys()):
        stats = weekly_sessions[week_key]
        week_date = datetime.strptime(week_key, '%Y-%m-%d')
        week_end = week_date + timedelta(days=4)  # Friday
        week_label = f"{week_date.strftime('%m/%d')}-{week_end.strftime('%m/%d')}"
        days_count = len(stats['days_worked'])
        efficiency = (stats['talk_time'] / stats['phone_time'] * 100) if stats['phone_time'] > 0 else 0
        print(f"{week_label:<14} {days_count:<6} {format_duration(int(stats['phone_time'])):<14} {format_duration(stats['talk_time']):<12} {efficiency:.1f}%")
        total_weekly_phone += stats['phone_time']
        total_weekly_talk += stats['talk_time']
    print("-" * 56)
    total_eff = (total_weekly_talk / total_weekly_phone * 100) if total_weekly_phone > 0 else 0
    print(f"{'TOTAL':<14} {'':<6} {format_duration(int(total_weekly_phone)):<14} {format_duration(total_weekly_talk):<12} {total_eff:.1f}%")

    # DAILY HOURS BREAKDOWN
    print("\n" + "=" * 80)
    print("DAILY CALL HOURS BREAKDOWN")
    print("=" * 80)
    print(f"{'Date':<12} {'Day':<10} {'Calls':<8} {'Duration':<12} {'Hours':<8}")
    print("-" * 50)
    total_daily_hours = 0
    sorted_dates = sorted(daily_conversions.items())
    for date, stats in sorted_dates:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%a')
        except:
            day_name = ''
        hours = stats['duration'] / 3600
        total_daily_hours += hours
        print(f"{date:<12} {day_name:<10} {stats['total']:<8} {format_duration(stats['duration']):<12} {hours:.2f}")
    print("-" * 50)
    print(f"{'TOTAL':<12} {'':<10} {overall_stats['total_calls']:<8} {format_duration(overall_stats['total_duration']):<12} {total_daily_hours:.2f}")

    # 1. CONVERSION RATE TRACKING
    print("\n" + "=" * 80)
    print("1. CONVERSION RATE TRACKING")
    print("=" * 80)
    interested = overall_stats['interested']
    total = overall_stats['total_calls']
    print(f"Total 'Interested' Outcomes: {interested}")
    print(f"Overall Conversion Rate: {interested/total*100:.2f}%")
    print(f"\nConversion Rate by Date:")
    sorted_dates = sorted(daily_conversions.items())
    for date, stats in sorted_dates:
        conv_rate = stats['interested'] / stats['total'] * 100 if stats['total'] > 0 else 0
        interested_str = f" -> {stats['interested']} interested" if stats['interested'] > 0 else ""
        print(f"  {date}: {stats['total']} calls, {conv_rate:.1f}% conversion{interested_str}")

    # 2. TIME-OF-DAY ANALYSIS
    print("\n" + "=" * 80)
    print("2. TIME-OF-DAY ANALYSIS")
    print("=" * 80)
    print("\nBy Hour:")
    print(f"{'Hour':<8} {'Calls':<8} {'Live Answer':<14} {'Live %':<10} {'Interested':<12}")
    print("-" * 52)
    for hour in sorted(hourly_stats.keys()):
        stats = hourly_stats[hour]
        live_pct = stats['live_answer'] / stats['total'] * 100 if stats['total'] > 0 else 0
        hour_str = f"{hour:02d}:00"
        print(f"{hour_str:<8} {stats['total']:<8} {stats['live_answer']:<14} {live_pct:<10.1f} {stats['interested']:<12}")

    print("\nBy Day of Week:")
    print(f"{'Day':<12} {'Calls':<8} {'Live Answer':<14} {'Live %':<10} {'Interested':<12}")
    print("-" * 56)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in day_order:
        if day in day_of_week_stats:
            stats = day_of_week_stats[day]
            live_pct = stats['live_answer'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"{day:<12} {stats['total']:<8} {stats['live_answer']:<14} {live_pct:<10.1f} {stats['interested']:<12}")

    # 3. SOURCE EFFECTIVENESS
    print("\n" + "=" * 80)
    print("3. SOURCE EFFECTIVENESS")
    print("=" * 80)
    print(f"{'Source':<30} {'Calls':<8} {'Interested':<12} {'Conv %':<10} {'VM Rate':<10}")
    print("-" * 70)
    sorted_sources = sorted(sources.items(), key=lambda x: x[1]['total'], reverse=True)
    for source, stats in sorted_sources:
        conv_rate = stats['interested'] / stats['total'] * 100 if stats['total'] > 0 else 0
        vm_rate = stats['voicemail'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"{source:<30} {stats['total']:<8} {stats['interested']:<12} {conv_rate:<10.1f} {vm_rate:<10.1f}")

    # 4. CONTACT RATE BY AREA CODE
    print("\n" + "=" * 80)
    print("4. CONTACT RATE (LIVE ANSWER) BY AREA CODE")
    print("=" * 80)
    print(f"{'Area Code':<12} {'Total':<8} {'Live Answer':<14} {'Live %':<10} {'Voicemail %':<12}")
    print("-" * 56)
    sorted_area_codes = sorted(area_codes.items(), key=lambda x: x[1]['total'], reverse=True)[:20]
    for ac, stats in sorted_area_codes:
        if stats['total'] >= 3:  # Only show area codes with 3+ calls
            live_pct = stats['live_answer'] / stats['total'] * 100 if stats['total'] > 0 else 0
            vm_pct = stats['voicemail'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"{ac:<12} {stats['total']:<8} {stats['live_answer']:<14} {live_pct:<10.1f} {vm_pct:<12.1f}")

    # 6. CALLS-TO-CONVERSION FUNNEL
    print("\n" + "=" * 80)
    print("6. CALLS-TO-CONVERSION FUNNEL")
    print("=" * 80)
    total_calls = overall_stats['total_calls']
    answered = overall_stats['answered']
    not_voicemail = answered - dispositions['Voicemail']['count']
    not_bad = not_voicemail - dispositions['Bad Number']['count'] - dispositions['No Call Outcome']['count']
    interested_count = overall_stats['interested']

    print(f"Total Dials:              {total_calls:>6}  (100%)")
    print(f"  -> Connected:           {answered:>6}  ({answered/total_calls*100:.1f}%)")
    print(f"  -> Live Conversations:  {not_bad:>6}  ({not_bad/total_calls*100:.1f}%)")
    print(f"  -> Interested:          {interested_count:>6}  ({interested_count/total_calls*100:.1f}%)")
    print(f"\nDials per Interested Lead: {total_calls/interested_count:.1f}:1" if interested_count > 0 else "\nNo interested leads yet")
    print(f"Live Conversations per Interested: {not_bad/interested_count:.1f}:1" if interested_count > 0 else "")

    # 7. CAMPAIGN PERFORMANCE
    print("\n" + "=" * 80)
    print("7. CAMPAIGN PERFORMANCE")
    print("=" * 80)
    print(f"{'Campaign':<35} {'Calls':<7} {'Int.':<6} {'Conv%':<7} {'VM%':<7} {'Avg Dur':<8}")
    print("-" * 80)
    sorted_campaigns = sorted(campaigns.items(), key=lambda x: x[1]['total'], reverse=True)
    for campaign, stats in sorted_campaigns:
        if stats['total'] >= 2:  # Only show campaigns with 2+ calls
            conv_rate = stats['interested'] / stats['total'] * 100 if stats['total'] > 0 else 0
            vm_rate = stats['voicemail'] / stats['total'] * 100 if stats['total'] > 0 else 0
            avg_dur = stats['duration'] / stats['total'] if stats['total'] > 0 else 0
            campaign_display = campaign[:33] + '..' if len(campaign) > 35 else campaign
            print(f"{campaign_display:<35} {stats['total']:<7} {stats['interested']:<6} {conv_rate:<7.1f} {vm_rate:<7.1f} {format_duration(int(avg_dur)):<8}")

    # Call Owners
    print("\n" + "=" * 80)
    print("CALL OWNERS (AGENTS)")
    print("=" * 80)
    sorted_agents = sorted(agents.items(), key=lambda x: x[1]['total_calls'], reverse=True)
    for agent, stats in sorted_agents:
        print(f"\n--- {agent} ---")
        print(f"  Total Calls: {stats['total_calls']}")
        print(f"  Total Duration: {format_duration(stats['total_duration'])}")
        if stats['total_calls'] > 0:
            answered = stats['statuses'].get('Answered', 0)
            if answered > 0:
                avg = stats['total_duration'] / answered
                print(f"  Avg Duration (answered): {format_duration(int(avg))}")
        print(f"  Call Types: {dict(stats['call_types'])}")
        print(f"  Statuses: {dict(stats['statuses'])}")
        print(f"  Top Dispositions:")
        sorted_disp = sorted(stats['dispositions'].items(), key=lambda x: x[1], reverse=True)[:5]
        for disp, count in sorted_disp:
            print(f"    - {disp}: {count}")

    # Agent Dialer Session Time
    print("\n" + "=" * 80)
    print("AGENT DIALER SESSION TIME")
    print("=" * 80)
    print("Time spent on dialer = Last call time + duration - First call time\n")

    for agent in sorted(agent_daily_sessions.keys()):
        sessions = agent_daily_sessions[agent]
        print(f"--- {agent} ---")
        print(f"{'Date':<12} {'First Call':<12} {'Last Call':<12} {'Session Time':<14} {'Talk Time':<12} {'Efficiency':<10}")
        print("-" * 72)

        total_session_seconds = 0
        total_talk_seconds = 0

        for date_key in sorted(sessions.keys()):
            session = sessions[date_key]
            if session['first_call'] and session['last_call']:
                first_time = session['first_call'].strftime('%I:%M %p')
                # Last call end time = last call start + duration
                last_end_seconds = session['last_call_duration']
                last_call_end = session['last_call'].timestamp() + last_end_seconds
                last_time = session['last_call'].strftime('%I:%M %p')

                # Session duration = last call end - first call start
                session_seconds = last_call_end - session['first_call'].timestamp()
                total_session_seconds += session_seconds

                # Get talk time for this agent on this day
                talk_seconds = session['talk_time']
                total_talk_seconds += talk_seconds

                # Efficiency = talk time / session time
                efficiency = (talk_seconds / session_seconds * 100) if session_seconds > 0 else 0

                print(f"{date_key:<12} {first_time:<12} {last_time:<12} {format_duration(int(session_seconds)):<14} {format_duration(talk_seconds):<12} {efficiency:.1f}%")

        print("-" * 72)
        total_efficiency = (total_talk_seconds / total_session_seconds * 100) if total_session_seconds > 0 else 0
        print(f"{'TOTAL':<12} {'':<12} {'':<12} {format_duration(int(total_session_seconds)):<14} {format_duration(total_talk_seconds):<12} {total_efficiency:.1f}%")
        print(f"\nTotal Dialer Time: {format_duration(int(total_session_seconds))} ({total_session_seconds/3600:.2f} hours)")
        print(f"Total Talk Time:   {format_duration(total_talk_seconds)} ({total_talk_seconds/3600:.2f} hours)")
        print()

    # Dispositions
    print("\n" + "=" * 80)
    print("CALLS BY DISPOSITION")
    print("=" * 80)
    sorted_dispositions = sorted(dispositions.items(), key=lambda x: x[1]['count'], reverse=True)
    for disp, stats in sorted_dispositions:
        avg_dur = stats['total_duration'] / stats['count'] if stats['count'] > 0 else 0
        pct = stats['count'] / overall_stats['total_calls'] * 100
        print(f"{disp}:")
        print(f"  Count: {stats['count']} ({pct:.1f}%)")
        print(f"  Total Duration: {format_duration(stats['total_duration'])}")
        print(f"  Avg Duration: {format_duration(int(avg_dur))}")

    # INTERESTED LEADS SUMMARY
    print("\n" + "=" * 80)
    print("INTERESTED LEADS SUMMARY")
    print("=" * 80)
    if interested_leads:
        print(f"Total Interested Leads: {len(interested_leads)}\n")
        print(f"{'Date':<22} {'Phone Number':<16} {'Duration':<10} {'CRM Link'}")
        print("-" * 100)
        for lead in interested_leads:
            phone = lead['to_number'] if lead['to_number'] else 'N/A'
            crm = lead['crm_link'] if lead['crm_link'] else 'No CRM Link'
            print(f"{lead['date']:<22} {phone:<16} {lead['duration']:<10} {crm}")
    else:
        print("No interested leads in this dataset.")

def export_csv(data, csv_filepath):
    """Export analysis data to CSV files"""
    import os
    base_path = os.path.splitext(csv_filepath)[0]

    overall_stats = data['overall_stats']
    daily_conversions = data['daily_conversions']
    dispositions = data['dispositions']
    sources = data['sources']
    campaigns = data['campaigns']
    area_codes = data['area_codes']
    agents = data['agents']
    interested_leads = data['interested_leads']
    min_date = data['min_date']
    max_date = data['max_date']

    # 1. Summary CSV
    summary_file = f"{base_path}_summary.csv"
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        if min_date and max_date:
            writer.writerow(['Date Range Start', min_date.strftime('%Y-%m-%d')])
            writer.writerow(['Date Range End', max_date.strftime('%Y-%m-%d')])
        writer.writerow(['Total Calls', overall_stats['total_calls']])
        writer.writerow(['Total Duration (seconds)', overall_stats['total_duration']])
        writer.writerow(['Answered', overall_stats['answered']])
        writer.writerow(['Missed', overall_stats['missed']])
        writer.writerow(['Outgoing', overall_stats['outgoing']])
        writer.writerow(['Incoming', overall_stats['incoming']])
        writer.writerow(['Interested', overall_stats['interested']])
        writer.writerow(['Conversion Rate %', f"{overall_stats['interested']/overall_stats['total_calls']*100:.2f}"])
    print(f"  Created: {summary_file}")

    # 2. Daily breakdown CSV
    daily_file = f"{base_path}_daily.csv"
    with open(daily_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Day', 'Calls', 'Duration_Seconds', 'Duration_Formatted', 'Hours', 'Interested'])
        for date, stats in sorted(daily_conversions.items()):
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                day_name = date_obj.strftime('%A')
            except:
                day_name = ''
            hours = stats['duration'] / 3600
            writer.writerow([date, day_name, stats['total'], stats['duration'],
                           format_duration(stats['duration']), f"{hours:.2f}", stats['interested']])
    print(f"  Created: {daily_file}")

    # 3. Dispositions CSV
    disp_file = f"{base_path}_dispositions.csv"
    with open(disp_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Disposition', 'Count', 'Percentage', 'Total_Duration_Seconds', 'Avg_Duration_Seconds'])
        for disp, stats in sorted(dispositions.items(), key=lambda x: x[1]['count'], reverse=True):
            pct = stats['count'] / overall_stats['total_calls'] * 100
            avg_dur = stats['total_duration'] / stats['count'] if stats['count'] > 0 else 0
            writer.writerow([disp, stats['count'], f"{pct:.1f}", stats['total_duration'], f"{avg_dur:.0f}"])
    print(f"  Created: {disp_file}")

    # 4. Sources CSV
    sources_file = f"{base_path}_sources.csv"
    with open(sources_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Source', 'Calls', 'Interested', 'Conversion_Rate', 'Voicemail_Rate'])
        for source, stats in sorted(sources.items(), key=lambda x: x[1]['total'], reverse=True):
            conv_rate = stats['interested'] / stats['total'] * 100 if stats['total'] > 0 else 0
            vm_rate = stats['voicemail'] / stats['total'] * 100 if stats['total'] > 0 else 0
            writer.writerow([source, stats['total'], stats['interested'], f"{conv_rate:.1f}", f"{vm_rate:.1f}"])
    print(f"  Created: {sources_file}")

    # 5. Campaigns CSV
    campaigns_file = f"{base_path}_campaigns.csv"
    with open(campaigns_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Campaign', 'Calls', 'Interested', 'Conversion_Rate', 'Voicemail_Rate', 'Avg_Duration_Seconds'])
        for campaign, stats in sorted(campaigns.items(), key=lambda x: x[1]['total'], reverse=True):
            conv_rate = stats['interested'] / stats['total'] * 100 if stats['total'] > 0 else 0
            vm_rate = stats['voicemail'] / stats['total'] * 100 if stats['total'] > 0 else 0
            avg_dur = stats['duration'] / stats['total'] if stats['total'] > 0 else 0
            writer.writerow([campaign, stats['total'], stats['interested'], f"{conv_rate:.1f}", f"{vm_rate:.1f}", f"{avg_dur:.0f}"])
    print(f"  Created: {campaigns_file}")

    # 6. Area codes CSV
    area_codes_file = f"{base_path}_area_codes.csv"
    with open(area_codes_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Area_Code', 'Total_Calls', 'Live_Answers', 'Live_Answer_Rate', 'Voicemail_Rate'])
        for ac, stats in sorted(area_codes.items(), key=lambda x: x[1]['total'], reverse=True):
            live_pct = stats['live_answer'] / stats['total'] * 100 if stats['total'] > 0 else 0
            vm_pct = stats['voicemail'] / stats['total'] * 100 if stats['total'] > 0 else 0
            writer.writerow([ac, stats['total'], stats['live_answer'], f"{live_pct:.1f}", f"{vm_pct:.1f}"])
    print(f"  Created: {area_codes_file}")

    # 7. Agents CSV
    agents_file = f"{base_path}_agents.csv"
    with open(agents_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Agent', 'Total_Calls', 'Total_Duration_Seconds', 'Answered', 'Missed', 'Incoming', 'Outgoing'])
        for agent, stats in sorted(agents.items(), key=lambda x: x[1]['total_calls'], reverse=True):
            writer.writerow([agent, stats['total_calls'], stats['total_duration'],
                           stats['statuses'].get('Answered', 0), stats['statuses'].get('Missed', 0),
                           stats['call_types'].get('Incoming', 0), stats['call_types'].get('Outgoing', 0)])
    print(f"  Created: {agents_file}")

    # 8. Interested leads CSV
    interested_file = f"{base_path}_interested_leads.csv"
    with open(interested_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Phone_Number', 'Duration', 'CRM_Contact_ID', 'CRM_Link', 'Campaign'])
        for lead in interested_leads:
            writer.writerow([lead['date'], lead['to_number'], lead['duration'],
                           lead['crm_contact_id'], lead['crm_link'], lead['campaign']])
    print(f"  Created: {interested_file}")

    # 9. Agent session times CSV
    agent_daily_sessions = data['agent_daily_sessions']
    sessions_file = f"{base_path}_agent_sessions.csv"
    with open(sessions_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Agent', 'Date', 'First_Call', 'Last_Call', 'Session_Seconds', 'Session_Formatted', 'Talk_Seconds', 'Talk_Formatted', 'Efficiency_Pct'])
        for agent in sorted(agent_daily_sessions.keys()):
            sessions = agent_daily_sessions[agent]
            for date_key in sorted(sessions.keys()):
                session = sessions[date_key]
                if session['first_call'] and session['last_call']:
                    first_time = session['first_call'].strftime('%I:%M %p')
                    last_time = session['last_call'].strftime('%I:%M %p')
                    last_call_end = session['last_call'].timestamp() + session['last_call_duration']
                    session_seconds = last_call_end - session['first_call'].timestamp()
                    talk_seconds = session['talk_time']
                    efficiency = (talk_seconds / session_seconds * 100) if session_seconds > 0 else 0
                    writer.writerow([agent, date_key, first_time, last_time, int(session_seconds),
                                   format_duration(int(session_seconds)), talk_seconds,
                                   format_duration(talk_seconds), f"{efficiency:.1f}"])
    print(f"  Created: {sessions_file}")

    print(f"\nCSV export complete: 9 files created with base name '{base_path}'")

def main():
    parser = argparse.ArgumentParser(
        description='Analyze call data from CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python kixxy.py input/calls.csv
  python kixxy.py input/calls.csv -o report.txt
  python kixxy.py input/calls.csv --csv output/analysis.csv
  python kixxy.py input/calls.csv -o report.txt --csv output/analysis.csv
        '''
    )
    parser.add_argument('input', nargs='?', default=r'input\kix-sep to 27 Nov.csv',
                        help='Input CSV file path (default: input\\kix-sep to 27 Nov.csv)')
    parser.add_argument('-o', '--output',
                        help='Output file path for the report (default: print to console)')
    parser.add_argument('--csv', metavar='CSV_PATH',
                        help='Also export data to CSV files (creates multiple files with this base name)')

    args = parser.parse_args()

    # Analyze the data
    print(f"Reading: {args.input}")
    data = analyze_calls(args.input)

    # Generate report
    if args.output:
        # Redirect stdout to file
        print(f"Writing report to: {args.output}")
        with open(args.output, 'w', encoding='utf-8') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            print_report(data)
            sys.stdout = old_stdout
        print("Report saved.")
    else:
        print_report(data)

    # Export CSV if requested
    if args.csv:
        print(f"\nExporting CSV files...")
        export_csv(data, args.csv)

if __name__ == '__main__':
    main()
