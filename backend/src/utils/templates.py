from jinja2 import Environment, PackageLoader, select_autoescape
from pathlib import Path
import json

from constants import CHECK_DESCRIPTIONS, HUMAN_READABLE_NAMES, REQUIRED_CHECKS_NAMES, OPTIONAL_CHECKS_NAMES, INFORMATION_CHECKS_NAMES
from .helpers import get_description, get_title, get_version_state

env = Environment(
        loader=PackageLoader("main"),
        autoescape=select_autoescape()
    )

main_dashboard = env.get_template("main_dashboard.html")
empty_dashboard = env.get_template("empty_dashboard.html")

#Renders dashboard
async def render_dashboard(dataset_id, metadata, validation_report, callback):

    test_results = json.loads(validation_report)

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

        if check_id in REQUIRED_CHECKS_NAMES:
            required_tests.append(entry)
            if is_visible:
                total_required += 1
                if test['status'] == 'SUCCESS':
                    passed_required += 1

        if check_id in OPTIONAL_CHECKS_NAMES:
            optional_tests.append(entry)
            if is_visible:
                total_optional += 1
                if test['status'] == 'SUCCESS':
                    passed_optional += 1

        if check_id in INFORMATION_CHECKS_NAMES:
            information_tests.append(entry)
            if is_visible:
                total_information += 1
                if test['status'] == 'SUCCESS':
                    passed_information += 1

        if is_visible:
            visible_checks += 1
            if test['status'] == 'SUCCESS':
                passed_checks += 1



    description = get_description(metadata)
    title = get_title(metadata)
    version_state = get_version_state(metadata)



    return main_dashboard.render(dataset_id=dataset_id,
                           required_tests = required_tests,
                           optional_tests = optional_tests,
                           information_tests = information_tests,
                           dataset_title = title,
                           version_state = version_state,
                           passed_checks = (passed_checks/visible_checks) if visible_checks else 0,
                           passed_required = passed_required,
                           total_required = total_required,
                           passed_optional = passed_optional,
                           total_optional = total_optional,
                           passed_information = passed_information,
                           total_information = total_information,
                           callback=callback
                           )

async def render_empty_dashboard(dataset_id, callback):
    return empty_dashboard.render(dataset_id=dataset_id, callback=callback)

