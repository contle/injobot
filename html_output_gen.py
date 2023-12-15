from pathlib import Path

from common import save_to_file

CompanyDescription = tuple[str, str]
IdNameLocationType = tuple[str, str, str, str]
ExportRecords = list[IdNameLocationType]
ExportType = dict[CompanyDescription, ExportRecords]

html_start = '''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* {box-sizing: border-box}

body {
  font-family: "Lato", sans-serif;
  margin: 0;
}

html, body, .tab, .tabcontent {
  height: 100%;
}

.tab, .tabcontent {
  overflow-y: scroll;
}

.tab {
  float: left;
  border: 1px solid #ccc;
  background-color: #f1f1f1;
  width: 30%;
}

.tab button {
  display: block;
  background-color: inherit;
  color: black;
  padding: 22px 16px;
  width: 100%;
  border: none;
  outline: none;
  text-align: left;
  cursor: pointer;
  transition: 0.3s;
  font-size: 17px;
}

.tab button:hover {
  background-color: #ddd;
}

.tab button.active {
  background-color: #ccc;
}

.tabcontent {
  float: left;
  padding: 0px 12px;
  border: 1px solid #ccc;
  width: 70%;
  border-left: none;
}
</style>
</head>
<body>

<!--maybe later: <button onclick="saveIdsAndClose()">save ids and close</button><br>-->\n\n'''

html_end = '''<script>
function readPosition(evt, jobId) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(jobId).style.display = "block";
  evt.currentTarget.className += " active";
}

document.getElementById("firstTab").click();

var appliedIds = "";
function applied(jobId) {
  jobIdStr = jobId.toString();
  appliedIds += jobIdStr + ", ";
  window.open("https://www.linkedin.com/jobs/view/" + jobIdStr + "/", "_blank");
}

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/* // maybe later:
async function saveIdsAndClose() {
  var bb = new Blob([appliedIds], { type: 'text/plain' });
  var a = document.createElement('a');
  a.download = 'download.txt';
  a.href = window.URL.createObjectURL(bb);
  a.click();
  a.remove();
  await sleep(100);
  open(location, '_self').close();
}*/
</script>

</body>
</html>\n'''

def tab_button(id: int, caption: str, first_of_list: bool) -> str:
    default_text = ' id="firstTab"' if first_of_list else ''
    return f'  <button class="tablinks" onclick="readPosition(event, {id})"{default_text}>{caption}</button>\n'

def apply_button(job_id: int, caption: str) -> str:
    return f'<button onclick="applied({job_id})">{caption}</button>'

def tab_details(job_id: int, details: ExportRecords, description: str) -> str:
    pre_text = ''
    for (id, name, location, type) in details:
        pre_text += f'{apply_button(id, type)}{name}.{location}<br>\n'
    return f'<div id={job_id} class="tabcontent">{pre_text}<br>\n{description}\n</div>\n\n'

def generate_tabs_and_buttons(data: ExportType) -> str:
    buttons_text = '<div class="tab">\n'
    tabs_text = ''
    is_first = True
    for (company, description), details in data.items():
        first_id = details[0][0]
        first_position_name = details[0][1]
        buttons_text += tab_button(first_id, '<br>'.join((company, first_position_name)), is_first)
        is_first = False
        tabs_text += tab_details(first_id, details, description)
    buttons_text += '</div>\n\n'

    return buttons_text + tabs_text

def generate_html(filename: Path, data: ExportType) -> str:
    html_text = html_start + generate_tabs_and_buttons(data) + html_end
    save_to_file(filename, html_text)
