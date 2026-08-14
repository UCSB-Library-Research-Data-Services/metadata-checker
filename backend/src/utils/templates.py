from jinja2 import Environment, PackageLoader, select_autoescape
from pathlib import Path
import json
import logging

from constants import CHECK_DESCRIPTIONS, HUMAN_READABLE_NAMES
from validator import get_check_levels
from .helpers import get_description, get_title, get_version_state

logger = logging.getLogger(__name__)

env = Environment(
        loader=PackageLoader("main"),
        autoescape=select_autoescape()
    )

main_dashboard = env.get_template("main_dashboard.html")
empty_dashboard = env.get_template("empty_dashboard.html")
email_report = env.get_template("email_report.html")

#Colors used to render each check's status in the emailed report, where CSS
#custom properties/classes (styles.css) aren't available.
STATUS_COLORS = {
    "SUCCESS": "#2b8a3e", "OK": "#2b8a3e",
    "FAILURE": "#c92a2a", "FAILED": "#c92a2a", "ERROR": "#c92a2a",
    "WARN": "#e67700", "WARNING": "#e67700",
    "SKIP": "#5c6b7a", "SKIPPED": "#5c6b7a", "NA": "#5c6b7a",
}

#Parses a validation_report JSON string into required/optional/information
#test lists plus pass/total stats. Entries land in the *_tests lists regardless
#of visibility; only the numeric counters skip hidden checks.
def build_check_buckets(validation_report):

    test_results = json.loads(validation_report)
    check_levels = get_check_levels()

    #seperate out into three categories
    required_tests = []
    optional_tests = []
    information_tests = []


    #used for stats (only visible checks count toward these)
    passed_checks = 0
    visible_checks = 0
    passed_required = 0
    total_required = 0
    passed_optional = 0
    total_optional = 0
    passed_information = 0
    total_information = 0



    #sort into three lists, get stats
    for test in test_results:
        check_id = test['check_id'].removesuffix('.xml')
        is_visible = bool(test.get('visibility', 1))

        entry = {'check_id': check_id,
                 'label': HUMAN_READABLE_NAMES.get(check_id, check_id),
                 'status': test['status'],
                 'description': CHECK_DESCRIPTIONS.get(check_id, "No description available."),
                 'output': test.get('output'),
                 'visibility': is_visible
                 }

        level = check_levels.get(check_id)

        if level == "REQUIRED":
            required_tests.append(entry)
            if is_visible:
                total_required += 1
                if test['status'] == 'SUCCESS':
                    passed_required += 1
        elif level == "OPTIONAL":
            optional_tests.append(entry)
            if is_visible:
                total_optional += 1
                if test['status'] == 'SUCCESS':
                    passed_optional += 1
        elif level == "INFO":
            information_tests.append(entry)
            if is_visible:
                total_information += 1
                if test['status'] == 'SUCCESS':
                    passed_information += 1
        else:
            logger.warning("Check %s has no level in the suite XML; dropped from dashboard", check_id)

        if is_visible:
            visible_checks += 1
            if test['status'] == 'SUCCESS':
                passed_checks += 1

    return {
        'required_tests': required_tests,
        'optional_tests': optional_tests,
        'information_tests': information_tests,
        'passed_checks': passed_checks,
        'visible_checks': visible_checks,
        'passed_required': passed_required,
        'total_required': total_required,
        'passed_optional': passed_optional,
        'total_optional': total_optional,
        'passed_information': passed_information,
        'total_information': total_information,
    }

#Renders dashboard
async def render_dashboard(dataset_id, metadata, validation_report, callback, report_generated_at):

    buckets = build_check_buckets(validation_report)

    description = get_description(metadata)
    title = get_title(metadata)
    version_state = get_version_state(metadata)



    return main_dashboard.render(dataset_id=dataset_id,
                           required_tests = buckets['required_tests'],
                           optional_tests = buckets['optional_tests'],
                           information_tests = buckets['information_tests'],
                           dataset_title = title,
                           version_state = version_state,
                           report_generated_at = report_generated_at,
                           passed_checks = (buckets['passed_checks']/buckets['visible_checks']) if buckets['visible_checks'] else 0,
                           passed_required = buckets['passed_required'],
                           total_required = buckets['total_required'],
                           passed_optional = buckets['passed_optional'],
                           total_optional = buckets['total_optional'],
                           passed_information = buckets['passed_information'],
                           total_information = buckets['total_information'],
                           callback=callback
                           )

async def render_empty_dashboard(dataset_id, callback):
    return empty_dashboard.render(dataset_id=dataset_id, callback=callback)

#Renders the emailed report. Unlike the dashboard, hidden checks are fully
#excluded (not just excluded from stats), matching what the user currently
#sees after toggling checks off.
async def render_report_email(dataset_id, metadata, validation_report):

    buckets = build_check_buckets(validation_report)

    visible_required = [t for t in buckets['required_tests'] if t['visibility']]
    visible_optional = [t for t in buckets['optional_tests'] if t['visibility']]
    visible_information = [t for t in buckets['information_tests'] if t['visibility']]

    return email_report.render(
        dataset_id=dataset_id,
        dataset_title=get_title(metadata),
        version_state=get_version_state(metadata),
        required_tests=visible_required,
        optional_tests=visible_optional,
        information_tests=visible_information,
        passed_checks=(buckets['passed_checks'] / buckets['visible_checks']) if buckets['visible_checks'] else 0,
        passed_required=buckets['passed_required'],
        total_required=buckets['total_required'],
        passed_optional=buckets['passed_optional'],
        total_optional=buckets['total_optional'],
        passed_information=buckets['passed_information'],
        total_information=buckets['total_information'],
        status_colors=STATUS_COLORS,
    )

