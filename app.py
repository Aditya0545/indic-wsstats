#!/usr/bin/env python3

import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from config import stats, Config

__version__ = "2.0"

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/indic_wsstats'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Stat model
class Stat(db.Model):
    __tablename__ = 'stats'
    id = db.Column(db.Integer, primary_key=True)
    language_code = db.Column(db.String(5), nullable=False)
    main_aps = db.Column(db.Integer)
    main_pages = db.Column(db.Integer)
    main_without_scan = db.Column(db.Integer)
    main_with_scan = db.Column(db.Integer)
    not_proofread = db.Column(db.Integer)
    num_of_pages = db.Column(db.Integer)
    page_aps = db.Column(db.Integer)
    problematic = db.Column(db.Integer)
    proofread = db.Column(db.Integer)
    validated = db.Column(db.Integer)
    without_text = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, nullable=False)

@app.route('/')
def index():
    data = Stat.query.all()  # Open the JSON file for reading
    print(f"Number of entries retrieved: {len(data)}")  # Debug output
    timestamp = data[-1].timestamp.strftime("%A, %d. %B %Y %I:%M%p") if data else "No data"
    return render_template('index.html', stats= stats, data= data, timestamp=timestamp)

@app.route('/wikitable')
def wikitable():
    stats = Stat.query.all() # Open the JSON file for reading
    if stats:
        wikiTable = "Statistics on "+ jsonData[ 'timestamp']
    else:
        wikiTable = "No data"

    wikiTable += """
{|class="wikitable sortable"
|-
! colspan="7" style="text-align:center;background: #ffffff;" | Page namespace
! colspan="4" style="text-align:center;background: #ffffff;" | Main namespace
|-
!style="background: #ffffff;"|'''Language'''
!style="background: #ffffff;"|'''All pages'''
!style="background: #ddd;"|'''Without text'''
!style="background: #ffa0a0;"|'''Not proofread'''
!style="background: #b0b0ff;"|'''Problematic'''
!style="background: #ffe867;"|'''Proofread'''
!style="background: #90ff90;"|'''Validated'''
!style="background: #ffffff;"|'''All pages'''
!style="background: #90ff90;"|'''With scans'''
!style="background: #ffa0a0;"|'''Without scans'''
!style="background: #ffffff;"|'''%'''"""

    for stat in stats:

        wikiTable += """\n|-
|%s || %d || %d || %d || %d || %d || %d || %d || %d || %d || %.2f""" % (
            stat,
            stat.language_code,
            stat.num_of_pages,
            stat.without_text,
            stat.not_proofread,
            stat.problematic,
            stat.proofread,
            stat.validated,
            stat.main_pages,
            stat.main_with_scan,
            stat.main_without_scan,
            100 * stat.main_with_scan / (stat.main_with_scan + stat.main_without_scan) if (stat.main_with_scan + stat.main_without_scan) > 0 else 0
        )

    wikiTable +="\n|}"
    return render_template('wikitable.html', Wikitable= wikiTable)

# API
@app.route('/api/stats')
def statsAPI():
    stats = Stat.query.all()
    stats_dict = {
        stat.language_code: {
            "Main_APS": stat.main_aps,
            "Main_Pages": stat.main_pages,
            "Main_WithOutScan": stat.main_without_scan,
            "Main_WithScan": stat.main_with_scan,
            "Not_proofread": stat.not_proofread,
            "Num_of_pages": stat.num_of_pages,
            "Page_APS": stat.page_aps,
            "Problematic": stat.problematic,
            "Proofread": stat.proofread,
            "Validated": stat.validated,
            "Without_text": stat.without_text
        }
        for stat in stats
    }
    return jsonify(stats_dict)


@app.route('/graph')
def graph():
    return render_template('graph.html')

@app.route('/activeuser')
def activeuser():
    wsProject = request.args.get('project', None)
    wsMonth = request.args.get('month', None)
    data = None
    fileExists = True
    total = {
        "proofread": 0,
        "validate": 0
    }
    if wsMonth is not None:
        try:
            jsonFile = open("ActiveUserStats/" + wsMonth + ".json", "r")
            data = json.load( jsonFile )
            jsonFile.close()
            data = data[wsProject]

            # Count the total
            for count in data.values():
                total["proofread"] = total["proofread"] + int(count["proofread"])
                total["validate"] = total["validate"] + int(count["validate"])
            return render_template('activeuser.html', data= data, project=wsProject, total=total, fileExists=True)
        except FileNotFoundError:
            return render_template('activeuser.html', data= "invalid", project=wsProject, total=total, fileExists=False)
    return render_template('activeuser.html', data= data, project=wsProject, total=total, fileExists=True)

@app.route('/logs')
def logs():
    with open("jobs.log", "r") as f:
        logList = f.readlines()
    if logList == []:
        return render_template('logs.html', logExists = False, logs = [])
    else:
        return render_template('logs.html',logExists = True, logs = logList)

# Migration route
@app.route('/insert_stats', methods=['POST'])
def insert_stats():
    try:
        with open('Stats.json') as f:
            data = json.load(f)

        # Get the timestamp
        timestamp_str = data.pop('timestamp')  # Remove timestamp from data to use later
        timestamp = datetime.strptime(timestamp_str, '%A, %d. %B %Y %I:%M%p')

        # Insert each language's stats into the database
        for lang_code, stats in data.items():
            # Check if the entry already exists
            existing_stat = Stat.query.filter_by(language_code=lang_code, timestamp=timestamp).first()
            if existing_stat:
                print(f"Data for {lang_code} on {timestamp} already exists. Skipping insertion.")
                continue  # Skip inserting if it already exists

            new_stat = Stat(
                language_code=lang_code,
                main_aps=stats['Main_APS'],
                main_pages=stats['Main_Pages'],
                main_without_scan=stats['Main_WithOutScan'],
                main_with_scan=stats['Main_WithScan'],
                not_proofread=stats['Not_proofread'],
                num_of_pages=stats['Num_of_pages'],
                page_aps=stats['Page_APS'],
                problematic=stats['Problematic'],
                proofread=stats['Proofread'],
                validated=stats['Validated'],
                without_text=stats['Without_text'],
                timestamp=timestamp
            )
            db.session.add(new_stat)

        db.session.commit()
        return jsonify({"message": "Stats inserted successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()

