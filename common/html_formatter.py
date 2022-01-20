import common.date_utils as date_utils
import common.utils as utils
import datetime
import dateutil 


template = None
with open('/Users/gnowakow/Projects/EMS/TeamUp/docs/schedule_template.txt', 'r') as f:
    template = f.read()

unstaffed_template = None

with open('/Users/gnowakow/Projects/EMS/TeamUp/docs/unstaffed_template.txt', 'r') as f:
    unstaffed_template = f.read()


def build_shift_summary_table(summary) -> str:
    summary_table = '<table>'
    summary_table += '<tr><th>Member</th><th>Total Hours</th></tr>'
    for summary_key, summary_value in summary.items():
        summary_table += '<tr><td>{}</td><td>{}</td></tr>'.format(summary_key, summary_value)
    summary_table += '</table>'
    return summary_table



# Might consider this in the future: https://ptable.readthedocs.io/en/latest/tutorial.html  (at least for debugging/printing interactively ascii tables)
def format_html_shift_report(final_report_map):

    """
    Input: final_report_map


    Returns a map of:
      key: shift_date (Same key as in final_report_map.  Example: "2022-01-08T11:00:00-05:00")
      value: html_string
    """

    html_map = dict()

    for shift_date, shift_and_coverage in final_report_map.items():
        shift = shift_and_coverage['shift']
        coverage = shift_and_coverage['coverage']
        summary = shift_and_coverage['shift-summary']

        max_members = -1
        for coverage_span in coverage:
            max_members = max(max_members, len(coverage_span['who'].split(',')))

        shift_content = '<h2>{}</h2>'.format(utils.create_shift_name(shift))
        shift_content += '<h3>Shift Times: {} - {}</h3>'.format(date_utils.date_simple_format(shift['start_dt']), date_utils.date_simple_format(shift['end_dt']))
        shift_table = '<table>'
        shift_table += '<tr><th>Start</th><th>End</th><th>Hours</th>{}</tr>'.format(''.join(['<th>Member</th>' for x in range(max_members)]))
        for coverage_span in coverage:
            shift_row = '<tr><td>{}</td><td>{}</td><td class="cell_hour">{}</td>'.format(
                date_utils.key_to_date(coverage_span['start_dt']).strftime(date_utils.OUTPUT_FMT_YMDHM), 
                date_utils.key_to_date(coverage_span['end_dt']).strftime(date_utils.OUTPUT_FMT_YMDHM),
                date_utils.get_hours(date_utils.key_to_date(coverage_span['start_dt']), date_utils.key_to_date(coverage_span['end_dt']))
                )
            shift_row += ''.join(['<td>{}</td>'.format(x) for x in coverage_span['who'].split(',')])
            # TODO: Fill in blank cells with empty strings here
            num_blank_cells = max_members - len(coverage_span['who'].split(','))
            shift_row += ''.join(['<td></td>' for x in range(num_blank_cells)])
            shift_row += '</tr>'
            shift_table += shift_row

        shift_table += '</table>'
        shift_content += shift_table

        shift_content += '<h3>Shift Summary</h3>'
        shift_content += build_shift_summary_table(summary)

        html_file = template.replace('<!-- Content -->', shift_content)
        html_map[shift_date] = html_file

    return html_map


def format_html_report_errors(shift_errors, start_date, max_days):

    if len(shift_errors) == 0:
        return

    col_headers = ['Start', 'End', 'Hours', 'Role Required']
    classes = ['','','cell_hour','']

    print('The folowing shifts have errors:')
    shift_content = ''
    for shift_data in shift_errors:
        shift = shift_data['shift']
        errors = shift_data['errors']

        days_from_now = date_utils.get_days_diff(datetime.datetime.strptime(start_date, date_utils.API_DATE_FORMAT_YMD), dateutil.parser.isoparse(shift['start_dt']) )

        if days_from_now <= max_days:
            shift_content += '<h2>{} days from now</h2>'.format(days_from_now)

            error_rows = []
            for error in errors:
                shift_row = [
                    error['start_dt'],
                    error['end_dt'],
                    date_utils.get_hours(datetime.datetime.strptime(error['start_dt'], date_utils.OUTPUT_FMT_YMDHM), datetime.datetime.strptime(error['end_dt'], date_utils.OUTPUT_FMT_YMDHM)),
                    error['error']
                ]
                error_rows.append(shift_row)
            
            error_table = HtmlTable(col_headers, error_rows, classes)
            error_table.insert_header([utils.create_shift_name(shift)], [4])

            second_row = 'Shift Times: {} - {}'.format(
                date_utils.date_simple_format(shift['start_dt']), 
                date_utils.date_simple_format(shift['end_dt']))
            error_table.insert_header([second_row], [4])
            
        shift_content += str(error_table)

    return unstaffed_template.replace('<!-- Content -->', shift_content)


class HtmlTable:
    def __init__(self, header, rows, classes):
        self.header = header
        self.rows = rows
        self.classes = classes
        self.extra_headers = []

    def add_header(self, header):
        self.header = header

    def insert_header(self, extra_header, span=[]):
        extra_hdr = '<tr>'
        if len(span) > 0:
            for idx, hdr in enumerate(extra_header):
                if idx <= len(span) and span[idx] > 0:
                    extra_hdr += '<th colspan="{}">{}</th>'.format(span[idx], hdr)
                else:
                    extra_hdr += '<th>{}</th>'.format(hdr)
        extra_hdr += '</tr>'
        self.extra_headers.append(extra_hdr)

    def add_row(self, row):
        self.rows.append(row)

    def __str__(self):
        table = '<table>'
        table += ''.join(self.extra_headers)
        table += '<tr>'
        for header in self.header:
            table += '<th>{}</th>'.format(header)
        table += '</tr>'
        for row in self.rows:
            table += '<tr>'
            for idx, cell in enumerate(row):
                klass = ''
                if self.classes is not None and len(self.classes[idx]) > 0:
                    klass = ' class="{}"'.format(self.classes[idx])
                table += '<td{}>{}</td>'.format(klass, cell)
            table += '</tr>'
        table += '</table>'
        return table


